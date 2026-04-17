import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

# 🏛️ INSTITUTIONAL SETTINGS (2026 UK Spec)
STARTING_CAPITAL = 10000.00
ONBOARDING_TOLL = 12.00    # Bank Transfer + MEXC On-ramp
CGT_ALLOWANCE = 3000.00     # 2026/27 UK Annual Allowance
CGT_RATE = 0.18             # Basic Rate (18%) as of April 2026
FRICTION_FACTOR = 0.10      # Maintenance friction for active capital

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
        
        # INITIALIZATION LOGIC
        if not payout_data:
            current_balance = STARTING_CAPITAL - ONBOARDING_TOLL
            print(f"📦 INITIALIZING VAULT: £{current_balance} (After £12 Gas/Onboarding)")
        else:
            current_balance = float(payout_data[-1]['new_balance'])

        active_capital = current_balance * 0.70  
        
        # Pull the Live Tape
        tape_sheet = ledger.worksheet("LIVE_TAPE")
        tape_df = pd.DataFrame(tape_sheet.get_all_records())
        
        # Pull the Transaction Log (To find Ejection Fees)
        tx_sheet = ledger.worksheet("TRANSACTION_LOG")
        tx_df = pd.DataFrame(tx_sheet.get_all_records())
        
        target_assets = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
        
        # 🛡️ FILTER: Only audit 'Active' assets from the last 8 hours
        # In V3, we only calculate yield for coins the Scout didn't eject
        if not tape_df.empty:
            filtered_tape = tape_df[tape_df['asset'].isin(target_assets)]
            # We filter for only the 'Active' pings
            active_pings = filtered_tape[filtered_tape['is_active'] == 1]
            
            if active_pings.empty:
                avg_funding = 0
                print("⚠️ No active assets found in this window. Yield is 0.")
            else:
                latest_rates = active_pings.sort_values('timestamp').groupby('asset').last()
                avg_funding = latest_rates['funding_rate'].astype(float).mean()
        else:
            avg_funding = 0

        # --- 📈 THE NET COMPOUNDING MATH ---
        # 1. Gross Gain
        gross_payout = active_capital * avg_funding
        
        # 2. Extract Ejection Fees from TRANSACTION_LOG
        # (This looks for fees logged by the Scout since the last Auditor run)
        recent_fees = 0
        if not tx_df.empty:
            tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
            # Only count fees from the last 8.5 hours to be safe
            cutoff = pd.Timestamp.utcnow() - pd.Timedelta(hours=8.5)
            recent_fees = tx_df[tx_df['timestamp'] > cutoff]['toll_paid'].sum()

        # 3. Final Net Profit
        total_overhead = (gross_payout * FRICTION_FACTOR) + recent_fees
        net_payout = gross_payout - total_overhead
        new_balance = current_balance + net_payout
        
        # 4. TAX RESERVE CALCULATION (Visual Only)
        total_profit_to_date = new_balance - STARTING_CAPITAL
        taxable_amount = max(0, total_profit_to_date - CGT_ALLOWANCE)
        virtual_tax_reserve = taxable_amount * CGT_RATE
        
        # --- 🧾 FILING THE LEDGER ---
        audit_entry = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            round(avg_funding, 8),
            round(gross_payout, 4),
            round(total_overhead, 4), 
            round(new_balance, 4)   
        ]
        
        payout_sheet.append_row(audit_entry)
        print(f"✅ V3 Audit Complete. Balance: £{new_balance:.2f} | Tax Res: £{virtual_tax_reserve:.2f}")

    except Exception as e:
        print(f"❌ V3 Audit Critical Error: {e}")

if __name__ == "__main__":
    run_audit()
