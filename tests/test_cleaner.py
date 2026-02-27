"""
Tests for cleaner module in modules/cleaner.py
"""
import os
import tempfile
import pytest
from datetime import datetime

from config import Config
from modules.cleaner import Cleaner, CleanerStats
from modules.models import (
    RiskLevel,
    ClassificationResult,
    AIAnalysisResult,
)


class TestCleanerStats:
    """Test CleanerStats dataclass."""

    def test_cleaner_stats_defaults(self):
        """Test CleanerStats default values."""
        stats = CleanerStats()

        assert stats.deleted_count == 0
        assert stats.failed_count == 0
        assert stats.skipped_count == 0
        assert stats.total_size_freed == 0
        assert stats.failed_paths == []

    def test_cleaner_stats_custom_values(self):
        """Test CleanerStats with custom values."""
        stats = CleanerStats(
            deleted_count=5,
            failed_count=2,
            skipped_count=1,
            total_size_freed=1024 * 1024 * 100,  # 100 MB
            failed_paths=["/path/1", "/path/2"],
        )

        assert stats.deleted_count == 5
        assert stats.failed_count == 2
        assert stats.skipped_count == 1
        assert stats.total_size_freed == 104857600
        assert len(stats.failed_paths) == 2


class TestCleaner:
    """Test Cleaner class."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return Config()

    @pytest.fixture
    def cleaner(self, config):
        """Create a Cleaner instance."""
        return Cleaner(config)

    @pytest.fixture
    def temp_folder(self):
        """Create a temporary folder for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_cleaner_init(self, config):
        """Test Cleaner initialization."""
        cleaner = Cleaner(config)
        assert cleaner.config == config
        stats = cleaner.get_stats()
        assert stats.deleted_count == 0
        assert stats.failed_count == 0

    def test_delete_direct_file(self, cleaner, temp_folder):
        """Test direct deletion of a file."""
        # Create a test file
        test_file = os.path.join(temp_folder, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        assert os.path.exists(test_file)

        # Delete the file
        result = cleaner.delete_direct(test_file)

        assert result is True
        assert not os.path.exists(test_file)

        # Check stats
        stats = cleaner.get_stats()
        assert stats.deleted_count == 1
        assert stats.failed_count == 0

    def test_delete_direct_folder(self, cleaner, temp_folder):
        """Test direct deletion of a folder."""
        # Create a test folder with files
        test_folder = os.path.join(temp_folder, "test_folder")
        os.makedirs(test_folder)
        test_file = os.path.join(test_folder, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        assert os.path.exists(test_folder)
        assert os.path.exists(test_file)

        # Delete the folder
        result = cleaner.delete_direct(test_folder)

        assert result is True
        assert not os.path.exists(test_folder)

        # Check stats
        stats = cleaner.get_stats()
        assert stats.deleted_count == 1

    def test_delete_direct_nested_folder(self, cleaner, temp_folder):
        """Test direct deletion of nested folders."""
        # Create nested folder structure
        nested_folder = os.path.join(temp_folder, "level1", "level2", "level3")
        os.makedirs(nested_folder)

        # Create files at different levels
        file1 = os.path.join(temp_folder, "level1", "file1.txt")
        file2 = os.path.join(temp_folder, "level1", "level2", "file2.txt")
        file3 = os.path.join(nested_folder, "file3.txt")

        for f in [file1, file2, file3]:
            with open(f, "w") as fh:
                fh.write("content")

        # Delete the top-level folder
        result = cleaner.delete_direct(os.path.join(temp_folder, "level1"))

        assert result is True
        assert not os.path.exists(os.path.join(temp_folder, "level1"))

    def test_delete_direct_nonexistent_path(self, cleaner):
        """Test deleting a non-existent path."""
        result = cleaner.delete_direct("/nonexistent/path/12345")

        assert result is False
        stats = cleaner.get_stats()
        assert stats.failed_count == 1
        assert "/nonexistent/path/12345" in stats.failed_paths

    def test_delete_direct_size_tracking(self, cleaner, temp_folder):
        """Test that size is tracked correctly during deletion."""
        # Create a file with known size
        test_file = os.path.join(temp_folder, "size_test.txt")
        content = "x" * 1024  # 1 KB
        with open(test_file, "w") as f:
            f.write(content)

        # Delete and check size tracking
        cleaner.delete_direct(test_file)

        stats = cleaner.get_stats()
        # Size should be at least the content size (may include metadata)
        assert stats.total_size_freed >= 1024

    def test_delete_with_recycle_bin_true(self, cleaner, temp_folder):
        """Test delete with recycle bin enabled (falls back to direct delete)."""
        test_file = os.path.join(temp_folder, "recycle_test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        result = cleaner.delete(test_file, use_recycle_bin=True)

        assert result is True
        assert not os.path.exists(test_file)

    def test_delete_with_recycle_bin_false(self, cleaner, temp_folder):
        """Test delete with recycle bin disabled (direct delete)."""
        test_file = os.path.join(temp_folder, "direct_test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        result = cleaner.delete(test_file, use_recycle_bin=False)

        assert result is True
        assert not os.path.exists(test_file)

    def test_delete_uses_config_default(self, config, temp_folder):
        """Test that delete uses config default for recycle bin."""
        config.delete_use_recycle_bin = False
        cleaner = Cleaner(config)

        test_file = os.path.join(temp_folder, "config_test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        result = cleaner.delete(test_file)

        assert result is True
        assert not os.path.exists(test_file)

    def test_delete_batch(self, cleaner, temp_folder):
        """Test batch deletion of multiple paths."""
        # Create multiple test files
        paths = []
        for i in range(5):
            test_file = os.path.join(temp_folder, f"batch_{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"content {i}")
            paths.append(test_file)

        # Delete all
        results = cleaner.delete_batch(paths)

        assert len(results) == 5
        for path in paths:
            assert results[path] is True
            assert not os.path.exists(path)

        stats = cleaner.get_stats()
        assert stats.deleted_count == 5

    def test_delete_batch_with_failures(self, cleaner, temp_folder):
        """Test batch deletion with some failures."""
        # Create some files
        existing_paths = []
        for i in range(3):
            test_file = os.path.join(temp_folder, f"existing_{i}.txt")
            with open(test_file, "w") as f:
                f.write("content")
            existing_paths.append(test_file)

        # Mix with non-existent paths
        all_paths = existing_paths + ["/nonexistent/1", "/nonexistent/2"]

        results = cleaner.delete_batch(all_paths)

        assert len(results) == 5
        # Check existing files were deleted
        for path in existing_paths:
            assert results[path] is True
            assert not os.path.exists(path)

        # Check non-existent paths failed
        assert results["/nonexistent/1"] is False
        assert results["/nonexistent/2"] is False

        stats = cleaner.get_stats()
        assert stats.deleted_count == 3
        assert stats.failed_count == 2

    def test_delete_batch_with_progress_callback(self, cleaner, temp_folder):
        """Test batch deletion with progress callback."""
        # Create test files
        paths = []
        for i in range(3):
            test_file = os.path.join(temp_folder, f"progress_{i}.txt")
            with open(test_file, "w") as f:
                f.write("content")
            paths.append(test_file)

        # Track progress
        progress_calls = []

        def progress_callback(current, total, path, success):
            progress_calls.append({
                "current": current,
                "total": total,
                "path": path,
                "success": success,
            })

        cleaner.delete_batch(paths, progress_callback=progress_callback)

        assert len(progress_calls) == 3
        for i, call in enumerate(progress_calls):
            assert call["current"] == i + 1
            assert call["total"] == 3
            assert call["success"] is True

    def test_delete_classified(self, cleaner, temp_folder):
        """Test deletion of classification results."""
        # Create test folders
        paths = []
        for i in range(3):
            test_folder = os.path.join(temp_folder, f"classified_{i}")
            os.makedirs(test_folder)
            test_file = os.path.join(test_folder, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")
            paths.append(test_folder)

        # Create classification results with selected=True
        results_list = []
        for path in paths:
            result = ClassificationResult(
                path=path,
                risk_level=RiskLevel.SAFE,
                source_name="TestApp",
                confidence=0.9,
                evidence_chain=[],
                selected=True,
            )
            results_list.append(result)

        # Delete selected
        results = cleaner.delete_classified(results_list)

        assert len(results) == 3
        for path in paths:
            assert results[path] is True
            assert not os.path.exists(path)

        stats = cleaner.get_stats()
        assert stats.deleted_count == 3

    def test_delete_classified_only_selected(self, cleaner, temp_folder):
        """Test that only selected items are deleted."""
        # Create test folders
        selected_folder = os.path.join(temp_folder, "selected")
        not_selected_folder = os.path.join(temp_folder, "not_selected")

        os.makedirs(selected_folder)
        os.makedirs(not_selected_folder)

        with open(os.path.join(selected_folder, "test.txt"), "w") as f:
            f.write("content")
        with open(os.path.join(not_selected_folder, "test.txt"), "w") as f:
            f.write("content")

        # Create classification results
        selected_result = ClassificationResult(
            path=selected_folder,
            risk_level=RiskLevel.SAFE,
            source_name="TestApp",
            confidence=0.9,
            evidence_chain=[],
            selected=True,
        )

        not_selected_result = ClassificationResult(
            path=not_selected_folder,
            risk_level=RiskLevel.CAUTION,
            source_name="TestApp",
            confidence=0.5,
            evidence_chain=[],
            selected=False,
        )

        results = cleaner.delete_classified([selected_result, not_selected_result])

        assert results[selected_folder] is True
        assert not os.path.exists(selected_folder)
        assert os.path.exists(not_selected_folder)  # Should still exist

        stats = cleaner.get_stats()
        assert stats.deleted_count == 1
        assert stats.skipped_count == 1

    def test_delete_classified_with_progress(self, cleaner, temp_folder):
        """Test classification deletion with progress callback."""
        test_folder = os.path.join(temp_folder, "progress_test")
        os.makedirs(test_folder)

        result = ClassificationResult(
            path=test_folder,
            risk_level=RiskLevel.SAFE,
            source_name="Test",
            confidence=0.9,
            evidence_chain=[],
            selected=True,
        )

        progress_calls = []

        def progress_callback(current, total, path, success):
            progress_calls.append({"current": current, "total": total})

        cleaner.delete_classified([result], progress_callback=progress_callback)

        assert len(progress_calls) == 1
        assert progress_calls[0]["current"] == 1
        assert progress_calls[0]["total"] == 1

    def test_get_stats(self, cleaner, temp_folder):
        """Test get_stats returns correct statistics."""
        # Create and delete some files
        for i in range(3):
            test_file = os.path.join(temp_folder, f"stats_{i}.txt")
            with open(test_file, "w") as f:
                f.write("content")
            cleaner.delete_direct(test_file)

        stats = cleaner.get_stats()

        assert isinstance(stats, CleanerStats)
        assert stats.deleted_count == 3

    def test_reset_stats(self, cleaner, temp_folder):
        """Test resetting statistics."""
        # Create and delete a file
        test_file = os.path.join(temp_folder, "reset_test.txt")
        with open(test_file, "w") as f:
            f.write("content")
        cleaner.delete_direct(test_file)

        # Verify stats have values
        stats = cleaner.get_stats()
        assert stats.deleted_count == 1

        # Reset
        cleaner.reset_stats()

        # Verify stats are reset
        stats = cleaner.get_stats()
        assert stats.deleted_count == 0
        assert stats.failed_count == 0
        assert stats.skipped_count == 0
        assert stats.total_size_freed == 0
        assert stats.failed_paths == []

    def test_size_calculation_folder(self, cleaner, temp_folder):
        """Test size calculation for folders with multiple files."""
        # Create folder with multiple files
        test_folder = os.path.join(temp_folder, "size_folder")
        os.makedirs(test_folder)

        # Create files with known sizes
        for i in range(3):
            test_file = os.path.join(test_folder, f"file_{i}.txt")
            with open(test_file, "w") as f:
                f.write("x" * 1024)  # 1 KB each

        # Delete and verify size
        cleaner.delete_direct(test_folder)

        stats = cleaner.get_stats()
        # Should be at least 3 KB (3 files x 1 KB)
        assert stats.total_size_freed >= 3 * 1024


class TestCleanerIntegration:
    """Integration tests for Cleaner class."""

    @pytest.fixture
    def config(self):
        """Create a test config with specific settings."""
        config = Config()
        config.delete_use_recycle_bin = False
        return config

    @pytest.fixture
    def cleaner(self, config):
        """Create a Cleaner instance."""
        return Cleaner(config)

    @pytest.fixture
    def temp_folder(self):
        """Create a temporary folder for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_full_workflow(self, cleaner, temp_folder):
        """Test a full workflow with multiple operations."""
        # Create test structure
        folders = []
        for i in range(5):
            folder = os.path.join(temp_folder, f"workflow_{i}")
            os.makedirs(folder)
            with open(os.path.join(folder, "test.txt"), "w") as f:
                f.write("content")
            folders.append(folder)

        # Create classification results
        results = [
            ClassificationResult(
                path=folders[0],
                risk_level=RiskLevel.SAFE,
                source_name="App1",
                confidence=0.9,
                evidence_chain=[],
                selected=True,
            ),
            ClassificationResult(
                path=folders[1],
                risk_level=RiskLevel.SAFE,
                source_name="App2",
                confidence=0.85,
                evidence_chain=[],
                selected=True,
            ),
            ClassificationResult(
                path=folders[2],
                risk_level=RiskLevel.SUGGEST,
                source_name="App3",
                confidence=0.7,
                evidence_chain=[],
                selected=False,
            ),
        ]

        # Delete classified
        delete_results = cleaner.delete_classified(results)

        assert delete_results[folders[0]] is True
        assert delete_results[folders[1]] is True
        assert folders[2] in delete_results  # Should be in results even if skipped

        # Check stats
        stats = cleaner.get_stats()
        assert stats.deleted_count == 2
        assert stats.skipped_count == 1

        # Reset and do more operations
        cleaner.reset_stats()

        # Batch delete remaining
        remaining = [folders[3], folders[4]]
        batch_results = cleaner.delete_batch(remaining)

        assert batch_results[folders[3]] is True
        assert batch_results[folders[4]] is True

        stats = cleaner.get_stats()
        assert stats.deleted_count == 2
        assert stats.failed_count == 0
