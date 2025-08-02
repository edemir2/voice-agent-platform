import pandas as pd
import openai
import os
import time
from dotenv import load_dotenv

# --- Load Environment Variables for the API Key ---
load_dotenv()
try:
    openai.api_key = os.getenv("OPENAI_API_KEY") 
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file.")
except Exception as e:
    print(f"❌ Error setting up OpenAI: {e}")
    exit()


def get_country_with_ai(company_info_text):
    """Uses AI to infer the country of origin from company details."""
    if not company_info_text:
        return "Unknown"

    prompt = f"""
    You are a geopolitical and business analyst. Based on the following information about a company, infer its most likely country of origin.
    Consider the company name, top-level domain of the email (.com, .vn, .qa), address details, and any other clues.
    Provide ONLY the country name as a single string (e.g., "United States", "Qatar", "Vietnam"). If you absolutely cannot determine the country, return "Unknown".

    Company Information:
    ---
    {company_info_text}
    ---
    Country:
    """

    try:
        print(f"🤖 Analyzing for country: {company_info_text.splitlines()[0]}")
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert business analyst who only responds with a single country name."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=20
        )
        country = response.choices[0].message.content.strip()
        return country
    except Exception as e:
        print(f"❌ Error during AI country detection: {e}")
        return "Error"

# --- Main Analysis Function ---
def main():
    """Main function to load, enrich, sort, and save the data."""
    input_filename = 'dealership_data.csv'
    output_filename = 'sorted_and_enriched_dealers.xlsx'

    try:
        df = pd.read_csv(input_filename)

        print("--- DEBUGGING INFO ---")
        print(f"Pandas loaded {len(df.columns)} columns.")
        print("----------------------")
        # Rename columns to be more script-friendly (remove spaces, etc.)
        df.columns = ['Company', 'Contact_Name', 'Position', 'Email', 'Experience', 'Phone']
    except FileNotFoundError:
        print(f"❌ Error: '{input_filename}' not found. Make sure you downloaded it to the correct folder.")
        return

    # --- 1. Add 'Country' column if it doesn't exist ---
    if 'Country' not in df.columns:
        df['Country'] = None # Initialize with empty values

    # --- 2. Clean up the 'Experience' Column ---
    df['Experience'] = df['Experience'].astype(str)
    df['Experience_Years'] = df['Experience'].str.extract(r'(\d+)').astype(float)
    df['Experience_Years'] = df['Experience_Years'].fillna(0)

    # --- 3. Identify Country for each row if not already done ---
    for index, row in df.iterrows():
        # Only process rows where the country is not yet filled in
        if pd.isna(row['Country']) or row['Country'] is None:
            # Combine info to give the AI context
            info_text = f"Company: {row['Company']}\nContact: {row['Contact_Name']}\nEmail: {row['Email']}"
            
            country = get_country_with_ai(info_text)
            df.loc[index, 'Country'] = country
            time.sleep(5) # Pause between AI calls to avoid rate limits

    print("\n✅ Country analysis complete.")

    # --- 4. Sort by Experience (Descending) ---
    print("Sorting data by experience...")
    sorted_df = df.sort_values(by='Experience_Years', ascending=False)
    
    # --- 5. Save the final report to an Excel file ---
    # We select the columns we want in the final report
    final_columns = ['Company', 'Contact_Name', 'Position', 'Email', 'Country', 'Experience_Years', 'Phone']
    sorted_df[final_columns].to_excel(output_filename, index=False)

    print(f"\n🎉 Success! Your sorted and enriched data has been saved to '{output_filename}'")

if __name__ == "__main__":
    main()