import os
from pathlib import Path
from . import complete_path, complete_model, complete_chain, complete_residue, complete_atom
from ..types import ChainType, ModelType

def test_complete_path():
    cwd = Path(__file__).parent.parent.as_posix()
    os.chdir(cwd)  # cd src

    assert complete_path("co", "open").completions == ["completion"]
    assert complete_path("t", "open").completions == ["tool.py", "types.py"]

    # absolute path
    assert complete_path(f"{cwd}/co", "open").completions == ["completion"]
    assert complete_path(f"{cwd}/t", "open").completions == ["tool.py", "types.py"]

def _models():
    return [
        ModelType(id=(1,), name="protein A", chains=[ChainType("A"), ChainType("B")], nonstandard_residue_names={"ATP"}),
        ModelType(id=(1, 1), name="protein A-1"),
        ModelType(id=(1, 2), name="protein A-2"),
        ModelType(id=(2,), name="protein B", chains=[ChainType("A")]),
    ]

def test_complete_model():
    models = _models()
    out = complete_model(models, "#", "show")
    assert out.completions == ["#1", "#1.1", "#1.2", "#2"]
    out = complete_model(models, "#1", "show")
    assert out.completions == ["#1", "#1.1", "#1.2"]
    out = complete_model(models, "#1.", "show")
    assert out.completions == ["#1.1", "#1.2"]
    out = complete_model(models, "#2", "show")
    assert out.completions == ["#2"]

def test_complete_chain():
    models = _models()
    out = complete_chain(models, "/", "show")
    assert out.completions == ["/A", "/B"]
    out = complete_chain(models, "/A", "show")
    assert out.completions == ["/A"]

def test_complete_chain_after_model():
    models = _models()
    out = complete_model(models, "#1/", "show")
    assert out.completions == ["#1/A", "#1/B"]
    out = complete_model(models, "#1/A", "show")
    assert out.completions == ["#1/A"]

def test_complete_residues():
    models = _models()
    out = complete_residue(models, ":L", "show")
    assert ":ATP" not in out.completions
    out = complete_residue(models, ":A", "show")
    assert ":ATP" in out.completions
    
def test_complete_atom():
    models = _models()
    out = complete_atom(models, "@", "show")
    assert "@O" in out.completions
    out = complete_atom(models, "@C", "show")
    assert out.completions == ["@Ca", "@Cb", "@C"]
