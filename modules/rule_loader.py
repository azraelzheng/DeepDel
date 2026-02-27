"""
Rule Loader Module for DeepDel Application.

This module provides the RuleLoader class which handles loading and matching
deletion rules from JSON configuration files.
"""

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


class RuleLoader:
    """
    Rule loader class for managing deletion rules.

    This class handles loading rule files from JSON, caching loaded rules,
    and matching paths against patterns.

    Attributes:
        rules_dir: Directory containing rule JSON files
        _cache: Internal cache for loaded rules
    """

    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize the RuleLoader.

        Args:
            rules_dir: Path to the directory containing rule files.
                      Defaults to "rules".
        """
        self.rules_dir = rules_dir
        self._cache: Dict[str, Dict] = {}

    def _load_json_file(self, filename: str) -> Dict:
        """
        Load a JSON file from the rules directory.

        Args:
            filename: Name of the JSON file to load.

        Returns:
            Parsed JSON content as a dictionary, or empty dict on error.
        """
        cache_key = filename.replace(".json", "")
        if cache_key in self._cache:
            return self._cache[cache_key]

        filepath = Path(self.rules_dir) / filename

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[cache_key] = data
                return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}

    def load_safe_rules(self) -> Dict:
        """
        Load safe deletion rules.

        Safe rules define patterns for folders that can be safely deleted.

        Returns:
            Dictionary containing safe deletion patterns and rules.
        """
        return self._load_json_file("safe_rules.json")

    def load_suggest_rules(self) -> Dict:
        """
        Load suggested deletion rules.

        Suggest rules define patterns for folders that may be good candidates
        for deletion but require user review.

        Returns:
            Dictionary containing suggested deletion patterns and rules.
        """
        return self._load_json_file("suggest_rules.json")

    def load_caution_rules(self) -> Dict:
        """
        Load caution deletion rules.

        Caution rules define patterns for folders that should be handled
        with care or should not be deleted.

        Returns:
            Dictionary containing caution patterns and rules.
        """
        return self._load_json_file("caution_rules.json")

    def load_software_db(self) -> Dict:
        """
        Load the software database.

        The software database contains known software patterns for identification.

        Returns:
            Dictionary containing software information and folder patterns.
        """
        return self._load_json_file("software_db.json")

    def match_pattern(self, path: str, pattern: str) -> bool:
        """
        Match a path against a pattern with wildcard support.

        Supports the following wildcard patterns:
        - **/name - matches name at any depth
        - path/** - matches everything under path
        - **/path/** - matches any path containing the specified path segment
        - * - matches any sequence of characters (except path separators)
        - ** - matches any sequence of characters including path separators
        - **\\name - Windows-style pattern matching name at any depth

        Args:
            path: The file/folder path to match.
            pattern: The pattern to match against.

        Returns:
            True if the path matches the pattern, False otherwise.
        """
        if not path or not pattern:
            return False

        # Normalize path separators to forward slashes
        normalized_path = path.replace("\\", "/")
        normalized_pattern = pattern.replace("\\", "/")

        # Case-insensitive matching on Windows
        if os.name == "nt" or "\\" in path:
            normalized_path = normalized_path.lower()
            normalized_pattern = normalized_pattern.lower()

        # Handle **/path/** pattern - matches any path containing the specified segment
        if normalized_pattern.startswith("**/") and normalized_pattern.endswith("/**"):
            middle = normalized_pattern[3:-3]  # Remove **/ and /**
            if middle in normalized_path:
                return True
            # Also check if path ends with or starts with the middle part
            if normalized_path.endswith("/" + middle) or normalized_path.startswith(middle + "/"):
                return True
            return False

        # Handle **/name pattern - matches name at any depth
        if normalized_pattern.startswith("**/"):
            name = normalized_pattern[3:]  # Remove **/
            # If name contains /, it's a path that should be found anywhere in the path
            if "/" in name:
                # Check if the path contains this sub-path
                if name in normalized_path:
                    return True
                # Also check if path ends with this sub-path
                if normalized_path.endswith("/" + name) or normalized_path == name:
                    return True
                return False
            else:
                # Simple case: match a single name at any depth
                path_parts = normalized_path.split("/")
                for part in path_parts:
                    if part == name:
                        return True
                return False

        # Handle path/** pattern - matches everything under path
        if normalized_pattern.endswith("/**"):
            prefix = normalized_pattern[:-3]  # Remove /**
            # Check if path starts with the prefix
            if normalized_path == prefix:
                return True
            if normalized_path.startswith(prefix + "/"):
                return True
            return False

        # Handle patterns with ** in the middle
        if "**" in normalized_pattern:
            try:
                # Convert ** to a regex pattern
                # ** matches zero or more path components
                regex_pattern = self._pattern_to_regex(normalized_pattern)
                return bool(re.match(regex_pattern, normalized_path))
            except re.error:
                return False

        # Handle simple glob with * (single level wildcard)
        if "*" in normalized_pattern:
            # Use fnmatch for simple glob patterns
            try:
                return fnmatch.fnmatch(normalized_path, normalized_pattern)
            except Exception:
                return False

        # Exact match
        return normalized_path == normalized_pattern

    def _pattern_to_regex(self, pattern: str) -> str:
        """
        Convert a glob pattern with ** to a regex pattern.

        Args:
            pattern: The glob pattern to convert.

        Returns:
            A regex pattern string.
        """
        # Escape special regex characters except * and **
        result = ""
        i = 0
        while i < len(pattern):
            if pattern[i:i+2] == "**":
                # ** matches zero or more path components
                result += ".*"
                i += 2
            elif pattern[i] == "*":
                # * matches any characters except /
                result += "[^/]*"
                i += 1
            elif pattern[i] in ".^$+?{}[]|()\\":
                # Escape regex special characters
                result += "\\" + pattern[i]
                i += 1
            else:
                result += pattern[i]
                i += 1

        return "^" + result + "$"

    def get_all_safe_patterns(self) -> List[Dict]:
        """
        Get all safe deletion patterns.

        Collects patterns from various categories in the safe rules file:
        - temp_patterns
        - cache_patterns
        - dev_caches
        - log_patterns
        - patterns (simple format)

        Returns:
            List of pattern dictionaries from safe rules.
            Each dictionary contains 'pattern' and optionally 'description'.
        """
        rules = self.load_safe_rules()
        all_patterns: List[Dict] = []

        # Handle simple format with 'patterns' key
        if "patterns" in rules:
            all_patterns.extend(rules["patterns"])

        # Handle structured format with multiple categories
        categories = [
            "temp_patterns",
            "cache_patterns",
            "dev_caches",
            "log_patterns",
        ]

        for category in categories:
            if category in rules:
                patterns = rules[category]
                if isinstance(patterns, list):
                    all_patterns.extend(patterns)

        return all_patterns

    def find_matching_software(self, folder_name: str) -> Optional[Dict]:
        """
        Find software that matches the given folder name.

        Searches the software database for entries whose folder patterns
        match the given folder name.

        The software database can have two formats:
        - 'software' key with 'folder_patterns' list
        - 'applications' key with 'folder_names' list

        Args:
            folder_name: The name of the folder to identify.

        Returns:
            Dictionary containing matching software information, or None if no match.
            The dictionary includes 'name', 'type', and folder patterns.
        """
        if not folder_name:
            return None

        db = self.load_software_db()

        # Normalize folder name for case-insensitive comparison
        normalized_name = folder_name.lower()

        # Handle 'software' format (folder_patterns)
        software_list = db.get("software", [])
        for software in software_list:
            patterns = software.get("folder_patterns", [])
            for pattern in patterns:
                normalized_pattern = pattern.lower()

                # Check for exact match
                if normalized_name == normalized_pattern:
                    return software

                # Check for wildcard match
                if "*" in pattern:
                    try:
                        if fnmatch.fnmatch(normalized_name, normalized_pattern):
                            return software
                    except Exception:
                        continue

        # Handle 'applications' format (folder_names)
        applications = db.get("applications", [])
        for app in applications:
            folder_names = app.get("folder_names", [])
            for folder in folder_names:
                # Normalize for comparison
                normalized_folder = folder.lower().replace("\\", "/")

                # Check exact match
                if normalized_name == normalized_folder:
                    return app

                # Check if folder name is part of the pattern
                # e.g., "Code" matches "Code", "Google\\Chrome" matches "Chrome"
                folder_parts = normalized_folder.split("/")
                if normalized_name in folder_parts:
                    return app

                # Check wildcard match
                if "*" in folder:
                    try:
                        if fnmatch.fnmatch(normalized_name, normalized_folder):
                            return app
                    except Exception:
                        continue

        return None

    def is_caution_pattern(self, folder_name: str, path: str) -> bool:
        """
        Check if a folder matches any caution pattern.

        Checks multiple categories of caution patterns:
        - user_data_indicators
        - config_indicators
        - protected_folders
        - patterns (simple format)

        Args:
            folder_name: The name of the folder.
            path: The full path to the folder.

        Returns:
            True if the folder matches a caution pattern, False otherwise.
        """
        rules = self.load_caution_rules()

        # Handle simple format with 'patterns' key
        patterns = rules.get("patterns", [])
        for rule in patterns:
            pattern = rule.get("pattern", "")
            if self.match_pattern(folder_name, pattern):
                return True
            if self.match_pattern(path, pattern):
                return True

        # Handle user_data_indicators
        user_data = rules.get("user_data_indicators", [])
        if isinstance(user_data, list):
            for rule in user_data:
                pattern = rule.get("pattern", "")
                if self.match_pattern(folder_name, pattern):
                    return True
                if self.match_pattern(path, pattern):
                    return True

        # Handle config_indicators
        config_indicators = rules.get("config_indicators", [])
        if isinstance(config_indicators, list):
            for rule in config_indicators:
                pattern = rule.get("pattern", "")
                if self.match_pattern(folder_name, pattern):
                    return True
                if self.match_pattern(path, pattern):
                    return True

        # Handle protected_folders (list of folder names)
        protected = rules.get("protected_folders", [])
        if isinstance(protected, list):
            normalized_name = folder_name.lower()
            for folder in protected:
                if normalized_name == folder.lower():
                    return True

        return False

    def clear_cache(self) -> None:
        """
        Clear the rule cache.

        This forces rules to be reloaded from files on next access.
        """
        self._cache.clear()

    def reload_all_rules(self) -> None:
        """
        Reload all rules from files.

        Clears the cache and preloads all rule files.
        """
        self.clear_cache()
        self.load_safe_rules()
        self.load_suggest_rules()
        self.load_caution_rules()
        self.load_software_db()
