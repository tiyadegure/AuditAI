"""
EAS (Ethereum Attestation Service) Attestation Module

Posts audit results on-chain via EAS on Sepolia testnet.

Degradation gates (checked in order, each -> mock+warn, never raise):
  1. no WALLET_PRIVATE_KEY          -> mock (ISC-7)
  2. no/invalid SCHEMA_UID          -> mock (ISC-11)
  3. RPC unreachable after fallback -> mock (ISC-8)
  4. tx build/send/revert           -> error-... marker (ISC-9, ISC-10)

Schema (pre-registered, fixed UID in .env):
  uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode,
  uint64 timestamp, address contractAddress
"""

from __future__ import annotations

import hashlib
import os
import time

from ..utils.logger import get_logger

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEPOLIA_RPC_URL_DEFAULT = "https://sepolia.drpc.org"

EAS_CONTRACT_ADDRESS = "0xC2679fBD37d54388Ce493F1DB75320D236e1815e"
SCHEMA_REGISTRY_ADDRESS = "0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0"

# Minimal EAS ABI: only the attest function we call.
EAS_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "schema", "type": "bytes32"},
                    {
                        "components": [
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint64", "name": "expirationTime", "type": "uint64"},
                            {"internalType": "bool", "name": "revocable", "type": "bool"},
                            {"internalType": "bytes32", "name": "refUID", "type": "bytes32"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {"internalType": "uint256", "name": "value", "type": "uint256"},
                        ],
                        "internalType": "struct EAS.AttestationRequestData",
                        "name": "data",
                        "type": "tuple",
                    },
                ],
                "internalType": "struct EAS.AttestationRequest",
                "name": "request",
                "type": "tuple",
            },
        ],
        "name": "attest",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function",
    },
]

ZERO_BYTES32 = "0x0000000000000000000000000000000000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# Encoding helper
# ---------------------------------------------------------------------------

def _encode_audit_data(
    contract_address: str,
    audit_score: int,
    vulnerabilities_found: int,
    audit_mode: str,
    timestamp: int,
) -> bytes:
    """ABI-encode attestation data matching the registered schema.

    Schema order (from EAS registration):
      uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode,
      uint64 timestamp, address contractAddress
    """
    import eth_abi

    audit_score = max(0, min(int(audit_score), 255))
    vulnerabilities_found = max(0, min(int(vulnerabilities_found), 65535))
    timestamp = max(0, min(int(timestamp), 2**64 - 1))

    return eth_abi.encode(
        ["uint8", "uint16", "string", "uint64", "address"],
        [
            audit_score,
            vulnerabilities_found,
            audit_mode,
            timestamp,
            contract_address,
        ],
    )


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------

_SEV_TO_SCORE = {
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 7,
    "informational": 9,
    "info": 9,
}


def compute_audit_score(vulnerabilities: list[dict]) -> int:
    """Derive a 0-10 security score from findings.

    0 = many criticals, 10 = no vulnerabilities found.
    """
    if not vulnerabilities:
        return 10

    worst = 10
    for v in vulnerabilities:
        sev = (v.get("severity") or "medium").lower()
        score = _SEV_TO_SCORE.get(sev, 5)
        worst = min(worst, score)
    return worst


# ---------------------------------------------------------------------------
# Mock helper
# ---------------------------------------------------------------------------

def _mock_tx_hash(label: str) -> str:
    """Return a deterministic mock tx hash (ISC-7/ISC-8/ISC-11)."""
    digest = hashlib.sha256(f"mock-eas-{label}-{time.time()}".encode()).hexdigest()
    return f"mock-0x{digest[:64]}"


# ---------------------------------------------------------------------------
# Web3 connection (lazy, with fallback)
# ---------------------------------------------------------------------------

