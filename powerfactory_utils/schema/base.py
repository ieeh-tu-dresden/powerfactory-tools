# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime
import pathlib
import uuid
from enum import Enum

from pydantic import BaseModel
from pydantic import Field

VERSION = "1.1.0"


class VoltageSystemType(Enum):
    AC = "AC"
    DC = "DC"


class Base(BaseModel):
    @classmethod
    def from_file(cls, file_path: str | pathlib.Path) -> Base:
        return cls.parse_file(file_path)

    def to_json(self, file_path: str | pathlib.Path, indent: int = 2) -> None:
        file_path = pathlib.Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w+", encoding="utf-8") as file_handle:
            file_handle.write(self.json(indent=indent))

    @classmethod
    def from_json(cls, json_str: str) -> Base:
        return cls.parse_raw(json_str)


class Meta(Base):
    version = VERSION
    name: str
    date: datetime.date  # date of export
    id: uuid.UUID = Field(default_factory=uuid.uuid4)  # noqa: A003, VNE003
    project: str | None = None  # project the export is related to

    class Config:
        frozen = True
