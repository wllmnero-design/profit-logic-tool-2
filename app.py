import streamlit as st
import pandas as pd
import random
import re
import requests
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

# Extensive Make/Model database for dropdowns
VEHICLE_DB = {
    "Chevrolet": ["Silverado 1500", "Equinox", "Malibu", "Tahoe", "Traverse", "Colorado", "Trax", "Suburban"],
    "Ford": ["F-150", "Escape", "Explorer", "Edge", "Mustang", "Bronco", "Ranger", "Expedition"],
    "Honda": ["Accord", "Civic", "CR-V", "Pilot", "Odyssey", "HR-V", "Ridgeline"],
    "Hyundai": ["Tucson", "Elantra", "Sonata", "Santa Fe", "Palisade", "Kona", "Venue"],
    "Kia": ["Sportage", "Sorento", "Telluride", "Optima", "K5", "Forte", "Soul", "Carnival"],
    "Nissan": ["Rogue", "Altima", "Sentra", "Pathfinder", "Frontier", "Murano", "Kicks"],
    "Toyota": ["Camry", "RAV4", "Corolla", "Highlander", "Tacoma", "Tundra", "4Runner", "Sienna"],
    "Genesis": ["G70", "G80", "G90", "GV70", "GV80"],
    "Jeep": ["Grand Cherokee", "Wrangler", "Cherokee", "Compass", "Gladiator"],
    "Subaru": ["Outback", "Forester", "Crosstrek", "Ascent", "Impreza", "Legacy"],
    "Volkswagen": ["Jetta", "Tiguan", "Atlas", "Taos", "Golf"],
    "Other": ["Other Model"]
}

BASE_MSRP = {
    'hyundai_tucson': 26000, 'hyundai_elantra': 21000, 'hyundai_sonata': 25000,
    'nissan_rogue': 28000, 'nissan_altima': 25000, 'toyota_camry': 27000,
    'toyota_rav4': 29000, 'honda_accord': 28000, 'kia_sportage': 27000,
    'genesis_gv70': 45000, 'chevrolet_equinox': 26000, 'ford_escape': 27000
}

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if 'dealer_turn_data' not in st.session_state: st.session_state.dealer_turn_data = {}
if 'dealer_gross_data' not in st.session_state: st.session_state.dealer_gross_data = {}
if 'sales_summary' not in st.session_state: st.session_state.sales_summary = None

# VIN Decoder State
if 'dec_make' not in st.session_state: st.session_state.dec_make = "Kia"
if 'dec_model' not in st.session_state: st.session_state.dec_model = "Sportage"
if 'dec_year' not in st.session_state: st.session_state.dec_year = 2020

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
    try: return -float(val_str) if is_neg else float(val_str)
    except ValueError: return 0.0

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

@st.cache_data(show_spinner=False)
def decode_vin_nhtsa(vin):
    """Pings the free US Govt NHTSA API to fully decode Make, Model, and Year"""
    if len(vin) != 17 or any(c in vin for c in 'IOQ'): return "", "", CURRENT_YEAR - 3
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()['Results'][0]
            make = data.get('Make', '').title()
            model = data.get('Model', '').title()
            try: year = int(data.get('ModelYear', ''))
            except ValueError: year = CURRENT_YEAR - 3
            return make, model, year
    except Exception: pass
    return "", "", CURRENT_YEAR - 3

