from contextlib import nullcontext as does_not_raise

import pytest

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import ImportHandler
from powerfactory_tools.versions.pf2024.utils.io import ExportHandler

test_data = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles"],
}

test_data2 = {
    "name": "Alice",
    "age": 25,
    "city": ["New York", "Los Angeles"],
}

test_data3 = {
    "name": "Alice",
    "age": 25,
    "city": "New York",
}


@pytest.fixture
def fake_path(tmp_path):
    return tmp_path


class TestExportImportData:
    @pytest.mark.parametrize(
        ("data", "file_type", "expectation"),
        [
            (test_data, FileType.CSV, does_not_raise()),
            (test_data, FileType.JSON, does_not_raise()),
            (test_data, FileType.FEATHER, does_not_raise()),
            (test_data2, FileType.CSV, does_not_raise()),
            (test_data2, FileType.JSON, does_not_raise()),
            (test_data2, FileType.FEATHER, does_not_raise()),
            (test_data3, FileType.CSV, does_not_raise()),
            (test_data3, FileType.JSON, does_not_raise()),
            (test_data3, FileType.FEATHER, does_not_raise()),
        ],
    )
    def test_export_import_user_data(
        self,
        data,
        fake_path,
        file_type: FileType,
        expectation,
    ) -> None:
        file_name = "test_data"
        with expectation:
            eh = ExportHandler(directory_path=fake_path)
            # Export data to file
            eh.export_user_data(data, file_type=file_type, file_name=file_name)

            # Import data from file
            file_name = f"{file_name}{file_type.value}"
            full_file_path = fake_path / file_name
            ih = ImportHandler(file_path=full_file_path)
            imported_data = ih.import_user_data()
            assert data == imported_data
