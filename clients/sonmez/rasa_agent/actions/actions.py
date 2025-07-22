from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import json
import os
import re

# Load data paths
BASE_DIR = os.path.dirname(__file__)
TENT_DATA_PATH = os.path.join(BASE_DIR, "questions_model_faq_with_categories.json")
GENERAL_DATA_PATH = os.path.join(BASE_DIR, "questions_general.json")
ACCESSORY_DATA_PATH = os.path.join(BASE_DIR, "unified_sonmez_accessories.json")
RAW_TENT_LIST_PATH = os.path.join(BASE_DIR, "unified_sonmez_tents.json")

class ActionCheckAvailability(Action):
    def name(self) -> Text:
        return "action_check_availability"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        product_name = tracker.get_slot("product_name")

        if not product_name:
            dispatcher.utter_message(text="Which item are you asking about?")
            return []

        with open(ACCESSORY_DATA_PATH, "r", encoding="utf-8") as f:
            accessories = json.load(f)

        for item in accessories:
            if product_name.lower() in item["name"].lower():
                availability = item.get("availability", "Unknown")
                dispatcher.utter_message(text=f"{item['name']} is currently: {availability}")
                return []

        dispatcher.utter_message(text="I couldn't find that accessory in our catalog.")
        return []

class ActionTentInfo(Action):
    def name(self) -> Text:
        return "action_tent_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List[Dict[Text, Any]]:
        product_name = tracker.get_slot("product_name")
        info_field = tracker.get_slot("info_field")

        if not product_name:
            dispatcher.utter_message(text="Which tent model are you asking about?")
            return []

        with open(TENT_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            if product_name.lower() in entry["model"].lower():
                answer = entry["answer"]
                dispatcher.utter_message(text=f"{entry['question']} → {answer}")
                return []

        dispatcher.utter_message(text="I couldn't find details on that tent.")
        return []

class ActionGeneralQuestion(Action):
    def name(self) -> Text:
        return "action_general_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List[Dict[Text, Any]]:
        query = tracker.latest_message.get("text", "")

        with open(GENERAL_DATA_PATH, "r", encoding="utf-8") as f:
            general_data = json.load(f)

        for entry in general_data["questions"]:
            if entry["question"].lower() in query.lower():
                dispatcher.utter_message(text=entry["answer"])
                return []

        dispatcher.utter_message(text="I'll need to check with the office for that information.")
        return []

class ActionTentByCapacity(Action):
    def name(self) -> Text:
        return "action_tent_by_capacity"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List[Dict[Text, Any]]:
        user_text = tracker.latest_message.get("text", "").lower()

        capacity_map = {
            "single": 1,
            "2": 2,
            "4": 4,
            "6": 6,
            "10": 10,
            "14": 14
        }

        matched = None
        for key in capacity_map.keys():
            if re.search(rf"\b{key}\b", user_text):
                matched = capacity_map[key]
                break

        if not matched:
            dispatcher.utter_message(text="How many people should the tent fit?")
            return []

        with open(RAW_TENT_LIST_PATH, "r", encoding="utf-8") as f:
            tent_data = json.load(f)

        matched_tents = []
        for tent in tent_data:
            category = tent.get("category", "").lower()
            if str(matched) in category:
                matched_tents.append(f"{tent['name']} – ${tent['price']}")

        if matched_tents:
            response = f"Here are our {matched}-person tents:\n" + "\n".join(matched_tents)
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(text=f"Sorry, I couldn’t find any tents for {matched} people.")

        return []