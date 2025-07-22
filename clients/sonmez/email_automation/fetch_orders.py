import os
import imaplib
import email
import re
from email.header import decode_header
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import traceback
import dateparser

# Load environment variables
load_dotenv()

YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
YANDEX_PASSWORD = os.getenv("YANDEX_PASSWORD")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# --- KNOWLEDGE BASE FOR PRODUCT CATEGORIZATION ---
# --- KNOWLEDGE BASE FOR PRODUCT CATEGORIZATION ---

TENT_KEYWORDS = [
    "LONDON", "BUSHCRAFT", "CAPSULE", "MAXIA", "DISCOVER",
    "AQUILA", "PRESTIGE", "BUNGALOW", "CABIN", "FLOATING", "FAMILY"
]

COLOR_KEYWORDS = [
    # Common color names
    "ORANGE", "YELLOW", "DESERT", "GREY", "GRAY", "RED", "GREEN", "DESERT CAMO", "STANDARD",

    # SMZ fabric codes (with and without leading zero)
    "SMZ11", "SMZ12", "SMZ13", "SMZ14", "SMZ15", "SMZ16", "SMZ17", "SMZ18", "SMZ19", "SMZ20",
    "SMZ011", "SMZ012", "SMZ013", "SMZ014", "SMZ015", "SMZ016", "SMZ017", "SMZ018", "SMZ019", "SMZ020"
]

EXTRA_KEYWORDS = [
    # Tent accessories
    "FLOOR MAT", "HAND PUMP", "Sönmez Outdoor Rechargeable Digital Air Pump", "Bravo GE BTP-2 12V Inflation Pump", "TENT BAG", "INFLATION VALVE", "FIXING STAKES",
    "AWNING POLE", "CARRY BAG", "REPAIR KIT", "ORGANIZER", "LOCK DOOR",
    "CINEMA SCREEN", "TENSION LANYARD", "GUYLINES", "METAL TENT PEGS",

    # Stove & heater accessories
    "STOVE", "FIREPROOF MAT", "DIESEL HEATER", "FIRE GUARD", "PIPE", "WATER TANK",
    "PIZZA OVEN", "CHIMNEY PROTECTOR", "PERCOLOATOR", "GRILL", "HEAT-RESISTANT GLOVES",
    "SCRUBBING SPONGE", "CAMP TABLE", "WOODLANDER", "NOMAD", "WINNERWELL",

    # Inflatable screen
    "CINEVISION", "MOVIE SCREEN", "INFLATABLE SCREEN"
]


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

def setup_google_sheets():
    """Authenticates with Google Sheets API using service account."""
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        print("✅ Successfully authenticated with Google Sheets API.")
        return service
    except Exception as e:
        print(f"❌ Error setting up Google Sheets API: {e}")
        return None

