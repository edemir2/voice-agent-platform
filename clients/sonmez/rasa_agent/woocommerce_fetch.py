import requests
from requests.auth import HTTPBasicAuth
import json

#WooCommerce API credentials
consumer_key = "ck_38c8f9d651789093eace11a982d19acf074465d5"
consumer_secret = "cs_ee743c16b0234c765db69be727941b9402576387"

url = "https://sonmezoutdoor.us/wp-json/wc/v3/products"

response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret))

if response.status_code == 200:
    products = response.json()
    with open("woocommerce_products.json", "w") as f:
        json.dump(products, f, indent=2)
    print("✅ Products saved to woocommerce_products.json")
else:
    print("❌ Failed:", response.status_code, response.text)
