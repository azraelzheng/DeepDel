"""
Tests for registry utility functions in utils/registry.py
"""

import os
import sys
import pytest
from typing import Dict, List, Optional

# Skip all tests on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Registry functions are Windows-only"
)


class TestCheckProgramInstalled:
    """Test check_program_installed function."""

    def test_function_exists(self):
        """Test that the function can be imported."""
        from utils.registry import check_program_installed
        assert callable(check_program_installed)

    def test_returns_optional_bool(self):
        """Test that function returns Optional[bool]."""
        from utils.registry import check_program_installed

        # Test with a registry key that likely doesn't exist
        result = check_program_installed("NonExistentProgram_12345")
        assert result is None or isinstance(result, bool)

    def test_with_empty_key(self):
        """Test with empty registry key."""
        from utils.registry import check_program_installed

        result = check_program_installed("")
        assert result is None or isinstance(result, bool)

    def test_with_none_key(self):
        """Test with None registry key."""
        from utils.registry import check_program_installed

        result = check_program_installed(None)
        assert result is None or isinstance(result, bool)


class TestGetInstalledPrograms:
    """Test get_installed_programs function."""

    def test_function_exists(self):
        """Test that the function can be imported."""
        from utils.registry import get_installed_programs
        assert callable(get_installed_programs)

    def test_returns_list(self):
        """Test that function returns a list."""
        from utils.registry import get_installed_programs

        result = get_installed_programs()
        assert isinstance(result, list)

    def test_list_contains_dicts(self):
        """Test that the returned list contains dictionaries."""
        from utils.registry import get_installed_programs

        result = get_installed_programs()
        assert isinstance(result, list)
        # If there are programs, check that they're dicts
        if result:
            for item in result:
                assert isinstance(item, dict)

    def test_program_dict_has_expected_keys(self):
        """Test that program dictionaries have expected keys."""
        from utils.registry import get_installed_programs

        result = get_installed_programs()
        # Common keys that should be present (if any programs exist)
        expected_keys = ['name', 'key', 'install_location']
        if result:
            # At least some programs should have 'name' key
            programs_with_name = [p for p in result if 'name' in p]
            assert len(programs_with_name) > 0 or len(result) == 0


class TestGetMruEntries:
    """Test get_mru_entries function."""

    def test_function_exists(self):
        """Test that the function can be imported."""
        from utils.registry import get_mru_entries
        assert callable(get_mru_entries)

    def test_returns_list(self):
        """Test that function returns a list."""
        from utils.registry import get_mru_entries

        result = get_mru_entries()
        assert isinstance(result, list)

    def test_list_contains_dicts(self):
        """Test that the returned list contains dictionaries."""
        from utils.registry import get_mru_entries

        result = get_mru_entries()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_mru_dict_has_expected_keys(self):
        """Test that MRU dictionaries have expected keys."""
        from utils.registry import get_mru_entries

        result = get_mru_entries()
        # Each MRU entry should have 'source' and 'entries' keys
        for item in result:
            assert 'source' in item
            assert isinstance(item['source'], str)


class TestFindShortcutTarget:
    """Test find_shortcut_target function."""

    def test_function_exists(self):
        """Test that the function can be imported."""
        from utils.registry import find_shortcut_target
        assert callable(find_shortcut_target)

    def test_returns_optional_str(self):
        """Test that function returns Optional[str]."""
        from utils.registry import find_shortcut_target

        result = find_shortcut_target("NonExistentFolder_12345")
        assert result is None or isinstance(result, str)

    def test_with_empty_folder_name(self):
        """Test with empty folder name."""
        from utils.registry import find_shortcut_target

        result = find_shortcut_target("")
        assert result is None or isinstance(result, str)

    def test_with_none_folder_name(self):
        """Test with None folder name."""
        from utils.registry import find_shortcut_target

        result = find_shortcut_target(None)
        assert result is None or isinstance(result, str)


class TestRegistryErrorHandling:
    """Test error handling in registry functions."""

    def test_get_installed_programs_handles_errors(self):
        """Test that get_installed_programs handles errors gracefully."""
        from utils.registry import get_installed_programs

        # Should not raise any exceptions
        result = get_installed_programs()
        assert isinstance(result, list)

    def test_get_mru_entries_handles_errors(self):
        """Test that get_mru_entries handles errors gracefully."""
        from utils.registry import get_mru_entries

        # Should not raise any exceptions
        result = get_mru_entries()
        assert isinstance(result, list)

    def test_check_program_installed_handles_errors(self):
        """Test that check_program_installed handles errors gracefully."""
        from utils.registry import check_program_installed

        # Should not raise any exceptions even with invalid input
        result = check_program_installed("Invalid\0Key")
        assert result is None or isinstance(result, bool)
