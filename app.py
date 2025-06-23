import streamlit as st
import plotly.express as px
import yfinance as yf
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime, timedelta

# ========== API Setup ==========
api_key = st.secrets["openrouter_api_key"]
model_name = st.secrets["openrouter_model"]
api_base = "https://openrouter.ai/api/v1"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# ========== Simulated Login ==========
def login_section():
    st.sidebar.subheader("🔐 Simulated Login")
    email = st.sidebar.text_input("Enter your email")
    password = st.sidebar.text_input("Enter your password", type="password")
    if st.sidebar.button("Login"):
        if email and password:
            st.session_state['user'] = {"email": email}
            st.success(f"✅ Logged in as {email}")
        else:
            st.error("❌ Please enter both email and password")

# ========== Portfolio Allocation ==========
def get_portfolio_allocation(risk):
    return {
        "Low": {"Equity": 30, "Debt": 60, "Gold": 10},
        "Medium": {"Equity": 50, "Debt": 40, "Gold": 10},
        "High": {"Equity": 70, "Debt": 20, "Gold": 10}
    }[risk]

# ========== GPT Portfolio Explanation ==========
def explain_portfolio(allocation, age, risk, goal):
    prompt = f"""
    Act like a professional financial advisor. Explain this portfolio allocation for a {age}-year-old user with {risk} risk tolerance and goal: {goal}.
    The allocation is: Equity: {allocation['Equity']}%, Debt: {allocation['Debt']}%, Gold: {allocation['Gold']}%."""
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful financial advisor."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(f"{api_base}/chat/completions", headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]

# ========== CAGR Fetcher ==========
def fetch_cagr(ticker, years=5):
    try:
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        data = yf.download(ticker, start=start, end=end, progress=False)
        if data.empty or "Adj Close" not in data:
            st.warning(f"No data for {ticker}")
            return None
        start_price = data["Adj Close"].iloc[0]
        end_price = data["Adj Close"].iloc[-1]
        cagr = ((end_price / start_price) ** (1 / years)) - 1
        return round(cagr * 100, 2)
    except Exception as e:
        st.error(f"Error fetching CAGR for {ticker}: {e}")
        return None

# ========== PDF Report ==========
def generate_pdf(name, age, income, risk, goal, allocation, explanation, mip_info=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Wealth Advisor Report", ln=True, align="C")
    pdf.set_font("Arial", '', 12)

    pdf.ln(10)
    pdf.cell(200, 10, f"Name: {name} | Age: {age} | Income: ₹{income:,}", ln=True)
    pdf.cell(200, 10, f"Risk Tolerance: {risk} | Goal: {goal}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Portfolio Allocation:", ln=True)
    for asset, percent in allocation.items():
        pdf.cell(200, 10, f"{asset}: {percent}%", ln=True)

    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Advisor's Explanation:\n{explanation}")

    if mip_info:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"\nMonthly Investment Plan:\n"
                              f"Target: ₹{mip_info['future_value']}\n"
                              f"Invest ₹{mip_info['monthly']:,}/month for {mip_info['years']} years "
                              f"at {mip_info['rate']}% expected return.")

    pdf.output("/mnt/data/wealth_report.pdf")

# ========== Streamlit App ==========
st.set_page_config(page_title="GenAI Wealth Advisor", page_icon="💼")
st.title("💼 GenAI-Based Wealth Advisor Chatbot")

login_section()
if 'user' not in st.session_state:
    st.stop()

# ========== User Profile Inputs ==========
st.subheader("👤 Profile Details")
age = st.slider("Age", 18, 70, 30)
income = st.number_input("Monthly Income (₹)", value=50000)
risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
goal = st.text_input("Primary Goal (e.g., retirement, house)")

if st.button("🔍 Generate Portfolio"):
    allocation = get_portfolio_allocation(risk_tolerance)

    fig = px.pie(
        names=list(allocation.keys()),
        values=list(allocation.values()),
        title="Your Investment Allocation",
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig)

    explanation = explain_portfolio(allocation, age, risk_tolerance, goal)
    st.markdown("### 📘 Advisor's Explanation")
    st.write(explanation)

    # ========== Monthly Investment Plan ==========
    st.subheader("📈 Monthly Investment Plan")
    rate = st.slider("Expected Annual Return (%)", 6.0, 15.0, 12.0)
    years = st.slider("Investment Duration (Years)", 1, 40, 10)
    months = years * 12
    monthly_rate = rate / 100 / 12

    target = st.number_input("Target Corpus (₹)", value=4500000)
    monthly = target * monthly_rate / ((1 + monthly_rate) ** months - 1)
    monthly = round(monthly)
    st.success(f"To reach ₹{target:,} in {years} years at {rate}% return, invest ₹{monthly:,}/month.")

    mip_info = {
        "mode": "goal",
        "monthly": monthly,
        "years": years,
        "rate": rate,
        "future_value": target
    }

    # ========== Real-Time CAGR ==========
    st.subheader("📉 Real-Time Return Estimates")
    st.caption("Tickers Used: NIFTYBEES (Equity), SBIETF10Y (Debt), GOLDBEES (Gold)")

    returns = {
        "Equity": fetch_cagr("NIFTYBEES.NS"),
        "Debt": fetch_cagr("SBIETF10Y.NS"),
        "Gold": fetch_cagr("GOLDBEES.NS")
    }

    df = pd.DataFrame({
        "Asset": list(returns.keys()),
        "CAGR (%)": list(returns.values())
    })

    st.dataframe(df)

    valid_cagrs = [r for r in returns.values() if r is not None]
    if valid_cagrs:
        avg = round(sum(valid_cagrs) / len(valid_cagrs), 2)
        st.info(f"📊 Average CAGR across assets: {avg}%")
    else:
        st.error("❌ Unable to fetch CAGR data. Please check internet connection or tickers.")

    # ========== PDF ==========
    if st.button("📄 Generate PDF Report"):
        generate_pdf("User", age, income, risk_tolerance, goal, allocation, explanation, mip_info)
        st.download_button("📥 Download PDF", open("/mnt/data/wealth_report.pdf", "rb"), "Wealth_Report.pdf")

    # ========== Feedback ==========
    st.subheader("⭐ Rate Your Experience")
    rating = st.selectbox("How would you rate this output?", ["Select", "Excellent", "Good", "Average", "Poor"])
    if rating != "Select":
        st.success("🎉 Thank you for your feedback! You may restart the app now.")
        if st.button("🔄 Restart"):
            st.session_state.clear()
            st.experimental_rerun()
