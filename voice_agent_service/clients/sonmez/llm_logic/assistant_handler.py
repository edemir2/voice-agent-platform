import os
from openai import OpenAI

def build_prompt_and_context(user_input, mentioned_product, product_list):
    if mentioned_product:
        # Expert mode
        system_prompt = (
            "You are a product expert. A customer is asking about a specific product. "
            "Using only the detailed information provided, answer their question naturally and concisely. "
            "If the answer isn't in the details, say you don't have that specific information."
        )

        keywords_to_find = ["Fabric:", "Cold Resistance:", "High Temperature:",
                            "Sun Protection Factor:", "Wind Resistance:", "Dimensions:"]
        details_to_include = [
            f"- {d.strip()}" for d in mentioned_product.get("material_details", [])
            if any(k in d for k in keywords_to_find)
        ]

        context = (
            f"Answering questions about: {mentioned_product['name']}\n"
            "Key Details:\n" + "\n".join(details_to_include)
        ) if details_to_include else "No specific material details available."

    else:
        # Friendly general responder
        system_prompt = (
            "You are a friendly greeter for Sönmez Outdoor. You can answer general questions or list the available products. "
            "Keep your answers brief and encourage the user to ask about a specific model."
        )
        product_names = [product['name'] for product in product_list]
        context = "The available tent models are: " + ", ".join(product_names) + "."

    return system_prompt, context


def run_assistant(user_input, mentioned_product, product_list):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # ✅ Delayed until .env is loaded

    system_prompt, context = build_prompt_and_context(user_input, mentioned_product, product_list)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": context},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content.strip() if response else "I'm having trouble responding right now."
