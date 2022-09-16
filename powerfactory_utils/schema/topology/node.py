from typing import Optional

from powerfactory_utils.schema.base import Base


class Node(Base):
    name: str
    u_n: float
    description: Optional[str] = None
