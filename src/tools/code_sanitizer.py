"""
Code Sanitizer Tool
Removes non-essential elements from code
Reference: A1 paper - Code Sanitizer Tool
"""

import re
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CodeSanitizer:
    """
    Code Sanitizer: Removes non-essential elements from code.
    
    Features:
    1. Remove comments
    2. Remove unused imports
    3. Remove library dependencies
    4. Focus on executable logic
    
    Reference: A1 paper Section 3 - Code Sanitizer Tool
    """
    
    def __init__(self, remove_comments: bool = True, remove_unused: bool = True):
        self.remove_comments = remove_comments
        self.remove_unused = remove_unused
    
    def sanitize(self, code: str) -> str:
        """
        Sanitize code.
        
        Args:
            code: Original code
            
        Returns:
            Sanitized code
        """
        logger.info("Sanitizing code")
        
        result = code
        
        if self.remove_comments:
            result = self._remove_comments(result)
        
        if self.remove_unused:
            result = self._remove_unused_imports(result)
        
        # Remove empty lines
        result = self._remove_empty_lines(result)
        
        return result
    
    def _remove_comments(self, code: str) -> str:
        """Remove comments from code"""
        # Remove single-line comments (but not URLs)
        code = re.sub(r'(?<!:)//.*$', '', code, flags=re.MULTILINE)
        
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        return code
    
    def _remove_unused_imports(self, code: str) -> str:
        """Remove unused imports"""
        lines = code.split('\n')
        result_lines = []
        imports = []
        
        # First pass: collect imports and their symbols
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                result_lines.append(line)
                continue
            
            # Check if it's an import line
            if stripped.startswith('import ') or stripped.startswith('from '):
                imports.append(line)
                continue
            
            result_lines.append(line)
        
        # Second pass: check which imports are actually used
        code_body = '\n'.join(result_lines)
        
        used_imports = []
        for imp in imports:
            # Extract the imported symbol
            match = re.search(r'import\s+(\w+)', imp)
            if match:
                symbol = match.group(1)
                # Check if symbol is used in code body
                if re.search(r'\b' + re.escape(symbol) + r'\b', code_body):
                    used_imports.append(imp)
                else:
                    logger.debug(f"Removing unused import: {imp.strip()}")
            else:
                # Keep if we can't parse
                used_imports.append(imp)
        
        # Reconstruct code
        result = '\n'.join(used_imports) + '\n' + '\n'.join(result_lines)
        
        return result
    
    def _remove_empty_lines(self, code: str) -> str:
        """Remove excessive empty lines"""
        # Replace multiple empty lines with single empty line
        code = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
        
        return code.strip()
