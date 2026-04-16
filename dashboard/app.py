import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="UAC Care System Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and header
st.title("🏥 Unaccompanied Children Care System Dashboard")
st.markdown("### System Capacity & Care Load Analytics")
st.markdown("*Real-time monitoring of federal care system capacity and load*")
st.markdown("---")

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('data/processed/uac_data_clean.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    return df

try:
    df = load_data()
    st.success(f"✅ Data loaded successfully! ({len(df)} records from {df['Date'].min().strftime('%B %Y')} to {df['Date'].max().strftime('%B %Y')})")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Calculate additional metrics if they don't exist
if 'Load_Volatility' not in df.columns:
    df['Load_Volatility'] = df['Total_System_Load'].rolling(30).std() / df['Total_System_Load'].rolling(30).mean() * 100

# Calculate KPIs for original data
total_system_load = df['Total_System_Load']
stress_threshold_original = total_system_load.quantile(0.85)
df['Stress_Period'] = total_system_load > stress_threshold_original
df['Backlog_Indicator'] = df['Net_Daily_Intake'] > 0
df['Cumulative_Backlog'] = df['Net_Daily_Intake'].cumsum()

# Sidebar filters
st.sidebar.header("📊 Dashboard Controls")

# Date range filter
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Metric toggles
st.sidebar.subheader("Display Options")
show_cbp = st.sidebar.checkbox("Show CBP Custody", value=True)
show_hhs = st.sidebar.checkbox("Show HHS Care", value=True)
show_stress = st.sidebar.checkbox("Show Stress Threshold", value=True)
show_rolling = st.sidebar.checkbox("Show 7-Day Average", value=True)

# Time granularity
granularity = st.sidebar.selectbox(
    "Time Granularity",
    ["Daily", "Weekly", "Monthly"]
)

# Filter data based on date range
if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
    df_filtered = df[mask].copy()
else:
    df_filtered = df.copy()

# Apply granularity
if granularity == "Weekly":
    df_filtered = df_filtered.resample('W', on='Date').mean().reset_index()
elif granularity == "Monthly":
    df_filtered = df_filtered.resample('M', on='Date').mean().reset_index()

# RECALCULATE derived columns after filtering and resampling (FIX FOR THE ERROR)
stress_threshold = df_filtered['Total_System_Load'].quantile(0.85)
df_filtered['Stress_Period'] = df_filtered['Total_System_Load'] > stress_threshold
df_filtered['Backlog_Indicator'] = df_filtered['Net_Daily_Intake'] > 0
df_filtered['Cumulative_Backlog'] = df_filtered['Net_Daily_Intake'].cumsum()

# Ensure 7-day rolling average exists
if '7day_avg_load' not in df_filtered.columns:
    df_filtered['7day_avg_load'] = df_filtered['Total_System_Load'].rolling(7).mean()

# KPI Row
st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    current_load = df_filtered['Total_System_Load'].iloc[-1]
    avg_load = df_filtered['Total_System_Load'].mean()
    delta_load = ((current_load/avg_load)-1)*100 if avg_load > 0 else 0
    st.metric(
        "Total Children Under Care",
        f"{current_load:,.0f}",
        delta=f"{delta_load:.1f}% vs avg",
        help="Current total children in CBP + HHS custody"
    )

with col2:
    current_cbp = df_filtered['Children in CBP custody'].iloc[-1]
    st.metric(
        "CBP Custody",
        f"{current_cbp:,.0f}",
        help="Children currently in CBP custody"
    )

with col3:
    current_hhs = df_filtered['Children in HHS Care'].iloc[-1]
    st.metric(
        "HHS Care",
        f"{current_hhs:,.0f}",
        help="Children currently in HHS care"
    )

with col4:
    net_intake = df_filtered['Net_Daily_Intake'].iloc[-1]
    st.metric(
        "Net Intake Pressure",
        f"{net_intake:,.0f}",
        delta="Inflow" if net_intake > 0 else "Outflow",
        help="Daily transfers minus discharges"
    )

with col5:
    stress_days = df_filtered['Stress_Period'].sum()
    stress_pct = (stress_days / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
    st.metric(
        "Stress Days",
        f"{int(stress_days)} days",
        delta=f"{stress_pct:.1f}% of period",
        help="Days above stress threshold (85th percentile)"
    )

st.markdown("---")

# Main Dashboard Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 System Load Overview",
    "🔄 CBP vs HHS Comparison",
    "📉 Net Intake & Backlog",
    "⚠️ Stress Period Analysis",
    "📋 KPI Summary"
])

