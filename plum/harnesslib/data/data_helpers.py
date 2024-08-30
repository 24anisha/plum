"""
Helper functions for writing `DataCollector`s and `DataLens`es.
"""
from enum import Enum
import pathlib
from typing import (
    Callable,
    Dict,
    get_args,
    get_type_hints,
    Any,
    Generic,
    NamedTuple,
    Protocol,
    Type,
    TypeVar)
import jsonpickle

from plum.harnesslib.data_model.base import ID


class HasId(Protocol):
    """
    Base class for data rows with an ID.
    """
    id: ID


T_Row = TypeVar('T_Row', bound=HasId)
"""
Type variable that represents a row of storeable data.
The only requirement to such a a type is that it has an assignable field `id`.
"""


def get_all_fields(data_type: Type[object]) -> dict[str, Type[object]]:
    """
    Return all type-annotated fields defined by the given type, including inherited fields.
    """
    # Process classes in reverse MRO so later ones may override earlier ones
    fields: dict[str, Type[object]] = {}
    mro = list(data_type.mro())
    mro.reverse()
    for cls in mro:
        if cls is object:
            continue
        fields.update(get_type_hints(cls))

    # Resolve generic type varaiables
    type_var_values: dict[str, Type[object]] = {}
    if Generic in mro:
        type_var_values = {name: value for name, value in zip(  # type: ignore
            mro[-1].__parameters__, get_args(data_type))}  # type: ignore
    for name, type in fields.items():
        if type in type_var_values.keys():
            fields[name] = type_var_values[type]  # type: ignore

    return fields


def replace_if_id(value: Any) -> Any:
    """Return `value.id` if `value` is an object with an `id` field, otherwise return `value`."""
    if hasattr(value, 'id'):
        return value.id
    return value


class ExtractedData(NamedTuple):
    """
    Type for `extract_row_fields` to hold a dictionary of extracted fields, and a dictionary of
    remaining fields.
    """
    fields: dict[str, Any]
    remaining: dict[str, Any]


def extract_row_fields(
        row: Any,
        fields: set[str],
        *,
        ignore: set[str] = set()) -> ExtractedData:
    """
    Extract the data from a row as a Python dictionary, and flatten HasId fields into their ids.
    The fields named in `fields` will be put in the returned named tuple under `fields`.
    All other public fields will be put in `remaining`. Public fields will be taken to be those not
    starting with `_`.
    Fields listed in `ignore` will be ignored from either dicts.
    """
    extracted = ExtractedData({}, {})
    for key, value in row.__dict__.items():
        if key in ignore:
            continue
        if key in fields:
            extracted.fields[key] = replace_if_id(value)
        elif not key.startswith('_'):
            extracted.remaining[key] = replace_if_id(value)
    return extracted


def serialize_to_json(obj: Any) -> str:
    """
    Serialize Python types and objects to JSON, preserving the public fields.
    If `obj` is an object, this does not serialize its private members(starting with `_`), and any
    keys or values that have `id` attributes will be replaced by that `id`, unless the `id = -1`.
    TODO: This function should ideally:
     - Replace sub - objects(both keys and values) that have an assigned `id` field with their id
       (and for sub-sub-objects, etc.). This is currently only done for the direct keys and values
       of `obj`, if `obj` is a custom class element or a dict(i.e. not a list or a set, etc.)
     - Not include private fields(fields starting with '_') of sub - objects and keys.
     - Encode frozensets more elegantly.
    """
    if isinstance(obj, pathlib.Path):
        return str(obj)

    def process_dict(d: dict[Any, Any], init: dict[Any, Any] = {}) -> dict[Any, Any]:
        "Given a dict of fields, filter out private fields and replace HasId fields with their id."
        new_d: dict[Any, Any] = {**init}  # copy
        for k, v in d.items():
            if (not isinstance(k, str)) or not k.startswith('_'):
                new_d[replace_if_id(k)] = replace_if_id(v)
        return new_d
    if isinstance(obj, dict):
        objd: dict[Any, Any] = obj  # For the type checker
        serialize_obj = process_dict(objd)
    elif not hasattr(obj, "__dict__"):
        # Built-in types
        serialize_obj = obj
    else:
        serialize_obj: dict[Any, Any] = {"py-object": obj.__module__ + "." + obj.__class__.__name__}
        serialize_obj = process_dict(obj.__dict__, init=serialize_obj)
    # The replace here is a workaround since `jsonpickle.encode` leaves out the
    # key `py/object` (it produces this key itself when its input is an object,
    # but we've artificially converted that to a dict ourselves).
    return (jsonpickle.encode(serialize_obj, make_refs=False, keys=True)
            .replace("py-object", "py/object"))


class Serializer:
    """
    A serializer that can serialize different types of objects to string.
    """

    def __init__(self):
        self.schemes: Dict[Type[Any], Callable[..., str]] = {}

    def register_scheme(self, tp: Type[Any], representation: Callable[..., str]):
        self.schemes[tp] = representation

    def is_serializable(self, type: Type[Any]) -> bool:
        for tp in self.schemes:
            if issubclass(type, tp):
                return True
        return False

    def serialize(self, obj: Any) -> str:
        for tp, representation in self.schemes.items():
            if isinstance(obj, tp):
                return representation(obj)
        raise ValueError(f'Cannot convert {obj} to string')


# A default Serializer handling types that are already string-like
text_like = Serializer()
text_like.register_scheme(Enum, lambda x: x.value)
text_like.register_scheme(pathlib.Path, str)
text_like.register_scheme(str, lambda x: x)

# A more complex Serializer that serializes to JSON
json_like = Serializer()
json_like.register_scheme(object, serialize_to_json)

