from youtube_transcript_api import YouTubeTranscriptApi

video_id = "jNQXAC9IVRw" # Me at the zoo

try:
    print(f"Fetching transcript for {video_id} using fetch()...")
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id)
    print("✅ Success!")
    # Transcript might be a list of dicts
    print(transcript[:2]) 
except Exception as e:
    print(f"❌ Failed: {e}")
