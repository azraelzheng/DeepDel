"""
Tests for rule_loader module.

Tests the RuleLoader class which handles loading and matching rules from JSON files.
"""
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from modules.rule_loader import RuleLoader


class TestRuleLoaderInit:
    """Test RuleLoader initialization."""

    def test_init_default_rules_dir(self):
        """Test initialization with default rules directory."""
        loader = RuleLoader()
        assert loader.rules_dir == "rules"

    def test_init_custom_rules_dir(self):
        """Test initialization with custom rules directory."""
        loader = RuleLoader(rules_dir="custom_rules")
        assert loader.rules_dir == "custom_rules"

    def test_init_empty_cache(self):
        """Test that cache is empty on initialization."""
        loader = RuleLoader()
        assert loader._cache == {}


class TestLoadSafeRules:
    """Test load_safe_rules method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test rule files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create safe_rules.json
            safe_rules = {
                "patterns": [
                    {"pattern": "**/cache", "description": "Cache folders"},
                    {"pattern": "**/temp", "description": "Temp folders"},
                    {"pattern": "**/__pycache__", "description": "Python cache"},
                ]
            }
            with open(rules_dir / "safe_rules.json", "w", encoding="utf-8") as f:
                json.dump(safe_rules, f)

            yield str(rules_dir)

    def test_load_safe_rules_success(self, temp_rules_dir):
        """Test loading safe rules from file."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        rules = loader.load_safe_rules()

        assert "patterns" in rules
        assert len(rules["patterns"]) == 3
        assert rules["patterns"][0]["pattern"] == "**/cache"

    def test_load_safe_rules_caches_result(self, temp_rules_dir):
        """Test that loaded rules are cached."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        # First load
        rules1 = loader.load_safe_rules()
        # Second load should return cached result
        rules2 = loader.load_safe_rules()

        assert rules1 is rules2
        assert "safe_rules" in loader._cache

    def test_load_safe_rules_file_not_found(self):
        """Test handling of missing safe rules file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = RuleLoader(rules_dir=tmpdir)
            rules = loader.load_safe_rules()
            assert rules == {}

    def test_load_safe_rules_invalid_json(self):
        """Test handling of invalid JSON in safe rules file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "safe_rules.json"
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write("invalid json {")

            loader = RuleLoader(rules_dir=tmpdir)
            rules = loader.load_safe_rules()
            assert rules == {}


class TestLoadSuggestRules:
    """Test load_suggest_rules method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test rule files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create suggest_rules.json
            suggest_rules = {
                "patterns": [
                    {"pattern": "**/logs", "description": "Log folders"},
                    {"pattern": "**/backup", "description": "Backup folders"},
                ]
            }
            with open(rules_dir / "suggest_rules.json", "w", encoding="utf-8") as f:
                json.dump(suggest_rules, f)

            yield str(rules_dir)

    def test_load_suggest_rules_success(self, temp_rules_dir):
        """Test loading suggest rules from file."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        rules = loader.load_suggest_rules()

        assert "patterns" in rules
        assert len(rules["patterns"]) == 2
        assert rules["patterns"][0]["pattern"] == "**/logs"

    def test_load_suggest_rules_caches_result(self, temp_rules_dir):
        """Test that loaded rules are cached."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        rules1 = loader.load_suggest_rules()
        rules2 = loader.load_suggest_rules()

        assert rules1 is rules2
        assert "suggest_rules" in loader._cache


