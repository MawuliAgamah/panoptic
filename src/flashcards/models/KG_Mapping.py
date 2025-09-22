from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any


@dataclass
class KG_Mapping:
    id: str
    card_id: str
    user_id: str
    nodes: list[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KG_Mapping':
        """Create KG_Mapping instance from dictionary"""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert KG_Mapping instance to dictionary"""
        return asdict(self)

    