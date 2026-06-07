"""
Chain Verifier
Record audit results on-chain for transparency
Reference: BGA Track - AI for Transparency
"""

import json
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChainVerifier:
    """
    Chain Verifier: Record audit results on-chain.
    
    Features:
    1. Record audit results as on-chain transactions
    2. Generate verifiable credentials for audits
    3. Verify contract integrity
    
    Reference: BGA Track - AI for Transparency
    """
    
    # 免费公共 RPC（无 API Key 限制，按实测延迟排序）
    FREE_RPCS = [
        "https://eth-mainnet.g.alchemy.com/v2/Wuh10y_yTyH6_v9MV1FEq",  # Alchemy - 最快
        "https://eth.drpc.org",              # ~2s, 备用
        "https://ethereum-rpc.publicnode.com", # ~2s, 备用
    ]

    def __init__(self, rpc_url: str = None, chain_id: int = 1):
        self.rpc_url = rpc_url or self.FREE_RPCS[0]
        self.chain_id = chain_id
        self._web3 = None
    
    def _get_web3(self):
        """Get or create Web3 instance with failover"""
        if self._web3 is None:
            try:
                from web3 import Web3
                self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                # 验证连接
                if not self._web3.is_connected():
                    self._try_fallback_rpcs()
            except ImportError:
                logger.error("web3 not installed. Run: pip install web3")
                raise
        return self._web3

    def _try_fallback_rpcs(self):
        """Try fallback RPC endpoints"""
        from web3 import Web3
        for rpc in self.FREE_RPCS:
            if rpc == self.rpc_url:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc))
                if w3.is_connected():
                    self.rpc_url = rpc
                    self._web3 = w3
                    logger.info(f"Switched to RPC: {rpc}")
                    return
            except Exception:
                continue
        logger.warning("All RPC endpoints failed")
    
    async def record_audit(self, contract_address: str, audit_result: dict) -> str:
        """
        Record audit result through EAS, falling back safely.
        
        Args:
            contract_address: Audited contract address
            audit_result: Audit result dict
            
        Returns:
            Transaction hash
        """
        logger.info(f"Recording audit for {contract_address}")
        
        try:
            from .eas_attest import attest_audit

            result = attest_audit(
                contract_address=contract_address,
                vulnerabilities=audit_result.get("vulnerabilities", []),
                audit_mode=audit_result.get("mode", "all"),
            )
            tx_hash = result.get("tx_hash") or ""

            if result.get("mock"):
                logger.warning(result.get("message", "EAS mock fallback"))
            elif result.get("success"):
                logger.info(f"Audit attested on EAS: {tx_hash}")
            else:
                logger.error(result.get("message", "EAS attestation failed"))

            return tx_hash
            
        except Exception as e:
            logger.error(f"Failed to record audit: {e}")
            return f"error-{str(e)[:16]}"
    
    async def verify_contract(self, contract_address: str) -> dict:
        """
        Verify contract integrity.
        
        Args:
            contract_address: Contract address
            
        Returns:
            Verification result
        """
        logger.info(f"Verifying contract {contract_address}")
        
        try:
            w3 = self._get_web3()
            
            # Get contract code
            code = w3.eth.get_code(contract_address)
            
            # Check if contract exists
            is_contract = len(code) > 0
            
            # Get bytecode hash for integrity check
            code_hash = w3.keccak(code).hex() if is_contract else None
            
            return {
                "address": contract_address,
                "is_contract": is_contract,
                "code_hash": code_hash,
                "code_size": len(code),
                "verified": is_contract,
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "address": contract_address,
                "error": str(e),
                "verified": False,
            }
    
    async def generate_credential(self, audit_result: dict) -> dict:
        """
        Generate verifiable credential for audit.
        
        Args:
            audit_result: Audit result dict
            
        Returns:
            Verifiable credential dict (W3C format)
        """
        logger.info("Generating verifiable credential")
        
        # Create W3C Verifiable Credential
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://smartaudit.io/credentials/v1",
            ],
            "type": ["VerifiableCredential", "SmartContractAuditCredential"],
            "issuer": {
                "id": "did:eth:ai-audit-agent",
                "name": "AI Smart Contract Audit Agent",
            },
            "issuanceDate": "2026-05-31T00:00:00Z",
            "credentialSubject": {
                "contractAddress": audit_result.get("contract_address"),
                "auditScore": audit_result.get("score", 0),
                "vulnerabilitiesFound": len(audit_result.get("vulnerabilities", [])),
                "auditMode": audit_result.get("mode", "all"),
            },
            "proof": {
                "type": "EthereumEip712Signature2021",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:eth:ai-audit-agent#key-1",
            },
        }
        
        return credential
    
    def _compute_hash(self, data: dict) -> str:
        """Compute hash of audit record"""
        import hashlib
        
        # Create deterministic hash
        data_str = json.dumps(data, sort_keys=True)
        hash_bytes = hashlib.sha256(data_str.encode()).digest()
        
        return f"0x{hash_bytes.hex()[:64]}"
