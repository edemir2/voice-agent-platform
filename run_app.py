# This line imports the 'app' object we defined in our webhook file.
from voice_agent_service.clients.sonmez.twilio_flow.llm_webhook import app

if __name__ == "__main__":
    # host='0.0.0.0' makes the app accessible on our local network,
    # which is useful for testing with services like Twilio.
    # debug=True will provide helpful error messages while you're developing.
    app.run(host='0.0.0.0', port=5009, debug=True)