import pytest, re
from shell_adventure_docker import support
from shell_adventure_docker.support import call_with_args, sentence_list, UnrecognizedParamsError

class TestSupport:
    def test_call_with_args(self):
        args = {"a": 1, "b": 2, "c": 3}

        func = lambda a, b, c: (a, b, c)
        assert call_with_args(func, args) == (1, 2, 3)

        func = lambda a, b: (a, b)
        assert call_with_args(func, args) == (1, 2)

        func = lambda c: c
        assert call_with_args(func, args) == 3

        func = lambda: True
        assert call_with_args(func, args) == True

    def test_call_with_args_error(self):
        args = {"a": 1, "b": 2, }

        func = lambda c: True
        with pytest.raises(UnrecognizedParamsError, match = re.escape('Unrecognized param(s) c. Expected a and/or b.')):
            call_with_args(func, args)

    def test_retry(self):
        count = 0
        def func():
            nonlocal count
            count += 1
            raise KeyError("Key!")

        with pytest.raises(KeyError, match = "Key!"):
            support.retry(func, tries = 5, delay = 0)

        assert count == 5

    def test_sentence_list(self):
        assert sentence_list(["a", "b", "c"]) == "a, b and c"
        assert sentence_list(["a", "b"]) == "a and b"
        assert sentence_list(["a"]) == "a"
        assert sentence_list([]) == ""

        assert sentence_list(["a", "b", "c"], sep = "+", last_sep = "=") == "a+b=c"
        assert sentence_list( (str(i) for i in range(3)) ) == "0, 1 and 2" # iterables work as well as list

