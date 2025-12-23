from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    status: int = Field(200)
    message: str = Field("Success")
    data: Optional[T] = Field(None)
