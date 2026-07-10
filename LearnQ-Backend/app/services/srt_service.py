from typing import List, Dict

def format_srt_timestamp(seconds: float) -> str:
    """Converts seconds into the SRT timestamp format HH:MM:SS,ms"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    seconds = milliseconds // 1000
    milliseconds %= 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def create_srt_file(segments: List[Dict], output_path: str):
    """
    Takes a list of Whisper segments and writes them to an SRT file.
    """
    print(f"Creating SRT file at: {output_path}")
    with open(output_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(segments):
            # 1. Write the segment number
            srt_file.write(f"{i + 1}\n")
            
            # 2. Write the start and end timestamps
            start_time = format_srt_timestamp(segment['start'])
            end_time = format_srt_timestamp(segment['end'])
            srt_file.write(f"{start_time} --> {end_time}\n")
            
            # 3. Write the transcribed text
            srt_file.write(f"{segment['text'].strip()}\n\n")
    print("✅ SRT file created successfully.")