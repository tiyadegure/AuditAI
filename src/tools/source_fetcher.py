"""
Source Code Fetcher Tool
Fetches contract source code from various sources
Reference: A1 paper - Source Code Fetcher Tool
"""

import asyncio
import aiohttp
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SourceCodeFetcher:
    """
    Source Code Fetcher: Fetches contract source code.
    
    Sources:
    1. Local file
    2. Etherscan API (verified source code)
    3. IPFS (if available)
    
    Reference: A1 paper Section 3 - Source Code Fetcher Tool
    """
    
    def __init__(self, etherscan_api_key: str = None):
        self.etherscan_api_key = etherscan_api_key or "YourApiKeyToken"
        self.etherscan_url = "https://api.etherscan.io/api"
    
    def fetch(self, source: str) -> str:
        """
        Fetch contract source code.
        
        Args:
            source: Contract source (file path, address, or IPFS hash)
            
        Returns:
            Contract source code
        """
        logger.info(f"Fetching source from: {source}")
        
        # Check if it's a file path
        if Path(source).exists():
            return self._fetch_from_file(source)
        
        # Check if it's an Ethereum address
        if self._is_ethereum_address(source):
            return asyncio.run(self.fetch_async(source))
        
        # Check if it's an IPFS hash
        if source.startswith("Qm") or source.startswith("bafy"):
            return asyncio.run(self.fetch_async(source))
        
        raise ValueError(f"Unknown source type: {source}")
    
    async def fetch_async(self, source: str) -> str:
        """Async version of fetch"""
        if Path(source).exists():
            return self._fetch_from_file(source)
        
        if self._is_ethereum_address(source):
            return await self._fetch_from_etherscan(source)
        
        if source.startswith("Qm") or source.startswith("bafy"):
            return await self._fetch_from_ipfs(source)
        
        raise ValueError(f"Unknown source type: {source}")
    
    def _fetch_from_file(self, file_path: str) -> str:
        """Fetch source from local file"""
        logger.info(f"Fetching from file: {file_path}")
        return Path(file_path).read_text()
    
    async def _fetch_from_etherscan(self, address: str) -> str:
        """
        Fetch verified source code from Etherscan API.
        
        Reference: Etherscan API documentation
        """
        logger.info(f"Fetching from Etherscan: {address}")
        
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": self.etherscan_api_key,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.etherscan_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        if data.get("status") == "1" and data.get("result"):
                            result = data["result"][0]
                            source = result.get("SourceCode", "")
                            
                            if source:
                                logger.info(f"Fetched {len(source)} chars from Etherscan")
                                return source
                            else:
                                logger.warning("Contract not verified on Etherscan")
                                raise ValueError("Contract source code not verified on Etherscan")
                        else:
                            raise ValueError(f"Etherscan API error: {data.get('message')}")
                    else:
                        raise ValueError(f"Etherscan API request failed: {resp.status}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Etherscan API request failed: {e}")
            raise
    
    async def _fetch_from_ipfs(self, ipfs_hash: str) -> str:
        """
        Fetch source from IPFS gateway.
        
        Reference: IPFS HTTP Gateway documentation
        """
        logger.info(f"Fetching from IPFS: {ipfs_hash}")
        
        # Use public IPFS gateway
        gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(gateway_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        source = await resp.text()
                        logger.info(f"Fetched {len(source)} chars from IPFS")
                        return source
                    else:
                        raise ValueError(f"IPFS gateway returned {resp.status}")
                        
        except asyncio.TimeoutError:
            logger.error("IPFS fetch timed out")
            raise ValueError("IPFS fetch timed out")
        except aiohttp.ClientError as e:
            logger.error(f"IPFS fetch failed: {e}")
            raise
    
    def _is_ethereum_address(self, address: str) -> bool:
        """Check if string is an Ethereum address"""
        return address.startswith("0x") and len(address) == 42
