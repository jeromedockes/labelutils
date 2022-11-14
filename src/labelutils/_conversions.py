import argparse

from labelutils import _inception, _labelbuddy


def convert_docs(docs_reader, docs_writer):
    with docs_reader:
        with docs_writer:
            docs_writer.write(docs_reader.read())


def convert_command(args=None):
    all_readers = {
        cls.format_name: cls
        for cls in [
            _labelbuddy.LabelBuddyReader,
            _inception.InceptionDirReader,
        ]
    }
    all_writers = {
        cls.format_name: cls
        for cls in [_labelbuddy.LabelBuddyWriter, _inception.InceptionWriter]
    }
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from", required=True, choices=sorted(all_readers.keys())
    )
    parser.add_argument(
        "--to", required=True, choices=sorted(all_writers.keys())
    )
    for reader in all_readers.values():
        reader.edit_argument_parser(parser)
    for writer in all_writers.values():
        writer.edit_argument_parser(parser)
    args = parser.parse_args(args)
    selected_reader = all_readers[getattr(args, "from")].from_args(args)
    selected_writer = all_writers[args.to].from_args(args)
    convert_docs(selected_reader, selected_writer)
