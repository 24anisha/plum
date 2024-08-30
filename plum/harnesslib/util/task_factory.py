"""Tools to make it easier to discover tasks."""

from typing import Any, Type, Generic, TypeVar

from plum.harnesslib.languages import Language

T = TypeVar('T')


class LanguageSpecificTaskFactory(Generic[T]):
    """Simplifies discovery of language-specific tasks.

    These factories are usually registered in the `harnesslib.task` module as
    a way to make it easier to discover all the language-specific tasks in one place.
    """

    def __init__(self):
        """Create a new `LanguageSpecificTaskFactory`."""
        self._constructors_by_language: dict[Language, Type[T]] = {}

    def register(self, language: Language, type: Type[T]):
        """Register a `harnesslib.task.Task` constructor for a given language.`.

        Args:
            language: The `harnesslib.languages.Language` for the Task.
            type: The class Task to construct.
        """
        self._constructors_by_language[language] = type

    def __call__(self, *args: Any, language: Language, **kwargs: Any) -> T:
        """
        Construct a new language-specific task.

        Args:
            *args: Positional arguments to pass to the constructor.
            language: The `harnesslib.languages.Language` for the Task. Must be provided by keyword.
            **kwargs: Keyword arguments to pass to the constructor.
        """
        if language in self._constructors_by_language:
            return self._constructors_by_language[language](*args, **kwargs)
        else:
            raise ValueError(f"No `{T.__name__}` constructor registered for language `{language}`")
