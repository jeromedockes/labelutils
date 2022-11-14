import json

import pytest

from labelutils import _conversions


def test_inception_char_offsets_correction(tmp_path):
    wtsv = """#someheader

#Text=aéo𝄞x.
1-1	0-6	aéo𝄞x	mylabel
1-2	6-7	.	_
"""
    (tmp_path / "doc.txt").write_text("aéo𝄞x.", "utf-8")
    (tmp_path / "doc.wtsv").write_text(wtsv, "utf8")
    jsonl = tmp_path / "doc.jsonl"
    _conversions.convert_command(
        [
            "--from",
            "inception",
            "--to",
            "labelbuddy",
            "--in_wtsv_dir",
            str(tmp_path),
            "--in_txt_dir",
            (str(tmp_path)),
            "--out_jsonl",
            str(jsonl),
        ]
    )
    doc = json.loads(jsonl.read_text("utf-8"))
    assert doc["annotations"][0]["end_char"] == 5

    out = tmp_path / "out"
    _conversions.convert_command(
        [
            "--from",
            "labelbuddy",
            "--to",
            "inception",
            "--in_wtsv_dir",
            str(tmp_path),
            "--in_jsonl",
            str(jsonl),
            "--out_inception_dir",
            str(out)
        ]
    )
    converted_back = (out / "wtsv" / "doc.wtsv").read_text("utf-8")
    assert converted_back == wtsv




def test_inception_pmc_round_trip(test_data_dir, tmp_path):
    pmc_dir = test_data_dir / "inception" / "pmc"
    wtsv_dir = pmc_dir / "wtsv"
    txt_dir = pmc_dir / "txt"
    jsonl = tmp_path / "docs.jsonl"
    _conversions.convert_command(
        [
            "--from",
            "inception",
            "--to",
            "labelbuddy",
            "--in_wtsv_dir",
            str(wtsv_dir),
            "--in_txt_dir",
            (str(txt_dir)),
            "--out_jsonl",
            str(jsonl),
        ]
    )

    out_dir = tmp_path / "inception"
    _conversions.convert_command(
        [
            "--from",
            "labelbuddy",
            "--to",
            "inception",
            "--in_wtsv_dir",
            str(wtsv_dir),
            "--in_jsonl",
            str(jsonl),
            "--out_inception_dir",
            str(out_dir),
        ]
    )
    for anno_file in wtsv_dir.glob("*.wtsv"):
        in_text = anno_file.read_text("utf-8")
        out_text = (out_dir / "wtsv" / anno_file.name).read_text("utf-8")
        assert in_text == out_text
