"""
Tests for classifier module.

Tests the Classifier class which determines final risk classification
for folders based on identification results and AI analysis.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from config import Config
from modules.classifier import Classifier
from modules.models import (
    ScanResult,
    IdentificationResult,
    ClassificationResult,
    AIAnalysisResult,
    RiskLevel,
    ProgramStatus,
    SourceType,
)
from modules.rule_loader import RuleLoader


class TestClassifierInit:
    """Test Classifier initialization."""

    def test_init_with_config_only(self):
        """Test initialization with config only."""
        config = Config()
        classifier = Classifier(config)

        assert classifier.config is config
        assert classifier.ai_analyzer is None
        assert classifier.rule_loader is not None

    def test_init_with_ai_analyzer(self):
        """Test initialization with AI analyzer."""
        config = Config()
        mock_ai = MagicMock()
        classifier = Classifier(config, ai_analyzer=mock_ai)

        assert classifier.config is config
        assert classifier.ai_analyzer is mock_ai

    def test_init_with_custom_rule_loader(self):
        """Test that rule_loader is initialized."""
        config = Config()
        classifier = Classifier(config)

        assert isinstance(classifier.rule_loader, RuleLoader)


class TestClassifySafeFolder:
    """Test classification of safe folders."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    @pytest.fixture
    def scan_result(self):
        """Create a sample scan result."""
        return ScanResult(
            path="C:/Users/Test/AppData/Local/Temp/cache",
            name="cache",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

    def test_classify_safe_folder_returns_safe(self, classifier, scan_result):
        """Test that a folder identified as SAFE returns SAFE classification."""
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Temp Files",
            source_type=SourceType.SYSTEM,
            confidence=0.95,
            risk_level=RiskLevel.SAFE,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.SAFE
        assert result.selected is True
        assert result.path == scan_result.path
        assert result.source_name == "Temp Files"

    def test_classify_safe_folder_high_confidence(self, classifier, scan_result):
        """Test that safe folder with high confidence is selected."""
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Cache",
            confidence=0.99,
            risk_level=RiskLevel.SAFE,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.is_safe is True
        assert result.selected is True


class TestClassifyCautionFolder:
    """Test classification of caution folders."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    def test_classify_running_program_is_caution(self, classifier):
        """Test that a running program folder is classified as CAUTION."""
        scan_result = ScanResult(
            path="C:/Program Files/Steam",
            name="Steam",
            size_bytes=1024 * 1024 * 1024,
            file_count=100,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Steam",
            source_type=SourceType.GAME,
            confidence=0.9,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.RUNNING,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.CAUTION
        assert result.selected is False

    def test_classify_caution_pattern_is_caution(self, classifier):
        """Test that a caution pattern match is classified as CAUTION."""
        scan_result = ScanResult(
            path="C:/Users/Test/Documents",
            name="Documents",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Documents",
            confidence=0.7,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.UNKNOWN,
        )

        # Documents is a protected folder in caution_rules
        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.CAUTION


class TestClassifySuggestFolder:
    """Test classification of suggest folders."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    def test_classify_uninstalled_program_is_suggest(self, classifier):
        """Test that an uninstalled program folder is classified as SUGGEST."""
        scan_result = ScanResult(
            path="C:/Program Files/OldApp",
            name="OldApp",
            size_bytes=1024 * 1024 * 100,
            file_count=50,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="OldApp",
            confidence=0.85,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.UNINSTALLED,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.SUGGEST
        assert result.selected is True

    def test_classify_suggest_folder_selected(self, classifier):
        """Test that SUGGEST folders are selected by default."""
        scan_result = ScanResult(
            path="C:/Games/OldGame",
            name="OldGame",
            size_bytes=1024 * 1024 * 500,
            file_count=200,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="OldGame",
            confidence=0.75,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.PORTABLE_GONE,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.is_suggest is True
        assert result.selected is True


class TestClassifyWithAI:
    """Test classification with AI assistance."""

    @pytest.fixture
    def config_with_ai(self):
        """Create a config with AI enabled."""
        config = Config()
        config.ai_enabled = True
        config.ai_trigger_confidence = 0.6
        return config

    @pytest.fixture
    def mock_ai_analyzer(self):
        """Create a mock AI analyzer."""
        ai = MagicMock()
        ai.analyze.return_value = AIAnalysisResult(
            suggestion="can_delete",
            confidence=0.8,
            reason="This is a cache folder that can be safely deleted",
            risk_points=[],
        )
        return ai

    def test_classify_calls_ai_when_confidence_low(
        self, config_with_ai, mock_ai_analyzer
    ):
        """Test that AI is called when confidence is below threshold."""
        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai_analyzer)

        scan_result = ScanResult(
            path="C:/Users/Test/UnknownFolder",
            name="UnknownFolder",
            size_bytes=1024 * 1024 * 50,
            file_count=30,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Unknown",
            confidence=0.4,  # Below threshold
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        # AI should have been called
        mock_ai_analyzer.analyze.assert_called_once()
        assert result.ai_result is not None

    def test_classify_uses_ai_result_for_suggestion(
        self, config_with_ai, mock_ai_analyzer
    ):
        """Test that AI result affects classification."""
        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai_analyzer)

        scan_result = ScanResult(
            path="C:/Users/Test/UnknownFolder",
            name="UnknownFolder",
            size_bytes=1024 * 1024 * 50,
            file_count=30,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Unknown",
            confidence=0.4,  # Below threshold
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.ai_result.suggestion == "can_delete"
        # Should be SUGGEST based on AI's can_delete recommendation
        assert result.risk_level == RiskLevel.SUGGEST

    def test_classify_ai_says_caution(self, config_with_ai):
        """Test classification when AI returns caution."""
        mock_ai = MagicMock()
        mock_ai.analyze.return_value = AIAnalysisResult(
            suggestion="caution",
            confidence=0.9,
            reason="This folder contains user data",
            risk_points=["User data detected"],
        )

        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai)

        scan_result = ScanResult(
            path="C:/Users/Test/ImportantData",
            name="ImportantData",
            size_bytes=1024 * 1024 * 100,
            file_count=500,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Important Data",
            confidence=0.3,
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.CAUTION
        assert result.selected is False

    def test_classify_no_ai_when_high_confidence(self, config_with_ai, mock_ai_analyzer):
        """Test that AI is not called when confidence is high."""
        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai_analyzer)

        scan_result = ScanResult(
            path="C:/Users/Test/AppData/Local/Temp",
            name="Temp",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Temp Files",
            confidence=0.95,  # High confidence
            risk_level=RiskLevel.SAFE,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        # AI should not be called for high confidence SAFE results
        mock_ai_analyzer.analyze.assert_not_called()
        assert result.ai_result is None

    def test_classify_ai_disabled_no_call(self, mock_ai_analyzer):
        """Test that AI is not called when disabled."""
        config = Config()
        config.ai_enabled = False
        config.ai_trigger_confidence = 0.6

        classifier = Classifier(config, ai_analyzer=mock_ai_analyzer)

        scan_result = ScanResult(
            path="C:/Users/Test/UnknownFolder",
            name="UnknownFolder",
            size_bytes=1024 * 1024 * 50,
            file_count=30,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path=scan_result.path,
            source_name="Unknown",
            confidence=0.3,  # Low confidence
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        mock_ai_analyzer.analyze.assert_not_called()


class TestClassifyBatch:
    """Test batch classification."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample scan and identification results."""
        scan_results = [
            ScanResult(
                path="C:/Temp/cache1",
                name="cache1",
                size_bytes=1024 * 1024,
                file_count=10,
                last_access=datetime.now(),
            ),
            ScanResult(
                path="C:/Program Files/Steam",
                name="Steam",
                size_bytes=1024 * 1024 * 1024,
                file_count=100,
                last_access=datetime.now(),
            ),
            ScanResult(
                path="C:/Games/OldGame",
                name="OldGame",
                size_bytes=1024 * 1024 * 500,
                file_count=200,
                last_access=datetime.now(),
            ),
        ]

        id_results = [
            IdentificationResult(
                path="C:/Temp/cache1",
                source_name="Cache",
                confidence=0.9,
                risk_level=RiskLevel.SAFE,
                program_status=ProgramStatus.UNKNOWN,
            ),
            IdentificationResult(
                path="C:/Program Files/Steam",
                source_name="Steam",
                confidence=0.95,
                risk_level=RiskLevel.SUGGEST,
                program_status=ProgramStatus.RUNNING,
            ),
            IdentificationResult(
                path="C:/Games/OldGame",
                source_name="OldGame",
                confidence=0.85,
                risk_level=RiskLevel.SUGGEST,
                program_status=ProgramStatus.UNINSTALLED,
            ),
        ]

        return scan_results, id_results

    def test_classify_batch_returns_list(self, classifier, sample_data):
        """Test that classify_batch returns a list."""
        scan_results, id_results = sample_data

        results = classifier.classify_batch(scan_results, id_results)

        assert isinstance(results, list)
        assert len(results) == 3

    def test_classify_batch_correct_order(self, classifier, sample_data):
        """Test that batch results are in correct order."""
        scan_results, id_results = sample_data

        results = classifier.classify_batch(scan_results, id_results)

        assert results[0].path == "C:/Temp/cache1"
        assert results[1].path == "C:/Program Files/Steam"
        assert results[2].path == "C:/Games/OldGame"

    def test_classify_batch_correct_classifications(self, classifier, sample_data):
        """Test that batch classifications are correct."""
        scan_results, id_results = sample_data

        results = classifier.classify_batch(scan_results, id_results)

        # First: SAFE (safe folder)
        assert results[0].risk_level == RiskLevel.SAFE
        assert results[0].selected is True

        # Second: CAUTION (running program)
        assert results[1].risk_level == RiskLevel.CAUTION
        assert results[1].selected is False

        # Third: SUGGEST (uninstalled program)
        assert results[2].risk_level == RiskLevel.SUGGEST
        assert results[2].selected is True

    def test_classify_batch_empty_lists(self, classifier):
        """Test batch classification with empty lists."""
        results = classifier.classify_batch([], [])

        assert results == []

    def test_classify_batch_mismatched_lengths(self, classifier):
        """Test batch classification with mismatched list lengths."""
        scan_results = [
            ScanResult(
                path="C:/Test1",
                name="Test1",
                size_bytes=1024,
                file_count=1,
                last_access=datetime.now(),
            ),
        ]
        id_results = [
            IdentificationResult(
                path="C:/Test1",
                source_name="Test1",
                confidence=0.9,
                risk_level=RiskLevel.SAFE,
            ),
            IdentificationResult(
                path="C:/Test2",
                source_name="Test2",
                confidence=0.8,
                risk_level=RiskLevel.SAFE,
            ),
        ]

        # Should raise ValueError for mismatched lengths
        with pytest.raises(ValueError):
            classifier.classify_batch(scan_results, id_results)


class TestClassificationResultProperties:
    """Test ClassificationResult properties."""

    def test_is_safe_property(self):
        """Test is_safe property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SAFE,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_safe is True
        assert result.is_suggest is False
        assert result.is_caution is False

    def test_is_suggest_property(self):
        """Test is_suggest property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SUGGEST,
            source_name="Test",
            confidence=0.8,
            evidence_chain=[],
        )
        assert result.is_safe is False
        assert result.is_suggest is True
        assert result.is_caution is False

    def test_is_caution_property(self):
        """Test is_caution property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.CAUTION,
            source_name="Test",
            confidence=0.7,
            evidence_chain=[],
        )
        assert result.is_safe is False
        assert result.is_suggest is False
        assert result.is_caution is True


class TestEvidenceChain:
    """Test evidence chain handling."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    def test_evidence_chain_preserved(self, classifier):
        """Test that evidence chain from identification is preserved."""
        scan_result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Test",
            source_name="Test",
            confidence=0.9,
            risk_level=RiskLevel.SAFE,
            evidence_chain=["Evidence 1", "Evidence 2"],
        )

        result = classifier.classify(scan_result, id_result)

        assert "Evidence 1" in result.evidence_chain
        assert "Evidence 2" in result.evidence_chain

    def test_evidence_chain_adds_classification_info(self, classifier):
        """Test that classification adds to evidence chain."""
        scan_result = ScanResult(
            path="C:/Program Files/TestApp",
            name="TestApp",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Program Files/TestApp",
            source_name="TestApp",
            confidence=0.9,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.RUNNING,
        )

        result = classifier.classify(scan_result, id_result)

        # Should have added evidence about running status
        assert any("running" in e.lower() for e in result.evidence_chain)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    def test_classify_with_empty_evidence_chain(self, classifier):
        """Test classification with empty evidence chain."""
        scan_result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Test",
            source_name="Test",
            confidence=0.9,
            risk_level=RiskLevel.SAFE,
            evidence_chain=[],
        )

        result = classifier.classify(scan_result, id_result)

        assert isinstance(result.evidence_chain, list)

    def test_classify_with_unknown_program_status(self, classifier):
        """Test classification with unknown program status."""
        scan_result = ScanResult(
            path="C:/Unknown",
            name="Unknown",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Unknown",
            source_name="Unknown",
            confidence=0.5,
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        result = classifier.classify(scan_result, id_result)

        # Unknown status should default to CAUTION from id_result
        assert result.risk_level == RiskLevel.CAUTION
        assert result.selected is False

    def test_classify_with_ai_exception(self):
        """Test that AI exceptions are handled gracefully."""
        config = Config()
        config.ai_enabled = True
        config.ai_trigger_confidence = 0.6

        mock_ai = MagicMock()
        mock_ai.analyze.side_effect = Exception("AI service unavailable")

        classifier = Classifier(config, ai_analyzer=mock_ai)

        scan_result = ScanResult(
            path="C:/Unknown",
            name="Unknown",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Unknown",
            source_name="Unknown",
            confidence=0.3,
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.UNKNOWN,
        )

        # Should not raise, should fall back to default classification
        result = classifier.classify(scan_result, id_result)

        assert result is not None
        assert result.risk_level == RiskLevel.CAUTION


class TestAIResultHandling:
    """Test handling of AI analysis results."""

    @pytest.fixture
    def config_with_ai(self):
        """Create a config with AI enabled."""
        config = Config()
        config.ai_enabled = True
        config.ai_trigger_confidence = 0.6
        return config

    def test_ai_result_can_delete_sets_suggest(self, config_with_ai):
        """Test that 'can_delete' AI result sets SUGGEST."""
        mock_ai = MagicMock()
        mock_ai.analyze.return_value = AIAnalysisResult(
            suggestion="can_delete",
            confidence=0.8,
            reason="Safe to delete",
        )

        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai)

        scan_result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Test",
            source_name="Test",
            confidence=0.3,
            risk_level=RiskLevel.CAUTION,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.SUGGEST
        assert result.selected is True

    def test_ai_result_keep_sets_caution(self, config_with_ai):
        """Test that 'keep' AI result sets CAUTION."""
        mock_ai = MagicMock()
        mock_ai.analyze.return_value = AIAnalysisResult(
            suggestion="keep",
            confidence=0.9,
            reason="Important folder",
        )

        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai)

        scan_result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Test",
            source_name="Test",
            confidence=0.3,
            risk_level=RiskLevel.CAUTION,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.CAUTION
        assert result.selected is False

    def test_ai_result_caution_sets_caution(self, config_with_ai):
        """Test that 'caution' AI result sets CAUTION."""
        mock_ai = MagicMock()
        mock_ai.analyze.return_value = AIAnalysisResult(
            suggestion="caution",
            confidence=0.7,
            reason="May contain important data",
        )

        classifier = Classifier(config_with_ai, ai_analyzer=mock_ai)

        scan_result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Test",
            source_name="Test",
            confidence=0.3,
            risk_level=RiskLevel.CAUTION,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.risk_level == RiskLevel.CAUTION
        assert result.selected is False


