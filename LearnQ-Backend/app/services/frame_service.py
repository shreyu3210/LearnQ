import cv2
import numpy as np
import base64
import time
import os
import torch
from torchvision import transforms
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ThreadPoolExecutor, as_completed
import tritonclient.http as httpclient
from typing import List, Tuple
import logging
from tqdm import tqdm

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# --- Configuration ---
SERVER_URL = "localhost:8000"
FRAME_CLASSIFIER_NAME = "frame_classifier"
TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])
CLASS_NAMES = ['bad_frames', 'good_frames']


def _extract_keyframes_for_chunk(args: Tuple) -> List[Tuple[float, np.ndarray]]:
    """Worker function to extract keyframes from a video segment using SSIM."""
    video_path, start_ms, end_ms, threshold, min_frame_interval = args
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return []

    cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)
    keyframes = []
    prev_frame_gray = None
    frame_number = 0
    last_keyframe_number = -min_frame_interval

    while True:
        current_pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if current_pos_ms >= end_ms: break
        ret, frame = cap.read()
        if not ret: break

        frame_number += 1
        current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame_gray is None:
            keyframes.append((current_pos_ms / 1000.0, frame))
            prev_frame_gray = current_frame_gray
            last_keyframe_number = frame_number
            continue

        if frame_number - last_keyframe_number >= min_frame_interval:
            score, _ = ssim(prev_frame_gray, current_frame_gray, full=True)
            if score < threshold:
                keyframes.append((current_pos_ms / 1000.0, frame))
                prev_frame_gray = current_frame_gray
                last_keyframe_number = frame_number
    
    cap.release()
    return keyframes


def _parallel_extract_keyframes(video_path: str) -> List[Tuple[float, np.ndarray]]:
    """Orchestrates parallel keyframe extraction."""
    logger.info("--- Step 1: Extracting Keyframes in Parallel ---")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Error: Could not open video.")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_ms = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps * 1000)
    cap.release()
    
    num_chunks = 8
    chunk_duration_ms = duration_ms / num_chunks
    tasks = [(video_path, i * chunk_duration_ms, (i + 1) * chunk_duration_ms, 0.88, 15) for i in range(num_chunks)]

    all_keyframes = []
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        futures = [executor.submit(_extract_keyframes_for_chunk, t) for t in tasks]
        
        # --- CHANGE 1: Replaced tqdm with logging ---
        completed_chunks = 0
        for future in as_completed(futures):
            all_keyframes.extend(future.result())
            completed_chunks += 1
            logger.info(f"🎞️  Keyframe extraction progress: {completed_chunks}/{num_chunks} chunks complete.")
            # -----------------------------------------------

    all_keyframes.sort(key=lambda x: x[0])
    logger.info(f"Found {len(all_keyframes)} total potential keyframes.")
    return all_keyframes


def _filter_frames_with_triton(keyframes: List[Tuple[float, np.ndarray]]) -> List[Tuple[float, np.ndarray]]:
    """Uses the Triton server to classify a batch of frames."""
    logger.info("--- Step 2: Filtering Frames with Triton Model ---")
    if not keyframes: return []

    good_frames = []
    client = httpclient.InferenceServerClient(url=SERVER_URL)
    
    batch_size = 32
    # --- CHANGE 2: Replaced tqdm with logging ---
    num_batches = (len(keyframes) + batch_size - 1) // batch_size
    for i in range(0, len(keyframes), batch_size):
        current_batch_num = (i // batch_size) + 1
        logger.info(f"🧠 Classifying frame batch {current_batch_num}/{num_batches}...")
        
        batch_keyframes = keyframes[i:i + batch_size]
        timestamps, frames = zip(*batch_keyframes)
        
        processed_frames = [TRANSFORM(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) for frame in frames]
        batch_tensor = torch.stack(processed_frames)

        input_tensor = httpclient.InferInput("input", batch_tensor.shape, "FP32")
        input_tensor.set_data_from_numpy(batch_tensor.numpy(), binary_data=True)

        response = client.infer(model_name=FRAME_CLASSIFIER_NAME, inputs=[input_tensor])
        predictions = response.as_numpy("output")
        pred_indices = np.argmax(predictions, axis=1)

        for j, pred_idx in enumerate(pred_indices):
            if CLASS_NAMES[pred_idx] == 'good_frames':
                good_frames.append(batch_keyframes[j])
    # -----------------------------------------------

    logger.info(f"Triton classified {len(good_frames)} frames as 'good'.")
    return good_frames


# You can add your original _deduplicate_frames function here if you need it
# ...

FRAMES_OUTPUT_DIRECTORY = './frames'
# --- MAIN PUBLIC FUNCTION ---
# This is the function your API will call.
def extract_and_select_good_frames(video_path: str) -> List[str]:
    """Runs the full pipeline and returns final frames as base64 strings."""
    start_time = time.time()
    
    # Step 1: Extract candidate keyframes
    keyframes = _parallel_extract_keyframes(video_path)
    if not keyframes: return []

    # Step 2: Filter with Triton
    good_frames = _filter_frames_with_triton(keyframes)
    
    final_frames_with_ts = good_frames # Using good_frames directly for now
    
    import shutil
    if os.path.exists(FRAMES_OUTPUT_DIRECTORY):
        shutil.rmtree(FRAMES_OUTPUT_DIRECTORY)
    os.makedirs(FRAMES_OUTPUT_DIRECTORY, exist_ok=True)
    
    for timestamp, frame in final_frames_with_ts:
        safe_timestamp = f"{timestamp:.2f}".replace('.', '_')
        filename = f"frame_{safe_timestamp}s.jpg"
        output_path = os.path.join(FRAMES_OUTPUT_DIRECTORY, filename)
        cv2.imwrite(output_path, frame)
        
    final_frames_base64 = []
    for _, frame in final_frames_with_ts[:5]:
        _, buffer = cv2.imencode('.jpg', frame)
        base64_string = base64.b64encode(buffer).decode('utf-8')
        final_frames_base64.append(base64_string)

    end_time = time.time()
    logger.info(f"\n✅ Frame processing pipeline finished in {end_time - start_time:.2f} seconds.")
    
    return final_frames_base64