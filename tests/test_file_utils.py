"""
Tests for file utility functions in utils/file_utils.py
"""

import os
import tempfile
import time
import pytest
from datetime import datetime
from pathlib import Path


class TestGetFolderSize:
    """Test get_folder_size function."""

    def test_empty_folder(self):
        """Test size of empty folder."""
        from utils.file_utils import get_folder_size

        with tempfile.TemporaryDirectory() as tmpdir:
            assert get_folder_size(tmpdir) == 0

    def test_folder_with_files(self):
        """Test size of folder with files."""
        from utils.file_utils import get_folder_size

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with known sizes
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")

            with open(file1, "wb") as f:
                f.write(b"x" * 100)
            with open(file2, "wb") as f:
                f.write(b"x" * 200)

            assert get_folder_size(tmpdir) == 300

    def test_folder_with_nested_folders(self):
        """Test size of folder with nested subfolders."""
        from utils.file_utils import get_folder_size

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(subdir, "file2.txt")

            with open(file1, "wb") as f:
                f.write(b"x" * 100)
            with open(file2, "wb") as f:
                f.write(b"x" * 200)

            assert get_folder_size(tmpdir) == 300

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import get_folder_size

        with pytest.raises(FileNotFoundError):
            get_folder_size("/non/existent/path/12345")


