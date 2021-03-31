import pytest
from shell_adventure_docker.random_helper import RandomHelper
from pathlib import Path

class TestRandomHelper:
    def test_name(self, tmp_path):
        (tmp_path / "dict.txt").write_text("apple\n\n\n\nbanana\norange\n")
        random = RandomHelper(tmp_path / "dict.txt")

        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}

        with pytest.raises(Exception, match="Out of unique names"):
            random.name()