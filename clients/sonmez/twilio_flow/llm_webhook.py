import os
from dotenv import load_dotenv
from flask import Flask, request, send_file, Response
from datetime import datetime
import tempfile
import requests



from data.product_loader import load_tent_products, load_accessories
from llm_logic.product_matcher import match_product
from llm_logic.assistant_handler import run_assistant
from voice.elevenlabs_tts import generate_audio

# === INIT APP ===
app = Flask(__name__)

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=env_path)


# === ENV VARIABLES ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")
assert ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID and NGROK_BASE_URL, "Missing ENV variables"

# === LOAD DATA ===
tents = load_tent_products()
accessories = load_accessories()

# === TWILIO VOICE WEBHOOK ===
@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    user_input = request.form.get("SpeechResult", "")
    mentioned_product = match_product(user_input, tents)
    answer = run_assistant(user_input, mentioned_product, tents)

    if not answer.strip():
        answer = "I'm sorry, I didn't quite understand. Could you please say that again?"

    tts_audio = generate_audio(answer)
    if tts_audio is None:
        twiml = """
        <Response>
            <Say voice="alice">I'm sorry, I am having trouble responding right now.</Say>
            <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
        </Response>
        """
        return Response(twiml, mimetype="text/xml")

    # Save and play audio
    temp_dir = tempfile.gettempdir()
    filename = f"tts_{datetime.now().timestamp():.0f}.mp3"
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "wb") as f:
        f.write(tts_audio)

    play_url = f"{NGROK_BASE_URL}/audio/{filename}"
    action_url = f"{NGROK_BASE_URL}/voice-webhook"
    twiml = f"""
    <Response>
        <Play>{play_url}</Play>
        <Gather input="speech" action="{action_url}" speechTimeout="auto" />
    </Response>
    """
    return Response(twiml, mimetype="text/xml")

# === AUDIO FILE ENDPOINT ===
@app.route("/audio/<filename>")
def audio(filename):
    temp_dir = tempfile.gettempdir()
    return send_file(os.path.join(temp_dir, filename), mimetype="audio/mpeg")

# === OPTIONAL: ORDER STATUS PLACEHOLDER ===
def get_order_status_from_woocommerce(order_id):
    url = f"https://yourshop.com/wp-json/wc/v3/orders/{order_id}"
    auth = (os.getenv("WC_KEY"), os.getenv("WC_SECRET"))
    try:
        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"Order #{data['id']} is currently '{data['status']}' and was placed on {data['date_created'][:10]}."
        else:
            return "Sorry, I couldn’t find that order."
    except requests.exceptions.RequestException:
        return "Sorry, I'm having trouble connecting to the order system right now."

# === RUN LOCALLY ===
if __name__ == "__main__":
    app.run(port=5009)
