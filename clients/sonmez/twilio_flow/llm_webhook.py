from flask import Flask, request, send_file, Response
from openai import OpenAI # <-- 1. Import the new client
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import re

app = Flask(__name__)

# === CONFIG ===
load_dotenv()

# 2. Initialize the client (it will automatically use the OPENAI_API_KEY environment variable)
client = OpenAI() 

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")

assert ELEVENLABS_API_KEY, "Missing ELEVENLABS_API_KEY"
assert ELEVENLABS_VOICE_ID, "Missing ELEVENLABS_VOICE_ID"
assert NGROK_BASE_URL, "Missing NGROK_BASE_URL"

# === Load product JSON ===
with open("structured_tent_products.json", "r") as f:
    tents = json.load(f)

with open("scraped_accessories.json", "r") as f:
    accessories = json.load(f)

# === Load product JSON ===
with open("structured_tent_products.json", "r") as f:
    tents = json.load(f)

with open("scraped_accessories.json", "r") as f:
    accessories = json.load(f)

# === Create a clean, summarized context ===
def summarize_products(product_list, limit=7):
    summary_lines = []
    for product in product_list[:limit]:
        name = product.get('name', 'N/A')
        # For tents, show capacity. For others, it will be ignored.
        capacity_str = ""
        if 'capacity' in product and product['capacity'].get('camping'):
            capacity_str = f", Capacity: {product['capacity']['camping']} people"
        
        # Get the base price from the first color option
        price_str = ""
        if 'colors' in product and product['colors']:
            price_str = f", Price: ${product['colors'][0].get('price', 'N/A')}"
            
        summary_lines.append(f"- {name}{capacity_str}{price_str}")
    return "\n".join(summary_lines)

tent_summary = summarize_products(tents)
accessory_summary = summarize_products(accessories)

product_context = f"Here are the available tents:\n{tent_summary}\n\nHere are some available accessories:\n{accessory_summary}"

# === Route ===
@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    user_input = request.form.get("SpeechResult", "")
    
    # --- Check for order status request ---
    order_match = re.search(r"(?:order\s*#?\s*)(\d{3,})", user_input.lower())
    order_status = None
    if order_match:
        order_id = order_match.group(1)
        order_status = get_order_status_from_woocommerce(order_id)
        
    # --- Call GPT ---
    messages = [
        {"role": "system", "content": "You are a friendly and helpful voice assistant for Sönmez Outdoor. Your primary goal is to answer questions about products using the provided catalog and check order statuses. If a user asks a question you cannot answer with the provided information, or if they engage in small talk, respond politely and guide them back to your main functions."},
        {"role": "system", "content": product_context}
    ]
    if order_status:
        messages.append({"role": "system", "content": f"Order status: {order_status}"})
    messages.append({"role": "user", "content": user_input})

    # 3. Use the new syntax to create the chat completion
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    answer = response.choices[0].message.content

    # Add a check for empty or whitespace-only responses ===
    if not answer or not answer.strip():
        answer = "I'm sorry, I didn't quite understand. Could you please say that again?"

    # --- Call ElevenLabs ---
    tts_audio = elevenlabs_tts(answer)

    # Handle TTS failure gracefully 
    if tts_audio is None:
        # If TTS failed, use Twilio's built-in <Say> as a fallback
        twiml = """
        <Response>
            <Say voice="alice">I'm sorry, I am having trouble responding right now. Please try again in a moment.</Say>
            <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
        </Response>
        """
        return Response(twiml, mimetype="text/xml")
    
    # Save the file to play
    file_path = f"/tmp/tts_{datetime.now().timestamp()}.mp3"
    with open(file_path, "wb") as f:
        f.write(tts_audio)
        
    # --- Return TwiML with <Play> ---
    play_url = f"{NGROK_BASE_URL}/audio/{os.path.basename(file_path)}"
    twiml = f"""
    <Response>
        <Play>{play_url}</Play>
        <Gather input="speech" action="/voice-webhook" speechTimeout="auto" />
    </Response>
    """
    return Response(twiml, mimetype="text/xml")

# === Serve audio files ===
@app.route("/audio/<filename>")
def audio(filename):
    return send_file(f"/tmp/{filename}", mimetype="audio/mpeg")

# === ElevenLabs helper ===
def elevenlabs_tts(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        print(f"Error calling ElevenLabs API: {e}")
        return None # Return None to indicate failure

# === WooCommerce helper ===

def get_order_status_from_woocommerce(order_id):
    # This is a placeholder. Make sure this URL and the keys are correct.
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

if __name__ == "__main__":
    app.run(port=5009)