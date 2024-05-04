import streamlit as st
import pandas as pd
import requests
import requests
import concurrent.futures

API_KEY = ''

prompt = f"""
You are a skilled accountant. 
Determine the closest matching account type for each account below. 
If there is no matching type, name it 'Not an Account type'. 

The possible types are:
1. Asset - Bank Accounts
2. Asset - Cash
3. Asset - Current Asset
4. Asset - Fixed Asset
5. Asset - Inventory
6. Asset - Non-current Asset
7. Equity - Shareholders Equity
8. Expense - Direct Costs
9. Expense - Operating Expense
10. Expense - Other Expense
11. Liability - Current Liability
12. Liability - Non-current Liability
13. Revenue - Operating Revenue
14. Revenue - Other Revenue

For each bank account, return only mapped account type.
An example of the format is within the three backticks:
```
Expense - Operating Expense
Expense - Other Expense
Expense - Direct Costs
# Add more if there are more than 3 bank accounts given. 
```
Do not add additional words. If there are 15 bank accounts given, you must return exactly 15 mapped account types. 
"""

def classify_account_types(account_names, batch_size=15):
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
    }
    results = [None] * len(account_names)  

    def process_batch(start_index):
        end_index = min(start_index + batch_size, len(account_names))
        batch = account_names[start_index:end_index]
        messages = [{
            'role': 'system',
            'content': prompt
        }]
        for name in batch:
            messages.append({
                'role': 'user',
                'content': f"Account name: {name}"
            })

        data = {
            "model": "gpt-4-turbo",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1000
        }

        try:
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
            response.raise_for_status()
            response_json = response.json()
            content = response_json['choices'][0]['message']['content']
            content = content.strip("```").strip()
            batch_results = [line.strip() for line in content.split('\n')]

            if len(batch_results) != len(batch):
                print("batch: ", batch)
                print("batch results: ", batch_results)
                raise ValueError(f"Expected {len(batch)} results, but got {len(batch_results)}")
        except (requests.exceptions.RequestException, ValueError, IndexError) as e:
            print(f"Error processing batch: {e}")
            batch_results = ["Error in classification"] * len(batch)  

        results[start_index:end_index] = batch_results

    with concurrent.futures.ThreadPoolExecutor() as executor:
        indices = range(0, len(account_names), batch_size)
        executor.map(process_batch, indices)

    return results


def process_trial_balance(file):
    trial_balance_data = pd.read_excel(file)
    trial_balance_cleaned = trial_balance_data.iloc[4:].dropna(axis=1, how='all')
    trial_balance_cleaned.columns = ['Account', 'Debit', 'Credit']
    trial_balance_cleaned[['Account Code', 'Account Name']] = trial_balance_cleaned['Account'].str.extract(r'(\d+(?:\.\d+)*)\s+(.*)')
    trial_balance_cleaned = trial_balance_cleaned.drop(columns=['Account'])
    trial_balance_cleaned = trial_balance_cleaned.dropna(subset=['Account Code', 'Account Name'])
    
    account_names = trial_balance_cleaned['Account Name'].tolist()
    account_types = classify_account_types(account_names)
    trial_balance_cleaned['Account Type'] = account_types
    
    trial_balance_cleaned['Status'] = 'Active'
    trial_balance_cleaned['Unique ID'] = ''
    
    final_data = trial_balance_cleaned[['Account Type', 'Account Name', 'Account Code', 'Status', 'Unique ID']]
    return final_data

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

st.title('Trial Balance to COA Mapping Tool')

uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    processed_data = process_trial_balance(uploaded_file)
    st.write("Processed Data", processed_data)
    csv = convert_df_to_csv(processed_data)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='mapped_coa.csv',
        mime='text/csv',
    )