class TestCountFilesInFolder:
    """Test count_files_in_folder function."""

    def test_empty_folder(self):
        """Test count of empty folder."""
        from utils.file_utils import count_files_in_folder

        with tempfile.TemporaryDirectory() as tmpdir:
            assert count_files_in_folder(tmpdir) == 0

    def test_folder_with_files(self):
        """Test count with multiple files."""
        from utils.file_utils import count_files_in_folder

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                filepath = os.path.join(tmpdir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write("test")

            assert count_files_in_folder(tmpdir) == 5

    def test_folder_with_nested_files(self):
        """Test count with nested subfolders."""
        from utils.file_utils import count_files_in_folder

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in root
            for i in range(2):
                filepath = os.path.join(tmpdir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write("test")

            # Create files in subfolder
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            for i in range(3):
                filepath = os.path.join(subdir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write("test")

            assert count_files_in_folder(tmpdir) == 5

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import count_files_in_folder

        with pytest.raises(FileNotFoundError):
            count_files_in_folder("/non/existent/path/12345")


class TestGetFileExtensions:
    """Test get_file_extensions function."""

    def test_empty_folder(self):
        """Test extensions in empty folder."""
        from utils.file_utils import get_file_extensions

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_file_extensions(tmpdir)
            assert result == {}

    def test_various_extensions(self):
        """Test with various file extensions."""
        from utils.file_utils import get_file_extensions

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use unique filenames since Windows filesystem is case-insensitive
            extensions = [".txt", ".py", ".json", ".TXT", ".Txt"]
            filenames = ["file1.txt", "file2.py", "file3.json", "file4.TXT", "file5.Txt"]
            for filename in filenames:
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, "w") as f:
                    f.write("test")

            result = get_file_extensions(tmpdir)
            # Extensions should be lowercase and merged
            assert result.get(".txt") == 3  # .txt, .TXT, .Txt all become .txt
            assert result.get(".py") == 1
            assert result.get(".json") == 1

    def test_nested_folder_extensions(self):
        """Test extensions in nested folders."""
        from utils.file_utils import get_file_extensions

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in root
            filepath = os.path.join(tmpdir, "file.txt")
            with open(filepath, "w") as f:
                f.write("test")

            # Create files in subfolder
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            filepath = os.path.join(subdir, "file.py")
            with open(filepath, "w") as f:
                f.write("test")

            result = get_file_extensions(tmpdir)
            assert result.get(".txt") == 1
            assert result.get(".py") == 1

    def test_file_without_extension(self):
        """Test files without extension."""
        from utils.file_utils import get_file_extensions

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file without extension
            filepath = os.path.join(tmpdir, "README")
            with open(filepath, "w") as f:
                f.write("test")

            result = get_file_extensions(tmpdir)
            # Files without extension should have empty string as key
            assert result.get("") == 1

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import get_file_extensions

        with pytest.raises(FileNotFoundError):
            get_file_extensions("/non/existent/path/12345")


class TestIsFolderEmpty:
    """Test is_folder_empty function."""

    def test_empty_folder(self):
        """Test with empty folder."""
        from utils.file_utils import is_folder_empty

        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_folder_empty(tmpdir) is True

    def test_folder_with_file(self):
        """Test with folder containing file."""
        from utils.file_utils import is_folder_empty

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "file.txt")
            with open(filepath, "w") as f:
                f.write("test")

            assert is_folder_empty(tmpdir) is False

    def test_folder_with_subfolder_only(self):
        """Test with folder containing only subfolder."""
        from utils.file_utils import is_folder_empty

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            # Folder with subfolder is not empty
            assert is_folder_empty(tmpdir) is False

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import is_folder_empty

        with pytest.raises(FileNotFoundError):
            is_folder_empty("/non/existent/path/12345")


class TestHasExecutables:
    """Test has_executables function."""

    def test_no_executables(self):
        """Test folder without executables."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            for ext in [".txt", ".py", ".json"]:
                filepath = os.path.join(tmpdir, f"file{ext}")
                with open(filepath, "w") as f:
                    f.write("test")

            assert has_executables(tmpdir) is False

    def test_with_exe_file(self):
        """Test folder with .exe file."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "program.exe")
            with open(filepath, "w") as f:
                f.write("test")

            assert has_executables(tmpdir) is True

    def test_with_msi_file(self):
        """Test folder with .msi file."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "installer.msi")
            with open(filepath, "w") as f:
                f.write("test")

            assert has_executables(tmpdir) is True

    def test_with_bat_file(self):
        """Test folder with .bat file."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "script.bat")
            with open(filepath, "w") as f:
                f.write("test")

            assert has_executables(tmpdir) is True

    def test_with_cmd_file(self):
        """Test folder with .cmd file."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "script.cmd")
            with open(filepath, "w") as f:
                f.write("test")

            assert has_executables(tmpdir) is True

    def test_executable_in_subfolder(self):
        """Test with executable in subfolder."""
        from utils.file_utils import has_executables

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            filepath = os.path.join(subdir, "program.exe")
            with open(filepath, "w") as f:
                f.write("test")

            assert has_executables(tmpdir) is True

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import has_executables

        with pytest.raises(FileNotFoundError):
            has_executables("/non/existent/path/12345")


class TestGetLastAccessTime:
    """Test get_last_access_time function."""

    def test_folder_access_time(self):
        """Test getting folder access time."""
        from utils.file_utils import get_last_access_time

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_last_access_time(tmpdir)
            assert result is not None
            assert isinstance(result, datetime)

    def test_file_access_time(self):
        """Test getting file access time."""
        from utils.file_utils import get_last_access_time

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "file.txt")
            with open(filepath, "w") as f:
                f.write("test")

            result = get_last_access_time(filepath)
            assert result is not None
            assert isinstance(result, datetime)

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import get_last_access_time

        result = get_last_access_time("/non/existent/path/12345")
        assert result is None


class TestGetFolderDepth:
    """Test get_folder_depth function."""

    def test_flat_folder(self):
        """Test folder with no subfolders."""
        from utils.file_utils import get_folder_depth

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in root
            for i in range(3):
                filepath = os.path.join(tmpdir, f"file{i}.txt")
                with open(filepath, "w") as f:
                    f.write("test")

            assert get_folder_depth(tmpdir) == 0

    def test_one_level_depth(self):
        """Test folder with one level of subfolders."""
        from utils.file_utils import get_folder_depth

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            filepath = os.path.join(subdir, "file.txt")
            with open(filepath, "w") as f:
                f.write("test")

            assert get_folder_depth(tmpdir) == 1

    def test_multiple_levels(self):
        """Test folder with multiple levels of subfolders."""
        from utils.file_utils import get_folder_depth

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure: tmpdir/a/b/c/file.txt
            path = tmpdir
            for folder in ["a", "b", "c"]:
                path = os.path.join(path, folder)
                os.makedirs(path)

            filepath = os.path.join(path, "file.txt")
            with open(filepath, "w") as f:
                f.write("test")

            assert get_folder_depth(tmpdir) == 3

    def test_non_existent_path(self):
        """Test with non-existent path."""
        from utils.file_utils import get_folder_depth

        with pytest.raises(FileNotFoundError):
            get_folder_depth("/non/existent/path/12345")


class TestFormatSize:
    """Test format_size function."""

    def test_bytes(self):
        """Test formatting bytes."""
        from utils.file_utils import format_size

        assert format_size(0) == "0 B"
        assert format_size(100) == "100.00 B"
        assert format_size(1023) == "1023.00 B"

    def test_kilobytes(self):
        """Test formatting kilobytes."""
        from utils.file_utils import format_size

        assert format_size(1024) == "1.00 KB"
        assert format_size(1024 * 5) == "5.00 KB"
        assert format_size(1024 * 1023) == "1023.00 KB"

    def test_megabytes(self):
        """Test formatting megabytes."""
        from utils.file_utils import format_size

        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 100) == "100.00 MB"
        assert format_size(1024 * 1024 * 1023) == "1023.00 MB"

    def test_gigabytes(self):
        """Test formatting gigabytes."""
        from utils.file_utils import format_size

        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size(1024 * 1024 * 1024 * 5) == "5.00 GB"
        assert format_size(1024 * 1024 * 1024 * 100) == "100.00 GB"

    def test_terabytes(self):
        """Test formatting terabytes."""
        from utils.file_utils import format_size

        assert format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert format_size(1024 * 1024 * 1024 * 1024 * 2) == "2.00 TB"

    def test_negative_size(self):
        """Test formatting negative size."""
        from utils.file_utils import format_size

        # Negative sizes should be handled gracefully
        result = format_size(-100)
        # Should return something reasonable
        assert isinstance(result, str)