def _get_web3():
    """Create a Web3 instance for Sepolia with fallback."""
    try:
        from web3 import Web3
    except ImportError:
        raise RuntimeError("web3 is required. Run: pip install web3")

    rpc_url = os.getenv("SEPOLIA_RPC_URL", SEPOLIA_RPC_URL_DEFAULT)
    fallbacks = [
        rpc_url,
        "https://sepolia.drpc.org",
        "https://rpc.sepolia.org",
        "https://ethereum-sepolia-rpc.publicnode.com",
    ]

    for url in fallbacks:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
            if w3.is_connected():
                logger.info(f"EAS: connected to {url}")
                return w3
        except Exception:
            continue

    # ISC-8: all RPCs failed
    raise ConnectionError("All Sepolia RPC endpoints unreachable")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def attest_audit(
    contract_address: str,
    vulnerabilities: list[dict],
    audit_mode: str = "all",
) -> dict:
    """Attest audit results on EAS Sepolia.

    Returns dict with keys:
        success  : bool
        tx_hash  : str (real 0x... or mock-... or error-...)
        message  : str
        mock     : bool  (True when degradation kicked in)
    """
    # --- Gate 1: WALLET_PRIVATE_KEY (ISC-7) ---
    private_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
    if not private_key:
        msg = "ISC-7: WALLET_PRIVATE_KEY not set - returning mock attestation"
        logger.warning(msg)
        return {"success": False, "tx_hash": _mock_tx_hash("no-key"), "message": msg, "mock": True}

    # Normalise key (ensure 0x prefix)
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    # --- Gate 2: SCHEMA_UID (ISC-11) ---
    schema_uid = os.getenv("SCHEMA_UID", "").strip()
    try:
        if not schema_uid.startswith("0x") or len(schema_uid) != 66:
            raise ValueError("SCHEMA_UID must be 0x + 64 hex chars")
        schema_bytes = bytes.fromhex(schema_uid[2:])
        if len(schema_bytes) != 32:
            raise ValueError("SCHEMA_UID must decode to 32 bytes")
    except ValueError as exc:
        msg = f"ISC-11: SCHEMA_UID invalid ({exc}) - returning mock"
        logger.warning(msg)
        return {"success": False, "tx_hash": _mock_tx_hash("bad-schema"), "message": msg, "mock": True}

    # --- Compute fields ---
    audit_score = compute_audit_score(vulnerabilities)
    vuln_count = len(vulnerabilities)
    ts = int(time.time())

    logger.info(
        f"EAS attest: contract={contract_address} score={audit_score} "
        f"vulns={vuln_count} mode={audit_mode}"
    )

    # --- Gate 3: RPC connection (ISC-8) ---
    try:
        w3 = _get_web3()
    except (ConnectionError, Exception) as exc:
        msg = f"ISC-8: Sepolia RPC unreachable - {exc}"
        logger.warning(msg)
        return {"success": False, "tx_hash": _mock_tx_hash("rpc-fail"), "message": msg, "mock": True}

    # --- Build transaction (Gate 4a) ---
    try:
        checksum_contract = w3.to_checksum_address(contract_address)
        encoded_data = _encode_audit_data(
            checksum_contract, audit_score, vuln_count, audit_mode, ts,
        )

        eas_address = os.getenv("EAS_CONTRACT_ADDRESS", EAS_CONTRACT_ADDRESS).strip() or EAS_CONTRACT_ADDRESS
        eas = w3.eth.contract(
            address=w3.to_checksum_address(eas_address),
            abi=EAS_ABI,
        )

        request_data = (
            checksum_contract,                         # recipient
            0,                                          # expirationTime
            True,                                       # revocable
            bytes.fromhex(ZERO_BYTES32[2:]),            # refUID
            encoded_data,                               # data
            0,                                          # value
        )

        # Nonce
        from web3 import Account
        from hexbytes import HexBytes

        account = Account.from_key(private_key)
        nonce = w3.eth.get_transaction_count(account.address)

        # Gas estimation + EIP-1559 fees
        try:
            latest_block = w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas", w3.to_wei(10, "gwei"))
        except Exception:
            base_fee = w3.to_wei(10, "gwei")

        max_priority = w3.to_wei(2, "gwei")

        tx_params = {
            "chainId": 11155111,
            "from": account.address,
            "nonce": nonce,
            "gas": 300_000,
            "maxFeePerGas": base_fee * 2 + max_priority,
            "maxPriorityFeePerGas": max_priority,
        }
        try:
            tx = eas.functions.attest(
                (HexBytes(schema_bytes), request_data)
            ).build_transaction(tx_params)
        except Exception as exc:
            logger.warning(f"EAS: EIP-1559 tx build failed, retrying legacy gasPrice - {exc}")
            legacy_params = {
                "chainId": 11155111,
                "from": account.address,
                "nonce": nonce,
                "gas": 300_000,
                "gasPrice": w3.eth.gas_price,
            }
            tx = eas.functions.attest(
                (HexBytes(schema_bytes), request_data)
            ).build_transaction(legacy_params)

        # --- Sign + Send (Gate 4b/4c) ---
        signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info(f"EAS: tx sent, hash={tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt.status == 1:
            tx_hex = receipt.transactionHash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex
            logger.info(f"EAS: attestation confirmed - {tx_hex}")
            return {
                "success": True,
                "tx_hash": tx_hex,
                "message": f"Attestation confirmed on Sepolia",
                "mock": False,
            }
        else:
            msg = f"ISC-9: tx reverted (receipt.status=0) - tx={tx_hash.hex()}"
            logger.error(msg)
            return {"success": False, "tx_hash": f"error-revert-{tx_hash.hex()[:16]}", "message": msg, "mock": False}

    except Exception as exc:
        msg = f"ISC-10: tx build/send failed - {exc}"
        logger.error(msg)
        return {"success": False, "tx_hash": f"error-{hashlib.sha256(str(exc).encode()).hexdigest()[:16]}", "message": msg, "mock": False}
