"""
Slither Tool
Wrapper for Slither static analysis
Reference: crytic/slither (6,273 stars)
"""

import subprocess
import json
import tempfile
import re
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SlitherTool:
    """
    Slither Tool: Wrapper for Slither static analysis.
    
    Features:
    1. Run Slither on contract files
    2. Run Slither on code strings
    3. Parse and format results
    
    Reference: crytic/slither
    """
    
    def __init__(self):
        pass
    
    def analyze(self, contract_path: str) -> list[dict]:
        """
        Run Slither on a contract file.
        
        Args:
            contract_path: Path to contract file
            
        Returns:
            List of findings
        """
        logger.info(f"Running Slither on {contract_path}")
        
        try:
            # Slither refuses to overwrite an existing --json file, so we need a
            # path that does NOT exist yet. Create a temp dir and point at a file
            # inside it (the file itself must not be pre-created).
            tmp_dir = tempfile.mkdtemp(prefix="slither_")
            json_path = str(Path(tmp_dir) / "slither.json")
            
            # Run Slither with JSON output to file
            result = subprocess.run(
                ["slither", contract_path, "--json", json_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            # Read JSON output
            try:
                json_path_obj = Path(json_path)
                if json_path_obj.exists():
                    data = json.loads(json_path_obj.read_text())
                    
                    # Extract findings
                    findings = []
                    for detector in data.get("results", {}).get("detectors", []):
                        findings.append({
                            "check": detector.get("check", ""),
                            "impact": detector.get("impact", ""),
                            "confidence": detector.get("confidence", ""),
                            "location": self._format_location(detector.get("elements", [])),
                            "description": detector.get("description", ""),
                        })
                    
                    logger.info(f"Slither found {len(findings)} vulnerabilities")
                    return findings
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse Slither JSON: {e}")
            finally:
                # Clean up temp file + dir
                Path(json_path).unlink(missing_ok=True)
                try:
                    Path(tmp_dir).rmdir()
                except OSError:
                    pass
            
            # Fallback: parse text output
            return self._parse_text_output(result.stdout + result.stderr)
            
        except subprocess.TimeoutExpired:
            logger.error("Slither analysis timed out")
            return []
        except FileNotFoundError:
            logger.error("Slither not installed. Install: pip install slither-analyzer")
            return []
        except Exception as e:
            logger.error(f"Slither analysis failed: {e}")
            return []
    
    def analyze_code(self, code: str) -> list[dict]:
        """
        Run Slither on code string.
        
        Args:
            code: Solidity code
            
        Returns:
            List of findings
        """
        logger.info("Running Slither on code")
        
        # Write code to temp file
        with tempfile.NamedTemporaryFile(suffix=".sol", delete=False, mode='w') as f:
            f.write(code)
            temp_path = f.name
        
        try:
            return self.analyze(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def _format_location(self, elements: list) -> str:
        """Format location from Slither elements"""
        if not elements:
            return "unknown"
        
        for elem in elements:
            source = elem.get("source_mapping", {})
            filename = source.get("filename_relative", "")
            lines = source.get("lines", [])
            
            if filename and lines:
                return f"{filename}:{lines[0]}"
        
        return "unknown"
    
    def _parse_text_output(self, output: str) -> list[dict]:
        """Parse Slither text output as fallback"""
        findings = []
        
        # Pattern: INFO:Detectors:\nDetector: <check>\n<description>
        detector_pattern = r'Detector:\s*(\S+)\s*\n(.*?)(?=Detector:|$)'
        matches = re.findall(detector_pattern, output, re.DOTALL)
        
        for check, description in matches:
            # Extract impact from description
            impact = "medium"
            if "high" in description.lower():
                impact = "high"
            elif "low" in description.lower():
                impact = "low"
            elif "informational" in description.lower():
                impact = "informational"
            
            # Extract location
            location_match = re.search(r'(\S+\.sol)#(\d+)', description)
            location = f"{location_match.group(1)}:{location_match.group(2)}" if location_match else "unknown"
            
            findings.append({
                "check": check,
                "impact": impact,
                "confidence": "high",
                "location": location,
                "description": description.strip()[:500],
            })
        
        logger.info(f"Slither found {len(findings)} vulnerabilities")
        return findings
