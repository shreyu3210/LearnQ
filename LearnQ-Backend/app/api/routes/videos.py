from fastapi import APIRouter, status, UploadFile, File, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from app.services import triton_service, transcription_service, ytdlp_service, auth_service, video_service, frame_service
from app.services.transcription_service import clean_transcript_with_gemini,final_res_extraction
from app.schemas import user as user_schema,video as video_schema
from app.schemas.video import YouTubeURL,FileName
from fastapi.concurrency import run_in_threadpool
import concurrent.futures
import asyncio
from sqlalchemy.orm import Session
from app.db import database
from typing import List, Optional
from app.schemas.response import ResponseModel
import shutil
import os
import uuid 
import mimetypes
import glob


router = APIRouter()
UPLOAD_DIRECTORY = "./uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


@router.get("/test-models", tags=["Tests"])
def test_triton_models():
    """
    An endpoint to check the status of all models on the Triton server.
    """
    # print("Testing")
    status = triton_service.check_triton_server_status()
    if status['status'] == "error":
        
            return {
        "status": "error",
        "data": {"model_statuses": status}
    }
    return {
        "status": "success",
        "data": {"model_statuses": status}
    }

@router.post("/transcribe", tags=["Transcription"])
async def transcribe_video(
    file: FileName,
    current_user: user_schema.User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Processes video: extracts frames and transcribes audio in parallel,
    then sends both to Gemini for summary and quiz generation.
    """
    file_path_to_process = None
    status = triton_service.check_triton_server_status()
    print("Testing Server status...")
    if status['status'] == "error":
        
            return {
        "status": "error",
        "data": {"model_statuses": status}
    }
    print("Server online..")
    # Step 1: Locate the video file
    exact_path = os.path.join(UPLOAD_DIRECTORY, file.fileName)
    if os.path.exists(exact_path):
        file_path_to_process = exact_path
    else:
        search_pattern = os.path.join(UPLOAD_DIRECTORY, f"{file.fileName}.*")
        files_found = glob.glob(search_pattern)

        if not files_found:
            raise HTTPException(
                status_code=404,
                detail=f"No file found for ID '{file.fileName}'"
            )
        if len(files_found) > 1:
            raise HTTPException(
                status_code=500,
                detail=f"Multiple files found for ID '{file.fileName}'. Ambiguous request."
            )
        
        file_path_to_process = files_found[0]

    

    # Step 2: Create video record in database
    
   
    try:
        # Step 3: Run transcription and frame extraction in parallel
        print("🚀 Starting parallel processing: Transcription + Frame Extraction")
        
        loop = asyncio.get_event_loop()
        
        # Create tasks for parallel execution
        transcription_task = loop.run_in_executor(
            None,
            transcription_service.process_audio_and_transcribe,
            file_path_to_process,
            True,  # include_timestamps
            30,    # window_size
            False  # clean_with_gemini - we'll do this later with frames
        )
        
        frame_extraction_task = loop.run_in_executor(
            None,
            frame_service.extract_and_select_good_frames,
            file_path_to_process
        )
        
        # Wait for both tasks to complete
        transcription, best_frames_base64 = await asyncio.gather(
            transcription_task,
            frame_extraction_task
        )
        
        # print("✅ Parallel processing completed")
        # print(f"📝 Transcription length: {len(transcription)} chars")
        # print(f"🖼️  Extracted frames: {len(best_frames_base64)}")

        # Step 4: Check for transcription errors
        if isinstance(transcription, dict) and "error" in transcription:
            return {
                "status": "error",
                "message": "Transcription process failed",
                "data": transcription
            }

        # Step 5: Process with Gemini (transcript + frames)
        # print("🤖 Processing with Gemini (transcript + frames)...")
        cleaned_text_gemini = await loop.run_in_executor(
            None,
            transcription_service.clean_transcript_with_gemini,
            transcription,
            best_frames_base64
        )
        
        # Step 6: Extract final results (summary + quiz)
        final_res = transcription_service.final_res_extraction(
            cleaned_text_gemini,
            transcription
        )
        video_record = video_service.create_video_record(
        db=db,
        title=final_res.get("title"),
        storage_path=file_path_to_process,
        user_id=current_user.id
    )

        # Step 7: Save results to database
        # print("💾 Saving results to database...")
        video_service.save_processing_results(
            db=db,
            video_id=video_record.id,
            transcription_data=final_res
        )
        
        print("✅ Processing pipeline completed successfully")
        # 
        return {
            "status": "success",
            "message": "Video processing completed",
            "data": {
                "video_id": video_record.id,
                "summary": final_res.get("summary", ""),
                "latex_quiz": final_res.get("latex_quiz", []),
                "timestamp": final_res.get("timestamp", "")
            
                
            }
        }
        
    except Exception as e:
        # print(f"❌ Error during video processing: {str(e)}")
        import traceback
        # print(traceback.format_exc())
        
        # Optionally delete the video record if processing failed
        # db.delete(video_record)
        # db.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Video processing failed: {str(e)}"
        )

@router.post("/upload", tags=["Video"])
async def upload_video(video: UploadFile = File(...),current_user: user_schema.User = Depends(auth_service.get_current_user)):
    """
    Accepts a video file, saves it to the server with a unique ID,
    and returns the new filename.
    """
    try:
        if video.filename:
            # 1. Get the file extension from the original filename
            file_extension = os.path.splitext(video.filename)[1]
            if file_extension.lower() not in ['.mp4','.webm','.mkv','.avi','.mp3','.wav','.m4a','.ogg']:
                raise HTTPException(422,detail='Invalid File Format')
            # 2. Generate a unique ID and combine it with the extension
            unique_filename = f"{str(uuid.uuid4())}{file_extension}"
            
            # 3. Create the full path to save the file
            file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
            
            # 4. Save the uploaded file to the 'uploads' directory
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
            # print(unique_filename)
            # 5. Return the NEW unique filename in the response
            return {
                "status": "success",
                "message": "File uploaded successfully",
                "data": {"video_id": unique_filename}
            }
        else:
            raise HTTPException(400,detail='No file')
    except HTTPException as e:
# Re-raise the HTTPException to let FastAPI handle it correctly
        raise e
    except Exception as e:
        # If any error occurs during the process, raise an HTTPException
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during file upload: {e}"
        )



@router.post("/transcribe-youtube", tags=["Video"])
async def transcribe_youtube_video(request_data: YouTubeURL,current_user: user_schema.User = Depends(auth_service.get_current_user)):
    """
    Downloads a video from a YouTube URL, transcribes it using Triton,
    and returns the resulting text.
    """

    youtube_url = str(request_data.url)
    video_id = str(uuid.uuid4())
    # 1. Download the video from YouTube
    downloaded_file_path = await run_in_threadpool(
        ytdlp_service.download_youtube_video, url=youtube_url, video_id=video_id
    )
    
    

    # print("video name",video_id)
    if downloaded_file_path:
        return {
            "status": "success",
            "message": "YouTube video Downloaded successfully",
            "data": {"video_id": video_id +'.mp4', "youtube_url": youtube_url}
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error in YouTube download service"
        )
       

@router.get("/me/history", response_model=ResponseModel[List[video_schema.VideoHistory]], tags=["Video"])
def get_user_history(current_user: user_schema.User = Depends(auth_service.get_current_user), db: Session = Depends(database.get_db)):
    """
    Retrieves a list of all videos and their processed results for the
    current user, sorted by the latest first.
    """
    try:
        # This is the correct and secure way to get the user's ID
        history = video_service.get_user_history(db=db, user_id=current_user.id)
        
        # This is a successful response, even if the history list is empty
        return {
            "status": "success",
            "message": "User history retrieved successfully",
            "data": history
        }
    except Exception as e:
        # This will catch any unexpected database errors
        print(f"❌ Error retrieving user history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user history due to a server error."
        )


@router.get("/video/{filename}", tags=["Video"])
async def stream_video(filename: str, range: Optional[str] = Header(None)):
    """
    Streams a video file from the uploads directory.
    Supports HTTP Range requests for seeking in the browser video player.
    """
    # Try exact match first
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    
    if not os.path.exists(file_path):
        # Try finding file with glob pattern (in case extension differs)
        search_pattern = os.path.join(UPLOAD_DIRECTORY, f"{filename}.*")
        files_found = glob.glob(search_pattern)
        if files_found:
            file_path = files_found[0]
        else:
            raise HTTPException(status_code=404, detail="Video file not found")
    
    file_size = os.path.getsize(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "video/mp4"
    
    # If no Range header, return the full file
    if range is None:
        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
        
        return StreamingResponse(
            iter_file(),
            media_type=content_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            }
        )
    
    # Parse Range header (e.g., "bytes=0-1023")
    try:
        range_str = range.replace("bytes=", "")
        range_parts = range_str.split("-")
        start = int(range_parts[0])
        end = int(range_parts[1]) if range_parts[1] else file_size - 1
    except (ValueError, IndexError):
        start = 0
        end = file_size - 1
    
    # Clamp end to file size
    end = min(end, file_size - 1)
    content_length = end - start + 1
    
    def iter_range():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    return StreamingResponse(
        iter_range(),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
        }
    )
