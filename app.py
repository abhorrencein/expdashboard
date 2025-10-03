import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime

# === PREMIUM STYLING: Palantir Meets BCG ===
st.markdown("""
<style>
    /* Core typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0f172a;
    }
    
    /* Layout */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header */
    h1 {
        font-weight: 800;
        background: linear-gradient(90deg, #1e293b 0%, #4f46e5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.25rem;
    }
    .subtitle {
        color: #64748b;
        font-size: 1.15rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }
    
    /* Upload zone */
    .stFileUploader > div {
        border: 2px dashed #e2e8f0;
        border-radius: 16px;
        padding: 2rem;
        background: #f8fafc;
        transition: all 0.3s ease;
        text-align: center;
    }
    .stFileUploader > div:hover {
        border-color: #818cf8;
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08);
    }
    
    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03), 0 2px 4px -1px rgba(0,0,0,0.02);
        text-align: center;
        flex: 1;
        min-width: 120px;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0.5rem 0;
    }
    .kpi-label {
        font-size: 0.875rem;
        color: #64748b;
    }
    
    /* Chart containers */
    .chart-section {
        margin: 2rem 0;
    }
    .chart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .chart-title {
        font-weight: 600;
        font-size: 1.25rem;
        color: #1e293b;
    }
    .explain-btn {
        background: none;
        border: none;
        color: #6366f1;
        cursor: pointer;
        font-size: 0.875rem;
        padding: 0.25rem;
        border-radius: 6px;
    }
    .explain-btn:hover {
        background: #f0f4ff;
    }
    .chart-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
        margin-bottom: 1.5rem;
    }
    
    /* Export button */
    .export-btn {
        background: #4f46e5;
        color: white;
        border: none;
        padding: 0.5rem 1.25rem;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
    }
    .export-btn:hover {
        background: #4338ca;
    }
    
    /* Footer */
    .app-footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.875rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e2e8f0;
    }
    
    /* Hide Streamlit chrome */
    #MainMenu, footer, .stDeployButton {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# === CACHEABLE DATA PROCESSING ===
@st.cache_data(show_spinner=False)
def process_survey_file(file_content: bytes, file_name: str):
    """Process file with full intelligence pipeline"""
    df = pd.read_excel(file_content, sheet_name=0)
    if df.empty:
        return None, "Empty file"
    
    # Drop metadata rows
    df = df.dropna(subset=[df.columns[0]], how='all')
    
    # SurveyCTO metadata columns to remove
    metadata_cols = {
        'starttime', 'endtime', 'deviceimei', 'subscriberid',
        '_version_', '_index', '_parent_index', 'audit',
        'review_status', 'review_comment', 'formhub/uuid'
    }
    cols_to_drop = [col for col in df.columns if col in metadata_cols]
    clean_df = df.drop(columns=cols_to_drop, errors='ignore')
    
    # Schema inference
    schema = {}
    for col in clean_df.columns:
        col_lower = col.lower()
        col_type = "other"
        assumptions = []
        
        # GPS detection
        if 'lat' in col_lower or 'latitude' in col_lower:
            col_type = "gps_lat"
        elif 'lon' in col_lower or 'longitude' in col_lower:
            col_type = "gps_lon"
        # Categorical detection
        elif clean_df[col].dtype == 'object':
            unique_vals = clean_df[col].dropna().unique()
            if len(unique_vals) == 0:
                col_type = "empty"
            elif len(unique_vals) < 15:
                col_type = "categorical"
                # Infer common patterns
                if set(unique_vals) <= {1, 2, '1', '2'}:
                    assumptions.append("Assumed 1=Yes, 2=No")
                elif set(unique_vals) <= {1, 2, 3, 4, 5}:
                    assumptions.append("Treated as Likert scale")
        # Numeric detection
        elif pd.api.types.is_numeric_dtype(clean_df[col]):
            if clean_df[col].min() >= 0 and clean_df[col].max() <= 100:
                col_type = "percentage"
            else:
                col_type = "numeric"
        
        schema[col] = {
            "type": col_type,
            "assumptions": assumptions,
            "completeness": 1 - clean_df[col].isnull().mean()
        }
    
    # Calculate survey duration if possible
    duration_info = None
    if 'starttime' in df.columns and 'endtime' in df.columns:
        try:
            start = pd.to_datetime(df['starttime'], errors='coerce')
            end = pd.to_datetime(df['endtime'], errors='coerce')
            durations = (end - start).dt.total_seconds() / 60  # in minutes
            valid_durations = durations[durations > 0]
            if len(valid_durations) > 0:
                duration_info = {
                    "avg_minutes": round(valid_durations.mean(), 1),
                    "count": len(valid_durations)
                }
        except:
            pass
    
    return {
        "raw_df": df,
        "clean_df": clean_df,
        "schema": schema,
        "metadata_dropped": len(cols_to_drop),
        "duration_info": duration_info,
        "filename": file_name
    }, None

# === MAIN APP ===
st.title("InsightFlow")
st.markdown('<div class="subtitle">Automated survey intelligence for field teams</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload your SurveyCTO export (XLSX)", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is not None:
    # Generate file hash for caching
    file_content = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_content).hexdigest()
    
    with st.spinner("Analyzing your survey..."):
        result, error = process_survey_file(file_content, uploaded_file.name)
    
    if error:
        st.error(f"❌ {error}")
        st.stop()
    
    data = result
    clean_df = data["clean_df"]
    schema = data["schema"]
    
    # === HEADER BANNER ===
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); 
                border-left: 4px solid #3b82f6; 
                padding: 1.25rem; 
                border-radius: 0 12px 12px 0;
                margin: 1.5rem 0;">
        <strong>✅ Intelligence ready.</strong> Processed <strong>{len(clean_df):,} responses</strong> from <em>{data['filename'].replace('.xlsx', '')}</em>.
    </div>
    """, unsafe_allow_html=True)
    
    # === KPI SUMMARY ===
    st.subheader("Survey Health")
    kpi_cols = st.columns(4)
    
    with kpi_cols[0]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{len(clean_df):,}</div>
            <div class="kpi-label">Responses</div>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_cols[1]:
        completeness = sum(1 for s in schema.values() if s["completeness"] > 0.9) / len(schema) if schema else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{completeness:.0%}</div>
            <div class="kpi-label">High-Quality Fields</div>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_cols[2]:
        gps_count = sum(1 for col in clean_df.columns if 'lat' in col.lower() or 'lon' in col.lower())
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{"Yes" if gps_count >= 2 else "No"}</div>
            <div class="kpi-label">Geotagged</div>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_cols[3]:
        if data["duration_info"]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{data['duration_info']['avg_minutes']}m</div>
                <div class="kpi-label">Avg. Duration</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">—</div>
                <div class="kpi-label">Duration</div>
            </div>
            """, unsafe_allow_html=True)
    
    # === CONTEXTUAL CHARTS ===
    st.markdown('<div class="chart-section">', unsafe_allow_html=True)
    st.subheader("Key Insights")
    
    # Prioritize charts: categorical first, then GPS
    cat_cols = [col for col in clean_df.columns 
                if schema[col]["type"] == "categorical"]
    
    if cat_cols:
        for col in cat_cols[:4]:  # Top 4 only
            with st.container():
                col1, col2 = st.columns([6,1])
                with col1:
                    st.markdown(f'<div class="chart-title">{col.replace("_", " ").title()}</div>', unsafe_allow_html=True)
                with col2:
                    if schema[col]["assumptions"]:
                        with st.popover("ℹ️ Explain"):
                            st.caption("Assumptions made:")
                            for assumption in schema[col]["assumptions"]:
                                st.write(f"• {assumption}")
                            st.caption("Raw values sample:")
                            st.code(clean_df[col].dropna().head(3).to_list())
                
                st.bar_chart(clean_df[col].value_counts(), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    # GPS Map
    lat_col = next((c for c in clean_df.columns if schema[c]["type"] == "gps_lat"), None)
    lon_col = next((c for c in clean_df.columns if schema[c]["type"] == "gps_lon"), None)
    
    if lat_col and lon_col:
        gps_df = clean_df[[lat_col, lon_col]].dropna()
        gps_df = gps_df.rename(columns={lat_col: 'latitude', lon_col: 'longitude'})
        gps_df = gps_df[
            (gps_df['latitude'].between(-90, 90)) & 
            (gps_df['longitude'].between(-180, 180))
        ]
        if not gps_df.empty:
            with st.container():
                st.markdown('<div class="chart-title">Field Locations</div>', unsafe_allow_html=True)
                st.map(gps_df, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === EXPORT SECTION ===
    st.divider()
    st.subheader("Export Cleaned Data")
    
    # Prepare cleaned CSV with human-readable headers
    export_df = clean_df.copy()
    csv = export_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download Cleaned Dataset (CSV)",
        data=csv,
        file_name=f"cleaned_{uploaded_file.name.replace('.xlsx', '.csv')}",
        mime="text/csv",
        key='download-csv'
    )
    
    st.caption("• Metadata removed • Human-readable columns • Ready for analysis")
    
    # === FOOTER ===
    st.markdown("""
    <div class="app-footer">
        InsightFlow • Automated survey intelligence • All processing happens in your browser
    </div>
    """, unsafe_allow_html=True)

else:
    st.info("👆 Upload a SurveyCTO XLSX file to begin. Export as **Excel (analytics-ready)** for best results.")
