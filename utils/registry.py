"""
Windows Registry utility functions for DeepDel application.

This module provides utility functions for working with the Windows Registry,
including checking installed programs, MRU entries, and shortcut targets.

Note: These functions are Windows-specific and will return None or empty lists
on non-Windows platforms or when errors occur.
"""

import os
import sys
from typing import Dict, List, Optional

# Import winreg only on Windows
if sys.platform == "win32":
    import winreg
else:
    winreg = None


# Registry paths for installed programs
UNINSTALL_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

# MRU (Most Recently Used) registry locations
MRU_PATHS = [
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs", "RecentDocs"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU", "RunMRU"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths", "TypedPaths"),
]

# Start Menu locations for shortcut searching
START_MENU_PATHS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
]


def check_program_installed(registry_key: str) -> Optional[bool]:
    """
    Check if a program has an uninstall entry in the registry.

    Searches through the standard uninstall registry locations to find
    a matching program entry.

    Args:
        registry_key: The registry key name to search for (case-insensitive).
                     This is typically the subkey name under the Uninstall path.

    Returns:
        True if the program is found in the uninstall registry,
        False if not found,
        None if an error occurs or on non-Windows platforms.
    """
    if winreg is None:
        return None

    if not registry_key or not isinstance(registry_key, str):
        return None

    # Clean the key name
    registry_key = registry_key.strip()
    if not registry_key:
        return None

    try:
        # Search through all uninstall paths
        for hive, path in UNINSTALL_PATHS:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                    # Enumerate subkeys to find matching program
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            if subkey_name.lower() == registry_key.lower():
                                return True
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue

        return False

    except Exception:
        return None


def get_installed_programs() -> List[Dict]:
    """
    Get a list of installed programs from the registry.

    Scans all standard uninstall registry locations and collects
    information about installed programs.

    Returns:
        List of dictionaries containing program information:
        - name: Display name of the program
        - key: Registry key name
        - install_location: Installation location (if available)
        - uninstall_string: Uninstall command (if available)
        - publisher: Publisher name (if available)
        - version: Version string (if available)

        Returns empty list on non-Windows platforms or errors.
    """
    if winreg is None:
        return []

    programs = []
    seen_names = set()

    try:
        for hive, path in UNINSTALL_PATHS:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                    # Enumerate all subkeys
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            program_info = _read_program_info(key, subkey_name)

                            if program_info and program_info.get('name'):
                                # Avoid duplicates by name (case-insensitive)
                                name_lower = program_info['name'].lower()
                                if name_lower not in seen_names:
                                    seen_names.add(name_lower)
                                    programs.append(program_info)
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue

    except Exception:
        pass

    return programs


def _read_program_info(parent_key, subkey_name: str) -> Optional[Dict]:
    """
    Read program information from a registry subkey.

    Args:
        parent_key: The parent registry key.
        subkey_name: Name of the subkey to read.

    Returns:
        Dictionary with program information or None if not a valid program.
    """
    if winreg is None:
        return None

    try:
        with winreg.OpenKey(parent_key, subkey_name, 0, winreg.KEY_READ) as subkey:
            program = {
                'key': subkey_name,
                'name': _read_registry_value(subkey, 'DisplayName'),
                'install_location': _read_registry_value(subkey, 'InstallLocation'),
                'uninstall_string': _read_registry_value(subkey, 'UninstallString'),
                'publisher': _read_registry_value(subkey, 'Publisher'),
                'version': _read_registry_value(subkey, 'DisplayVersion'),
            }

            # Only return if we have at least a display name
            if program['name']:
                return program
            return None

    except (PermissionError, OSError):
        return None


def _read_registry_value(key, value_name: str) -> Optional[str]:
    """
    Read a string value from a registry key.

    Args:
        key: The registry key to read from.
        value_name: Name of the value to read.

    Returns:
        String value or None if not found or not a string type.
    """
    if winreg is None:
        return None

    try:
        value, value_type = winreg.QueryValueEx(key, value_name)
        if value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            return str(value).strip() if value else None
        return None
    except (OSError, FileNotFoundError):
        return None