def generate_vauto_market_data(make, model, year, target_mileage, radius, zip_code):
    """
    FUTURE API PLUG-IN: Replace this mock logic with a call to MarketCheck API.
    Example: requests.get(f"https://api.marketcheck.com/v2/search/car/active?api_key=YOUR_KEY...")
    """
    key = f"{str(make).lower()}_{str(model).lower().replace(' ', '_')}"
    base_price = BASE_MSRP.get(key, 25000) * (0.85 ** max(0, CURRENT_YEAR - year))
    
    # Generate 15 to 30 simulated live listings within the radius
    random.seed(f"{make}{model}{year}{zip_code}")
    num_listings = random.randint(18, 35) 
    rad_int = int(radius.replace(" miles", ""))
    
    sellers = ["SUN STATE FORD", "MAZDA OF WESLEY...", "GETTEL STADIUM...", "Prime Leasing and Sales", "CAR SELECT LLC", "Universal Nissan", "OFFLEASE ORLANDO", "C & L MOTORS"]
    colors = ["Blue", "Black", "Gray", "Silver", "White", "Red"]
    interiors = ["Black Cloth", "Gray Cloth", "Black Leather", "Beige Leather"]
    
    listings = []
    for i in range(num_listings):
        price_var = random.gauss(0, 1500)
        mileage_var = random.gauss(0, 15000)
        dist = random.randint(0, rad_int)
        
        listings.append({
            "Vehicle": f"{year} {make} {model}",
            "Color": random.choice(colors),
            "Interior": random.choice(interiors),
            "List Price": max(4000, int(base_price - ((target_mileage + mileage_var - target_mileage) * 0.08) + price_var)),
            "Odometer (mi)": max(1000, int(target_mileage + mileage_var)),
            "Age": int(abs(random.gauss(45, 30))),
            "Distance (mi)": dist,
            "Seller": random.choice(sellers),
            "VDP": "🔗 Link"
        })
    
    df = pd.DataFrame(listings)
    # Sort by price ascending to match vAuto default Rank
    df = df.sort_values(by="List Price", ascending=True).reset_index(drop=True)
    df.insert(0, "Rank", df.index + 1)
    
    # Randomize vRank (vAuto's proprietary value rank)
    v_ranks = list(range(1, len(df) + 1))
    random.shuffle(v_ranks)
    df.insert(1, "vRank", v_ranks)
    
    return df

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
tab1, tab2, tab3 = st.tabs(["Single VIN Lookup", "Sales Performance", "Batch Processor"])

