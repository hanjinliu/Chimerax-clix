from chimerax.core.commands.cli import (
    NoArg, NoneArg, BoolArg, StringArg, EmptyArg, EnumOf, DynamicEnum, IntArg, Int2Arg,
    Int3Arg, IntsArg, NonNegativeIntArg, PositiveIntArg, FloatArg, Float2Arg, Float3Arg, 
    FloatsArg, NonNegativeFloatArg, PositiveFloatArg, FloatOrDeltaArg, AxisArg, 
    CenterArg, CoordSysArg, PlaceArg, Bounded, SurfacesArg, SurfaceArg, 
    ModelIdArg, ModelArg, ModelsArg, TopModelsArg, ObjectsArg, RestOfLine, 
    WholeRestOfLine, FileNameArg, OpenFileNameArg, SaveFileNameArg, OpenFolderNameArg, 
    SaveFolderNameArg, OpenFileNamesArg, AttrNameArg, PasswordArg, CharacterArg
)
from chimerax.core.commands.colorarg import ColorArg, Color8Arg, Color8TupleArg, ColormapArg, ColormapRangeArg
from chimerax.core.commands.atomspec import AtomSpecArg

_STR_MAP: dict[type, str] = {
    NoArg: "no argument",
    NoneArg: "None",
    BoolArg: "bool",
    StringArg: "str",
    EmptyArg: "empty",
    IntArg: "int",
    Int2Arg: "(int, int)",
    Int3Arg: "(int, int, int)",
    IntsArg: "(int, ...)",
    NonNegativeIntArg: "int (&le; 0)",
    PositiveIntArg: "int (&lt; 0)",
    FloatArg: "float",
    Float2Arg: "(float, float)",
    Float3Arg: "(float, float, float)",
    FloatsArg: "(float, ...)",
    NonNegativeFloatArg: "float (&le; 0)",
    PositiveFloatArg: "float (&lt; 0)",
    FloatOrDeltaArg: "float or delta",
    FileNameArg: "file name", 
    OpenFileNameArg: "existing file path", 
    SaveFileNameArg: "file path", 
    OpenFolderNameArg: "existing folder path", 
    SaveFolderNameArg: "folder path", 
    OpenFileNamesArg: "existing file paths",
    AxisArg: "axis (3 floats, \"x\", \"y\", \"z\" or two atoms)",
    CenterArg: "center (3 floats or objects)",
    RestOfLine: "rest of line",
    WholeRestOfLine: "whole rest of line",
    ColorArg: "color",
    Color8Arg: "color (8-bit)",
    Color8TupleArg: "(int, int, int)",
    ColormapArg: "colormap",
    ColormapRangeArg: "colormap range",
}

def _cls_to_str(cls: type):
    return _STR_MAP.get(cls, cls.__name__)

def _enum_to_str(ann: EnumOf):
    return "{" + ", ".join(ann.values) + "}"

def _dyn_enum_to_str(ann: DynamicEnum):
    return "{" + ", ".join(ann.values_func()) + "}"

def _bounded_to_str(ann: Bounded):
    base_anno = parse_annotation(ann.anno)
    if ann.inclusive:
        return f"{base_anno} ({ann.min} &le; X &le; {ann.max})"
    else:
        return f"{base_anno} ({ann.min} &lt; X &lt; {ann.max})"

def parse_annotation(ann) -> str:
    if isinstance(ann, type):
        return _cls_to_str(ann)
    if isinstance(ann, EnumOf):
        return _enum_to_str(ann)
    if isinstance(ann, DynamicEnum):
        return _dyn_enum_to_str(ann)
    if isinstance(ann, Bounded):
        return _bounded_to_str(ann)
    return str(ann)
