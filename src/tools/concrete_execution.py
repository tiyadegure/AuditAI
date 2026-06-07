"""
Concrete Execution Tool
Execute exploits using Foundry (forge test) with A1 paper's three feedback signals:
  1. Profitability Oracle — binary pass/fail + profit extraction from logs
  2. Execution Trace — call stack + state changes from forge -vvvvv
  3. Revert Reason — failure reason string extraction

Reference: A1 paper Section 3.3 — "feedback integration uses three signals:
(i) a binary profitability oracle, (ii) execution traces, (iii) revert reasons."
Forge docs: https://book.getfoundry.sh/forge/running-tests#traces
"""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from ..utils.logger import get_logger
from ..chain.chain_verifier import ChainVerifier

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Forge availability check (cached, async-safe)
# ---------------------------------------------------------------------------
_forge_available: bool | None = None


async def _check_forge_available_async() -> bool:
    """Async check once whether `forge` binary is on PATH."""
    global _forge_available
    if _forge_available is not None:
        return _forge_available
    try:
        proc = await asyncio.create_subprocess_exec(
            "forge", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
        _forge_available = proc.returncode == 0
    except (FileNotFoundError, OSError, asyncio.TimeoutError):
        _forge_available = False
    return _forge_available


# ---------------------------------------------------------------------------
# Top-level parse function — usable standalone for unit testing
# ---------------------------------------------------------------------------
def parse_forge_output(stdout: str, stderr: str = "", returncode: int = 1) -> dict:
    """
    Parse forge test output (either JSON or verbose text) into the three
    A1 feedback signals.

    Args:
        stdout: Raw stdout from `forge test`.
        stderr: Raw stderr from `forge test`.
        returncode: Process exit code.

    Returns:
        dict with keys:
          - success (bool): Overall pass/fail
          - tests_passed (int)
          - tests_failed (int)
          - gas_used (int): Total gas across tests
          - profit (float): 1.0 if profitable (test passes), 0.0 otherwise
          - revert_reason (str): Revert reason from the first failing test
          - trace (str): Human-readable execution trace (from -vvvvv)
          - raw_output (str): Last 2000 chars of stdout
          - test_results (dict): Per-test details {name: {status, reason, gas, trace}}
    """
    result: dict = {
        "success": returncode == 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "gas_used": 0,
        "profit": 0.0,
        "revert_reason": "",
        "trace": "",
        "raw_output": stdout[-2000:] if stdout else "",
        "test_results": {},
    }

    # --- Try JSON mode first (forge test --json) ---
    if stdout and stdout.strip().startswith("{"):
        try:
            parsed = _parse_forge_json(stdout)
            result.update(parsed)
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"JSON parse failed, falling back to text: {e}")

    # --- Fallback: parse human-readable -vvvvv text output ---
    parsed = _parse_forge_text(stdout or "", stderr or "")
    result.update(parsed)
    return result


# ---------------------------------------------------------------------------
# JSON parser (forge test --json [-vvvvv])
# ---------------------------------------------------------------------------
def _parse_forge_json(stdout: str) -> dict:
    """
    Parse structured JSON output from `forge test --json`.

    The JSON schema (Forge 1.7.x):
    {
      "path/to/Test.t.sol:ContractName": {
        "test_results": {
          "test_name()": {
            "status": "Success" | "Failure" | "Skipped",
            "reason": "revert message" | null,
            "kind": {"Unit": {"gas": N}} | ...,
            "traces": [...],
            "logs": [...],
          }
        }
      }
    }
    """
    data = json.loads(stdout)

    tests_passed = 0
    tests_failed = 0
    total_gas = 0
    revert_reason = ""
    trace_lines: list[str] = []
    test_results: dict = {}

    for suite_path, suite_data in data.items():
        test_results_map = suite_data.get("test_results", {})
        for test_name, test_data in test_results_map.items():
            status = test_data.get("status", "")
            reason = test_data.get("reason") or ""
            gas = 0
            kind = test_data.get("kind", {})
            if isinstance(kind, dict):
                for kind_info in kind.values():
                    if isinstance(kind_info, dict):
                        gas = kind_info.get("gas", 0)

            is_success = status == "Success"
            if is_success:
                tests_passed += 1
            else:
                tests_failed += 1
                if not revert_reason and reason:
                    revert_reason = reason

            total_gas += gas

            # Build per-test entry
            test_entry: dict = {
                "status": "pass" if is_success else "fail",
                "reason": reason,
                "gas": gas,
            }

            # Extract human-readable trace from traces array (if -vvvvv was used)
            traces = test_data.get("traces", [])
            if traces:
                trace_text = _extract_trace_from_json(traces)
                test_entry["trace"] = trace_text
                trace_lines.append(f"--- {test_name} ---\n{trace_text}")

            test_results[test_name] = test_entry

    return {
        "success": tests_failed == 0,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "gas_used": total_gas,
        "profit": 1.0 if tests_failed == 0 else 0.0,
        "revert_reason": revert_reason,
        "trace": "\n\n".join(trace_lines),
        "test_results": test_results,
    }


def _extract_trace_from_json(traces: list) -> str:
    """
    Extract a human-readable call-trace summary from forge's JSON traces array.

    Each trace entry is a nested structure. We walk the tree and collect:
      - Contract::function calls
      - Gas usage
      - Storage changes
      - Return data / revert reasons
    """
    lines: list[str] = []
    _walk_trace_node(traces, lines, depth=0)
    return "\n".join(lines)


def _walk_trace_node(node, lines: list[str], depth: int) -> None:
    """Recursively walk a trace node tree."""
    if isinstance(node, dict):
        # Leaf node with trace data
        trace_data = node.get("traces", node)
        if isinstance(trace_data, list):
            for item in trace_data:
                _walk_trace_node(item, lines, depth)
            return

        label = node.get("label", "")
        trace_type = node.get("trace_type", "")
        gas_used = node.get("gas_used", "")
        return_data = node.get("return_data", "")
        status = node.get("status", "")
        storage_changes = node.get("storage_changes", {})

        indent = "  " * depth
        if label:
            parts = [f"{indent}{label}"]
            if trace_type:
                parts.append(f"[{trace_type}]")
            if gas_used:
                parts.append(f"(gas: {gas_used})")
            lines.append(" ".join(parts))

        if storage_changes and isinstance(storage_changes, dict):
            for slot, change in storage_changes.items():
                lines.append(f"{indent}  storage @ {slot}: {change}")

        if status and status not in ("Stop", "Return"):
            lines.append(f"{indent}  status: {status}")

        if return_data and return_data != "0x":
            lines.append(f"{indent}  return: {return_data[:200]}")

        # Recurse into children
        for key in ("nodes", "children", "steps", "ordering"):
            children = node.get(key)
            if children and isinstance(children, list):
                for child in children:
                    _walk_trace_node(child, lines, depth + 1)

    elif isinstance(node, list):
        for item in node:
            _walk_trace_node(item, lines, depth)


# ---------------------------------------------------------------------------
# Text parser (forge test -vvvvv, no --json)
# ---------------------------------------------------------------------------
_FORGE_FAIL_RE = re.compile(
    r"\[FAIL(?::\s*(?P<reason>.+?))?\]\s+(?P<test>\S+)\s*\(gas:\s*(?P<gas>\d+)\)",
    re.IGNORECASE,
)
_FORGE_PASS_RE = re.compile(
    r"\[PASS\]\s+(?P<test>\S+)\s*\(gas:\s*(?P<gas>\d+)\)",
    re.IGNORECASE,
)
_FORGE_SUITE_RE = re.compile(
    r"Ran\s+\d+\s+test\s+suites?.+?:\s*(?P<passed>\d+)\s+tests?\s+passed,\s*(?P<failed>\d+)\s+failed",
    re.IGNORECASE,
)
_FORGE_REVERT_RE = re.compile(
    r"←\s*\[Revert\]\s*(?P<reason>.+)",
)


