# from pydantic import BaseModel, HttpUrl
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class YouTubeURL(BaseModel):
    url: HttpUrl

class FileName(BaseModel):
    fileName: str


# class TranscriptionResult(BaseModel):
#     cleaned_full_text: str
#     timestamped_groups: List[str]

class ProcessingResultSchema(BaseModel):
    transcription: Optional[str] = None
    summary: Optional[str] = None
    quiz: Optional[List[dict]] = None
    
    class Config:
        from_attributes = True

class VideoHistory(BaseModel):
    id: int
    title: str
    storage_path: str
    result: Optional[ProcessingResultSchema] = None

    class Config:
        from_attributes = True