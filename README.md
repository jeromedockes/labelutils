# labelutils

Python scripts to perform conversions between [labelbuddy](https://jeromedockes.github.io/labelbuddy)’s and other annotation tools’ file formats.

## Installation

Can be installed from PyPI with 

```
pip install labelutils
```

But as this is WIP, it might be better at the moment to install from the Git repository to get a more up-to-date version:

```
pip install "git+https://github.com/jeromedockes/labelutils.git"
```

## Usage

After installing we can use the command `labelutils_convert`:

### inception → labelbuddy format

```
labelutils_convert --from inception  --to labelbuddy --in_txt_dir /path/to/txt_dir --in_wtsv_dir /path/to/wtsv_dir --out_jsonl docs.jsonl
```

Where:

- `/path/to/txt_dir` is a directory containing `.txt` files that have been imported into Inception, ie the contents of the documents.
- `path/to/wtsv_dir` is a directory containing the `.wtsv` WebAnno files exported from Inception, whose names must match those of the `.txt` files except for the extension.


### labelbuddy → inception format

```
labelutils_convert --from labelbuddy --to inception --in_jsonl docs.jsonl --in_wtsv_dir  /path/to/wtsv_dir --out_inception_dir inception_docs
```

Where:

- `docs.jsonl` contains documents & annotations in labelbuddy format.
- `/path/to/wtsv_dir` is a directory containing `.wtsv` WebAnno files exported from Inception. If it contains any annotations, they are ignored, but this file is still needed to get Inception's tokenization of the documents.
- output will be stored in `inception_docs`
