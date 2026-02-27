"""
Process utility functions for DeepDel application.

This module provides utility functions for working with system processes,
including listing running processes and finding processes by folder name.
"""

from typing import Dict, List, Optional

import psutil


def get_running_processes() -> List[Dict]:
    """
    Get all running processes.

    Retrieves information about all currently running processes on the system.

    Returns:
        List of dictionaries containing process information:
        - pid: Process ID (int)
        - name: Process name (str)
        - exe: Executable path (str, may be empty if not accessible)
        - cmdline: Command line arguments (str, may be empty if not accessible)
    """
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            proc_info = proc.info

            # Convert cmdline from list to string
            cmdline = ""
            if proc_info.get('cmdline'):
                cmdline = " ".join(proc_info['cmdline'])

            processes.append({
                'pid': proc_info.get('pid', 0),
                'name': proc_info.get('name', ''),
                'exe': proc_info.get('exe') or '',
                'cmdline': cmdline
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that have terminated or cannot be accessed
            pass

    return processes


def is_process_running(process_name: str) -> bool:
    """
    Check if a process with the given name is running.

    Performs a case-insensitive comparison of process names.

    Args:
        process_name: Name of the process to check (e.g., "explorer.exe").

    Returns:
        True if a process with the given name is running, False otherwise.
    """
    if not process_name:
        return False

    process_name_lower = process_name.lower()

    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info.get('name', '')
            if name.lower() == process_name_lower:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that have terminated or cannot be accessed
            pass

    return False


def find_process_by_folder(folder_name: str) -> Optional[Dict]:
    """
    Find a process related to the given folder name.

    Searches for a process whose executable path or name contains the
    folder name. Returns the first match found.

    Matching logic:
    - Check if folder_name appears in the executable path (case-insensitive)
    - Check if folder_name appears in the process name (case-insensitive)

    Args:
        folder_name: Name of the folder to search for.

    Returns:
        Dictionary with process information if found, None otherwise:
        - pid: Process ID (int)
        - name: Process name (str)
        - exe: Executable path (str)
        - cmdline: Command line arguments (str)
    """
    if not folder_name:
        return None

    folder_name_lower = folder_name.lower()

    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            proc_info = proc.info

            exe_path = proc_info.get('exe') or ''
            name = proc_info.get('name', '')

            # Check if folder_name appears in exe path
            if exe_path and folder_name_lower in exe_path.lower():
                cmdline = ""
                if proc_info.get('cmdline'):
                    cmdline = " ".join(proc_info['cmdline'])

                return {
                    'pid': proc_info.get('pid', 0),
                    'name': name,
                    'exe': exe_path,
                    'cmdline': cmdline
                }

            # Check if folder_name appears in process name
            if name and folder_name_lower in name.lower():
                cmdline = ""
                if proc_info.get('cmdline'):
                    cmdline = " ".join(proc_info['cmdline'])

                return {
                    'pid': proc_info.get('pid', 0),
                    'name': name,
                    'exe': exe_path,
                    'cmdline': cmdline
                }

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that have terminated or cannot be accessed
            pass

    return None
