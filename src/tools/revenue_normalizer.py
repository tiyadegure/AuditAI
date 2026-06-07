"""
Revenue Normalizer Tool
Normalize token amounts to native currency (ETH)
Reference: A1 paper - Revenue Normalizer Tool
"""

import asyncio
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RevenueNormalizerTool:
    """
    Revenue Normalizer Tool: Convert extracted tokens to native currency.
    
    Features:
    1. Query token prices from CoinGecko or similar
    2. Calculate USD/ETH value of extracted tokens
    3. Handle different token decimals
    
    Reference: A1 paper Section 3 - Revenue Normalizer Tool
    """
    
    def __init__(self, coingecko_api_key: str = None):
        self.coingecko_api_key = coingecko_api_key
        self._price_cache = {}
    
    async def normalize(self, token_address: str, amount: int, decimals: int = 18) -> dict:
        """
        Normalize token amount to native currency.
        
        Args:
            token_address: Token contract address
            amount: Token amount (in smallest unit)
            decimals: Token decimals
            
        Returns:
            Normalized value dict
        """
        logger.info(f"Normalizing {amount} of token {token_address}")
        
        try:
            # Get token price
            price_usd = await self._get_token_price(token_address)
            
            # Calculate value
            human_amount = amount / (10 ** decimals)
            value_usd = human_amount * price_usd
            
            # Get ETH price for conversion
            eth_price = await self._get_eth_price()
            value_eth = value_usd / eth_price if eth_price > 0 else 0
            
            return {
                "token_address": token_address,
                "amount": amount,
                "human_amount": human_amount,
                "decimals": decimals,
                "price_usd": price_usd,
                "value_usd": value_usd,
                "value_eth": value_eth,
            }
            
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            return {
                "token_address": token_address,
                "amount": amount,
                "error": str(e),
            }
    
    async def _get_token_price(self, token_address: str) -> float:
        """Get token price from CoinGecko"""
        # Check cache
        if token_address in self._price_cache:
            return self._price_cache[token_address]
        
        try:
            import aiohttp
            
            # CoinGecko API
            url = f"https://api.coingecko.com/api/v3/simple/token_price/ethereum"
            params = {
                "contract_addresses": token_address,
                "vs_currencies": "usd",
            }
            
            if self.coingecko_api_key:
                params["x_cg_demo_api_key"] = self.coingecko_api_key
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = data.get(token_address.lower(), {}).get("usd", 0)
                        self._price_cache[token_address] = price
                        return price
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get token price: {e}")
            return 0
    
    async def _get_eth_price(self) -> float:
        """Get ETH price in USD"""
        return await self._get_token_price("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    
    # ------------------------------------------------------------------
    # DexUtils: price-estimate swap helpers (A1 Appendix B)
    # ------------------------------------------------------------------

    async def swap_exact_token_to_base_token(
        self, token_address: str, amount: float, base_token: str = "WETH"
    ) -> dict:
        """Convert extracted token to base asset via price estimation.

        Corresponds to A1 Appendix B: ``swapExactTokenToBaseToken``.
        In production, this should query Uniswap V2/V3 for the deepest
        liquidity path.  Here we estimate using current token/ETH prices.
        """
        try:
            token_price = await self._get_token_price(token_address)
            eth_price = await self._get_eth_price()

            if eth_price <= 0:
                return {
                    "base_token": base_token,
                    "estimated_amount": 0.0,
                    "token_address": token_address,
                    "method": "swapExactTokenToBaseToken",
                    "path": [token_address, base_token],
                    "error": "eth_price_unavailable",
                }

            estimated = amount * (token_price / eth_price) if token_price else 0.0
            return {
                "base_token": base_token,
                "estimated_amount": estimated,
                "token_address": token_address,
                "method": "swapExactTokenToBaseToken",
                "path": [token_address, base_token],
            }
        except Exception as e:
            logger.error(f"swap_exact_token_to_base_token failed: {e}")
            return {
                "base_token": base_token,
                "estimated_amount": 0.0,
                "token_address": token_address,
                "method": "swapExactTokenToBaseToken",
                "path": [token_address, base_token],
                "error": str(e),
            }

    async def swap_exact_base_token_to_token(
        self, token_address: str, base_amount: float, base_token: str = "WETH"
    ) -> dict:
        """Convert base asset to target token via price estimation.

        Corresponds to A1 Appendix B: ``swapExactBaseTokenToToken``.
        """
        try:
            token_price = await self._get_token_price(token_address)
            eth_price = await self._get_eth_price()

            if token_price <= 0:
                return {
                    "token_address": token_address,
                    "estimated_amount": 0.0,
                    "base_token": base_token,
                    "method": "swapExactBaseTokenToToken",
                    "path": [base_token, token_address],
                    "error": "token_price_unavailable",
                }

            estimated = base_amount * (eth_price / token_price)
            return {
                "token_address": token_address,
                "estimated_amount": estimated,
                "base_token": base_token,
                "method": "swapExactBaseTokenToToken",
                "path": [base_token, token_address],
            }
        except Exception as e:
            logger.error(f"swap_exact_base_token_to_token failed: {e}")
            return {
                "token_address": token_address,
                "estimated_amount": 0.0,
                "base_token": base_token,
                "method": "swapExactBaseTokenToToken",
                "path": [base_token, token_address],
                "error": str(e),
            }

    async def swap_excess_tokens_to_base_token(
        self, token_balances: list[dict], base_token: str = "WETH"
    ) -> dict:
        """Batch-convert surplus token balances to base asset.

        Corresponds to A1 Appendix B: ``swapExcessTokensToBaseToken``.
        Each element of *token_balances* should have at least
        ``{token_address, amount}``.
        """
        conversions = []
        total_base = 0.0
        for entry in token_balances:
            result = await self.swap_exact_token_to_base_token(
                entry["token_address"], entry["amount"], base_token
            )
            conversions.append(result)
            total_base += result.get("estimated_amount", 0.0)

        return {
            "base_token": base_token,
            "total_estimated_base": total_base,
            "conversions": conversions,
            "method": "swapExcessTokensToBaseToken",
        }

    async def batch_normalize(self, tokens: list[dict]) -> list[dict]:
        """
        Batch normalize multiple tokens.
        
        Args:
            tokens: List of {token_address, amount, decimals}
            
        Returns:
            List of normalized values
        """
        results = []
        
        for token in tokens:
            result = await self.normalize(
                token["token_address"],
                token["amount"],
                token.get("decimals", 18),
            )
            results.append(result)
        
        return results
