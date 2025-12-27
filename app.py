import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Merchant Fee Auditor", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS FOR "PRO" LOOK ---
st.markdown("""
    <style>
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Card Styling */
    .metric-card {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Typography */
    h1 {color: #0e1117; font-weight: 700;}
    h3 {color: #262730;}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("⚖️ Merchant Fee Auditor")
st.markdown("""
### **Stop overpaying for payment processing.**
Most businesses pay **3.4% - 3.8%** instead of the promised 2.9%. 
Upload your Stripe export to detect **International Leakage** and **Sunk Refund Costs**.
""")

# --- INSTRUCTIONS EXPANDER ---
with st.expander("📝 How to get your data from Stripe (Click here)"):
    st.markdown("""
    1. Log into your Stripe Dashboard.
    2. Go to **Reports** > **Balance**.
    3. Click **Export** (top right).
    4. Select **"Balance change from activity"** as the report type.
    5. Columns needed: `Gross`, `Fee`, `Net`, `Type`, `Card Country`.
    """)

st.divider()

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 Upload your CSV file here", type=['csv'])

if uploaded_file is not None:
    try:
        # Load Data
        df = pd.read_csv(uploaded_file)
        
        # --- DATA CLEANING ---
        df.columns = [c.lower().strip() for c in df.columns]
        
        def get_col(options):
            for o in options:
                if o in df.columns: return o
            return None

        col_fee = get_col(['fee', 'fees', 'stripe fee'])
        col_gross = get_col(['amount', 'gross', 'amount (gross)'])
        col_net = get_col(['net', 'amount (net)'])
        col_type = get_col(['type', 'reporting category', 'transaction type'])
        col_country = get_col(['card country', 'card_country_code', 'payment_method_details_card_country'])

        if not col_fee or not col_gross:
            st.error("❌ Error: We couldn't find 'Fee' or 'Gross Amount' columns. Please check your export settings.")
            st.stop()

        # Numeric Cleanup
        for col in [col_fee, col_gross, col_net]:
            if col:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').astype(float)

        # --- METRIC CALCULATIONS ---
        df_charges = df[df[col_gross] > 0].copy() 
        total_gross = df_charges[col_gross].sum()
        total_fees = df[col_fee].abs().sum() 
        effective_rate = (total_fees / total_gross) * 100 if total_gross > 0 else 0
        
        # International Logic
        if col_country:
            intl_txns = df[df[col_country] != 'US']
            intl_volume = intl_txns[col_gross].sum()
            intl_fees_estimated = intl_volume * 0.015 
        else:
            intl_fees_estimated = 0

        # Refund Logic
        refund_fees = 0.0
        if col_type:
            refunds = df[df[col_type].astype(str).str.contains('refund', case=False, na=False)]
            refund_fees = refunds[col_fee].abs().sum()

        # --- DASHBOARD UI (The Pretty Part) ---
        
        st.subheader("📊 The Audit Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Processed", f"${total_gross:,.0f}")
        
        with col2:
            st.metric("Total Fees Paid", f"${total_fees:,.0f}")
            
        with col3:
            # Color Logic for Rate
            rate_delta = 2.9 - effective_rate
            st.metric("Effective Rate", f"{effective_rate:.2f}%", delta=f"{rate_delta:.2f}%", delta_color="normal")
            if effective_rate > 3.2:
                st.warning("⚠️ Rate is High (>3.2%)")

        with col4:
            st.metric("Est. Intl Surcharge", f"${intl_fees_estimated:,.0f}", help="Extra 1.5% fee on foreign cards")

        st.divider()

        # --- CHARTS & TABLES ---
        c_chart, c_table = st.columns([2, 1])

        with c_chart:
            st.subheader("📈 Monthly Fee Trend")
            # Create Date Column
            if 'created (utc)' in df.columns:
                df['date'] = pd.to_datetime(df['created (utc)'])
            elif 'created' in df.columns:
                df['date'] = pd.to_datetime(df['created'])
            else:
                df['date'] = pd.to_datetime("today")

            df['Month'] = df['date'].dt.strftime('%Y-%m')
            monthly = df.groupby('Month')[[col_gross, col_fee]].sum().reset_index()
            
            fig = px.bar(monthly, x='Month', y=col_fee, title="Fees Paid by Month", color_discrete_sequence=['#FF4B4B'])
            fig.update_layout(plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

        with c_table:
            st.subheader("📅 Monthly Breakdown")
            monthly['Real Rate'] = (monthly[col_fee].abs() / monthly[col_gross]) * 100
            st.dataframe(monthly[['Month', col_gross, 'Real Rate']].style.format({
                col_gross: "${:,.0f}",
                'Real Rate': "{:.2f}%"
            }), use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")