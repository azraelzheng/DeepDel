"""
AI Analyzer module for DeepDel application.

This module provides the AIAnalyzer class for analyzing folders
using AI (GLM) to determine deletion safety.
"""

import json
from typing import Any, Dict, Optional

from modules.models import AIAnalysisResult, ScanResult
from utils.llm.glm import GLMClient


class AIAnalyzer:
    """
    AI Analyzer class for analyzing folders using AI.

    This class uses the GLM API to analyze folders and provide
    deletion recommendations when the identifier has low confidence.

    Attributes:
        config: Configuration object with AI settings.
        client: GLM API client.
    """

    def __init__(self, config):
        """
        Initialize the AI Analyzer.

        Args:
            config: Configuration object containing AI settings:
                - ai_provider: AI provider name
                - ai_model: Model to use
                - ai_timeout: Timeout for API calls
        """
        self.config = config
        self.client = GLMClient(
            model=getattr(config, 'ai_model', 'glm-4-flash'),
            timeout=getattr(config, 'ai_timeout', 10),
        )

    def analyze(
        self,
        scan_result: ScanResult,
        source_name: Optional[str] = None,
        program_status: Optional[str] = None,
        evidence_chain: Optional[list] = None,
    ) -> Optional[AIAnalysisResult]:
        """
        Analyze a folder and provide a deletion recommendation.

        This method sends sanitized information about the folder to the AI
        and receives a recommendation on whether it can be safely deleted.

        Args:
            scan_result: ScanResult containing folder information.
            source_name: Name of the identified source program.
            program_status: Status of the associated program.
            evidence_chain: List of evidence from identification.

        Returns:
            AIAnalysisResult with suggestion, confidence, and reason,
            or None if analysis fails.
        """
        # Build sanitized input for AI
        ai_input = self._build_ai_input(
            scan_result, source_name, program_status, evidence_chain
        )

        # Build prompt
        prompt = self._build_prompt(ai_input)

        try:
            # Call AI API
            response = self.client.chat(prompt)

            # Parse response
            return self._parse_response(response)

        except Exception:
            # Return None on failure (caller should handle gracefully)
            return None

    def _build_ai_input(
        self,
        scan_result: ScanResult,
        source_name: Optional[str],
        program_status: Optional[str],
        evidence_chain: Optional[list],
    ) -> Dict[str, Any]:
        """
        Build sanitized input for AI analysis.

        Only includes non-sensitive information about the folder.

        Args:
            scan_result: ScanResult containing folder information.
            source_name: Name of the identified source program.
            program_status: Status of the associated program.
            evidence_chain: List of evidence from identification.

        Returns:
            Dictionary with sanitized folder information.
        """
        # Format size
        size_mb = scan_result.size_bytes / (1024 * 1024)
        if size_mb >= 1024:
            size_str = f"{size_mb / 1024:.2f} GB"
        else:
            size_str = f"{size_mb:.2f} MB"

        # Format extensions (top 5)
        ext_summary = {}
        if scan_result.file_extensions:
            sorted_ext = sorted(
                scan_result.file_extensions.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            total_files = sum(scan_result.file_extensions.values())
            for ext, count in sorted_ext:
                ext_summary[ext] = round(count / total_files, 2) if total_files > 0 else 0

        return {
            "folder_name": scan_result.name,
            "file_extensions": ext_summary,
            "file_count": scan_result.file_count,
            "total_size": size_str,
            "has_executables": scan_result.has_executables,
            "identified_source": source_name or "Unknown",
            "program_status": program_status or "unknown",
            "evidence": evidence_chain[:3] if evidence_chain else [],
        }

    def _build_prompt(self, ai_input: Dict[str, Any]) -> str:
        """
        Build the AI prompt from the input data.

        Args:
            ai_input: Sanitized folder information.

        Returns:
            Prompt string for the AI.
        """
        prompt = f"""分析以下文件夹信息，判断是否可以安全删除。请以JSON格式返回结果。

文件夹信息:
- 名称: {ai_input['folder_name']}
- 文件数量: {ai_input['file_count']}
- 总大小: {ai_input['total_size']}
- 包含可执行文件: {'是' if ai_input['has_executables'] else '否'}
- 识别的来源程序: {ai_input['identified_source']}
- 程序状态: {ai_input['program_status']}
- 主要文件类型: {json.dumps(ai_input['file_extensions'], ensure_ascii=False)}
- 识别证据: {json.dumps(ai_input['evidence'], ensure_ascii=False)}

请返回以下JSON格式:
{{
    "suggestion": "can_delete" 或 "caution" 或 "keep",
    "confidence": 0.0到1.0之间的数值,
    "reason": "判断理由的简短说明",
    "risk_points": ["可能的风险点1", "可能的风险点2"]
}}

判断标准:
- can_delete: 可以安全删除，是临时文件、缓存或残留文件
- caution: 需要谨慎，可能包含用户数据或配置
- keep: 建议保留，是重要系统文件或正在使用的程序数据

只返回JSON，不要其他说明。"""

        return prompt

    def _parse_response(self, response: str) -> Optional[AIAnalysisResult]:
        """
        Parse the AI response into an AIAnalysisResult.

        Args:
            response: Raw response string from the AI.

        Returns:
            AIAnalysisResult or None if parsing fails.
        """
        try:
            # Try to extract JSON from response
            json_str = response.strip()

            # Remove markdown code blocks if present
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]

            json_str = json_str.strip()

            # Parse JSON
            data = json.loads(json_str)

            # Validate required fields
            suggestion = data.get("suggestion", "caution")
            confidence = float(data.get("confidence", 0.5))
            reason = data.get("reason", "AI分析结果")
            risk_points = data.get("risk_points", [])

            # Clamp confidence to valid range
            confidence = max(0.0, min(1.0, confidence))

            # Validate suggestion
            if suggestion not in ("can_delete", "caution", "keep"):
                suggestion = "caution"

            return AIAnalysisResult(
                suggestion=suggestion,
                confidence=confidence,
                reason=reason,
                risk_points=risk_points if isinstance(risk_points, list) else [],
            )

        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def is_available(self) -> bool:
        """
        Check if the AI service is available.

        Returns:
            True if the AI service is configured and available.
        """
        return self.client is not None
