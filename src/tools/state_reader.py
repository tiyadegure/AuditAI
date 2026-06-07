"""
State Reader Tool
Read contract state from blockchain
Reference: A1 paper - State Reader Tool
"""

import json
import asyncio
from typing import Any, Optional
from ..utils.logger import get_logger
from ..chain.chain_verifier import ChainVerifier

logger = get_logger(__name__)


class StateReaderTool:
    """
    State Reader Tool: Read contract state from blockchain.
    
    Features:
    1. Analyze ABIs to identify view functions
    2. Capture state snapshots at target blocks via batch calls
    3. Query contract storage slots
    
    Reference: A1 paper Section 3 - State Reader Tool
    """
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or ChainVerifier.FREE_RPCS[0]
        self._web3 = None
    
    def _get_web3(self):
        """Get or create Web3 instance"""
        if self._web3 is None:
            try:
                from web3 import Web3
                self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            except ImportError:
                logger.error("web3 not installed. Run: pip install web3")
                raise
        return self._web3
    
    async def read_state(self, contract_address: str, block_number: int = None) -> dict:
        """
        Read contract state.
        
        Args:
            contract_address: Contract address
            block_number: Block number (latest if None)
            
        Returns:
            Contract state dict
        """
        logger.info(f"Reading state of {contract_address}")
        
        try:
            w3 = self._get_web3()
            
            # Get contract code
            code = w3.eth.get_code(contract_address, block_identifier=block_number)
            
            # Get balance
            balance = w3.eth.get_balance(contract_address, block_identifier=block_number)
            
            # Get transaction count (nonce)
            nonce = w3.eth.get_transaction_count(contract_address, block_identifier=block_number)
            
            return {
                "address": contract_address,
                "balance": str(balance),
                "nonce": nonce,
                "code_size": len(code),
                "block_number": block_number or "latest",
            }
            
        except Exception as e:
            logger.error(f"Failed to read state: {e}")
            return {
                "address": contract_address,
                "error": str(e),
            }
    
    async def query_function(self, contract_address: str, function_name: str, args: list = None) -> Any:
        """
        Query a view function.
        
        Args:
            contract_address: Contract address
            function_name: Function name
            args: Function arguments
            
        Returns:
            Function return value
        """
        logger.info(f"Querying {function_name} on {contract_address}")
        
        try:
            w3 = self._get_web3()
            
            # Build function call
            # Using low-level eth_call for flexibility
            from web3 import Web3
            
            # Simple function selector (first 4 bytes of keccak256)
            fn_selector = Web3.keccak(text=f"{function_name}()")[:4]
            
            # Make call
            result = w3.eth.call({
                "to": contract_address,
                "data": fn_selector.hex(),
            }, block_identifier="latest")
            
            return result.hex()
            
        except Exception as e:
            logger.error(f"Failed to query function: {e}")
            return None
    
    async def capture_snapshot(self, contract_address: str, block_number: int = None) -> dict:
        """
        Capture a state snapshot.
        
        Args:
            contract_address: Contract address
            block_number: Block number
            
        Returns:
            State snapshot dict
        """
        logger.info(f"Capturing snapshot of {contract_address}")
        
        try:
            w3 = self._get_web3()
            
            # Get basic state
            state = await self.read_state(contract_address, block_number)
            
            # Get storage at key slots
            storage = {}
            common_slots = [0, 1, 2, 3, 4, 5]  # Common storage slots
            
            for slot in common_slots:
                try:
                    value = w3.eth.get_storage_at(
                        contract_address, 
                        slot, 
                        block_identifier=block_number or "latest"
                    )
                    if value != b'\x00' * 32:
                        storage[slot] = value.hex()
                except Exception:
                    pass
            
            state["storage"] = storage
            state["snapshot_time"] = str(asyncio.get_event_loop().time())
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to capture snapshot: {e}")
            return {
                "address": contract_address,
                "error": str(e),
            }
    
    async def get_abi(self, contract_address: str) -> list:
        """
        Get contract ABI (from Etherscan or similar).
        
        Args:
            contract_address: Contract address
            
        Returns:
            Contract ABI list
        """
        # In production, fetch from Etherscan API
        # For now, return empty ABI
        logger.info(f"Getting ABI for {contract_address}")
        return []
