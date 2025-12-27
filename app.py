import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="Merchant Fee Auditor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (The Design Magic) ---
st.markdown("""
    <style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Remove top padding to look like a website, not a doc */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom Hero Section */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 40px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .hero h1 {
        color: white !important;
        margin: 0;
        font-size: 2.5rem;
    }
    .hero p {
        font-size: 1.2rem;
        opacity: 0.9;
    }

    /* Metric Cards (Like ProjectionLab) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Upload Box Styling */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #3b82f6;
        border-radius: 10px;
        padding: 20px;
        background-color: #f8fafc;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HERO SECTION ---
st.markdown("""
    <div class="hero">
        <h1>⚖️ Merchant Fee Auditor</h1>
        <p>Stop overpaying Stripe. Upload your CSV to detect hidden 'International Leakage'.</p>
    </div>
    """, unsafe_allow_html=True)

# --- APP LOGIC ---
uploaded_file = st.file_uploader("Drop your Stripe 'Balance Change' CSV here", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- CLEANING ---
        df.columns = [c.lower().strip() for c in df.columns]
        def get_col(options):
            for o in options:
                if o in df.columns: return o
            return None

        col_fee = get_col(['fee', 'fees', 'stripe fee'])
        col_gross = get_col(['amount', 'gross', 'amount (gross)'])
        col_country = get_col(['card country', 'card_country_code'])
        col_type = get_col(['type', 'reporting category'])

        if not col_fee or not col_gross:
            st.error("❌ Column mismatch. Ensure you exported 'Balance Change from Activity'.")
            st.stop()

        # Numeric Conversion
        for col in [col_fee, col_gross]:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').astype(float)

        # Calculations
        total_gross = df[df[col_gross] > 0][col_gross].sum()
        total_fees = df[col_fee].abs().sum()
        effective_rate = (total_fees / total_gross * 100) if total_gross > 0 else 0
        
        intl_leakage = 0
        if col_country:
            intl_vol = df[df[col_country] != 'US'][col_gross].sum()
            intl_leakage = intl_vol * 0.015

        # --- METRICS GRID ---
        st.markdown("### 📊 Audit Report")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Volume", f"${total_gross:,.0f}")
        col2.metric("Fees Paid", f"${total_fees:,.0f}")
        col3.metric("Effective Rate", f"{effective_rate:.2f}%", 
                    delta=f"{2.9 - effective_rate:.2f}% (vs Standard)",
                    delta_color="normal" if effective_rate < 3.0 else "inverse")
        col4.metric("Est. Leakage", f"${intl_leakage:,.0f}")

        # --- CHARTS ---
        st.divider()
        st.markdown("### 📈 Fee Analysis")
        
        # Monthly Chart
        if 'created' in df.columns:
            df['date'] = pd.to_datetime(df['created'])
            monthly = df.groupby(df['date'].dt.strftime('%Y-%m'))[[col_gross, col_fee]].sum().reset_index()
            
            fig = px.bar(monthly, x='date', y=col_fee, 
                         title="Fees per Month",
                         labels={'date': 'Month', col_fee: 'Fees ($)'},
                         color_discrete_sequence=['#3b82f6'])
            fig.update_layout(plot_bgcolor="white", margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error reading file: {e}")

else:
    # --- LANDING PAGE DEMO ---
    st.info("👋 Don't have a file? The tool will analyze leakage once you upload a Stripe export.")