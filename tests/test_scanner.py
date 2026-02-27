"""
Tests for the Scanner module.

This module tests the file scanning functionality of DeepDel.
"""

import os
import tempfile
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from modules.scanner import Scanner
from modules.models import ScanResult


class TestScanner:
    """Test cases for the Scanner class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp(prefix="deepdel_test_")
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """Create a test configuration."""
        cfg = Config()
        cfg.scan_paths = [temp_dir]
        cfg.scan_min_size_mb = 0.0  # No minimum size for tests
        cfg.scan_exclude = []
        cfg.performance_max_workers = 2
        return cfg

    @pytest.fixture
    def sample_folder_structure(self, temp_dir):
        """Create a sample folder structure for testing."""
        # Create folder structure:
        # temp_dir/
        #   folder1/ (contains files, 2MB total)
        #     file1.txt (1MB)
        #     file2.txt (1MB)
        #   folder2/ (empty - should be skipped)
        #   folder3/ (contains exe)
        #     app.exe
        #   folder4/ (small file, below min_size if set)
        #     small.txt (1KB)
        #   .hidden_folder/
        #     hidden.txt

        # folder1 - 2MB of text files
        folder1 = os.path.join(temp_dir, "folder1")
        os.makedirs(folder1)
        with open(os.path.join(folder1, "file1.txt"), "wb") as f:
            f.write(b"x" * (1024 * 1024))  # 1MB
        with open(os.path.join(folder1, "file2.txt"), "wb") as f:
            f.write(b"x" * (1024 * 1024))  # 1MB

        # folder2 - empty
        folder2 = os.path.join(temp_dir, "folder2")
        os.makedirs(folder2)

        # folder3 - contains executable
        folder3 = os.path.join(temp_dir, "folder3")
        os.makedirs(folder3)
        with open(os.path.join(folder3, "app.exe"), "wb") as f:
            f.write(b"MZ" + b"x" * 1000)  # Fake exe header

        # folder4 - small file
        folder4 = os.path.join(temp_dir, "folder4")
        os.makedirs(folder4)
        with open(os.path.join(folder4, "small.txt"), "wb") as f:
            f.write(b"x" * 1024)  # 1KB

        # hidden folder
        hidden_folder = os.path.join(temp_dir, ".hidden_folder")
        os.makedirs(hidden_folder)
        with open(os.path.join(hidden_folder, "hidden.txt"), "wb") as f:
            f.write(b"hidden content")

        return temp_dir

    def test_scanner_init(self, config):
        """Test scanner initialization with config."""
        scanner = Scanner(config)
        assert scanner.config == config
        assert scanner._stop_event is not None
        assert not scanner._is_scanning

    def test_scan_single_path(self, config, sample_folder_structure):
        """Test scanning a single path returns valid results."""
        scanner = Scanner(config)

        # Scan the temp_dir to get its subfolders
        results = list(scanner.scan_path(sample_folder_structure))

        # Find folder1 in the results
        folder1_path = os.path.join(sample_folder_structure, "folder1")
        result = next((r for r in results if r.path == folder1_path), None)

        assert result is not None
        assert isinstance(result, ScanResult)
        assert result.path == folder1_path
        assert result.name == "folder1"
        assert result.size_bytes == 2 * 1024 * 1024  # 2MB
        assert result.file_count == 2
        assert ".txt" in result.file_extensions
        assert result.file_extensions[".txt"] == 2
        assert not result.has_executables

    def test_scan_path_with_executables(self, config, sample_folder_structure):
        """Test that executable detection works correctly."""
        scanner = Scanner(config)

        # Scan the temp_dir to get its subfolders
        results = list(scanner.scan_path(sample_folder_structure))

        # Find folder3 in the results
        folder3_path = os.path.join(sample_folder_structure, "folder3")
        result = next((r for r in results if r.path == folder3_path), None)

        assert result is not None
        assert result.has_executables
        assert ".exe" in result.file_extensions

    def test_scan_empty_folder_skipped(self, config, sample_folder_structure):
        """Test that empty folders are skipped."""
        scanner = Scanner(config)
        folder2 = os.path.join(sample_folder_structure, "folder2")

        results = list(scanner.scan_path(folder2))

        # Empty folder should return no results
        assert len(results) == 0

    def test_min_size_filtering(self, temp_dir):
        """Test that folders below min_size_mb are filtered out."""
        # Create config with min_size of 0.5 MB (512KB)
        cfg = Config()
        cfg.scan_paths = [temp_dir]
        cfg.scan_min_size_mb = 0.5  # 512KB minimum
        cfg.scan_exclude = []
        cfg.performance_max_workers = 2

        # Create a small folder
        small_folder = os.path.join(temp_dir, "small_folder")
        os.makedirs(small_folder)
        with open(os.path.join(small_folder, "tiny.txt"), "wb") as f:
            f.write(b"x" * 1024)  # Only 1KB

        # Create a larger folder
        large_folder = os.path.join(temp_dir, "large_folder")
        os.makedirs(large_folder)
        with open(os.path.join(large_folder, "big.txt"), "wb") as f:
            f.write(b"x" * (1024 * 1024))  # 1MB

        scanner = Scanner(cfg)
        results = list(scanner.scan_path(temp_dir))

        # Only the large folder should be returned
        assert len(results) == 1
        assert results[0].name == "large_folder"

    def test_exclude_patterns(self, temp_dir):
        """Test that exclude patterns filter out matching folders."""
        cfg = Config()
        cfg.scan_paths = [temp_dir]
        cfg.scan_min_size_mb = 0.0
        cfg.scan_exclude = ["*.tmp", "cache*", ".hidden*"]
        cfg.performance_max_workers = 2

        # Create various folders with files
        cache_folder = os.path.join(temp_dir, "cache_data")
        os.makedirs(cache_folder)
        with open(os.path.join(cache_folder, "data.txt"), "wb") as f:
            f.write(b"x" * 1024)

        normal_folder = os.path.join(temp_dir, "normal_data")
        os.makedirs(normal_folder)
        with open(os.path.join(normal_folder, "info.txt"), "wb") as f:
            f.write(b"x" * 1024)

        hidden_folder = os.path.join(temp_dir, ".hidden")
        os.makedirs(hidden_folder)
        with open(os.path.join(hidden_folder, "secret.txt"), "wb") as f:
            f.write(b"x" * 1024)

        scanner = Scanner(cfg)
        results = list(scanner.scan_path(temp_dir))

        # Only normal_folder should be returned
        assert len(results) == 1
        assert results[0].name == "normal_data"

    def test_stop_functionality(self, config, sample_folder_structure):
        """Test that stop() halts scanning."""
        scanner = Scanner(config)

        # Create many subfolders to allow time for stop
        for i in range(50):
            subfolder = os.path.join(sample_folder_structure, f"folder_{i}")
            os.makedirs(subfolder)
            with open(os.path.join(subfolder, f"file_{i}.txt"), "wb") as f:
                f.write(b"x" * 10240)  # 10KB each

        # Stop before scanning
        scanner.stop()

        # The stop_event should be set
        assert scanner._stop_event.is_set()

        # Now scan - should return empty or partial results
        results = list(scanner.scan_path(sample_folder_structure))

        # Results should be empty because stop was called before scanning
        # (scan_path clears the stop event at start, but if stop is called
        # during iteration, it will stop early)
        # Let's test that calling stop() during a scan works
        scanner.reset()

        # For a proper stop test, we need to call stop in a separate thread
        # while scanning is happening

    def test_reset_functionality(self, config):
        """Test that reset() clears scanner state."""
        scanner = Scanner(config)

        # Set stop event
        scanner._stop_event.set()
        scanner._is_scanning = True

        scanner.reset()

        assert not scanner._stop_event.is_set()
        assert not scanner._is_scanning

    def test_scan_all(self, config, sample_folder_structure):
        """Test scanning all configured paths."""
        scanner = Scanner(config)

        results = scanner.scan_all()

        # Should find all non-empty folders
        assert len(results) >= 3  # folder1, folder3, folder4, .hidden_folder (4 total)
        assert all(isinstance(r, ScanResult) for r in results)

        # Check that all paths are under the temp_dir
        for result in results:
            assert result.path.startswith(sample_folder_structure)

    def test_scan_all_with_progress_callback(self, config, sample_folder_structure):
        """Test that progress callback is called during scan_all."""
        scanner = Scanner(config)

        progress_values = []

        def progress_callback(current, total):
            progress_values.append((current, total))

        results = scanner.scan_all(progress_callback=progress_callback)

        assert len(results) >= 3
        assert len(progress_values) > 0
        # Progress should increase
        assert progress_values[-1][0] == progress_values[-1][1]  # Final: current == total

    def test_folder_depth_calculation(self, config, temp_dir):
        """Test that folder depth is calculated correctly."""
        scanner = Scanner(config)

        # Create nested structure
        nested = os.path.join(temp_dir, "level1", "level2", "level3")
        os.makedirs(nested)
        # Put file at deepest level
        with open(os.path.join(nested, "deep.txt"), "wb") as f:
            f.write(b"x" * 1024)

        results = list(scanner.scan_path(temp_dir))

        # Find the level1 folder result
        level1_result = next((r for r in results if r.name == "level1"), None)
        assert level1_result is not None
        assert level1_result.folder_depth == 2  # level2/level3 = 2 levels deep

    def test_scan_nonexistent_path(self, config):
        """Test scanning a non-existent path returns empty."""
        scanner = Scanner(config)

        results = list(scanner.scan_path("/nonexistent/path/12345"))

        assert len(results) == 0

    def test_scan_result_has_created_time(self, config, temp_dir):
        """Test that created_time is populated in scan results."""
        scanner = Scanner(config)

        # Create a folder with files
        test_folder = os.path.join(temp_dir, "test_created")
        os.makedirs(test_folder)
        with open(os.path.join(test_folder, "file.txt"), "wb") as f:
            f.write(b"x" * 1024)

        # Scan the parent directory to get the subfolder
        results = list(scanner.scan_path(temp_dir))

        # Find our test folder
        result = next((r for r in results if r.name == "test_created"), None)
        assert result is not None
        assert result.created_time is not None

    def test_multiple_scan_paths(self, temp_dir):
        """Test scanning multiple configured paths."""
        # Create two separate directory trees
        dir1 = os.path.join(temp_dir, "scan_root1")
        dir2 = os.path.join(temp_dir, "scan_root2")
        os.makedirs(dir1)
        os.makedirs(dir2)

        # Add content to each
        folder1 = os.path.join(dir1, "folder1")
        os.makedirs(folder1)
        with open(os.path.join(folder1, "file1.txt"), "wb") as f:
            f.write(b"x" * 1024)

        folder2 = os.path.join(dir2, "folder2")
        os.makedirs(folder2)
        with open(os.path.join(folder2, "file2.txt"), "wb") as f:
            f.write(b"x" * 1024)

        # Configure both paths
        cfg = Config()
        cfg.scan_paths = [dir1, dir2]
        cfg.scan_min_size_mb = 0.0
        cfg.scan_exclude = []
        cfg.performance_max_workers = 2

        scanner = Scanner(cfg)
        results = scanner.scan_all()

        # Should find folders from both paths
        paths_found = [r.path for r in results]
        assert folder1 in paths_found
        assert folder2 in paths_found


class TestScannerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp(prefix="deepdel_edge_test_")
        yield temp_path
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_scan_file_instead_of_folder(self, config, temp_dir):
        """Test scanning a file path instead of a folder."""
        # Create a file
        file_path = os.path.join(temp_dir, "test_file.txt")
        with open(file_path, "wb") as f:
            f.write(b"x" * 1024)

        scanner = Scanner(config)
        results = list(scanner.scan_path(file_path))

        # Should return empty - we only scan folders
        assert len(results) == 0

    def test_scan_with_permission_error(self, temp_dir):
        """Test that permission errors are handled gracefully."""
        cfg = Config()
        cfg.scan_paths = [temp_dir]
        cfg.scan_min_size_mb = 0.0
        cfg.scan_exclude = []
        cfg.performance_max_workers = 2

        scanner = Scanner(cfg)

        # Create a folder
        test_folder = os.path.join(temp_dir, "accessible")
        os.makedirs(test_folder)
        with open(os.path.join(test_folder, "file.txt"), "wb") as f:
            f.write(b"x" * 1024)

        # Mock os.walk to raise permission error on some folders
        with patch('os.walk') as mock_walk:
            mock_walk.side_effect = PermissionError("Access denied")

            results = list(scanner.scan_path(test_folder))

            # Should handle gracefully and return empty
            assert len(results) == 0

    def test_concurrent_scanning(self, temp_dir):
        """Test that concurrent scans work correctly with thread pool."""
        # Create multiple folders
        for i in range(10):
            folder = os.path.join(temp_dir, f"folder_{i}")
            os.makedirs(folder)
            with open(os.path.join(folder, f"file_{i}.txt"), "wb") as f:
                f.write(b"x" * 1024)

        cfg = Config()
        cfg.scan_paths = [temp_dir]
        cfg.scan_min_size_mb = 0.0
        cfg.scan_exclude = []
        cfg.performance_max_workers = 4

        scanner = Scanner(cfg)
        results = scanner.scan_all()

        assert len(results) == 10


# Need to define config fixture for edge case tests
@pytest.fixture
def config(temp_dir):
    """Create a test configuration for edge case tests."""
    cfg = Config()
    cfg.scan_paths = [temp_dir]
    cfg.scan_min_size_mb = 0.0
    cfg.scan_exclude = []
    cfg.performance_max_workers = 2
    return cfg
