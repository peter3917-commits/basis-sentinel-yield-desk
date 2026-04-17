import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import plotly.express as px
from datetime import datetime

# --- 🏛️ INSTITUTIONAL UI CONFIG ---
st.set_page_config(page_title="Sentinel V3 | Command", page_icon="🛡️", layout="wide")

CGT_ALLOWANCE = 3000.00
CGT_RATE = 0.18 

def load_v3_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        
        # Load core sheets
        tape_df = pd.DataFrame(ledger.worksheet("LIVE_TAPE").get_all_records())
        payout_df = pd.DataFrame(ledger.worksheet("BASIS_PAYOUT_LOG").get_all_records())
        
        # 🛡️ Safety: If is_active is missing from Sheet, create it to prevent crash
        if not tape_df.empty and 'is_active' not in tape_df.columns:
            tape_df['is_active'] = 1
        
        # 🛡️ Soft check for Transaction Log
        try:
            tx_df = pd.DataFrame(ledger.worksheet("TRANSACTION_LOG").get_all_records())
        except:
            tx_df = pd.DataFrame(columns=['timestamp', 'asset', 'action', 'toll_paid', 'reason'])
        
        for df in [tape_df, payout_df, tx_df]:
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return tape_df, payout_df, tx_df
    except Exception as e:
        st.error(f"⚠️ Vault Access Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 🚀 THE COMMAND CENTER ---
st.title("🛡️ Basis-Sentinel V3: Professional Yield Desk")

tape_df, payout_df, tx_df = load_v3_data()

if not payout_df.empty:
    current_balance = float(payout_df['new_balance'].iloc[-1])
    total_net_profit = current_balance - 10000.00
    
    total_fees = 0.00
    if not tx_df.empty:
        tx_df['toll_paid'] = pd.to_numeric(tx_df['toll_paid'], errors='coerce').fillna(0)
        total_fees = tx_df['toll_paid'].sum()
    
    taxable_amount = max(0, total_net_profit - CGT_ALLOWANCE)
    tax_reserve = taxable_amount * CGT_RATE
    true_liquidity = current_balance - tax_reserve

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vault Balance", f"£{current_balance:,.2f}")
    m2.metric("HMRC Tax Reserve", f"£{tax_reserve:,.2f}", delta_color="inverse")
    m3.metric("True Net", f"£{true_liquidity:,.2f}")
    m4.metric("Active Capital", f"£{(current_balance * 0.7):,.2f}")
    m5.metric("Total Tolls", f"£{total_fees:,.2f}", delta_color="inverse")

    # --- 🛰️ HEATMAP ---
    st.divider()
    if not tape_df.empty:
        current_basket = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
        latest = tape_df[tape_df['asset'].isin(current_basket)]
        latest = latest.sort_values('timestamp').groupby('asset').last().reset_index()
        
        # Double-check column exists before applying lambda
        if 'is_active' in latest.columns:
            latest['Status'] = latest['is_active'].apply(lambda x: "🟢 ACTIVE" if x == 1 else "🛡️ SHIELDED")
            latest['Projected_APY'] = latest.apply(
                lambda x: (x['funding_rate'] * 3 * 365 * 100) if x['is_active'] == 1 else 0.0, axis=1
            )
        
        st.dataframe(
            latest[['asset', 'Status', 'Projected_APY', 'funding_rate', 'basis_gap']].style.background_gradient(cmap='RdYlGn', subset=['Projected_APY']),
            width='stretch'
        )

    # --- 📈 CURVE ---
    st.divider()
    fig = px.line(payout_df, x='timestamp', y='new_balance', template="plotly_dark")
    fig.update_traces(line_color='#00ffcc')
    st.plotly_chart(fig, width='stretch')

else:
    st.info("Awaiting first V3 Audit. Ensure TRANSACTION_LOG sheet exists and is shared.")
