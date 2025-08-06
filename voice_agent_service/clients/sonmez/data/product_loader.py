import json
import os

# Absolute path of the directory this script is in.
script_dir = os.path.dirname(__file__)

def load_tent_products():
    # Solution: Join the script's directory with the filename to create a full, reliable path.
    file_path = os.path.join(script_dir, "structured_tent_products.json")
    with open(file_path, "r") as f:
        return json.load(f)

def load_accessories():
    # ApplIED the same fix here.
    file_path = os.path.join(script_dir, "scraped_accessories.json")
    with open(file_path, "r") as f:
        return json.load(f)