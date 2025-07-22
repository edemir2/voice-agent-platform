import requests
from bs4 import BeautifulSoup
import json
import re
import time
from urllib.parse import quote_plus

def find_product_url(product_name):
    """
    Searches the website for a product and returns the URL of the first result.
    """
    search_query = quote_plus(product_name)
    search_url = f"https://sonmezoutdoor.us/?s={search_query}&post_type=product"
    print(f"Searching for '{product_name}'...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first product link in the search results
        first_result = soup.select_one('.product-grid-item .wd-entities-title a')
        
        if first_result and first_result.get('href'):
            url = first_result.get('href')
            print(f"Found URL: {url}")
            return url
        else:
            print(f"Warning: No product found for '{product_name}'.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error searching for '{product_name}': {e}")
        return None

def parse_specifications(soup):
    """Parses the 'TENT DETAILS', 'Material', and 'Manufacturing' sections."""
    specs = {
        "capacity": {"camping": None, "glamping": None},
        "dimensions": None,
        "floor_space": None,
        "internal_area": None,
        "weight": None,
        "doors": None,
        "windows": None,
        "inflation_time": None,
        "material_details": [],
        "manufacturing_country": None
    }
    for item in soup.select('.vc_tta-panel-body .wd-list li .list-content'):
        text = item.get_text(separator=" ", strip=True)
        if ':' in text:
            key, value = text.split(':', 1)
            key, value = key.strip(), value.strip()
            
            if "Camping Capacity" in key:
                match = re.search(r'\d+', value)
                if match: specs["capacity"]["camping"] = int(match.group())
            elif "Glamping Capacity" in key:
                match = re.search(r'\d+', value)
                if match: specs["capacity"]["glamping"] = int(match.group())
            elif "Tent Dimensions" in key: specs["dimensions"] = value
            elif "Floor Space" in key: specs["floor_space"] = value
            elif "Internal Usable Area" in key: specs["internal_area"] = value
            elif "Package Weight" in key: specs["weight"] = value
            elif "Doors" in key and "Lock" not in key:
                match = re.search(r'\d+', value)
                if match: specs["doors"] = int(match.group())
            elif "Windows" in key:
                match = re.search(r'\d+', value)
                if match: specs["windows"] = int(match.group())
            elif "Inflating Time" in key: specs["inflation_time"] = value
            elif "Country Of Manufacture" in key: specs["manufacturing_country"] = value
            else: specs["material_details"].append(f"{key}: {value}")
    return specs

def scrape_product_page(url, target_name, accessories_data):
    """
    Scrapes a single product page and uses the local JSON for accessories.
    """
    print(f"Scraping page: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        time.sleep(1)
        soup = BeautifulSoup(response.text, 'html.parser')

        product_data = {
            "name": target_name,
            "url": url,
            "colors": [],
            "key_features": [],
            "benefits": [],
            "included_accessories": accessories_data.get(target_name, [])
        }

        # Get colors and variations
        variations_form = soup.select_one('form.variations_form')
        if variations_form and 'data-product_variations' in variations_form.attrs:
            variations_json = json.loads(variations_form['data-product_variations'])
            for variation in variations_json:
                color_name = "N/A"
                attributes = variation.get('attributes', {})
                if 'attribute_pa_colour' in attributes:
                    color_name = attributes['attribute_pa_colour'].replace('-', ' ').title()
                elif 'attribute_pa_top-color' in attributes:
                    color_name = attributes['attribute_pa_top-color'].replace('-', ' ').title()
                product_data['colors'].append({
                    "color": color_name,
                    "price": float(variation.get('display_price', 0)),
                    "sku": variation.get('sku', '') 
                })
        
        # Get specifications
        specs = parse_specifications(soup)
        product_data.update(specs)
        
        # *** CORRECTED KEY FEATURES LOGIC ***
        # 1. Find the link to the "FEATURES" tab to get its target ID
        features_link = soup.find('a', string=re.compile(r'\bfeatures\b', re.IGNORECASE))
        if features_link and features_link.has_attr('href'):
            # 2. Get the panel ID from the link's href attribute
            panel_id = features_link['href'].lstrip('#')
            features_panel = soup.find('div', id=panel_id)

            if features_panel:
                # 3. Find all <strong> tags within that specific panel
                strong_tags = features_panel.select('strong, b')
                for tag in strong_tags:
                    feature_text = tag.get_text(strip=True).split('–')[0].strip().replace(':', '')
                    
                    # 4. Apply filters to get only the feature titles
                    if text and len(text) > 4 and 'patented design' not in text.lower() and '(extra option)' not in text.lower() and 'carry bag' not in text.lower() and 'repair kit' not in text.lower():
                        if feature_text not in product_data['key_features']:
                            product_data['key_features'].append(feature_text)

        # Get Benefits
        benefits_section = soup.find('h4', string=re.compile(r'product benefits', re.IGNORECASE))
        if benefits_section:
            container = benefits_section.find_parent('div', class_='wpb_wrapper')
            if container:
                for benefit in container.select('.info-box-title'):
                    product_data['benefits'].append(benefit.get_text(strip=True))

        return product_data

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not scrape {url}. Reason: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while processing {url}: {e}")
        return None


if __name__ == "__main__":
    target_products = [
        "Air Bushcraft Premium", "London Prestige (S)", "London Prestige (M)",
        "London 360 Discover M", "London Family", "London 360",
        "London 360 Discover", "Air Bungalow", "Air Aquila",
        "Aero Cabin", "Air Capsule", "London Maxia 480","SÖNMEZ FLOATING TENT"
    ]

    all_products_data = []

    try:
        with open('products_with_included_accesories.json', 'r', encoding='utf-8') as f:
            accessories_lookup = json.load(f)
    except FileNotFoundError:
        print("FATAL ERROR: `products_with_included_accesories.json` not found. Please create it first.")
        exit()

    print("Scraper starting...")
    for product_name in target_products:
        product_url = find_product_url(product_name)
        if product_url:
            product_details = scrape_product_page(product_url, product_name, accessories_lookup)
            if product_details:
                all_products_data.append(product_details)
        print("-" * 20)
    
    output_file = 'structured_tent_products.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_products_data, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ Scraping complete!")
    print(f"Data for {len(all_products_data)} products saved to {output_file}")