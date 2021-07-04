""" Miscellaneous support classes and functions """
from typing import Iterable, Union, Callable,  Dict, Any, List
import os, time, inspect

PathLike = Union[str, os.PathLike]
"""Type for a string representing a path or a PathLike object."""

def extra_func_params(func: Callable[..., Any], params: List[str]):
    """ Returns any params of func that aren't in params. You can use this to check if you can safely use call_with_args() """
    func_params = set(inspect.getfullargspec(func).args)
    return [parm for parm in func_params if parm not in params]

def call_with_args(func: Callable[..., Any], args: Dict[str, Any]) -> Any:
    """
    Takes a function and a map of args to their names. Any values in args that have the same name as a parameter of func
    will be passed to func. Ignores missing args, and will throw an error if func has parameters that aren't in args.
    Returns the return result of func.
    """
    func_params = set(inspect.getfullargspec(func).args)
    known_args = list(args.keys())

    # Make sure there are no unrecognized parameters
    extra_params = extra_func_params(func, known_args)
    if extra_params:
        raise UnrecognizedParamsError(
            f'Unrecognized param(s) {sentence_list(extra_params, quote = True)}.' + 
            f' Expected {sentence_list(known_args, last_sep = " and/or ", quote = True)}.',
            extra_params = extra_params
        )

    # Only pass the args that the checker function has
    args_to_pass = {param: args[param] for param in func_params}
    return func(**args_to_pass)

class UnrecognizedParamsError(Exception):
    """ Exception for when call_with_args's func has paramaters not in the given paramater list. """
    def __init__(self, message: str, extra_params: List[str]):
        self.message = message
        self.extra_params = extra_params

    def __str__(self):
        return self.message
    
    def __reduce__(self): # Make it picklable
        return (type(self), (self.message, self.extra_params))

def retry(func: Callable[[], Any], tries = 16, delay = 0.25) -> Any:
    """
    Retries the given function until it succeeds without an error.
    tries is the maximum number of tries, delay is delay betwen tries
    """
    for attempt in range(tries - 1):
        try:
            return func()
        except:
            time.sleep(delay)
    return func() # Last time just let the errors get raised.

def sentence_list(arr: Iterable[str], sep: str = ", ", last_sep: str = " and ", quote = False):
    """
    Takes a list of strings, returns a string representing the list with the final seperator different. Optionally
    quotes each of the items. Eg.
    >>> sentence_list(["a", "b", "c"])
    "a, b and c"
    >>> sentence_list(["a", "b"], quote = True, last_sep = " or ")
    "'a' or 'c'"
    """
    arr = list(arr)
    if quote:
        arr = [repr(s) for s in arr]

    if len(arr) == 0:
        return ""
    elif len(arr) == 1:
        return arr[0]
    else:
        return sep.join(arr[:-1]) + last_sep + arr[-1]

    