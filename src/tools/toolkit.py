"""
ToolKit: Unified interface for all domain-specific tools
"""

from .source_fetcher import SourceCodeFetcher
from .state_reader import StateReaderTool
from .code_sanitizer import CodeSanitizer
from .concrete_execution import ConcreteExecutionTool
from .revenue_normalizer import RevenueNormalizerTool
from .slither_tool import SlitherTool
from .aderyn_tool import AderynTool
from .constructor_param import ConstructorParameterTool


class ToolKit:
    """
    Unified interface for all domain-specific tools.
    
    Tools:
    1. source_fetcher: Fetch contract source code
    2. state_reader: Read contract state
    3. code_sanitizer: Sanitize code
    4. concrete_execution: Execute contracts
    5. revenue_normalizer: Normalize revenue
    6. slither: Static analysis
    7. constructor_param: Decode constructor parameters
    """
    
    def __init__(self):
        self.source_fetcher = SourceCodeFetcher()
        self.state_reader = StateReaderTool()
        self.code_sanitizer = CodeSanitizer()
        self.concrete_execution = ConcreteExecutionTool()
        self.revenue_normalizer = RevenueNormalizerTool()
        self.slither = SlitherTool()
        self.aderyn = AderynTool()
        self.constructor_param = ConstructorParameterTool()
