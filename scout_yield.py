import os
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

def fetch_mexc_data():
    assets = ['BTC', 'ETH', 'SOL', 'XRP', 'XLM', 'HBAR']
    results = []
    print(f"--- 🛰️ SCOUT START: {datetime.utcnow()} ---")
    
    for asset in assets:
        symbol = f"{asset}_USDT"
        url = f"https://contract.mexc.com/api/v1/contract/detail?symbol={symbol}"
        try:
            response = requests.get(url, timeout=10).json()
            if response.get('success'):
                data = response['data']
                entry = {
                    'staff': 'Scout_Yield',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'asset': asset,
                    'mark_price': str(data['lastPrice']),
                    'index_price': str(data['indexPrice']),
                    'funding_rate': float(data['fundingRate']),
                    'basis_gap': float(data['lastPrice']) - float(data['indexPrice'])
                }
                results.append(entry)
                print(f"✅ Fetched {asset}: {data['lastPrice']}")
            else:
                print(f"⚠️ MEXC rejected {asset}: {response.get('message')}")
        except Exception as e:
            print(f"❌ Connection Error for {asset}: {e}")
            
    print(f"--- 🛰️ SCOUT FINISHED: {len(results)} assets captured ---")
    return results

def update_ledger(data):
    if not data:
        print("❌ No data to write. Aborting GSheets update.")
        return

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Open by ID
        sheet_id = os.getenv("GSHEET_ID")
        ledger = client.open_by_key(sheet_id)
        worksheet = ledger.worksheet("LIVE_TAPE")
        
        print(f"🚀 Connected to Ledger: {ledger.title}")
        
        # Convert to List of Lists
        rows_to_append = [[val for val in entry.values()] for entry in data]
        
        # APPEND
        worksheet.append_rows(rows_to_append)
        print(f"✅ SUCCESSFULLY APPENDED {len(rows_to_append)} ROWS TO GOOGLE SHEETS.")
        
    except Exception as e:
        print(f"❌ GOOGLE SHEETS ERROR: {e}")

if __name__ == "__main__":
    market_data = fetch_mexc_data()
    update_ledger(market_data)
