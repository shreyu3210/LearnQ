import yt_dlp
import os
import glob

DOWNLOAD_DIRECTORY = "./uploads"
os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)

def download_youtube_video(url: str, video_id: str) -> str:
    """
    Downloads a video from a YouTube URL, saving it with a unique video_id.
    Returns the full path to the downloaded file.
    """
    print(f"\nDownloading YouTube video from: {url} with ID: {video_id}")

    output_template = os.path.join(DOWNLOAD_DIRECTORY, f"{video_id}.%(ext)s")
    # quality = '480p'
    # ydl_opts = {
    #     'format': 'best',  
    #     'outtmpl': output_template,  # <-- FIX #1: Use the template with the video_id
    #     'merge_output_format': 'mp4',
    # }
    quality = '480p'
    ydl_opts = {
    'format': 'best[height<=480]/bestvideo[height<=480]+bestaudio/best',
    'outtmpl': output_template,
    'merge_output_format': 'mp4',
    # --- NEW SETTINGS FOR 2026 ---
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'], # Mobile clients are harder to block
            'player_skip': ['webpage', 'configs'],
        }
    },
    'nocheckcertificate': True,
    'quiet': False,
    'no_warnings': False,
    }

    try:
        # FIX #2: Call the download function
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # The final path should be the video_id with the .mp4 extension
        downloaded_filepath = os.path.join(DOWNLOAD_DIRECTORY, f"{video_id}.mp4")
        
        # Verify the file now exists
        if os.path.exists(downloaded_filepath):
            print(f"✅ Video downloaded to: {downloaded_filepath}")
            return downloaded_filepath
        else:
            # Fallback search in case the extension was different
            search_pattern = os.path.join(DOWNLOAD_DIRECTORY, f"{video_id}.*")
            files_found = glob.glob(search_pattern)
            if files_found:
                actual_file = files_found[0]
                print(f"✅ Video downloaded to: {actual_file}")
                return actual_file
            
            raise Exception("File was not found after download completed.")

    except Exception as e:
        print(f"❌ Error downloading YouTube video: {e}")
        return None