from sqlalchemy import Column, Integer, String, ForeignKey, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default='user')
    videos = relationship("Video", back_populates="owner")
    
class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    # In production, this would be the Azure Blob Storage URL/path
    storage_path = Column(String, nullable=False) 
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship to link back to the User
    owner = relationship("User", back_populates="videos")
    
    # One-to-one relationship to its processing results
    result = relationship("ProcessingResult", back_populates="video", uselist=False, cascade="all, delete-orphan")
    
    
class ProcessingResult(Base):
    __tablename__ = "processing_results"

    id = Column(Integer, primary_key=True, index=True)
    transcription = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    quiz = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Foreign key to link back to the Video
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, unique=True)
    
    # Relationship to link back to the Video
    video = relationship("Video", back_populates="result")