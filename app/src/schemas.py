"""Request and response schemas. Validation happens here, once, at the API boundary."""

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str


class AskIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class AskOut(BaseModel):
    answer: str
