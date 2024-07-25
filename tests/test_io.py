import pathlib
from contextlib import nullcontext as does_not_raise

import pytest

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import export_data
from powerfactory_tools.utils.io import import_data

# Sample test data
test_data = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles", "Chicago"],
}


# Temporary directory fixture for storing test files
@pytest.fixture()
def temp_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


class TestExportImportData:
    @pytest.mark.parametrize(
        ("file_type", "expectation"),
        [
            (FileType.CSV, does_not_raise()),
            (FileType.JSON, does_not_raise()),
            (FileType.FEATHER, does_not_raise()),
        ],
    )
    def test_import_data(self, temp_dir: pathlib.Path, file_type: FileType, expectation) -> None:
        with expectation:
            # Export data to file
            export_data(data=test_data, export_path=temp_dir, file_type=file_type, file_name="test_data")

            # Import data from file
            file_name = f"{test_data}{file_type}"
            full_file_path = temp_dir / file_name
            imported_data = import_data(full_file_path, file_type)
            assert test_data == imported_data
