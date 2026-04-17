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

# 2026 UK Tax Spec (Hagley, England)
CGT_ALLOWANCE = 3000.00
CGT_RATE = 0.18  # Basic Rate

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 🔑 VAULT ACCESS ENGINE ---
def load_v3_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        ledger = client.open_by_key(os.getenv("GSHEET_ID"))
        
        # Load the 3 Core Sheets
        tape_df = pd.DataFrame(ledger.worksheet("LIVE_TAPE").get_all_records())
        payout_df = pd.DataFrame(ledger.worksheet("BASIS_PAYOUT_LOG").get_all_records())
        tx_df = pd.DataFrame(ledger.worksheet("TRANSACTION_LOG").get_all_records())
        
        # Format Data
        for df in [tape_df, payout_df, tx_df]:
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return tape_df, payout_df, tx_df
    except Exception as e:
        st.error(f"⚠️ Vault Access Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 🚀 THE COMMAND CENTER ---
st.title("🛡️ Basis-Sentinel V3: Professional Yield Desk")
st.caption(f"Strategy: Market-Neutral | Mode: Negative Yield Ejection & Basis Entry Filter")

tape_df, payout_df, tx_df = load_v3_data()

if not payout_df.empty:
    # --- 💎 THE 5-COLUMN METRIC ROW ---
    current_balance = float(payout_df['new_balance'].iloc[-1])
    total_net_profit = current_balance - 10000.00
    total_fees = tx_df['toll_paid'].sum() if not tx_df.empty else 0.00
    
    # HMRC Tax Reserve Logic
    taxable_amount = max(0, total_net_profit - CGT_ALLOWANCE)
    tax_reserve = taxable_amount * CGT_RATE
    true_liquidity = current_balance - tax_reserve

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vault Balance", f"£{current_balance:,.2f}", f"£{total_net_profit:+.2f}")
    m2.metric("HMRC Tax Reserve", f"£{tax_reserve:,.2f}", "2026 UK Spec", delta_color="inverse")
    m3.metric("True Liquidity", f"£{true_liquidity:,.2f}", "Post-Tax/Fees")
    m4.metric("Active Capital", f"£{(current_balance * 0.7):,.2f}", "70% Deploy")
    m5.metric("Total Tolls", f"£{total_fees:,.2f}", "Exit/Entry Fees", delta_color="inverse")

    # --- 🛰️ THE SHIELD HEATMAP ---
    st.divider()
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🛰️ Live Shield Status & Heatmap")
        if not tape_df.empty:
            # Filter for latest status of our 6-coin basket
            current_basket = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
            latest = tape_df[tape_df['asset'].isin(current_basket)]
            latest = latest.sort_values('timestamp').groupby('asset').last().reset_index()
            
            # 🛡️ DECISION DISPLAY
            latest['Status'] = latest['is_active'].apply(lambda x: "🟢 ACTIVE" if x == 1 else "🛡️ SHIELDED")
            # Calculate APY only for Active assets
            latest['Projected_APY'] = latest.apply(
                lambda x: (x['funding_rate'] * 3 * 365 * 100) if x['is_active'] == 1 else 0.0, axis=1
            )
            
            display_df = latest[['asset', 'Status', 'Projected_APY', 'funding_rate', 'basis_gap']].sort_values('Projected_APY', ascending=False)
            
            st.dataframe(
                display_df.style.background_gradient(cmap='RdYlGn', subset=['Projected_APY'])
                .format({'Projected_APY': '{:.2f}%', 'funding_rate': '{:.6f}', 'basis_gap': '{:.4f}'}),
                use_container_width=True
            )

    with c2:
        st.subheader("📡 Desk Integrity")
        last_ping = tape_df['timestamp'].max()
        st.success(f"Scout Protocol: ONLINE")
        st.info(f"Last Heartbeat: {last_ping.strftime('%H:%M:%S')} UTC")
        active_count = latest['is_active'].sum()
        st.write(f"Yield Deployment: {active_count} / 6 Assets")
        if active_count < 6:
            st.warning(f"{6 - active_count} Assets Ejected (Negative Yield Protection)")

    # --- 📈 THE COMPOUNDING CURVE ---
    st.divider()
    st.subheader("📈 Auditor: Net Liquidation Curve")
    fig = px.line(payout_df, x='timestamp', y='new_balance', 
                  template="plotly_dark", markers=True)
    fig.update_traces(line_color='#00ffcc', line_width=3)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🧾 View Black-Box Transaction Log (Tolls Paid)"):
        if not tx_df.empty:
            st.dataframe(tx_df.sort_values('timestamp', ascending=False).head(10), use_container_width=True)
        else:
            st.info("No transaction tolls recorded yet.")

else:
    st.info("Waiting for first V3 Audit to be filed...")
