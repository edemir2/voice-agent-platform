import json
import os

def load_tent_products():
    with open("structured_tent_products.json", "r") as f:
        return json.load(f)

def load_accessories():
    with open("scraped_accessories.json", "r") as f:
        return json.load(f)