def parse_order_email(body_html, tent_keywords, color_keywords, extra_keywords):
    soup = BeautifulSoup(body_html, 'html.parser')
    order_details = {}

    # Pre-emptively remove all script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    try:
        # --- Universal Order ID and Date Extraction ---
        order_id_match = re.search(r'(?:Order\s#|Yeni sipariş:\s|New order\s#)(\d+)', body_html, re.IGNORECASE)
        date_match = re.search(r'\((\d{1,2}\s\w+\s\d{4})\)', body_html, re.IGNORECASE)
        order_details['id'] = order_id_match.group(1) if order_id_match else 'N/A'
        raw_date = date_match.group(1) if date_match else None
        order_details['date'] = dateparser.parse(raw_date).strftime('%Y-%m-%d') if raw_date else 'N/A'
        if order_details['id'] == 'N/A': return None

        # --- Full Customer Name and Address Parsing Logic ---
        customer_name, customer_address, total_price = 'N/A', 'N/A', 'N/A'
        try:
            billing_address_text_node = soup.find(string=re.compile(r'^\s*(Billing address|Fatura adresi)\s*$', re.IGNORECASE))
            if billing_address_text_node:
                address_element = billing_address_text_node.find_parent().find_next_sibling()
                if address_element:
                    address_lines = list(address_element.stripped_strings)
                    if address_lines:
                        customer_name = address_lines[0]
                        physical_address_parts = [line for line in address_lines[1:] if '@' not in line and not re.match(r'^\+?\d[\d\s-]{7,}\d$', line)]
                        customer_address = "\n".join(physical_address_parts)
        except: pass
        try:
            total_text_node = soup.find(string=re.compile(r'^\s*(Total|Toplam):\s*$', re.IGNORECASE))
            if total_text_node:
                total_price = total_text_node.find_parent().find_next_sibling().get_text(strip=True)
        except: pass
        order_details.update({'customer': customer_name, 'address': customer_address, 'total_price': total_price})

        # --- Product Parsing Logic ---
        all_ordered_items = []
        # Primary Method: Formal "Product" table
        product_header = soup.find('th', string=re.compile(r'^Product$', re.IGNORECASE))
        if product_header:
            product_table_body = product_header.find_parent('thead').find_next_sibling('tbody')
            if product_table_body:
                product_rows = product_table_body.find_all('tr')
                for row in product_rows:
                    product_cell = row.find('td')
                    if product_cell:
                        all_ordered_items.extend(list(product_cell.stripped_strings))
        
        # --- FIX: Re-instated the robust fallback parser ---
        # This will run if the primary method fails to find any items.
        if not all_ordered_items:
            # We combine all keyword lists to find any potential product line
            all_keywords = tent_keywords + color_keywords + extra_keywords
            # Create a pattern to find any of these words
            pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in all_keywords) + r')\b', re.IGNORECASE)
            
            # Find all text nodes in the email that contain a product keyword
            found_strings = soup.find_all(string=pattern)
            cleaned_items = set()
            for text_node in found_strings:
                # Find the parent element to get the full product line, not just the keyword
                parent = text_node.find_parent(['p', 'div', 'span', 'strong', 'td', 'li'])
                if parent:
                    full_text = parent.get_text(strip=True).replace('\n', ' ')
                    # Heuristic to avoid grabbing long, non-product paragraphs
                    if len(full_text) < 150:
                         # Exclude summary lines
                        if not any(summary_word in full_text for summary_word in ['Subtotal', 'Shipping', 'Total', 'Payment']):
                            cleaned_items.add(full_text)
            all_ordered_items.extend(list(cleaned_items))


        # --- Categorization Logic ---
        tents, raw_colors, extras = [], [], []
        EXTENDED_COLOR_NAMES = color_keywords + ["GRAY"] 
        color_name_pattern = re.compile('|'.join(re.escape(name) for name in EXTENDED_COLOR_NAMES), re.IGNORECASE)
        
        for item in all_ordered_items:
            item = item.strip().lstrip('•').strip()
            if not item: continue
            item_upper = item.upper()

            if '$' in item or any(keyword in item_upper for keyword in extra_keywords):
                extras.append(item)
                continue

            if any(keyword in item_upper for keyword in tent_keywords):
                tents.append(item)
                color_matches_in_tent = color_name_pattern.findall(item)
                if color_matches_in_tent:
                    raw_colors.extend(color_matches_in_tent)
                continue

            color_tag_match = re.match(r'Colou?r:\s*(.*)', item, re.IGNORECASE)
            if color_tag_match:
                color_name = color_tag_match.group(1).strip()
                if color_name:
                    raw_colors.append(color_name)
                continue

            if item_upper.startswith("SMZ") or re.fullmatch(color_name_pattern, item):
                raw_colors.append(item)
                continue
            
            extras.append(item)

        # --- Post-processing and Normalization ---
        normalized_colors = []
        for color in raw_colors:
            if color.upper().startswith("SMZ"):
                normalized_colors.append(re.sub(r'\s+', '', color).upper())
            else:
                normalized_colors.append(color.title())
        
        final_tents = sorted(list(set(t for t in tents if t and t.strip() != ':')))
        final_colors = sorted(list(set(c for c in normalized_colors if c and c.strip() != ':')))
        final_extras = sorted(list(set(e for e in extras if e and e.strip() != ':')))
        
        order_details['tents'] = final_tents
        order_details['colors'] = final_colors
        order_details['extras'] = final_extras

        return order_details

    except Exception:
        traceback.print_exc()
        return None
    
