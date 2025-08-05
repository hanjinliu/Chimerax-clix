from __future__ import annotations

from typing import Callable, Iterator
from .state import CompletionState, Context
from .action import ResidueAction, MissingResidueAction, Action
from .specs import ModelSpec, ChainSpec, ResidueSpec
from .._utils import colored
from ..types import ModelType, ChainType
from ..consts import ALL_ATOMS, ALL_AMINO_ACIDS

def complete_model(
    context: Context,
    last_word: str,
    current_command: str | None,
    model_filter: Callable[[list[ModelType]], list[ModelType]] = lambda x: x,
):
    """Get model completion state for given context.
    
    Parameters
    ----------
    context : Context
        The context of the application.
    last_word : str
        The last word in the command line to complete.
    current_command : str | None
        The current command being typed, if any.
    model_filter : Callable[[list[ModelType]], list[ModelType]], optional
        A function to filter models, such as to only include surfaces.
    """
    # model ID completion
    # "#" -> "#1 (model name)" etc.
    # try model+chain specifiction completion such as "#1/B"
    models = model_filter(context.models)
    if "/" in last_word:
        model_spec_str, chain_spec_str = last_word.rsplit("/", 1)
        model_spec = ModelSpec(model_spec_str[1:])
        if ":" in chain_spec_str and not chain_spec_str.endswith((":", "@")):
            if state_list_aa := list_amino_acids(
                context, last_word, current_command, model_spec, chain_spec_str
            ):
                return state_list_aa
        state = complete_chain(
            context.with_models(model_spec.filter(models)),
            last_word="/" + chain_spec_str,
            current_command=current_command,
        )
        return CompletionState(
            text=last_word,
            completions=[f"{model_spec_str}{c}" for c in state.completions],
            command=current_command,
            info=state.info,
            type="model," + state.type
        )
        
    if ":" in last_word and not last_word.endswith("@"):
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
        # seed is like "1-3,5"
        former, sep, num = _rsplit_spec(seed)
        spec_existing = ModelSpec(former)
        # check the former part exists in the model list
        if len(spec_existing.filter(models)) == 0:
            return CompletionState(last_word, [], current_command)
        for model in _natural_sort_models(models):
            model_spec = ".".join(str(_id) for _id in model.id)
            if model_spec.startswith(num) and not spec_existing.contains(model):
                comps.append(f"#{former}{sep}{model_spec}")
                info.append(colored("..." + model.name, "#F88181"))
    else:
        for model in _natural_sort_models(models):
            spec = _model_to_spec(model)
            if spec.startswith("#" + seed):
                comps.append(spec)
                info.append(colored(model.name, "#F88181"))
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
    chain_descriptions: dict[str, str] = {}
    seed = _make_seed(last_word, "/")
    if "," in seed or "-" in seed:
        # chain ID is a list of IDs such as "/A,B,C"
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
                chain_id = f"/{chain.chain_id}"
                all_chain_ids.add(chain_id)
                if chain.description:
                    chain_descriptions[chain_id] = colored(chain.description, "#F88181")
    all_chain_ids = sorted(all_chain_ids)
    _fallback_desc = colored("(<i>chain ID</i>)", "#F88181")
    info = [chain_descriptions.get(chain_id, _fallback_desc) for chain_id in all_chain_ids]

    # Now, all_chain_ids is like ["/A", "/B", ...]
    return CompletionState(
        last_word,
        all_chain_ids, 
        current_command, 
        info=info, 
        type="chain"
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

def list_amino_acids(
    context: Context,
    last_word: str,
    current_command: str | None,
    model_spec: ModelSpec,
    chain_spec_str: str,
    type: str = "model,chain,residue",
):
    chain_spec_str, residue_spec_str = chain_spec_str.split(":", 1)
    residue_spec = ResidueSpec(residue_spec_str)
    if residue_spec.entries:
        # if user start typing residue number, show sequence view.
        res_index = residue_spec.last_index()
        actions, index_start = _get_residue_actions(context, res_index, model_spec, ChainSpec(chain_spec_str)) or []
        return CompletionState(
            text=last_word,
            completions=[""] * len(actions),
            command=current_command,
            info=[action.info() for action in actions],
            action=actions,
            type=type,
            index_start=index_start,
        )
    return None

def _make_seed(last_word: str, prefix: str) -> str:
    if last_word.startswith(prefix):
        return last_word[len(prefix):]
    return last_word

def _model_to_spec(model: ModelType) -> str:
    return "#" + ".".join(str(_id) for _id in model.id)

def _natural_sort_models(models: list[ModelType]) -> Iterator[ModelType]:
    """Sort models by their IDs in a natural way.
    
    (i,) comes before (i, j) or (i, j, k).
    """
    yield_later: "list[ModelType]" = []
    for model in models:
        if len(model.id) == 1:
            yield model
        else:
            yield_later.append(model)
    yield from sorted(yield_later, key=lambda m: m.id)


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

def _get_residue_actions(
    context: Context,
    res_index: int,  # usually one-based index
    model_spec: ModelSpec,
    chain_spec: ChainSpec,
) -> tuple[list[Action], int]:
    current_chain = _get_chain(context.models, model_spec, chain_spec)
    if current_chain is None:
        return [], 0
    if res_index < 0 or res_index >= len(current_chain.residues):
        return [], 0
    output = []
    num_residues = len(current_chain.residues)
    characters = current_chain.characters
    num_to_show = 40
    _range_start = max(0, res_index - num_to_show)
    _range_stop = min(num_residues, res_index + num_to_show)
    _iter = zip(
        range(_range_start, _range_stop), 
        characters[_range_start:_range_stop]
    )
    i_start = current_chain.numbering_start
    for i, char in _iter:
        res = current_chain.residues[i]
        if res is None:
            output.append(MissingResidueAction(i + i_start, char))
        else:
            output.append(ResidueAction(res))
    return output, res_index - _range_start - i_start

def _get_chain(
    models: list[ModelType],
    model_spec: ModelSpec,
    chain_spec: ChainSpec,
) -> ChainType | None:
    """Get the chain from the models based on the model and chain specifications."""
    for model in models:
        if model_spec.contains(model):
            for chain in model.chains:
                if chain_spec.contains(chain):
                    return chain
    return None
