"""
Classifier Module for DeepDel Application.

This module provides the Classifier class which determines the final risk
classification for folders based on identification results and AI analysis.
"""

from typing import List, Optional

from config import Config
from modules.models import (
    ScanResult,
    IdentificationResult,
    ClassificationResult,
    AIAnalysisResult,
    RiskLevel,
    ProgramStatus,
)
from modules.rule_loader import RuleLoader


class Classifier:
    """
    Classifier class for determining folder deletion risk levels.

    This class combines identification results with rule-based and AI-based
    analysis to determine the final classification of folders.

    Attributes:
        config: Application configuration
        ai_analyzer: Optional AI analyzer for additional analysis
        rule_loader: Rule loader for checking caution patterns
    """

    def __init__(self, config: Config, ai_analyzer=None):
        """
        Initialize the Classifier.

        Args:
            config: Application configuration instance
            ai_analyzer: Optional AI analyzer instance for enhanced analysis
        """
        self.config = config
        self.ai_analyzer = ai_analyzer
        self.rule_loader = RuleLoader()

    def classify(
        self, scan_result: ScanResult, id_result: IdentificationResult
    ) -> ClassificationResult:
        """
        Classify a folder based on scan and identification results.

        Classification logic:
        1. If id_result.risk_level == SAFE: Return SAFE, selected=True
        2. Check caution_rules: If matches -> CAUTION
        3. Check program_status: RUNNING -> CAUTION, UNINSTALLED -> SUGGEST
        4. If confidence < config.ai_trigger_confidence and ai_analyzer available:
           Call AI for suggestion
        5. Default: selected = (risk_level in [SAFE, SUGGEST])

        Args:
            scan_result: Scan result containing folder information
            id_result: Identification result with source and risk info

        Returns:
            ClassificationResult with final classification
        """
        evidence_chain = list(id_result.evidence_chain)
        risk_level = id_result.risk_level
        ai_result: Optional[AIAnalysisResult] = None

        # Step 1: If already identified as SAFE, return immediately
        if id_result.risk_level == RiskLevel.SAFE:
            evidence_chain.append("Identified as safe for deletion")
            return ClassificationResult(
                path=scan_result.path,
                risk_level=RiskLevel.SAFE,
                source_name=id_result.source_name,
                confidence=id_result.confidence,
                evidence_chain=evidence_chain,
                ai_result=None,
                selected=True,
            )

        # Step 2: Check caution rules using rule_loader
        if self.rule_loader.is_caution_pattern(scan_result.name, scan_result.path):
            evidence_chain.append(f"Matches caution pattern")
            risk_level = RiskLevel.CAUTION

        # Step 3: Check program status
        elif id_result.program_status == ProgramStatus.RUNNING:
            evidence_chain.append("Associated program is currently running")
            risk_level = RiskLevel.CAUTION

        elif id_result.program_status == ProgramStatus.UNINSTALLED:
            evidence_chain.append("Associated program has been uninstalled")
            risk_level = RiskLevel.SUGGEST

        elif id_result.program_status == ProgramStatus.PORTABLE_GONE:
            evidence_chain.append("Portable program no longer exists at original location")
            risk_level = RiskLevel.SUGGEST

        # Step 4: If confidence is low and AI is available, call AI for suggestion
        elif (
            self._should_use_ai(id_result.confidence)
            and self.ai_analyzer is not None
        ):
            ai_result = self._call_ai_analyzer(scan_result, id_result)
            if ai_result is not None:
                risk_level = self._determine_risk_from_ai(ai_result)
                evidence_chain.append(f"AI analysis: {ai_result.reason}")

        # Step 5: Determine selection based on risk level
        selected = risk_level in [RiskLevel.SAFE, RiskLevel.SUGGEST]

        return ClassificationResult(
            path=scan_result.path,
            risk_level=risk_level,
            source_name=id_result.source_name,
            confidence=id_result.confidence,
            evidence_chain=evidence_chain,
            ai_result=ai_result,
            selected=selected,
        )

    def classify_batch(
        self, scan_results: List[ScanResult], id_results: List[IdentificationResult]
    ) -> List[ClassificationResult]:
        """
        Classify multiple folders in batch.

        Args:
            scan_results: List of scan results
            id_results: List of identification results (must match scan_results length)

        Returns:
            List of ClassificationResult instances

        Raises:
            ValueError: If scan_results and id_results have different lengths
        """
        if len(scan_results) != len(id_results):
            raise ValueError(
                f"Mismatched list lengths: {len(scan_results)} scan results vs "
                f"{len(id_results)} identification results"
            )

        if not scan_results:
            return []

        results = []
        for scan_result, id_result in zip(scan_results, id_results):
            result = self.classify(scan_result, id_result)
            results.append(result)

        return results

    def _should_use_ai(self, confidence: float) -> bool:
        """
        Determine if AI analysis should be used based on confidence.

        Args:
            confidence: Current confidence level

        Returns:
            True if AI should be used, False otherwise
        """
        return (
            self.config.ai_enabled
            and confidence < self.config.ai_trigger_confidence
        )

    def _call_ai_analyzer(
        self, scan_result: ScanResult, id_result: IdentificationResult
    ) -> Optional[AIAnalysisResult]:
        """
        Call the AI analyzer for additional analysis.

        Args:
            scan_result: Scan result for the folder
            id_result: Identification result for the folder

        Returns:
            AIAnalysisResult if successful, None otherwise
        """
        try:
            return self.ai_analyzer.analyze(scan_result, id_result)
        except Exception:
            # Handle AI errors gracefully
            return None

    def _determine_risk_from_ai(self, ai_result: AIAnalysisResult) -> RiskLevel:
        """
        Determine risk level from AI analysis result.

        Args:
            ai_result: AI analysis result

        Returns:
            RiskLevel based on AI suggestion
        """
        suggestion = ai_result.suggestion.lower()

        if suggestion == "can_delete":
            return RiskLevel.SUGGEST
        elif suggestion in ["caution", "keep"]:
            return RiskLevel.CAUTION
        else:
            # Default to caution for unknown suggestions
            return RiskLevel.CAUTION
