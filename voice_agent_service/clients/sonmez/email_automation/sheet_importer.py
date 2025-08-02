import os
import imaplib
import email
import json
import time
from email.header import decode_header
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import date, timedelta
import openai
import gspread

# --- Load Environment Variables ---
load_dotenv()
YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
YANDEX_PASSWORD = os.getenv("YANDEX_PASSWORD")
GOOGLE_SHEET_ID = os.getenv("DEALERSHIP_SHEET_ID")
CREDENTIALS_FILE = os.getenv("DEALERSHIP_CREDENTIALS_FILE") 

try:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file.")
except Exception as e:
    print(f"❌ Error setting up OpenAI: {e}")
    exit()

# --- Google Sheets Connection ---
def connect_to_google_sheets():
    """Connects to Google Sheets using the service account credentials."""
    try:
        # Uses the credentials1.json file in the same directory
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
        # Assumes you are writing to the first sheet
        worksheet = spreadsheet.sheet1
        print("✅ Successfully connected to Google Sheets.")
        return worksheet
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
        return None

# --- AI Information Extraction --- 
def extract_info_with_ai(email_body):
    """Uses OpenAI to extract structured data from an email body."""
    if not email_body or len(email_body) < 20:
        return None

    # This prompt is the key to handling varied email formats
    prompt = f"""
    You are an expert data entry assistant. Your task is to analyze the following email text, which is a dealership or partnership application, and extract specific details.

    The fields to extract are:
    - CompanyName
    - ContactName
    - Position
    - ContactEmail
    - Experience
    - ContactPhone

    Instructions:
    1.  Carefully read the entire email to find the information.
    2.  If a field is not mentioned, use "N/A" as the value.
    3.  For "Experience", extract numerical values like '2 years', '30', '1+' and standardize it (e.g., "2 years"). If not present, return 'N/A'.
    4.  The output MUST be a valid JSON object only. Do not add any introductory text, explanations, or markdown formatting like ```json.

    Email Text:
    ---
    {email_body}
    ---
    JSON Output:
    """

    try:
        print("🤖 Sending email content to AI for data extraction...")
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o", # Best model for complex extraction
            messages=[
                {"role": "system", "content": "You are a data entry assistant that only outputs valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"} # Enforces JSON output
        )
        # The response content is a JSON string, so we parse it
        extracted_data = json.loads(response.choices[0].message.content)
        print(f"✅ AI analysis complete for: {extracted_data.get('CompanyName', 'N/A')}")
        return extracted_data
    except json.JSONDecodeError as e:
        print(f"❌ AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error during OpenAI API call: {e}")
        return None

# --- Email Parsing (Slightly modified from previous script) ---
def get_email_body(msg):
    """Extracts the plain text or cleaned HTML body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break # Found plain text, use it
                except:
                    continue
        if not body: # If no plain text found, fallback to HTML
             for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    soup = BeautifulSoup(part.get_payload(decode=True).decode(errors='ignore'), 'html.parser')
                    body = soup.get_text(separator='\n', strip=True)
                    break
    else: # Not multipart
        if 'text/plain' in msg.get_content_type():
            body = msg.get_payload(decode=True).decode(errors='ignore')
        elif 'text/html' in msg.get_content_type():
            soup = BeautifulSoup(msg.get_payload(decode=True).decode(errors='ignore'), 'html.parser')
            body = soup.get_text(separator='\n', strip=True)

    return body

# --- Main Application Logic ---
def main():
    """Main function to run the email scraping and sheet importing."""
    worksheet = connect_to_google_sheets()
    if not worksheet:
        return

    # 1. Connect to Yandex Mail
    try:
        mail = imaplib.IMAP4_SSL("imap.yandex.com")
        mail.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        mail.select("inbox")
        print("✅ Successfully connected to Yandex Mail.")
    except Exception as e:
        print(f"❌ Error connecting to Yandex Mail: {e}")
        return

    # 2. Search for emails from the last 2 days
    search_date = (date.today() - timedelta(days=2)).strftime("%d-%b-%Y")
    search_criteria = f'(SINCE "{search_date}")'
    status, messages = mail.search(None, search_criteria)

    if status != "OK" or not messages[0]:
        print('ℹ️ No emails found in the last 2 days.')
        mail.logout()
        return

    email_ids = messages[0].split()
    print(f"📨 Found {len(email_ids)} emails from the last 2 days. Analyzing...")

    # Define keywords to identify relevant emails
    keywords = ["dealership", "application", "partnership", "reselling", "interest", "dealer"]

    for mail_id in email_ids:
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        if status != 'OK': continue
            
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Decode subject and check for keywords
        subject = str(decode_header(str(msg["Subject"]))[0][0])
        if not any(keyword in subject.lower() for keyword in keywords):
            # print(f"Skipping email with subject: '{subject}'")
            continue # Skip if no keywords are in the subject

        print(f"\nProcessing relevant email with subject: '{subject}'")
        body = get_email_body(msg)
        
        # 3. Use AI to extract info
        data = extract_info_with_ai(body)
        
        # 4. Write data to Google Sheets
        if data:
            try:
                # Prepare row in the correct order for your sheet
                row = [
                    data.get("CompanyName", "N/A"),
                    data.get("ContactName", "N/A"),
                    data.get("Position", "N/A"),
                    data.get("ContactEmail", "N/A"),
                    data.get("Experience", "N/A"),
                    data.get("ContactPhone", "N/A")
                ]
                worksheet.append_row(row, value_input_option='USER_ENTERED')
                print(f"✅ Successfully wrote '{row[0]}' to Google Sheets.")
            except Exception as e:
                print(f"❌ Failed to write to Google Sheets: {e}")

        # Pause to avoid hitting API rate limits
        time.sleep(15)

    print("\n✅ All relevant emails processed.")
    mail.logout()


if __name__ == "__main__":
    main()