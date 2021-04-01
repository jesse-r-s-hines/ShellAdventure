import pytest
from shell_adventure_docker.random_helper import RandomHelper

class TestRandomHelper:
    def test_name(self):
        random = RandomHelper(
            name_dictionary = "apple\n\n\n\nbanana\norange\n"
        )

        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}

        with pytest.raises(Exception, match="Out of unique names"):
            random.name()