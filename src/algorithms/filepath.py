from __future__ import annotations
from pathlib import Path
from typing import Iterable

def complete_path(last_word: str) -> list[str] | None:
    """Return list of available paths for the given last word."""
    if last_word == "":
        return None
    if last_word.endswith(("/.", "\\.")):
        # If path string ends with ".", pathlib.Path will ignore it.
        # Here, we replace it with "$" to avoid this behavior.
        _maybe_path = Path(last_word[:-1].lstrip("'").lstrip('"')).absolute() / "$"
    else:
        _maybe_path = Path(last_word.lstrip("'").lstrip('"')).absolute()
    if _maybe_path.exists():
        if _maybe_path.is_dir():
            if last_word.endswith(("/", "\\")):
                sep = ""
            else:
                sep = "\\" if "\\" in last_word else "/"
            completions = [
                sep + _p for _p in _iter_upto(p.name for p in _maybe_path.glob("*"))
            ]
            return completions
    elif _maybe_path.parent.exists() and _maybe_path != Path("/").absolute():
        _iter = _maybe_path.parent.glob("*")
        pref = _maybe_path.as_posix().rsplit("/", 1)[1]
        if pref == "$":
            pref = "."
        completions = _iter_upto(
            (p.name for p in _iter if p.name.startswith(pref)),
            include_hidden=pref.startswith(".") or pref == "$",
        )
        return completions
    return None

def _iter_upto(it: Iterable[str], n: int = 64, include_hidden: bool = False) -> list[str]:
    if include_hidden:
        return [a for _, a in zip(range(n), it)]
    else:
        return [a for _, a in zip(range(n), it) if not a.startswith(".")]


if __name__ == "__main__":
    import os

    def assert_equal(a, b):
        assert a == b, f"{a=} {b=}"

    cwd = Path(__file__).parent.parent.as_posix()
    os.chdir(cwd)  # cd src

    assert_equal(complete_path("co"), ["completion"])
    assert_equal(complete_path("t"), ["tool.py", "types.py"])

    # absolute path
    assert_equal(complete_path(f"{cwd}/co"), ["completion"])
    assert_equal(complete_path(f"{cwd}/t"), ["tool.py", "types.py"])
    print("PASSED")
