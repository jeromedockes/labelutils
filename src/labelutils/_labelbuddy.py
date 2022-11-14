"""labelbuddy’s JSONL format."""

from __future__ import annotations
import io
import json
import pathlib
import types
from typing import Any, Dict, Generator, Optional, Type, Mapping, Iterable

from labelutils import _utils


class LabelBuddyReader(_utils._BaseReader):
    format_name = "labelbuddy"

    @staticmethod
    def edit_argument_parser(parser):
        parser.add_argument(
            "--in_jsonl",
            type=str,
            help="JSONL file containing labelbuddy documents and annotations.",
        )

    @classmethod
    def from_args(cls, args):
        assert args.in_jsonl is not None
        return cls(args.in_jsonl)

    _labelbuddy_jsonl: pathlib.Path
    _open_file: Optional[io.TextIOWrapper]

    def __init__(self, labelbuddy_jsonl: _utils.PathLikeOrStr) -> None:
        self._labelbuddy_jsonl = pathlib.Path(labelbuddy_jsonl)
        self._open_file = None

    def __enter__(self) -> LabelBuddyReader:
        self._open_file = open(self._labelbuddy_jsonl, encoding="UTF-8")
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        del exc_type, exc_value, traceback
        if self._open_file is not None:
            self._open_file.close()

    def _do_read(self) -> Generator[Dict[str, Any], None, None]:
        assert self._open_file is not None, "Use as a context manager"
        for line in self._open_file:
            yield json.loads(line)


class LabelBuddyWriter:
    format_name = "labelbuddy"

    @staticmethod
    def edit_argument_parser(parser):
        parser.add_argument(
            "--out_jsonl",
            type=str,
            help="JSONL file in which to write labelbuddy documents and "
            "annotations.",
        )

    @classmethod
    def from_args(cls, args):
        assert args.out_jsonl is not None
        return cls(args.out_jsonl)

    _labelbuddy_jsonl: pathlib.Path
    _open_file: Optional[io.TextIOWrapper]

    def __init__(self, labelbuddy_jsonl: _utils.PathLikeOrStr) -> None:
        self._labelbuddy_jsonl = pathlib.Path(labelbuddy_jsonl)
        self._open_file = None

    def __enter__(self) -> LabelBuddyWriter:
        self._open_file = open(
            self._labelbuddy_jsonl, mode="w", encoding="UTF-8"
        )
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        del exc_type, exc_value, traceback
        if self._open_file is not None:
            self._open_file.close()

    def write(self, documents: Iterable[Mapping[str, Any]]) -> None:
        assert self._open_file is not None, "Use as a context manager"
        for doc in documents:
            self._open_file.write(json.dumps(doc))
            self._open_file.write("\n")
