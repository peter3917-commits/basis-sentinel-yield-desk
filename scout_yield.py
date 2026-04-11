import os
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- 🏛️ INSTITUTIONAL DATA FETCH ---
def fetch_mexc_data():
    assets = ['BTC', 'ETH', 'SOL', 'XRP', 'XLM', 'HBAR']
    results = []
    
    for asset in assets:
        symbol = f"{asset}_USDT"
        # MEXC API for Contract/Futures data
        url = f"https://contract.mexc.com/api/v1/contract/detail?symbol={symbol}"
        try:
            response = requests.get(url).json()
            if response['success']:
                data = response['data']
                results.append({
                    'staff': 'Scout_Yield',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'asset': asset,
                    'mark_price': data['lastPrice'],
                    'index_price': data['indexPrice'],
                    'funding_rate': data['fundingRate'],
                    'basis_gap': float(data['lastPrice']) - float(data['indexPrice'])
                })
        except Exception as e:
            print(f"Error fetching {asset}: {e}")
    return results

# --- 🔑 VAULT CONNECTION ---
def update_ledger(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Load secrets from environment
    creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open the ledger
    sheet = client.open_by_key(os.getenv("GSHEET_ID")).worksheet("LIVE_TAPE")
    
    # Convert to list of lists for gspread
    df = pd.DataFrame(data)
    sheet.append_rows(df.values.tolist())
    print("Ledger updated successfully.")

# --- 🚀 EXECUTION ---
if __name__ == "__main__":
    market_data = fetch_mexc_data()
    if market_data:
        update_ledger(market_data)
