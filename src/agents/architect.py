"""
Architect Agent
Designs repair strategies for identified vulnerabilities
Reference: Smartify - Architect Agent
"""

import re
import json
from ..tools import ToolKit
from ..knowledge import KnowledgeBase
from ..utils.logger import get_logger
from ..utils.mimo_llm import get_mimo_llm

logger = get_logger(__name__)


class ArchitectAgent:
    """
    Architect Agent: Designs repair strategies for identified vulnerabilities.
    
    Responsibilities:
    1. Analyze vulnerability context
    2. Design repair strategy
    3. Consider trade-offs (security vs functionality)
    4. Provide step-by-step repair plan
    
    Reference: Smartify - Architect Agent
    """
    
    def __init__(self, tools: ToolKit, knowledge: KnowledgeBase):
        self.tools = tools
        self.knowledge = knowledge
        self.llm = get_mimo_llm()
    
    async def design_repair(self, contract_code: str, vulnerability: dict) -> dict:
        """
        Design a repair strategy for a vulnerability.
        
        Args:
            contract_code: The contract code
            vulnerability: Vulnerability details
            
        Returns:
            Repair strategy with steps and considerations
        """
        logger.info(f"Designing repair for {vulnerability.get('id', 'unknown')}")
        
        # Retrieve similar repairs from knowledge base
        similar_repairs = await self._retrieve_similar_repairs(vulnerability)
        
        # Analyze vulnerability context
        context = await self._analyze_context(contract_code, vulnerability)
        
        # Design strategy
        strategy = await self._design_strategy(contract_code, vulnerability, context, similar_repairs)
        
        return {
            "vulnerability_id": vulnerability.get("id", "unknown"),
            "strategy": strategy.get("description", ""),
            "steps": strategy.get("steps", []),
            "considerations": strategy.get("considerations", []),
            "similar_repairs": similar_repairs,
            "plan": strategy.get("description", ""),
            "root_cause": strategy.get("root_cause", ""),
            "side_effects": strategy.get("side_effects", ""),
            "verification": strategy.get("verification", ""),
        }
    
    async def _retrieve_similar_repairs(self, vulnerability: dict) -> list[dict]:
        """Retrieve similar repairs from knowledge base using RAG."""
        logger.info("Retrieving similar repairs via RAG")
        
        vuln_type = vulnerability.get("type", "unknown")
        description = vulnerability.get("description", "")
        query_text = f"{vuln_type} {description}".strip()
        results = await self.knowledge.query(query_text, top_k=5)
        
        return results
    
    async def _analyze_context(self, contract_code: str, vulnerability: dict) -> dict:
        """Analyze the context of a vulnerability"""
        logger.info("Analyzing vulnerability context")
        
        # Extract relevant code sections
        code_sections = self._extract_code_sections(contract_code, vulnerability)
        
        # Analyze dependencies
        dependencies = self._analyze_dependencies(contract_code, vulnerability)
        
        return {
            "code_sections": code_sections,
            "dependencies": dependencies,
        }
    
    async def _design_strategy(self, contract_code: str, vulnerability: dict, context: dict, similar_repairs: list[dict]) -> dict:
        """Design the repair strategy using MiMo's generate() method.
        
        Uses the Smartify Architect role to produce a structured repair plan
        with root cause analysis, required changes, side effects, and verification.
        """
        logger.info("Designing repair strategy with MiMo (Smartify Architect role)")
        
        vuln_type = vulnerability.get("type", "unknown")
        severity = vulnerability.get("severity", "unknown")
        location = vulnerability.get("location", "unknown")
        description = vulnerability.get("description", "")
        
        # Build RAG context from similar repairs
        repair_context = ""
        if similar_repairs:
            repair_context = "\n\nRelevant knowledge from similar fixes:\n"
            for repair in similar_repairs[:3]:
                content = repair.get("content", "")
                metadata = repair.get("metadata", {})
                source = metadata.get("vuln_category", metadata.get("source_path", "unknown"))
                repair_context += f"- [{source}] {content[:300]}\n"
        
        # Build context from code sections
        code_context = ""
        if context.get("code_sections"):
            code_context = "\n\nRelevant code sections:\n" + "\n---\n".join(context["code_sections"][:5])
        
        # Build context from dependencies
        dep_context = ""
        if context.get("dependencies"):
            dep_context = "\n\nDependencies: " + ", ".join(context["dependencies"][:10])
        
        system_prompt = (
            "You are an Architect specializing in Solidity smart contracts. "
            "Your role is to design high-level repair plans for identified vulnerabilities. "
            "You analyze root causes, specify required code changes, assess side effects, "
            "and propose verification strategies. Be precise and actionable."
        )
        
        prompt = f"""Create a high-level repair plan for the following vulnerability.

Vulnerability Report:
- Type: {vuln_type}
- Severity: {severity}
- Location: {location}
- Description: {description}

Contract Code:
```solidity
{contract_code[:3000]}
```
{code_context}{dep_context}{repair_context}

Instruction: Based on the vulnerability report and context above, develop a structured repair plan. Output a JSON object with these four fields:
1. "root_cause": Root cause analysis explaining why this vulnerability exists
2. "required_changes": List of specific code changes needed (mention functions/lines)
3. "side_effects": List of potential side effects or risks from the fix
4. "verification": Verification strategy to confirm the fix works
5. "description": Brief one-line strategy summary
6. "steps": List of concrete repair steps
7. "considerations": List of important implementation considerations

Return ONLY valid JSON."""

        try:
            result = await self.llm.generate(prompt, system_prompt=system_prompt, max_tokens=1024)
            
            # Try to parse JSON response
            try:
                if "```json" in result:
                    json_str = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    json_str = result.split("```")[1].split("```")[0]
                else:
                    json_str = result
                
                strategy = json.loads(json_str.strip())
                return strategy
            except json.JSONDecodeError:
                # If not valid JSON, parse text plan into structured form
                return self._parse_text_plan(result, vuln_type)
                
        except Exception as e:
            logger.error(f"MiMo strategy design failed: {e}")
            
            # Fallback strategy
            return self._get_fallback_strategy(vuln_type)
    
    def _parse_text_plan(self, text: str, vuln_type: str) -> dict:
        """Parse a text-based repair plan into structured format."""
        steps = []
        considerations = []
        root_cause = ""
        side_effects = ""
        verification = ""
        
        # Extract sections by common headings
        current_section = None
        for line in text.split("\n"):
            line_lower = line.strip().lower()
            if "root cause" in line_lower:
                current_section = "root_cause"
                continue
            elif "code change" in line_lower or "required change" in line_lower:
                current_section = "changes"
                continue
            elif "side effect" in line_lower or "potential risk" in line_lower:
                current_section = "side_effects"
                continue
            elif "verification" in line_lower or "test" in line_lower:
                current_section = "verification"
                continue
            
            stripped = line.strip()
            if not stripped:
                continue
            
            # Numbered or bulleted items
            is_list_item = bool(re.match(r'^\d+[.)\-]|^[-*•]', stripped))
            clean_item = re.sub(r'^\d+[.)\-]\s*|^[-*•]\s*', '', stripped).strip()
            
            if current_section == "root_cause" and clean_item:
                root_cause += clean_item + " "
            elif current_section == "changes" and is_list_item and clean_item:
                steps.append(clean_item)
            elif current_section == "changes" and clean_item and not steps:
                steps.append(clean_item)
            elif current_section == "side_effects" and clean_item:
                side_effects += clean_item + " " if not side_effects else "; " + clean_item
            elif current_section == "verification" and is_list_item and clean_item:
                verification += clean_item + "; " if not verification else clean_item + "; "
            elif current_section is None and is_list_item and clean_item:
                steps.append(clean_item)
        
        # If no steps extracted, use the whole text to generate basic steps
        if not steps:
            steps = [
                "Analyze root cause of " + vuln_type + " vulnerability",
                "Implement targeted fix based on analysis",
                "Verify fix does not break existing functionality",
            ]
        
        return {
            "description": text.split("\n")[0][:200] if text else f"Fix {vuln_type} vulnerability",
            "root_cause": root_cause.strip(),
            "required_changes": steps,
            "side_effects": side_effects.strip(),
            "verification": verification.strip(),
            "steps": steps,
            "considerations": [f"Ensure fix for {vuln_type} doesn't introduce regressions", "Consider gas optimization"],
        }
    
    def _extract_code_sections(self, contract_code: str, vulnerability: dict) -> list[str]:
        """
        Extract relevant code sections based on vulnerability location.
        
        Reference: Smartify - code section extraction
        """
        location = vulnerability.get("location", "")
        
        if not location:
            # Try to find by vulnerability type
            vuln_type = vulnerability.get("type", "unknown")
            patterns = {
                "reentrancy": [r'\.call\{', r'\.transfer\(', r'\.send\('],
                "overflow": [r'\+', r'\-', r'\*', r'uint'],
                "access-control": [r'onlyOwner', r'require\(', r'modifier'],
            }
            
            search_patterns = patterns.get(vuln_type, [r'function\s+\w+'])
        else:
            # Parse location to get line number
            line_match = re.search(r'line\s*(\d+)', location)
            if line_match:
                line_num = int(line_match.group(1))
                lines = contract_code.split('\n')
                start = max(0, line_num - 5)
                end = min(len(lines), line_num + 5)
                return ["\n".join(lines[start:end])]
            
            search_patterns = [r'function\s+\w+']
        
        # Search for relevant code sections
        sections = []
        lines = contract_code.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in search_patterns:
                if re.search(pattern, line):
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    sections.append("\n".join(lines[start:end]))
                    break
        
        return sections[:5]  # Limit to 5 sections
    
    def _analyze_dependencies(self, contract_code: str, vulnerability: dict) -> list[str]:
        """
        Analyze dependencies of the vulnerable code.
        
        Reference: Smartify - dependency analysis
        """
        dependencies = []
        
        # Find imports
        import_pattern = r'import\s+["\']([^"\']+)["\']'
        imports = re.findall(import_pattern, contract_code)
        dependencies.extend(imports)
        
        # Find contract inheritance
        inherit_pattern = r'contract\s+\w+\s+is\s+([^{]+)'
        inherits = re.findall(inherit_pattern, contract_code)
        for inherit in inherits:
            deps = [d.strip() for d in inherit.split(',')]
            dependencies.extend(deps)
        
        # Find external calls
        call_pattern = r'\.\w+\('
        calls = re.findall(call_pattern, contract_code)
        dependencies.extend([c.strip('.') for c in calls[:10]])
        
        return list(set(dependencies))
    
    def _get_fallback_strategy(self, vuln_type: str) -> dict:
        """Get fallback strategy based on vulnerability type"""
        strategies = {
            "reentrancy": {
                "description": "Apply checks-effects-interactions pattern",
                "steps": [
                    "Move state changes before external calls",
                    "Add reentrancy guard modifier",
                    "Use OpenZeppelin's ReentrancyGuard",
                ],
                "considerations": [
                    "Ensure all state changes happen before external calls",
                    "Consider using ReentrancyGuard from OpenZeppelin",
                    "Test with various attack scenarios",
                ],
            },
            "overflow": {
                "description": "Add overflow protection",
                "steps": [
                    "Use Solidity 0.8+ which has built-in overflow checks",
                    "Or use SafeMath library for older versions",
                    "Add explicit overflow checks where needed",
                ],
                "considerations": [
                    "Solidity 0.8+ automatically reverts on overflow",
                    "Consider gas implications of SafeMath",
                    "Test edge cases",
                ],
            },
            "access-control": {
                "description": "Add proper access control",
                "steps": [
                    "Add onlyOwner modifier",
                    "Use OpenZeppelin's Ownable",
                    "Add role-based access control if needed",
                ],
                "considerations": [
                    "Ensure owner can't be changed arbitrarily",
                    "Consider multi-sig for critical operations",
                    "Document access control requirements",
                ],
            },
        }
        
        return strategies.get(vuln_type, {
            "description": f"Fix {vuln_type} vulnerability",
            "steps": [
                "Analyze the vulnerability",
                "Design a fix",
                "Implement the fix",
                "Test the fix",
            ],
            "considerations": [
                "Ensure the fix doesn't introduce new issues",
                "Maintain backward compatibility",
                "Consider gas optimization",
            ],
        })