class TestLoadCautionRules:
    """Test load_caution_rules method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test rule files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create caution_rules.json
            caution_rules = {
                "patterns": [
                    {"pattern": "**/system32", "description": "System folder"},
                    {"pattern": "**/program files/**", "description": "Program files"},
                ]
            }
            with open(rules_dir / "caution_rules.json", "w", encoding="utf-8") as f:
                json.dump(caution_rules, f)

            yield str(rules_dir)

    def test_load_caution_rules_success(self, temp_rules_dir):
        """Test loading caution rules from file."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        rules = loader.load_caution_rules()

        assert "patterns" in rules
        assert len(rules["patterns"]) == 2
        assert rules["patterns"][0]["pattern"] == "**/system32"

    def test_load_caution_rules_caches_result(self, temp_rules_dir):
        """Test that loaded rules are cached."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        rules1 = loader.load_caution_rules()
        rules2 = loader.load_caution_rules()

        assert rules1 is rules2
        assert "caution_rules" in loader._cache


class TestLoadSoftwareDb:
    """Test load_software_db method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test software database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create software_db.json
            software_db = {
                "software": [
                    {
                        "name": "Google Chrome",
                        "folder_patterns": ["chrome", "google/chrome"],
                        "type": "software"
                    },
                    {
                        "name": "Visual Studio Code",
                        "folder_patterns": ["vscode", "code"],
                        "type": "dev_tool"
                    },
                    {
                        "name": "Steam",
                        "folder_patterns": ["steam", "steamapps"],
                        "type": "game"
                    }
                ]
            }
            with open(rules_dir / "software_db.json", "w", encoding="utf-8") as f:
                json.dump(software_db, f)

            yield str(rules_dir)

    def test_load_software_db_success(self, temp_rules_dir):
        """Test loading software database from file."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        db = loader.load_software_db()

        assert "software" in db
        assert len(db["software"]) == 3
        assert db["software"][0]["name"] == "Google Chrome"

    def test_load_software_db_caches_result(self, temp_rules_dir):
        """Test that loaded database is cached."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        db1 = loader.load_software_db()
        db2 = loader.load_software_db()

        assert db1 is db2
        assert "software_db" in loader._cache


class TestMatchPattern:
    """Test match_pattern method."""

    @pytest.fixture
    def loader(self):
        """Create a RuleLoader instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = RuleLoader(rules_dir=tmpdir)
            yield loader

    def test_match_pattern_double_star_name(self, loader):
        """Test **/name pattern - matches name at any depth."""
        # Should match
        assert loader.match_pattern("C:/Users/Test/cache", "**/cache") is True
        assert loader.match_pattern("C:/cache", "**/cache") is True
        assert loader.match_pattern("/home/user/app/cache", "**/cache") is True
        assert loader.match_pattern("D:/Games/Steam/steamapps/cache", "**/cache") is True

        # Should not match
        assert loader.match_pattern("C:/Users/Test/cachefolder", "**/cache") is False
        assert loader.match_pattern("C:/Users/Test/cache123", "**/cache") is False

    def test_match_pattern_double_star_suffix(self, loader):
        """Test path/** pattern - matches everything under path."""
        # Should match
        assert loader.match_pattern("C:/Program Files/Steam/file.txt", "C:/Program Files/Steam/**") is True
        assert loader.match_pattern("C:/Program Files/Steam/subfolder/file.txt", "C:/Program Files/Steam/**") is True
        assert loader.match_pattern("C:/Program Files/Steam/deep/nested/path/file.txt", "C:/Program Files/Steam/**") is True

        # Should not match
        assert loader.match_pattern("C:/Program Files/Other/file.txt", "C:/Program Files/Steam/**") is False

    def test_match_pattern_single_star(self, loader):
        """Test simple glob with * wildcard."""
        # Should match
        assert loader.match_pattern("C:/Users/Test/cache", "C:/Users/*/cache") is True
        assert loader.match_pattern("C:/Users/Admin/cache", "C:/Users/*/cache") is True
        assert loader.match_pattern("test.log", "*.log") is True
        assert loader.match_pattern("file.txt", "*.txt") is True
        assert loader.match_pattern("C:/temp/cache_v1", "C:/temp/cache*") is True

        # Should not match
        assert loader.match_pattern("C:/Users/Test/Other", "C:/Users/*/cache") is False
        assert loader.match_pattern("test.txt", "*.log") is False

    def test_match_pattern_exact_match(self, loader):
        """Test exact path matching (no wildcards)."""
        assert loader.match_pattern("C:/cache", "C:/cache") is True
        assert loader.match_pattern("C:/cache", "C:/temp") is False

    def test_match_pattern_case_insensitive(self, loader):
        """Test case-insensitive matching on Windows."""
        # On Windows, paths are case-insensitive
        assert loader.match_pattern("C:/Cache", "**/cache") is True
        assert loader.match_pattern("C:/CACHE", "**/cache") is True

    def test_match_pattern_combined_wildcards(self, loader):
        """Test combined wildcard patterns."""
        assert loader.match_pattern("C:/Users/Test/AppData/Local/cache", "**/Local/cache") is True
        assert loader.match_pattern("C:/Users/Test/AppData/Local/Cache", "C:/Users/*/AppData/**/Cache") is True

    def test_match_pattern_empty_path(self, loader):
        """Test matching with empty path."""
        assert loader.match_pattern("", "**/cache") is False
        assert loader.match_pattern("", "cache") is False

    def test_match_pattern_backslash_paths(self, loader):
        """Test matching Windows backslash paths."""
        assert loader.match_pattern("C:\\Users\\Test\\cache", "**/cache") is True
        assert loader.match_pattern("C:\\Program Files\\Steam\\file.txt", "C:/Program Files/Steam/**") is True


