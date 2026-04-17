import os
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# 🏛️ V3 INSTITUTIONAL SETTINGS
STATE_FILE = "vault_states.json"
TOLL_RATE = 0.0008     # 0.08% Toll (Fees + Slippage)
EXIT_THRESHOLD = -0.0005  # Eject if funding < -0.05%
ENTRY_THRESHOLD = 0.0001 # Re-enter if funding > +0.01%

def load_states():
    """Reads the 'Memory' of which coins are Active (1) or Ejected (0)."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    # Default fallback: All assets Active
    return {a: 1 for a in ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']}

def log_transaction(ledger, asset, action, reason):
    """Fires a record to the TRANSACTION_LOG for the Auditor to see."""
    try:
        sheet = ledger.worksheet("TRANSACTION_LOG")
        # Fee is 0.08% of the £1,166 share per coin (~£0.93 - we use £1.40 as a conservative sandbox toll)
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, asset, action, 1.40, reason])
    except Exception as e:
        print(f"⚠️ Failed to log transaction for {asset}: {e}")

def fetch_and_monitor(states, ledger):
    assets = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
    results = []
    print(f"--- 🛰️ V3 SCOUT START: {datetime.utcnow()} ---")
    
    url = "https://contract.mexc.com/api/v1/contract/ticker"
    
    try:
        response = requests.get(url, timeout=15).json()
        if response.get('success') and 'data' in response:
            ticker_map = {t['symbol']: t for t in response['data']}
            
            for asset in assets:
                symbol = f"{asset}_USDT"
                if symbol in ticker_map:
                    d = ticker_map[symbol]
                    price = float(d.get('lastPrice', 0))
                    index_price = float(d.get('indexPrice', price))
                    funding = float(d.get('fundingRate', 0))
                    gap = price - index_price
                    
                    # 🧠 DECISION ENGINE
                    current_state = states.get(asset, 1)
                    final_state = current_state
                    
                    # 🔴 NEGATIVE EJECTION: High cost to stay in?
                    if current_state == 1 and funding < EXIT_THRESHOLD:
                        final_state = 0
                        log_transaction(ledger, asset, "EJECT", f"Yield {funding:.6f}")
                        print(f"⚠️ EJECTING {asset}: Stop Loss triggered.")
                        
                    # 🟢 BASIS ENTRY FILTER: Is the 'House' price discounted?
                    elif current_state == 0 and funding > ENTRY_THRESHOLD and gap > 0:
                        final_state = 1
                        log_transaction(ledger, asset, "ENTER", f"Basis {gap:.4f}")
                        print(f"✅ RE-ENTERING {asset}: Safe entry conditions met.")

                    states[asset] = final_state

                    results.append({
                        'staff': 'Scout_V3',
                        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        'asset': asset,
                        'mark_price': price,
                        'index_price': index_price,
                        'funding_rate': funding,
                        'basis_gap': gap,
                        'is_active': final_state # 🛡️ This tells the Auditor what to count
                    })
        
        # Save memory locally (GitHub Action will commit this)
        with open(STATE_FILE, "w") as f:
            json.dump(states, f)

    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
    
    return results

def update_live_tape(ledger, data):
    if not data: return
    try:
        worksheet = ledger.worksheet("LIVE_TAPE")
        rows = [[v for v in d.values()] for d in data]
        worksheet.append_rows(rows)
        print(f"✅ V3 LEDGER UPDATED.")
    except Exception as e:
        print(f"❌ GOOGLE SHEETS ERROR: {e}")

if __name__ == "__main__":
    # Standard GSheets Auth
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    ledger = client.open_by_key(os.getenv("GSHEET_ID"))

    # Execute Intelligence Loop
    vault_memory = load_states()
    market_intel = fetch_and_monitor(vault_memory, ledger)
    update_live_tape(ledger, market_intel)
