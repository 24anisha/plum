from dataclasses import dataclass, field
from typing import NewType
import abc


ID = NewType('ID', int)
"""
Identifiers are just ints, but for increased type - safety, they are wrapped in this type alias.
"""


@dataclass
class DataModel(abc.ABC):
    """
    This is the common base class for all data recorded in lists or tables within an experiment.
    Data  model classes should extend this base class
    unless they are always nested inside another `DataModel` object.
    The ID of the object is set in :meth:`harnesslib.data.SQLDataLens.store`.
    """

    id: ID = field(default=ID(-1), init=False)
