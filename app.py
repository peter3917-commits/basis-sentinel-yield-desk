import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# --- 🏛️ INSTITUTIONAL UI CONFIG ---
st.set_page_config(page_title="Basis-Sentinel | Yield Desk", page_icon="⚖️", layout="wide")

st.title("⚖️ Basis-Sentinel: £10,000 Virtual Yield Desk")
st.markdown("### Market-Neutral Cash & Carry Protocol")

# --- 🔑 AUTHENTICATION ---
def get_ledger():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(os.getenv("GSHEET_ID"))

try:
    ledger = get_ledger()
    tape_sheet = ledger.worksheet("LIVE_TAPE")
    payout_sheet = ledger.worksheet("BASIS_PAYOUT_LOG")
    
    # Load Data
    tape_df = pd.DataFrame(tape_sheet.get_all_records())
    payout_df = pd.DataFrame(payout_sheet.get_all_records())

    # --- 📊 TOP LEVEL METRICS ---
    m1, m2, m3 = st.columns(3)
    
    current_balance = payout_df['new_balance'].iloc[-1] if not payout_df.empty else 10000.00
    total_profit = current_balance - 10000.00
    
    m1.metric("Virtual Vault Balance", f"£{current_balance:,.2f}", f"{total_profit:+.2f}")
    m2.metric("The Shield (Margin Pot)", "£3,000.00", "30% Allocation")
    m3.metric("Staff Status", "ONLINE", "Scout_Yield @ 5m")

    # --- 🛰️ THE YIELD HEATMAP ---
    st.divider()
    st.header("🛰️ Analyst: Yield Heatmap")
    
    if not tape_df.empty:
        # Calculate APY for each asset
        latest = tape_df.sort_values('timestamp').groupby('asset').last().reset_index()
        latest['projected_apy'] = latest['funding_rate'].apply(lambda x: round(x * 3 * 365 * 100, 2))
        
        # Display Heatmap
        heatmap = latest[['asset', 'projected_apy', 'funding_rate', 'basis_gap']].sort_values('projected_apy', ascending=False)
        
        # Style the APY
        st.dataframe(heatmap.style.background_gradient(cmap='RdYlGn', subset=['projected_apy']), use_container_width=True)
        
        # Visual Bar Chart
        st.bar_chart(latest.set_index('asset')['projected_apy'])
    else:
        st.info("Awaiting the first pings from Scout_Yield...")

    # --- 🧾 THE AUDIT TRAIL ---
    st.divider()
    st.header("🧾 Auditor: 8-Hour Payout Log")
    if not payout_df.empty:
        st.table(payout_df.tail(10))
    else:
        st.write("No payout cycles recorded yet. (Next payout at 00:00, 08:00, or 16:00 UTC).")

except Exception as e:
    st.error(f"⚠️ Dashboard Connection Error: {e}")
