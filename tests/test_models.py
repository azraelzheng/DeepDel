"""
Tests for data models in modules/models.py
"""
import pytest
from datetime import datetime, timedelta
from modules.models import (
    RiskLevel,
    ProgramStatus,
    SourceType,
    ScanResult,
    IdentificationResult,
    AIAnalysisResult,
    ClassificationResult,
)


class TestEnums:
    """Test enum definitions."""

    def test_risk_level_values(self):
        """Test RiskLevel enum has correct values."""
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.SUGGEST.value == "suggest"
        assert RiskLevel.CAUTION.value == "caution"

    def test_program_status_values(self):
        """Test ProgramStatus enum has correct values."""
        assert ProgramStatus.INSTALLED.value == "installed"
        assert ProgramStatus.RUNNING.value == "running"
        assert ProgramStatus.UNINSTALLED.value == "uninstalled"
        assert ProgramStatus.PORTABLE_GONE.value == "portable_gone"
        assert ProgramStatus.UNKNOWN.value == "unknown"

    def test_source_type_values(self):
        """Test SourceType enum has correct values."""
        assert SourceType.SOFTWARE.value == "software"
        assert SourceType.GAME.value == "game"
        assert SourceType.DEV_TOOL.value == "dev_tool"
        assert SourceType.SYSTEM.value == "system"
        assert SourceType.UNKNOWN.value == "unknown"


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_scan_result_creation(self):
        """Test basic ScanResult creation."""
        now = datetime.now()
        result = ScanResult(
            path="C:/Test/Path",
            name="TestFolder",
            size_bytes=1024 * 1024 * 100,  # 100 MB
            file_count=50,
            last_access=now,
            is_folder=True,
            file_extensions={".dll": 10, ".exe": 5},
            has_executables=True,
            folder_depth=3,
            created_time=now - timedelta(days=30),
        )

        assert result.path == "C:/Test/Path"
        assert result.name == "TestFolder"
        assert result.size_bytes == 104857600
        assert result.file_count == 50
        assert result.last_access == now
        assert result.is_folder is True
        assert result.file_extensions == {".dll": 10, ".exe": 5}
        assert result.has_executables is True
        assert result.folder_depth == 3
        assert result.created_time is not None

    def test_scan_result_defaults(self):
        """Test ScanResult default values."""
        now = datetime.now()
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024,
            file_count=1,
            last_access=now,
        )

        assert result.is_folder is True
        assert result.file_extensions == {}
        assert result.has_executables is False
        assert result.folder_depth == 0
        assert result.created_time is None

    def test_scan_result_size_mb(self):
        """Test size_mb property."""
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024 * 1024 * 50,  # 50 MB
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.size_mb == 50.0

    def test_scan_result_size_gb(self):
        """Test size_gb property."""
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024 * 1024 * 1024 * 2,  # 2 GB
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.size_gb == 2.0

    def test_scan_result_format_size(self):
        """Test format_size method."""
        # Test bytes
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=512,
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.format_size() == "512.00 B"

        # Test KB
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024 * 5,  # 5 KB
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.format_size() == "5.00 KB"

        # Test MB
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024 * 1024 * 100,  # 100 MB
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.format_size() == "100.00 MB"

        # Test GB
        result = ScanResult(
            path="C:/Test",
            name="Test",
            size_bytes=1024 * 1024 * 1024 * 5,  # 5 GB
            file_count=1,
            last_access=datetime.now(),
        )
        assert result.format_size() == "5.00 GB"


