"""
Validator Agent
Verifies that patches fix vulnerabilities without introducing new issues
Reference: Smartify - Refiner-Validator feedback loop
"""

import json
from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.mimo_llm import get_mimo_llm

logger = get_logger(__name__)


def _as_code(x):
    """Extract string code from dict or pass through if already a string."""
    return x["code"] if isinstance(x, dict) and "code" in x else x


class ValidatorAgent:
    """
    Validator Agent: Verifies patches fix vulnerabilities.
    
    Responsibilities:
    1. Verify patch fixes the vulnerability
    2. Ensure no new vulnerabilities introduced
    3. Run concrete execution tests
    4. Check gas optimization
    5. Validate backward compatibility
    
    Reference: Smartify - Refiner-Validator feedback loop
    """
    
    def __init__(self, tools: ToolKit, knowledge: KnowledgeBase):
        self.tools = tools
        self.knowledge = knowledge
        self.llm = get_mimo_llm()
    
    async def verify(self, contract_code: str, patch_code: str, vulnerability: dict) -> dict:
        """
        Verify a patch fixes a vulnerability.
        
        Uses Slither delta (detector disappearance) as the primary signal.
        Forge concrete tests are optional — their failure does not block `passed`.
        
        Args:
            contract_code: The original contract code
            patch_code: The patched code
            vulnerability: The vulnerability to verify
            
        Returns:
            Verification result with pass/fail and details
        """
        logger.info(f"Verifying patch for {vulnerability.get('id', 'unknown')}")
        
        # Run static analysis on patched code
        static_analysis = await self._run_static_analysis(patch_code)
        
        # Primary signal: Slither delta — does the target detector disappear?
        resolution = await self._check_vulnerability_resolved(contract_code, patch_code, vulnerability)
        
        # Check for new vulnerabilities
        new_vulnerabilities = await self._check_new_vulnerabilities(patch_code)
        
        # Optional signal: concrete execution (non-blocking)
        concrete_tests = await self._run_concrete_tests(contract_code, patch_code, vulnerability)
        
        # Primary signal: real exploit PoC (A1) — original should be exploitable,
        # patched should NOT be. exploit_confirmed is None when the exploit channel
        # is unavailable (gen/exec failed), in which case we fall back to Slither delta.
        exploit_poc = await self._run_exploit_poc(contract_code, patch_code, vulnerability)
        
        if exploit_poc.get("exploit_confirmed") is not None:
            # Primary signal available
            passed = exploit_poc["exploit_confirmed"]
        else:
            # Fallback: exploit channel unavailable → original Slither delta logic
            passed = (
                static_analysis["passed"]
                and resolution["resolved"]
                and len(new_vulnerabilities) == 0
            )
        
        return {
            "passed": passed,
            "details": {
                "static_analysis": static_analysis,
                "concrete_tests": concrete_tests,
                "new_vulnerabilities": new_vulnerabilities,
                "resolution": resolution,
                "exploit_poc": exploit_poc,
            },
            "score": self._calculate_score(static_analysis, concrete_tests, new_vulnerabilities, resolution, exploit_poc),
        }
    
    async def execute_exploit(self, contract_address: str, exploit_code: str) -> dict:
        """
        Execute an exploit against a contract.
        
        Args:
            contract_address: The contract address
            exploit_code: The exploit code
            
        Returns:
            Exploit execution result
        """
        logger.info(f"Executing exploit on {contract_address}")
        
        # Use concrete execution tool
        result = await self.tools.concrete_execution.execute(
            contract_address=contract_address,
            exploit_code=exploit_code,
        )
        
        return {
            "success": result.get("success", False),
            "transaction_hash": result.get("transaction_hash"),
            "profit": result.get("profit", 0),
            "gas_used": result.get("gas_used", 0),
            "details": result.get("details", ""),
        }
    
    async def _run_static_analysis(self, patch_code: str) -> dict:
        """Run static analysis on patched code"""
        logger.info("Running static analysis on patched code")
        
        try:
            # Use Slither
            results = self.tools.slither.analyze_code(_as_code(patch_code))
            
            # Check for critical issues
            critical_issues = [r for r in results if r.get("impact") == "High"]
            
            return {
                "passed": len(critical_issues) == 0,
                "issues": results,
                "critical_count": len(critical_issues),
            }
        except Exception as e:
            logger.error(f"Static analysis failed: {e}")
            return {
                "passed": False,
                "issues": [],
                "critical_count": 0,
                "error": str(e),
            }
    
    async def _check_vulnerability_resolved(self, contract_code: str, patch_code: str, vulnerability: dict) -> dict:
        """
        Slither delta check: did the target detector disappear after patching?
        
        Returns:
            {"resolved": bool, "original_checks": [...], "patched_checks": [...], "reason": str}
        """
        logger.info("Running Slither delta verification")
        
        try:
            original_results = self.tools.slither.analyze_code(_as_code(contract_code))
            patched_results = self.tools.slither.analyze_code(_as_code(patch_code))
            
            original_checks = [r.get("check", "") for r in original_results]
            patched_checks = [r.get("check", "") for r in patched_results]
            
            # Determine which detector check matches this vulnerability
            vuln_type = vulnerability.get("type", "").lower().strip()
            
            # Find matching check in original results (substring match, case-insensitive)
            target_check = None
            for check in original_checks:
                check_lower = check.lower()
                if vuln_type in check_lower or check_lower in vuln_type:
                    target_check = check
                    break
            
            if target_check:
                # Target detector was in original → check if it's gone in patched
                if target_check not in patched_checks:
                    return {
                        "resolved": True,
                        "original_checks": original_checks,
                        "patched_checks": patched_checks,
                        "reason": f"Detector '{target_check}' present in original, absent in patched code",
                    }
                else:
                    return {
                        "resolved": False,
                        "original_checks": original_checks,
                        "patched_checks": patched_checks,
                        "reason": f"Detector '{target_check}' still present after patching",
                    }
            else:
                # Vulnerability type not detected by Slither in original — weak pass
                # Check that patched code doesn't have MORE critical/high detectors
                orig_critical_high = sum(1 for r in original_results if r.get("impact") in ("High", "Critical"))
                patched_critical_high = sum(1 for r in patched_results if r.get("impact") in ("High", "Critical"))
                
                weak_pass = patched_critical_high <= orig_critical_high
                return {
                    "resolved": weak_pass,
                    "original_checks": original_checks,
                    "patched_checks": patched_checks,
                    "reason": (
                        f"Slither did not detect '{vuln_type}' in original code; "
                        f"weak-pass: critical/high count {orig_critical_high} -> {patched_critical_high}"
                    ),
                }
        except Exception as e:
            logger.error(f"Slither delta check failed: {e}")
            return {
                "resolved": False,
                "original_checks": [],
                "patched_checks": [],
                "reason": f"Slither delta check errored: {e}",
            }
    
    async def _run_concrete_tests(self, contract_code: str, patch_code: str, vulnerability: dict) -> dict:
        """
        Run concrete execution tests via Forge.
        
        This is an **optional** signal.  Forge scaffold is often unavailable, so
        a failure here does NOT hard-block the verification.  The caller inspects
        the 'skipped' flag.
        """
        logger.info("Running concrete execution tests (non-blocking)")
        
        try:
            # Generate test case for vulnerability
            test_case = await self._generate_test_case(vulnerability)
            
            # Run test on original code
            original_result = await self.tools.concrete_execution.test(
                contract_code=_as_code(contract_code),
                test_case=test_case,
            )
            
            # Run test on patched code
            patched_result = await self.tools.concrete_execution.test(
                contract_code=_as_code(patch_code),
                test_case=test_case,
            )
            
            # Verify patch fixes vulnerability
            # Original should be vulnerable (test fails), patched should pass
            passed = (
                original_result.get("tests_failed", 0) > 0 and
                patched_result.get("tests_failed", 0) == 0
            )
            
            return {
                "passed": passed,
                "skipped": False,
                "original_result": original_result,
                "patched_result": patched_result,
            }
        except Exception as e:
            logger.warning(f"Concrete tests unavailable (forge scaffold missing): {e}")
            return {
                "passed": None,
                "skipped": True,
                "reason": f"forge scaffold unavailable: {e}",
            }
    
    async def _check_new_vulnerabilities(self, patch_code: str) -> list[dict]:
        """Check for new vulnerabilities in patched code"""
        logger.info("Checking for new vulnerabilities")
        
        try:
            # Run Slither on patched code
            results = self.tools.slither.analyze_code(_as_code(patch_code))
            
            # Filter for high/medium severity
            new_vulns = [r for r in results if r.get("impact") in ["High", "Medium"]]
            
            return new_vulns
        except Exception as e:
            logger.error(f"Vulnerability check failed: {e}")
            return []

    async def _run_exploit_poc(self, original_code, patched_code, vulnerability) -> dict:
        """双向验证：原始合约 exploit 应成功，修补合约同一 exploit 应失败。
        返回 {exploit_confirmed: bool|None, original, patched, note}。
        任何异常/生成失败 → exploit_confirmed=None（T3.3 退回 Slither delta）。"""
        from src.tools.exploit_gen import generate_exploit

        def _ok(r):
            return r.get("tests_passed", 0) > 0 and r.get("tests_failed", 1) == 0

        try:
            exploit = await generate_exploit(self.llm, _as_code(original_code), vulnerability)
            if not exploit or not exploit.strip():
                return {"exploit_confirmed": None, "note": "exploit gen failed"}
            orig = await self.tools.concrete_execution.execute("local", exploit)
            # 修补合约：重新生成 exploit（patched_code 与 original 结构可能不同，replace 不可靠）
            patched_exploit = await generate_exploit(self.llm, _as_code(patched_code), vulnerability)
            patched = await self.tools.concrete_execution.execute("local", patched_exploit) if patched_exploit else {}
            confirmed = _ok(orig) and not _ok(patched)
            return {"exploit_confirmed": confirmed, "original": orig, "patched": patched}
        except Exception as e:
            logger.warning(f"exploit poc failed, fallback to slither delta: {e}")
            return {"exploit_confirmed": None, "note": str(e)}

    async def _generate_test_case(self, vulnerability: dict) -> str:
        """Generate a test case for a vulnerability using LLM"""
        vuln_type = vulnerability.get("type", "unknown")
        description = vulnerability.get("description", "")
        
        prompt = f"""Generate a Foundry test case for this vulnerability type.

Vulnerability Type: {vuln_type}
Description: {description}

Return a complete Foundry test contract with:
1. Setup function to deploy the vulnerable contract
2. Test function that demonstrates the vulnerability
3. Use forge-std/Test.sol

Return ONLY the Solidity code."""

        try:
            result = await self.llm.analyze_code(prompt)
            
            # Extract Solidity code
            if "```solidity" in result:
                code = result.split("```solidity")[1].split("```")[0]
                return code.strip()
            elif "```" in result:
                code = result.split("```")[1].split("```")[0]
                return code.strip()
            
            return result
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            
            # Fallback to template
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract VulnerabilityTest is Test {{
    function test_{vuln_type.replace('-', '_')}() public {{
        // Test for {vuln_type}
        // {description}
        assertTrue(true, "Vulnerability test placeholder");
    }}
}}"""
    
    def _calculate_score(self, static_analysis: dict, concrete_tests: dict, new_vulnerabilities: list, resolution: dict | None = None, exploit_poc: dict | None = None) -> float:
        """Calculate verification score.

        Weights (T3.3): exploit PoC is the primary signal (0.4); Slither delta
        resolution drops to auxiliary (0.2). When the exploit channel is
        unavailable (exploit_confirmed is None), its 0.4 falls back onto the
        resolution signal so scoring does not regress.
        """
        score = 0.0
        if static_analysis.get("passed", False):
            score += 0.3
        if len(new_vulnerabilities) == 0:
            score += 0.2

        confirmed = (exploit_poc or {}).get("exploit_confirmed")
        if confirmed is not None:
            # exploit channel active — primary signal 0.4
            if confirmed:
                score += 0.4
            # resolution as auxiliary 0.2
            if resolution and resolution.get("resolved", False):
                score += 0.2
        else:
            # exploit channel unavailable — fall back to Slither delta as primary (0.4)
            if resolution and resolution.get("resolved", False):
                score += 0.4
            # concrete tests bonus (legacy fallback)
            if concrete_tests.get("passed") is True:
                score += 0.1
        return score
