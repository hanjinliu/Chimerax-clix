from __future__ import annotations

from typing import Callable, Iterator
from .state import CompletionState, Context
from ..types import ModelType, ChainType

ALL_ATOMS = ["Ca", "Cb", "C", "N", "O", "OH"]
ALL_AMINO_ACIDS = [
    "Ala", "Arg", "Asn", "Asp", "Cys", "Gln", "Glu", "Gly", "His", "Ile",
    "Leu", "Lys", "Met", "Phe", "Pro", "Ser", "Thr", "Trp", "Tyr", "Val",
]

TOOLTIP_FOR_AMINO_ACID = {
    "Ala": "Alanine (A)",
    "Arg": "Arginine (R)",
    "Asn": "Asparagine (N)",
    "Asp": "Aspartic acid (D)",
    "Cys": "Cysteine (C)",
    "Gln": "Glutamine (Q)",
    "Glu": "Glutamic acid (E)",
    "Gly": "Glycine (G)",
    "His": "Histidine (H)",
    "Ile": "Isoleucine (I)",
    "Leu": "Leucine (L)",
    "Lys": "Lysine (K)",
    "Met": "Methionine (M)",
    "Phe": "Phenylalanine (F)",
    "Pro": "Proline (P)",
    "Ser": "Serine (S)",
    "Thr": "Threonine (T)",
    "Trp": "Tryptophan (W)",
    "Tyr": "Tyrosine (Y)",
    "Val": "Valine (V)",
}

def complete_model(
    context: Context,
    last_word: str,
    current_command: str | None,
    model_filter: Callable[[list[ModelType]], list[ModelType]] = lambda x: x,
):
    # model ID completion
    # "#" -> "#1 (model name)" etc.
    # try model+chain specifiction completion such as "#1/B"
    models = model_filter(context.models)
    if "/" in last_word:
        model_spec_str, chain_spec = last_word.rsplit("/", 1)
        model_spec = ModelSpec(model_spec_str[1:])
        state = complete_chain(
            context.with_models(model_spec.filter(models)),
            last_word="/" + chain_spec, 
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{model_spec_str}{c}" for c in state.completions],
            command=current_command,
            info=state.info,
            type="model," + state.type
        )
        
    if ":" in last_word:
        model_spec_str, chain_spec = last_word.split(":", 1)
        model_spec = ModelSpec(model_spec_str[1:])
        state = complete_residue(
            context.with_models(model_spec.filter(models)), 
            last_word=":" + chain_spec,
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{model_spec_str}{r}" for r in state.completions],
            command=current_command,
            info=state.info,
            type="model," + state.type,
        )
    if "@" in last_word:
        model_spec_str, atom_spec = last_word.split("@", 1)
        model_spec = ModelSpec(model_spec_str[1:])
        state = complete_atom(
            context.with_models(model_spec.filter(models)),
            last_word="@" + atom_spec,
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{model_spec_str}{a}" for a in state.completions],
            command=current_command,
            info=state.info,
            type="model," + state.type,
        )

    comps: list[str] = []
    info: list[str] = []
    seed = _make_seed(last_word, "#")
    if "," in seed or "-" in seed:
        former, sep, num = _rsplit_spec(seed)
        spec_existing = ModelSpec(former)
        # check the former part exists in the model list
        if len(spec_existing.filter(models)) == 0:
            return CompletionState(last_word, [], current_command)
        for model in models:
            model_spec = ".".join(str(_id) for _id in model.id)
            if model_spec.startswith(num) and not spec_existing.contains(model):
                comps.append(f"#{former}{sep}{model_spec}")
                info.append("..." + model.name)
    else:
        for model in models:
            spec = _model_to_spec(model)
            if spec.startswith("#" + seed):
                comps.append(spec)
                info.append(model.name)
    return CompletionState(last_word, comps, current_command, info, type="model")

def complete_chain(
    context: Context,
    last_word: str,
    current_command: str | None,
    model_filter: Callable[[list[ModelType]], list[ModelType]] = lambda x: x,
):
    models = model_filter(context.models)
    if ":" in last_word:
        chain_spec_str, residue_spec = last_word.split(":", 1)
        state = complete_residue(
            context.with_models(models),
            last_word=":" + residue_spec,
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{chain_spec_str}{r}" for r in state.completions],
            command=current_command,
            info=state.info,
            type="chain," + state.type,
        )
    if "@" in last_word:
        chain_spec_str, atom_spec = last_word.split("@", 1)
        state = complete_atom(
            context.with_models(models),
            last_word="@" + atom_spec,
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{chain_spec_str}{a}" for a in state.completions],
            command=current_command,
            info=state.info,
            type="chain," + state.type,
        )
    
    all_chains: list[ChainType] = []
    for model in models:
        if hasattr(model, "chains"):
            all_chains.extend(model.chains)

    # collect all the available chain IDs
    all_chain_ids: set[str] = set()
    seed = _make_seed(last_word, "/")
    if "," in seed or "-" in seed:
        former, sep, num = _rsplit_spec(seed)
        spec_existing = ChainSpec(former)
        # check the former part exists in the model list
        if len(spec_existing.filter(all_chains)) == 0:
            return CompletionState(last_word, [], current_command)
        for chain in all_chains:
            _id: str = chain.chain_id
            if _id.startswith(num) and not spec_existing.contains(chain):
                all_chain_ids.add(f"/{former}{sep}{_id}")
    else:
        for chain in all_chains:
            if chain.chain_id.startswith(seed):  # chain id does not start with "/"
                all_chain_ids.add(f"/{chain.chain_id}")
    all_chain_ids = sorted(all_chain_ids)

    # Now, all_chain_ids is like ["/A", "/B", ...]
    return CompletionState(
        last_word, all_chain_ids, current_command, 
        ["(<i>chain ID</i>)"] * len(all_chain_ids), type="chain"
    )

