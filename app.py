import streamlit as st
import pandas as pd
import pygsheets
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import io
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ===================== CONFIG =====================
SPREADSHEET_ID = "1dWv4kVugXNFQ2NaodZkawaXRglqRJOWR"  # From your actual spreadsheet
SHEET_GID = "840573777"  # From your URL
SHEET_NAME = "Pri Payment"
SERVICE_FILE = "service_account.json"

st.set_page_config(page_title="Payment Dashboard", layout="wide")

# ===================== AUTO REFRESH SETTINGS =====================
st.sidebar.subheader("🔄 Auto Refresh Settings")

enable_auto = st.sidebar.checkbox("Enable Auto Refresh", value=False)
interval = st.sidebar.number_input("Refresh Interval (seconds)", 10, 300, 60)

if enable_auto:
    st_autorefresh(interval=interval * 1000, key="auto_refresh")

# ===================== CUSTOM CSS FOR DARK THEME =====================
st.markdown("""
<style>
    /* Main background */
    .main .block-container {
        padding-top: 2rem;
        background-color: #0E1117;
    }
    
    /* Metric cards styling */
    .metric-card {
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.4);
    }
    
    .metric-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #94A3B8;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #374151;
    }
    
    /* Status summary styling */
    .status-summary {
        background: #1E293B;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #374151;
        margin-bottom: 1rem;
    }
    
    .status-item {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid #374151;
    }
    
    .status-item:last-child {
        border-bottom: none;
    }
    
    /* Chart container */
    .chart-container {
        background: #1E293B;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #374151;
        margin-bottom: 1rem;
    }
    
    /* KPI row styling */
    .kpi-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ===================== DATA LOADING FUNCTIONS =====================
def clean_colname(x):
    x = str(x).strip().lower()
    x = re.sub(r"[^0-9a-zA-Z_ ]", "", x)
    x = x.replace(" ", "_")
    return x if x else "col"

def clean_num(x):
    if x is None:
        return 0.0
    x = str(x).strip()
    x = re.sub(r"[^\d\.\-]", "", x)
    return float(x) if x.replace('.', '', 1).isdigit() else 0.0

def safe_num(v):
    try:
        if pd.isna(v) or v == "" or str(v).strip() == "":
            return 0.0
        # Remove currency symbols and commas
        v_clean = str(v).replace('₹', '').replace(',', '').replace(' ', '').strip()
        return float(v_clean)
    except:
        return 0.0

def parse_date(v):
    try:
        return pd.to_datetime(v, dayfirst=True, errors="coerce")
    except:
        return pd.NaT

# ===================== LOAD VIA SERVICE ACCOUNT =====================
@st.cache_data(ttl=120)
def load_via_service():
    try:
        gc = pygsheets.authorize(service_file=SERVICE_FILE)
        
        # Open by ID (most reliable method)
        sh = gc.open_by_key(SPREADSHEET_ID)
        st.sidebar.success(f"📊 Opened: {sh.title}")
        
        # Try to get the specific sheet by GID
        try:
            wks = sh.worksheet(property='id', value=SHEET_GID)
            st.sidebar.info(f"📑 Using sheet: {wks.title} (GID: {SHEET_GID})")
        except:
            # Fallback to first sheet
            wks = sh[0]
            st.sidebar.warning(f"⚠️ Using first sheet: {wks.title}")
        
        # Get all data
        data = wks.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            st.sidebar.warning("📭 Loaded empty dataframe")
            return None
            
        st.sidebar.success(f"✅ Loaded {len(df)} records via Service Account")
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ Service Account failed: {str(e)}")
        return None

# ===================== LOAD VIA CSV EXPORT =====================
@st.cache_data(ttl=120)
def load_via_csv():
    try:
        # Using your exact GID from the URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={SHEET_GID}"
        
        # Add cache busting to avoid stale data
        df = pd.read_csv(csv_url)
        
        if df.empty:
            st.sidebar.warning("📭 CSV loaded but empty")
            return None
            
        st.sidebar.success(f"✅ Loaded {len(df)} records via CSV")
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ CSV Export failed: {str(e)}")
        return None

# ===================== DEMO DATA (Fallback) =====================
def load_demo_data():
    """Load demo data matching your expected structure"""
    demo_data = {
        'Unit Name': ['Unit A', 'Unit B', 'Unit C', 'Unit D'],
        'Work Order No': ['WO001', 'WO002', 'WO003', 'WO004'],
        'Order Amount': ['79,290,940.00', '65,000,000.00', '45,500,000.00', '38,750,000.00'],
        'Final Amount': ['91,102,303.30', '75,000,000.00', '52,500,000.00', '44,750,000.00'],
        'Payment Received': ['36,923,263.30', '30,000,000.00', '25,000,000.00', '18,500,000.00'],
        'Pending Amount': ['0.00', '0.00', '0.00', '0.00'],
        'Payment Mode': ['Online', 'Cash', 'Cheque', 'Cash and Online'],
        'Work Status': ['Completed', 'In Progress', 'Pending', 'Completed'],
        'Date': ['01/01/2024', '15/01/2024', '20/01/2024', '25/01/2024']
    }
    return pd.DataFrame(demo_data)

# ===================== MAIN DATA LOADING LOGIC =====================
def load_data():
    st.sidebar.header("🔧 Data Configuration")
    
    # Display current configuration
    st.sidebar.info(f"""
    **Current Setup:**
    - Spreadsheet: `{SPREADSHEET_ID}`
    - Sheet GID: `{SHEET_GID}`
    """)
    
    # Data source selection
    data_source = st.sidebar.radio(
        "Select Data Source:",
        ["CSV Export (Recommended)", "Service Account", "Demo Data"],
        index=0
    )
    
    df = None
    
    if data_source == "Service Account":
        df = load_via_service()
        if df is None:
            st.sidebar.warning("🔄 Falling back to CSV Export...")
            df = load_via_csv()
            
    elif data_source == "CSV Export":
        df = load_via_csv()
        
    else:  # Demo Data
        df = load_demo_data()
        st.sidebar.info("📋 Using Demo Data for display")
    
    # Final fallback to demo data
    if df is None or df.empty:
        st.error("❌ Could not load data from either source. Using demo data.")
        df = load_demo_data()
        st.warning("⚠️ Displaying DEMO DATA - Check your spreadsheet sharing settings")
    
    return process_raw_data(df)

def process_raw_data(df):
    """Process and clean the raw data"""
    # Create a clean copy
    df_clean = df.copy()
    
    # Clean column names
    df_clean.columns = [clean_colname(c) for c in df_clean.columns]
    
    # Debug info
    with st.sidebar.expander("🔍 Debug Info"):
        st.write("Original columns:", list(df.columns))
        st.write("Cleaned columns:", list(df_clean.columns))
        if not df_clean.empty:
            st.write("First row sample:", df_clean.iloc[0].to_dict())
        st.write("Data types:", df_clean.dtypes.astype(str))
    
    # Flexible column mapping - handle different possible column names
    column_mapping = {
        'unit_name': ['unit_name', 'unit', 'unitname', 'name'],
        'work_order_no': ['work_order_no', 'work_order', 'wo_no', 'order_no', 'workorder'],
        'order_amount': ['order_amount', 'order', 'amount', 'order_amt'],
        'final_amount': ['final_amount', 'final', 'final_amt', 'total_amount'],
        'payment_received': ['payment_received', 'received', 'paid', 'payment_received'],
        'pending_amount': ['pending_amount', 'pending', 'balance', 'due_amount'],
        'payment_mode': ['payment_mode', 'mode', 'payment_type', 'type'],
        'work_status': ['work_status', 'status', 'job_status'],
        'p_date': ['p_date', 'date', 'payment_date', 'transaction_date']
    }
    
    # Apply column mapping
    for standard_name, possible_names in column_mapping.items():
        for possible_name in possible_names:
            if possible_name in df_clean.columns and standard_name not in df_clean.columns:
                df_clean.rename(columns={possible_name: standard_name}, inplace=True)
                break
    
    # Ensure required columns exist
    for col in ['order_amount', 'final_amount', 'payment_received', 'pending_amount']:
        if col not in df_clean.columns:
            df_clean[col] = 0.0
            st.sidebar.warning(f"⚠️ Column '{col}' not found, using defaults")
    
    # Convert numeric columns
    for col in ['order_amount', 'final_amount', 'payment_received', 'pending_amount']:
        df_clean[col] = df_clean[col].apply(safe_num)
    
    # Calculate pending amount if not properly set
    df_clean["pending_amount"] = df_clean["final_amount"] - df_clean["payment_received"]
    
    # Process work status
    if 'work_status' not in df_clean.columns:
        df_clean['work_status'] = 'Unknown'
    else:
        df_clean['work_status'] = df_clean['work_status'].fillna('Unknown').astype(str).str.strip()
    
    # Process dates
    if 'p_date' in df_clean.columns:
        df_clean['payment_date'] = df_clean['p_date'].apply(parse_date)
        df_clean['year'] = df_clean['payment_date'].dt.year.fillna(2024).astype(int)
    else:
        df_clean['year'] = 2024
    
    return df_clean

# ===================== MAIN APP =====================
def main():
    st.title("💼 Payment Dashboard")
    
    # 🔄 REFRESH BUTTON
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    df = load_data()
    
    if df.empty:
        st.warning("No data loaded. Please check your connection and try again.")
        st.stop()
    
    # ===================== KPIs =====================
    total_order = df["order_amount"].sum()
    total_final = df["final_amount"].sum()
    total_received = df["payment_received"].sum()
    total_pending = df["pending_amount"].sum()
    
    st.markdown('<div class="section-header">📈 Key Performance Indicators</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Order Amount</div>
                <div class="metric-value">₹ {total_order:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Final Amount</div>
                <div class="metric-value">₹ {total_final:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Received</div>
                <div class="metric-value">₹ {total_received:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Pending</div>
                <div class="metric-value">₹ {total_pending:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ===================== PIE CHARTS SECTION =====================
    st.markdown('<div class="section-header">💰 Payment Analytics</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Pie chart: Pending vs Received
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("**Pending vs Received**")
        
        pie_df = pd.DataFrame({
            "Status": ["Received", "Pending"],
            "Amount": [total_received, total_pending]
        })
        
        colors = ['#10B981', '#EF4444']  # Green for received, Red for pending
        
        fig = px.pie(pie_df, names="Status", values="Amount", hole=0.45,
                     color_discrete_sequence=colors)
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Pie chart: Payment mode distribution
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("**Payment Mode Distribution**")
        
        if "payment_mode" in df.columns and not df["payment_mode"].empty:
            mode_df = df.groupby("payment_mode")["payment_received"].sum().reset_index()
            mode_df = mode_df[mode_df["payment_received"] > 0]  # Filter out zero values
            
            if not mode_df.empty:
                fig2 = px.pie(mode_df, names="payment_mode", values="payment_received", 
                             hole=0.45, color_discrete_sequence=px.colors.qualitative.Set3)
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="white",
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=400
                )
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No payment mode data available")
        else:
            st.info("Payment Mode column not available")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ===================== STATUS WISE PENDING PIE CHART =====================
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("**Status-wise Pending Distribution**")
        
        status_pending = df.groupby("work_status")["pending_amount"].sum().reset_index()
        status_pending = status_pending[status_pending["pending_amount"] > 0]
        
        if not status_pending.empty:
            fig3 = px.pie(status_pending, names="work_status", values="pending_amount", 
                         hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig3.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="white",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=400
            )
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No pending amounts by status")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ===================== STATUS WISE SUMMARY =====================
    with col2:
        st.markdown('<div class="status-summary">', unsafe_allow_html=True)
        st.markdown("**Status-wise Summary**")
        
        summary = df.groupby("work_status").agg(
            count=("work_status", "count"),
            actual_pending=("pending_amount", "sum"),
            total_final=("final_amount", "sum"),
            total_received=("payment_received", "sum")
        ).reset_index()
        
        for _, row in summary.iterrows():
            if row["work_status"].lower() == "completed":
                pending_display = 0.0  # Completed should have 0 pending
                status_color = "#10B981"  # Green for completed
            else:
                pending_display = row["actual_pending"]
                status_color = "#F59E0B"  # Amber for pending
            
            st.markdown(f"""
                <div class="status-item">
                    <span style="color: {status_color}; font-weight: 600;">{row['work_status']}</span>
                    <span>Count: {row['count']} | ₹ {pending_display:,.2f}</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ===================== YEARLY SUMMARY CHART =====================
    st.markdown('<div class="section-header">📅 Year-wise Summary</div>', unsafe_allow_html=True)
    
    if 'year' in df.columns:
        yearly_data = df.groupby('year')[
            ['order_amount', 'final_amount', 'payment_received', 'pending_amount']
        ].sum().reset_index()
        
        if not yearly_data.empty:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig4 = px.bar(
                yearly_data,
                x='year',
                y=['order_amount', 'final_amount', 'payment_received'],
                title='Year-wise Amount Comparison',
                labels={'value': 'Amount (₹)', 'year': 'Year', 'variable': 'Type'},
                barmode='group',
                color_discrete_sequence=['#3B82F6', '#8B5CF6', '#10B981']
            )
            fig4.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # ===================== FILTERS SECTION =====================
    st.markdown('<div class="section-header">🔍 Filter Records</div>', unsafe_allow_html=True)
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        # Status filter
        status_options = ["All"] + list(df["work_status"].unique())
        selected_status = st.selectbox("Filter by Status", status_options)
    
    with filter_col2:
        # Payment mode filter
        if "payment_mode" in df.columns:
            mode_options = ["All"] + list(df["payment_mode"].unique())
            selected_mode = st.selectbox("Filter by Payment Mode", mode_options)
        else:
            selected_mode = "All"
    
    with filter_col3:
        # Amount range filter
        min_amount = float(df["final_amount"].min())
        max_amount = float(df["final_amount"].max())
        amount_range = st.slider(
            "Filter by Final Amount Range (₹)",
            min_value=min_amount,
            max_value=max_amount,
            value=(min_amount, max_amount)
        )
    
    # Apply filters
    filtered_df = df.copy()
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["work_status"] == selected_status]
    
    if selected_mode != "All" and "payment_mode" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["payment_mode"] == selected_mode]
    
    filtered_df = filtered_df[
        (filtered_df["final_amount"] >= amount_range[0]) & 
        (filtered_df["final_amount"] <= amount_range[1])
    ]
    
    # ===================== RECORDS TABLE =====================
    st.markdown('<div class="section-header">📋 Detailed Records</div>', unsafe_allow_html=True)
    
    # Display filtered results summary
    st.metric("Filtered Records", len(filtered_df))
    
    # Data table with better styling
    display_columns = []
    for col in ['unit_name', 'work_order_no', 'order_amount', 'final_amount', 
                'payment_received', 'pending_amount', 'payment_mode', 'work_status', 'p_date']:
        if col in filtered_df.columns:
            display_columns.append(col)
    
    if display_columns:
        st.dataframe(
            filtered_df[display_columns],
            use_container_width=True,
            height=400
        )
    else:
        st.dataframe(filtered_df, use_container_width=True, height=400)
    
    # ===================== DOWNLOAD SECTION =====================
    st.markdown("---")
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Filtered CSV", 
        csv, 
        "filtered_payment_data.csv",
        type="primary"
    )
    
    # ===================== FOOTER =====================
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6B7280; font-size: 0.8rem;'>"
        "Payment Dashboard • Built with Streamlit • Data updates automatically"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

