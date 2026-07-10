# With frame extraction 

import whisper
from whisper.tokenizer import get_tokenizer
import librosa
import numpy as np
import tritonclient.http as httpclient
import torch
import google.generativeai as genai
from app.core.config import settings
import concurrent.futures
from typing import List, Dict, Union
import json
import time
import logging
import signal
from contextlib import contextmanager
import PIL.Image
import io
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = "localhost:8000"
WHISPER_ENCODER_NAME = "whisper_encoder"
WHISPER_DECODER_NAME = "whisper_decoder"

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')


class TimeoutException(Exception):
    pass


@contextmanager
def time_limit(seconds):
    """Context manager to enforce time limits on operations"""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Timed out after {seconds} seconds")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def clean_transcript_with_gemini(transcript: str, images_base64: List[str]) -> str:
    """
    Sends a raw transcript and frames to Gemini and returns a cleaned, polished version
    with summary and quiz.
    """
    logger.info("🤖 Processing transcript and frames with Gemini...")
    
    prompt: List[Union[str, PIL.Image.Image]] = [
        f"""
You are an expert content processor. Based on the given transcript and video frames, perform these tasks:

1. Summarize the transcript in a structured way with main topics as keys and relevant points as lists. 
   Remove any timestamps in the format [00:00:00 --> 00:00:30] before summarizing.
2. Generate a Quiz based on the content.
3. Output must be in the following **JSON format**:
4. Give a simple title for the topic in the transcript between 2-10 words

{{
    "title": "Title of transcript",
    "summary": "Summary text as a single string",
    "latex_quiz": [
        {{
            "question": "...",
            "choices": ["choice1", "choice2", "choice3", "choice4"],
            "answer": "...",
            "explanation": "..."
        }},
        ...
    ]
}}

### Rules for summary:
- Include basic styling of summary text using markdown compatible with react-markdown
- Use # for topic and ## for sub topic headings
- Use the video frames as additional context to enhance the summary

### Rules for quiz generation:
- Use transcript and visual context from frames.
- Do NOT add any prefatory or postfatory phrases such as "according to the transcript" or "as explained in the lecture" in the questions. Use "video" word instead of "transcript" if necessary.
- Questions must be clear, concise, and purely factual.
- Include MCQs covering almost all topics in the transcript. If the transcript is less than 2 minutes, create only 10 MCQs; otherwise, create 20 MCQs.
- Questions should be neutral and direct.
- Each question object must include:
    - "question": Question text
    - "choices": Array of exactly 4 choices
    - "answer": Correct choice as text
    - "explanation": Short explanation for the correct answer

Return ONLY the JSON object exactly as specified.

Transcript:
{transcript}

The following images are keyframes from the video that provide visual context
Specify like (from the video) in the mcq question if the question is created using frames provided :
        """,
    ]
    
    # Add images to the prompt
    for i, base64_string in enumerate(images_base64):
        try:
            image_bytes = base64.b64decode(base64_string)
            img = PIL.Image.open(io.BytesIO(image_bytes))
            prompt.append(img)
            logger.info(f"✅ Added image {i+1}/{len(images_base64)} to prompt")
        except Exception as e:
            logger.warning(f"⚠️ Could not process image {i+1}: {e}")

    try:
        response = gemini_model.generate_content(prompt)
        logger.info("✅ Gemini multi-modal processing successful")
        return response.text.strip()
    except Exception as e:
        logger.error(f"❌ Error during Gemini processing: {e}")
        return json.dumps({
            "summary": "Error during content generation.",
            "latex_quiz": []
        })


def _sanitize_gemini_json(raw: str) -> str:
    """
    Sanitize raw Gemini output to extract valid JSON.
    Handles markdown fences, trailing commas, and other common issues.
    """
    import re
    text = raw.strip()
    
    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    elif text.startswith("```"):
        text = text.lstrip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
        text = text.rstrip("`").strip()
    
    # Extract the outermost JSON object { ... }
    brace_start = text.find('{')
    if brace_start != -1:
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
        if brace_end != -1:
            text = text[brace_start:brace_end + 1]
    
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    return text


