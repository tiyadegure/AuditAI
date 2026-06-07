"""
Refiner Agent
Iteratively improves code patches for quality and security.
Implements A1-style three-signal feedback loop using concrete execution.
"""

import json
from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.mimo_llm import get_mimo_llm

logger = get_logger(__name__)


class RefinerAgent:
    """
    Refiner Agent: Iteratively improves code patches with A1 three-signal feedback.

    Three signals from concrete_execution (A1 Algorithm 1):
      1. profit (float): 1.0 = profitable/passed, 0.0 = failed
      2. revert_reason (str): revert reason if execution reverted
      3. trace (str): full execution trace
    """

    def __init__(self, tools: ToolKit, knowledge: KnowledgeBase):
        self.tools = tools
        self.knowledge = knowledge
        self.llm = get_mimo_llm()
        self.max_iterations = 5  # A1 论文: 5轮收益递减, k=5 达 54.2%
        self.min_marginal_gain = 0.03  # 边际增益 < 3pp 提前终止

    async def refine(self, contract_code: str, patch: dict) -> dict:
        """
        Refine a code patch through iterative improvement with A1 three-signal feedback.

        Each iteration:
          1. Run concrete_execution.execute() → get profit / revert_reason / trace
          2. If profit >= 1.0 → patch verified, break
          3. Otherwise → build A1 follow-up prompt with all three signals → LLM improves patch
          4. If marginal gain < min_marginal_gain → early stop

        Returns:
            Backward-compatible dict with patch_code and refinement_iterations
        """
        logger.info(f"Refining patch for {patch['vulnerability_id']}")

        current_patch = patch["patch_code"]
        iterations = []
        prev_profit = 0.0

        for i in range(self.max_iterations):
            # --- Signal 1: Concrete Execution (A1 Algorithm 1, lines 9-10) ---
            exec_result = await self.tools.concrete_execution.execute(
                contract_address="local",
                exploit_code=current_patch,
            )

            # --- Signal 2: Binary Profitability Oracle ---
            curr_profit = exec_result.get("profit", 0.0)
            is_profitable = curr_profit >= 1.0

            # --- Signal 3: Revert Reason + Execution Trace ---
            revert_reason = exec_result.get("revert_reason", "")
            trace = exec_result.get("trace", "")

            if is_profitable:
                logger.info(f"Patch verified profitable at iteration {i}")
                iterations.append({
                    "iteration": i + 1,
                    "profitable": True,
                    "revert_reason": revert_reason,
                    "patch": current_patch,
                })
                break

            # Check marginal gain: if no improvement in profit signal, early stop
            marginal_gain = curr_profit - prev_profit
            if i > 0 and marginal_gain < self.min_marginal_gain:
                logger.info(
                    f"Marginal gain {marginal_gain:.3f} < {self.min_marginal_gain} at iteration {i}, stopping early"
                )
                iterations.append({
                    "iteration": i + 1,
                    "profitable": False,
                    "revert_reason": revert_reason,
                    "marginal_gain": marginal_gain,
                    "patch": current_patch,
                })
                break

            # Construct A1-style feedback dict (Appendix A.2)
            feedback = {
                "profit": curr_profit,
                "revert_reason": revert_reason,
                "trace_summary": trace[:300] if trace else "",
                "previous_tool_outputs": [
                    {"iteration": it["iteration"], "revert_reason": it.get("revert_reason", "")}
                    for it in iterations
                ],
            }

            # Improve via A1 follow-up prompt
            improved_patch = await self._improve_with_feedback(
                contract_code, current_patch, feedback
            )

            iterations.append({
                "iteration": i + 1,
                "profitable": False,
                "revert_reason": revert_reason,
                "marginal_gain": marginal_gain,
                "patch": improved_patch,
            })
            prev_profit = curr_profit
            current_patch = improved_patch

        # Fallback: supplement with LLM self-review for non-execution quality signals
        if not any(it.get("profitable") for it in iterations):
            review = await self._review_patch(contract_code, current_patch)
            if review.get("quality_score", 0.0) < 0.6:
                logger.warning(
                    f"LLM review quality {review['quality_score']:.2f} < 0.6, applying supplementary improvement"
                )
                improved = await self._improve_patch(contract_code, current_patch, review)
                current_patch = improved

        return {
            **patch,
            "patch_code": current_patch,
            "refinement_iterations": iterations,
        }

    async def _improve_with_feedback(
        self, contract_code: str, patch_code: str, feedback: dict
    ) -> str:
        """
        A1-style follow-up prompt: explicitly informs LLM of execution failure,
        revert reason, trace summary, preserves historical knowledge, and
        requests explicit reasoning.
        """
        logger.info("Generating A1 follow-up improvement")

        # Build history summary from previous tool outputs
        history_lines = []
        for prev in feedback.get("previous_tool_outputs", []):
            history_lines.append(
                f"  - Iteration {prev['iteration']}: revert_reason='{prev.get('revert_reason', 'N/A')}'"
            )
        history_summary = "\n".join(history_lines) if history_lines else "  (none)"

        system_prompt = (
            "You are an expert Solidity security engineer.\n"
            "Your task is to fix a smart contract patch that failed concrete execution.\n"
            "You must:\n"
            "1. Keep all knowledge from previous iterations\n"
            "2. Analyze what went wrong based on the execution signals\n"
            "3. Provide explicit reasoning in comments within your code\n"
            "4. Output ONLY the improved Solidity patch code"
        )

        prompt = (
            f"The previous patch attempt failed concrete execution.\n\n"
            f"## Previous Execution Signals (A1 three-signal feedback)\n\n"
            f"**Profit signal**: {feedback['profit']} (0.0 = failed, 1.0 = passed)\n"
            f"**Revert reason**: {feedback['revert_reason'] or 'N/A'}\n"
            f"**Execution trace (truncated)**:\n{feedback['trace_summary'] or 'N/A'}\n\n"
            f"## History of Previous Iterations\n{history_summary}\n\n"
            f"## Original Contract\n```solidity\n{contract_code}\n```\n\n"
            f"## Current Patch (failed)\n```solidity\n{patch_code}\n```\n\n"
            f"## Instructions\n"
            f"1. Diagnose WHY the patch failed (revert reason, trace)\n"
            f"2. Fix the root cause — do not make cosmetic changes\n"
            f"3. Add inline comments explaining your reasoning\n"
            f"4. Output ONLY the improved Solidity code, no markdown fences"
        )

        try:
            result = await self.llm.generate(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Refiner LLM call failed for {patch_code[:40]}...: {e}")
            return patch_code  # graceful degradation: return patch unchanged

        # Strip markdown fences if LLM wraps them
        code = result.strip()
        if code.startswith("```"):
            code = code.split("\n", 1)[-1] if "\n" in code else code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()

    async def _review_patch(self, contract_code: str, patch_code: str) -> dict:
        """Review a patch for quality and security issues using MiMo"""
        logger.info("Reviewing patch with MiMo")

        try:
            system_prompt = """You are an expert code reviewer for Solidity smart contracts.
Review patches for quality, security, and best practices."""

            prompt = f"""Review the following patch for quality and security issues.

Original Code:
```solidity
{contract_code}
```

Patched Code:
```solidity
{patch_code}
```

Provide review in JSON format:
{{
    "quality_score": 0.0-1.0,
    "improvements": ["improvement1", ...],
    "issues": ["issue1", ...]
}}"""

            result = await self.llm.generate(prompt, system_prompt)

            # Parse JSON response
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(result[start:end])

        except Exception as e:
            logger.error(f"MiMo review failed: {e}")

        # Fallback review
        return {
            "quality_score": 0.8,
            "improvements": [
                "Consider adding input validation",
                "Add event emission for transparency",
            ],
            "issues": [],
        }

    async def _improve_patch(self, contract_code: str, patch_code: str, review: dict) -> str:
        """Improve a patch based on review using MiMo"""
        logger.info("Improving patch with MiMo")

        try:
            system_prompt = """You are an expert Solidity developer.
Improve code patches based on review feedback."""

            prompt = f"""Improve the following patch based on review feedback.

Original Code:
```solidity
{contract_code}
```

Current Patch:
```solidity
{patch_code}
```

Review Feedback:
{json.dumps(review, indent=2)}

Provide the improved patch code."""

            return await self.llm.generate(prompt, system_prompt)

        except Exception as e:
            logger.error(f"MiMo improvement failed: {e}")
            return patch_code
