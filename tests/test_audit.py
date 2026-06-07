"""
Tests for the AI Smart Contract Security Audit Agent
"""

import pytest
import asyncio
from pathlib import Path

from src.agents import AgentOrchestrator
from src.tools import ToolKit
from src.knowledge import KnowledgeBase


@pytest.fixture
def sample_contract():
    """Sample contract for testing"""
    return Path("data/contracts/VulnerableBank.sol").read_text()


@pytest.fixture
def orchestrator():
    """Agent orchestrator fixture"""
    return AgentOrchestrator()


@pytest.fixture
def toolkit():
    """ToolKit fixture"""
    return ToolKit()


@pytest.fixture
def knowledge_base():
    """Knowledge base fixture"""
    return KnowledgeBase()


class TestToolKit:
    """Tests for ToolKit"""
    
    def test_toolkit_initialization(self, toolkit):
        """Test toolkit initialization"""
        assert toolkit.source_fetcher is not None
        assert toolkit.state_reader is not None
        assert toolkit.code_sanitizer is not None
        assert toolkit.concrete_execution is not None
        assert toolkit.revenue_normalizer is not None
        assert toolkit.slither is not None


class TestSourceCodeFetcher:
    """Tests for SourceCodeFetcher"""
    
    def test_fetch_local_file(self, toolkit):
        """Test fetching from local file"""
        contract_path = "data/contracts/VulnerableBank.sol"
        code = toolkit.source_fetcher.fetch(contract_path)
        assert "contract VulnerableBank" in code
    
    def test_fetch_nonexistent_file(self, toolkit):
        """Test fetching nonexistent file"""
        with pytest.raises(ValueError):
            toolkit.source_fetcher.fetch("nonexistent.sol")


class TestCodeSanitizer:
    """Tests for CodeSanitizer"""
    
    def test_remove_comments(self, toolkit):
        """Test comment removal"""
        code = """
        // This is a comment
        contract Test {
            /* Multi-line
               comment */
            function foo() {}
        }
        """
        sanitized = toolkit.code_sanitizer.sanitize(code)
        assert "//" not in sanitized
        assert "/*" not in sanitized
        assert "contract Test" in sanitized


class TestSlitherTool:
    """Tests for SlitherTool"""
    
    def test_analyze_code(self, toolkit, sample_contract):
        """Test Slither analysis on code"""
        results = toolkit.slither.analyze_code(sample_contract)
        # Should find vulnerabilities
        assert isinstance(results, list)


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator"""
    
    @pytest.mark.asyncio
    async def test_detect(self, orchestrator):
        """Test vulnerability detection"""
        contract_path = "data/contracts/VulnerableBank.sol"
        vulnerabilities = await orchestrator.detect(contract_path)
        assert isinstance(vulnerabilities, list)


class TestKnowledgeBase:
    """Tests for KnowledgeBase"""
    
    def test_initialization(self, knowledge_base):
        """Test knowledge base initialization"""
        # Verify vector search flag is set (default False until initialize() is called)
        assert hasattr(knowledge_base, 'using_vector_search')
        assert knowledge_base.using_vector_search is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