def final_res_extraction(response_text: str, timestamp: str) -> dict:
    """Extract and format the final results from Gemini response."""
    try:
        sanitized = _sanitize_gemini_json(response_text)
        parsed = json.loads(sanitized)
        
        title = parsed.get("title", "")
        summary = parsed.get("summary", "")
        if isinstance(summary, dict):
            pass  # Keep as-is
        elif isinstance(summary, str):
            summary = summary.strip()
        else:
            summary = ""

        latex_quiz = parsed.get("latex_quiz", [])

        return {
            "title": title,
            "summary": summary,
            "latex_quiz": latex_quiz,
            "timestamp": timestamp.strip()
        }
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decoding failed: {e}")
        logger.info("🔄 Attempting regex-based field extraction as fallback...")
        
        import re
        # Fallback: try to extract fields individually via regex
        title = ""
        summary = ""
        latex_quiz = []
        
        title_match = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
        if title_match:
            title = title_match.group(1)
        
        summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1)
        
        quiz_match = re.search(r'"latex_quiz"\s*:\s*(\[[\s\S]*\])', response_text)
        if quiz_match:
            try:
                quiz_text = quiz_match.group(1)
                # Remove trailing commas
                quiz_text = re.sub(r',\s*([}\]])', r'\1', quiz_text)
                latex_quiz = json.loads(quiz_text)
            except json.JSONDecodeError:
                logger.warning("⚠️ Could not parse quiz from fallback regex")
        
        return {
            "title": title,
            "summary": summary,
            "latex_quiz": latex_quiz,
            "timestamp": timestamp.strip()
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return {
            "title": "",
            "summary": "",
            "latex_quiz": [],
            "timestamp": timestamp.strip()
        }


def format_timestamp(seconds: float) -> str:
    """Convert seconds to hh:mm:ss format."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def create_segmented_timestamps(segments: List[Dict], window_size: int = 60) -> str:
    """
    Create timestamp-segmented transcript from segments.
    Groups text into time windows (default 60 seconds).
    """
    if not segments:
        return ""
    
    segments = sorted(segments, key=lambda x: x["chunk_index"])
    
    output_lines = []
    current_start = 0
    buffer_text = []
    
    for seg in segments:
        start, end, text = seg["start"], seg["end"], seg["text"].strip()
        
        # Clean special tokens from text
        text = text.replace("<|endoftext|>", "").replace(
            "<|startoftranscript|>", ""
        ).replace("<|transcribe|>", "").replace("<|notimestamps|>", "")
        
        if not text:
            continue
            
        buffer_text.append(text)
        
        # If segment passes window_size window, flush it
        if end - current_start >= window_size:
            combined_text = ' '.join(buffer_text)
            timestamp_line = f"[{format_timestamp(current_start)} --> {format_timestamp(end)}] {combined_text}\n\n"
            
            output_lines.append(timestamp_line)
            current_start = end
            buffer_text = []
    
    # Write remaining buffer if any
    if buffer_text:
        last_end = segments[-1]["end"]
        combined_text = ' '.join(buffer_text)
        timestamp_line = f"[{format_timestamp(current_start)} --> {format_timestamp(last_end)}] {combined_text}"
        output_lines.append(timestamp_line)
    
    return "\n".join(output_lines)


def transcribe_chunk_with_timing(
    spectrogram: np.ndarray,
    chunk_index: int,
    tokenizer,
    num_chunks: int,
    max_tokens: int = 180,
    decoder_timeout: int = 30
) -> Dict:
    """
    Uses Triton to transcribe a single 30-second audio chunk with improved error handling.
    """
    chunk_id = f"Chunk-{chunk_index}"
    logger.info(f"🎯 [{chunk_id}] Starting transcription...")
    
    try:
        # Connect to Triton Server
        connection_start = time.time()
        client = httpclient.InferenceServerClient(
            url=SERVER_URL,
            connection_timeout=10.0,
            network_timeout=decoder_timeout
        )
        logger.info(f"✅ [{chunk_id}] Connected in {time.time() - connection_start:.2f}s")

        # Encoder call
        logger.info(f"🔵 [{chunk_id}] Running encoder...")
        encoder_start = time.time()
        
        input_tensor_encoder = httpclient.InferInput("input_features", (1, 80, 3000), "FP32")
        input_tensor_encoder.set_data_from_numpy(spectrogram[np.newaxis, :], binary_data=True)
        
        response_encoder = client.infer(
            model_name=WHISPER_ENCODER_NAME,
            inputs=[input_tensor_encoder],
            timeout=int(30 * 1_000_000)
        )
        encoder_output = response_encoder.as_numpy("last_hidden_state")
        logger.info(f"✅ [{chunk_id}] Encoder completed in {time.time() - encoder_start:.2f}s")

        # Decoder loop
        logger.info(f"🔵 [{chunk_id}] Starting decoder loop (max {max_tokens} tokens)...")
        lang_token = tokenizer.to_language_token("en")
        tokens = np.array([[tokenizer.sot, lang_token, tokenizer.translate]], dtype=np.int64)
        
        input_tensor_encoder_hidden = httpclient.InferInput(
            "encoder_hidden_states",
            encoder_output.shape,
            "FP32"
        )
        input_tensor_encoder_hidden.set_data_from_numpy(encoder_output, binary_data=True)
        
        EOT = tokenizer.eos_token_id if hasattr(tokenizer, "eos_token_id") else tokenizer.eot
        
        decoder_start = time.time()
        tokens_generated = 0
        last_log_time = time.time()
        
        for iteration in range(max_tokens):
            current_time = time.time()
            if current_time - last_log_time > 5 or iteration % 50 == 0:
                logger.info(f"🔄 [{chunk_id}] Token {iteration}/{max_tokens} | Time: {current_time - decoder_start:.1f}s")
                last_log_time = current_time
            
            input_tensor_tokens = httpclient.InferInput("input_ids", tokens.shape, "INT64")
            input_tensor_tokens.set_data_from_numpy(tokens, binary_data=True)
            
            try:
                response_decoder = client.infer(
                    model_name=WHISPER_DECODER_NAME,
                    inputs=[input_tensor_tokens, input_tensor_encoder_hidden],
                    timeout=int(decoder_timeout * 1_000_000)
                )
            except Exception as e:
                logger.error(f"❌ [{chunk_id}] Decoder inference failed at token {iteration}: {str(e)}")
                raise
            
            logits = response_decoder.as_numpy("logits")
            next_token = np.argmax(logits[:, -1, :], axis=-1)
            tokens = np.append(tokens, next_token[:, np.newaxis], axis=-1)
            tokens_generated += 1
            
            if next_token[0] == EOT:
                logger.info(f"✅ [{chunk_id}] EOT reached after {tokens_generated} tokens in {time.time() - decoder_start:.2f}s")
                break
            
            if iteration == max_tokens - 1:
                logger.warning(f"⚠️  [{chunk_id}] Reached max tokens ({max_tokens}). Possible infinite loop!")
        
        raw_text = tokenizer.decode(tokens[0, 3:])
        raw_text = raw_text.strip()

        chunk_start = chunk_index * 30.0
        chunk_end = chunk_start + 30.0

        total_time = time.time() - connection_start
        logger.info(f"✅ [{chunk_id}] COMPLETED in {total_time:.2f}s | Tokens: {tokens_generated} | Text length: {len(raw_text)} chars")
        
        return {
            "start": chunk_start,
            "end": chunk_end,
            "text": raw_text,
            "chunk_index": chunk_index,
            "tokens_generated": tokens_generated,
            "processing_time": total_time
        }
        
    except TimeoutException as e:
        logger.error(f"❌ [{chunk_id}] TIMEOUT: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ [{chunk_id}] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def process_audio_and_transcribe(
    file_path: str,
    include_timestamps: bool = True,
    window_size: int = 60,
    clean_with_gemini: bool = False,  # Changed default to False
    max_workers: int = 8,
    chunk_timeout: int = 120
) -> str:
    """
    Main function to process audio and generate transcription.
    Returns timestamped transcript string.
    """
    overall_start = time.time()
    logger.info(f"🎬 Starting transcription for: {file_path}")
    
    try:
        # Load and prepare audio
        logger.info("📊 Loading audio file...")
        audio_load_start = time.time()
        audio, sr = librosa.load(file_path, sr=16000)
        audio_duration = len(audio) / sr
        logger.info(f"✅ Audio loaded in {time.time() - audio_load_start:.2f}s | Duration: {audio_duration:.1f}s")

        # Split into chunks
        num_chunks = int(np.ceil(len(audio) / (30 * sr)))
        logger.info(f"🔪 Splitting into {num_chunks} chunks (30s each)")
        
        tokenizer = get_tokenizer(multilingual=True)
        spectrograms_to_process = []
        
        for i in range(num_chunks):
            start = i * 30 * sr
            end = start + (30 * sr)
            chunk = audio[start:end]
            
            chunk = whisper.pad_or_trim(chunk)
            mel_spectrogram_tensor = whisper.log_mel_spectrogram(chunk).to(torch.float32)
            spectrogram = mel_spectrogram_tensor.numpy()
            spectrograms_to_process.append(spectrogram)
        
        logger.info(f"✅ Prepared {len(spectrograms_to_process)} spectrograms")

        # Parallel transcription
        segments = [None] * num_chunks
        failed_chunks = []
        
        logger.info(f"🚀 Starting parallel transcription with {max_workers} workers...")
        transcription_start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    transcribe_chunk_with_timing,
                    spec, i, tokenizer, num_chunks
                ): i 
                for i, spec in enumerate(spectrograms_to_process)
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_index, timeout=chunk_timeout * num_chunks):
                index = future_to_index[future]
                completed += 1
                
                try:
                    segment_data = future.result(timeout=chunk_timeout)
                    segments[index] = segment_data
                    logger.info(f"✅ Progress: {completed}/{num_chunks} chunks completed ({completed/num_chunks*100:.1f}%)")
                    
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ Chunk {index} TIMEOUT after {chunk_timeout}s")
                    failed_chunks.append(index)
                    segments[index] = {
                        "start": index * 30.0,
                        "end": (index + 1) * 30.0,
                        "text": "[TIMEOUT ERROR]",
                        "chunk_index": index,
                        "error": "timeout"
                    }
                    
                except Exception as exc:
                    logger.error(f"❌ Chunk {index} FAILED: {type(exc).__name__}: {str(exc)}")
                    failed_chunks.append(index)
                    segments[index] = {
                        "start": index * 30.0,
                        "end": (index + 1) * 30.0,
                        "text": f"[ERROR: {type(exc).__name__}]",
                        "chunk_index": index,
                        "error": str(exc)
                    }
        
        transcription_time = time.time() - transcription_start
        logger.info(f"✅ Transcription completed in {transcription_time:.2f}s")
        
        if failed_chunks:
            logger.warning(f"⚠️  {len(failed_chunks)} chunks failed: {failed_chunks}")
        
        segments = [seg for seg in segments if seg is not None]
        
        # Create timestamped transcript
        logger.info("🔧 Creating timestamped transcript...")
        timestamped_output = create_segmented_timestamps(segments, window_size)
        
        total_time = time.time() - overall_start
        logger.info(f"✅ COMPLETE! Total time: {total_time:.2f}s | Failed chunks: {len(failed_chunks)}")
        
        return timestamped_output
        
    except Exception as e:
        logger.error(f"❌ FATAL ERROR in process_audio_and_transcribe: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise