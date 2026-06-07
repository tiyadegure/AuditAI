"""
AI Smart Contract Security Audit Agent
Main entry point
"""

import asyncio
import click
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load .env before any module reads MIMO_API_KEY.
# override=True so the verified CN key in .env wins over any stale shell key.
load_dotenv(override=True)
import os as _os
_os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from src.agents import AgentOrchestrator
from src.evaluation import EvaluationEngine
from src.chain import ChainVerifier, attest_audit
from src.mcp import MCPServer

console = Console()


def _print_attestation_result(result: dict):
    """Render EAS attestation result without exposing config secrets."""
    tx_hash = result.get("tx_hash", "")
    message = result.get("message", "")

    if result.get("success") and not result.get("mock"):
        console.print(f"[green]Attestation: {tx_hash}[/]  {message}")
        console.print(f"[cyan]Sepolia tx: https://sepolia.etherscan.io/tx/{tx_hash}[/cyan]")
    elif result.get("mock"):
        console.print(f"[yellow]Mock attestation: {tx_hash}[/]  {message}")
        console.print("[yellow]No real transaction was sent.[/yellow]")
    else:
        console.print(f"[red]Attestation failed: {tx_hash}[/]  {message}")


@click.group()
def cli():
    """AI Smart Contract Security Audit Agent"""
    pass


@cli.command()
@click.argument("contract_path", type=click.Path(exists=True))
@click.option("--mode", "-m", type=click.Choice(["detect", "patch", "exploit", "all"]), default="all")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--max-patches", type=int, default=2,
              help="Max vulnerabilities to patch, highest-severity first. Use -1 for all. Default: 2")
@click.option("--attest", is_flag=True, default=False,
              help="Attest audit results on-chain (EAS Sepolia) after completion")
@click.option("--contract-address", default=None,
              help="Contract address for on-chain attestation (required with --attest)")
@click.option("--resume", is_flag=True, default=False,
              help="Resume from last checkpoint")
def audit(contract_path: str, mode: str, output: str | None, max_patches: int,
          attest: bool, contract_address: str | None, resume: bool):
    """Audit a smart contract for vulnerabilities"""
    if attest and not contract_address:
        raise click.UsageError("--contract-address is required when using --attest")

    console.print(Panel(f"[bold blue]Auditing: {contract_path}[/bold blue]"))

    orchestrator = AgentOrchestrator()
    asyncio.run(orchestrator.initialize())
    result = asyncio.run(orchestrator.audit(contract_path, mode, max_patches=max_patches, resume=resume))
    
    if output:
        Path(output).write_text(result.to_json())
        console.print(f"[green]Results saved to: {output}[/green]")
    else:
        console.print(result.to_console())

    # --- On-chain attestation (--attest flag) ---
    if attest:
        console.print(Panel("[bold cyan]Attesting on EAS (Sepolia)...[/bold cyan]"))
        att = attest_audit(
            contract_address=contract_address,
            vulnerabilities=result.vulnerabilities,
            audit_mode=mode,
        )
        _print_attestation_result(att)


@cli.command()
@click.argument("contract_path", type=click.Path(exists=True))
@click.option("--multi-expert", "-me", is_flag=True, help="Use multi-expert analysis from forefy/.context")
@click.option("--strategy", "-s", type=click.Choice(["ba", "ta", "all"]), default="all",
              help="Detection strategy: ba=broad analysis, ta=targeted analysis, all=both (LLM-SmartAudit §3.2)")
def detect(contract_path: str, multi_expert: bool, strategy: str):
    """Detect vulnerabilities in a smart contract"""
    console.print(Panel(f"[bold yellow]Detecting vulnerabilities: {contract_path}[/bold yellow]"))
    
    orchestrator = AgentOrchestrator()
    asyncio.run(orchestrator.initialize())
    result = asyncio.run(orchestrator.detect(contract_path, use_multi_expert=multi_expert, strategy=strategy))
    
    # Handle both list and object results
    if isinstance(result, list):
        # Display list of vulnerabilities
        from rich.table import Table
        table = Table(title="Vulnerabilities Found")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Source", style="blue")
        
        for vuln in result:
            table.add_row(
                vuln.get("id", "unknown"),
                vuln.get("type", "unknown"),
                vuln.get("severity", "medium"),
                vuln.get("source", "unknown"),
            )
        console.print(table)
    else:
        console.print(result.to_console())


@cli.command()
@click.argument("contract_path", type=click.Path(exists=True))
@click.argument("vulnerability_id")
def patch(contract_path: str, vulnerability_id: str):
    """Patch a specific vulnerability in a smart contract"""
    console.print(Panel(f"[bold green]Patching {vulnerability_id}: {contract_path}[/bold green]"))
    
    orchestrator = AgentOrchestrator()
    asyncio.run(orchestrator.initialize())
    result = asyncio.run(orchestrator.patch(contract_path, vulnerability_id))
    console.print(result.to_console())


@cli.command()
@click.argument("contract_address")
@click.argument("exploit_code_path", type=click.Path(exists=True))
def exploit(contract_address: str, exploit_code_path: str):
    """Execute an exploit against a contract"""
    console.print(Panel(f"[bold red]Executing exploit: {contract_address}[/bold red]"))
    
    orchestrator = AgentOrchestrator()
    asyncio.run(orchestrator.initialize())
    result = asyncio.run(orchestrator.exploit(contract_address, exploit_code_path))
    console.print(result.to_console())


@cli.command()
@click.argument("contract_address")
@click.option("--contract-path", default=None, type=click.Path(exists=True),
              help="Path to contract source (auto-detects from audit history if omitted)")
def attest(contract_address: str, contract_path: str | None):
    """Attest audit results on EAS (Sepolia testnet)"""
    console.print(Panel(f"[bold cyan]EAS Attestation for: {contract_address}[/bold cyan]"))

    # If contract_path given, run a quick detection-only audit to get vulns
    if contract_path:
        orchestrator = AgentOrchestrator()
        asyncio.run(orchestrator.initialize())
        vulns = asyncio.run(orchestrator.detect(contract_path))
    else:
        vulns = []
        console.print("[yellow]No contract path — attesting with empty vuln list (score=10)[/yellow]")

    result = attest_audit(
        contract_address=contract_address,
        vulnerabilities=vulns,
        audit_mode="all",
    )

    _print_attestation_result(result)


@cli.command()
def serve():
    """Start the MCP server"""
    console.print(Panel("[bold cyan]Starting MCP Server...[/bold cyan]"))
    
    server = MCPServer()
    asyncio.run(server.start())


@cli.command()
def evaluate():
    """Run evaluation on test cases"""
    console.print(Panel("[bold magenta]Running Evaluation...[/bold magenta]"))
    
    engine = EvaluationEngine()
    results = asyncio.run(engine.run_all())
    console.print(results.to_console())


if __name__ == "__main__":
    cli()
