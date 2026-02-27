"""
Data models for DeepDel application.

This module contains dataclasses and enums used throughout the application
for representing scan results, identification results, and classification data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class RiskLevel(Enum):
    """Risk level classification for folders."""

    SAFE = "safe"
    SUGGEST = "suggest"
    CAUTION = "caution"


class ProgramStatus(Enum):
    """Status of the program associated with a folder."""

    INSTALLED = "installed"
    RUNNING = "running"
    UNINSTALLED = "uninstalled"
    PORTABLE_GONE = "portable_gone"
    UNKNOWN = "unknown"


class SourceType(Enum):
    """Type of software source."""

    SOFTWARE = "software"
    GAME = "game"
    DEV_TOOL = "dev_tool"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ScanResult:
    """
    Result of scanning a folder for deletion analysis.

    Attributes:
        path: Full path to the scanned folder
        name: Name of the folder
        size_bytes: Total size in bytes
        file_count: Number of files in the folder
        last_access: Last access time of the folder
        is_folder: Whether this is a folder (default True)
        file_extensions: Dictionary mapping file extensions to counts
        has_executables: Whether the folder contains executable files
        folder_depth: Depth of the folder structure
        created_time: When the folder was created (optional)
    """

    path: str
    name: str
    size_bytes: int
    file_count: int
    last_access: datetime
    is_folder: bool = True
    file_extensions: Dict[str, int] = field(default_factory=dict)
    has_executables: bool = False
    folder_depth: int = 0
    created_time: Optional[datetime] = None

    @property
    def size_mb(self) -> float:
        """Return size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Return size in gigabytes."""
        return self.size_bytes / (1024 * 1024 * 1024)

    def format_size(self) -> str:
        """
        Format the size as a human-readable string.

        Returns:
            Formatted size string with appropriate unit (B, KB, MB, GB)
        """
        if self.size_bytes < 1024:
            return f"{self.size_bytes:.2f} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.2f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class IdentificationResult:
    """
    Result of identifying the source program of a folder.

    Attributes:
        path: Full path to the folder
        source_name: Name of the identified program (default "Unknown")
        source_type: Type of the source (default UNKNOWN)
        confidence: Confidence level of identification (0.0 to 1.0)
        risk_level: Risk level for deletion (default CAUTION)
        evidence_chain: List of evidence supporting the identification
        program_status: Status of the associated program
        size_bytes: Total size of the folder
        last_access: Last access time of the folder
    """

    path: str
    source_name: str = "Unknown"
    source_type: SourceType = SourceType.UNKNOWN
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.CAUTION
    evidence_chain: List[str] = field(default_factory=list)
    program_status: ProgramStatus = ProgramStatus.UNKNOWN
    size_bytes: int = 0
    last_access: Optional[datetime] = None

    def add_evidence(self, evidence: str) -> None:
        """
        Add evidence to the evidence chain.

        Args:
            evidence: Description of evidence found during identification
        """
        self.evidence_chain.append(evidence)


@dataclass
class AIAnalysisResult:
    """
    Result of AI analysis for a folder.

    Attributes:
        suggestion: AI suggestion (can_delete, caution, keep)
        confidence: Confidence level of the suggestion (0.0 to 1.0)
        reason: Explanation for the suggestion
        risk_points: List of potential risks identified
    """

    suggestion: str  # can_delete, caution, keep
    confidence: float
    reason: str
    risk_points: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert the result to a dictionary.

        Returns:
            Dictionary representation of the AI analysis result
        """
        return {
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "reason": self.reason,
            "risk_points": self.risk_points,
        }


@dataclass
class ClassificationResult:
    """
    Final classification result combining identification and AI analysis.

    Attributes:
        path: Full path to the folder
        risk_level: Final risk level classification
        source_name: Name of the identified source program
        confidence: Overall confidence level
        evidence_chain: Combined evidence from identification
        ai_result: Optional AI analysis result
        selected: Whether this folder is selected for deletion
    """

    path: str
    risk_level: RiskLevel
    source_name: str
    confidence: float
    evidence_chain: List[str]
    ai_result: Optional[AIAnalysisResult] = None
    selected: bool = False

    @property
    def is_safe(self) -> bool:
        """Check if the risk level is SAFE."""
        return self.risk_level == RiskLevel.SAFE

    @property
    def is_suggest(self) -> bool:
        """Check if the risk level is SUGGEST."""
        return self.risk_level == RiskLevel.SUGGEST

    @property
    def is_caution(self) -> bool:
        """Check if the risk level is CAUTION."""
        return self.risk_level == RiskLevel.CAUTION