with tab1:
    st.subheader("System Load Over Time")
    
    # Create system load chart
    fig = go.Figure()
    
    if show_cbp:
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Children in CBP custody'],
            name='CBP Custody',
            fill='tozeroy',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='Date: %{x}<br>CBP: %{y:,.0f}<extra></extra>'
        ))
    
    if show_hhs:
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Children in HHS Care'],
            name='HHS Care',
            fill='tonexty',
            line=dict(color='#ff7f0e', width=2),
            hovertemplate='Date: %{x}<br>HHS: %{y:,.0f}<extra></extra>'
        ))
    
    if show_rolling and '7day_avg_load' in df_filtered.columns:
        fig.add_trace(go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['7day_avg_load'],
            name='7-Day Average',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='Date: %{x}<br>7-Day Avg: %{y:,.0f}<extra></extra>'
        ))
    
    if show_stress:
        fig.add_hline(
            y=stress_threshold,
            line_dash="dash",
            line_color="red",
            opacity=0.5,
            annotation_text=f"Stress Threshold: {stress_threshold:,.0f}",
            annotation_position="top right"
        )
    
    fig.update_layout(
        height=500,
        hovermode='x unified',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=50, r=50, t=30, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Key insights
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📊 **Peak System Load**: {df_filtered['Total_System_Load'].max():,.0f} children")
    with col2:
        st.info(f"📈 **Average System Load**: {df_filtered['Total_System_Load'].mean():,.0f} children")

with tab2:
    st.subheader("CBP vs HHS Load Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart for current distribution
        current_cbp = df_filtered['Children in CBP custody'].iloc[-1]
        current_hhs = df_filtered['Children in HHS Care'].iloc[-1]
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['CBP Custody', 'HHS Care'],
            values=[current_cbp, current_hhs],
            hole=.3,
            marker_colors=['#1f77b4', '#ff7f0e']
        )])
        fig_pie.update_layout(title=f"Current Load Distribution (Total: {current_cbp + current_hhs:,.0f})")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Area chart for comparison
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Children in CBP custody'],
            name='CBP',
            fill='tozeroy',
            line=dict(color='#1f77b4')
        ))
        fig_area.add_trace(go.Scatter(
            x=df_filtered['Date'],
            y=df_filtered['Children in HHS Care'],
            name='HHS',
            fill='tonexty',
            line=dict(color='#ff7f0e')
        ))
        fig_area.update_layout(title="Load Distribution Over Time", height=400)
        st.plotly_chart(fig_area, use_container_width=True)

with tab3:
    st.subheader("Net Intake & Backlog Trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Net intake bar chart
        fig_intake = px.bar(
            df_filtered,
            x='Date',
            y='Net_Daily_Intake',
            title='Daily Net Intake (Inflow - Outflow)',
            color=df_filtered['Net_Daily_Intake'] > 0,
            color_discrete_map={True: '#2ecc71', False: '#e74c3c'}
        )
        fig_intake.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_intake, use_container_width=True)
    
    with col2:
        # Cumulative backlog
        fig_backlog = px.line(
            df_filtered,
            x='Date',
            y='Cumulative_Backlog',
            title='Cumulative Backlog Over Time'
        )
        fig_backlog.update_layout(height=400)
        st.plotly_chart(fig_backlog, use_container_width=True)
    
    # Backlog metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Backlog", f"{df_filtered['Cumulative_Backlog'].iloc[-1]:,.0f}")
    with col2:
        backlog_days = (df_filtered['Net_Daily_Intake'] > 0).sum()
        st.metric("Days with Positive Intake", f"{backlog_days}")
    with col3:
        total_transfers = df_filtered['Children transferred out of CBP custody'].sum()
        total_discharges = df_filtered['Children discharged from HHS Care'].sum()
        discharge_ratio = (total_discharges / total_transfers * 100) if total_transfers > 0 else 0
        st.metric("Discharge Offset Ratio", f"{discharge_ratio:.1f}%")

