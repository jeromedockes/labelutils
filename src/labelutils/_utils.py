from __future__ import annotations
import abc
from os import PathLike
import types
from typing import Union, Generator, Dict, Any, Type

PathLikeOrStr = Union[PathLike, str]


class _BaseReader:
    def read(self) -> Generator[Dict[str, Any], None, None]:
        for i, doc in enumerate(self._do_read()):
            print(f"Processed {i + 1} documents.", end="\r", flush=True)
            yield doc
        print()

    @abc.abstractmethod
    def _do_read(self) -> Generator[Dict[str, Any], None, None]:
        """Read documents from a given format and yield them as dicts."""

    def __enter__(self) -> _BaseReader:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        del exc_type, exc_value, traceback
