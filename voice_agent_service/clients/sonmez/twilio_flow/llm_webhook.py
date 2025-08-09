import os
from dotenv import load_dotenv
from flask import Flask, request, send_file, Response
from datetime import datetime
import tempfile
from pathlib import Path

# Developer's Note: The imports are now streamlined. We only bring in what's necessary
# for the RAG system: the assistant handler, the TTS engine, and the WhatsApp blueprint.
from voice_agent_service.clients.sonmez.llm_logic.assistant_handler import run_rag_assistant
from voice_agent_service.clients.sonmez.voice.elevenlabs_tts import generate_audio
from voice_agent_service.clients.sonmez.whatsapp_flow.whatsapp_webhook import whatsapp_bp

# Developer's Note: Standard Flask app initialization.
app = Flask(__name__)

# Developer's Note: This is a robust way to find the .env file in the project root,
# regardless of where the script is run from.
env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(dotenv_path=env_path)

# Developer's Note: Loading all necessary API keys and base URLs from environment
# variables is a security best practice. The 'assert' ensures the app fails fast
# if any of these critical variables are missing.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")
assert ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID and NGROK_BASE_URL, "Missing ENV variables"

# Developer's Note: This dictionary will store the conversation history for each unique
# phone call. Using CallSid as the key is the correct way to handle multiple
# concurrent calls, ensuring conversations don't get mixed up.
chat_history = {}

@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    """Handles incoming voice calls from Twilio."""
    # Developer's Note: We extract the unique CallSid to manage this call's specific history.
    call_sid = request.form.get("CallSid")
    # SpeechResult contains the text transcribed from the user's speech.
    user_input = request.form.get("SpeechResult", "")

    # Retrieve this call's history, or start a new empty list if it's the first turn.
    history = chat_history.get(call_sid, [])

    # Developer's Note: This is the core logic. All the complexity is now handled by our
    # RAG assistant. We just pass the user's input and the conversation history.
    answer = run_rag_assistant(user_input, history)

    # Save the updated history back to our main dictionary for the next turn.
    chat_history[call_sid] = history

    # Developer's Note: A simple fallback for cases where the AI might return an empty response.
    if not answer.strip():
        answer = "I'm sorry, I didn't quite understand. Could you please say that again?"

    # Convert the AI's text answer into speech.
    tts_audio = generate_audio(answer)
    if tts_audio is None:
        # If TTS fails, provide a graceful audio error to the user.
        twiml = "<Response><Say>I'm having trouble responding right now.</Say></Response>"
        return Response(twiml, mimetype="text/xml")

    # Developer's Note: To play custom audio in a Twilio call, we must host the audio file
    # at a publicly accessible URL. Here, we save the generated MP3 to a temporary
    # directory and use our NGROK URL to create the public link.
    temp_dir = tempfile.gettempdir()
    filename = f"tts_{datetime.now().timestamp():.0f}.mp3"
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "wb") as f:
        f.write(tts_audio)

    play_url = f"{NGROK_BASE_URL}/audio/{filename}"
    
    # Developer's Note: This TwiML response tells Twilio to play our generated audio file
    # and then immediately listen for the user's next response, continuing the conversation.
    twiml = f"""
    <Response>
        <Play>{play_url}</Play>
        <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
    </Response>
    """
    return Response(twiml, mimetype="text/xml")

@app.route("/audio/<filename>")
def audio(filename):
    """A simple endpoint to serve the temporary audio files."""
    temp_dir = tempfile.gettempdir()
    return send_file(os.path.join(temp_dir, filename), mimetype="audio/mpeg")

# Developer's Note: This registers the routes from our whatsapp_webhook.py file,
# allowing our single Flask application to handle both voice and WhatsApp.
app.register_blueprint(whatsapp_bp)

# The get_order_status_from_woocommerce function has been removed to avoid redundancy.
# It will be built out as a separate tool for the RAG agent.