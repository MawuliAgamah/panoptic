from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Union
from pydantic import field_validator


class TopicModel(BaseModel):
    """Metadata generated from text chunks"""
    topics: List[str] = Field(
        description="Main topics in the text, max 3",
        max_length=3
    )


class KeyWordModel(BaseModel):
    """Metadata generated from text chunks"""
    keywords: List[str] = Field(
        description="Key terms from the text, max 3",
        max_length=3
    )


