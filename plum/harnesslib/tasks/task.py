"""
Module for Tasks.

An experiment conceptually breaks down into "tasks" that should be executed and which outputs data.
This data should be stored, and also piped forward into later tasks. In this conceptual framework, a
"task" may be seen as a void function that does its thing and returns some result.

For data storage, it is imperative that this void function be statically type annotated, as the
`Runner` will provide this type to the `DataCollector` for deciding how to storage the impending
output of the task.

The `Task` class captures this concept and makes it Pythonic to apply in experiments: The
constructor of a `Task` is where the task-specific input is given, while its `execute` method is the
void function that does the work and returns the results. The `execute` method is required to be
type annotated for data storage.
"""

from plum.harnesslib.data import HasId
from typing import Generic, Union, TypeVar
from abc import ABC, abstractmethod
from typing import get_args
from inflection import underscore, pluralize


T_SRow = TypeVar('T_SRow', bound=HasId, covariant=True)
"Type for a row of data or a super-type thereof"

TaskResult = Union[T_SRow, list[T_SRow]]
"The result of a task may be a single row of data, or a list of rows"


class GenericTask(ABC, Generic[T_SRow]):
    """
    This is a base class for a task, which is essentially a void function that returns some result.

    Wrapping up such a void function as an instance of `Task` is for tidiness: The constructor is
    the natural place for providing the arguments needed for carrying out the task, while the
    `execute()` method allows a return type annotation.
    """

    def __init__(self, result_name: Union[str, None] = None):
        """
        Initialize the result_name.

        Args:
            result_name: the default name used for the task.
        """
        self.result_name = result_name or generate_result_name_from_task(self)

    @abstractmethod
    def execute(self) -> TaskResult[T_SRow]:
        """
        Execute the given task.
        """


def generate_result_name_from_task(task_obj: GenericTask[T_SRow]) -> str:
    """Given a task object, generate a pluralized snake_case name for the result.

    Args:

    task_obj: The task object to generate the result name from.

    Returns: pluralized snake_case name from the return type of the task.
    """

    # The __orig_bases__ is only present in a Generic class and here we want
    # on restrict only to GenericTask.
    if not (hasattr(task_obj.__class__, "__orig_bases__") and (
            task_obj.__class__.__orig_bases__[0] != "GenericTask")):  # type: ignore
        raise TypeError("The task must be derived from a base class that derives from GenericTask.")

    return underscore(pluralize(get_args(task_obj.__class__.__orig_bases__[0])[  # type: ignore
                      0].__name__))


class SingleResultTask(GenericTask[T_SRow]):
    """
    A task that returns a single result.
    """
    @abstractmethod
    def execute(self) -> T_SRow:
        """
        Execute the given task.
        """


class MultiResultTask(GenericTask[T_SRow]):
    """
    A task that returns a single result.
    """

    @abstractmethod
    def execute(self) -> list[T_SRow]:
        """
        Execute the given task.
        """


Task = Union[SingleResultTask[T_SRow], MultiResultTask[T_SRow]]
