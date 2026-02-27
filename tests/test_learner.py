"""
Tests for learning module in modules/learner.py
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta

from modules.learner import Learner
from modules.models import ScanResult, ProgramStatus, RiskLevel


class TestLearnerInit:
    """Test Learner initialization."""

    def test_init_with_default_path(self):
        """Test Learner initialization with default path."""
        learner = Learner()
        assert learner.db_path == "data/learner.db"

    def test_init_with_custom_path(self):
        """Test Learner initialization with custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            learner = Learner(db_path)
            assert learner.db_path == db_path

    def test_database_tables_created(self):
        """Test that database tables are created on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            learner = Learner(db_path)

            # Check that tables exist
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check decisions table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decisions'"
            )
            assert cursor.fetchone() is not None

            # Check learned_rules table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='learned_rules'"
            )
            assert cursor.fetchone() is not None

            # Check ai_cache table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_cache'"
            )
            assert cursor.fetchone() is not None

            conn.close()


class TestRecordDecision:
    """Test recording user decisions."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    @pytest.fixture
    def sample_scan_result(self):
        """Create a sample ScanResult for testing."""
        return ScanResult(
            path="C:/Users/Test/AppData/Local/Steam/htmlcache",
            name="htmlcache",
            size_bytes=1024 * 1024 * 50,  # 50 MB
            file_count=100,
            last_access=datetime.now() - timedelta(days=30),
            file_extensions={".html": 50, ".css": 30, ".js": 20},
            has_executables=False,
            folder_depth=4,
        )

    def test_record_decision_deleted(self, learner, sample_scan_result):
        """Test recording a delete decision."""
        learner.record_decision(
            scan_result=sample_scan_result,
            source_name="Steam",
            program_status=ProgramStatus.INSTALLED,
            ai_suggestion="can_delete",
            risk_level=RiskLevel.SAFE,
            user_decision="deleted",
        )

        # Verify decision was recorded
        import sqlite3

        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM decisions")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_record_decision_kept(self, learner, sample_scan_result):
        """Test recording a keep decision."""
        learner.record_decision(
            scan_result=sample_scan_result,
            source_name="Steam",
            program_status=ProgramStatus.INSTALLED,
            ai_suggestion="caution",
            risk_level=RiskLevel.CAUTION,
            user_decision="kept",
        )

        # Verify decision was recorded
        import sqlite3

        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_decision FROM decisions WHERE folder_name = ?", ("htmlcache",))
        decision = cursor.fetchone()[0]
        conn.close()

        assert decision == "kept"

    def test_record_decision_stores_all_fields(self, learner, sample_scan_result):
        """Test that all fields are stored correctly."""
        learner.record_decision(
            scan_result=sample_scan_result,
            source_name="Steam",
            program_status=ProgramStatus.INSTALLED,
            ai_suggestion="can_delete",
            ai_confidence=0.85,
            risk_level=RiskLevel.SAFE,
            user_decision="deleted",
        )

        import sqlite3
        import json

        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT folder_name, identified_source, source_confidence, program_status,
                   file_extensions, has_executables, folder_depth, total_files, total_size,
                   ai_suggestion, ai_confidence, risk_level, user_decision
            FROM decisions
            """
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "htmlcache"  # folder_name
        assert row[1] == "Steam"  # identified_source
        assert row[2] == 1.0  # source_confidence (default for now)
        assert row[3] == "installed"  # program_status
        assert json.loads(row[4]) == {".html": 50, ".css": 30, ".js": 20}  # file_extensions
        assert row[5] == 0  # has_executables (False)
        assert row[6] == 4  # folder_depth
        assert row[7] == 100  # total_files
        assert row[8] == 1024 * 1024 * 50  # total_size
        assert row[9] == "can_delete"  # ai_suggestion
        assert row[10] == 0.85  # ai_confidence
        assert row[11] == "safe"  # risk_level
        assert row[12] == "deleted"  # user_decision


class TestLearnedRules:
    """Test learned rules creation and retrieval."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    @pytest.fixture
    def sample_scan_result(self):
        """Create a sample ScanResult for testing."""
        return ScanResult(
            path="C:/Users/Test/AppData/Local/Discord/Cache",
            name="Cache",
            size_bytes=1024 * 1024 * 100,
            file_count=200,
            last_access=datetime.now() - timedelta(days=15),
            file_extensions={".cache": 100, ".dat": 50, ".tmp": 50},
            has_executables=False,
            folder_depth=4,
        )

    def test_no_learned_suggestion_initially(self, learner, sample_scan_result):
        """Test that there's no learned suggestion initially."""
        suggestion = learner.get_learned_suggestion(
            folder_name="Cache",
            path="C:/Users/Test/AppData/Local/Discord/Cache",
            source_name="Discord",
        )
        assert suggestion is None

    def test_learned_rule_after_three_same_decisions(self, learner, sample_scan_result):
        """Test that a learned rule is created after 3 same decisions."""
        # Record 3 delete decisions for the same folder+source
        for i in range(3):
            learner.record_decision(
                scan_result=sample_scan_result,
                source_name="Discord",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        # Now check for learned suggestion
        suggestion = learner.get_learned_suggestion(
            folder_name="Cache",
            path="C:/Users/Test/AppData/Local/Discord/Cache",
            source_name="Discord",
        )

        assert suggestion is not None
        assert suggestion["suggested_action"] == "can_delete"
        assert suggestion["total_decisions"] >= 3

    def test_learned_rule_priority_source_folder_parent(self, learner):
        """Test priority: source+folder+parent > source+folder > folder only."""
        # Create scan results with different paths but same folder name
        scan1 = ScanResult(
            path="C:/Users/Test/AppData/Local/App1/Cache",
            name="Cache",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
            folder_depth=4,
        )
        scan2 = ScanResult(
            path="C:/Users/Test/AppData/Local/App2/Cache",
            name="Cache",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
            folder_depth=4,
        )

        # Record decisions for App1/Cache - delete
        for _ in range(3):
            learner.record_decision(
                scan_result=scan1,
                source_name="App1",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        # Record decisions for App2/Cache - keep
        for _ in range(3):
            learner.record_decision(
                scan_result=scan2,
                source_name="App2",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="caution",
                risk_level=RiskLevel.CAUTION,
                user_decision="kept",
            )

        # Check that each path gets the correct suggestion
        suggestion1 = learner.get_learned_suggestion(
            folder_name="Cache",
            path="C:/Users/Test/AppData/Local/App1/Cache",
            source_name="App1",
        )
        suggestion2 = learner.get_learned_suggestion(
            folder_name="Cache",
            path="C:/Users/Test/AppData/Local/App2/Cache",
            source_name="App2",
        )

        assert suggestion1["suggested_action"] == "can_delete"
        assert suggestion2["suggested_action"] == "keep"


class TestGetSimilarDecisions:
    """Test getting similar past decisions."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    def test_get_similar_decisions_empty(self, learner):
        """Test getting similar decisions when none exist."""
        decisions = learner.get_similar_decisions(source_name="NonExistent")
        assert decisions == []

    def test_get_similar_decisions_returns_matching(self, learner):
        """Test that similar decisions are returned for matching source."""
        scan_result = ScanResult(
            path="C:/Test/Path",
            name="TestFolder",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record multiple decisions for the same source
        for i in range(3):
            learner.record_decision(
                scan_result=scan_result,
                source_name="TestApp",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        decisions = learner.get_similar_decisions(source_name="TestApp")
        assert len(decisions) == 3

    def test_get_similar_decisions_excludes_other_sources(self, learner):
        """Test that decisions for other sources are not included."""
        scan_result = ScanResult(
            path="C:/Test/Path",
            name="TestFolder",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record decisions for App1
        learner.record_decision(
            scan_result=scan_result,
            source_name="App1",
            program_status=ProgramStatus.INSTALLED,
            ai_suggestion="can_delete",
            risk_level=RiskLevel.SAFE,
            user_decision="deleted",
        )

        # Record decisions for App2
        learner.record_decision(
            scan_result=scan_result,
            source_name="App2",
            program_status=ProgramStatus.INSTALLED,
            ai_suggestion="keep",
            risk_level=RiskLevel.CAUTION,
            user_decision="kept",
        )

        decisions_app1 = learner.get_similar_decisions(source_name="App1")
        decisions_app2 = learner.get_similar_decisions(source_name="App2")

        assert len(decisions_app1) == 1
        assert len(decisions_app2) == 1
        assert decisions_app1[0]["user_decision"] == "deleted"
        assert decisions_app2[0]["user_decision"] == "kept"


class TestClearAllDecisions:
    """Test clearing all decision records."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    def test_clear_all_decisions(self, learner):
        """Test that clear_all_decisions removes all records."""
        scan_result = ScanResult(
            path="C:/Test/Path",
            name="TestFolder",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record some decisions
        for i in range(5):
            learner.record_decision(
                scan_result=scan_result,
                source_name="TestApp",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        # Clear all decisions
        learner.clear_all_decisions()

        # Verify decisions are cleared
        import sqlite3

        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM decisions")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    def test_clear_also_clears_learned_rules(self, learner):
        """Test that clear_all_decisions also removes learned rules."""
        scan_result = ScanResult(
            path="C:/Test/Path",
            name="TestFolder",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record enough decisions to create a learned rule
        for i in range(3):
            learner.record_decision(
                scan_result=scan_result,
                source_name="TestApp",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        # Clear all decisions
        learner.clear_all_decisions()

        # Verify learned rules are cleared
        import sqlite3

        conn = sqlite3.connect(learner.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM learned_rules")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0


class TestAICache:
    """Test AI response caching functionality."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    def test_cache_ai_response(self, learner):
        """Test caching an AI response."""
        query_hash = "abc123"
        query_summary = "Steam htmlcache folder analysis"
        ai_response = json.dumps({"suggestion": "can_delete", "confidence": 0.95})

        learner.cache_ai_response(query_hash, query_summary, ai_response)

        cached = learner.get_cached_ai_response(query_hash)
        assert cached is not None
        assert cached == ai_response

    def test_get_nonexistent_cache(self, learner):
        """Test getting a non-existent cached response."""
        cached = learner.get_cached_ai_response("nonexistent")
        assert cached is None


class TestLearnedSuggestionEdgeCases:
    """Test edge cases for learned suggestions."""

    @pytest.fixture
    def learner(self):
        """Create a Learner instance with temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_learner.db")
            yield Learner(db_path)

    def test_learned_suggestion_without_source(self, learner):
        """Test getting learned suggestion without source name."""
        scan_result = ScanResult(
            path="C:/Temp/Junk",
            name="Junk",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record decisions without source name
        for _ in range(3):
            learner.record_decision(
                scan_result=scan_result,
                source_name=None,
                program_status=ProgramStatus.UNKNOWN,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )

        # Should still get a learned suggestion based on folder name only
        suggestion = learner.get_learned_suggestion(
            folder_name="Junk", path="C:/Temp/Junk", source_name=None
        )

        assert suggestion is not None
        assert suggestion["suggested_action"] == "can_delete"

    def test_mixed_decisions_no_clear_pattern(self, learner):
        """Test that mixed decisions (delete and keep) result in caution."""
        scan_result = ScanResult(
            path="C:/Test/MixedFolder",
            name="MixedFolder",
            size_bytes=1024 * 1024,
            file_count=10,
            last_access=datetime.now(),
        )

        # Record 2 delete and 2 keep decisions
        for _ in range(2):
            learner.record_decision(
                scan_result=scan_result,
                source_name="MixedApp",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="can_delete",
                risk_level=RiskLevel.SAFE,
                user_decision="deleted",
            )
            learner.record_decision(
                scan_result=scan_result,
                source_name="MixedApp",
                program_status=ProgramStatus.INSTALLED,
                ai_suggestion="keep",
                risk_level=RiskLevel.CAUTION,
                user_decision="kept",
            )

        # After 4 decisions, should have a learned rule
        suggestion = learner.get_learned_suggestion(
            folder_name="MixedFolder",
            path="C:/Test/MixedFolder",
            source_name="MixedApp",
        )

        # Mixed decisions should result in 'caution' action
        assert suggestion is not None
        assert suggestion["suggested_action"] == "caution"


import json  # Import at module level for use in TestAICache
