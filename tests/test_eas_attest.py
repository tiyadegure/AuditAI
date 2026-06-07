"""
Smoke tests for EAS attestation fallback and encoding.
"""

import pytest
from click.testing import CliRunner

import src.main as main_mod
from src.chain.chain_verifier import ChainVerifier
from src.chain.eas_attest import _encode_audit_data, attest_audit


def test_attest_audit_missing_key_returns_mock(monkeypatch):
    monkeypatch.delenv("WALLET_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("SCHEMA_UID", "0x" + "11" * 32)

    result = attest_audit("0x0000000000000000000000000000000000000001", [], "all")

    assert result["mock"] is True
    assert result["success"] is False
    assert result["tx_hash"].startswith("mock-0x")


def test_attest_audit_bad_schema_returns_mock_before_rpc(monkeypatch):
    monkeypatch.setenv(
        "WALLET_PRIVATE_KEY",
        "0x" + "11" * 32,
    )
    monkeypatch.setenv("SCHEMA_UID", "0x1234")

    result = attest_audit("0x0000000000000000000000000000000000000001", [], "all")

    assert result["mock"] is True
    assert result["success"] is False
    assert result["tx_hash"].startswith("mock-0x")
    assert "SCHEMA_UID invalid" in result["message"]


def test_encode_audit_data_schema_order():
    import eth_abi

    encoded = _encode_audit_data(
        "0x0000000000000000000000000000000000000001",
        10,
        2,
        "all",
        123,
    )
    decoded = eth_abi.decode(
        ["uint8", "uint16", "string", "uint64", "address"],
        encoded,
    )

    assert decoded[0] == 10
    assert decoded[1] == 2
    assert decoded[2] == "all"
    assert decoded[3] == 123
    assert decoded[4].lower().endswith("0001")


def test_encode_audit_data_clamps_uint_fields():
    import eth_abi

    encoded = _encode_audit_data(
        "0x0000000000000000000000000000000000000001",
        -1,
        70000,
        "all",
        -5,
    )
    decoded = eth_abi.decode(
        ["uint8", "uint16", "string", "uint64", "address"],
        encoded,
    )

    assert decoded[0] == 0
    assert decoded[1] == 65535
    assert decoded[3] == 0


@pytest.mark.asyncio
async def test_record_audit_degrades_without_key(monkeypatch):
    monkeypatch.delenv("WALLET_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("SCHEMA_UID", "0x" + "11" * 32)
    verifier = ChainVerifier(rpc_url="http://127.0.0.1:1", chain_id=11155111)

    tx = await verifier.record_audit(
        "0x0000000000000000000000000000000000000001",
        {"vulnerabilities": [], "mode": "all"},
    )

    assert isinstance(tx, str)
    assert tx.startswith("mock-0x")


def test_audit_attest_requires_contract_address_before_audit(monkeypatch):
    class FailIfInstantiated:
        def __init__(self, *args, **kwargs):
            raise AssertionError("audit should not start without --contract-address")

    monkeypatch.setattr(main_mod, "AgentOrchestrator", FailIfInstantiated)

    runner = CliRunner()
    result = runner.invoke(
        main_mod.cli,
        ["audit", "data/contracts/VulnerableBank.sol", "--attest"],
    )

    assert result.exit_code == 2
    assert "--contract-address is required when using --attest" in result.output


def test_standalone_attest_without_contract_path_uses_empty_mock(monkeypatch):
    class FailIfInstantiated:
        def __init__(self, *args, **kwargs):
            raise AssertionError("standalone attest without --contract-path should not audit")

    monkeypatch.setattr(main_mod, "AgentOrchestrator", FailIfInstantiated)
    monkeypatch.delenv("WALLET_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("SCHEMA_UID", "0x" + "11" * 32)

    runner = CliRunner()
    result = runner.invoke(
        main_mod.cli,
        ["attest", "0x0000000000000000000000000000000000000001"],
    )

    assert result.exit_code == 0
    assert "attesting with empty vuln list" in result.output
    assert "mock-0x" in result.output
    assert "WALLET_PRIVATE_KEY not set" in result.output
    assert "No real transaction was sent." in result.output
