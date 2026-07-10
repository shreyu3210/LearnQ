from sqlalchemy.orm import Session
from app.db import models
from app.schemas import video as video_schema

def create_video_record(db: Session, title: str, storage_path: str, user_id: int):
    """
    Creates a new video record in the database for a user.
    """
    db_video = models.Video(title=title, storage_path=storage_path, owner_id=user_id)
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def save_processing_results(db: Session, video_id: int, transcription_data: dict):
    """
    Saves the transcription, summary, and quiz results to the database.
    """
    db_result = models.ProcessingResult(
        video_id=video_id,
        transcription=transcription_data.get("timestamp"),
        summary=transcription_data.get("summary"),
        quiz=transcription_data.get("latex_quiz")
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_user_history(db: Session, user_id: int):
    """
    Retrieves all videos and their results for a user, sorted by latest first.
    """
    # Only return videos where owner_id matches user_id
    return db.query(models.Video).filter(models.Video.owner_id == user_id).all()
    