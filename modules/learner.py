"""
Learning module for DeepDel application.

This module provides the Learner class for recording user decisions,
generating learned rules, and managing AI response caching.
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.models import ProgramStatus, RiskLevel, ScanResult


class Learner:
    """
    Learner class for recording user decisions and providing learned suggestions.

    This class manages a SQLite database for storing:
    - User decisions about folder deletions
    - Learned rules based on decision patterns
    - AI response cache for avoiding duplicate API calls

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = "data/learner.db"):
        """
        Initialize the Learner with a database path.

        Creates the database and required tables if they don't exist.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """
        Ensure the database file and tables exist.

        Creates the database directory and all required tables if they
        don't already exist.
        """
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT NOT NULL,
                parent_path_pattern TEXT,
                identified_source TEXT,
                source_confidence REAL,
                program_status TEXT,
                file_extensions TEXT,
                has_executables INTEGER,
                folder_depth INTEGER,
                total_files INTEGER,
                total_size INTEGER,
                days_since_access INTEGER,
                created_cluster_date TEXT,
                ai_suggestion TEXT,
                ai_confidence REAL,
                risk_level TEXT,
                user_decision TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create learned_rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_program TEXT,
                folder_name_pattern TEXT,
                parent_path_pattern TEXT,
                extension_profile TEXT,
                suggested_action TEXT NOT NULL,
                confidence REAL,
                delete_count INTEGER DEFAULT 0,
                keep_count INTEGER DEFAULT 0,
                total_decisions INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create ai_cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query_summary TEXT,
                ai_response TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def record_decision(
        self,
        scan_result: ScanResult,
        source_name: Optional[str],
        program_status: ProgramStatus,
        ai_suggestion: Optional[str],
        risk_level: RiskLevel,
        user_decision: str,
        ai_confidence: Optional[float] = None,
    ) -> None:
        """
        Record a user decision about a folder.

        Args:
            scan_result: ScanResult containing folder information.
            source_name: Name of the identified source program.
            program_status: Status of the associated program.
            ai_suggestion: AI's suggestion (can_delete, caution, keep).
            risk_level: Risk level classification.
            user_decision: User's decision ('deleted' or 'kept').
            ai_confidence: Confidence level of the AI suggestion.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate days since access
        days_since_access = None
        if scan_result.last_access:
            delta = datetime.now() - scan_result.last_access
            days_since_access = delta.days

        # Calculate parent path pattern (anonymize)
        parent_path_pattern = self._get_parent_path_pattern(scan_result.path)

        cursor.execute("""
            INSERT INTO decisions (
                folder_name, parent_path_pattern, identified_source, source_confidence,
                program_status, file_extensions, has_executables, folder_depth,
                total_files, total_size, days_since_access,
                ai_suggestion, ai_confidence, risk_level, user_decision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_result.name,
            parent_path_pattern,
            source_name,
            1.0 if source_name else 0.0,
            program_status.value,
            json.dumps(scan_result.file_extensions),
            1 if scan_result.has_executables else 0,
            scan_result.folder_depth,
            scan_result.file_count,
            scan_result.size_bytes,
            days_since_access,
            ai_suggestion,
            ai_confidence,
            risk_level.value,
            user_decision,
        ))

        conn.commit()
        conn.close()

        # Update learned rules
        self._update_learned_rules()

    def _get_parent_path_pattern(self, path: str) -> str:
        """
        Get a pattern for the parent path.

        This anonymizes the path by replacing user-specific parts.

        Args:
            path: Full path to the folder.

        Returns:
            Anonymized parent path pattern.
        """
        if not path:
            return ""

        # Replace user-specific paths with patterns
        path = path.replace("\\", "/")

        # Get parent directory
        parts = path.split("/")
        if len(parts) > 1:
            # Keep the last 2-3 directory levels as pattern
            return "/".join(parts[-3:-1]) if len(parts) >= 3 else "/".join(parts[:-1])
        return ""

    def get_learned_suggestion(
        self,
        folder_name: str,
        path: str = "",
        source_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a learned suggestion based on past decisions.

        Uses priority matching:
        1. source + folder + parent path
        2. source + folder
        3. folder only

        Args:
            folder_name: Name of the folder.
            path: Full path to the folder.
            source_name: Name of the identified source program.

        Returns:
            Dictionary with suggested_action, confidence, and total_decisions,
            or None if no learned rule matches.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        parent_pattern = self._get_parent_path_pattern(path) if path else ""

        # Try priority 1: source + folder + parent
        if source_name and parent_pattern:
            cursor.execute("""
                SELECT suggested_action, confidence, total_decisions
                FROM learned_rules
                WHERE source_program = ? AND folder_name_pattern = ? AND parent_path_pattern = ?
                AND total_decisions >= 2
            """, (source_name, folder_name, parent_pattern))
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    "suggested_action": row[0],
                    "confidence": row[1],
                    "total_decisions": row[2],
                }

        # Try priority 2: source + folder
        if source_name:
            cursor.execute("""
                SELECT suggested_action, confidence, total_decisions
                FROM learned_rules
                WHERE source_program = ? AND folder_name_pattern = ?
                AND total_decisions >= 3
            """, (source_name, folder_name))
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    "suggested_action": row[0],
                    "confidence": row[1],
                    "total_decisions": row[2],
                }

        # Try priority 3: folder only
        cursor.execute("""
            SELECT suggested_action, confidence, total_decisions
            FROM learned_rules
            WHERE folder_name_pattern = ? AND (source_program IS NULL OR source_program = '')
            AND total_decisions >= 3
        """, (folder_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "suggested_action": row[0],
                "confidence": row[1],
                "total_decisions": row[2],
            }

        return None

    def _update_learned_rules(self) -> None:
        """
        Update learned rules based on recorded decisions.

        Analyzes decisions and creates/updates rules when patterns emerge.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all unique combinations
        cursor.execute("""
            SELECT
                identified_source,
                folder_name,
                parent_path_pattern,
                user_decision,
                COUNT(*) as count
            FROM decisions
            GROUP BY identified_source, folder_name, parent_path_pattern, user_decision
        """)

        # Aggregate decisions
        rule_data: Dict[tuple, Dict[str, int]] = {}
        for row in cursor.fetchall():
            source, folder, parent, decision, count = row
            key = (source or "", folder or "", parent or "")
            if key not in rule_data:
                rule_data[key] = {"delete": 0, "keep": 0}
            if decision == "deleted":
                rule_data[key]["delete"] += count
            else:
                rule_data[key]["keep"] += count

        # Update learned_rules table
        for (source, folder, parent), counts in rule_data.items():
            total = counts["delete"] + counts["keep"]
            if total < 3:
                continue

            # Determine suggested action
            if counts["delete"] > counts["keep"]:
                suggested_action = "can_delete"
                confidence = counts["delete"] / total
            elif counts["keep"] > counts["delete"]:
                suggested_action = "keep"
                confidence = counts["keep"] / total
            else:
                suggested_action = "caution"
                confidence = 0.5

            # Check if rule exists
            cursor.execute("""
                SELECT id FROM learned_rules
                WHERE source_program = ? AND folder_name_pattern = ? AND parent_path_pattern = ?
            """, (source or None, folder or None, parent or None))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE learned_rules SET
                        suggested_action = ?,
                        confidence = ?,
                        delete_count = ?,
                        keep_count = ?,
                        total_decisions = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (suggested_action, confidence, counts["delete"], counts["keep"], total, existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO learned_rules (
                        source_program, folder_name_pattern, parent_path_pattern,
                        suggested_action, confidence, delete_count, keep_count, total_decisions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (source or None, folder or None, parent or None, suggested_action, confidence, counts["delete"], counts["keep"], total))

        conn.commit()
        conn.close()

    def get_similar_decisions(self, source_name: str) -> List[Dict[str, Any]]:
        """
        Get similar past decisions for a source program.

        Args:
            source_name: Name of the source program.

        Returns:
            List of dictionaries containing decision information.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT folder_name, user_decision, risk_level, created_at
            FROM decisions
            WHERE identified_source = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (source_name,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "folder_name": row[0],
                "user_decision": row[1],
                "risk_level": row[2],
                "created_at": row[3],
            })

        conn.close()
        return results

    def clear_all_decisions(self) -> None:
        """
        Clear all decision records and learned rules.

        This effectively resets the learning system.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM decisions")
        cursor.execute("DELETE FROM learned_rules")
        cursor.execute("DELETE FROM ai_cache")

        conn.commit()
        conn.close()

    def cache_ai_response(
        self,
        query_hash: str,
        query_summary: str,
        ai_response: str,
    ) -> None:
        """
        Cache an AI response for future use.

        Args:
            query_hash: Hash of the query for lookup.
            query_summary: Human-readable summary of the query.
            ai_response: The AI's response to cache.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO ai_cache (query_hash, query_summary, ai_response)
            VALUES (?, ?, ?)
        """, (query_hash, query_summary, ai_response))

        conn.commit()
        conn.close()

    def get_cached_ai_response(self, query_hash: str) -> Optional[str]:
        """
        Get a cached AI response.

        Args:
            query_hash: Hash of the query.

        Returns:
            Cached AI response or None if not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT ai_response FROM ai_cache WHERE query_hash = ?",
            (query_hash,)
        )
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    @staticmethod
    def generate_query_hash(folder_name: str, extensions: Dict[str, int]) -> str:
        """
        Generate a hash for a query for caching purposes.

        Args:
            folder_name: Name of the folder.
            extensions: Dictionary of file extensions.

        Returns:
            SHA256 hash of the query.
        """
        data = f"{folder_name}:{json.dumps(extensions, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
