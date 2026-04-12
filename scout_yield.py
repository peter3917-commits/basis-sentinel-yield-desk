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
        # Using the v1 contract detail endpoint
        url = f"https://contract.mexc.com/api/v1/contract/detail?symbol={symbol}"
        try:
            response = requests.get(url, timeout=10).json()
            
            # Audit the structure
            if response.get('success') and 'data' in response:
                d = response['data']
                
                # Resilient key checking
                price = d.get('lastPrice') or d.get('last_price') or d.get('indexPrice')
                funding = d.get('fundingRate') or d.get('funding_rate', 0)
                
                if price is not None:
                    entry = {
                        'staff': 'Scout_Yield',
                        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        'asset': asset,
                        'mark_price': float(price),
                        'index_price': float(d.get('indexPrice', price)),
                        'funding_rate': float(funding),
                        'basis_gap': float(price) - float(d.get('indexPrice', price))
                    }
                    results.append(entry)
                    print(f"✅ Captured {asset}: Price {price} | Funding {funding}")
                else:
                    print(f"⚠️ Data missing for {asset}: {d}")
            else:
                print(f"❌ MEXC Error for {asset}: {response.get('message', 'Unknown Error')}")
                
        except Exception as e:
            print(f"❌ Connection/Parsing Error for {asset}: {str(e)}")
            
    print(f"--- 🛰️ SCOUT FINISHED: {len(results)} assets captured ---")
    return results

def update_ledger(data):
    if not data:
        print("❌ No data captured. GSheets update skipped.")
        return

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        worksheet = ledger.worksheet("LIVE_TAPE")
        
        rows = [[v for v in d.values()] for d in data]
        worksheet.append_rows(rows)
        print(f"✅ SUCCESSFULLY FILED {len(rows)} ROWS TO THE LEDGER.")
        
    except Exception as e:
        print(f"❌ GOOGLE SHEETS ERROR: {e}")

if __name__ == "__main__":
    market_data = fetch_mexc_data()
    update_ledger(market_data)
