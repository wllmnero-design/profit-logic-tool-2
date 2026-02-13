import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime
import theme_analog_warmth as theme

st.set_page_config(page_title="Profit Logic V5 — Dealer Direct OS", layout="wide")
theme.apply_theme()

# ---------------------------------------------------------
# CONSTANTS & DEFAULTS
# ---------------------------------------------------------
BUY_FEES = 865
CURRENT_YEAR = datetime.now().year

DEFAULT_INDUSTRY_TURN = {
    'hyundai_tucson': 30, 'hyundai_elantra': 32, 'hyundai_sonata': 32,
    'hyundai_kona': 25, 'hyundai_palisade': 28, 'hyundai_santa_fe': 42,
    'nissan_rogue': 36, 'nissan_altima': 40, 'nissan_kicks': 33,
    'toyota_camry': 26, 'toyota_rav4': 35, 'honda_accord': 32,
    'kia_sportage': 56, 'genesis_gv70': 36, 'genesis_g70': 42
}

BASE_MSRP = {
    'hyundai_tucson': 26000, 'hyundai_elantra': 21000, 'hyundai_sonata': 25000,
    'nissan_rogue': 28000, 'nissan_altima': 25000, 'toyota_camry': 27000,
    'toyota_rav4': 29000, 'honda_accord': 28000, 'kia_sportage': 27000,
    'genesis_gv70': 45000, 'chevrolet_equinox': 26000, 'ford_escape': 27000
}

WMI_MAPPING = {
    '1G': 'Chevrolet', '2G': 'Chevrolet', '3G': 'Chevrolet',
    '1H': 'Honda', '2H': 'Honda', '3H': 'Honda', 'JH': 'Honda',
    '1N': 'Nissan', '3N': 'Nissan', 'JN': 'Nissan',
    '1T': 'Toyota', '2T': 'Toyota', '3T': 'Toyota', '4T': 'Toyota', '5T': 'Toyota', 'JT': 'Toyota',
    'KM8': 'Hyundai', 'KMH': 'Hyundai', '5NM': 'Hyundai',
    'KN': 'Kia', '5X': 'Kia',
    '1F': 'Ford', '2F': 'Ford', '3F': 'Ford', '4F': 'Ford',
    'KMT': 'Genesis'
}

