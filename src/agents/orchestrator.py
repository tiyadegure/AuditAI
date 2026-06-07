"""
Agent Orchestrator
Coordinates the five specialized agents for smart contract audit
"""

import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .auditor import AuditorAgent
from .architect import ArchitectAgent
from .code_generator import CodeGeneratorAgent
from .refiner import RefinerAgent
from .validator import ValidatorAgent
from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.checkpoint import save_checkpoint, load_checkpoint, clear_checkpoint

logger = get_logger(__name__)


@dataclass
class AuditResult:
    """Result of a smart contract audit"""
    contract_path: str
    vulnerabilities: list[dict]
    patches: list[dict]
    verification: list[dict]
    report: str
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps({
            "contract_path": self.contract_path,
            "vulnerabilities": self.vulnerabilities,
            "patches": self.patches,
            "verification": self.verification,
            "report": self.report,
        }, indent=2)
    
    def to_console(self) -> str:
        """Format for console output"""
        from rich.table import Table
        from rich.console import Console
        
        console = Console()
        
        table = Table(title="Audit Results")
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")
        
        table.add_row("Contract", self.contract_path)
        table.add_row("Vulnerabilities Found", str(len(self.vulnerabilities)))
        table.add_row("Patches Generated", str(len(self.patches)))
        table.add_row("Verified Fixes", str(len([v for v in self.verification if v.get("passed")])))
        
        return table


