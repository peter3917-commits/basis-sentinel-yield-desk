import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

# 🏛️ INSTITUTIONAL FRICTION SETTINGS
FRICTION_FACTOR = 0.10 

def run_audit():
    try:
        # --- 🔑 AUTHENTICATION ---
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        
        # --- 📊 DATA COLLECTION ---
        payout_sheet = ledger.worksheet("BASIS_PAYOUT_LOG")
        payout_data = payout_sheet.get_all_records()
        
        # Starting Capital Logic (£10,000 baseline)
        current_balance = float(payout_data[-1]['new_balance']) if payout_data else 10000.00
        active_capital = current_balance * 0.70  
        
        tape_sheet = ledger.worksheet("LIVE_TAPE")
        tape_df = pd.DataFrame(tape_sheet.get_all_records())
        
        if tape_df.empty:
            print("❌ Auditor: No tape data found. Aborting.")
            return

        # 🏛️ UPDATED ASSET BASKET: Re-aligning with the High-Velocity Scout
        target_assets = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
        
        # Filter tape for ONLY our current basket and get latest rates
        filtered_tape = tape_df[tape_df['asset'].isin(target_assets)]
        
        if filtered_tape.empty:
            print("❌ Auditor: No valid asset data found for current basket. Check Scout.")
            return

        latest_rates = filtered_tape.sort_values('timestamp').groupby('asset').last()
        avg_funding = latest_rates['funding_rate'].astype(float).mean()
        
        # --- 📈 THE NET COMPOUNDING MATH ---
        # 1. Calculate Gross Gain
        gross_payout = active_capital * avg_funding
        
        # 2. Calculate Slippage/Fees
        slippage_cost = gross_payout * FRICTION_FACTOR
        
        # 3. Final Net Profit
        net_payout = gross_payout - slippage_cost
        
        # 4. New Vault Total
        new_balance = current_balance + net_payout
        
        # --- 🧾 FILING THE LEDGER ---
        audit_entry = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            round(avg_funding, 8),
            round(gross_payout, 4),
            round(slippage_cost, 4), 
            round(new_balance, 4)   
        ]
        
        payout_sheet.append_row(audit_entry)
        print(f"✅ Audit Successful for {target_assets}")
        print(f"✅ Net: £{net_payout:.4f} | Avg Funding: {avg_funding:.6f}")

    except Exception as e:
        print(f"❌ Audit Critical Error: {e}")

if __name__ == "__main__":
    run_audit()