# TAB 2 IS NOW TAB 1: SINGLE VIN LOOKUP (VAUTO OVERHAUL)
with tab1:
    st.header("Single VIN Appraisal")
    
    # VIN Input & Decode logic
    vin_col, zip_col = st.columns([3, 1])
    vin_input = vin_col.text_input("VIN (17 characters) - Live NHTSA Decoding", max_chars=17).upper()
    zip_code = zip_col.text_input("Origin Zip Code", value="32801")
    
    if vin_input and len(vin_input) == 17:
        with st.spinner("Decoding via US Govt Database..."):
            d_make, d_model, d_year = decode_vin_nhtsa(vin_input)
            if d_make:
                st.session_state.dec_make = d_make
                st.session_state.dec_model = d_model
                st.session_state.dec_year = d_year
                st.success(f"Decoded: {d_year} {d_make} {d_model}")
            else:
                st.error("Invalid VIN or not found in NHTSA database.")
                
    c1, c2, c3, c4 = st.columns(4)
    
    # Make Dropdown logic
    makes_list = list(VEHICLE_DB.keys())
    if st.session_state.dec_make not in makes_list: makes_list.append(st.session_state.dec_make)
    make_idx = makes_list.index(st.session_state.dec_make) if st.session_state.dec_make in makes_list else 0
    make_input = c1.selectbox("Make", makes_list, index=make_idx)
    
    # Model Dropdown logic
    models_list = VEHICLE_DB.get(make_input, [])
    if st.session_state.dec_model not in models_list: models_list.insert(0, st.session_state.dec_model)
    if not models_list: models_list = ["Other Model"]
    model_input = c2.selectbox("Model", models_list)
    
    year_input = c3.number_input("Year", min_value=1980, max_value=2030, value=st.session_state.dec_year)
    mileage_input = c4.number_input("Mileage", min_value=0, step=1000, value=50000)
    
    rad = st.selectbox("Market Search Radius", ["25 miles", "50 miles", "100 miles", "200 miles"], index=1)
    
    if st.button("Search Market", type="primary"):
        if not make_input or not model_input:
            st.warning("Please fill Make and Model.")
        else:
            # Fetch simulated data to match vAuto format
            df_mkt = generate_vauto_market_data(make_input, model_input, year_input, mileage_input, rad, zip_code)
            
            market_avg_price = df_mkt["List Price"].mean()
            market_median_mileage = df_mkt["Odometer (mi)"].median()
            avg_dom = df_mkt["Age"].mean()
            
            cpm = calculate_cpm(market_avg_price, year_input, CURRENT_YEAR, auto_cpm, manual_cpm)
            mileage_impact = (market_median_mileage - mileage_input) * cpm
            adjusted_retail = market_avg_price + mileage_impact
            max_buy = (adjusted_retail * (1 - margin_target)) - recon_cost - BUY_FEES
            
            st.markdown("---")
            
            # VAUTO STYLE METRICS OVERVIEW
            col_target, col_market, col_books = st.columns([1.2, 1.8, 1])
            
            with col_target:
                st.markdown("### Pricing Analysis")
                st.metric("Recommended Max Buy", f"${max_buy:,.0f}")
                st.write(f"Adjusted Retail: **${adjusted_retail:,.0f}**")
                st.write(f"Recon & Fees: **-${recon_cost + BUY_FEES:,.0f}**")
                st.write(f"Target Margin: **{margin_target*100:.0f}%**")
                st.caption(f"Used CPM: ${cpm:.3f}/mi")
                
            with col_market:
                st.markdown("### Market Overview")
                mc1, mc2, mc3 = st.columns(3)
                
                price_diff = market_avg_price - adjusted_retail
                mc1.metric("Avg. Price", f"${market_avg_price:,.0f}", f"${abs(price_diff):,.0f} {'below' if price_diff > 0 else 'above'}", delta_color="inverse")
                
                odo_diff = market_median_mileage - mileage_input
                mc2.metric("Avg. Odometer", f"{market_median_mileage:,.0f}", f"{abs(odo_diff):,.0f} mi. {'above' if odo_diff > 0 else 'below'}", delta_color="inverse")
                
                mc3.metric("Mkt. Days Supply", f"{int(avg_dom)}", "Overall | Like Mine")
                
            with col_books:
                st.markdown("### Books (Est.)")
                st.write(f"Black Book: **${market_avg_price * 0.92:,.0f}**")
                st.write(f"KBB.com: **${market_avg_price * 1.05:,.0f}**")
                st.write(f"MMR: **${market_avg_price * 0.88:,.0f}**")

            st.markdown("---")
            
            # VAUTO STYLE COMPETITIVE SET TABLE
            st.markdown(f"### Competitive Set ({len(df_mkt)} Vehicles)")
            
            # Format dataframe for clean display with HTML for Color/Interior
            df_disp = df_mkt.copy()
            df_disp["Vehicle"] = df_disp["Vehicle"] + "<br><span style='font-size: 0.8em; color: gray;'>Color: " + df_disp["Color"] + " | Interior: " + df_disp["Interior"] + "</span>"
            df_disp["List Price"] = df_disp["List Price"].apply(lambda x: f"${x:,.0f}")
            df_disp["Odometer (mi)"] = df_disp["Odometer (mi)"].apply(lambda x: f"{x:,.0f}")
            
            df_disp = df_disp[["Rank", "vRank", "Vehicle", "List Price", "Odometer (mi)", "Age", "Distance (mi)", "Seller", "VDP"]]
            
            # To render the HTML inside the dataframe correctly in Streamlit, we must use to_html
            st.markdown(df_disp.to_html(escape=False, index=False), unsafe_allow_html=True)


# TAB 2: SALES PERFORMANCE (DATA UPLOAD)
with tab2:
    st.header("Sales Performance Data")
    st.markdown("""
    <div class="info-box">
    Upload your dealer's DMS sales log (CSV or Excel) to extract custom turn rates and gross averages by Make/Model. 
    The logic engine will automatically apply your proprietary data.
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
                st.error(f"Missing expected columns: {', '.join(missing)}")
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
            
            csv_df = res_df.drop(columns=['_raw_mi', '_raw_front'])
            csv_df['Turn Days'] = csv_df['Turn Days'].apply(lambda x: f"{x:.0f}d")
            csv_df['Front Margin'] = csv_df['Front Margin'].apply(lambda x: f"{x*100:.1f}%")
            csv = csv_df.to_csv(index=False).encode('utf-8')
            
            st.download_button("Download Results CSV", data=csv, file_name="batch_results.csv", mime="text/csv")
