import streamlit as st

st.set_page_config(page_title="SurveyCTO Dashboard", layout="wide")
st.title("📊 Auto Dashboard for SurveyCTO")
st.write("Upload your SurveyCTO XLSX export below. We'll clean it and show insights.")

uploaded_file = st.file_uploader("Choose a SurveyCTO XLSX file", type=["xlsx"])

if uploaded_file is not None:
    st.success("✅ File received! (Next: auto-clean and visualize.)")
    st.info("Tip: Export from SurveyCTO as 'Excel (analytics-ready)' for best results.")
