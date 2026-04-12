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
    
    # 🏛️ NEW ENDPOINT: Ticker data carries the live prices and funding
    url = "https://contract.mexc.com/api/v1/contract/ticker"
    
    try:
        response = requests.get(url, timeout=15).json()
        
        if response.get('success') and 'data' in response:
            all_tickers = response['data']
            
            # Map the tickers to a dictionary for fast lookup
            ticker_map = {t['symbol']: t for t in all_tickers}
            
            for asset in assets:
                symbol = f"{asset}_USDT"
                if symbol in ticker_map:
                    d = ticker_map[symbol]
                    
                    # Surgical data extraction
                    price = float(d.get('lastPrice', 0))
                    index_price = float(d.get('indexPrice', price))
                    funding = float(d.get('fundingRate', 0))
                    
                    entry = {
                        'staff': 'Scout_Yield',
                        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        'asset': asset,
                        'mark_price': price,
                        'index_price': index_price,
                        'funding_rate': funding,
                        'basis_gap': price - index_price
                    }
                    results.append(entry)
                    print(f"✅ Captured {asset}: ${price:,.2f} | Funding: {funding:.6f}")
                else:
                    print(f"⚠️ Symbol {symbol} not found in ticker list.")
        else:
            print(f"❌ MEXC API Error: {response.get('message', 'No data in response')}")
            
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
            
    print(f"--- 🛰️ SCOUT FINISHED: {len(results)} assets captured ---")
    return results

def update_ledger(data):
    if not data:
        print("❌ No data captured. Skipping Google Sheets update.")
        return

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        worksheet = ledger.worksheet("LIVE_TAPE")
        
        # Format for gspread
        rows = [[v for v in d.values()] for d in data]
        worksheet.append_rows(rows)
        print(f"✅ SUCCESSFULLY FILED {len(rows)} ROWS TO THE LEDGER.")
        
    except Exception as e:
        print(f"❌ GOOGLE SHEETS ERROR: {e}")

if __name__ == "__main__":
    market_data = fetch_mexc_data()
    update_ledger(market_data)
