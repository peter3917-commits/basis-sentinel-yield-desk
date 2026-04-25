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

# 2026 UK Spec
CGT_ALLOWANCE = 3000.00
CGT_RATE = 0.18 

# 🎨 IMPROVED READABILITY CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricLabel"] { color: #e6edf3 !important; font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { color: #00ffcc !important; }
    [data-testid="stMetricDelta"] { color: #8b949e !important; }
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
        
        # 🛡️ Resiliency Check
        if not tape_df.empty and 'is_active' not in tape_df.columns:
            tape_df['is_active'] = 1

        for df in [tape_df, payout_df, tx_df]:
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # 🏛️ CHRONOLOGICAL FIX: Force the ledger into chronological order 
        # This prevents the dashboard from picking the wrong 'last' row
        if not payout_df.empty:
            payout_df = payout_df.sort_values('timestamp', ascending=True).reset_index(drop=True)
            
        return tape_df, payout_df, tx_df
    except Exception as e:
        st.error(f"⚠️ Vault Access Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 🚀 THE FRONT OFFICE ---
st.title("🛡️ Basis-Sentinel V3: Professional Yield Desk")
st.caption(f"Strategy: Market-Neutral Cash & Carry | Location: Hagley, UK | Spec: 2026/27")

tape_df, payout_df, tx_df = load_v3_data()

if not payout_df.empty:
    # 💎 CALCULATION ENGINE
    payout_df['new_balance'] = pd.to_numeric(payout_df['new_balance'], errors='coerce')
    
    # After sorting in load_v3_data, iloc[-1] is now guaranteed to be the most recent entry
    current_balance = float(payout_df['new_balance'].iloc[-1])
    net_profit = current_balance - 10000.00
    roi = (net_profit / 10000.00) * 100
    
    total_fees = pd.to_numeric(tx_df['toll_paid'], errors='coerce').sum() if not tx_df.empty else 0.00
    taxable_amount = max(0, net_profit - CGT_ALLOWANCE)
    tax_reserve = taxable_amount * CGT_RATE
    true_net = current_balance - tax_reserve

    # --- 💎 METRICS ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vault Balance", f"£{current_balance:,.2f}", f"£{net_profit:+.2f}")
    m2.metric("Geometric ROI", f"{roi:.4f}%", "Net-of-Friction")
    m3.metric("HMRC Tax Reserve", f"£{tax_reserve:,.2f}", "2026 CGT Spec", delta_color="inverse")
    m4.metric("True Liquidity", f"£{true_net:,.2f}", "Post-Tax Net")
    m5.metric("Total Tolls", f"£{total_fees:,.2f}", "Fees & Slippage", delta_color="inverse")

    # --- 🛰️ YIELD HEATMAP ---
    st.divider()
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🛰️ Live Shield Status & Heatmap")
        if not tape_df.empty:
            current_basket = ['BTC', 'ETH', 'SOL', 'BNB', 'SUI', 'APT']
            latest = tape_df[tape_df['asset'].isin(current_basket)]
            
            if not latest.empty:
                latest = latest.sort_values('timestamp').groupby('asset').last().reset_index()
                
                # Dynamic Status Rendering
                latest['Status'] = latest.apply(
                    lambda x: "🟢 ACTIVE" if x['is_active'] == 1 else 
                    ("🛡️ SHIELDED (Basis)" if x['basis_gap'] < 0 else "🛡️ SHIELDED (Yield)"), 
                    axis=1
                )
                
                latest['Projected_APY'] = latest.apply(
                    lambda x: (x['funding_rate'] * 3 * 365 * 100) if x['is_active'] == 1 else 0.0, axis=1
                )
                
                heatmap_df = latest[['asset', 'Status', 'Projected_APY', 'funding_rate', 'basis_gap']].sort_values('Projected_APY', ascending=False)
                st.dataframe(
                    heatmap_df.style.background_gradient(cmap='RdYlGn', subset=['Projected_APY'])
                    .format({'Projected_APY': '{:.2f}%', 'funding_rate': '{:.6f}', 'basis_gap': '{:.4f}'}),
                    width='stretch'
                )

    with c2:
        st.subheader("📡 Desk Status")
        if not tape_df.empty:
            last_ping = tape_df['timestamp'].max()
            st.success(f"Scout Protocol: ONLINE")
            st.info(f"Last Heartbeat: {last_ping.strftime('%H:%M:%S')} UTC")
            active_count = latest['is_active'].sum()
            st.write(f"Deployment: {active_count} / 6 Assets")
            if active_count < 6:
                st.warning(f"Protective Shielding: {6-active_count} Assets")

    # --- 📈 GROWTH ---
    st.divider()
    st.subheader("📈 Auditor: Net Liquidation Curve")
    fig = px.line(payout_df, x='timestamp', y='new_balance', 
                  template="plotly_dark", markers=True)
    fig.update_traces(line_color='#00ffcc', line_width=3)
    st.plotly_chart(fig, width='stretch')

    # --- 🧾 THE DUAL LEDGERS ---
    st.divider()
    col_l, col_r = st.columns(2)
    
    with col_l:
        with st.expander("📊 View Audit History (BASIS_PAYOUT_LOG)"):
            st.dataframe(payout_df.sort_values('timestamp', ascending=False), width='stretch')
            
    with col_r:
        with st.expander("🧾 View Transaction Log (Tolls Paid)"):
            if not tx_df.empty:
                st.dataframe(tx_df.sort_values('timestamp', ascending=False), width='stretch')
            else:
                st.info("No transaction tolls recorded yet.")

else:
    st.error("Firm Locked: Check BASIS_PAYOUT_LOG.")