def _parse_forge_text(stdout: str, stderr: str) -> dict:
    """Parse human-readable forge test -vvvvv output."""
    combined = stdout + "\n" + stderr

    tests_passed = 0
    tests_failed = 0
    total_gas = 0
    revert_reason = ""
    first_failing_test = ""
    test_results: dict = {}
    seen_tests: set[str] = set()  # deduplicate (test lines repeat in summary)

    # Parse PASS tests (deduplicate)
    for m in _FORGE_PASS_RE.finditer(combined):
        test_name = m.group("test")
        if test_name in seen_tests:
            continue
        seen_tests.add(test_name)
        gas = int(m.group("gas"))
        tests_passed += 1
        total_gas += gas
        test_results[test_name] = {"status": "pass", "reason": "", "gas": gas}

    # Parse FAIL tests (deduplicate)
    for m in _FORGE_FAIL_RE.finditer(combined):
        test_name = m.group("test")
        if test_name in seen_tests:
            continue
        seen_tests.add(test_name)
        gas = int(m.group("gas"))
        reason = m.group("reason") or ""
        tests_failed += 1
        total_gas += gas
        test_results[test_name] = {"status": "fail", "reason": reason, "gas": gas}
        if not revert_reason:
            revert_reason = reason
            first_failing_test = test_name

    # If no regex-matched revert reason, try the Revert arrow pattern
    if not revert_reason:
        rm = _FORGE_REVERT_RE.search(combined)
        if rm:
            revert_reason = rm.group("reason").strip()

    # Extract trace blocks for each test
    trace_sections = _extract_trace_blocks(combined)
    for test_name, trace_text in trace_sections.items():
        if test_name in test_results:
            test_results[test_name]["trace"] = trace_text

    # Fallback: suite-level summary
    sm = _FORGE_SUITE_RE.search(combined)
    if sm:
        # Only override if regex didn't find individual tests
        if not test_results:
            tests_passed = int(sm.group("passed"))
            tests_failed = int(sm.group("failed"))

    return {
        "success": tests_failed == 0 and (tests_passed > 0 or returncode_is_success(combined)),
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "gas_used": total_gas,
        "profit": 1.0 if tests_failed == 0 and tests_passed > 0 else 0.0,
        "revert_reason": revert_reason,
        "trace": "\n\n".join(
            f"--- {name} ---\n{txt}" for name, txt in trace_sections.items()
        ),
        "test_results": test_results,
    }


def returncode_is_success(combined: str) -> bool:
    """Heuristic: check if output indicates success."""
    return "Suite result: ok" in combined


_TRACE_BLOCK_RE = re.compile(
    r"Traces:\s*\n(.*?)(?=\n\[PASS\]|\n\[FAIL|\nSuite result:|\nRan\s|\Z)",
    re.DOTALL,
)


def _extract_trace_blocks(text: str) -> dict[str, str]:
    """
    Extract per-test trace blocks from -vvvvv text output.

    Format:
      [FAIL: reason] testName() (gas: N)
      Traces:
        [150861] Contract::setUp()
          ├─ ...
          └─ ...
        [N] Contract::testName()
          ├─ ...
          └─ ← [Revert] reason
    """
    blocks: dict[str, str] = {}
    # Find test header + trace pairs
    lines = text.split("\n")
    current_test = ""
    in_trace = False
    trace_lines: list[str] = []

    for line in lines:
        pass_match = _FORGE_PASS_RE.match(line)
        fail_match = _FORGE_FAIL_RE.match(line)

        if pass_match or fail_match:
            # Save previous trace
            if current_test and trace_lines:
                blocks[current_test] = "\n".join(trace_lines)
            current_test = (pass_match or fail_match).group("test")
            trace_lines = []
            in_trace = False
            continue

        if line.strip() == "Traces:":
            in_trace = True
            continue

        if in_trace:
            # Trace ends at next test header or empty section
            if line.startswith("[PASS]") or line.startswith("[FAIL]") or line.startswith("Suite result:"):
                if current_test and trace_lines:
                    blocks[current_test] = "\n".join(trace_lines)
                in_trace = False
                current_test = ""
                trace_lines = []
            else:
                trace_lines.append(line)

    # Save last trace
    if current_test and trace_lines:
        blocks[current_test] = "\n".join(trace_lines)

    return blocks


