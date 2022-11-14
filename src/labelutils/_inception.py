"""Inception's WebAnno 3.3 format.

txt for text and .wtsv for tokenized text with annotations.
"""
from __future__ import annotations
import dataclasses
import io
import pathlib
import re
import types
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    Mapping,
    Iterable,
    Sequence,
)

import pandas as pd

from labelutils import _utils, _char_indices


@dataclasses.dataclass
class InceptionDocPaths:
    text_file: _utils.PathLikeOrStr
    annotations_file: Optional[_utils.PathLikeOrStr] = None


class _InceptionDoc:
    _ANNOTATIONS_COLUMNS = ["token_idx", "label", "annotation_id"]
    _TOKENS_COLUMNS = [
        "token_idx",
        "sentence_idx",
        "token_idx_in_sentence",
        "start_char",
        "end_char",
        "token",
    ]
    # Use -1 rather than NaN for annotations without id so we can store them as
    # integers not floats
    _NULL_ID = -1

    convert_utf16_indices: bool

    _char_indices: _char_indices.CharIndices
    _tokens: pd.DataFrame
    _annotations: pd.DataFrame
    _doc_header: str
    _sentence_wrappers: List[Tuple[str, str]]
    _stream: io.TextIOWrapper
    _current_line: str
    _token_idx: int
    _at_end: bool

    def __init__(
        self,
        wtsv_file: pathlib.Path,
        text: str,
        convert_utf16_indices: bool = True,
    ) -> None:
        self.convert_utf16_indices = convert_utf16_indices
        self._char_indices = _char_indices.CharIndices(text)
        self._token_idx = 0
        with open(wtsv_file, "r", encoding="UTF-8") as stream:
            self._stream = stream
            self._at_end = False
            self._next()
            self._doc_header = self._read_header()
            self._sentence_wrappers = []
            tokens = []
            annotations = []
            while not self._at_end:
                (
                    sentence_wrapper,
                    sentence_tokens,
                    sentence_annotations,
                ) = self._read_sentence()
                self._sentence_wrappers.append(sentence_wrapper)
                tokens.extend(sentence_tokens)
                annotations.extend(sentence_annotations)
            self._tokens = pd.DataFrame(tokens, columns=self._TOKENS_COLUMNS)
            self._annotations = pd.DataFrame(
                annotations, columns=self._ANNOTATIONS_COLUMNS
            )

    def _next(self) -> bool:
        try:
            self._current_line = next(self._stream).rstrip("\n")
            return True
        except StopIteration:
            self._current_line = ""
            self._at_end = True
            return False

    def _read_header(self) -> str:
        header_lines = []
        while not self._at_end and not self._current_line.startswith("#Text"):
            header_lines.append(self._current_line + "\n")
            self._next()
        return "".join(header_lines)

    def _read_sentence(self):
        head_lines = []
        while not self._at_end and self._current_line.startswith("#"):
            head_lines.append(self._current_line + "\n")
            self._next()
        sentence_head = "".join(head_lines)
        sentence_tokens, sentence_annotations = [], []
        while not self._at_end and self._current_line:
            token_row, token_annotations = self._read_token()
            sentence_tokens.append(token_row)
            sentence_annotations.extend(token_annotations)
        tail_lines = []
        while not self._at_end and not self._current_line:
            tail_lines.append(self._current_line + "\n")
            self._next()
        sentence_tail = "".join(tail_lines)
        sentence_wrapper = sentence_head, sentence_tail
        return sentence_wrapper, sentence_tokens, sentence_annotations

    def _parse_annotations_line(
        self, token_idx: int, annotations_text: str
    ) -> List[Dict[str, Any]]:
        if annotations_text == "_":
            return []
        annotations = []
        annotation_parts = annotations_text.split("|")
        for part in annotation_parts:
            match = re.match(r"^(.*?)(?:\[(\d+)\])?$", part)
            assert match is not None
            annotation_id = match.group(2)
            if annotation_id is None:
                annotation_id = self._NULL_ID
            else:
                annotation_id = int(annotation_id)

            annotations.append(
                {
                    "token_idx": token_idx,
                    "label": match.group(1),
                    "annotation_id": annotation_id,
                }
            )
        return annotations

    def _parse_token_line(self, token_line: str) -> Dict[str, Any]:
        # we cannot just split on "\t" because tokens can contain tabs that are
        # not escaped, here is an example: '173-137 41017-41022       _' Also
        # some lines contain trailing tabs, for example '1-2 5-8 and _ '
        token_line = token_line.strip()
        sentence_info, char_info, rest = token_line.split("\t", maxsplit=2)
        sentence_idx, token_idx_in_sentence = map(
            int, sentence_info.split("-")
        )
        start_char, end_char = map(int, char_info.split("-"))
        if self.convert_utf16_indices:
            start_char, end_char = self._char_indices.utf16_to_unicode[
                [start_char, end_char]
            ]
        token, annotations_text = rest.rsplit("\t", maxsplit=1)
        return {
            "sentence_idx": sentence_idx,
            "token_idx_in_sentence": token_idx_in_sentence,
            "start_char": start_char,
            "end_char": end_char,
            "token": token,
            "annotations_text": annotations_text,
        }

    def _read_token(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        token_row = self._parse_token_line(self._current_line)
        token_row["token_idx"] = self._token_idx
        token_annotations = self._parse_annotations_line(
            self._token_idx, token_row.pop("annotations_text")
        )
        self._token_idx += 1
        self._next()
        return token_row, token_annotations

    def _get_annotations_lines(self):
        annotations_text = self._annotations["label"].copy()
        has_id = self._annotations["annotation_id"] != self._NULL_ID
        annotations_text[has_id] = [
            "{}[{}]".format(*row)
            for row in self._annotations[has_id][
                ["label", "annotation_id"]
            ].values
        ]
        return annotations_text.groupby(
            self._annotations["token_idx"]
        ).aggregate("|".join)

    def _get_token_lines(self):
        tokens = self._tokens.copy()
        if self.convert_utf16_indices:
            tokens["start_char"] = self._char_indices.unicode_to_utf16[
                tokens["start_char"].values
            ]
            tokens["end_char"] = self._char_indices.unicode_to_utf16[
                tokens["end_char"].values
            ]
        token_text = pd.Series(
            [
                "{}-{}\t{}-{}\t{}".format(*row)
                for row in tokens.loc[
                    :,
                    [
                        "sentence_idx",
                        "token_idx_in_sentence",
                        "start_char",
                        "end_char",
                        "token",
                    ],
                ].values
            ],
            index=self._tokens.index,
        )
        annotations_text = self._get_annotations_lines()
        text = token_text.str.cat(
            annotations_text, join="left", na_rep="_", sep="\t"
        )
        return text

    def write(self, output_file: pathlib.Path) -> None:
        token_lines = self._get_token_lines()
        with open(output_file, "w", encoding="UTF-8") as stream:
            stream.write(self._doc_header)
            for sentence_wrapper, (_, sentence_tokens) in zip(
                self._sentence_wrappers,
                token_lines.groupby(self._tokens["sentence_idx"]),
            ):
                head, tail = sentence_wrapper
                stream.write(head)
                stream.write("\n".join(sentence_tokens.values))
                stream.write("\n")
                stream.write(tail)

    def set_annotations(
        self, annotations: Sequence[Mapping[str, Any]]
    ) -> None:
        annotations_df = pd.DataFrame(annotations)
        anno_token = []
        for anno_idx, anno_row in annotations_df.iterrows():
            overlapping_tokens = self._tokens["token_idx"][
                (anno_row["start_char"] < self._tokens["end_char"])
                & (self._tokens["start_char"] < anno_row["end_char"])
            ].values
            assert len(overlapping_tokens)
            anno_token.extend(
                (anno_idx, token_idx) for token_idx in overlapping_tokens
            )
        anno_token_df = pd.DataFrame(
            anno_token, columns=["annotation_idx", "token_idx"]
        )
        token_counts = anno_token_df.groupby("annotation_idx").count()
        annotations_needing_id = set(
            token_counts[token_counts["token_idx"] > 1].index.values
        )
        annotation_counts = anno_token_df.groupby("token_idx").count()
        multi_anno_tokens = annotation_counts[
            annotation_counts["annotation_idx"] > 1
        ].index
        annotations_needing_id.update(
            anno_token_df[anno_token_df["token_idx"].isin(multi_anno_tokens)][
                "annotation_idx"
            ].values
        )
        annotations_df["annotation_id"] = -1
        annotations_df.loc[
            sorted(annotations_needing_id), "annotation_id"
        ] = range(1, len(annotations_needing_id) + 1)
        anno_token_df = anno_token_df.join(annotations_df, on="annotation_idx")
        anno_token_df.rename(columns={"label_name": "label"}, inplace=True)
        self._annotations = anno_token_df.loc[:, self._ANNOTATIONS_COLUMNS]

    def get_annotations(self) -> List[Dict[str, Any]]:
        result = []
        detailed_annotations = pd.merge(
            self._annotations,
            self._tokens,
            left_on="token_idx",
            right_on="token_idx",
        )
        has_id = detailed_annotations["annotation_id"] != self._NULL_ID
        for _, anno in detailed_annotations[~has_id].iterrows():
            result.append(
                {
                    "start_char": int(anno["start_char"]),
                    "end_char": int(anno["end_char"]),
                    "label_name": anno["label"],
                }
            )
        for _, anno_group in detailed_annotations[has_id].groupby(
            "annotation_id"
        ):
            start_char = anno_group["start_char"].min()
            end_char = anno_group["end_char"].max()
            result.append(
                {
                    "start_char": int(start_char),
                    "end_char": int(end_char),
                    "label_name": anno_group["label"].values[0],
                }
            )
        return result


def _load_inception_doc(doc: InceptionDocPaths) -> Dict[str, Any]:
    text_file = pathlib.Path(doc.text_file)
    text = text_file.read_text("UTF-8")
    result = {
        "text": text,
        "metadata": {
            "txt_filename": text_file.name,
            "wtsv_filename": text_file.with_suffix(".wtsv").name,
            "filename": text_file.stem,
        },
    }
    if doc.annotations_file is not None:
        wtsv = _InceptionDoc(pathlib.Path(doc.annotations_file), text)
        result["annotations"] = wtsv.get_annotations()
    return result


class InceptionReader(_utils._BaseReader):
    _inception_docs: Sequence[InceptionDocPaths]

    def __init__(self, documents: Sequence[InceptionDocPaths]) -> None:
        self._inception_docs = documents

    def _do_read(self) -> Generator[Dict[str, Any], None, None]:
        for doc in self._inception_docs:
            yield _load_inception_doc(doc)


class InceptionDirReader(_utils._BaseReader):
    format_name = "inception"

    @staticmethod
    def edit_argument_parser(parser):
        parser.add_argument(
            "--in_txt_dir",
            type=str,
            help="Directory containing the raw text files.",
        )
        try:
            parser.add_argument(
                "--in_wtsv_dir",
                type=str,
                help="Directory containing the wtsv Inception "
                "tokenization or annotation files.",
            )
        except Exception:
            pass

    @classmethod
    def from_args(cls, args):
        assert args.in_txt_dir is not None
        assert args.in_wtsv_dir is not None
        return cls(args.in_txt_dir, args.in_wtsv_dir)

    def __init__(
        self, txt_dir: _utils.PathLikeOrStr, wtsv_dir: _utils.PathLikeOrStr
    ) -> None:
        self._txt_dir = pathlib.Path(txt_dir)
        self._wtsv_dir = pathlib.Path(wtsv_dir)

    def _do_read(self) -> Generator[Dict[str, Any], None, None]:
        for txt_file in sorted(self._txt_dir.glob("*.txt")):
            matching_wtsv = (self._wtsv_dir / txt_file.name).with_suffix(
                ".wtsv"
            )
            wtsv_file = matching_wtsv if matching_wtsv.is_file() else None
            yield _load_inception_doc(InceptionDocPaths(txt_file, wtsv_file))


class InceptionWriter:
    format_name = "inception"

    _wtsv_dir: pathlib.Path
    _output_dir: pathlib.Path
    _filename_pattern: str

    @staticmethod
    def edit_argument_parser(parser):
        parser.add_argument(
            "--out_inception_dir",
            type=str,
            help="Directory in which to write output "
            "Inception(WebAnno) documents and annotations.",
        )
        try:
            parser.add_argument(
                "--in_wtsv_dir",
                type=str,
                help="Directory containing the Inception tokenizations.",
            )
        except Exception:
            pass
        parser.add_argument(
            "--filename_pattern",
            type=str,
            default="{filename}",
            help="Pattern used to construct the filename for each document. "
            "It should not include any extension. Keys present in the "
            "documents’ metadata can be inserted between '{}' and will be "
            "interpolated.",
        )

    @classmethod
    def from_args(cls, args):
        assert args.in_wtsv_dir is not None
        assert args.out_inception_dir is not None
        return cls(
            args.in_wtsv_dir, args.out_inception_dir, args.filename_pattern
        )

    def __init__(
        self,
        wtsv_dir: _utils.PathLikeOrStr,
        output_dir: _utils.PathLikeOrStr,
        filename_pattern: str,
    ) -> None:
        self._wtsv_dir = pathlib.Path(wtsv_dir)
        self._output_dir = pathlib.Path(output_dir)
        self._filename_pattern = filename_pattern

    def __enter__(self) -> InceptionWriter:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        del exc_type, exc_value, traceback

    def write(self, documents: Iterable[Mapping[str, Any]]) -> None:
        out_wtsv_dir = self._output_dir / "wtsv"
        out_txt_dir = self._output_dir / "txt"
        for out_dir in out_wtsv_dir, out_txt_dir:
            out_dir.mkdir(exist_ok=True, parents=True)

        for doc in documents:
            stem = self._filename_pattern.format(**doc["metadata"])
            wtsv_file = (self._wtsv_dir / stem).with_suffix(".wtsv")

            output_wtsv = (out_wtsv_dir / stem).with_suffix(".wtsv")
            wtsv = _InceptionDoc(wtsv_file, doc["text"])
            wtsv.set_annotations(doc["annotations"])
            wtsv.write(output_wtsv)

            output_txt = (out_txt_dir / stem).with_suffix(".txt")
            output_txt.write_text(doc["text"], encoding="utf-8")
