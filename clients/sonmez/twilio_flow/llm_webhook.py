from flask import Flask, request, send_file, Response
from openai import OpenAI  # OpenAI Chat API client
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import re
import platform
import tempfile

app = Flask(__name__)

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# === INIT OPENAI CLIENT ===
client = OpenAI()  # Uses OPENAI_API_KEY from environment

# === LOAD API KEYS AND CONFIG ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")

# Ensure all required keys are present
assert ELEVENLABS_API_KEY, "Missing ELEVENLABS_API_KEY"
assert ELEVENLABS_VOICE_ID, "Missing ELEVENLABS_VOICE_ID"
assert NGROK_BASE_URL, "Missing NGROK_BASE_URL"

print(f"--- Using ElevenLabs Key ending in: ...{ELEVENLABS_API_KEY[-4:]}")

# === LOAD PRODUCT DATA ===
with open("structured_tent_products.json", "r") as f:
    tents = json.load(f)

with open("scraped_accessories.json", "r") as f:
    accessories = json.load(f)

# === CONTEXT FOR GENERAL RESPONSES ===
product_names = [product['name'] for product in tents]
brief_product_context = "The available tent models are: " + ", ".join(product_names) + "."

# === MAIN TWILIO WEBHOOK ENDPOINT ===
@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    user_input = request.form.get("SpeechResult", "")

    # --- Step 1: Try to match a product from user input ---
    mentioned_product = None
    for product in tents:
        if product['name'].lower() in user_input.lower():
            mentioned_product = product
            break

    # --- Step 2: Set up the system prompt & context ---
    system_prompt = ""
    context_to_use = ""

    if mentioned_product:
        # If a specific product is mentioned, prepare expert mode
        system_prompt = (
            "You are a product expert. A customer is asking about a specific product. "
            "Using only the detailed information provided, answer their question naturally and concisely. "
            "If the answer isn't in the details, say you don't have that specific information."
        )

        # Filter relevant details to build a narrow context
        details_to_include = []
        keywords_to_find = ["Fabric:", "Cold Resistance:", "High Temperature:",
                            "Sun Protection Factor:", "Wind Resistance:", "Dimensions:"]
        for detail in mentioned_product.get('material_details', []):
            if any(keyword in detail for keyword in keywords_to_find):
                details_to_include.append(f"- {detail.strip()}")

        context_to_use = (
            f"Answering questions about: {mentioned_product['name']}\n"
            f"Key Details:\n" +
            "\n".join(details_to_include) if details_to_include else "No specific material details available."
        )
    else:
        # If no product is mentioned, use greeter mode
        system_prompt = (
            "You are a friendly greeter for Sönmez Outdoor. You can answer general questions or list the available products. "
            "Keep your answers brief and encourage the user to ask about a specific model."
        )
        context_to_use = brief_product_context

    # --- Step 3: Send prompt and context to OpenAI ---
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": context_to_use},
        {"role": "user", "content": user_input}
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    answer = response.choices[0].message.content

    # Fallback if model fails to generate a response
    if not answer or not answer.strip():
        answer = "I'm sorry, I didn't quite understand. Could you please say that again?"

    # --- Step 4: Generate audio with ElevenLabs and prepare TwiML response ---
    tts_audio = elevenlabs_tts(answer)

    # If TTS fails, respond with a fallback message
    if tts_audio is None:
        twiml = f"""
        <Response>
            <Say voice="alice">I'm sorry, I am having trouble responding right now.</Say>
            <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
        </Response>
        """
        return Response(twiml, mimetype="text/xml")

    # Save audio file to a temporary directory
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
    # Return TwiML response
    return Response(twiml, mimetype="text/xml")

# === AUDIO PLAYBACK ENDPOINT FOR TWILIO ===
@app.route("/audio/<filename>")
def audio(filename):
    temp_dir = tempfile.gettempdir()
    return send_file(os.path.join(temp_dir, filename), mimetype="audio/mpeg")


# === ELEVENLABS TTS HELPER FUNCTION ===
def elevenlabs_tts(text):
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
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()  # Raise error if request failed
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error calling ElevenLabs API: {e}")
        return None


# === PLACEHOLDER FOR ORDER STATUS CHECKING ===
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


# === RUN THE APP LOCALLY ON PORT 5009 ===
if __name__ == "__main__":
    app.run(port=5009)
