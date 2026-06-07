"""
Constructor Parameter Tool
Extract and decode constructor parameters from deployed contracts.
Reference: A1 paper - Constructor Parameter Tool
"""

import asyncio
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConstructorParameterTool:
    """
    Constructor Parameter Tool: Decode constructor initialisation arguments
    from a deployed contract's creation transaction.

    Workflow (mirrors A1 Section 3):
    1. Retrieve the creation tx hash via Etherscan ``getcontractcreation``.
    2. Fetch the raw ``input`` data (bytecode + ABI-encoded args).
    3. Strip the deployed bytecode prefix to isolate constructor args.
    4. Optionally ABI-decode the args when an ABI is provided.

    Reference: A1 paper Section 3 - Constructor Parameter Tool
    """

    def __init__(self, rpc_url: str = None, etherscan_api_key: str = None):
        from ..chain.chain_verifier import ChainVerifier
        self.rpc_url = rpc_url or ChainVerifier.FREE_RPCS[0]
        self.etherscan_api_key = etherscan_api_key or "YourApiKeyToken"
        self.etherscan_url = "https://api.etherscan.io/api"
        self._web3 = None

    # ------------------------------------------------------------------
    # Lazy web3 init — mirrors src/tools/state_reader.py pattern
    # ------------------------------------------------------------------
    def _get_web3(self):
        """Get or create Web3 instance (lazy init)."""
        if self._web3 is None:
            try:
                from web3 import Web3
                self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            except ImportError:
                logger.error("web3 not installed. Run: pip install web3")
                raise
        return self._web3

    # ------------------------------------------------------------------
    # Main public method
    # ------------------------------------------------------------------
    async def extract_constructor_params(
        self, contract_address: str, abi: list = None
    ) -> dict:
        """Decode constructor parameters for a deployed contract.

        Args:
            contract_address: Deployed contract address.
            abi: Optional ABI list containing a ``constructor`` entry.
                 When provided the trailing bytes are ABI-decoded.

        Returns:
            dict with ``contract_address``, ``creation_tx``,
            ``raw_constructor_args``, ``decoded_params`` (or ``None``),
            and optionally ``error``.
        """
        result: dict = {
            "contract_address": contract_address,
            "creation_tx": None,
            "raw_constructor_args": None,
            "decoded_params": None,
        }

        try:
            # Step 1 — get creation tx hash from Etherscan
            creation_tx = await self._get_creation_tx_hash(contract_address)
            if creation_tx is None:
                result["error"] = "creation_tx_not_found"
                return result
            result["creation_tx"] = creation_tx

            # Step 2 — fetch raw input data
            input_data = await self._get_transaction_input(creation_tx)
            if input_data is None:
                result["error"] = "transaction_input_unavailable"
                return result

            # Step 3 — split constructor args from bytecode
            bytecode = await self._get_deployed_bytecode(contract_address)
            constructor_args_hex = self._split_constructor_args(
                input_data, bytecode
            )
            result["raw_constructor_args"] = constructor_args_hex

            # Step 4 — decode if ABI provided
            if abi and constructor_args_hex:
                decoded = self._decode_args(abi, constructor_args_hex)
                result["decoded_params"] = decoded

        except Exception as e:
            logger.error(f"extract_constructor_params failed: {e}")
            result["error"] = str(e)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_creation_tx_hash(self, contract_address: str) -> Optional[str]:
        """Fetch creation tx hash via Etherscan ``getcontractcreation``."""
        try:
            import aiohttp

            params = {
                "module": "contract",
                "action": "getcontractcreation",
                "contractaddresses": contract_address,
                "apikey": self.etherscan_api_key,
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(self.etherscan_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "1" and data.get("result"):
                            return data["result"][0].get("txHash")
                        logger.warning(
                            f"Etherscan getcontractcreation: {data.get('message')}"
                        )
            return None
        except Exception as e:
            logger.error(f"Etherscan creation tx lookup failed: {e}")
            return None

    async def _get_transaction_input(self, tx_hash: str) -> Optional[str]:
        """Fetch raw input data for a transaction via web3."""
        try:
            w3 = self._get_web3()
            tx = w3.eth.get_transaction(tx_hash)
            return tx.input.hex() if hasattr(tx.input, "hex") else tx.input
        except Exception as e:
            logger.error(f"Failed to get transaction input: {e}")
            return None

    async def _get_deployed_bytecode(self, contract_address: str) -> Optional[str]:
        """Fetch deployed runtime bytecode via web3."""
        try:
            w3 = self._get_web3()
            code = w3.eth.get_code(contract_address)
            return code.hex() if hasattr(code, "hex") else code
        except Exception as e:
            logger.error(f"Failed to get deployed bytecode: {e}")
            return None

    def _split_constructor_args(
        self, input_data: str, bytecode: str
    ) -> Optional[str]:
        """Strip deployed bytecode prefix to isolate constructor args.

        The creation ``input`` is ``creation_bytecode + constructor_args``.
        The deployed ``bytecode`` is a substring of the creation bytecode
        (minus constructor args).  We find where it ends and return the rest.
        """
        if not input_data or not bytecode:
            return None

        # Normalise hex
        input_data = input_data.lower().replace("0x", "")
        bytecode = bytecode.lower().replace("0x", "")

        # The deployed bytecode may appear as a sub-sequence.  Try exact
        # suffix match first; fall back to last occurrence.
        if input_data.endswith(bytecode):
            # creation bytecode == deployed bytecode (no extra args)
            # constructor args would be empty
            idx = len(input_data) - len(bytecode)
        else:
            idx = input_data.rfind(bytecode)
            if idx == -1:
                # Can't locate; return everything after a reasonable guess
                # (some compilers embed metadata differently)
                logger.warning(
                    "Could not locate deployed bytecode in creation input; "
                    "returning full input as fallback"
                )
                return input_data

        args = input_data[idx + len(bytecode) :]
        return "0x" + args if args else None

    def _decode_args(self, abi: list, args_hex: str) -> Optional[dict]:
        """ABI-decode constructor arguments using the provided ABI."""
        try:
            from eth_abi import decode as abi_decode

            # Find constructor entry in ABI
            ctor = next(
                (item for item in abi if item.get("type") == "constructor"), None
            )
            if ctor is None:
                logger.warning("No constructor entry in ABI; skipping decode")
                return None

            param_types = [p["type"] for p in ctor.get("inputs", [])]
            if not param_types:
                return {}

            raw = bytes.fromhex(args_hex.replace("0x", ""))
            values = abi_decode(param_types, raw)

            decoded = {}
            for param, value in zip(ctor["inputs"], values):
                # web3 returns bytes as HexBytes; convert for JSON safety
                if isinstance(value, bytes):
                    value = "0x" + value.hex()
                decoded[param["name"]] = value

            return decoded

        except ImportError:
            logger.error("eth-abi not installed. Run: pip install eth-abi")
            return None
        except Exception as e:
            logger.error(f"ABI decode failed: {e}")
            return None
