from contextlib import nullcontext as does_not_raise

import pytest

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import export_user_data
from powerfactory_tools.utils.io import import_user_data

test_data = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles", "Chicago"],
}


@pytest.fixture()
def fake_path(tmp_path):
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
    def test_export_import_user_data(
        self,
        fake_path,
        file_type: FileType,
        expectation,
    ) -> None:
        file_name = "test_data"
        with expectation:
            # Export data to file
            export_user_data(data=test_data, export_path=fake_path, file_type=file_type, file_name=file_name)

            # Import data from file
            file_name = f"{file_name}{file_type.value}"
            full_file_path = fake_path / file_name
            imported_data = import_user_data(full_file_path, file_type)
            assert test_data == imported_data
