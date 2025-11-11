import typing as t
from contextlib import nullcontext as does_not_raise

import pandas as pd
import polars as pl
import pytest
from polars.testing import assert_frame_equal as pl_assert_frame_equal

from powerfactory_tools.utils.io import FileType
from powerfactory_tools.utils.io import PandasIoHandler
from powerfactory_tools.utils.io import PolarsIoHandler

# Test data for export and import tests
test_dict1 = {
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "city": ["New York", "Los Angeles"],
}
test_pd_df1 = pd.DataFrame(
    {
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "city": ["New York", "Los Angeles", None],  # Fill missing value with None
    },
)
test_pl_df1 = pl.from_pandas(test_pd_df1)

test_dict2 = {
    "name": "Alice",
    "age": 25,
    "city": ["New York", "Los Angeles"],  # List as a single cell
}
test_pd_df2 = pd.DataFrame.from_dict(test_dict2)
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


def sort_nested_dict(d):
    """Recursively sorts all dictionary keys at every level.

    Leaves lists and other types unchanged, except that if a list contains dicts, those dicts are sorted too.
    """
    if isinstance(d, dict):
        return {k: sort_nested_dict(d[k]) for k in sorted(d)}
    if isinstance(d, list):
        return [sort_nested_dict(item) for item in d]
    return d


@pytest.fixture
def fake_path(tmp_path):
    return tmp_path


class TestExportImportDataPandas:
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
            (test_dict1, FileType.CSV, does_not_raise()),
            (test_dict1, FileType.JSON, does_not_raise()),
            (test_dict1, FileType.FEATHER, does_not_raise()),
            (test_dict2, FileType.CSV, does_not_raise()),
            (test_dict2, FileType.JSON, does_not_raise()),
            (test_dict2, FileType.FEATHER, does_not_raise()),
            (test_dict3, FileType.CSV, does_not_raise()),
            (test_dict3, FileType.JSON, does_not_raise()),
            (test_dict3, FileType.FEATHER, does_not_raise()),
            (test_pl_df1, FileType.CSV, does_not_raise()),
            (test_pl_df1, FileType.JSON, does_not_raise()),
            (test_pl_df1, FileType.FEATHER, does_not_raise()),
            (test_pl_df2, FileType.CSV, does_not_raise()),
            (test_pl_df2, FileType.JSON, does_not_raise()),
            (test_pl_df2, FileType.FEATHER, does_not_raise()),
            # (test_nested_dict1, FileType.CSV, does_not_raise()),  # not natively supported by Polars, as nested dict must be serialized manually before  # noqa: ERA001
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
            ioh = PolarsIoHandler()
            ioh.export_user_data(data, export_root_path=fake_path, file_type=file_type, file_name=file_name)

            # Import data from file
            file_name = f"{file_name}{file_type.value}"
            full_file_path = fake_path / file_name
            imported_dataframe = ioh.import_user_data(full_file_path)
            if imported_dataframe is None:
                pytest.fail("Import returned None, expected a DataFrame.")

            if isinstance(data, dict):
                if file_type == FileType.JSON:
                    data = t.cast("dict", sort_nested_dict(data))
                origin_dataframe = ioh.convert_dict_to_dataframe(data)
                pl_assert_frame_equal(origin_dataframe, imported_dataframe, check_column_order=False)
            else:
                pl_assert_frame_equal(data, imported_dataframe, check_column_order=False)