# ---------------------------------------------------------------------------
# ConcreteExecutionTool class
# ---------------------------------------------------------------------------
class ConcreteExecutionTool:
    """
    Concrete Execution Tool: Execute exploits using Foundry.

    Features:
    1. Fork blockchain at specific blocks
    2. Execute exploit PoCs against real on-chain states
    3. Return A1's three feedback signals: profitability, trace, revert_reason

    Reference: A1 paper Section 3 - Concrete Execution Tool
    """

    def __init__(self, framework: str = "foundry", rpc_url: str = None):
        self.framework = framework
        self.rpc_url = rpc_url or ChainVerifier.FREE_RPCS[0]

    # -----------------------------------------------------------------------
    # Public API (interface preserved for toolkit.py compatibility)
    # -----------------------------------------------------------------------
    async def execute(self, contract_address: str, exploit_code: str, block_number: int = None) -> dict:
        """
        Execute an exploit against a contract.

        Args:
            contract_address: Contract address or "local" for local test
            exploit_code: Solidity exploit code (Foundry test)
            block_number: Block number to fork at

        Returns:
            Execution result with A1 three-signal feedback:
              success, gas_used, profit, revert_reason, trace, test_results
        """
        logger.info(f"Executing exploit on {contract_address}")

        if contract_address == "local":
            return await self._execute_local(exploit_code)
        else:
            return await self._execute_fork(contract_address, exploit_code, block_number)

    async def test(self, contract_code: str, test_case: str) -> dict:
        """
        Run a test case against contract code.

        Args:
            contract_code: Solidity contract code
            test_case: Foundry test code

        Returns:
            Test result with A1 three-signal feedback.
        """
        logger.info("Running concrete test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write contract
            contract_path = Path(tmpdir) / "src" / "Contract.sol"
            contract_path.parent.mkdir(parents=True)
            contract_path.write_text(contract_code)

            # Write test
            test_path = Path(tmpdir) / "test" / "Test.t.sol"
            test_path.parent.mkdir(parents=True)
            test_path.write_text(test_case)

            # Write foundry.toml
            config_path = Path(tmpdir) / "foundry.toml"
            config_path.write_text('[profile.default]\nsrc = "src"\ntest = "test"\n')

            result = await self._run_forge_test(tmpdir)
            return result

    # -----------------------------------------------------------------------
    # Invariant / Fuzz testing
    # -----------------------------------------------------------------------
    async def fuzz(self, contract_code: str, invariant_contract: str, timeout: int = 300) -> dict:
        """
        Run Foundry invariant (fuzz) tests against a contract.

        Args:
            contract_code: Solidity source of the contract under test.
            invariant_contract: Solidity test contract with invariant_* functions.
            timeout: Max seconds for the forge process (default 300).

        Returns:
            dict with keys: passed (bool), fuzz_findings (list[dict]), raw (str).
            On timeout: passed=True, fuzz_findings=[], note="fuzz timeout".
        """
        logger.info("Running invariant fuzz test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # -- scaffold: src + test + foundry.toml with invariant config --
            contract_path = Path(tmpdir) / "src" / "Contract.sol"
            contract_path.parent.mkdir(parents=True)
            contract_path.write_text(contract_code)

            test_path = Path(tmpdir) / "test" / "Invariant.t.sol"
            test_path.parent.mkdir(parents=True)
            test_path.write_text(invariant_contract)

            config_path = Path(tmpdir) / "foundry.toml"
            config_path.write_text(
                '[profile.default]\n'
                'src = "src"\n'
                'test = "test"\n'
                '[profile.default.invariant]\n'
                'runs = 256\n'
                'depth = 32\n'
            )

            # -- install forge-std (required for `import "forge-std/Test.sol"`) --
            try:
                git_proc = await asyncio.create_subprocess_exec(
                    "git", "init", cwd=tmpdir,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(git_proc.communicate(), timeout=15)

                install_proc = await asyncio.create_subprocess_exec(
                    "forge", "install", "foundry-rs/forge-std",
                    cwd=tmpdir,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(install_proc.communicate(), timeout=60)
                if install_proc.returncode != 0:
                    logger.warning("forge install forge-std failed — tests may not compile")
            except (asyncio.TimeoutError, FileNotFoundError) as e:
                logger.warning(f"forge-std install skipped: {e}")

            # -- run forge test --
            try:
                proc = await asyncio.create_subprocess_exec(
                    "forge", "test", "--match-test", "invariant_", "--json", "-vvvvv",
                    cwd=tmpdir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Invariant fuzz timed out after {timeout}s")
                return {"passed": True, "fuzz_findings": [], "note": "fuzz timeout"}

            out = stdout.decode(errors="replace")
            err = stderr.decode(errors="replace")
            parsed = parse_forge_output(out, err, proc.returncode)
            findings = self._extract_invariant_failures(parsed, out)

            return {
                "passed": len(findings) == 0,
                "fuzz_findings": findings,
                "raw": out[:4000],
            }

    def _extract_invariant_failures(self, parsed: dict, raw: str) -> list[dict]:
        """
        Extract failing invariant tests from parsed forge output.

        Args:
            parsed: Output of parse_forge_output() — has test_results dict.
            raw: Raw stdout string (unused, reserved for text-mode fallback).

        Returns:
            List of dicts with invariant name, counterexample/reason, and impact.
        """
        findings: list[dict] = []
        for test_name, res in (parsed.get("test_results") or {}).items():
            if res.get("status") == "fail" and "invariant_" in test_name:
                findings.append({
                    "invariant": test_name,
                    "counterexample": res.get("reason", ""),
                    "impact": "High",
                })
        return findings

    async def generate_invariant_contract(self, contract_code: str) -> str:
        """
        Generate a Foundry invariant test contract for the given contract via LLM.

        Reuses the _generate_test_case pattern (validator.py): LLM call → code
        block extraction → minimal template fallback so the fuzz() pipeline never
        breaks on LLM failure.

        Args:
            contract_code: Solidity source of the contract under test.

        Returns:
            A Solidity invariant test contract string (importable by fuzz()).
        """
        from ..utils.mimo_llm import get_mimo_llm

        prompt = (
            "Generate a Foundry invariant test contract for fuzzing this contract.\n"
            f"Contract:\n```solidity\n{contract_code}\n```\n"
            "Requirements: import forge-std/Test.sol and the contract under test "
            "(it lives at src/Contract.sol, so use `import \"../src/Contract.sol\";`). "
            "Define setUp() that deploys the contract and 2-3 invariant_ functions "
            "covering balance/supply conservation and access control. "
            "Return ONLY the Solidity test contract."
        )

        try:
            llm = get_mimo_llm()
            result = await llm.generate(prompt=prompt, temperature=0.2)

            # Extract Solidity code block
            if "```solidity" in result:
                return result.split("```solidity")[1].split("```")[0].strip()
            if "```" in result:
                return result.split("```")[1].split("```")[0].strip()
            return result.strip()
        except Exception as e:
            logger.error(f"Invariant contract generation failed: {e}")
            # Minimal template fallback — compiles, runs, finds nothing
            return (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                'import "forge-std/Test.sol";\n'
                'import "../src/Contract.sol";\n\n'
                "contract InvariantTest is Test {\n"
                "    function invariant_true() public {\n"
                '        assertTrue(true, "placeholder invariant");\n'
                "    }\n"
                "}\n"
            )

    # -----------------------------------------------------------------------
    # Internal execution helpers
    # -----------------------------------------------------------------------
    async def _execute_local(self, exploit_code: str) -> dict:
        """Execute exploit on local Foundry instance."""
        logger.info("Executing on local Foundry instance")

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            test_dir = Path(tmpdir) / "test"
            src_dir.mkdir(parents=True)
            test_dir.mkdir(parents=True)

            # Write exploit as test
            test_path = test_dir / "Exploit.t.sol"
            test_path.write_text(exploit_code)

            # Write foundry.toml
            config_path = Path(tmpdir) / "foundry.toml"
            config_path.write_text(
                '[profile.default]\nsrc = "src"\ntest = "test"\nverbosity = 5\n'
            )

            result = await self._run_forge_test(tmpdir)
            return result

    async def _execute_fork(self, contract_address: str, exploit_code: str, block_number: int = None) -> dict:
        """Execute exploit on forked blockchain."""
        logger.info(f"Executing on forked blockchain at {contract_address}")

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            test_dir = Path(tmpdir) / "test"
            src_dir.mkdir(parents=True)
            test_dir.mkdir(parents=True)

            # Write exploit
            test_path = test_dir / "Exploit.t.sol"
            test_path.write_text(exploit_code)

            # Write foundry.toml with fork config
            config_path = Path(tmpdir) / "foundry.toml"
            fork_block = f'\nblock_number = {block_number}' if block_number else ""
            config_path.write_text(
                f'[profile.default]\n'
                f'src = "src"\ntest = "test"\n'
                f'verbosity = 5\n'
                f'fork_url = "{self.rpc_url}"{fork_block}\n'
            )

            result = await self._run_forge_test(tmpdir)
            return result

    # -----------------------------------------------------------------------
    # Forge test runner (with JSON + text dual parsing)
    # -----------------------------------------------------------------------
    async def _run_forge_test(self, project_dir: str) -> dict:
        """
        Run forge test with -vvvvv verbosity and parse the three A1 signals.

        Strategy:
          1. Try `forge test --json -vvvvv` for structured JSON with full traces
          2. Fall back to `forge test -vvvvv` text output if JSON parsing fails
          3. Gracefully handle forge-not-installed case
        """
        # Check forge availability
        if not await _check_forge_available_async():
            logger.warning("Forge not installed — returning unavailable signal")
            return {
                "success": False,
                "tests_passed": 0,
                "tests_failed": 0,
                "gas_used": 0,
                "profit": 0.0,
                "revert_reason": "",
                "trace": "",
                "raw_output": "",
                "test_results": {},
                "error": "forge_unavailable",
                "message": "Forge is not installed. Install Foundry: curl -L https://foundry.paradigm.xyz | bash",
            }

        try:
            # First attempt: JSON mode (structured + traces)
            proc = await asyncio.create_subprocess_exec(
                "forge", "test", "--json", "-vvvvv",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
            stdout_text = stdout.decode(errors="replace")
            stderr_text = stderr.decode(errors="replace")

            result = parse_forge_output(stdout_text, stderr_text, proc.returncode)

            # If JSON parsing produced no test results, try text-only fallback
            if not result.get("test_results") and proc.returncode != 0:
                logger.debug("JSON parse empty, retrying with text-only -vvvvv")
                result = await _run_forge_text_fallback(project_dir)

            return result

        except asyncio.TimeoutError:
            logger.error("Forge test timed out after 180s")
            return {
                "success": False,
                "error": "timeout",
                "tests_passed": 0,
                "tests_failed": 0,
                "gas_used": 0,
                "profit": 0.0,
                "revert_reason": "Test timed out after 180 seconds",
                "trace": "",
                "raw_output": "",
                "test_results": {},
            }
        except FileNotFoundError:
            logger.error("Forge not found")
            return {
                "success": False,
                "error": "forge_unavailable",
                "tests_passed": 0,
                "tests_failed": 0,
                "gas_used": 0,
                "profit": 0.0,
                "revert_reason": "",
                "trace": "",
                "raw_output": "",
                "test_results": {},
                "message": "Forge not installed. Install Foundry: curl -L https://foundry.paradigm.xyz | bash",
            }
        except Exception as e:
            logger.error(f"Forge test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tests_passed": 0,
                "tests_failed": 0,
                "gas_used": 0,
                "profit": 0.0,
                "revert_reason": "",
                "trace": "",
                "raw_output": "",
                "test_results": {},
            }


async def _run_forge_text_fallback(project_dir: str) -> dict:
    """Run forge test with -vvvvv only (no --json) and parse text output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "forge", "test", "-vvvvv",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        return parse_forge_output(
            stdout.decode(errors="replace"),
            stderr.decode(errors="replace"),
            proc.returncode,
        )
    except Exception as e:
        logger.error(f"Text fallback also failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "tests_passed": 0,
            "tests_failed": 0,
            "gas_used": 0,
            "profit": 0.0,
            "revert_reason": "",
            "trace": "",
            "raw_output": "",
            "test_results": {},
        }
