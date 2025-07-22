from flask import Flask, request, Response
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

@app.route("/voice-webhook", methods=["POST"])
def voice_webhook():
    # Send basic input to Rasa server
    user_input = "hello"  # Static for now
    response = requests.post(
        "http://localhost:5005/webhooks/rest/webhook",
        json={"sender": "twilio_user", "message": user_input}
    )
    data = response.json()
    reply = data[0]["text"] if data else "Sorry, I didn’t understand that."

    # Return TwiML with the response
    twiml = f"""
    <Response>
        <Say>{reply}</Say>
    </Response>
    """
    return Response(twiml, mimetype="text/xml")

if __name__ == "__main__":
    app.run(port=5009)
