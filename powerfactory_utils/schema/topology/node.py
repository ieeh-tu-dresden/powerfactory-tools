# -*- coding: utf-8 -*-

from powerfactory_utils.schema.base import Base


class Node(Base):
    name: str
    u_n: float
    description: str | None = None
