from __future__ import annotations

import sys

if sys.platform == "win32":
    _FONT = "Consolas"
elif sys.platform == "darwin":
    _FONT = "Menlo"
else:
    _FONT = "Monospace"

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
