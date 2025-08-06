import os
import requests
import time 

def generate_audio(text):
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise ValueError("Missing ElevenLabs API credentials")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

  

    max_retries = 3
    base_delay = 2  # Start with a 2-second delay

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            # If the request was successful, return the content
            if response.status_code == 200:
                return response.content
            
            # If we hit a rate limit, wait and try again
            if response.status_code == 429:
                print(f"[TTS WARNING] Rate limit exceeded. Waiting for {base_delay} seconds before retrying...")
                time.sleep(base_delay)
                base_delay *= 2  # Double the delay for the next attempt
                continue # Go to the next attempt in the loop

            # For other HTTP errors, raise an exception and stop
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            print(f"[TTS ERROR] {e}")
            break # Stop retrying on connection errors

    # If all retries fail, return None
    print("[TTS ERROR] All retry attempts failed.")
    return None