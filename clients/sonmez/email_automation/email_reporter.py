import os
import imaplib
import email
import re
from email.header import decode_header
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import collections
import time
import openai 

# --- Load Environment Variables ---
load_dotenv()
YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
YANDEX_PASSWORD = os.getenv("YANDEX_PASSWORD")
# Set up OpenAI client
try:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file.")
except Exception as e:
    print(f"❌ Error setting up OpenAI: {e}")
    exit()

def prepare_email_for_prompt(body, max_chars=1500):
    """Truncates the email body to a max character length to save tokens."""
    if len(body) > max_chars:
        return body[:max_chars] + "..."
    return body

# --- Email Connection and Parsing Functions (Unchanged from your script) ---


def connect_to_yandex():
    """Connects to the Yandex IMAP server and logs in."""
    try:
        mail = imaplib.IMAP4_SSL("imap.yandex.com")
        mail.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        mail.select("inbox")
        print("✅ Successfully connected to Yandex Mail.")
        return mail
    except Exception as e:
        print(f"❌ Error connecting to Yandex Mail: {e}")
        return None

def clean_html_to_text(html_text):
    """Removes HTML tags and extra whitespace from a string."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'html.parser')
    return re.sub(r'\s+', ' ', soup.get_text()).strip()

def decode_header_text(header):
    """Decodes email headers to a readable string."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    header_parts = []
    for part, encoding in decoded_parts:
        try:
            if isinstance(part, bytes):
                header_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                header_parts.append(part)
        except (UnicodeDecodeError, LookupError):
            header_parts.append(str(part))
    return "".join(header_parts)

def get_email_body(msg):
    """Extracts the plain text or cleaned HTML body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    return part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    continue
    else:
        if msg.get_content_type() == 'text/plain':
            return msg.get_payload(decode=True).decode(errors='ignore')

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                return clean_html_to_text(part.get_payload(decode=True).decode(errors='ignore'))
    elif msg.get_content_type() == 'text/html':
         return clean_html_to_text(msg.get_payload(decode=True).decode(errors='ignore'))
    return ""

# --- NEW: AI-Powered Summarization Logic ---

def get_ai_summary_for_day(day_email_content):
    """
    Sends all email content for a day to the OpenAI API for reasoning and summarization.
    """
    if not day_email_content:
        return "No emails to analyze for this day."

    # This prompt is the key to getting the output you want.
    # It instructs the AI to reason about the emails, not just summarize them.
    prompt = f"""
    You are an intelligent executive assistant. Your task is to analyze the following email data from a single day and provide a concise, insightful summary.

    - Identify the main topics, conversations, and outcomes.
    - Mention the key people and companies involved (e.g., Olicia from PayPal, Vera from Wonderchat).
    - **Reason about the interactions.** For example, if you see a meeting link and a follow-up, state that a meeting or demo likely occurred.
    - Summarize any customer problems and whether they were resolved.
    - Synthesize all information into a brief, narrative paragraph for the day. Do not just list the emails.

    Here is the combined email data for the day:
    ---
    {day_email_content}
    ---
    Provide the reasoned summary for this day's activities:
    """

    try:
        print("🤖 Sending data to AI for analysis...")
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # "gpt-3.5-turbo" for a faster, cheaper option, gpt-4o-mini for a more powerful option
            messages=[
                {"role": "system", "content": "You are a helpful executive assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # A little creativity
            max_tokens=250   # Control the length of the output
        )
        summary = response.choices[0].message.content.strip()
        print("✅ AI analysis complete.")
        return summary
    except Exception as e:
        print(f"❌ Error during OpenAI API call: {e}")
        return "Could not generate AI summary due to an error."


# --- Main Application Logic ---

def generate_daily_report(start_date, end_date):
    """Main function to run the email analysis and reporting for a specific date range."""
    mail = connect_to_yandex()
    if not mail:
        return

    # Format dates for IMAP search
    start_date_str = start_date.strftime("%d-%b-%Y")
    end_date_str = end_date.strftime("%d-%b-%Y")
    
    # Search for emails within the specified date range
    search_criteria = f'(SINCE "{start_date_str}" BEFORE "{end_date_str}")'
    status, messages = mail.search(None, search_criteria)

    if status != "OK" or not messages[0]:
        print(f'ℹ️ No emails found between {start_date_str} and {end_date_str}.')
        mail.logout()
        return

    email_ids = messages[0].split()
    print(f"📨 Found {len(email_ids)} emails from the specified period. Analyzing...")

    # Use defaultdict to store concatenated email bodies for each day
    daily_email_data = collections.defaultdict(str)
    date_range = [start_date + timedelta(days=x) for x in range((end_date-start_date).days)]

    for mail_id in reversed(email_ids): # Process newest first
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        if status != 'OK': continue
            
        msg = email.message_from_bytes(msg_data[0][1])
        
        try:
            email_dt = email.utils.parsedate_to_datetime(msg["Date"])
            email_date_obj = email_dt.date()
        except:
            continue # Skip emails with invalid date format

        # Check if the email is within our target date range
        if start_date <= email_date_obj < end_date:
            day_str = email_date_obj.strftime("%A, %Y-%m-%d") # e.g., "Monday, 2025-07-14"
            
    
    subject = decode_header_text(msg["Subject"])
    sender = decode_header_text(msg["From"])
    body = get_email_body(msg)

    # Prepare and truncate the body to save tokens
    prepared_body = prepare_email_for_prompt(body) # <-- ADD THIS LINE

    # Append the structured content for the AI to analyze
    daily_email_data[day_str] += f"Email from '{sender}' with subject '{subject}':\n{prepared_body}\n\n---\n\n"

    # --- Generate the Final Report ---
    report = f"Email Activity Report ({start_date_str} to {end_date_str})\n"
    report += "="*50 + "\n\n"

    # Iterate through the dates to ensure every day in the range is in the report
    for day in date_range:
        day_str = day.strftime("%A, %Y-%m-%d")
        report += f"## {day_str.upper()}\n\n"
        
        day_content = daily_email_data[day_str]
        ai_summary = get_ai_summary_for_day(day_content)
        report += f"{ai_summary}\n\n"
        report += "-"*50 + "\n\n"

        # Add a delay to respect rate limits between days
        print("⏳ Pausing for 20 seconds to respect API rate limits...")
        time.sleep(20) 


    output_filename = "daily_ai_report_Wed.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\n✅ Report has been generated! Check the file: '{output_filename}'")
    mail.logout()

if __name__ == "__main__":
    # --- Analyze ONE specific day ---
    
    # Set the single day I want to analyze
    start_date = date(2025, 7, 16)  # Change this to the desired date
    
    # The end date is the next day, because the search is not inclusive
    end_date = start_date + timedelta(days=1)

    print(f"🔎 Analyzing emails for the single day: {start_date.strftime('%Y-%m-%d')}...")
    generate_daily_report(start_date=start_date, end_date=end_date)