import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import plotly.express as px
from datetime import datetime

# --- 🏛️ UI CONFIG ---
st.set_page_config(page_title="Sentinel V3 | Command", page_icon="🛡️", layout="wide")

# 🎨 READABILITY CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricLabel"] { color: #e6edf3 !important; font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { color: #00ffcc !important; }
    </style>
    """, unsafe_allow_html=True)

def load_v3_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        
        tape_df = pd.DataFrame(ledger.worksheet("LIVE_TAPE").get_all_records())
        payout_df = pd.DataFrame(ledger.worksheet("BASIS_PAYOUT_LOG").get_all_records())
        
        try:
            tx_df = pd.DataFrame(ledger.worksheet("TRANSACTION_LOG").get_all_records())
        except:
            tx_df = pd.DataFrame(columns=['timestamp', 'asset', 'action', 'toll_paid', 'reason'])
        
        # Chronological Fix: Force sorting before returning
        for df in [tape_df, payout_df, tx_df]:
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        if not payout_df.empty:
            payout_df = payout_df.sort_values('timestamp', ascending=True).reset_index(drop=True)
            
        return tape_df, payout_df, tx_df
    except Exception as e:
        st.error(f"⚠️ Vault Access Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 🚀 THE COMMAND CENTER ---
st.title("🛡️ Basis-Sentinel V3: Professional Yield Desk")

tape_df, payout_df, tx_df = load_v3_data()

if not payout_df.empty:
    payout_df['new_balance'] = pd.to_numeric(payout_df['new_balance'], errors='coerce')
    current_balance = float(payout_df['new_balance'].iloc[-1])
    net_profit = current_balance - 10000.00
    roi = (net_profit / 10000.00) * 100
    
    total_fees = pd.to_numeric(tx_df['toll_paid'], errors='coerce').sum() if not tx_df.empty else 0.00
    tax_reserve = max(0, net_profit - 3000) * 0.18
    true_net = current_balance - tax_reserve

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vault Balance", f"£{current_balance:,.2f}", f"£{net_profit:+.2f}")
    m2.metric("Geometric ROI", f"{roi:.4f}%")
    m3.metric("HMRC Tax Reserve", f"£{tax_reserve:,.2f}", delta_color="inverse")
    m4.metric("True Liquidity", f"£{true_net:,.2f}")
    m5.metric("Total Tolls", f"£{total_fees:,.2f}", delta_color="inverse")

    st.divider()
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🛰️ Shield Status")
        if not tape_df.empty:
            current_basket = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
            latest = tape_df[tape_df['asset'].isin(current_basket)]
            latest = latest.sort_values('timestamp').groupby('asset').last().reset_index()
            
            latest['Status'] = latest.apply(
                lambda x: "🟢 ACTIVE" if x['is_active'] == 1 else 
                ("🛡️ SHIELDED (Basis)" if x['basis_gap'] < 0 else "🛡️ SHIELDED (Yield)"), axis=1)
            
            st.dataframe(latest[['asset', 'Status', 'funding_rate', 'basis_gap']], width='stretch')

    st.divider()
    st.subheader("📈 Auditor: Net Liquidation Curve")
    fig = px.line(payout_df, x='timestamp', y='new_balance', template="plotly_dark")
    fig.update_traces(line_color='#00ffcc')
    st.plotly_chart(fig, width='stretch')

    with st.expander("📊 Audit Ledger (BASIS_PAYOUT_LOG)"):
        st.dataframe(payout_df.sort_values('timestamp', ascending=False), width='stretch')
else:
    st.info("Check BASIS_PAYOUT_LOG headers.")
