import pandas as pd
import numpy as np


file_path = 'dealership_data.csv' 

try:
    # 2. Read the data from the CSV file into a DataFrame.
    df = pd.read_csv(file_path)


    # df.columns = ['Company', 'Contact Name', 'Position', 'Contact Email', 'Country', 'Experience', 'Contact Phone']

    # 3. Replace 'Unknown' in the 'Country' column to handle sorting.
    # Using `.loc` is a robust way to avoid warnings.
    df.loc[df['Country'] == 'Unknown', 'Country'] = np.nan

    # 4. Group and sort the DataFrame.
    # The logic remains the same: sort by country, then by experience (descending).
    df_sorted = df.sort_values(
        by=['Country', 'Experience'], 
        ascending=[True, False],
        na_position='last'
    )

    # 5. Print the entire sorted DataFrame.
    print("--- Sorted Data ---")
    print(df_sorted.to_string())

    # Optional: Save the sorted data to a new CSV file 
    df_sorted.to_csv('sorted_contacts.csv', index=False)
    print("\nSorted data has been saved to sorted_contacts.csv")


except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found. Please check the file name and path.")
except KeyError as e:
    print(f"Error: A required column was not found in the file: {e}. Please check your CSV's column headers.")