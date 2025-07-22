import requests
from bs4 import BeautifulSoup
import json
import re
import time

def get_product_urls(category_url):
    """
    Crawls a category, including all its paginated pages, to find all product URLs.
    """
    product_urls = set()
    page_number = 1
    
    while True:
        # Append / to the end of the URL if it's not there
        if not category_url.endswith('/'):
            category_url += '/'
            
        paginated_url = f"{category_url}page/{page_number}/"
        print(f"Crawling category page: {paginated_url}")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(paginated_url, headers=headers, timeout=15)
            
            if response.status_code == 404:
                print("Last page reached for this category.")
                break
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links_found = soup.select('div.product-grid-item a.product-image-link')
            
            if not links_found:
                print("No more products found on this page, stopping category crawl.")
                break

            for link in links_found:
                url = link.get('href')
                if url:
                    product_urls.add(url)
            
            page_number += 1
            time.sleep(1) # Be polite to the server

        except requests.exceptions.RequestException as e:
            print(f"Error fetching category page {paginated_url}: {e}")
            break
            
    return list(product_urls)

def scrape_accessory_page(url):
    """
    Scrapes a single product page for general accessory/stove details.
    """
    print(f"  -> Scraping product: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        time.sleep(1)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Initialize data dictionary with default values
        data = {
            "name": None,
            "url": url,
            "price": None,
            "sku": None,
            "category": None,
            "description": None,
            "image_url": None
        }

        # Extract Name
        if soup.select_one('h1.product_title'):
            data['name'] = soup.select_one('h1.product_title').get_text(strip=True)

        # Extract Price
        price_element = soup.select_one('p.price .amount bdi')
        if price_element:
            price_text = price_element.get_text(strip=True).replace('$', '').replace(',', '')
            try:
                data['price'] = float(price_text)
            except ValueError:
                print(f"    Warning: Could not convert price '{price_text}' to a number.")

        # Extract SKU
        if soup.select_one('.sku'):
            data['sku'] = soup.select_one('.sku').get_text(strip=True)

        # Extract Category from breadcrumbs
        if soup.select_one('.woocommerce-breadcrumb a:last-of-type'):
            data['category'] = soup.select_one('.woocommerce-breadcrumb a:last-of-type').get_text(strip=True)

        # Extract a brief description
        desc_element = soup.select_one('.woocommerce-product-details__short-description p')
        if not desc_element: # Fallback selector
             desc_element = soup.select_one('.product_meta + p')
        if desc_element:
            data['description'] = desc_element.get_text(strip=True)

        # Extract Main Image URL
        if soup.select_one('.woocommerce-product-gallery__image a'):
            data['image_url'] = soup.select_one('.woocommerce-product-gallery__image a')['href']

        return data

    except requests.exceptions.RequestException as e:
        print(f"    ERROR: Could not scrape {url}. Reason: {e}")
        return None
    except Exception as e:
        print(f"    ERROR: An unexpected error occurred while processing {url}: {e}")
        return None

if __name__ == "__main__":
    target_categories = [
        "https://sonmezoutdoor.us/product-category/tent-accessories/",
        "https://sonmezoutdoor.us/product-category/camping-equipment-outdoor-materials/camping-stove-equipment/",
        "https://sonmezoutdoor.us/product-category/camping-equipment-outdoor-materials/camping-stoves/"
    ]

    all_products = []
    processed_urls = set()

    print("Accessory scraper starting...")
    
    for category in target_categories:
        print("\n" + "="*50)
        print(f"Processing Category: {category}")
        print("="*50)
        
        product_urls = get_product_urls(category)
        print(f"Found {len(product_urls)} product links in this category.")
        
        for url in product_urls:
            if url not in processed_urls:
                processed_urls.add(url)
                details = scrape_accessory_page(url)
                if details:
                    all_products.append(details)
            else:
                print(f"  -> Skipping already processed URL: {url}")
    
    # Save the final structured data
    output_file = 'scraped_accessories.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ Scraping complete!")
    print(f"Data for {len(all_products)} unique products saved to {output_file}")