def main():
    sheets_service = setup_google_sheets()
    mail = connect_to_yandex()
    if not sheets_service or not mail: return

    search_query = '(OR (SUBJECT "New Order") (BODY "WooCommerce"))'
    status, messages = mail.search(None, search_query)

    if status != "OK" or not messages[0]:
        print('❌ No emails found matching the search criteria.')
        return

    email_ids = messages[0].split()
    print(f"📨 Found {len(email_ids)} candidate emails. Filtering for actual orders...")

    processed_orders = {}
    order_email_count = 0

    for mail_id_bytes in email_ids:
        status, msg_data = mail.fetch(mail_id_bytes, "(RFC822)")
        if status != "OK": continue

        msg = email.message_from_bytes(msg_data[0][1])

        subject_header = msg["Subject"]
        try:
            subject, encoding = decode_header(subject_header)[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8", errors='ignore')
        except Exception:
            subject = str(subject_header)

        if "failed" in subject.lower() or "cancelled" in subject.lower():
            print(f"🚫 Skipping failed or cancelled version: {subject}")
            continue

        body_html = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    body_html = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body_html = msg.get_payload(decode=True).decode(errors='ignore')

        if not body_html or ("new order" not in subject.lower() and "order summary" not in body_html.lower()):
            continue

        order_email_count += 1
        order_data = parse_order_email(body_html, TENT_KEYWORDS, COLOR_KEYWORDS, EXTRA_KEYWORDS)

        if not order_data or not order_data.get('id') or order_data.get('id') == 'N/A':
            print(f"⚠️ Failed to parse a valid Order ID from subject: {subject}")
            continue
        
        order_id = order_data['id']
        
        # --- FIX: Simplified and Corrected Duplicate Handling ---
        # The script reads newest emails first. So, if we've already seen an order ID,
        # we can safely skip the current (older) email.
        if order_id in processed_orders:
            print(f"⏭️ Skipping older email for already processed Order ID: {order_id}")
            continue
        else:
            # First time seeing this order ID, store it and mark email as seen.
            processed_orders[order_id] = order_data
            mail.store(mail_id_bytes, '+FLAGS', '\\Seen')

    # --- After the loop, process the curated list of orders ---
    print(f"\nFound {order_email_count} actual order emails to process.")
    print(f"Found {len(processed_orders)} unique, valid orders to log.")

    all_order_rows = []
    for order_id, order_data in processed_orders.items():
        tents = order_data.get('tents', [])
        extras = order_data.get('extras', [])
        colors = order_data.get('colors', [])

        if not tents and not extras and not colors:
            print(f"⏭️ Skipping truly empty order: {order_id}")
            continue

        print(f"⚙️  Logging Order ID: {order_id}")
        
        tents_str = ", ".join(tents) if tents else "N/A"
        colors_str = ", ".join(colors) if colors else "N/A"
        extras_str = ", ".join(extras) if extras else "N/A"

        all_order_rows.append([
            order_data.get('id', ''),
            order_data.get('customer', 'N/A'),
            order_data.get('address', 'N/A'),
            order_data.get('date', 'N/A'),
            order_data.get('total_price', 'N/A'),
            tents_str,
            colors_str,
            extras_str,
        ])
    
    if not all_order_rows:
        print("ℹ️  No new, unique orders to write to the sheet.")
    else:
        print(f"\n✍️ Writing data for {len(all_order_rows)} unique orders to Google Sheets...")
        header = ["Order ID", "Customer Name", "Address", "Date of Order", "Total Price", "Tent", "Color", "Extras"]
        final_data = [header] + all_order_rows
        try:
            sheets_service.spreadsheets().values().clear(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute()
            value_range_body = {'values': final_data}
            sheets_service.spreadsheets().values().update(
                spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A1",
                valueInputOption='USER_ENTERED', body=value_range_body
            ).execute()
            print("✅ Successfully wrote data to Google Sheet.")
        except Exception as e:
            print(f"❌ Error writing to Google Sheet: {e}")

    mail.logout()

if __name__ == "__main__":
    main()