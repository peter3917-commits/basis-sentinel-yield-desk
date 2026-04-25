import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# 🏛️ INSTITUTIONAL SETTINGS (2026 UK Spec)
STARTING_CAPITAL = 10000.00
ONBOARDING_TOLL = 12.00    # Bank Transfer + MEXC On-ramp
CGT_ALLOWANCE = 3000.00     # 2026/27 UK Annual Allowance
CGT_RATE = 0.18             # Basic Rate (18%)
FRICTION_FACTOR = 0.10      # Maintenance friction (10% of yield)

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
        
        # 🏛️ CHRONOLOGICAL FIX: Ensure we find the REAL latest balance
        if not payout_data:
            current_balance = STARTING_CAPITAL - ONBOARDING_TOLL
            print(f"📦 INITIALIZING: £{current_balance}")
        else:
            p_df = pd.DataFrame(payout_data)
            p_df['timestamp'] = pd.to_datetime(p_df['timestamp'])
            # Sort to find the actual latest entry regardless of Sheet order
            p_df = p_df.sort_values('timestamp', ascending=True)
            current_balance = float(p_df['new_balance'].iloc[-1])
            print(f"🔎 Current Ledger Balance: £{current_balance}")

        active_capital = current_balance * 0.70  
        
        # Pull Live Tape & Transaction Log
        tape_df = pd.DataFrame(ledger.worksheet("LIVE_TAPE").get_all_records())
        tx_df = pd.DataFrame(ledger.worksheet("TRANSACTION_LOG").get_all_records())
        
        target_assets = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
        
        # 🛡️ YIELD CALCULATION
        avg_funding = 0
        if not tape_df.empty:
            tape_df['timestamp'] = pd.to_datetime(tape_df['timestamp'])
            # Filter for assets and only 'Active' (not shielded) positions
            active_pings = tape_df[(tape_df['asset'].isin(target_assets)) & (tape_df['is_active'] == 1)]
            
            if not active_pings.empty:
                # Get the average of the most recent active rates
                latest_rates = active_pings.sort_values('timestamp').groupby('asset').last()
                avg_funding = latest_rates['funding_rate'].astype(float).mean()
        
        # 1. Gross Gain
        gross_payout = active_capital * avg_funding
        
        # 2. Extract Ejection Fees (The £7.00 Debt recovery)
        recent_fees = 0
        if not tx_df.empty:
            tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
            # Check for any tolls in the last 12 hours that haven't been 'audited' yet
            cutoff = datetime.utcnow() - timedelta(hours=12)
            recent_fees = tx_df[tx_df['timestamp'] > cutoff]['toll_paid'].astype(float).sum()

        # 3. Final Net Profit/Loss
        # Friction only applies if there was actual yield; fees apply always.
        total_overhead = (abs(gross_payout) * FRICTION_FACTOR) + recent_fees
        net_payout = gross_payout - total_overhead
        new_balance = current_balance + net_payout
        
        # --- 🧾 FILING THE LEDGER ---
        # We ALWAYS file now, even if yield is 0, to show the app is alive
        audit_entry = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            round(avg_funding, 8),
            round(gross_payout, 4),
            round(total_overhead, 4), 
            round(new_balance, 4)   
        ]
        
        # Append to the bottom (Professional standard)
        payout_sheet.append_row(audit_entry)
        print(f"✅ V3 Audit Filed. Net: £{net_payout:.2f} | New Balance: £{new_balance:.2f}")

    except Exception as e:
        print(f"❌ V3 Audit Critical Error: {e}")

if __name__ == "__main__":
    run_audit()
