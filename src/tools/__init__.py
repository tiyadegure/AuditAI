"""
Domain-Specific Tools for Smart Contract Audit
Based on A1's six tools architecture
"""

from .toolkit import ToolKit
from .source_fetcher import SourceCodeFetcher
from .state_reader import StateReaderTool
from .code_sanitizer import CodeSanitizer
from .concrete_execution import ConcreteExecutionTool
from .revenue_normalizer import RevenueNormalizerTool
from .slither_tool import SlitherTool
from .aderyn_tool import AderynTool

__all__ = [
    "ToolKit",
    "SourceCodeFetcher",
    "StateReaderTool",
    "CodeSanitizer",
    "ConcreteExecutionTool",
    "RevenueNormalizerTool",
    "SlitherTool",
    "AderynTool",
]