def get_mru_entries() -> List[Dict]:
    """
    Get Most Recently Used (MRU) entries from the registry.

    Reads MRU entries from various Windows registry locations including:
    - Recent documents
    - Run dialog history
    - Typed paths in Explorer

    Returns:
        List of dictionaries containing MRU information:
        - source: Name of the MRU source (e.g., "RecentDocs", "RunMRU")
        - entries: List of MRU entry strings

        Returns empty list on non-Windows platforms or errors.
    """
    if winreg is None:
        return []

    mru_data = []

    try:
        for hive, path, source_name in MRU_PATHS:
            try:
                entries = _read_mru_entries(hive, path)
                if entries:
                    mru_data.append({
                        'source': source_name,
                        'entries': entries
                    })
            except (PermissionError, OSError):
                continue

    except Exception:
        pass

    return mru_data


def _read_mru_entries(hive, path: str) -> List[str]:
    """
    Read MRU entries from a specific registry path.

    Args:
        hive: Registry hive (e.g., HKEY_CURRENT_USER).
        path: Registry path to read from.

    Returns:
        List of MRU entry strings.
    """
    if winreg is None:
        return []

    entries = []

    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            # Enumerate all values
            num_values = winreg.QueryInfoKey(key)[1]
            for i in range(num_values):
                try:
                    value_name, value_data, value_type = winreg.EnumValue(key, i)
                    # Skip the MRUList order indicator
                    if value_name.lower() != 'mrulist' and value_name.lower() != 'mrulistex':
                        if value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                            entry = str(value_data).strip()
                            if entry:
                                entries.append(entry)
                except OSError:
                    continue

    except (PermissionError, OSError):
        pass

    return entries


def find_shortcut_target(folder_name: str) -> Optional[str]:
    """
    Find a shortcut target in the Start Menu.

    Searches through Start Menu Program folders to find a shortcut
    that matches the given folder name.

    Args:
        folder_name: Name of the folder/program to search for.

    Returns:
        Path to the shortcut target if found, None otherwise.
    """
    if sys.platform != "win32":
        return None

    if not folder_name or not isinstance(folder_name, str):
        return None

    folder_name = folder_name.strip()
    if not folder_name:
        return None

    try:
        for start_menu_path in START_MENU_PATHS:
            if not os.path.exists(start_menu_path):
                continue

            result = _search_shortcut_in_path(start_menu_path, folder_name)
            if result:
                return result

    except Exception:
        pass

    return None


def _search_shortcut_in_path(base_path: str, folder_name: str) -> Optional[str]:
    """
    Search for a shortcut matching the folder name in a specific path.

    Args:
        base_path: Base path to search in.
        folder_name: Name to search for.

    Returns:
        Path to the shortcut if found, None otherwise.
    """
    try:
        # First, try direct folder match
        target_folder = os.path.join(base_path, folder_name)
        if os.path.isdir(target_folder):
            shortcut = _find_shortcut_in_folder(target_folder)
            if shortcut:
                return shortcut

        # Then search for folders containing the name
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                if folder_name.lower() in item.lower():
                    shortcut = _find_shortcut_in_folder(item_path)
                    if shortcut:
                        return shortcut

    except (PermissionError, OSError):
        pass

    return None


def _find_shortcut_in_folder(folder_path: str) -> Optional[str]:
    """
    Find the main shortcut in a folder.

    Args:
        folder_path: Path to the folder to search.

    Returns:
        Path to the first .lnk file found, or None.
    """
    try:
        for item in os.listdir(folder_path):
            if item.lower().endswith('.lnk'):
                return os.path.join(folder_path, item)
    except (PermissionError, OSError):
        pass

    return None