class AgentOrchestrator:
    """
    Orchestrates the five specialized agents for smart contract audit.
    
    Architecture:
    1. Auditor: Analyzes code, identifies vulnerabilities
    2. Architect: Designs repair strategies
    3. Code Generator: Generates patches
    4. Refiner: Iteratively improves code
    5. Validator: Verifies fixes
    """

    # Severity weight map for risk scoring (Todo 5)
    _SEV_WEIGHT = {
        "critical": 1.0, "high": 0.8, "medium": 0.5,
        "low": 0.2, "informational": 0.1,
    }
    
    def __init__(self, context_repo_path: str = ".context-repo"):
        self.tools = ToolKit()
        self.knowledge = KnowledgeBase(context_repo_path=context_repo_path)
        
        # Initialize agents
        self.auditor = AuditorAgent(self.tools, self.knowledge)
        self.architect = ArchitectAgent(self.tools, self.knowledge)
        self.code_generator = CodeGeneratorAgent(self.tools, self.knowledge)
        self.refiner = RefinerAgent(self.tools, self.knowledge)
        self.validator = ValidatorAgent(self.tools, self.knowledge)
    
    async def initialize(self):
        """Initialize the orchestrator and knowledge base"""
        logger.info("Initializing Agent Orchestrator")
        await self.knowledge.initialize()
    
    # ------------------------------------------------------------------
    # Step order — used by the resume logic to decide what to skip.
    # ------------------------------------------------------------------
    _STEP_ORDER = ("detect", "patch", "verify")

    def _step_is_done(self, checkpoint: dict | None, step: str) -> bool:
        """Return True if *step* was already completed in *checkpoint*."""
        if not checkpoint:
            return False
        last = checkpoint.get("last_completed_step")
        if not last:
            return False
        try:
            return self._STEP_ORDER.index(step) <= self._STEP_ORDER.index(last)
        except ValueError:
            return False

    async def audit(
        self,
        contract_path: str,
        mode: str = "all",
        max_patches: int = 2,
        resume: bool = False,
    ) -> AuditResult:
        """
        Run full audit on a smart contract.

        Args:
            contract_path: Path to the smart contract file
            mode: Audit mode (detect, patch, exploit, all)
            max_patches: cap on how many vulnerabilities to patch, highest
                severity first. Negative (e.g. -1) means patch all.
            resume: If True, attempt to resume from the last checkpoint.

        Returns:
            AuditResult with vulnerabilities, patches, and verification
        """
        logger.info(f"Starting audit of {contract_path} in {mode} mode (resume={resume})")

        checkpoint = load_checkpoint(contract_path) if resume else None
        if checkpoint and resume:
            logger.info(
                "Resuming from step '%s'",
                checkpoint.get("last_completed_step", "(none)"),
            )

        # Load contract
        contract_code = Path(contract_path).read_text()

        # ── Phase 1: Detect ──────────────────────────────────────────
        if self._step_is_done(checkpoint, "detect") and resume:
            logger.info("Resuming: detect already completed, loading from checkpoint")
            vulnerabilities = checkpoint["steps"]["detect"]["vulnerabilities"]
        else:
            try:
                vulnerabilities = await self.detect(contract_path)
                save_checkpoint(contract_path, mode, "detect", {
                    "vulnerabilities_count": len(vulnerabilities),
                    "vulnerabilities": vulnerabilities,
                })
            except Exception as e:
                save_checkpoint(contract_path, mode, "detect_failed", {"error": str(e)})
                raise

        if mode == "detect":
            clear_checkpoint(contract_path)
            return AuditResult(
                contract_path=contract_path,
                vulnerabilities=vulnerabilities,
                patches=[],
                verification=[],
                report="Detection complete",
            )

        # ── Phase 2: Patch ───────────────────────────────────────────
        if self._step_is_done(checkpoint, "patch") and resume:
            logger.info("Resuming: patch already completed, loading from checkpoint")
            patches = checkpoint["steps"]["patch"]["patches"]
        else:
            try:
                patches = await self._generate_patches(
                    contract_code, vulnerabilities, max_patches=max_patches
                )
                save_checkpoint(contract_path, mode, "patch", {
                    "patches_count": len(patches),
                    "patches": patches,
                })
            except Exception as e:
                save_checkpoint(contract_path, mode, "patch_failed", {"error": str(e)})
                raise

        if mode == "patch":
            clear_checkpoint(contract_path)
            return AuditResult(
                contract_path=contract_path,
                vulnerabilities=vulnerabilities,
                patches=patches,
                verification=[],
                report="Patching complete",
            )

        # ── Phase 3: Verify ──────────────────────────────────────────
        if self._step_is_done(checkpoint, "verify") and resume:
            logger.info("Resuming: verify already completed, loading from checkpoint")
            verification = checkpoint["steps"]["verify"]["verification"]
        else:
            try:
                verification = await self._verify_patches(contract_code, patches)
                save_checkpoint(contract_path, mode, "verify", {
                    "verification_count": len(verification),
                    "verification": verification,
                })
            except Exception as e:
                save_checkpoint(contract_path, mode, "verify_failed", {"error": str(e)})
                raise

        # All steps succeeded — clean up checkpoint
        clear_checkpoint(contract_path)

        return AuditResult(
            contract_path=contract_path,
            vulnerabilities=vulnerabilities,
            patches=patches,
            verification=verification,
            report=self._generate_report(vulnerabilities, patches, verification),
        )
    
    async def detect(self, contract_path: str, use_multi_expert: bool = False, strategy: str = "all") -> list[dict]:
        """
        Detect vulnerabilities in a smart contract.

        Uses Auditor agent with multiple detection strategies:
        1. Static analysis (Slither)
        2. LLM-based analysis (single or multi-expert)
        3. RAG knowledge retrieval

        Args:
            contract_path: Path to the smart contract file
            use_multi_expert: Use multi-expert analysis from forefy/.context
            strategy: Detection strategy — "ba" (broad analysis), "ta"
                (targeted analysis), or "all" (both). See LLM-SmartAudit §3.2.
        """
        logger.info(f"Detecting vulnerabilities in {contract_path}")
        return await self.auditor.detect(contract_path, use_multi_expert=use_multi_expert, strategy=strategy)
    
    async def patch(self, contract_path: str, vulnerability_id: str) -> dict:
        """
        Generate a patch for a specific vulnerability.
        
        Uses Architect + Code Generator + Refiner agents.
        """
        logger.info(f"Generating patch for {vulnerability_id}")
        
        # Load contract
        contract_code = Path(contract_path).read_text()
        
        # Get vulnerability details
        vulnerability = await self.auditor.get_vulnerability(contract_path, vulnerability_id)
        
        # Design repair strategy
        strategy = await self.architect.design_repair(contract_code, vulnerability)
        
        # Generate code
        patch = await self.code_generator.generate(contract_code, vulnerability, strategy)
        
        # Refine code
        refined_patch = await self.refiner.refine(contract_code, patch)
        
        return {
            "vulnerability_id": vulnerability_id,
            "strategy": strategy,
            "patch": refined_patch,
        }
    
    async def exploit(self, contract_address: str, exploit_code_path: str) -> dict:
        """
        Execute an exploit against a contract.
        
        Uses Validator agent with Concrete Execution tool.
        """
        logger.info(f"Executing exploit on {contract_address}")
        
        exploit_code = Path(exploit_code_path).read_text()
        
        return await self.validator.execute_exploit(contract_address, exploit_code)
    
    async def _generate_patches(self, contract_code: str, vulnerabilities: list[dict], max_patches: int = 2) -> list[dict]:
        """Generate patches, highest-severity first.

        Args:
            max_patches: cap on how many vulnerabilities to patch (highest
                severity first). Negative (e.g. -1) means no cap (patch all).
        """
        patches = []

        # Severity ordering, case-insensitive. Slither emits 'High'/'Informational',
        # MiMo emits 'high', BA/TA emit 'critical'. Lower rank = more severe.
        severity_rank = {
            "critical": 0, "high": 1, "medium": 2,
            "low": 3, "informational": 4, "info": 4,
        }

        def rank(vuln: dict) -> int:
            return severity_rank.get(str(vuln.get("severity", "")).strip().lower(), 5)

        # Highest-severity first; sorted() is stable so same-severity keeps detection order.
        ordered = sorted(vulnerabilities, key=rank)
        if max_patches >= 0:
            ordered = ordered[:max_patches]

        for vuln in ordered:
            # Design repair strategy
            strategy = await self.architect.design_repair(contract_code, vuln)
            
            # Generate code
            patch = await self.code_generator.generate(contract_code, vuln, strategy)
            
            # Refine code
            refined_patch = await self.refiner.refine(contract_code, patch)
            
            patches.append({
                "vulnerability": vuln,
                "strategy": strategy,
                "patch": refined_patch,
            })
        
        return patches
    
    async def _verify_patches(self, contract_code: str, patches: list[dict]) -> list[dict]:
        """Verify all patches"""
        results = []
        
        for patch_info in patches:
            # Verify the patch
            verification = await self.validator.verify(
                contract_code,
                patch_info["patch"],
                patch_info["vulnerability"]
            )
            
            results.append({
                "vulnerability": patch_info["vulnerability"],
                "passed": verification["passed"],
                "details": verification["details"],
            })
        
        return results
    
    def _generate_report(self, vulnerabilities: list[dict], patches: list[dict], verification: list[dict]) -> str:
        """
        Generate audit report using forefy/.context finding format.
        
        Format:
        ## [C/H/M/L]-[Number] [Impact] via [Weakness] in [Feature]
        """
        report_lines = []
        report_lines.append("# Smart Contract Security Audit Report")
        report_lines.append("")
        report_lines.append("## Summary")
        report_lines.append(f"- **Vulnerabilities Found**: {len(vulnerabilities)}")
        report_lines.append(f"- **Patches Generated**: {len(patches)}")
        report_lines.append(f"- **Verified Fixes**: {len([v for v in verification if v.get('passed')])}")
        report_lines.append("")
        
        # Severity mapping
        severity_map = {"critical": "C", "high": "H", "medium": "M", "low": "L"}
        
        # Calculate risk_score and sort findings by risk descending
        for vuln in vulnerabilities:
            sev = (vuln.get("severity") or "medium").lower()
            conf = float(vuln.get("confidence", 0.0))
            vuln["risk_score"] = round(self._SEV_WEIGHT.get(sev, 0.5) * conf, 3)
        vulnerabilities = sorted(vulnerabilities, key=lambda v: v.get("risk_score", 0), reverse=True)
        
        # Generate findings
        report_lines.append("## Findings")
        report_lines.append("")
        
        # Summary table (risk-ranked)
        report_lines.append("| # | Severity | Type | Location | Confidence | Risk | Verified |")
        report_lines.append("|---|----------|------|----------|-----------|------|----------|")
        for i, vuln in enumerate(vulnerabilities, 1):
            sev = (vuln.get("severity") or "medium").lower()
            conf = float(vuln.get("confidence", 0.0))
            risk = vuln.get("risk_score", 0.0)
            verified = "✅" if vuln.get("verified", True) else "⚠️ FP?"
            report_lines.append(
                f"| {i} | {sev.capitalize()} | {vuln.get('type','?')} | "
                f"{vuln.get('location','?')} | {conf:.2f} | {risk:.2f} | {verified} |"
            )
        report_lines.append("")
        
        for i, vuln in enumerate(vulnerabilities, 1):
            severity = vuln.get("severity", "medium").lower()
            severity_code = severity_map.get(severity, "M")
            vuln_type = vuln.get("type", "unknown")
            location = vuln.get("location", "unknown")
            
            report_lines.append(f"### {severity_code}-{i:03d} {vuln_type} in {location}")
            report_lines.append("")
            report_lines.append(f"**Severity**: {severity.capitalize()}")
            report_lines.append(f"**Source**: {vuln.get('source', 'unknown')}")
            report_lines.append(f"**Description**: {vuln.get('description', 'No description')}")
            report_lines.append("")
            
            # Add recommendation if available
            if vuln.get("recommendation"):
                report_lines.append(f"**Recommendation**: {vuln['recommendation']}")
                report_lines.append("")
            
            # Attach matching patch (by vulnerability id or type)
            vuln_id = vuln.get("id", "")
            vuln_type_lower = vuln_type.lower()
            matched_patch = None
            for p in patches:
                p_vuln = p.get("vulnerability", {})
                if (p_vuln.get("id", "") == vuln_id and vuln_id) or \
                   (p_vuln.get("type", "").lower() == vuln_type_lower):
                    matched_patch = p
                    break
            
            if matched_patch:
                strategy = matched_patch.get("strategy", "N/A")
                patch_code = matched_patch.get("patch", "")
                # Truncate patch to 500 chars for readability
                if len(patch_code) > 500:
                    patch_code = patch_code[:500] + "\n... (truncated)"
                report_lines.append("**Patch**:")
                report_lines.append(f"- Strategy: {strategy}")
                report_lines.append(f"```solidity\n{patch_code}\n```")
                report_lines.append("")
            
            # Attach matching verification result
            matched_verify = None
            for v in verification:
                v_vuln = v.get("vulnerability", {})
                if (v_vuln.get("id", "") == vuln_id and vuln_id) or \
                   (v_vuln.get("type", "").lower() == vuln_type_lower):
                    matched_verify = v
                    break
            
            if matched_verify:
                passed = matched_verify.get("passed", False)
                status_icon = "✅" if passed else "❌"
                details = matched_verify.get("details", "N/A")
                if len(details) > 200:
                    details = details[:200] + "..."
                report_lines.append(f"**Verification**: {status_icon} {'Passed' if passed else 'Failed'}")
                report_lines.append(f"- Details: {details}")
                report_lines.append("")
        
        # Remediation Summary
        fixed = len([v for v in verification if v.get('passed')])
        unfixed = len(vulnerabilities) - fixed
        report_lines.append("## Remediation Summary")
        report_lines.append(f"")
        report_lines.append(f"- **Fixed**: {fixed}")
        report_lines.append(f"- **Unfixed / Unverified**: {unfixed}")
        report_lines.append("")
        
        return "\n".join(report_lines)
