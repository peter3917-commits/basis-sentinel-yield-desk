import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import plotly.express as px
from datetime import datetime

# --- 🏛️ INSTITUTIONAL UI CONFIG ---
st.set_page_config(page_title="Basis-Sentinel | Yield Desk", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 🔑 VAULT ACCESS ENGINE ---
def get_ledger():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.getenv("GSHEETS_SECRET"))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(os.getenv("GSHEET_ID"))
    except Exception as e:
        st.error(f"⚠️ Vault Access Denied: {e}")
        return None

def load_data(ledger):
    try:
        tape_sheet = ledger.worksheet("LIVE_TAPE")
        payout_sheet = ledger.worksheet("BASIS_PAYOUT_LOG")
        
        t_df = pd.DataFrame(tape_sheet.get_all_records())
        p_df = pd.DataFrame(payout_sheet.get_all_records())
        
        if not p_df.empty:
            p_df.columns = ['timestamp', 'avg_funding_rate', 'gross_payout', 'slippage', 'new_balance']
            p_df['new_balance'] = pd.to_numeric(p_df['new_balance'], errors='coerce')
            p_df['slippage'] = pd.to_numeric(p_df['slippage'], errors='coerce')
            p_df['timestamp'] = pd.to_datetime(p_df['timestamp'], errors='coerce')
            p_df = p_df.dropna(subset=['new_balance', 'timestamp'])
            
        if not t_df.empty:
            t_df['timestamp'] = pd.to_datetime(t_df['timestamp'], errors='coerce')
            t_df['funding_rate'] = pd.to_numeric(t_df['funding_rate'], errors='coerce')
            t_df['basis_gap'] = pd.to_numeric(t_df['basis_gap'], errors='coerce')
            
        return t_df, p_df
    except Exception as e:
        st.warning(f"Resynchronizing Ledger... ({e})")
        return pd.DataFrame(), pd.DataFrame()

# --- 🚀 THE FRONT OFFICE ---
st.title("⚖️ Basis-Sentinel: £10,000 Virtual Yield Desk")
st.caption(f"Strategy: Market-Neutral Cash & Carry | Portfolio: High-Velocity Basket | Sampling: 180s")

try:
    ledger = get_ledger()

    if ledger:
        tape_df, payout_df = load_data(ledger)

        # --- 💎 THE 5-COLUMN METRIC ROW ---
        m1, m2, m3, m4, m5 = st.columns(5)
        
        if not payout_df.empty:
            current_balance = float(payout_df['new_balance'].iloc[-1])
            total_overhead = float(payout_df['slippage'].sum())
        else:
            current_balance = 10000.00
            total_overhead = 0.00

        net_profit = current_balance - 10000.00
        roi = (net_profit / 10000.00) * 100
        
        m1.metric("Vault Balance", f"£{current_balance:,.2f}", f"£{net_profit:+.4f}")
        m2.metric("Geometric ROI", f"{roi:.4f}%", "Net-of-Friction")
        m3.metric("The Shield", "£3,000.00", "30% Reserve")
        m4.metric("Active Capital", f"£{(current_balance * 0.7):,.2f}", "70% Deploy")
        m5.metric("Overhead Bin", f"£{total_overhead:,.4f}", "Fees & Slippage", delta_color="inverse")

        # --- 🛰️ YIELD HEATMAP ---
        st.divider()
        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader("🛰️ Live Yield Heatmap")
            if not tape_df.empty:
                # 🏛️ Filter for the NEW High-Velocity Basket
                current_basket = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
                latest = tape_df[tape_df['asset'].isin(current_basket)]
                latest = latest.sort_values('timestamp').groupby('asset').last().reset_index()
                
                latest['Projected_APY'] = latest['funding_rate'] * 3 * 365 * 100
                heatmap_df = latest[['asset', 'Projected_APY', 'basis_gap', 'funding_rate', 'mark_price']].sort_values('Projected_APY', ascending=False)
                
                st.dataframe(
                    heatmap_df.style.background_gradient(cmap='RdYlGn', subset=['Projected_APY'])
                    .format({'Projected_APY': '{:.2f}%', 'funding_rate': '{:.6f}', 'basis_gap': '{:.4f}'}),
                    use_container_width=True
                )
            else:
                st.info("Awaiting Scout heartbeat for new basket...")

        with c2:
            st.subheader("📡 Desk Status")
            if not tape_df.empty:
                last_ping = tape_df['timestamp'].max()
                st.success(f"Scout Online: {last_ping.strftime('%H:%M:%S')}")
                st.write(f"Basket: BTC, ETH, SOL, BNB, SUI, APT")
            else:
                st.error("Scout Signal Lost")

        # --- 📈 THE COMPOUNDING CURVE ---
        st.divider()
        st.subheader("📈 Auditor: Compounding Growth Curve (Net)")
        if not payout_df.empty:
            fig = px.line(payout_df, x='timestamp', y='new_balance', 
                          template="plotly_dark", markers=True,
                          labels={"new_balance": "Total Equity (£)", "timestamp": "Audit UTC"})
            fig.update_traces(line_color='#00ffcc', line_width=3)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("The Growth Curve will populate as audits are filed.")

        with st.expander("🧾 View Raw Audit Logs"):
            st.dataframe(payout_df.tail(20), use_container_width=True)

    else:
        st.error("Firm Locked: Check Secrets.")

except Exception as e:
    st.error(f"⚠️ Dashboard Error: {e}")
