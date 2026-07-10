from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

# Create a generic TypeVar
T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None