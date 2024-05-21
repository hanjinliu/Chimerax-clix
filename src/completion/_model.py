from __future__ import annotations
from .state import CompletionState

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

def complete_model(session, last_word: str, current_command: str | None):
    # model ID completion
    # "#" -> "#1 (model name)" etc.
    # try model+chain specifiction completion such as "#1/B"
    if "/" in last_word:
        model_spec, chain_spec = last_word.split("/", 1)
        for model in session.models.list():
            if _model_to_spec(model) == model_spec and hasattr(model, "chains"):
                with_chain_ids: list[str] = list(
                    f"{model_spec}/{_i}" for _i in model.chains.chain_ids
                    if _i.startswith(chain_spec)
                )
                return CompletionState(
                    last_word, with_chain_ids, current_command, 
                    ["<i>chain ID</i>"] * len(with_chain_ids), type="model,chain"
                )
    if ":" in last_word:
        model_spec, chain_spec = last_word.split(":", 1)
        for model in session.models.list():
            if _model_to_spec(model) == model_spec and hasattr(model, "nonstandard_residue_names"):
                with_residues: list[str] = list(
                    f"{model_spec}:{_r}" for _r in model.nonstandard_residue_names
                    if _r.startswith(chain_spec)
                )
                return CompletionState(
                    last_word, with_residues, current_command, 
                    ["<i>residue</i>"] * len(with_residues), type="model,residue"
                )
    if "@" in last_word:
        _, atom_spec = last_word.split("@", 1)
        all_atoms = [f"@{_a}" for _a in ALL_ATOMS if _a.startswith(atom_spec)]
        return CompletionState(
            last_word, all_atoms, current_command, 
            ["<i>atom</i>"] * len(all_atoms), type="model,atom"
        )
    comps = []
    info = []
    for model in session.models.list():
        spec = _model_to_spec(model)
        if spec.startswith(last_word):
            comps.append(_model_to_spec(model))
            info.append(model.name)
    return CompletionState(last_word, comps, current_command, info, type="model")

def complete_chain(session, last_word: str, current_command: str | None):
    # collect all the available chain IDs
    all_chain_ids: set[str] = set()
    for model in session.models.list():
        if not hasattr(model, "chains"):
            continue
        all_chain_ids.update(
            f"/{_i}" for _i in model.chains.chain_ids if _i.startswith(last_word[1:])
        )
    all_chain_ids = sorted(all_chain_ids)
    # Now, all_chain_ids is like ["/A", "/B", ...]
    return CompletionState(
        last_word, all_chain_ids, current_command, 
        ["<i>chain ID</i>"] * len(all_chain_ids), type="chain"
    )

def complete_residue(session, last_word: str, current_command: str | None):
    all_non_std_residues: set[str] = set()
    for model in session.models.list():
        if not hasattr(model, "nonstandard_residue_names"):
            continue
        all_non_std_residues.update(
            f":{_r}" for _r in model.nonstandard_residue_names 
            if _r.startswith(last_word[1:])
        )
    completions = sorted(all_non_std_residues)
    # Now, completions is like [":ATP", ":GTP", ...]
    # Adds the standard amino acids
    completions.extend(f":{_a}" for _a in ALL_AMINO_ACIDS if _a.startswith(last_word[1:]))
    return CompletionState(
        last_word, completions, current_command, 
        ["<i>residue</i>"] * len(all_non_std_residues) + ["<i>amino acid</i>"] * len(ALL_AMINO_ACIDS),
        type="residue",
    )

def complete_atom(session, last_word: str, current_command: str | None):
    all_atoms = [f"@{_a}" for _a in ALL_ATOMS if _a.startswith(last_word[1:])]
    return CompletionState(
        last_word, all_atoms, current_command, 
        ["<i>atom</i>"] * len(all_atoms), type="atom",
    )

def _model_to_spec(model):
    return "#" + ".".join(str(_id) for _id in model.id)
