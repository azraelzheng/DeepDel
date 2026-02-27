"""
Cleaner module for DeepDel application.

This module provides functionality for safely deleting files and folders,
with support for recycle bin, statistics tracking, and batch operations.
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

from config import Config
from modules.models import ClassificationResult


@dataclass
class CleanerStats:
    """
    Statistics for deletion operations.

    Attributes:
        deleted_count: Number of successfully deleted items
        failed_count: Number of failed deletions
        skipped_count: Number of skipped items (not selected for deletion)
        total_size_freed: Total size freed in bytes
        failed_paths: List of paths that failed to delete
    """

    deleted_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_size_freed: int = 0
    failed_paths: List[str] = field(default_factory=list)


class Cleaner:
    """
    Cleaner class for managing file and folder deletion.

    Provides methods for single and batch deletion operations,
    with support for recycle bin and statistics tracking.
    """

    def __init__(self, config: Config):
        """
        Initialize the Cleaner with configuration.

        Args:
            config: Configuration instance containing delete settings
        """
        self.config = config
        self._stats = CleanerStats()

    def delete(self, path: str, use_recycle_bin: bool = None) -> bool:
        """
        Delete a file or folder.

        Uses recycle bin if configured and available, otherwise
        performs direct deletion.

        Args:
            path: Path to the file or folder to delete
            use_recycle_bin: Whether to use recycle bin. If None, uses config setting.

        Returns:
            True if deletion was successful, False otherwise
        """
        if use_recycle_bin is None:
            use_recycle_bin = self.config.delete_use_recycle_bin

        if use_recycle_bin:
            return self._delete_with_recycle_bin(path)
        else:
            return self.delete_direct(path)

    def delete_direct(self, path: str) -> bool:
        """
        Permanently delete a file or folder (bypass recycle bin).

        Args:
            path: Path to the file or folder to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not os.path.exists(path):
            self._update_stats_failure(path)
            return False

        try:
            # Calculate size before deletion for stats
            size = self._get_path_size(path)

            # Perform deletion
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)

            # Update stats
            self._update_stats_success(size)
            return True

        except PermissionError:
            self._update_stats_failure(path)
            return False
        except OSError:
            self._update_stats_failure(path)
            return False

    def delete_batch(
        self,
        paths: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, bool]:
        """
        Delete multiple paths in batch.

        Args:
            paths: List of paths to delete
            progress_callback: Optional callback function for progress updates.
                Signature: callback(current: int, total: int, path: str, success: bool)

        Returns:
            Dictionary mapping paths to deletion success status
        """
        results = {}
        total = len(paths)

        for i, path in enumerate(paths, 1):
            success = self.delete_direct(path)
            results[path] = success

            if progress_callback:
                progress_callback(i, total, path, success)

        return results

    def delete_classified(
        self,
        classified_results: List[ClassificationResult],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, bool]:
        """
        Delete classified folders based on their selection status.

        Only deletes folders where selected=True in the ClassificationResult.

        Args:
            classified_results: List of ClassificationResult objects
            progress_callback: Optional callback function for progress updates.
                Signature: callback(current: int, total: int, path: str, success: bool)

        Returns:
            Dictionary mapping paths to deletion success status
        """
        results = {}
        total = len(classified_results)

        for i, result in enumerate(classified_results, 1):
            path = result.path

            if result.selected:
                success = self.delete_direct(path)
                results[path] = success
            else:
                # Skip non-selected items
                self._update_stats_skipped()
                results[path] = None  # Use None to indicate skipped

            if progress_callback:
                # For skipped items, pass None for success
                success_value = results[path] if results[path] is not None else None
                progress_callback(i, total, path, success_value)

        return results

    def get_stats(self) -> CleanerStats:
        """
        Get current deletion statistics.

        Returns:
            CleanerStats instance with current statistics
        """
        return self._stats

    def reset_stats(self) -> None:
        """Reset all statistics to default values."""
        self._stats = CleanerStats()

    def _delete_with_recycle_bin(self, path: str) -> bool:
        """
        Delete using recycle bin if available, fallback to direct delete.

        Args:
            path: Path to delete

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(path):
            self._update_stats_failure(path)
            return False

        try:
            # Calculate size before deletion
            size = self._get_path_size(path)

            # Try to use send2trash
            try:
                from send2trash import send2trash
                send2trash(path)
                self._update_stats_success(size)
                return True
            except ImportError:
                # Fallback to direct delete if send2trash not available
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                self._update_stats_success(size)
                return True

        except PermissionError:
            self._update_stats_failure(path)
            return False
        except OSError:
            self._update_stats_failure(path)
            return False

    def _get_path_size(self, path: str) -> int:
        """
        Calculate the size of a file or folder in bytes.

        Args:
            path: Path to calculate size for

        Returns:
            Size in bytes
        """
        if os.path.isfile(path):
            try:
                return os.path.getsize(path)
            except (OSError, PermissionError):
                return 0
        else:
            total_size = 0
            try:
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass
            return total_size

    def _update_stats_success(self, size: int) -> None:
        """
        Update statistics for successful deletion.

        Args:
            size: Size of deleted item in bytes
        """
        self._stats.deleted_count += 1
        self._stats.total_size_freed += size

    def _update_stats_failure(self, path: str) -> None:
        """
        Update statistics for failed deletion.

        Args:
            path: Path that failed to delete
        """
        self._stats.failed_count += 1
        self._stats.failed_paths.append(path)

    def _update_stats_skipped(self) -> None:
        """Update statistics for skipped item."""
        self._stats.skipped_count += 1
