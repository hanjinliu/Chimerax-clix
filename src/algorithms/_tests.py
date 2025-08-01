import os
from pathlib import Path
from . import complete_path, complete_model, complete_chain, complete_residue, complete_atom, Context
from ..types import ChainType, ModelType, WordInfo, CmdDesc

def test_complete_path():
    cwd = Path(__file__).parent.parent.as_posix()
    os.chdir(cwd)  # cd src

    assert complete_path("al", "open").completions == ["algorithms"]
    assert complete_path("t", "open").completions == ["tool.py", "types.py"]

    # absolute path
    assert complete_path(f"{cwd}/al", "open").completions == ["algorithms"]
    assert complete_path(f"{cwd}/t", "open").completions == ["tool.py", "types.py"]

def get_context():
    models = [
        ModelType(id=(1,), name="protein A", chains=[ChainType("A"), ChainType("B")], nonstandard_residue_names={"ATP"}),
        ModelType(id=(1, 1), name="protein A-1"),
        ModelType(id=(1, 2), name="protein A-2"),
        ModelType(id=(2,), name="protein B", chains=[ChainType("A")]),
    ]
    return Context(
        models=models,
        selectors=[], 
        wordinfo=WordInfo(cmd_desc=CmdDesc.construct()),
    )

def test_complete_model():
    ctx = get_context()
    out = complete_model(ctx, "#", "show")
    assert out.completions == ["#1", "#2", "#1.1", "#1.2"]
    out = complete_model(ctx, "#1", "show")
    assert out.completions == ["#1", "#1.1", "#1.2"]
    out = complete_model(ctx, "#1.", "show")
    assert out.completions == ["#1.1", "#1.2"]
    out = complete_model(ctx, "#2", "show")
    assert out.completions == ["#2"]

def test_complete_chain():
    ctx = get_context()
    out = complete_chain(ctx, "/", "show")
    assert out.completions == ["/A", "/B"]
    out = complete_chain(ctx, "/A", "show")
    assert out.completions == ["/A"]

def test_complete_chain_after_model():
    ctx = get_context()
    out = complete_model(ctx, "#1/", "show")
    assert out.completions == ["#1/A", "#1/B"]
    out = complete_model(ctx, "#1/A", "show")
    assert out.completions == ["#1/A"]

def test_complete_residues():
    ctx = get_context()
    out = complete_residue(ctx, ":L", "show")
    assert ":ATP" not in out.completions
    out = complete_residue(ctx, ":A", "show")
    assert ":ATP" in out.completions
    
def test_complete_atom():
    ctx = get_context()
    out = complete_atom(ctx, "@", "show")
    assert "@O" in out.completions
    out = complete_atom(ctx, "@C", "show")
    assert out.completions == ["@Ca", "@Cb", "@C"]

def test_future_annotation():
    """Test all the files start with `from __future__ import annotations`"""
    
    this_path = Path(__file__)
    root = this_path.parent.parent
    for path in root.glob("**/*.py"):
        if path.name == "__init__.py":
            continue
        if path == this_path:
            continue
        with path.open("r", encoding="utf-8") as f:
            line = f.readline()
            assert line.strip() == "from __future__ import annotations", f"File {path} does not start with `from __future__ import annotations`"