class TestSelectionLogic:
    """Test the selection logic for folders."""

    @pytest.fixture
    def classifier(self):
        """Create a classifier instance for testing."""
        config = Config()
        return Classifier(config)

    def test_safe_folders_are_selected(self, classifier):
        """Test that SAFE folders are selected by default."""
        scan_result = ScanResult(
            path="C:/Temp",
            name="Temp",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Temp",
            source_name="Temp",
            confidence=0.95,
            risk_level=RiskLevel.SAFE,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.selected is True

    def test_suggest_folders_are_selected(self, classifier):
        """Test that SUGGEST folders are selected by default."""
        scan_result = ScanResult(
            path="C:/OldApp",
            name="OldApp",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/OldApp",
            source_name="OldApp",
            confidence=0.85,
            risk_level=RiskLevel.SUGGEST,
            program_status=ProgramStatus.UNINSTALLED,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.selected is True

    def test_caution_folders_are_not_selected(self, classifier):
        """Test that CAUTION folders are not selected by default."""
        scan_result = ScanResult(
            path="C:/Program Files/App",
            name="App",
            size_bytes=1024,
            file_count=1,
            last_access=datetime.now(),
        )
        id_result = IdentificationResult(
            path="C:/Program Files/App",
            source_name="App",
            confidence=0.9,
            risk_level=RiskLevel.CAUTION,
            program_status=ProgramStatus.RUNNING,
        )

        result = classifier.classify(scan_result, id_result)

        assert result.selected is False
