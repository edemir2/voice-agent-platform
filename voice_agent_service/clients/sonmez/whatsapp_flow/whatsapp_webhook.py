from flask import Blueprint, request, Response

# === UPDATED IMPORT ===
# Import the new RAG assistant function.
from voice_agent_service.clients.sonmez.llm_logic.assistant_handler import run_rag_assistant

# Define the blueprint
whatsapp_bp = Blueprint('whatsapp', __name__)

# In-memory history for WhatsApp users (for demo purposes)
whatsapp_history = {}

@whatsapp_bp.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    # --- Get data from incoming message ---
    msg_body = request.form.get("Body", "")
    from_number = request.form.get("From", "") # Use this to track user history

    # Get or initialize conversation history for this specific user
    history = whatsapp_history.get(from_number, [])

    # --- SIMPLIFIED RAG LOGIC ---
    # Call the new RAG assistant directly.
    reply_text = run_rag_assistant(msg_body, history)
    
    # Save the updated history for this user
    whatsapp_history[from_number] = history

    # --- Formulate and send the TwiML response ---
    twiml = f"<Response><Message>{reply_text}</Message></Response>"
    return Response(twiml, mimetype="text/xml")