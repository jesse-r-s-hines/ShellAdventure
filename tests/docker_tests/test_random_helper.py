import pytest
from shell_adventure_docker.random_helper import RandomHelper

CONTENT_1 = """
Sentence a.  Sentence b.  Sentence c.

Sentence d. Sentence e.

Sentence f.
"""

CONTENT_2 = """

    Space indented paragraph.   



\tTab indented paragraph.   


"""

CONTENT_3 = "One line."

class TestRandomHelper:
    def test_name(self):
        random = RandomHelper(
            name_dictionary = "apple\n\n\n\nbanana\norange\n",
            content_sources = "",
        )

        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}

        with pytest.raises(Exception, match="Out of unique names"):
            random.name()

    def test_paragraphs(self):
        random = RandomHelper("", [CONTENT_1])
        paras = ["Sentence a.  Sentence b.  Sentence c.\n", "Sentence d. Sentence e.\n", "Sentence f.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras

        for _ in range(10): # random range
            assert len(random.paragraphs((1, 3)).split("\n\n")) in [1, 2, 3]

        for _ in range(10):
            all = random.paragraphs(3)
            assert all == "Sentence a.  Sentence b.  Sentence c.\n\nSentence d. Sentence e.\n\nSentence f.\n"

        # Will make lorem ipsum text if size is to big.
        assert "Sentence" not in random.paragraphs(10)


    def test_whitespace(self):
        random = RandomHelper("", [CONTENT_2])
        # indentation should be preserved
        paras = ["    Space indented paragraph.\n", "\tTab indented paragraph.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras

    def test_one_line(self):
        random = RandomHelper("", [CONTENT_3])
        assert random.paragraphs(1) == "One line.\n"


    def test_multiple_files(self):
        random = RandomHelper("", [CONTENT_1, CONTENT_2])
        paras1 = ["Sentence a.  Sentence b.  Sentence c.\n", "Sentence d. Sentence e.\n", "Sentence f.\n"]
        paras2 = ["    Space indented paragraph.\n", "\tTab indented paragraph.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras1 + paras2

        for _ in range(10): # Only CONTENT_1 has 3 paragraphs. Won't combine files.
            assert random.paragraphs(3) == "Sentence a.  Sentence b.  Sentence c.\n\nSentence d. Sentence e.\n\nSentence f.\n"

        for _ in range(10): # Lorem ipsum since there is no file that is big enough.
            assert "Sentence" not in random.paragraphs((4, 10))

    def test_no_content_sources(self):
        random = RandomHelper("")

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert len(random.paragraphs(10).split("\n\n")) == 10
            assert random.paragraphs(10).endswith("\n")