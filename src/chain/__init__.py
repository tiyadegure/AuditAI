"""
Chain Integration
On-chain verification and proof recording
"""

from .chain_verifier import ChainVerifier
from .eas_attest import attest_audit, compute_audit_score

__all__ = ["ChainVerifier", "attest_audit", "compute_audit_score"]
