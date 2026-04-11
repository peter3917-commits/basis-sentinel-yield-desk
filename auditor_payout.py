import os
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

def run_audit():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    ledger = client.open_by_key(os.getenv("GSHEET_ID"))
    
    # 1. Check current balance from BASIS_PAYOUT_LOG
    payout_sheet = ledger.worksheet("BASIS_PAYOUT_LOG")
    payout_data = payout_sheet.get_all_records()
    
    # Starting Capital: £10,000 (30% Shield/Margin Pot is £3,000)
    # Active Trading Capital is 70% of the current balance
    current_balance = float(payout_data[-1]['new_balance']) if payout_data else 10000.00
    active_capital = current_balance * 0.70 
    
    # 2. Get latest funding rates from LIVE_TAPE
    tape_sheet = ledger.worksheet("LIVE_TAPE")
    tape_df = pd.DataFrame(tape_sheet.get_all_records())
    
    if tape_df.empty:
        print("Auditor_Payout: No tape data found to calculate payout.")
        return

    # Get the average funding rate across the 6-coin basket
    latest_rates = tape_df.sort_values('timestamp').groupby('asset').last()
    avg_funding = latest_rates['funding_rate'].mean()
    
    # 3. Calculate Payout (Active Capital * Funding Rate)
    payout = active_capital * avg_funding
    new_balance = current_balance + payout
    
    # 4. Log the growth
    audit_entry = [
        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "BASKET_AVG",
        round(active_capital, 2),
        round(avg_funding, 8),
        round(payout, 4),
        round(new_balance, 4)
    ]
    payout_sheet.append_row(audit_entry)
    print(f"Auditor_Payout: Payout of £{payout:.4f} added. Total Vault: £{new_balance:.2f}")

if __name__ == "__main__":
    run_audit()