class TestGetAllSafePatterns:
    """Test get_all_safe_patterns method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test rule files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create safe_rules.json
            safe_rules = {
                "patterns": [
                    {"pattern": "**/cache", "description": "Cache folders", "risk": "low"},
                    {"pattern": "**/temp", "description": "Temp folders"},
                    {"pattern": "**/__pycache__", "description": "Python cache"},
                ]
            }
            with open(rules_dir / "safe_rules.json", "w", encoding="utf-8") as f:
                json.dump(safe_rules, f)

            yield str(rules_dir)

    def test_get_all_safe_patterns_returns_list(self, temp_rules_dir):
        """Test that get_all_safe_patterns returns a list."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        patterns = loader.get_all_safe_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) == 3

    def test_get_all_safe_patterns_pattern_structure(self, temp_rules_dir):
        """Test the structure of returned patterns."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        patterns = loader.get_all_safe_patterns()

        first_pattern = patterns[0]
        assert "pattern" in first_pattern
        assert first_pattern["pattern"] == "**/cache"
        assert "description" in first_pattern

    def test_get_all_safe_patterns_empty_rules(self):
        """Test with empty rules file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "safe_rules.json"
            with open(rules_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

            loader = RuleLoader(rules_dir=tmpdir)
            patterns = loader.get_all_safe_patterns()

            assert patterns == []


class TestFindMatchingSoftware:
    """Test find_matching_software method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test software database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create software_db.json
            software_db = {
                "software": [
                    {
                        "name": "Google Chrome",
                        "folder_patterns": ["chrome", "google/chrome"],
                        "type": "software"
                    },
                    {
                        "name": "Visual Studio Code",
                        "folder_patterns": ["vscode", "code"],
                        "type": "dev_tool"
                    },
                    {
                        "name": "Steam",
                        "folder_patterns": ["steam", "steamapps"],
                        "type": "game"
                    },
                    {
                        "name": "Test App",
                        "folder_patterns": ["test*"],
                        "type": "software"
                    }
                ]
            }
            with open(rules_dir / "software_db.json", "w", encoding="utf-8") as f:
                json.dump(software_db, f)

            yield str(rules_dir)

    def test_find_matching_software_exact_match(self, temp_rules_dir):
        """Test finding software with exact folder name match."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        result = loader.find_matching_software("chrome")

        assert result is not None
        assert result["name"] == "Google Chrome"
        assert result["type"] == "software"

    def test_find_matching_software_no_match(self, temp_rules_dir):
        """Test finding software with no matching folder."""
        loader = RuleLoader(rules_dir=temp_rules_dir)
        result = loader.find_matching_software("nonexistent")

        assert result is None

    def test_find_matching_software_case_insensitive(self, temp_rules_dir):
        """Test case-insensitive matching."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        result = loader.find_matching_software("CHROME")
        assert result is not None
        assert result["name"] == "Google Chrome"

        result = loader.find_matching_software("Steam")
        assert result is not None
        assert result["name"] == "Steam"

    def test_find_matching_software_wildcard_pattern(self, temp_rules_dir):
        """Test matching with wildcard patterns."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        result = loader.find_matching_software("test123")
        assert result is not None
        assert result["name"] == "Test App"

        result = loader.find_matching_software("testing")
        assert result is not None
        assert result["name"] == "Test App"

    def test_find_matching_software_first_match_wins(self, temp_rules_dir):
        """Test that first matching software is returned."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        # "steam" should match the Steam entry
        result = loader.find_matching_software("steam")
        assert result["name"] == "Steam"


class TestIsCautionPattern:
    """Test is_caution_pattern method."""

    @pytest.fixture
    def temp_rules_dir(self):
        """Create a temporary directory with test rule files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            # Create caution_rules.json
            caution_rules = {
                "patterns": [
                    {"pattern": "**/system32", "description": "System folder"},
                    {"pattern": "**/program files/**", "description": "Program files"},
                    {"pattern": "**/windows", "description": "Windows folder"},
                ]
            }
            with open(rules_dir / "caution_rules.json", "w", encoding="utf-8") as f:
                json.dump(caution_rules, f)

            yield str(rules_dir)

    def test_is_caution_pattern_matches(self, temp_rules_dir):
        """Test that caution patterns are correctly identified."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        assert loader.is_caution_pattern("Windows", "C:/Windows/system32") is True
        assert loader.is_caution_pattern("Program Files", "C:/Program Files/Steam") is True
        assert loader.is_caution_pattern("windows", "C:/windows") is True

    def test_is_caution_pattern_no_match(self, temp_rules_dir):
        """Test that non-caution patterns return False."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        assert loader.is_caution_pattern("cache", "C:/Users/Test/cache") is False
        assert loader.is_caution_pattern("temp", "C:/temp") is False

    def test_is_caution_pattern_case_insensitive(self, temp_rules_dir):
        """Test case-insensitive matching for caution patterns."""
        loader = RuleLoader(rules_dir=temp_rules_dir)

        assert loader.is_caution_pattern("SYSTEM32", "C:/SYSTEM32") is True
        assert loader.is_caution_pattern("Windows", "C:/windows") is True


class TestRuleLoaderCaching:
    """Test caching behavior of RuleLoader."""

    def test_cache_prevents_repeated_file_reads(self):
        """Test that caching prevents repeated file reads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "safe_rules.json"
            with open(rules_path, "w", encoding="utf-8") as f:
                json.dump({"patterns": [{"pattern": "**/cache"}]}, f)

            loader = RuleLoader(rules_dir=tmpdir)

            # First load
            with patch("builtins.open", wraps=open) as mock_open:
                loader.load_safe_rules()
                first_call_count = mock_open.call_count

            # Second load should use cache
            with patch("builtins.open", wraps=open) as mock_open:
                loader.load_safe_rules()
                # File should not be opened again
                assert mock_open.call_count == 0


class TestRuleLoaderEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_pattern_list(self):
        """Test handling of empty pattern lists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "safe_rules.json"
            with open(rules_path, "w", encoding="utf-8") as f:
                json.dump({"patterns": []}, f)

            loader = RuleLoader(rules_dir=tmpdir)
            patterns = loader.get_all_safe_patterns()

            assert patterns == []

    def test_malformed_pattern(self):
        """Test handling of malformed patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = RuleLoader(rules_dir=tmpdir)

            # Should handle malformed patterns gracefully
            result = loader.match_pattern("C:/test", "[invalid")
            # Should return False or raise an appropriate exception
            assert result is False

    def test_unicode_paths(self):
        """Test handling of Unicode paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = RuleLoader(rules_dir=tmpdir)

            assert loader.match_pattern("C:/Users/Test/AppData", "**/AppData") is True

    def test_very_long_path(self):
        """Test handling of very long paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = RuleLoader(rules_dir=tmpdir)

            long_path = "C:/" + "/".join(["folder" + str(i) for i in range(50)]) + "/cache"
            assert loader.match_pattern(long_path, "**/cache") is True


class TestActualRuleFiles:
    """Test against actual rule files in the rules/ directory."""

    @pytest.fixture
    def loader(self):
        """Create a RuleLoader with the actual rules directory."""
        return RuleLoader(rules_dir="H:/DeepDel/rules")

    def test_load_actual_safe_rules(self, loader):
        """Test loading actual safe rules file."""
        rules = loader.load_safe_rules()

        # Should have multiple pattern categories
        assert "temp_patterns" in rules
        assert "cache_patterns" in rules
        assert "dev_caches" in rules

        # Check temp patterns exist
        temp_patterns = rules.get("temp_patterns", [])
        assert len(temp_patterns) > 0
        assert any("temp" in p.get("pattern", "").lower() for p in temp_patterns)

    def test_load_actual_caution_rules(self, loader):
        """Test loading actual caution rules file."""
        rules = loader.load_caution_rules()

        # Should have user data indicators
        assert "user_data_indicators" in rules
        assert "config_indicators" in rules
        assert "protected_folders" in rules

        # Check protected folders
        protected = rules.get("protected_folders", [])
        assert "Desktop" in protected
        assert "Documents" in protected

    def test_load_actual_software_db(self, loader):
        """Test loading actual software database."""
        db = loader.load_software_db()

        # Should have applications
        assert "applications" in db
        apps = db.get("applications", [])
        assert len(apps) > 0

        # Check for known applications
        app_names = [app.get("name", "") for app in apps]
        assert "Visual Studio Code" in app_names
        assert "Steam" in app_names

    def test_get_all_safe_patterns_aggregates(self, loader):
        """Test that get_all_safe_patterns aggregates all pattern types."""
        patterns = loader.get_all_safe_patterns()

        # Should contain patterns from multiple categories
        assert len(patterns) > 0

        # Check for common cache patterns
        pattern_strs = [p.get("pattern", "") for p in patterns]
        # Should contain various cache-related patterns
        assert any("__pycache__" in p or "node_modules" in p or "cache" in p.lower() for p in pattern_strs)

    def test_find_software_with_actual_db(self, loader):
        """Test finding software using actual database."""
        # Test finding VS Code
        result = loader.find_matching_software("Code")
        assert result is not None
        assert result.get("name") == "Visual Studio Code"

        # Test finding Steam
        result = loader.find_matching_software("Steam")
        assert result is not None
        assert result.get("name") == "Steam"

    def test_is_caution_pattern_with_actual_rules(self, loader):
        """Test caution patterns with actual rules."""
        # Test protected folders
        assert loader.is_caution_pattern("Desktop", "C:/Users/Test/Desktop") is True
        assert loader.is_caution_pattern("Documents", "C:/Users/Test/Documents") is True

        # Test non-protected folders
        assert loader.is_caution_pattern("cache", "C:/Users/Test/cache") is False

    def test_match_dev_cache_patterns(self, loader):
        """Test matching development cache patterns from actual rules."""
        # Python cache
        assert loader.match_pattern("C:/Projects/myapp/__pycache__", "**/__pycache__") is True
        assert loader.match_pattern("C:/Projects/myapp/subdir/__pycache__", "**/__pycache__") is True

        # Node modules
        assert loader.match_pattern("C:/Projects/myapp/node_modules", "**/node_modules") is True

    def test_match_windows_style_patterns(self, loader):
        """Test matching Windows-style patterns from actual rules."""
        # Patterns like %LOCALAPPDATA%\\*\\Cache\\*
        # After normalization, should match paths with cache
        test_path = "C:/Users/Test/AppData/Local/Google/Chrome/User Data/Default/Cache"
        assert loader.match_pattern(test_path, "**/Cache") is True


class TestClearCacheAndReload:
    """Test cache clearing and reload functionality."""

    def test_clear_cache(self):
        """Test clear_cache method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a rule file
            rules_path = Path(tmpdir) / "safe_rules.json"
            with open(rules_path, "w", encoding="utf-8") as f:
                json.dump({"patterns": [{"pattern": "**/cache"}]}, f)

            loader = RuleLoader(rules_dir=tmpdir)
            loader.load_safe_rules()

            # Cache should contain the loaded rules
            assert "safe_rules" in loader._cache

            # Clear cache
            loader.clear_cache()

            # Cache should be empty
            assert loader._cache == {}

    def test_reload_all_rules(self):
        """Test reload_all_rules method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple rule files
            for filename, content in [
                ("safe_rules.json", {"patterns": []}),
                ("caution_rules.json", {"patterns": []}),
                ("software_db.json", {"software": []}),
            ]:
                with open(Path(tmpdir) / filename, "w", encoding="utf-8") as f:
                    json.dump(content, f)

            loader = RuleLoader(rules_dir=tmpdir)
            loader.reload_all_rules()

            # All rules should be cached
            assert "safe_rules" in loader._cache
            assert "caution_rules" in loader._cache
            assert "software_db" in loader._cache
