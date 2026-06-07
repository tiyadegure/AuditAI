"""
Aderyn Tool
Wrapper for Aderyn static analysis (Cyfrin/aderyn)
Interface aligned with SlitherTool — returns list[dict] with five standard fields.
"""

import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AderynTool:
    """
    Aderyn Tool: Wrapper for Aderyn static analysis.

    Features:
    1. Run Aderyn on project directories
    2. Run Aderyn on code strings (creates temp project structure)
    3. Parse JSON output and map to unified five-field format

    Reference: Cyfrin/aderyn (0.6.8+)

    Aderyn analyzes *project directories*, not individual .sol files.
    analyze_code() creates a temporary Foundry project structure internally.
    """

    # Severity mapping: aderyn issue group → unified impact label
    _SEVERITY_MAP = {
        "high_issues": "High",
        "low_issues": "Low",
        # Aderyn may add medium/critical groups in future versions
        "medium_issues": "Medium",
        "critical_issues": "Critical",
    }

    def __init__(self):
        pass

    def analyze(self, project_path: str) -> list[dict]:
        """
        Run Aderyn on a project directory.

        Args:
            project_path: Path to project directory (or a .sol file inside a project)

        Returns:
            List of findings with unified five-field format
        """
        logger.info(f"Running Aderyn on {project_path}")

        target = Path(project_path)
        # If a single .sol file is passed, use its parent as project root
        if target.is_file() and target.suffix == ".sol":
            project_dir = str(target.parent)
        elif target.is_dir():
            project_dir = str(target)
        else:
            project_dir = str(target)

        tmp_dir = tempfile.mkdtemp(prefix="aderyn_")
        json_path = str(Path(tmp_dir) / "report.json")

        try:
            result = subprocess.run(
                ["aderyn", project_dir, "--output", json_path],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Even on non-zero exit, aderyn may still produce output — try to parse
            try:
                json_path_obj = Path(json_path)
                if json_path_obj.exists() and json_path_obj.stat().st_size > 0:
                    data = json.loads(json_path_obj.read_text())
                    findings = self._parse_issues(data)
                    logger.info(f"Aderyn found {len(findings)} findings")
                    return findings
                else:
                    logger.warning(f"Aderyn produced no JSON output (exit {result.returncode})")
                    if result.stderr:
                        logger.debug(f"Aderyn stderr: {result.stderr[:500]}")
                    return []
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse Aderyn JSON: {e}")
                return []

        except FileNotFoundError:
            logger.warning("Aderyn not installed. Install: cargo install aderyn or download release binary")
            return []
        except subprocess.TimeoutExpired:
            logger.warning("Aderyn analysis timed out (120s)")
            return []
        except Exception as e:
            logger.warning(f"Aderyn analysis failed: {e}")
            return []
        finally:
            # Clean up temp output directory
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def analyze_code(self, code: str) -> list[dict]:
        """
        Run Aderyn on a code string.

        Creates a temporary Foundry project structure (aderyn requires a project
        directory, not a single .sol file), runs aderyn, and cleans up.

        Args:
            code: Solidity source code

        Returns:
            List of findings with unified five-field format
        """
        logger.info("Running Aderyn on code string")

        tmp_dir = tempfile.mkdtemp(prefix="aderyn_code_")
        try:
            # Create minimal Foundry project structure
            src_dir = Path(tmp_dir) / "src"
            src_dir.mkdir(parents=True)
            sol_file = src_dir / "Contract.sol"
            sol_file.write_text(code)

            # Minimal foundry.toml
            foundry_toml = Path(tmp_dir) / "foundry.toml"
            foundry_toml.write_text('[profile.default]\nsrc = "src"\n')

            return self.analyze(tmp_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _parse_issues(self, data: dict) -> list[dict]:
        """
        Parse Aderyn JSON output into unified five-field findings.

        Aderyn JSON schema (v0.6.8):
        {
            "high_issues": {"issues": [{title, description, detector_name, instances: [{contract_path, line_no, ...}]}]},
            "low_issues":  {"issues": [{title, description, detector_name, instances: [{contract_path, line_no, ...}]}]},
            ...
        }

        Maps to unified format:
        {check, impact, confidence, location, description}
        """
        findings = []

        for sev_key, impact in self._SEVERITY_MAP.items():
            block = data.get(sev_key) or {}
            issues = block.get("issues") or []
            for issue in issues:
                instances = issue.get("instances") or []
                if not instances:
                    # Issue with no instances — still record it at "unknown" location
                    findings.append({
                        "check": issue.get("detector_name", "aderyn-issue"),
                        "impact": impact,
                        "confidence": "medium",
                        "location": "unknown",
                        "description": self._build_description(issue),
                    })
                    continue

                # One finding per instance (aligns with Slither's per-element granularity)
                for inst in instances:
                    contract_path = inst.get("contract_path", "")
                    line_no = inst.get("line_no", "")
                    location = f"{contract_path}:{line_no}" if contract_path else "unknown"

                    desc = self._build_description(issue)
                    # Append hint if present (e.g., "State is changed at: ...")
                    hint = inst.get("hint")
                    if hint:
                        desc = f"{desc} ({hint})"

                    findings.append({
                        "check": issue.get("detector_name", "aderyn-issue"),
                        "impact": impact,
                        "confidence": "medium",
                        "location": location,
                        "description": desc,
                    })

        return findings

    def _build_description(self, issue: dict) -> str:
        """Build description from issue title + description fields."""
        title = issue.get("title", "")
        desc = issue.get("description", "")
        if title and desc:
            return f"{title}: {desc}"
        return title or desc or "No description"
