"""
Tests for process utility functions in utils/process.py
"""

import pytest
from typing import Dict, List, Optional


class TestGetRunningProcesses:
    """Test get_running_processes function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        from utils.process import get_running_processes

        result = get_running_processes()
        assert isinstance(result, list)

    def test_returns_non_empty_list(self):
        """Test that function returns a non-empty list on running system."""
        from utils.process import get_running_processes

        result = get_running_processes()
        # There should always be at least some processes running
        assert len(result) > 0

    def test_process_info_has_required_keys(self):
        """Test that each process info dict has required keys."""
        from utils.process import get_running_processes

        result = get_running_processes()
        required_keys = {'pid', 'name', 'exe', 'cmdline'}

        if result:  # If there are processes
            first_process = result[0]
            assert required_keys.issubset(first_process.keys())

    def test_process_pid_is_int(self):
        """Test that pid is an integer."""
        from utils.process import get_running_processes

        result = get_running_processes()
        if result:
            assert isinstance(result[0]['pid'], int)

    def test_process_name_is_string(self):
        """Test that name is a string."""
        from utils.process import get_running_processes

        result = get_running_processes()
        if result:
            assert isinstance(result[0]['name'], str)


class TestIsProcessRunning:
    """Test is_process_running function."""

    def test_explorer_is_running(self):
        """Test that explorer.exe is running on Windows."""
        from utils.process import is_process_running

        # explorer.exe is typically running on Windows
        result = is_process_running("explorer.exe")
        assert result is True

    def test_case_insensitive_match(self):
        """Test that process name matching is case insensitive."""
        from utils.process import is_process_running

        # Test with different case
        result = is_process_running("EXPLORER.EXE")
        assert result is True

    def test_non_existent_process(self):
        """Test with a process that definitely doesn't exist."""
        from utils.process import is_process_running

        result = is_process_running("nonexistent_process_xyz_12345.exe")
        assert result is False

    def test_empty_string(self):
        """Test with empty string."""
        from utils.process import is_process_running

        result = is_process_running("")
        assert result is False


class TestFindProcessByFolder:
    """Test find_process_by_folder function."""

    def test_returns_dict_or_none(self):
        """Test that function returns a dict or None."""
        from utils.process import find_process_by_folder

        result = find_process_by_folder("nonexistent_folder_xyz_12345")
        assert result is None or isinstance(result, dict)

    def test_non_existent_folder_returns_none(self):
        """Test that non-existent folder returns None."""
        from utils.process import find_process_by_folder

        result = find_process_by_folder("nonexistent_folder_xyz_12345")
        assert result is None

    def test_empty_string_returns_none(self):
        """Test with empty string."""
        from utils.process import find_process_by_folder

        result = find_process_by_folder("")
        assert result is None

    def test_found_process_has_required_keys(self):
        """Test that found process has all required keys."""
        from utils.process import find_process_by_folder

        # Try to find a process related to Windows folder
        result = find_process_by_folder("Windows")
        if result:  # If a process is found
            required_keys = {'pid', 'name', 'exe', 'cmdline'}
            assert required_keys.issubset(result.keys())
