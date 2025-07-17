from contextlib import nullcontext as does_not_raise

import pandas as pd
import pytest

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import ImportHandler
from powerfactory_tools.utils.io import convert_dataframe_to_dict
from powerfactory_tools.utils.io import convert_dict_to_dataframe
from powerfactory_tools.utils.io import convert_str_lists_to_lists
from powerfactory_tools.versions.pf2024.utils.io import ExportHandler

test_dict1 = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles"],
}
test_df1 = pd.DataFrame(
    {
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "city": ["New York", "Los Angeles", None],  # Fill missing value with None/NaN
    },
)

test_dict2 = {
    "name": "Alice",
    "age": 25,
    "city": ["New York", "Los Angeles"],
}
test_df2 = pd.DataFrame(
    {
        "name": ["Alice"],
        "age": [25],
        "city": [["New York", "Los Angeles"]],  # List as a single cell
    },
)

test_dict3 = {
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
            (test_dict1, FileType.CSV, does_not_raise()),
            (test_dict1, FileType.JSON, does_not_raise()),
            (test_dict1, FileType.FEATHER, does_not_raise()),
            (test_dict2, FileType.CSV, does_not_raise()),
            (test_dict2, FileType.JSON, does_not_raise()),
            (test_dict2, FileType.FEATHER, does_not_raise()),
            (test_dict3, FileType.CSV, does_not_raise()),
            (test_dict3, FileType.JSON, does_not_raise()),
            (test_dict3, FileType.FEATHER, does_not_raise()),
            (test_df1, FileType.CSV, does_not_raise()),
            (test_df1, FileType.JSON, does_not_raise()),
            (test_df1, FileType.FEATHER, does_not_raise()),
            (test_df2, FileType.CSV, does_not_raise()),
            (test_df2, FileType.JSON, does_not_raise()),
            (test_df2, FileType.FEATHER, does_not_raise()),
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
            imported_dataframe = ih.import_user_data()
            if imported_dataframe is None:
                pytest.fail("Import returned None, expected a DataFrame.")
            # Fix columns that may contain lists as strings (necessary for test_df2 and .CSV)
            convert_str_lists_to_lists(imported_dataframe, ["city"])

            if isinstance(data, dict):
                imported_dict = convert_dataframe_to_dict(imported_dataframe)
                assert data == imported_dict

                origin_dataframe = convert_dict_to_dataframe(data)
                pd.testing.assert_frame_equal(origin_dataframe, imported_dataframe)
            else:
                pd.testing.assert_frame_equal(data, imported_dataframe)

                origin_dataframe = convert_dict_to_dataframe(data)
                pd.testing.assert_frame_equal(origin_dataframe, imported_dataframe)
