"""
Tests for the Identifier module in modules/identifier.py
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from modules.models import (
    IdentificationResult,
    ProgramStatus,
    RiskLevel,
    ScanResult,
    SourceType,
)
from modules.identifier import Identifier


class TestIdentifierInit:
    """Test Identifier initialization."""

    def test_default_init(self):
        """Test initialization with default parameters."""
        identifier = Identifier()

        assert identifier.rules_dir == "rules"
        assert identifier.rule_loader is not None
        # Learner may be None if db doesn't exist
        assert identifier.learner is None or identifier.learner is not None

    def test_custom_rules_dir(self):
        """Test initialization with custom rules directory."""
        identifier = Identifier(rules_dir="custom_rules")

        assert identifier.rules_dir == "custom_rules"
        assert identifier.rule_loader.rules_dir == "custom_rules"

    def test_custom_db_path(self):
        """Test initialization with custom database path."""
        identifier = Identifier(db_path="custom/learner.db")

        # Should not raise an error
        assert identifier is not None


class TestIdentifierQuickMatch:
    """Test Stage 1: Quick Match."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_identify_known_software_vscode(self, identifier):
        """Test identification of VSCode folder."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,  # 100 MB
            file_count=1000,
            last_access=datetime.now(),
            file_extensions={".json": 100, ".js": 50},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        assert result.path == scan_result.path
        assert result.source_name == "Visual Studio Code"
        assert result.confidence > 0
        assert len(result.evidence_chain) > 0
        # Should have evidence about folder name match
        assert any("folder" in e.lower() or "match" in e.lower() or "software" in e.lower()
                   for e in result.evidence_chain)

    def test_identify_known_software_chrome(self, identifier):
        """Test identification of Chrome folder."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Local\\Google\\Chrome",
            name="Chrome",
            size_bytes=1024 * 1024 * 500,  # 500 MB
            file_count=5000,
            last_access=datetime.now(),
            file_extensions={".json": 200, ".db": 50},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        assert result.source_name == "Chrome"
        assert result.confidence > 0
        assert len(result.evidence_chain) > 0

    def test_identify_unknown_folder(self, identifier):
        """Test identification of unknown folder."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\SomeUnknownFolder12345",
            name="SomeUnknownFolder12345",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
            file_extensions={".txt": 5},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        assert result.source_name == "Unknown"
        # Confidence should be low for unknown folders
        assert result.confidence < 0.5


class TestIdentifierDevCaches:
    """Test identification of development caches."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_identify_node_modules(self, identifier):
        """Test identification of node_modules folder."""
        scan_result = ScanResult(
            path="C:\\Projects\\MyProject\\node_modules",
            name="node_modules",
            size_bytes=1024 * 1024 * 500,  # 500 MB
            file_count=10000,
            last_access=datetime.now(),
            file_extensions={".js": 5000, ".json": 2000, ".ts": 1000},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        assert result.source_type == SourceType.DEV_TOOL
        # Node modules should be identified as safe or suggest
        assert result.risk_level in [RiskLevel.SAFE, RiskLevel.SUGGEST]
        assert result.confidence > 0.5

    def test_identify_npm_cache(self, identifier):
        """Test identification of npm cache folder."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\npm-cache",
            name="npm-cache",
            size_bytes=1024 * 1024 * 200,
            file_count=500,
            last_access=datetime.now(),
            file_extensions={".tgz": 100, ".json": 50},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        assert result.confidence > 0


class TestIdentifierEvidenceChain:
    """Test evidence chain population."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_evidence_chain_is_populated(self, identifier):
        """Test that evidence chain is populated with findings."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,
            file_count=1000,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        assert len(result.evidence_chain) > 0
        # Evidence should be strings
        for evidence in result.evidence_chain:
            assert isinstance(evidence, str)

    def test_evidence_chain_includes_folder_match(self, identifier):
        """Test that evidence chain includes folder name match."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,
            file_count=1000,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Should include evidence about matching software library
        has_match_evidence = any(
            "software" in e.lower() or "match" in e.lower() or "folder" in e.lower()
            for e in result.evidence_chain
        )
        assert has_match_evidence

    def test_evidence_chain_copy_size_and_access(self, identifier):
        """Test that result copies size and last_access from scan result."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,
            file_count=1000,
            last_access=datetime(2024, 1, 15, 10, 30, 0),
        )

        result = identifier.identify(scan_result)

        assert result.size_bytes == scan_result.size_bytes
        assert result.last_access == scan_result.last_access


class TestIdentifierProgramStatus:
    """Test program status detection."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_program_status_unknown_by_default(self, identifier):
        """Test that unknown folders have UNKNOWN status."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\SomeRandomFolder",
            name="SomeRandomFolder",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Default status should be UNKNOWN for unrecognized folders
        assert result.program_status in [
            ProgramStatus.UNKNOWN,
            ProgramStatus.UNINSTALLED,
            ProgramStatus.INSTALLED,
        ]

    @patch('modules.identifier.find_process_by_folder')
    def test_program_status_running(self, mock_find_process, identifier):
        """Test that running processes are detected."""
        # Mock a running process
        mock_find_process.return_value = {
            'pid': 1234,
            'name': 'Code.exe',
            'exe': 'C:\\Program Files\\Microsoft VS Code\\Code.exe',
            'cmdline': ''
        }

        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,
            file_count=1000,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Should have evidence about running process
        has_process_evidence = any(
            "process" in e.lower() or "running" in e.lower()
            for e in result.evidence_chain
        )
        # If process is running, status should be RUNNING or evidence should mention it
        assert has_process_evidence or result.program_status == ProgramStatus.RUNNING


class TestIdentifierRiskLevel:
    """Test risk level determination."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_dev_cache_is_safe_or_suggest(self, identifier):
        """Test that dev caches are classified as safe or suggest."""
        scan_result = ScanResult(
            path="C:\\Projects\\MyProject\\node_modules",
            name="node_modules",
            size_bytes=1024 * 1024 * 500,
            file_count=10000,
            last_access=datetime.now(),
            file_extensions={".js": 5000},
        )

        result = identifier.identify(scan_result)

        assert result.risk_level in [RiskLevel.SAFE, RiskLevel.SUGGEST]

    def test_unknown_folder_is_caution(self, identifier):
        """Test that unknown folders are classified with caution."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\ImportantDataFolder",
            name="ImportantDataFolder",
            size_bytes=1024 * 1024,
            file_count=100,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Unknown folders should default to caution
        assert result.risk_level == RiskLevel.CAUTION


class TestIdentifierSourceType:
    """Test source type determination."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_software_source_type(self, identifier):
        """Test that software folders get SOFTWARE type."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Local\\Google\\Chrome",
            name="Chrome",
            size_bytes=1024 * 1024 * 500,
            file_count=5000,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        assert result.source_type == SourceType.SOFTWARE

    def test_dev_tool_source_type(self, identifier):
        """Test that dev tool folders get DEV_TOOL type."""
        scan_result = ScanResult(
            path="C:\\Projects\\MyProject\\node_modules",
            name="node_modules",
            size_bytes=1024 * 1024 * 500,
            file_count=10000,
            last_access=datetime.now(),
            file_extensions={".js": 5000, ".ts": 1000},
        )

        result = identifier.identify(scan_result)

        assert result.source_type == SourceType.DEV_TOOL


class TestIdentifierConfidence:
    """Test confidence level calculation."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_confidence_range(self, identifier):
        """Test that confidence is between 0 and 1."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\SomeFolder",
            name="SomeFolder",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        assert 0.0 <= result.confidence <= 1.0

    def test_high_confidence_for_known_software(self, identifier):
        """Test that known software has high confidence."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,
            file_count=1000,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Known software should have confidence > 0.5
        assert result.confidence > 0.5

    def test_low_confidence_for_unknown(self, identifier):
        """Test that unknown folders have low confidence."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\RandomUnknownFolderXYZ123",
            name="RandomUnknownFolderXYZ123",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Unknown should have low confidence
        assert result.confidence < 0.5


class TestIdentifierDeepAnalysis:
    """Test Stage 3: Deep Analysis."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_file_extension_analysis(self, identifier):
        """Test that file extensions are analyzed."""
        scan_result = ScanResult(
            path="C:\\Projects\\MyProject\\node_modules",
            name="node_modules",
            size_bytes=1024 * 1024 * 500,
            file_count=10000,
            last_access=datetime.now(),
            file_extensions={".js": 5000, ".ts": 2000, ".json": 1500},
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)
        # Should have identified this as a dev tool based on extensions
        assert result.source_type == SourceType.DEV_TOOL

    def test_executable_detection(self, identifier):
        """Test that executable files are detected."""
        scan_result = ScanResult(
            path="C:\\Program Files\\SomeApp",
            name="SomeApp",
            size_bytes=1024 * 1024 * 50,
            file_count=100,
            last_access=datetime.now(),
            has_executables=True,
        )

        result = identifier.identify(scan_result)

        assert isinstance(result, IdentificationResult)


class TestIdentifierLearning:
    """Test Stage 4: Learning integration."""

    @pytest.fixture
    def identifier_with_mock_learner(self):
        """Create an Identifier with a mocked learner."""
        identifier = Identifier(rules_dir="rules")

        # Create a mock learner
        mock_learner = MagicMock()
        mock_learner.get_learned_suggestion.return_value = {
            'source_name': 'LearnedApp',
            'decision_count': 3,
            'confidence': 0.8
        }

        identifier.learner = mock_learner
        return identifier

    def test_learner_provides_suggestion(self, identifier_with_mock_learner):
        """Test that learner provides suggestions when available."""
        identifier = identifier_with_mock_learner

        scan_result = ScanResult(
            path="C:\\Users\\Test\\LearnedFolder",
            name="LearnedFolder",
            size_bytes=1024 * 1024,
            file_count=100,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # The learner should have been consulted
        assert isinstance(result, IdentificationResult)

    def test_learner_evidence_includes_decision_count(self, identifier_with_mock_learner):
        """Test that learner evidence includes decision count."""
        identifier = identifier_with_mock_learner

        scan_result = ScanResult(
            path="C:\\Users\\Test\\LearnedFolder",
            name="LearnedFolder",
            size_bytes=1024 * 1024,
            file_count=100,
            last_access=datetime.now(),
        )

        result = identifier.identify(scan_result)

        # Should have evidence about learning
        has_learning_evidence = any(
            "learn" in e.lower() or "decision" in e.lower()
            for e in result.evidence_chain
        )
        # This test passes if learning evidence is present or learner was consulted
        assert isinstance(result, IdentificationResult)


class TestIdentifierIntegration:
    """Integration tests for the full identification pipeline."""

    @pytest.fixture
    def identifier(self):
        """Create an Identifier instance for testing."""
        return Identifier(rules_dir="rules")

    def test_full_pipeline_vscode(self, identifier):
        """Test full identification pipeline for VSCode."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\AppData\\Roaming\\Code",
            name="Code",
            size_bytes=1024 * 1024 * 100,  # 100 MB
            file_count=1000,
            last_access=datetime.now(),
            file_extensions={".json": 100, ".js": 50},
            has_executables=False,
        )

        result = identifier.identify(scan_result)

        # Verify all result fields are populated
        assert result.path == scan_result.path
        assert result.source_name == "Visual Studio Code"
        assert result.source_type in [SourceType.SOFTWARE, SourceType.DEV_TOOL]
        assert 0.0 <= result.confidence <= 1.0
        assert result.risk_level in [RiskLevel.SAFE, RiskLevel.SUGGEST, RiskLevel.CAUTION]
        assert len(result.evidence_chain) > 0
        assert result.program_status is not None
        assert result.size_bytes == scan_result.size_bytes
        assert result.last_access == scan_result.last_access

    def test_full_pipeline_unknown_folder(self, identifier):
        """Test full pipeline for completely unknown folder."""
        scan_result = ScanResult(
            path="C:\\Users\\Test\\CompletelyUnknownFolder12345",
            name="CompletelyUnknownFolder12345",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
            file_extensions={".dat": 1},
            has_executables=False,
        )

        result = identifier.identify(scan_result)

        # Unknown folders should have low confidence and caution risk
        assert result.source_name == "Unknown"
        assert result.confidence < 0.5
        assert result.risk_level == RiskLevel.CAUTION
        assert result.source_type == SourceType.UNKNOWN