with tab4:
    st.subheader("Stress Period Analysis")
    
    # Highlight stress periods
    stress_df = df_filtered[df_filtered['Stress_Period']]
    
    fig_stress = go.Figure()
    fig_stress.add_trace(go.Scatter(
        x=df_filtered['Date'],
        y=df_filtered['Total_System_Load'],
        name='System Load',
        line=dict(color='blue', width=2)
    ))
    
    # Highlight stress periods
    if len(stress_df) > 0:
        fig_stress.add_trace(go.Scatter(
            x=stress_df['Date'],
            y=stress_df['Total_System_Load'],
            name='Stress Periods',
            mode='markers',
            marker=dict(color='red', size=8, symbol='circle'),
            hovertemplate='Stress Period: %{x}<br>Load: %{y:,.0f}<extra></extra>'
        ))
    
    fig_stress.add_hline(
        y=stress_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Stress Threshold: {stress_threshold:,.0f}"
    )
    
    fig_stress.update_layout(height=500)
    st.plotly_chart(fig_stress, use_container_width=True)
    
    # Stress period details
    if len(stress_df) > 0:
        st.subheader("📅 Identified Stress Periods")
        st.dataframe(
            stress_df[['Date', 'Total_System_Load', 'Children in CBP custody', 
                      'Children in HHS Care', 'Net_Daily_Intake']].sort_values('Date', ascending=False),
            use_container_width=True
        )

with tab5:
    st.subheader("Comprehensive KPI Summary")
    
    # Calculate all KPIs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 System Load KPIs")
        kpi_data = {
            "Metric": [
                "Total Children Under Care (Avg)",
                "Peak System Load",
                "Minimum System Load",
                "Current System Load",
                "Load Volatility (Avg)"
            ],
            "Value": [
                f"{df_filtered['Total_System_Load'].mean():,.0f}",
                f"{df_filtered['Total_System_Load'].max():,.0f}",
                f"{df_filtered['Total_System_Load'].min():,.0f}",
                f"{df_filtered['Total_System_Load'].iloc[-1]:,.0f}",
                f"{df_filtered['Load_Volatility'].mean():.2f}%" if 'Load_Volatility' in df_filtered.columns else "N/A"
            ]
        }
        st.dataframe(pd.DataFrame(kpi_data), use_container_width=True)
    
    with col2:
        st.markdown("### 🔄 Flow KPIs")
        total_transfers = df_filtered['Children transferred out of CBP custody'].sum()
        total_discharges = df_filtered['Children discharged from HHS Care'].sum()
        flow_data = {
            "Metric": [
                "Total CBP Intakes",
                "Total HHS Transfers",
                "Total Discharges",
                "Average Net Intake",
                "Discharge Offset Ratio",
                "Backlog Accumulation"
            ],
            "Value": [
                f"{df_filtered['Children apprehended and placed in CBP custody'].sum():,.0f}",
                f"{total_transfers:,.0f}",
                f"{total_discharges:,.0f}",
                f"{df_filtered['Net_Daily_Intake'].mean():.1f}",
                f"{(total_discharges / total_transfers * 100):.1f}%" if total_transfers > 0 else "N/A",
                f"{df_filtered['Cumulative_Backlog'].iloc[-1]:,.0f}"
            ]
        }
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True)
    
    # Summary statistics
    st.markdown("### 📈 Period Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Date Range", f"{df_filtered['Date'].min().strftime('%b %Y')} - {df_filtered['Date'].max().strftime('%b %Y')}")
    with col2:
        st.metric("Total Days", f"{len(df_filtered)}")
    with col3:
        st.metric("Stress Days", f"{int(df_filtered['Stress_Period'].sum())}")

# Footer
st.markdown("---")
st.markdown("📊 *Data Source: HHS Unaccompanied Alien Children Program*")
st.markdown(f"⚙️ *Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
