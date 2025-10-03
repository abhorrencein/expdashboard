import streamlit as st
import pandas as pd

st.set_page_config(page_title="SurveyCTO Dashboard", layout="wide")
st.title("📊 Auto Dashboard for SurveyCTO")
st.write("Upload your SurveyCTO XLSX export below. We'll clean it and show insights.")

uploaded_file = st.file_uploader("Choose a SurveyCTO XLSX file", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Load the first sheet (SurveyCTO main data is usually here)
        df = pd.read_excel(uploaded_file, sheet_name=0)
        
        # Basic cleanup: drop rows where the first column is empty
        if not df.empty:
            df = df.dropna(subset=[df.columns[0]], how='all')
        
        st.success(f"✅ Loaded {len(df)} responses!")
        
        # Show a preview
        st.subheader("🔍 Data Preview (first 10 rows)")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Detect SurveyCTO-specific columns
        surveycto_cols = []
        if 'starttime' in df.columns:
            surveycto_cols.append("Start time")
        if 'endtime' in df.columns:
            surveycto_cols.append("End time")
        if any(col.endswith('_latitude') for col in df.columns):
            surveycto_cols.append("GPS coordinates")
        if '_version_' in df.columns:
            surveycto_cols.append("Form version")
            
        if surveycto_cols:
            st.info(f"📎 Detected SurveyCTO features: {', '.join(surveycto_cols)}")
        else:
            st.warning("⚠️ No SurveyCTO metadata found. Make sure you exported as 'Excel (analytics-ready)'.")
            
    except Exception as e:
        st.error("❌ Couldn't read the file.")
        st.code(str(e))
        st.info("💡 Tip: In SurveyCTO, go to **Data > Export > Excel (analytics-ready)**")