class TestIdentificationResult:
    """Test IdentificationResult dataclass."""

    def test_identification_result_defaults(self):
        """Test IdentificationResult default values."""
        result = IdentificationResult(path="C:/Test/Path")

        assert result.path == "C:/Test/Path"
        assert result.source_name == "Unknown"
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0
        assert result.risk_level == RiskLevel.CAUTION
        assert result.evidence_chain == []
        assert result.program_status == ProgramStatus.UNKNOWN
        assert result.size_bytes == 0
        assert result.last_access is None

    def test_identification_result_custom_values(self):
        """Test IdentificationResult with custom values."""
        now = datetime.now()
        result = IdentificationResult(
            path="C:/Test/Path",
            source_name="TestApp",
            source_type=SourceType.SOFTWARE,
            confidence=0.85,
            risk_level=RiskLevel.SUGGEST,
            evidence_chain=["Evidence 1", "Evidence 2"],
            program_status=ProgramStatus.INSTALLED,
            size_bytes=1024 * 1024,
            last_access=now,
        )

        assert result.path == "C:/Test/Path"
        assert result.source_name == "TestApp"
        assert result.source_type == SourceType.SOFTWARE
        assert result.confidence == 0.85
        assert result.risk_level == RiskLevel.SUGGEST
        assert result.evidence_chain == ["Evidence 1", "Evidence 2"]
        assert result.program_status == ProgramStatus.INSTALLED
        assert result.size_bytes == 1048576
        assert result.last_access == now

    def test_add_evidence(self):
        """Test add_evidence method."""
        result = IdentificationResult(path="C:/Test/Path")

        result.add_evidence("First evidence")
        assert "First evidence" in result.evidence_chain
        assert len(result.evidence_chain) == 1

        result.add_evidence("Second evidence")
        assert "Second evidence" in result.evidence_chain
        assert len(result.evidence_chain) == 2


class TestAIAnalysisResult:
    """Test AIAnalysisResult dataclass."""

    def test_ai_analysis_result_creation(self):
        """Test basic AIAnalysisResult creation."""
        result = AIAnalysisResult(
            suggestion="can_delete",
            confidence=0.95,
            reason="This is a cache folder that can be safely deleted.",
            risk_points=["May need to re-download some assets"],
        )

        assert result.suggestion == "can_delete"
        assert result.confidence == 0.95
        assert "cache folder" in result.reason
        assert len(result.risk_points) == 1

    def test_ai_analysis_result_defaults(self):
        """Test AIAnalysisResult default values."""
        result = AIAnalysisResult(
            suggestion="keep",
            confidence=0.5,
            reason="Cannot determine safely",
        )

        assert result.risk_points == []

    def test_ai_analysis_result_to_dict(self):
        """Test to_dict method."""
        result = AIAnalysisResult(
            suggestion="caution",
            confidence=0.75,
            reason="May contain user data",
            risk_points=["User config files", "Save games"],
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["suggestion"] == "caution"
        assert result_dict["confidence"] == 0.75
        assert result_dict["reason"] == "May contain user data"
        assert result_dict["risk_points"] == ["User config files", "Save games"]


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_classification_result_creation(self):
        """Test basic ClassificationResult creation."""
        ai_result = AIAnalysisResult(
            suggestion="can_delete",
            confidence=0.9,
            reason="Safe to delete",
        )
        result = ClassificationResult(
            path="C:/Test/Path",
            risk_level=RiskLevel.SAFE,
            source_name="TestApp",
            confidence=0.9,
            evidence_chain=["Evidence 1"],
            ai_result=ai_result,
            selected=True,
        )

        assert result.path == "C:/Test/Path"
        assert result.risk_level == RiskLevel.SAFE
        assert result.source_name == "TestApp"
        assert result.confidence == 0.9
        assert result.evidence_chain == ["Evidence 1"]
        assert result.ai_result == ai_result
        assert result.selected is True

    def test_classification_result_defaults(self):
        """Test ClassificationResult default values."""
        result = ClassificationResult(
            path="C:/Test/Path",
            risk_level=RiskLevel.CAUTION,
            source_name="Unknown",
            confidence=0.0,
            evidence_chain=[],
        )

        assert result.ai_result is None
        assert result.selected is False

    def test_classification_result_is_safe(self):
        """Test is_safe property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SAFE,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_safe is True

        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SUGGEST,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_safe is False

    def test_classification_result_is_suggest(self):
        """Test is_suggest property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SUGGEST,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_suggest is True

        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SAFE,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_suggest is False

    def test_classification_result_is_caution(self):
        """Test is_caution property."""
        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.CAUTION,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_caution is True

        result = ClassificationResult(
            path="C:/Test",
            risk_level=RiskLevel.SAFE,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
        )
        assert result.is_caution is False
