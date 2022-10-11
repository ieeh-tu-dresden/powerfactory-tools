from __future__ import annotations

import datetime
import pathlib
import uuid
from enum import Enum
from typing import TYPE_CHECKING
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator

if TYPE_CHECKING:
    from typing import Any
    from typing import Union


class VoltageSystemType(Enum):
    AC = "AC"
    DC = "DC"


class Base(BaseModel):
    @classmethod
    def from_file(cls, path: Union[str, pathlib.Path]) -> "Base":
        return cls.parse_file(path)

    def to_json(self, path: Union[str, pathlib.Path], indent: int = 2) -> bool:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as f:
            f.write(self.json(indent=indent))
        return True

    @classmethod
    def from_json(cls, json_str: str) -> "Base":
        return cls.parse_raw(json_str)


class Meta(Base):
    name: str
    date: datetime.date  # date of export
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project: Optional[str] = None  # project the export is related to

    @root_validator
    def schema_version(cls, values: dict[str, Any]) -> dict[str, Any]:
        values["version"] = "1.0"
        return values
