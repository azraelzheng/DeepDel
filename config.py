"""
DeepDel Configuration Module

This module provides configuration management for the DeepDel application.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
import yaml


@dataclass
class Config:
    """Configuration dataclass holding all application settings."""

    # Scan settings
    scan_paths: List[str] = field(default_factory=list)
    scan_min_size_mb: float = 1.0
    scan_exclude: List[str] = field(default_factory=list)

    # AI settings
    ai_enabled: bool = True
    ai_provider: str = "glm"
    ai_model: str = "glm-4-flash"
    ai_api_key: str = ""
    ai_trigger_confidence: float = 0.6
    ai_timeout: int = 10

    # Delete settings
    delete_use_recycle_bin: bool = True
    delete_create_restore_point: bool = False

    # Performance settings
    performance_max_workers: int = 4

    def load_from_file(self, filepath: str) -> None:
        """
        Load configuration from a YAML file.

        Args:
            filepath: Path to the YAML configuration file.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if data is None:
            return

        # Load scan settings
        if 'scan' in data:
            scan = data['scan']
            self.scan_paths = scan.get('paths', self.scan_paths)
            self.scan_min_size_mb = scan.get('min_size_mb', self.scan_min_size_mb)
            self.scan_exclude = scan.get('exclude', self.scan_exclude)

        # Load AI settings
        if 'ai' in data:
            ai = data['ai']
            self.ai_enabled = ai.get('enabled', self.ai_enabled)
            self.ai_provider = ai.get('provider', self.ai_provider)
            self.ai_model = ai.get('model', self.ai_model)
            self.ai_api_key = ai.get('api_key', self.ai_api_key)
            self.ai_trigger_confidence = ai.get('trigger_confidence', self.ai_trigger_confidence)
            self.ai_timeout = ai.get('timeout', self.ai_timeout)

        # Load delete settings
        if 'delete' in data:
            delete = data['delete']
            self.delete_use_recycle_bin = delete.get('use_recycle_bin', self.delete_use_recycle_bin)
            self.delete_create_restore_point = delete.get('create_restore_point', self.delete_create_restore_point)

        # Load performance settings
        if 'performance' in data:
            performance = data['performance']
            self.performance_max_workers = performance.get('max_workers', self.performance_max_workers)

    def get_expanded_scan_paths(self) -> List[str]:
        """
        Expand environment variables in scan paths.

        Returns:
            List of paths with environment variables expanded.
            For example, %TEMP% will be expanded to the actual temp directory path.
        """
        expanded_paths = []
        for path in self.scan_paths:
            # Expand environment variables like %TEMP%, %APPDATA%, etc.
            expanded = os.path.expandvars(path)
            expanded_paths.append(expanded)
        return expanded_paths

    def save_to_file(self, filepath: str) -> None:
        """
        Save configuration to a YAML file.

        Args:
            filepath: Path to save the YAML configuration file.
        """
        data = {
            'scan': {
                'paths': self.scan_paths,
                'min_size_mb': self.scan_min_size_mb,
                'exclude': self.scan_exclude,
            },
            'ai': {
                'enabled': self.ai_enabled,
                'provider': self.ai_provider,
                'model': self.ai_model,
                'api_key': self.ai_api_key,
                'trigger_confidence': self.ai_trigger_confidence,
                'timeout': self.ai_timeout,
            },
            'delete': {
                'use_recycle_bin': self.delete_use_recycle_bin,
                'create_restore_point': self.delete_create_restore_point,
            },
            'performance': {
                'max_workers': self.performance_max_workers,
            },
        }

        # Ensure directory exists
        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# Global singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the singleton configuration instance.

    Returns:
        The global Config instance. If not initialized, returns a new Config with defaults.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config(filepath: str) -> Config:
    """
    Reload configuration from a file.

    Args:
        filepath: Path to the YAML configuration file.

    Returns:
        The newly loaded Config instance.
    """
    global _config_instance
    _config_instance = Config()
    _config_instance.load_from_file(filepath)
    return _config_instance
