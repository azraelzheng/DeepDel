"""
File utility functions for DeepDel application.

This module provides utility functions for working with files and folders,
including size calculations, file counting, extension analysis, and more.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def get_folder_size(path: str) -> int:
    """
    Get total size of folder in bytes.

    Recursively calculates the total size of all files in the folder
    and its subfolders.

    Args:
        path: Path to the folder.

    Returns:
        Total size in bytes.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, PermissionError):
                # Skip files that cannot be accessed
                pass
    return total_size


def count_files_in_folder(path: str) -> int:
    """
    Count all files recursively in a folder.

    Args:
        path: Path to the folder.

    Returns:
        Total number of files in the folder and all subfolders.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    file_count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        file_count += len(filenames)
    return file_count


def get_file_extensions(path: str) -> Dict[str, int]:
    """
    Get file extension statistics for a folder.

    Recursively scans all files in the folder and counts occurrences
    of each file extension. Extensions are converted to lowercase.

    Args:
        path: Path to the folder.

    Returns:
        Dictionary mapping file extensions (including the dot) to counts.
        Files without extension are counted under empty string key.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    extensions: Dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            # Get extension (including the dot), lowercase
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            extensions[ext] = extensions.get(ext, 0) + 1
    return extensions


def is_folder_empty(path: str) -> bool:
    """
    Check if a folder is empty.

    A folder is considered empty if it contains no files and no subfolders.

    Args:
        path: Path to the folder.

    Returns:
        True if the folder is empty, False otherwise.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    # Use os.listdir to check if folder has any contents
    return len(os.listdir(path)) == 0


def has_executables(path: str) -> bool:
    """
    Check if folder contains executable files.

    Recursively searches for files with executable extensions:
    .exe, .msi, .bat, .cmd

    Args:
        path: Path to the folder.

    Returns:
        True if any executable file is found, False otherwise.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    executable_extensions = {".exe", ".msi", ".bat", ".cmd"}

    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext.lower() in executable_extensions:
                return True
    return False


def get_last_access_time(path: str) -> Optional[datetime]:
    """
    Get last access time of a file or folder.

    Args:
        path: Path to the file or folder.

    Returns:
        Datetime object representing the last access time,
        or None if the path does not exist or cannot be accessed.
    """
    if not os.path.exists(path):
        return None

    try:
        access_time = os.path.getatime(path)
        return datetime.fromtimestamp(access_time)
    except (OSError, PermissionError):
        return None


def get_folder_depth(path: str) -> int:
    """
    Calculate maximum directory depth of a folder.

    The depth is the maximum number of subfolder levels from the root
    folder to the deepest file. A folder with only files (no subfolders)
    has a depth of 0.

    Args:
        path: Path to the folder.

    Returns:
        Maximum depth of the folder structure.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    root_path = Path(path).resolve()
    max_depth = 0

    for dirpath, dirnames, filenames in os.walk(path):
        if filenames:  # Only count paths that have files
            current_path = Path(dirpath).resolve()
            try:
                relative = current_path.relative_to(root_path)
                depth = len(relative.parts)
                max_depth = max(max_depth, depth)
            except ValueError:
                # Path is not relative to root (shouldn't happen normally)
                pass

    return max_depth


def format_size(size_bytes: int) -> str:
    """
    Format bytes to human readable string.

    Converts a size in bytes to the most appropriate unit
    (B, KB, MB, GB, TB) for readability.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string with appropriate unit (e.g., "1.50 MB").
    """
    if size_bytes < 0:
        return f"{size_bytes:.2f} B"

    # Define units and their thresholds
    units = [
        (1024 * 1024 * 1024 * 1024, "TB"),
        (1024 * 1024 * 1024, "GB"),
        (1024 * 1024, "MB"),
        (1024, "KB"),
        (1, "B"),
    ]

    for threshold, unit in units:
        if size_bytes >= threshold:
            value = size_bytes / threshold
            return f"{value:.2f} {unit}"

    return "0 B"
