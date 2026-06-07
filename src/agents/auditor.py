"""
Auditor Agent
Analyzes code and identifies vulnerabilities
"""

from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.mimo_llm import get_mimo_llm

logger = get_logger(__name__)


class AuditorAgent:
    """
    Auditor Agent: Analyzes code and identifies vulnerabilities.
    
    Responsibilities:
    1. Static analysis using Slither
    2. LLM-based vulnerability detection
    3. RAG knowledge retrieval for context
    4. Broad Analysis (BA) for general vulnerabilities
    5. Targeted Analysis (TA) for known vulnerability types
    """

    _DETECTOR_FAMILIES = ("slither", "aderyn", "mimo", "ba", "ta", "expert1", "expert2", "triager")

    @staticmethod
    def _norm(s: str) -> str:
        """Normalise a string for fuzzy comparison in consensus scoring."""
        return (s or "").lower().replace("_", "").replace("-", "").replace(" ", "").strip()
    
    def __init__(self, tools: ToolKit, knowledge: KnowledgeBase):
        self.tools = tools
        self.knowledge = knowledge
        self.llm = get_mimo_llm()
        self.verificator_enabled = True
    
    async def detect(self, contract_path: str, use_multi_expert: bool = False, strategy: str = "all") -> list[dict]:
        """
        Detect vulnerabilities in a smart contract.
        
        Uses multiple detection strategies:
        1. Static analysis (Slither)
        2. LLM-based analysis (single or multi-expert)
        3. RAG knowledge retrieval
        4. Broad Analysis (BA) and/or Targeted Analysis (TA) per LLM-SmartAudit
        
        Args:
            contract_path: Path to the contract to analyze.
            use_multi_expert: Use multi-expert analysis instead of single LLM.
            strategy: Detection strategy — "ba" (broad), "ta" (targeted), or "all" (both, default).
        """
        logger.info(f"Detecting vulnerabilities in {contract_path} (strategy={strategy})")
        
        # Load contract code
        contract_code = self.tools.source_fetcher.fetch(contract_path)
        
        # Sanitize code
        sanitized_code = self.tools.code_sanitizer.sanitize(contract_code)
        
        # Run Slither, Aderyn, and LLM in parallel for speed
        import asyncio
        
        if use_multi_expert:
            # Multi-expert analysis (from forefy/.context)
            slither_results, aderyn_results, llm_results = await asyncio.gather(
                self._run_slither(contract_path),
                self._run_aderyn(contract_path),
                self._run_multi_expert_analysis(sanitized_code),
            )
        else:
            # Single LLM analysis
            slither_results, aderyn_results, llm_results = await asyncio.gather(
                self._run_slither(contract_path),
                self._run_aderyn(contract_path),
                self._run_llm_analysis(sanitized_code),
            )

        # BA/TA dual-strategy detection (LLM-SmartAudit §3.2.1)
        ba_results: list[dict] = []
        ta_results: list[dict] = []

        if strategy == "ba":
            ba_results = await self._broad_analysis(sanitized_code)
        elif strategy == "ta":
            ta_results = await self._targeted_analysis(sanitized_code)
        else:
            # strategy == "all": run both in parallel
            ba_results, ta_results = await asyncio.gather(
                self._broad_analysis(sanitized_code),
                self._targeted_analysis(sanitized_code),
            )

        # Collect raw findings from all sources BEFORE merging
        raw_findings = slither_results + aderyn_results + llm_results + ba_results + ta_results

        # Combine LLM + BA + TA for the merge step
        llm_results = llm_results + ba_results + ta_results

        # RAG knowledge retrieval
        rag_context = await self._retrieve_knowledge(sanitized_code)

        # Merge results — aderyn results join the static-analysis bucket
        static_results = slither_results + aderyn_results
        vulnerabilities = self._merge_results(static_results, llm_results, rag_context)

        # Tag each finding with the RAG source types that were retrieved
        rag_source_types = list({c.get("metadata", {}).get("type", "unknown") for c in rag_context})
        for v in vulnerabilities:
            v["rag_sources"] = rag_source_types

        # Confidence / consensus scoring
        vulnerabilities = self._score_confidence(vulnerabilities, raw_findings)

        # Verificator step: fact-check findings to reduce false positives
        vulnerabilities = await self._verify_findings(vulnerabilities, sanitized_code)

        # Log false positive summary
        false_positives = [v for v in vulnerabilities if not v.get("verified", True)]
        if false_positives:
            logger.info(f"Verificator flagged {len(false_positives)}/{len(vulnerabilities)} findings as false positives")

        return vulnerabilities
    
    async def get_vulnerability(self, contract_path: str, vulnerability_id: str) -> dict:
        """Get details of a specific vulnerability"""
        vulnerabilities = await self.detect(contract_path)
        
        for vuln in vulnerabilities:
            if vuln["id"] == vulnerability_id:
                return vuln
        
        raise ValueError(f"Vulnerability {vulnerability_id} not found")
    
    async def _run_slither(self, contract_path: str) -> list[dict]:
        """Run Slither static analysis"""
        logger.info("Running Slither analysis")
        
        # Use Slither tool
        results = self.tools.slither.analyze(contract_path)
        
        return [
            {
                "id": f"slither-{i}",
                "type": r["check"],
                "severity": r["impact"],
                "location": r["location"],
                "description": r["description"],
                "source": "slither",
            }
            for i, r in enumerate(results)
        ]

    async def _run_aderyn(self, contract_path: str) -> list[dict]:
        """Run Aderyn static analysis"""
        logger.info("Running Aderyn analysis")

        # Use Aderyn tool
        results = self.tools.aderyn.analyze(contract_path)

        return [
            {
                "id": f"aderyn-{i}",
                "type": r["check"],
                "severity": r["impact"],
                "location": r["location"],
                "description": r["description"],
                "source": "aderyn",
            }
            for i, r in enumerate(results)
        ]
    
    @staticmethod
    def _parse_vulnerabilities(raw: str, source: str = "mimo", id_prefix: str = "mimo") -> list[dict]:
        """Parse a JSON vulnerability list from an LLM response string.

        Handles responses where the JSON may be wrapped in markdown fences
        or embedded in prose.  Returns a normalised list of dicts ready for
        ``_merge_results``.
        """
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return []

        vulnerabilities = []
        for i, vuln in enumerate(data.get("vulnerabilities", [])):
            vulnerabilities.append({
                "id": f"{id_prefix}-{i}",
                "type": vuln.get("type", "unknown"),
                "severity": vuln.get("severity", "medium"),
                "location": vuln.get("location", ""),
                "description": vuln.get("description", ""),
                "recommendation": vuln.get("recommendation", ""),
                "source": source,
            })

        return vulnerabilities

    async def _run_llm_analysis(self, contract_code: str) -> list[dict]:
        """Run LLM-based vulnerability analysis using MiMo"""
        logger.info("Running LLM analysis with MiMo")
        
        try:
            result = await self.llm.analyze_code(contract_code)
            return self._parse_vulnerabilities(result, source="mimo", id_prefix="mimo")
        except Exception as e:
            logger.error(f"MiMo analysis failed: {e}")
            return []
    
    async def _run_multi_expert_analysis(self, contract_code: str) -> list[dict]:
        """
        Run multi-expert analysis from forefy/.context.
        
        Three separate analysis rounds:
        1. Security Expert 1: Systematic, methodical, core vulnerabilities
        2. Security Expert 2: Fresh perspective, economic focus
        3. Triager Validation: Challenge and validate findings
        """
        logger.info("Running multi-expert analysis")
        
        all_vulnerabilities = []
        
        # Round 1: Security Expert 1
        expert1_prompt = """You are Security Expert 1: Primary Smart Contract Auditor.
Systematic, methodical, focused on core vulnerabilities.

Analyze this code for:
1. Reentrancy vulnerabilities (all variants)
2. Access control mechanisms and permissions
3. Arithmetic operations for precision/overflow issues
4. External call safety and return value handling

Return JSON: {"vulnerabilities": [{"type": "...", "severity": "...", "location": "...", "description": "..."}]}"""
        
        # Round 2: Security Expert 2
        expert2_prompt = """You are Security Expert 2: Secondary Smart Contract Auditor.
Fresh perspective, economic focus, integration specialist.
Do NOT reference Expert 1's findings. Approach as if you've never seen their analysis.

Analyze for:
1. Economic attack vectors
2. Inter-contract communication security
3. External protocol integration risks
4. Composability and flash loan attack scenarios

Return JSON: {"vulnerabilities": [{"type": "...", "severity": "...", "location": "...", "description": "..."}]}"""
        
        # Round 3: Triager Validation
        triager_prompt = """You are the Triager Validation Expert (Budget Protector).
Financially motivated skeptic who must protect the security budget.
Actively challenge and attempt to disprove findings.

For each vulnerability, assess:
1. Is this a real vulnerability or false positive?
2. What is the actual business impact?
3. Is it worth fixing?

Return JSON: {"validated_vulnerabilities": [{"type": "...", "severity": "...", "location": "...", "description": "...", "is_valid": true/false, "business_impact": "..."}]}"""
        
        # Run all three experts in parallel
        import asyncio
        
        try:
            expert1_result, expert2_result, triager_result = await asyncio.gather(
                self.llm.generate(expert1_prompt + f"\n\nCode:\n```solidity\n{contract_code[:1500]}\n```"),
                self.llm.generate(expert2_prompt + f"\n\nCode:\n```solidity\n{contract_code[:1500]}\n```"),
                self.llm.generate(triager_prompt + f"\n\nCode:\n```solidity\n{contract_code[:1500]}\n```"),
            )
            
            # Parse all results
            import json
            import re
            
            for i, result in enumerate([expert1_result, expert2_result, triager_result]):
                expert_name = ["expert1", "expert2", "triager"][i]
                
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    
                    vulns = data.get("vulnerabilities", data.get("validated_vulnerabilities", []))
                    for j, vuln in enumerate(vulns):
                        # For triager, only include valid vulnerabilities
                        if expert_name == "triager" and not vuln.get("is_valid", True):
                            continue
                        
                        all_vulnerabilities.append({
                            "id": f"{expert_name}-{j}",
                            "type": vuln.get("type", "unknown"),
                            "severity": vuln.get("severity", "medium"),
                            "location": vuln.get("location", ""),
                            "description": vuln.get("description", ""),
                            "source": f"multi-expert-{expert_name}",
                        })
            
            logger.info(f"Multi-expert analysis found {len(all_vulnerabilities)} vulnerabilities")
            
        except Exception as e:
            logger.error(f"Multi-expert analysis failed: {e}")
        
        return all_vulnerabilities
    
    # ------------------------------------------------------------------
    # LLM-SmartAudit §3.2.1 — Broad Analysis (BA) & Targeted Analysis (TA)
    # ------------------------------------------------------------------

    _BA_SYSTEM_PROMPT = (
        "You are a Smart Contract Auditor performing Broad Analysis (BA).\n"
        "Use thought-reasoning: analyse the code step-by-step, identify potential issues, "
        "cross-check with known vulnerability patterns, and verify your reasoning.\n"
        "Return EXACTLY one JSON object: "
        '{"vulnerabilities": [{"type": "...", "severity": "critical/high/medium/low", '
        '"location": "function:line", "description": "..."}]}'
    )

    _TA_SYSTEM_PROMPT = (
        "You are a Smart Contract Auditor performing Targeted Analysis (TA).\n"
        "Focus ONLY on the specific vulnerability type requested. "
        "If the contract is NOT vulnerable, return {\"vulnerabilities\": []}.\n"
        'If it IS vulnerable, return: '
        '{"vulnerabilities": [{"type": "...", "severity": "critical/high/medium/low", '
        '"location": "function:line", "description": "...", "proof_of_concept": "..."}]}'
    )

    _TA_VULN_TYPES = [
        "reentrancy",
        "access_control",
        "integer_overflow",
        "front_running",
        "oracle_manipulation",
        "flash_loan_attack",
    ]

    async def _broad_analysis(self, contract_code: str) -> list[dict]:
        """BA mode: Thought-Reasoning (ReAct) prompt for broad-spectrum detection."""
        logger.info("Running Broad Analysis (BA)")

        prompt = (
            "Perform a broad-spectrum vulnerability analysis on the following "
            "Solidity smart contract. Identify ALL potential vulnerabilities.\n\n"
            f"```solidity\n{contract_code[:4000]}\n```"
        )

        try:
            result = await self.llm.generate(prompt, system_prompt=self._BA_SYSTEM_PROMPT)
            return self._parse_vulnerabilities(result, source="ba", id_prefix="ba")
        except Exception as e:
            logger.error(f"Broad Analysis (BA) failed: {e}")
            return []

    async def _targeted_analysis(self, contract_code: str) -> list[dict]:
        """TA mode: Buffer-Reasoning prompt, one prompt per known vulnerability type."""
        logger.info("Running Targeted Analysis (TA)")

        import asyncio

        async def _check_type(vuln_type: str) -> list[dict]:
            prompt = (
                f"Check this contract specifically for **{vuln_type}** vulnerabilities.\n\n"
                f"```solidity\n{contract_code[:4000]}\n```"
            )
            try:
                response = await self.llm.generate(prompt, system_prompt=self._TA_SYSTEM_PROMPT)
                parsed = self._parse_vulnerabilities(response, source="ta", id_prefix=f"ta-{vuln_type}")
                # Ensure the type field is set even if the LLM omitted it
                for p in parsed:
                    if p["type"] == "unknown":
                        p["type"] = vuln_type
                return parsed
            except Exception as e:
                logger.error(f"Targeted Analysis ({vuln_type}) failed: {e}")
                return []

        results_per_type = await asyncio.gather(
            *[_check_type(vt) for vt in self._TA_VULN_TYPES]
        )
        return [finding for batch in results_per_type for finding in batch]

    async def _retrieve_knowledge(self, contract_code: str) -> list[dict]:
        """Retrieve relevant knowledge from RAG"""
        logger.info("Retrieving knowledge from RAG")
        
        # Use knowledge base to find similar vulnerabilities
        results = await self.knowledge.query(contract_code)
        
        return results
    
    async def _verify_findings(self, findings: list[dict], contract_code: str) -> list[dict]:
        """SmartLLM Verificator: fact-check each finding against RAG knowledge to cut false positives."""
        import asyncio

        if not self.verificator_enabled:
            logger.info("Verificator: disabled, skipping")
            for f in findings:
                f.setdefault("verified", True)
                f.setdefault("verification_reasoning", "")
            return findings

        logger.info(f"Verificator: fact-checking {len(findings)} findings (parallel)")

        VERIFICATOR_SYSTEM = (
            "You are a Smart Contract Vulnerability Verificator. "
            "Your job is to fact-check a reported vulnerability finding against known vulnerability patterns "
            "and the actual contract code. Determine if the finding is a TRUE POSITIVE (real vulnerability) "
            "or FALSE POSITIVE (incorrect report). Be conservative: only declare FALSE POSITIVE if you have "
            "strong evidence that the reported issue does not exist in the code. "
            "\n\nRespond with EXACTLY this format:\n"
            "VERDICT: TRUE POSITIVE or FALSE POSITIVE\n"
            "REASONING: <your explanation>"
        )

        sem = asyncio.Semaphore(5)

        async def _verify_one(finding: dict) -> dict:
            """Verify a single finding with bounded concurrency."""
            finding.setdefault("verified", True)
            finding.setdefault("verification_reasoning", "")

            async with sem:
                # 1. RAG retrieval
                try:
                    query_text = f"{finding['type']} {finding.get('description', '')}"
                    rag_results = await self.knowledge.query(query_text=query_text, top_k=3)
                except Exception as e:
                    logger.warning(f"Verificator RAG query failed for {finding.get('id', '?')}: {e}")
                    rag_results = []

                knowledge_block = "\n".join(
                    f"- {r['content'][:300]}" for r in rag_results
                ) if rag_results else "(no relevant knowledge found)"

                # 2. Build verification prompt
                verification_prompt = (
                    f"Finding to verify:\n"
                    f"  Type: {finding['type']}\n"
                    f"  Description: {finding.get('description', 'N/A')}\n"
                    f"  Severity: {finding.get('severity', 'N/A')}\n"
                    f"  Location: {finding.get('location', 'N/A')}\n\n"
                    f"Relevant knowledge base entries:\n{knowledge_block}\n\n"
                    f"Contract code (relevant excerpt):\n```solidity\n{contract_code[:2000]}\n```\n\n"
                    f"Is this finding a TRUE POSITIVE or FALSE POSITIVE?"
                )

                # 3. Call LLM
                try:
                    response = await self.llm.generate(
                        prompt=verification_prompt,
                        system_prompt=VERIFICATOR_SYSTEM,
                        temperature=0.2,
                    )
                    finding["verification_reasoning"] = response.strip()
                except Exception as e:
                    logger.warning(f"Verificator LLM call failed for {finding.get('id', '?')}: {e}")
                    # On failure, keep finding as verified (conservative default)
                    return finding

                # 4. Parse verdict — conservative: only flag false positive on explicit match
                response_lower = response.lower()
                if "false positive" in response_lower and "true positive" not in response_lower:
                    finding["verified"] = False
                    logger.info(f"Verificator: {finding['type']} marked as FALSE POSITIVE")
                # Any ambiguity (both present, neither present, parse error) → keep as verified

            return finding

        return await asyncio.gather(*[_verify_one(f) for f in findings])

    def _score_confidence(self, merged: list[dict], raw_findings: list[dict]) -> list[dict]:
        """Annotate each merged finding with consensus score across detector families.

        Counts how many independent detector families flagged a matching
        (normalised type, normalised location) pair, then produces
        ``confidence`` ∈ [0, 1] and ``consensus_sources`` list on each finding.
        """
        for v in merged:
            key = (self._norm(v.get("type", "")), self._norm(v.get("location", "")))
            agree: set[str] = set()
            for r in raw_findings:
                rk = (self._norm(r.get("type", "")), self._norm(r.get("location", "")))
                # Match on normalised type; location must match or either side may be empty
                if rk[0] == key[0] and (rk[1] == key[1] or not key[1] or not rk[1]):
                    fam = (r.get("source", "") or "").split("-")[0]
                    if fam:
                        agree.add(fam)
            v["consensus_sources"] = sorted(agree)
            v["confidence"] = round(len(agree) / len(self._DETECTOR_FAMILIES), 3)
        return merged

    def _merge_results(self, slither_results: list[dict], llm_results: list[dict], rag_context: list[dict]) -> list[dict]:
        """Merge results from different detection strategies"""
        # Deduplicate and prioritize
        merged = {}
        
        # Add Slither results
        for vuln in slither_results:
            key = f"{vuln['type']}-{vuln['location']}"
            if key not in merged:
                merged[key] = vuln
        
        # Add LLM results (higher priority)
        for vuln in llm_results:
            key = f"{vuln['type']}-{vuln['location']}"
            merged[key] = vuln
        
        return list(merged.values())
