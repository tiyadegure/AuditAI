"""
MiMo LLM Wrapper
Direct integration with Xiaomi MiMo API
"""

import os
import json
import httpx
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

# MiMo API configuration
# Token Plan (China) - for tp- prefix keys (verified working endpoint)
MIMO_TOKEN_PLAN_BASE = os.getenv(
    "MIMO_TOKEN_PLAN_BASE", "https://token-plan-cn.xiaomimimo.com/v1"
)
# Official API - for regular API keys
MIMO_API_BASE = "https://api.xiaomimimo.com/v1"


class MiMoLLM:
    """
    MiMo LLM: Direct wrapper for Xiaomi MiMo API.
    
    Features:
    1. Direct connection to MiMo API (no Pi agent hop)
    2. Auto-detect token plan vs regular API key
    3. Connection pooling for better performance
    4. Support for code generation
    5. Support for analysis tasks
    """
    
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "mimo-v2.5-pro",
        temperature: float = 0.3,  # Lower for faster, more deterministic responses
        max_tokens: int = 2048,    # Reduced for faster responses
    ):
        self.api_key = api_key or os.getenv("MIMO_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not self.api_key:
            raise ValueError(
                "MIMO_API_KEY not set. Get your key at: https://platform.xiaomimimo.com/console/plan-manage\n"
                "Then set: export MIMO_API_KEY=your_key_here"
            )
        
        # Auto-detect API base: token plan keys (tp-) use different endpoint
        if api_base:
            self.api_base = api_base
        elif self.api_key.startswith("tp-"):
            self.api_base = MIMO_TOKEN_PLAN_BASE
            logger.info(f"Detected token plan key, using: {self.api_base}")
        else:
            self.api_base = os.getenv("MIMO_API_BASE", MIMO_API_BASE)
        
        # Create client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
        
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        Generate text using MiMo API.
        """
        logger.info(f"Generating with MiMo: {prompt[:50]}...")
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens or self.max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"MiMo API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"MiMo API error: {e}")
            raise
    
    async def analyze_code(self, code: str, task: str = "vulnerability_detection") -> str:
        """Analyze code using MiMo - optimized for speed."""
        system_prompt = """Smart contract security auditor. Find vulnerabilities. Return JSON."""
        
        # Truncate code for faster response
        code_preview = code[:1500] if len(code) > 1500 else code
        
        prompt = f"""Find vulnerabilities in this Solidity code. Return JSON only.

```solidity
{code_preview}
```

Format: {{"vulnerabilities": [{{"type": "...", "severity": "high/medium/low", "location": "...", "description": "..."}}]}}"""
        
        return await self.generate(prompt, system_prompt, max_tokens=1024)
    
    async def generate_patch(self, code: str, vulnerability: dict, strategy: dict) -> str:
        """Generate a patch for a vulnerability."""
        system_prompt = """You are an expert Solidity developer specializing in security.
Generate secure, gas-efficient code patches."""
        
        prompt = f"""Generate a patch for the following vulnerability.

Original Code:
```solidity
{code}
```

Vulnerability:
- Type: {vulnerability.get('type', 'unknown')}
- Description: {vulnerability.get('description', 'unknown')}
- Location: {vulnerability.get('location', 'unknown')}

Repair Strategy:
{json.dumps(strategy, indent=2)}

Provide the complete patched code."""
        
        return await self.generate(prompt, system_prompt)
    
    async def design_strategy(self, code: str, vulnerability: dict) -> dict:
        """Design a repair strategy."""
        system_prompt = """You are an expert security architect.
Design repair strategies for smart contract vulnerabilities."""
        
        prompt = f"""Design a repair strategy for the following vulnerability.

Code:
```solidity
{code}
```

Vulnerability:
- Type: {vulnerability.get('type', 'unknown')}
- Description: {vulnerability.get('description', 'unknown')}

Provide the strategy in JSON format:
{{
    "description": "strategy description",
    "steps": ["step1", "step2", ...],
    "considerations": ["consideration1", ...],
    "estimated_effort": "low/medium/high"
}}"""
        
        result = await self.generate(prompt, system_prompt)
        
        try:
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(result[start:end])
        except:
            pass
        
        return {
            "description": result,
            "steps": [],
            "considerations": [],
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
_mimo_llm = None


def get_mimo_llm() -> MiMoLLM:
    """Get or create global MiMo LLM instance"""
    global _mimo_llm
    
    if _mimo_llm is None:
        _mimo_llm = MiMoLLM()
    
    return _mimo_llm
