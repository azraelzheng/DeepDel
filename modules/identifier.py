"""
Identifier Module for DeepDel Application.

This module provides the Identifier class which identifies the source of
scanned folders using a multi-stage pipeline approach.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from modules.models import (
    IdentificationResult,
    ProgramStatus,
    RiskLevel,
    ScanResult,
    SourceType,
)
from modules.rule_loader import RuleLoader
from modules.learner import Learner
from utils.registry import check_program_installed, get_mru_entries
from utils.process import find_process_by_folder


class Identifier:
    """
    Identifier class for identifying folder sources.

    This class uses a multi-stage pipeline to identify the source program
    of a scanned folder:
    - Stage 1: Quick Match - Match folder name against software database
    - Stage 2: Association Check - Check registry, processes, MRU entries
    - Stage 3: Deep Analysis - Analyze file extensions, config contents
    - Stage 4: Learning - Query learner for past decisions

    Attributes:
        rules_dir: Directory containing rule files
        rule_loader: RuleLoader instance for loading rules
        learner: Learner instance for learning from decisions
    """

    # Dev cache folder names that indicate development tool caches
    DEV_CACHE_PATTERNS = [
        "node_modules",
        ".npm",
        "npm-cache",
        ".cache",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "venv",
        ".venv",
        "env",
        ".tox",
        ".nox",
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
        "target",
        ".gradle",
        ".mvn",
    ]

    # File extensions that indicate development tools
    DEV_EXTENSIONS = {
        ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
        ".py", ".pyc", ".pyd", ".pyo",
        ".java", ".kt", ".kts",
        ".go", ".mod", ".sum",
        ".rs", ".toml",
        ".rb", ".gem",
        ".php", ".composer",
        ".csproj", ".sln", ".cs",
        ".swift", ".xcodeproj",
    }

    # Cache patterns for risk assessment
    CACHE_INDICATORS = [
        "cache", "Cache", "CACHE",
        "temp", "Temp", "TEMP",
        "tmp", "Tmp",
        "log", "Log", "LOG",
        "GPUCache", "ShaderCache", "Code Cache",
        "Cookies", "Cookie",
    ]

    def __init__(
        self,
        rules_dir: str = "rules",
        db_path: str = "data/learner.db"
    ):
        """
        Initialize the Identifier.

        Args:
            rules_dir: Directory containing rule files. Defaults to "rules".
            db_path: Path to the learner database. Defaults to "data/learner.db".
        """
        self.rules_dir = rules_dir
        self.rule_loader = RuleLoader(rules_dir=rules_dir)

        # Initialize learner - may be None if database is not available
        self.learner: Optional[Learner] = None
        try:
            self.learner = Learner(db_path=db_path)
        except Exception:
            self.learner = None

    def identify(self, scan_result: ScanResult) -> IdentificationResult:
        """
        Identify the source of a scanned folder using the pipeline.

        Args:
            scan_result: The scan result to identify.

        Returns:
            IdentificationResult containing the identification details.
        """
        # Initialize result with basic info from scan
        result = IdentificationResult(
            path=scan_result.path,
            source_name="Unknown",
            source_type=SourceType.UNKNOWN,
            confidence=0.0,
            risk_level=RiskLevel.CAUTION,
            evidence_chain=[],
            program_status=ProgramStatus.UNKNOWN,
            size_bytes=scan_result.size_bytes,
            last_access=scan_result.last_access,
        )

        # Track confidence contributions
        confidence_score = 0.0
        confidence_weight = 0.0

        # Stage 1: Quick Match
        stage1_result = self._stage1_quick_match(scan_result, result)
        if stage1_result['matched']:
            confidence_score += stage1_result['confidence'] * 0.4
            confidence_weight += 0.4

        # Stage 2: Association Check
        stage2_result = self._stage2_association_check(scan_result, result)
        if stage2_result['found']:
            confidence_score += stage2_result['confidence'] * 0.3
            confidence_weight += 0.3

        # Stage 3: Deep Analysis
        stage3_result = self._stage3_deep_analysis(scan_result, result)
        if stage3_result['analyzed']:
            confidence_score += stage3_result['confidence'] * 0.2
            confidence_weight += 0.2

        # Stage 4: Learning
        stage4_result = self._stage4_learning(scan_result, result)
        if stage4_result['learned']:
            confidence_score += stage4_result['confidence'] * 0.1
            confidence_weight += 0.1

        # Calculate final confidence
        if confidence_weight > 0:
            result.confidence = min(1.0, confidence_score / confidence_weight)
        else:
            result.confidence = 0.0

        # Determine final risk level based on evidence
        result.risk_level = self._determine_risk_level(scan_result, result)

        return result

    def _stage1_quick_match(
        self,
        scan_result: ScanResult,
        result: IdentificationResult
    ) -> Dict:
        """
        Stage 1: Quick Match - Match folder name against software database.

        Args:
            scan_result: The scan result being identified.
            result: The identification result to update.

        Returns:
            Dictionary with 'matched' bool and 'confidence' float.
        """
        matched = False
        confidence = 0.0

        # Try to match against software database
        software_info = self.rule_loader.find_matching_software(scan_result.name)

        if software_info:
            matched = True
            confidence = 0.9  # High confidence for database match

            # Update result
            result.source_name = software_info.get('name', 'Unknown')

            # Determine source type from software info
            result.source_type = self._determine_source_type(software_info)

            # Add evidence
            result.add_evidence("Folder name matches software library")

        # Check for dev cache patterns
        elif self._is_dev_cache(scan_result.name):
            matched = True
            confidence = 0.85

            result.source_name = self._get_dev_cache_name(scan_result.name)
            result.source_type = SourceType.DEV_TOOL

            result.add_evidence("Folder name matches development cache pattern")

        return {'matched': matched, 'confidence': confidence}

    def _stage2_association_check(
        self,
        scan_result: ScanResult,
        result: IdentificationResult
    ) -> Dict:
        """
        Stage 2: Association Check - Check registry, processes, MRU.

        Args:
            scan_result: The scan result being identified.
            result: The identification result to update.

        Returns:
            Dictionary with 'found' bool and 'confidence' float.
        """
        found = False
        confidence = 0.0

        # Check for running process
        process_info = find_process_by_folder(scan_result.name)
        if process_info:
            found = True
            confidence = 0.95

            result.program_status = ProgramStatus.RUNNING
            result.add_evidence("Process is running")

            # If we don't have a source name yet, try to get it from process
            if result.source_name == "Unknown":
                exe_name = os.path.basename(process_info.get('exe', ''))
                if exe_name:
                    result.source_name = os.path.splitext(exe_name)[0]

        # Check registry for installed program
        installed = check_program_installed(scan_result.name)
        if installed is True:
            found = True
            confidence = max(confidence, 0.8)

            if result.program_status != ProgramStatus.RUNNING:
                result.program_status = ProgramStatus.INSTALLED

            result.add_evidence("Program installed in registry")

        elif installed is False:
            # Program not found in registry
            if result.source_name != "Unknown":
                # We identified a source but it's not installed
                result.program_status = ProgramStatus.UNINSTALLED
                result.add_evidence("Program uninstalled")

        # Check MRU entries
        if self._check_mru_entries(scan_result.name):
            found = True
            confidence = max(confidence, 0.6)
            result.add_evidence("Found in recent usage")

        return {'found': found, 'confidence': confidence}

    def _stage3_deep_analysis(
        self,
        scan_result: ScanResult,
        result: IdentificationResult
    ) -> Dict:
        """
        Stage 3: Deep Analysis - Analyze extensions and contents.

        Args:
            scan_result: The scan result being identified.
            result: The identification result to update.

        Returns:
            Dictionary with 'analyzed' bool and 'confidence' float.
        """
        analyzed = False
        confidence = 0.0

        # Analyze file extensions
        if scan_result.file_extensions:
            dev_score = self._analyze_dev_extensions(scan_result.file_extensions)

            if dev_score > 0.5:
                analyzed = True
                confidence = dev_score * 0.8

                if result.source_type == SourceType.UNKNOWN:
                    result.source_type = SourceType.DEV_TOOL

                if result.source_name == "Unknown":
                    result.source_name = self._guess_source_from_extensions(
                        scan_result.file_extensions
                    )

                result.add_evidence("File extensions indicate development tool")

        # Check for cache indicators in name or path
        if self._has_cache_indicator(scan_result.name, scan_result.path):
            analyzed = True
            confidence = max(confidence, 0.7)

            result.add_evidence("Folder appears to be a cache directory")

        # Check for executables
        if scan_result.has_executables:
            analyzed = True
            confidence = max(confidence, 0.5)

            result.add_evidence("Folder contains executables")

        return {'analyzed': analyzed, 'confidence': confidence}

    def _stage4_learning(
        self,
        scan_result: ScanResult,
        result: IdentificationResult
    ) -> Dict:
        """
        Stage 4: Learning - Query learner for past decisions.

        Args:
            scan_result: The scan result being identified.
            result: The identification result to update.

        Returns:
            Dictionary with 'learned' bool and 'confidence' float.
        """
        learned = False
        confidence = 0.0

        if not self.learner:
            return {'learned': learned, 'confidence': confidence}

        try:
            # Use the existing learner's interface
            suggestion = self.learner.get_learned_suggestion(
                folder_name=scan_result.name,
                path=scan_result.path,
                source_name=result.source_name if result.source_name != "Unknown" else None
            )

            if suggestion:
                learned = True
                confidence = suggestion.get('confidence', 0.5)

                # Add evidence with decision count
                total_decisions = suggestion.get('total_decisions', 1)
                result.add_evidence(f"Learning suggestion: {total_decisions} decisions")

        except Exception:
            pass

        return {'learned': learned, 'confidence': confidence}

    def _is_dev_cache(self, folder_name: str) -> bool:
        """Check if folder name matches a development cache pattern."""
        import fnmatch

        name_lower = folder_name.lower()
        for pattern in self.DEV_CACHE_PATTERNS:
            if fnmatch.fnmatch(name_lower, pattern.lower()):
                return True
            if name_lower == pattern.lower():
                return True

        return False

    def _get_dev_cache_name(self, folder_name: str) -> str:
        """Get a descriptive name for a dev cache folder."""
        cache_names = {
            "node_modules": "Node.js Dependencies",
            ".npm": "NPM Cache",
            "npm-cache": "NPM Cache",
            "__pycache__": "Python Cache",
            ".pytest_cache": "Pytest Cache",
            ".mypy_cache": "Mypy Cache",
            "venv": "Python Virtual Environment",
            ".venv": "Python Virtual Environment",
            "env": "Python Virtual Environment",
            "build": "Build Output",
            "dist": "Distribution Output",
            "target": "Build Target",
            ".gradle": "Gradle Cache",
            ".mvn": "Maven Cache",
        }

        return cache_names.get(folder_name, f"Dev Cache ({folder_name})")

    def _determine_source_type(self, software_info: Dict) -> SourceType:
        """Determine source type from software info."""
        # Check if software info has explicit type
        software_type = software_info.get('type', '').lower()

        if software_type in ('game', 'games'):
            return SourceType.GAME
        elif software_type in ('dev', 'development', 'dev_tool'):
            return SourceType.DEV_TOOL
        elif software_type in ('system', 'os'):
            return SourceType.SYSTEM

        # Infer from name
        name = software_info.get('name', '').lower()

        dev_indicators = ['node', 'npm', 'python', 'code', 'visual studio', 'git', 'docker']
        game_indicators = ['steam', 'minecraft', 'game', 'epic', 'gog']

        for indicator in dev_indicators:
            if indicator in name:
                return SourceType.DEV_TOOL

        for indicator in game_indicators:
            if indicator in name:
                return SourceType.GAME

        return SourceType.SOFTWARE

    def _check_mru_entries(self, folder_name: str) -> bool:
        """Check if folder name appears in MRU entries."""
        try:
            mru_entries = get_mru_entries()
            folder_lower = folder_name.lower()

            for mru in mru_entries:
                for entry in mru.get('entries', []):
                    if folder_lower in entry.lower():
                        return True

        except Exception:
            pass

        return False

    def _analyze_dev_extensions(self, extensions: Dict[str, int]) -> float:
        """Analyze file extensions to determine dev tool likelihood."""
        if not extensions:
            return 0.0

        total_files = sum(extensions.values())
        if total_files == 0:
            return 0.0

        dev_files = sum(
            count for ext, count in extensions.items()
            if ext.lower() in self.DEV_EXTENSIONS
        )

        return dev_files / total_files

    def _guess_source_from_extensions(self, extensions: Dict[str, int]) -> str:
        """Guess the source name from file extensions."""
        # Map dominant extensions to source names
        extension_sources = {
            '.js': 'Node.js Project',
            '.ts': 'TypeScript Project',
            '.py': 'Python Project',
            '.java': 'Java Project',
            '.go': 'Go Project',
            '.rs': 'Rust Project',
            '.rb': 'Ruby Project',
            '.php': 'PHP Project',
            '.cs': '.NET Project',
            '.swift': 'Swift Project',
        }

        # Find the most common dev extension
        max_count = 0
        dominant_ext = None

        for ext, count in extensions.items():
            ext_lower = ext.lower()
            if ext_lower in self.DEV_EXTENSIONS and count > max_count:
                max_count = count
                dominant_ext = ext_lower

        if dominant_ext:
            return extension_sources.get(dominant_ext, 'Development Project')

        return 'Unknown'

    def _has_cache_indicator(self, folder_name: str, path: str) -> bool:
        """Check if folder name or path has cache indicators."""
        for indicator in self.CACHE_INDICATORS:
            if indicator in folder_name or indicator in path:
                return True

        return False

    def _determine_risk_level(
        self,
        scan_result: ScanResult,
        result: IdentificationResult
    ) -> RiskLevel:
        """
        Determine the risk level based on all available information.

        Args:
            scan_result: The original scan result.
            result: The identification result with evidence.

        Returns:
            The determined RiskLevel.
        """
        # Dev caches are generally safe to delete
        if self._is_dev_cache(scan_result.name):
            return RiskLevel.SAFE

        # Cache directories are suggest
        if self._has_cache_indicator(scan_result.name, scan_result.path):
            return RiskLevel.SUGGEST

        # Uninstalled programs - suggest deletion
        if result.program_status == ProgramStatus.UNINSTALLED:
            return RiskLevel.SUGGEST

        # Running programs - caution
        if result.program_status == ProgramStatus.RUNNING:
            return RiskLevel.CAUTION

        # Installed programs - caution
        if result.program_status == ProgramStatus.INSTALLED:
            return RiskLevel.CAUTION

        # High confidence identification with DEV_TOOL type
        if result.source_type == SourceType.DEV_TOOL and result.confidence > 0.7:
            return RiskLevel.SUGGEST

        # Unknown with low confidence - caution
        if result.source_name == "Unknown" and result.confidence < 0.5:
            return RiskLevel.CAUTION

        # Default to caution for anything else
        return RiskLevel.CAUTION
