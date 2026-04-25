import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

def run_audit():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        
        payout_sheet = ledger.worksheet("BASIS_PAYOUT_LOG")
        p_df = pd.DataFrame(payout_sheet.get_all_records())
        
        if p_df.empty:
            current_balance = 9988.00 # 10k minus onboarding
        else:
            p_df['timestamp'] = pd.to_datetime(p_df['timestamp'])
            current_balance = float(p_df.sort_values('timestamp')['new_balance'].iloc[-1])

        # Calc Yield
        tape_df = pd.DataFrame(ledger.worksheet("LIVE_TAPE").get_all_records())
        tx_df = pd.DataFrame(ledger.worksheet("TRANSACTION_LOG").get_all_records())
        
        active_pings = tape_df[tape_df['is_active'] == 1]
        avg_funding = active_pings['funding_rate'].astype(float).mean() if not active_pings.empty else 0
        
        gross_payout = (current_balance * 0.70) * avg_funding
        
        # Fee Recovery: Look for tolls in last 48 hours not yet audited
        recent_fees = 0
        if not tx_df.empty:
            tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
            # Since the auditor stopped 2 days ago, we look back 50 hours
            cutoff = datetime.utcnow() - timedelta(hours=50)
            # Filter for fees that haven't been accounted for yet
            recent_fees = tx_df[tx_df['timestamp'] > cutoff]['toll_paid'].astype(float).sum()

        net_payout = gross_payout - (abs(gross_payout) * 0.10) - recent_fees
        new_balance = current_balance + net_payout
        
        # 🧾 FORCE ENTRY: Even if net_payout is negative/zero
        audit_entry = [datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 
                       round(avg_funding, 8), round(gross_payout, 4), 
                       round(recent_fees, 4), round(new_balance, 4)]
        
        payout_sheet.append_row(audit_entry)
        print(f"✅ Audit Synchronized. New Balance: £{new_balance}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_audit()