YEAR_CODES = {'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025, 'T': 2026}

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if 'dealer_turn_data' not in st.session_state:
    st.session_state.dealer_turn_data = {}
if 'dealer_gross_data' not in st.session_state:
    st.session_state.dealer_gross_data = {}
if 'sales_summary' not in st.session_state:
    st.session_state.sales_summary = None

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def parse_currency(val):
    if pd.isna(val): return 0.0
    val_str = str(val).strip()
    if not val_str or val_str == '-': return 0.0
    
    is_neg = False
    if val_str.startswith('(') and val_str.endswith(')'):
        is_neg, val_str = True, val_str[1:-1]
    elif val_str.startswith('-'):
        is_neg, val_str = True, val_str[1:]
        
    val_str = re.sub(r'[^\d.]', '', val_str)
    try:
        parsed = float(val_str)
        return -parsed if is_neg else parsed
    except ValueError:
        return 0.0

def get_base_cpm(price):
    if price < 15000: return 0.10
    if price < 45000: return 0.15
    if price < 80000: return 0.20
    return 0.30

def calculate_cpm(price, vehicle_year, current_year, use_auto, manual_cpm):
    base_cpm = get_base_cpm(price) if use_auto else manual_cpm
    age = max(current_year - vehicle_year, 0)
    return max(base_cpm * (0.85 ** age), 0.03)

def get_turn_days(make, model):
    key = f"{str(make).lower()}_{str(model).lower().replace(' ', '_')}"
    if key in st.session_state.dealer_turn_data:
        return st.session_state.dealer_turn_data[key], "YOUR Data"
    return DEFAULT_INDUSTRY_TURN.get(key, 38), "Industry Averages"

def get_priority(turn_days, margin):
    if turn_days <= 30 and margin >= 0.12: return "HIGH"
    if turn_days >= 60 and margin < 0.08: return "LOW"
    return "MEDIUM"

def decode_vin(vin):
    vin = vin.upper()
    if len(vin) != 17 or any(c in vin for c in 'IOQ'): return "", CURRENT_YEAR - 3
    make = "Unknown"
    for wmi, m in WMI_MAPPING.items():
        if vin.startswith(wmi):
            make = m
            break
    year = YEAR_CODES.get(vin[9], CURRENT_YEAR - 3)
    return make, year

# ---------------------------------------------------------
# SIDEBAR SETTINGS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## Settings")
    margin_str = st.selectbox("Margin Target", ["5%", "8%", "10%", "12%", "14%", "16%", "18%"], index=3)
    margin_target = float(margin_str.strip('%')) / 100.0

    recon_str = st.selectbox("Recon Cost", ["$1,000", "$1,500", "$2,000"], index=1)
    recon_cost = float(recon_str.replace('$', '').replace(',', ''))

    below_line = st.number_input("Below the Line", min_value=0, max_value=5000, step=100, value=1200)

    st.markdown("### Mileage Taper Logic")
    auto_cpm = st.checkbox("Auto CPM by Price", value=True)
    manual_cpm = 0.15
    if not auto_cpm:
        manual_cpm = st.slider("Manual CPM", 0.05, 0.50, 0.15, step=0.01)
    else:
        st.markdown("""
        <div style="font-size: 0.85rem; background-color: rgba(255,255,255,0.1); padding: 8px; border-radius: 4px;">
        <b>Tier Breakdown:</b><br>
        Budget (&lt;$15k): $0.10/mi<br>
        Mainstream ($15k-$45k): $0.15/mi<br>
        Luxury ($45k-$80k): $0.20/mi<br>
        High-Line ($80k+): $0.30/mi
        </div><br>
        """, unsafe_allow_html=True)

    st.markdown(f"**Buy Fees:** ${BUY_FEES}")
    
    st.markdown("---")
    num_models = len(st.session_state.dealer_turn_data)
    if num_models > 0:
        st.success(f"🟢 **Source:** YOUR Data ({num_models} models)")
    else:
        st.warning("🟡 **Source:** Industry Averages")

# ---------------------------------------------------------
# MAIN APP TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Sales Performance", "Single VIN Lookup", "Batch Processor"])

# TAB 1: SALES PERFORMANCE (DATA UPLOAD)
with tab1:
    st.header("Sales Performance Data")
    st.markdown("""
    <div class="info-box">
    Upload your dealer's DMS sales log (CSV or Excel) to extract custom turn rates and gross averages by Make/Model. 
    The logic engine will automatically apply your proprietary data to Tab 2 and Tab 3.
    </div>
    """, unsafe_allow_html=True)
    
    col_up, col_btn = st.columns([3, 1])
    uploaded_file = col_up.file_uploader("Upload DMS Sales Log", type=['csv', 'xlsx'])
    
    with col_btn:
        st.write("")
        st.write("")
        if st.button("Clear Data", use_container_width=True):
            st.session_state.dealer_turn_data = {}
            st.session_state.dealer_gross_data = {}
            st.session_state.sales_summary = None
            st.rerun()
            
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            req_cols = ['Sold Date', 'Received Date', 'Make', 'Model', 'Front Gross', 'Total Gross', 'Deal Type', 'Sold Price']
            missing = [c for c in req_cols if c not in df.columns]
            
            if missing:
                st.error(f"Missing expected columns: {', '.join(missing)}. Make sure the upload contains all standard columns.")
            else:
                df = df[df['Deal Type'].astype(str).str.upper() == 'RETAIL'].copy()
                df = df.dropna(subset=['Sold Date', 'Received Date'])
                df['Sold Date'] = pd.to_datetime(df['Sold Date'], errors='coerce')
                df['Received Date'] = pd.to_datetime(df['Received Date'], errors='coerce')
                
                df['Days_To_Sell'] = (df['Sold Date'] - df['Received Date']).dt.days
                df = df[(df['Days_To_Sell'] >= 0) & (df['Days_To_Sell'] <= 365)]
                
                for col in ['Front Gross', 'F&I Products Gross', 'Back Gross', 'Total Gross', 'Sold Price']:
                    if col in df.columns: df[col] = df[col].apply(parse_currency)
                
                total_sales = len(df)
                if total_sales > 0:
                    t_front = df['Front Gross'].sum()
                    t_gross = df['Total Gross'].sum()
                    avg_turn = df['Days_To_Sell'].mean()
                    avg_front = df['Front Gross'].mean()
                    
                    breakdown = df.groupby(['Make', 'Model']).agg(
                        Units_Sold=('Days_To_Sell', 'count'),
                        Avg_Turn=('Days_To_Sell', 'mean'),
                        Avg_Front_Gross=('Front Gross', 'mean'),
                        Avg_Total_Gross=('Total Gross', 'mean')
                    ).reset_index()
                    
                    turn_dict, gross_dict = {}, {}
                    for _, row in breakdown.iterrows():
                        key = f"{str(row['Make']).lower()}_{str(row['Model']).lower().replace(' ', '_')}"
                        turn_dict[key] = row['Avg_Turn']
                        gross_dict[key] = {'front': row['Avg_Front_Gross'], 'total': row['Avg_Total_Gross']}
                        
                    st.session_state.dealer_turn_data = turn_dict
                    st.session_state.dealer_gross_data = gross_dict
                    st.session_state.sales_summary = {
                        "total_sales": total_sales, "t_front": t_front, "t_gross": t_gross,
                        "avg_turn": avg_turn, "avg_front": avg_front, "breakdown": breakdown
                    }
                    st.success("✅ Data processed successfully! Turn rates saved to session.")
                else:
                    st.warning("No valid Retail deals found in the file.")
                
        except Exception as e:
            st.error(f"Error processing file: {e}")

    if st.session_state.sales_summary:
        ss = st.session_state.sales_summary
        st.subheader("Performance Summary")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Sales", f"{ss['total_sales']:,}")
        c2.metric("Total Front Gross", f"${ss['t_front']:,.2f}")
        c3.metric("Total Gross", f"${ss['t_gross']:,.2f}")
        c4.metric("Avg Turn", f"{ss['avg_turn']:.0f}d")
        c5.metric("Avg Front/Unit", f"${ss['avg_front']:,.2f}")
        
        st.subheader("Make/Model Breakdown")
        disp_df = ss['breakdown'].copy()
        disp_df['Avg_Turn'] = disp_df['Avg_Turn'].apply(lambda x: f"{x:.0f}d")
        for col in ['Avg_Front_Gross', 'Avg_Total_Gross']: disp_df[col] = disp_df[col].apply(lambda x: f"${x:,.2f}")
        
        st.markdown(disp_df.to_html(index=False), unsafe_allow_html=True)


# TAB 2: SINGLE VIN LOOKUP
with tab2:
    st.header("Single VIN Appraisal")
    
    vin_input = st.text_input("VIN (17 characters)", max_chars=17).upper()
    d_make, d_year = "", CURRENT_YEAR
    
    if vin_input:
        if len(vin_input) == 17 and not any(c in vin_input for c in 'IOQ'):
            d_make, d_year = decode_vin(vin_input)
        else:
            st.warning("VIN must be 17 characters and cannot contain I, O, or Q.")
            
    c1, c2, c3, c4 = st.columns(4)
    make_input = c1.text_input("Make", value=d_make)
    model_input = c2.text_input("Model")
    year_input = c3.number_input("Year", min_value=1980, max_value=2030, value=d_year)
    mileage_input = c4.number_input("Mileage", min_value=0, step=1000, value=50000)
    
    rad = st.selectbox("Search Radius", ["25 miles", "50 miles", "100 miles", "200 miles"], index=1)
    
    if st.button("Search Market", type="primary"):
        if not make_input or not model_input:
            st.warning("Please fill Make and Model.")
        else:
            random.seed(f"{vin_input}{make_input}{model_input}{year_input}")
            key = f"{str(make_input).lower()}_{str(model_input).lower().replace(' ', '_')}"
            base_price = BASE_MSRP.get(key, 25000) * (0.85 ** max(0, CURRENT_YEAR - year_input))
            
            listings = []
            for i in range(10):
                listings.append({
                    "Dealer": f"Competitor {i+1}",
                    "City": random.choice(["Local City", "Neighboring Town", "Metro Area"]),
                    "Price": max(5000, base_price + random.randint(-3000, 3000)),
                    "Mileage": max(1000, mileage_input + random.randint(-20000, 20000)),
                    "DOM": random.randint(5, 100),
                    "Certified": random.choice(["Yes", "No"])
                })
            df_mkt = pd.DataFrame(listings)
            
            market_avg_price = df_mkt["Price"].mean()
            market_median_mileage = df_mkt["Mileage"].median()
            
            cpm = calculate_cpm(market_avg_price, year_input, CURRENT_YEAR, auto_cpm, manual_cpm)
            mileage_impact = (market_median_mileage - mileage_input) * cpm
            adjusted_retail = market_avg_price + mileage_impact
            max_buy = (adjusted_retail * (1 - margin_target)) - recon_cost - BUY_FEES
            
            turn_days, source = get_turn_days(make_input, model_input)
            
            if margin_target >= 0.12 and turn_days <= 45:
                st.markdown('<div class="banner-success">AGGRESSIVE BUY</div>', unsafe_allow_html=True)
            elif margin_target < 0.08 or turn_days > 60:
                st.markdown('<div class="banner-error">PASS OR RENEGOTIATE</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="banner-warning">PROCEED WITH CAUTION</div>', unsafe_allow_html=True)
            
            alert = "100K+ CLIFF" if mileage_input >= 100000 else "NEAR 100K" if mileage_input >= 95000 else ""
            if alert: st.markdown(theme.alert_badge(alert), unsafe_allow_html=True)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.subheader("Ceiling Bid")
                st.metric("Max Buy Price", f"${max_buy:,.2f}")
                with st.expander("Show Logic Breakdown"):
                    st.write(f"Adjusted Retail: **${adjusted_retail:,.2f}**")
                    st.write(f"- Margin Target ({margin_target*100:.1f}%): **-${adjusted_retail*margin_target:,.2f}**")
                    st.write(f"- Recon Cost: **-${recon_cost:,.2f}**")
                    st.write(f"- Buy Fees: **-${BUY_FEES:,.2f}**")
            with col_b:
                st.subheader("Mileage Analysis")
                st.metric("Mileage Impact", f"${mileage_impact:,.2f}")
                st.write(f"Your Mileage: **{mileage_input:,}**")
                st.write(f"Market Median: **{market_median_mileage:,.0f}**")
                st.write(f"CPM Used: **${cpm:.3f}/mi**")
            with col_c:
                st.subheader("Market Intel")
                ds_display = f"YOUR Data" if source == "YOUR Data" else f"Industry Avg"
                st.metric("Turn Days", f"{turn_days:.0f}d", help=f"Source: {ds_display}")
                st.write(f"Listing Count: **10**")
                st.write(f"Avg DOM: **{df_mkt['DOM'].mean():.0f}d**")
                st.write(f"Price Range: **${df_mkt['Price'].min():,.0f} - ${df_mkt['Price'].max():,.0f}**")
                
            st.markdown("#### Competitor Listings")
            df_disp = df_mkt.copy()
            df_disp['Price'] = df_disp['Price'].apply(lambda x: f"${x:,.2f}")
            df_disp['Mileage'] = df_disp['Mileage'].apply(lambda x: f"{x:,.0f}")
            df_disp['DOM'] = df_disp['DOM'].apply(lambda x: f"{x}d")
            st.markdown(df_disp.to_html(index=False), unsafe_allow_html=True)


# TAB 3: BATCH PROCESSOR
with tab3:
    st.header("Batch Processor")
    bc1, bc2 = st.columns([3, 1])
    with bc1:
        batch_file = st.file_uploader("Upload Appraisals (CSV/Excel)", type=['csv', 'xlsx'])
    with bc2:
        st.write("")
        st.write("")
        load_sample = st.button("Load Sample", type="primary")
        
    df_batch = None
    if load_sample:
        df_batch = pd.DataFrame([
            {"vin": "1G1AL58FX7", "year": 2021, "make": "Chevrolet", "model": "Equinox", "mileage": 45000, "retail": 22000, "appraisal": 16000},
            {"vin": "JHMCR2F39C", "year": 2019, "make": "Honda", "model": "Accord", "mileage": 98000, "retail": 18500, "appraisal": 13000},
            {"vin": "4T1B11HK5M", "year": 2022, "make": "Toyota", "model": "Camry", "mileage": 25000, "retail": 26000, "appraisal": 20000},
            {"vin": "5XYPK4A63C", "year": 2020, "make": "Kia", "model": "Sportage", "mileage": 105000, "retail": 15000, "appraisal": 11000},
            {"vin": "KM8R54AP1L", "year": 2023, "make": "Hyundai", "model": "Tucson", "mileage": 12000, "retail": 29000, "appraisal": 24000}
        ])
    elif batch_file:
        df_batch = pd.read_csv(batch_file) if batch_file.name.endswith('.csv') else pd.read_excel(batch_file)
            
    if df_batch is not None:
        df_batch.columns = [str(c).lower().strip() for c in df_batch.columns]
        req = ['vin', 'year', 'make', 'model', 'mileage', 'retail', 'appraisal']
        missing = [c for c in req if c not in df_batch.columns]
        
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
        else:
            results = []
            for _, row in df_batch.iterrows():
                expected_miles = max(CURRENT_YEAR - row['year'], 1) * 12000
                cpm = calculate_cpm(row['retail'], row['year'], CURRENT_YEAR, auto_cpm, manual_cpm)
                
                mileage_impact = (expected_miles - row['mileage']) * cpm
                adj_retail = row['retail'] + mileage_impact
                
                max_buy = (adj_retail * (1 - margin_target)) - recon_cost - BUY_FEES
                room = max_buy - row['appraisal']
                
                front_gross = adj_retail - row['appraisal'] - recon_cost - BUY_FEES
                front_margin = front_gross / adj_retail if adj_retail > 0 else 0
                total_deal = front_gross + below_line
                
                turn_days, source = get_turn_days(row['make'], row['model'])
                priority = get_priority(turn_days, front_margin)
                alert = "100K+ CLIFF" if row['mileage'] >= 100000 else "NEAR 100K" if row['mileage'] >= 95000 else ""
                status = "UNDER BUDGET" if room >= 0 else "OVER BUDGET"
                
                results.append({
                    "Priority": priority, "Alert": alert,
                    "Year": row['year'], "Make": row['make'], "Model": row['model'], "Mileage": row['mileage'],
                    "Base Retail": row['retail'], "Mileage Impact": mileage_impact,
                    "Adjusted Retail": adj_retail, "Max Buy": max_buy, "Room": room,
                    "Front Gross": front_gross, "Front Margin": front_margin, "Total Deal": total_deal,
                    "Turn Days": turn_days, "Data Source": source, "Status": status,
                    "_raw_mi": mileage_impact, "_raw_front": front_gross
                })
                
            res_df = pd.DataFrame(results)
            
            st.subheader("Summary Metrics")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vehicle Count", len(res_df))
            c2.metric("Avg Turn", f"{res_df['Turn Days'].mean():.0f}d")
            under = len(res_df[res_df['Room'] >= 0])
            over = len(res_df[res_df['Room'] < 0])
            c3.metric("Under / Over Budget", f"{under} / {over}")
            c4.metric("100K+ Alerts", len(res_df[res_df['Alert'] == '100K+ CLIFF']))
            
            c5, c6, c7 = st.columns(3)
            val_added = res_df[res_df['_raw_mi'] > 0]['_raw_mi'].sum()
            val_deducted = res_df[res_df['_raw_mi'] < 0]['_raw_mi'].sum()
            c5.metric("Net Mileage Impact", f"${val_added + val_deducted:,.2f}")
            c6.metric("Total Front Gross", f"${res_df['_raw_front'].sum():,.2f}")
            c7.metric("Avg Front Margin %", f"{res_df['Front Margin'].mean()*100:.1f}%")
            
            # Format Data for Display
            disp_df = res_df.drop(columns=['_raw_mi', '_raw_front', 'Total Deal']).copy()
            disp_df['Priority'] = disp_df['Priority'].apply(theme.priority_badge)
            disp_df['Alert'] = disp_df['Alert'].apply(theme.alert_badge)
            disp_df['Status'] = disp_df['Status'].apply(theme.status_indicator)
            
            disp_df['Mileage'] = disp_df['Mileage'].apply(lambda x: f"{x:,.0f}")
            for col in ['Base Retail', 'Mileage Impact', 'Adjusted Retail', 'Max Buy', 'Room', 'Front Gross']:
                disp_df[col] = disp_df[col].apply(lambda x: f"${x:,.2f}")
            
            disp_df['Front Margin'] = disp_df['Front Margin'].apply(lambda x: f"{x*100:.1f}%")
            disp_df['Turn Days'] = disp_df['Turn Days'].apply(lambda x: f"{x:.0f}d")
            
            st.markdown("### Results Table")
            st.markdown(disp_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            # Raw CSV data for download
            csv_df = res_df.drop(columns=['_raw_mi', '_raw_front'])
            csv_df['Turn Days'] = csv_df['Turn Days'].apply(lambda x: f"{x:.0f}d")
            csv_df['Front Margin'] = csv_df['Front Margin'].apply(lambda x: f"{x*100:.1f}%")
            csv = csv_df.to_csv(index=False).encode('utf-8')
            
            st.download_button("Download Results CSV", data=csv, file_name="batch_results.csv", mime="text/csv")
