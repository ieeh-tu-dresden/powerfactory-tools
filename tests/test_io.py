from contextlib import nullcontext as does_not_raise

import pandas as pd
import polars as pl
import json
import pytest

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import PandasIoHandler
from powerfactory_tools.utils.io import PolarsIoHandler

test_dict1 = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles", "nn"],
}
test_pd_df1 = pd.DataFrame(
    {
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "city": ["New York", "Los Angeles", None],  # Fill missing value with None/NaN
    },
)
test_pl_df1 = pl.from_pandas(test_pd_df1)

test_dict2 = {
    "name": "Alice",
    "age": 25,
    "city": ["New York", "Los Angeles"],
}
test_pd_df2 = pd.DataFrame(
    {
        "name": ["Alice"],
        "age": [25],
        "city": [["New York", "Los Angeles"]],  # List as a single cell
    },
)
test_pl_df2 = pl.from_pandas(test_pd_df2)

test_dict3 = {
    "name": "Alice",
    "age": 25,
    "city": "New York",
}

test_nested_dict1 = {
    "key_name": {
        "Uabs1": {
            "value": 2.3,
            "unit": "kV",
        },
    },
    "key_name2": {
        "Uabs1": {
            "value": 30.3,
            "unit": "kV",
        },
    },
}


@pytest.fixture
def fake_path(tmp_path):
    return tmp_path


class TestExportImportDataPandas1:
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
            (test_pd_df1, FileType.CSV, does_not_raise()),
            (test_pd_df1, FileType.JSON, does_not_raise()),
            (test_pd_df1, FileType.FEATHER, does_not_raise()),
            (test_pd_df2, FileType.CSV, does_not_raise()),
            (test_pd_df2, FileType.JSON, does_not_raise()),
            (test_pd_df2, FileType.FEATHER, does_not_raise()),
            (test_nested_dict1, FileType.CSV, does_not_raise()),
            (test_nested_dict1, FileType.JSON, does_not_raise()),
            (test_nested_dict1, FileType.FEATHER, does_not_raise()),
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
            # Export data to file
            ioh = PandasIoHandler()
            ioh.export_user_data(data, export_root_path=fake_path, file_type=file_type, file_name=file_name)

            # Import data from file
            file_name = f"{file_name}{file_type.value}"
            full_file_path = fake_path / file_name
            imported_dataframe = ioh.import_user_data(full_file_path)
            if imported_dataframe is None:
                pytest.fail("Import returned None, expected a DataFrame.")
            # Fix columns that may contain lists as strings (necessary for test_df2 and .CSV)
            ioh.convert_str_lists_to_lists(imported_dataframe)
            # Fix columns that may contain dicts as strings (necessary for test_nested_dict1 and .CSV)
            ioh.convert_str_dicts_to_dicts(imported_dataframe)

            if isinstance(data, dict):
                imported_dict = ioh.convert_dataframe_to_dict(imported_dataframe)
                assert data == imported_dict

                origin_dataframe = ioh.convert_dict_to_dataframe(data)
                pd.testing.assert_frame_equal(origin_dataframe, imported_dataframe)
            else:
                pd.testing.assert_frame_equal(data, imported_dataframe)


class TestExportImportDataPolars:
    @pytest.mark.parametrize(
        ("data", "file_type", "expectation"),
        [
            # (test_dict1, FileType.CSV, does_not_raise()),
            (test_dict1, FileType.JSON, does_not_raise()),
            (test_dict1, FileType.FEATHER, does_not_raise()),
            # (test_dict2, FileType.CSV, does_not_raise()),
            # (test_dict2, FileType.JSON, does_not_raise()),
            # (test_dict2, FileType.FEATHER, does_not_raise()),
            # (test_dict3, FileType.CSV, does_not_raise()),
            # (test_dict3, FileType.JSON, does_not_raise()),
            # (test_dict3, FileType.FEATHER, does_not_raise()),
            # (test_pl_df1, FileType.CSV, does_not_raise()),
            # (test_pl_df1, FileType.JSON, does_not_raise()),
            # (test_pl_df1, FileType.FEATHER, does_not_raise()),
            # (test_pl_df2, FileType.CSV, does_not_raise()),
            # (test_pl_df2, FileType.JSON, does_not_raise()),
            # (test_pl_df2, FileType.FEATHER, does_not_raise()),
            # (test_nested_dict1, FileType.CSV, does_not_raise()),
            # (test_nested_dict1, FileType.JSON, does_not_raise()),
            # (test_nested_dict1, FileType.FEATHER, does_not_raise()),
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
            # Export data to file
            ioh = PolarsIoHandler()
            ioh.export_user_data(data, export_root_path=fake_path, file_type=file_type, file_name=file_name)

            # Import data from file
            file_name = f"{file_name}{file_type.value}"
            full_file_path = fake_path / file_name
            imported_dataframe = ioh.import_user_data(full_file_path)
            if imported_dataframe is None:
                pytest.fail("Import returned None, expected a DataFrame.")

            if isinstance(data, dict):
                imported_dict = imported_dataframe.to_dict(
                    as_series=False
                )  # TODO not working as nulls are not droped the same way in Polars
                if file_type == FileType.JSON:
                    assert json.dumps(data, sort_keys=True) == json.dumps(imported_dict, sort_keys=True)
                else:
                    assert data == imported_dict

                origin_dataframe = ioh.convert_dict_to_dataframe(data)
                pl.testing.assert_frame_equal(origin_dataframe, imported_dataframe)
            else:
                pl.testing.assert_frame_equal(data, imported_dataframe)
