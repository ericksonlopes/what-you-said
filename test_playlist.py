from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor


def test_playlist():
    # Use the playlist provided by the user
    playlist_url = "https://www.youtube.com/watch?v=dlQG02mwTD0&list=PLG47XsLEf0LdvYtX_zU7E_y_C1TgjgU59"
    
    print(f"Testing playlist extraction for: {playlist_url}")
    extractor = YoutubeExtractor(language="pt")
    
    try:
        videos = extractor.extract_playlist_videos(playlist_url)
        print(f"Extracted {len(videos)} videos.")
        for i, url in enumerate(videos[:5]):
            print(f"  {i+1}: {url}")
            
        if not videos:
            print("FAILED: No videos extracted.")
        else:
            print("SUCCESS: Videos extracted.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_playlist()
