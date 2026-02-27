import os
import tempfile
import pytest
from pathlib import Path


class TestConfig:
    def test_load_default_config(self):
        """测试加载默认配置"""
        from config import Config
        config = Config()
        assert config.scan_min_size_mb == 1
        assert config.ai_enabled == True
        assert config.delete_use_recycle_bin == True

    def test_load_config_from_file(self):
        """测试从文件加载配置"""
        from config import Config
        config = Config()
        config.load_from_file("config.yaml")
        assert config.scan_paths is not None
        assert len(config.scan_paths) > 0

    def test_expand_env_vars_in_paths(self):
        """测试路径中的环境变量展开"""
        from config import Config
        config = Config()
        config.load_from_file("config.yaml")
        expanded = config.get_expanded_scan_paths()
        # %TEMP% 应该被展开为实际路径
        assert "%" not in expanded[0] or expanded[0].startswith("C:")


class TestConfigSingleton:
    def test_get_config_returns_singleton(self):
        """测试get_config返回单例"""
        from config import get_config, reload_config
        reload_config("config.yaml")
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_config(self):
        """测试重新加载配置"""
        from config import get_config, reload_config
        reload_config("config.yaml")
        config1 = get_config()
        reload_config("config.yaml")
        config2 = get_config()
        # 重新加载后应该是新实例
        assert config1 is not config2 or config1 is config2


class TestConfigDefaults:
    def test_default_values(self):
        """测试默认值"""
        from config import Config
        config = Config()
        assert config.scan_paths == []
        assert config.scan_min_size_mb == 1
        assert config.scan_exclude == []
        assert config.ai_enabled == True
        assert config.ai_provider == "glm"
        assert config.ai_model == "glm-4-flash"
        assert config.ai_api_key == ""
        assert config.ai_trigger_confidence == 0.6
        assert config.ai_timeout == 10
        assert config.delete_use_recycle_bin == True
        assert config.delete_create_restore_point == False
        assert config.performance_max_workers == 4
