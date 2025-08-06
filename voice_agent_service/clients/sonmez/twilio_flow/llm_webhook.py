import os
from dotenv import load_dotenv
from flask import Flask, request, send_file, Response
from datetime import datetime
import tempfile
from pathlib import Path

# === UPDATED IMPORTS ===
# We now import the new RAG assistant and remove the old logic.
from voice_agent_service.clients.sonmez.llm_logic.assistant_handler import run_rag_assistant
from voice_agent_service.clients.sonmez.voice.elevenlabs_tts import generate_audio
from voice_agent_service.clients.sonmez.whatsapp_flow.whatsapp_webhook import whatsapp_bp

# === INIT APP ===
app = Flask(__name__)

# This path resolution is good. It robustly finds the .env file.
env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(dotenv_path=env_path)

# === ENV VARIABLES ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")
assert ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID and NGROK_BASE_URL, "Missing ENV variables"


# === TWILIO VOICE WEBHOOK ===
chat_history = {}

@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    call_sid = request.form.get("CallSid")
    user_input = request.form.get("SpeechResult", "")

    # Get or initialize conversation history for this specific call
    history = chat_history.get(call_sid, [])

    # --- SIMPLIFIED RAG LOGIC ---
    # Call the new RAG assistant directly. No more product matching needed.
    answer = run_rag_assistant(user_input, history)

    # Save the updated history for this call
    chat_history[call_sid] = history

    if not answer.strip():
        answer = "I'm sorry, I didn't quite understand. Could you please say that again?"

    tts_audio = generate_audio(answer)
    if tts_audio is None:
        twiml = "<Response><Say>I'm having trouble responding right now.</Say></Response>"
        return Response(twiml, mimetype="text/xml")

    # Save and play audio
    temp_dir = tempfile.gettempdir()
    filename = f"tts_{datetime.now().timestamp():.0f}.mp3"
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "wb") as f:
        f.write(tts_audio)

    play_url = f"{NGROK_BASE_URL}/audio/{filename}"
    twiml = f"""
    <Response>
        <Play>{play_url}</Play>
        <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
    </Response>
    """
    return Response(twiml, mimetype="text/xml")

# === AUDIO FILE ENDPOINT ===
@app.route("/audio/<filename>")
def audio(filename):
    temp_dir = tempfile.gettempdir()
    return send_file(os.path.join(temp_dir, filename), mimetype="audio/mpeg")

# Register the WhatsApp blueprint
app.register_blueprint(whatsapp_bp)

# The get_order_status_from_woocommerce function can remain if you plan to use it later.
# It does not interfere with the RAG implementation.
def get_order_status_from_woocommerce(order_id):
    # ... (function code) ...
    pass # Placeholder

# === OPTIONAL: ORDER STATUS PLACEHOLDER ===
def get_order_status_from_woocommerce(order_id):
    url = f"https://yourshop.com/wp-json/wc/v3/orders/{order_id}"
    auth = (os.getenv("WC_KEY"), os.getenv("WC_SECRET"))
    try:
        response = requests.get(url, auth=auth, timeout=10)
        response.raise_for_status()
        data = response.json()
        return f"Order #{data['id']} is currently '{data['status']}' and was placed on {data['date_created'][:10]}."
    except requests.exceptions.RequestException:
        return "Sorry, I'm having trouble connecting to the order system right now."
    
