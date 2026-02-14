from youtube_transcript_api import YouTubeTranscriptApi

video_id = "jNQXAC9IVRw"
try:
    ytt = YouTubeTranscriptApi()
    transcript_data = ytt.fetch(video_id)
    full_text = " ".join([entry['text'] for entry in transcript_data])
    print(f"Length: {len(full_text)}")
    print(full_text)
except Exception as e:
    print(f"Error: {e}")
