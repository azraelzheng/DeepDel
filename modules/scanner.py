"""
File Scanner Module for DeepDel application.

This module provides the Scanner class for scanning directories and
collecting information about folders for deletion analysis.
"""

import fnmatch
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Generator, List, Optional

from config import Config
from modules.models import ScanResult
from utils.file_utils import (
    count_files_in_folder,
    get_file_extensions,
    get_folder_depth,
    get_folder_size,
    get_last_access_time,
    has_executables,
    is_folder_empty,
)


class Scanner:
    """
    Scanner class for scanning directories and collecting folder information.

    This class provides functionality to scan directories recursively,
    apply filters based on size and exclude patterns, and return
    ScanResult objects containing detailed information about each folder.

    Attributes:
        config: Configuration object containing scan settings.
    """

    def __init__(self, config: Config):
        """
        Initialize the Scanner with configuration.

        Args:
            config: Configuration object containing scan settings including:
                - scan_min_size_mb: Minimum folder size in MB to include
                - scan_exclude: List of patterns to exclude
                - performance_max_workers: Number of threads for parallel scanning
        """
        self.config = config
        self._stop_event = threading.Event()
        self._is_scanning = False
        self._lock = threading.Lock()

    def scan_path(self, path: str) -> Generator[ScanResult, None, None]:
        """
        Scan a single path and yield ScanResult for each valid folder.

        This method scans the given path recursively, applying size filters
        and exclude patterns from the configuration. It collects detailed
        information about each folder including size, file count, extensions,
        and more.

        Args:
            path: Path to scan. Can be a file or directory.
                  If it's a file, yields nothing.
                  If it's a directory, yields ScanResult for each valid subfolder.

        Yields:
            ScanResult: Result object for each folder that passes all filters.

        Note:
            - Empty folders are skipped
            - Folders below min_size_mb are skipped
            - Folders matching exclude patterns are skipped
            - Permission errors are handled gracefully
        """
        if not os.path.exists(path):
            return

        # If path is a file, not a folder, return nothing
        if not os.path.isdir(path):
            return

        # Reset stop event for new scan
        self._stop_event.clear()

        with self._lock:
            self._is_scanning = True

        try:
            # Get immediate subfolders to scan
            subfolders = self._get_subfolders(path)

            # Use thread pool for parallel scanning
            max_workers = self.config.performance_max_workers

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all subfolder scanning tasks
                future_to_folder = {
                    executor.submit(self._scan_single_folder, folder): folder
                    for folder in subfolders
                }

                # Process results as they complete
                for future in as_completed(future_to_folder):
                    if self._stop_event.is_set():
                        # Cancel remaining futures
                        for f in future_to_folder:
                            f.cancel()
                        break

                    try:
                        result = future.result()
                        if result is not None:
                            yield result
                    except Exception:
                        # Handle any unexpected errors gracefully
                        pass
        finally:
            with self._lock:
                self._is_scanning = False

    def _get_subfolders(self, path: str) -> List[str]:
        """
        Get list of immediate subfolders in a path.

        Args:
            path: Parent directory path.

        Returns:
            List of full paths to immediate subfolders.
        """
        subfolders = []
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    subfolders.append(full_path)
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass
        return subfolders

    def _scan_single_folder(self, folder_path: str) -> Optional[ScanResult]:
        """
        Scan a single folder and return its ScanResult.

        This method collects all information about a folder including:
        - Size in bytes
        - File count
        - File extensions
        - Executable presence
        - Last access time
        - Folder depth
        - Creation time

        Args:
            folder_path: Full path to the folder to scan.

        Returns:
            ScanResult if folder passes all filters, None otherwise.
        """
        if self._stop_event.is_set():
            return None

        folder_name = os.path.basename(folder_path)

        # Check exclude patterns
        if self._should_exclude(folder_name):
            return None

        try:
            # Skip empty folders
            if is_folder_empty(folder_path):
                return None

            # Get folder size
            size_bytes = get_folder_size(folder_path)

            # Check minimum size filter
            min_size_bytes = self.config.scan_min_size_mb * 1024 * 1024
            if size_bytes < min_size_bytes:
                return None

            if self._stop_event.is_set():
                return None

            # Collect folder information
            file_count = count_files_in_folder(folder_path)
            file_extensions = get_file_extensions(folder_path)
            has_exe = has_executables(folder_path)
            last_access = get_last_access_time(folder_path)
            folder_depth = get_folder_depth(folder_path)
            created_time = self._get_created_time(folder_path)

            # Create and return ScanResult
            return ScanResult(
                path=folder_path,
                name=folder_name,
                size_bytes=size_bytes,
                file_count=file_count,
                last_access=last_access or datetime.now(),
                is_folder=True,
                file_extensions=file_extensions,
                has_executables=has_exe,
                folder_depth=folder_depth,
                created_time=created_time,
            )

        except (PermissionError, OSError):
            # Skip folders we can't access
            return None
        except Exception:
            # Handle any other unexpected errors
            return None

    def _should_exclude(self, name: str) -> bool:
        """
        Check if a folder name matches any exclude pattern.

        Args:
            name: Folder name to check.

        Returns:
            True if folder should be excluded, False otherwise.
        """
        for pattern in self.config.scan_exclude:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _get_created_time(self, path: str) -> Optional[datetime]:
        """
        Get creation time of a folder.

        Args:
            path: Path to the folder.

        Returns:
            Datetime object representing creation time, or None if unavailable.
        """
        try:
            creation_time = os.path.getctime(path)
            return datetime.fromtimestamp(creation_time)
        except (OSError, PermissionError):
            return None

    def scan_all(
        self, progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ScanResult]:
        """
        Scan all configured paths and return list of results.

        This method scans all paths configured in config.scan_paths,
        applying all filters and collecting detailed folder information.

        Args:
            progress_callback: Optional callback function called with
                (current, total) progress values during scanning.

        Returns:
            List of ScanResult objects for all valid folders found.

        Note:
            - Uses config.get_expanded_scan_paths() to expand environment variables
            - Results from all paths are combined into a single list
            - Progress callback is called after each path is processed
        """
        all_results: List[ScanResult] = []

        # Reset stop event for new scan
        self._stop_event.clear()

        # Get expanded scan paths (expands environment variables)
        scan_paths = self.config.get_expanded_scan_paths()
        total_paths = len(scan_paths)

        with self._lock:
            self._is_scanning = True

        try:
            for idx, path in enumerate(scan_paths):
                if self._stop_event.is_set():
                    break

                # Scan each configured path
                for result in self.scan_path(path):
                    all_results.append(result)

                # Report progress
                if progress_callback:
                    progress_callback(idx + 1, total_paths)
        finally:
            with self._lock:
                self._is_scanning = False

        return all_results

    def stop(self) -> None:
        """
        Stop the current scanning operation.

        This method sets the stop event, which signals all scanning
        threads to stop processing and return early.
        """
        self._stop_event.set()

    def reset(self) -> None:
        """
        Reset the scanner state.

        This method clears the stop event and resets the scanning state,
        allowing a new scan to be started.
        """
        self._stop_event.clear()
        with self._lock:
            self._is_scanning = False

    @property
    def is_scanning(self) -> bool:
        """
        Check if a scan is currently in progress.

        Returns:
            True if scanning is in progress, False otherwise.
        """
        with self._lock:
            return self._is_scanning
