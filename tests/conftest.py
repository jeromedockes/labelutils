import pathlib

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    return pathlib.Path(__file__).with_name("data")