def complete_residue(
    context: Context,
    last_word: str,
    current_command: str | None,
    model_filter: Callable[[list[ModelType]], list[ModelType]] = lambda x: x,
):
    models = model_filter(context.models)
    if "@" in last_word:
        residue_spec_str, atom_spec = last_word.split("@", 1)
        all_atoms = [f"{residue_spec_str}@{_a}" for _a in ALL_ATOMS if _a.startswith(atom_spec)]
        return CompletionState(
            last_word, 
            completions=all_atoms,
            command=current_command, 
            info=["(<i>atom</i>)"] * len(all_atoms), 
            type="residue,atom",
        )
    all_non_std_residues: set[str] = set()
    for model in models:
        if not hasattr(model, "nonstandard_residue_names"):
            continue
        all_non_std_residues.update(
            f":{_r}" for _r in model.nonstandard_residue_names 
            if _r.startswith(last_word[1:])
        )
    non_std_res = sorted(all_non_std_residues)
    # Now, completions is like [":ATP", ":GTP", ...]
    # Adds the standard amino acids
    seed = _make_seed(last_word, ":")
    aa = [f":{_a}" for _a in ALL_AMINO_ACIDS if _a.startswith(seed)]
    return CompletionState(
        last_word, 
        completions=non_std_res + aa,
        command=current_command, 
        info=["(<i>residue</i>)"] * len(non_std_res) + ["(<i>amino acid</i>)"] * len(aa),
        type="residue",
    )

def complete_atom(context: Context, last_word: str, current_command: str | None):
    seed = _make_seed(last_word, "@")
    all_atoms = [f"@{_a}" for _a in ALL_ATOMS if _a.startswith(seed)]
    return CompletionState(
        last_word, 
        completions=all_atoms,
        command=current_command, 
        info=["(<i>atom</i>)"] * len(all_atoms), 
        type="atom",
    )

def _make_seed(last_word: str, prefix: str) -> str:
    if last_word.startswith(prefix):
        return last_word[len(prefix):]
    return last_word

def _model_to_spec(model):
    return "#" + ".".join(str(_id) for _id in model.id)


class ModelSpec:
    def __init__(self, spec: str):
        ids: set[tuple[int, ...]] = set()
        for s in spec.split(","):
            if "." in s:
                s0, s1 = s.split(".", 1)
                if "-" in s1:
                    # "#1.1-3" -> (1, 1), (1, 2), (1, 3)
                    try:
                        model_id = int(s0)
                    except ValueError:
                        continue
                    start, end = s1.split("-", 1)
                    ids.update((model_id, x) for x in _safe_range(start, end))
                elif "-" in s0:
                    # not understood
                    continue
                else:
                    try:
                        ids.add((int(s0), int(s1)))
                    except ValueError:
                        continue
            else:
                if "-" in s:
                    start, end = s.split("-", 1)
                    ids.update((x,) for x in _safe_range(start, end))
                else:
                    try:
                        ids.add((int(s),))
                    except ValueError:
                        continue
        self.ids = ids

    def filter(self, models: list[ModelType]) -> list[ModelType]:
        return [m for m in models if m.id in self.ids]
    
    def contains(self, model: ModelType) -> bool:
        return model.id in self.ids

class ChainSpec:
    def __init__(self, spec: str):
        ids: set[int] = set()
        for s in spec.split(","):
            if "-" in s:
                start, end = s.split("-", 1)
                ids.update(x for x in _safe_char_range(start, end))
            else:
                try:
                    ids.add(ord(s))
                except (TypeError, ValueError):
                    continue
        self.ids = ids
    
    def filter(self, chains: list[ChainType]) -> list:
        return [c for c in chains if ord(c.chain_id) in self.ids]
    
    def contains(self, chain: ChainType) -> bool:
        return ord(chain.chain_id) in self.ids

def _safe_range(start: str, end: str) -> range:
    try:
        return range(int(start), int(end) + 1)
    except ValueError:
        return range(0)

def _safe_char_range(start: str, end: str) -> Iterator[int]:
    try:
        return iter(i for i in range(ord(start), ord(end) + 1))
    except (TypeError, ValueError):
        return iter([])

def _rsplit_spec(spec: str) -> tuple[str, str, str]:
    """
    Split by - or ,
    
    _rsplit_spec("1-3") -> ("1", "-", "3")
    _rsplit_spec("1-3,5") -> ("1-3", ",", "5")
    """
    hyphen_idx = spec.rfind("-")
    comma_idx = spec.rfind(",")
    if hyphen_idx == -1 and comma_idx == -1:
        return spec, "", ""
    idx = max(hyphen_idx, comma_idx)
    return spec[:idx], spec[idx], spec[idx+1:]
