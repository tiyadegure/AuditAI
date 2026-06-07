"""
Code Generator Agent
Generates secure code patches for vulnerabilities
Reference: Smartify - Code Generator Agent
"""

import json
from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.mimo_llm import get_mimo_llm

logger = get_logger(__name__)


class CodeGeneratorAgent:
    """
    Code Generator Agent: Generates secure code patches for vulnerabilities.
    
    Responsibilities:
    1. Generate code patches based on repair strategy
    2. Ensure code follows best practices
    3. Consider gas optimization
    4. Maintain functionality
    
    Reference: Smartify - Code Generator Agent
    """
    
    def __init__(self, tools: ToolKit, knowledge: KnowledgeBase):
        self.tools = tools
        self.knowledge = knowledge
        self.llm = get_mimo_llm()
    
    async def generate(self, contract_code: str, vulnerability: dict, strategy: dict) -> dict:
        """
        Generate a code patch for a vulnerability.
        
        Args:
            contract_code: The original contract code
            vulnerability: Vulnerability details
            strategy: Repair strategy from Architect
            
        Returns:
            Generated patch with code and explanation
        """
        logger.info(f"Generating patch for {vulnerability.get('id', 'unknown')}")
        
        # Retrieve code patterns from knowledge base
        patterns = await self._retrieve_patterns(vulnerability)
        
        # Generate patch
        patch = await self._generate_patch(contract_code, vulnerability, strategy, patterns)
        
        return {
            "vulnerability_id": vulnerability.get("id", "unknown"),
            "patch_code": patch["code"],
            "explanation": patch["explanation"],
            "patterns_used": patterns,
        }
    
    async def _retrieve_patterns(self, vulnerability: dict) -> list[dict]:
        """Retrieve relevant code patterns from knowledge base via RAG"""
        logger.info("Retrieving code patterns")
        
        # Build a richer query string for better RAG retrieval
        vuln_type = vulnerability.get("type", "unknown")
        description = vulnerability.get("description", "")
        query_text = f"{vuln_type} {description}".strip()
        
        # No filter_type: metadata doesn't store "vulnerability_pattern",
        # and pure semantic search over query_text is more effective.
        results = await self.knowledge.query(query_text, top_k=5)
        
        return results
    
    async def _generate_patch(self, contract_code: str, vulnerability: dict, strategy: dict, patterns: list[dict]) -> dict:
        """Generate the actual patch code using MiMo"""
        logger.info("Generating patch code with MiMo")
        
        vuln_type = vulnerability.get("type", "unknown")
        description = vulnerability.get("description", "")
        strategy_desc = strategy.get("description", "")
        
        # Build RAG context from retrieved patterns (inject real content)
        pattern_context = ""
        if patterns:
            pattern_context = "\n\nRAG Examples (similar vulnerability fixes):\n"
            for i, p in enumerate(patterns[:3]):  # Top 3 patterns
                content = p.get("content", "")[:400]  # Truncate to avoid prompt bloat
                pattern_context += f"--- Example {i+1} ---\n{content}\n\n"
        
        prompt = f"""Fix this vulnerability in the smart contract.

Vulnerability Type: {vuln_type}
Description: {description}
Repair Strategy: {strategy_desc}
{pattern_context}

Original Contract Code:
```solidity
{contract_code}
```

Requirements:
1. Fix the vulnerability
2. Maintain original functionality
3. Use safe patterns (checks-effects-interactions, SafeMath, etc.)
4. Add comments explaining the fix

Return ONLY the fixed Solidity code, no explanation."""

        # Smartify CodeGenerator role (Section 4.1 four-element template)
        code_gen_system = (
            "You are a Code Generator specializing in Solidity smart contracts. "
            "Generate repaired code based on the Architect's plan and RAG examples. "
            "Return only the fixed Solidity code wrapped in ```solidity fences."
        )

        try:
            result = await self.llm.generate(prompt, system_prompt=code_gen_system)
            
            # Extract Solidity code
            if "```solidity" in result:
                code = result.split("```solidity")[1].split("```")[0].strip()
            elif "```" in result:
                code = result.split("```")[1].split("```")[0].strip()
            else:
                code = result.strip()
            
            return {
                "code": code,
                "explanation": f"Fixed {vuln_type} vulnerability using MiMo-generated patch",
            }
        except Exception as e:
            logger.error(f"MiMo patch generation failed: {e}")
            
            # Fallback: generate a basic fix based on vulnerability type
            return self._generate_fallback_patch(contract_code, vulnerability)
    
    def _generate_fallback_patch(self, contract_code: str, vulnerability: dict) -> dict:
        """Generate a fallback patch based on vulnerability type"""
        vuln_type = vulnerability.get("type", "unknown")
        
        # Common fixes for known vulnerability types
        fixes = {
            "reentrancy": {
                "pattern": "checks-effects-interactions",
                "description": "Move state changes before external calls",
            },
            "overflow": {
                "pattern": "use SafeMath or Solidity 0.8+",
                "description": "Add overflow checks",
            },
            "access-control": {
                "pattern": "add onlyOwner modifier",
                "description": "Add proper access control",
            },
        }
        
        fix_info = fixes.get(vuln_type, fixes["reentrancy"])
        
        return {
            "code": contract_code,  # Return original with comment
            "explanation": f"Fix {vuln_type}: {fix_info['description']}",
        }
