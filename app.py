import streamlit as st
import plotly.express as px
import yfinance as yf
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime, timedelta

# ========== API Setup ==========
try:
    api_key = st.secrets["openrouter_api_key"]
    model_name = st.secrets["openrouter_model"]
except KeyError:
    st.error("❌ API key or model name is missing from secrets.")
    st.stop()

api_base = "https://openrouter.ai/api/v1"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# ========== Login ==========
def login_section():
    st.sidebar.subheader("🔐 Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if email and password:
            st.session_state['user'] = {"email": email}
            st.success(f"✅ Logged in as {email}")
        else:
            st.error("❌ Enter both email and password")

# ========== Portfolio Allocation ==========
def get_portfolio_allocation(risk):
    return {
        "Low": {"Equity": 30, "Debt": 60, "Gold": 10},
        "Medium": {"Equity": 50, "Debt": 40, "Gold": 10},
        "High": {"Equity": 70, "Debt": 20, "Gold": 10}
    }[risk]

# ========== GPT Portfolio Explanation ==========
def explain_portfolio(allocation, age, risk, goal):
    prompt = f"""Act as a certified financial advisor. Explain a portfolio for a {age}-year-old user with {risk} risk tolerance and goal: {goal}.
    Allocation: Equity {allocation['Equity']}%, Debt {allocation['Debt']}%, Gold {allocation['Gold']}%."""

    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful financial advisor."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        st.warning("⚠️ Could not connect to OpenRouter. Showing fallback response.")
        return "Based on your risk tolerance and age, a diversified portfolio of equity, debt, and gold is recommended. Equity provides high returns, debt ensures safety, and gold adds stability."

# ========== CAGR ==========
def fetch_cagr(ticker, years=5):
    try:
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        data = yf.download(ticker, start=start, end=end, progress=False)
        if data.empty:
            return None
        start_price = data["Adj Close"].iloc[0]
        end_price = data["Adj Close"].iloc[-1]
        return round(((end_price / start_price) ** (1 / years) - 1) * 100, 2)
    except:
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
    pdf.cell(200, 10, f"Risk: {risk} | Goal: {goal}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Allocation:", ln=True)
    for asset, percent in allocation.items():
        pdf.cell(200, 10, f"{asset}: {percent}%", ln=True)

    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Advisor's Explanation:\n{explanation}")

    if mip_info:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"Investment Plan:\nTarget: ₹{mip_info['future_value']:,}\n"
                              f"Monthly: ₹{mip_info['monthly']:,} for {mip_info['years']} years at {mip_info['rate']}%.")

    pdf.output("/mnt/data/wealth_report.pdf")

# ========== Streamlit UI ==========
st.set_page_config(page_title="GenAI Wealth Advisor", page_icon="💼")
st.title("💼 GenAI Wealth Advisor")

login_section()
if 'user' not in st.session_state:
    st.stop()

st.subheader("👤 Your Profile")
age = st.slider("Age", 18, 70, 30)
income = st.number_input("Monthly Income (₹)", value=50000)
risk = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
goal = st.text_input("Financial Goal")

if st.button("🔍 Generate Portfolio"):
    allocation = get_portfolio_allocation(risk)
    fig = px.pie(names=list(allocation.keys()), values=list(allocation.values()), title="Portfolio Allocation")
    st.plotly_chart(fig)

    explanation = explain_portfolio(allocation, age, risk, goal)
    st.markdown("### 📘 Advisor's Explanation")
    st.write(explanation)

    st.subheader("📈 Monthly SIP Plan")
    rate = st.slider("Expected Return (%)", 6.0, 15.0, 12.0)
    years = st.slider("Duration (Years)", 1, 40, 10)
    target = st.number_input("Target Corpus (₹)", value=5000000)

    months = years * 12
    monthly_rate = rate / 100 / 12
    monthly = round(target * monthly_rate / ((1 + monthly_rate) ** months - 1))
    st.success(f"Invest ₹{monthly:,}/month to reach ₹{target:,} in {years} years.")

    mip_info = {
        "monthly": monthly,
        "years": years,
        "rate": rate,
        "future_value": target
    }

    st.subheader("📉 Real-Time CAGR Estimates")
    returns = {
        "Equity": fetch_cagr("NIFTYBEES.NS"),
        "Debt": fetch_cagr("ICICILIQ.NS"),
        "Gold": fetch_cagr("GOLDBEES.NS")
    }

    df = pd.DataFrame({"Asset": list(returns.keys()), "CAGR (%)": list(returns.values())})
    st.dataframe(df)

    valid = [v for v in returns.values() if v is not None]
    if valid:
        st.info(f"Average CAGR: {round(sum(valid)/len(valid),2)}%")
    else:
        st.warning("❗ Could not fetch CAGR data. You may be offline or tickers are invalid.")

    if st.button("📄 Generate PDF Report"):
        generate_pdf("User", age, income, risk, goal, allocation, explanation, mip_info)
        st.download_button("📥 Download PDF", open("/mnt/data/wealth_report.pdf", "rb"), "Wealth_Report.pdf")

    st.subheader("⭐ Feedback")
    if st.selectbox("Rate the experience", ["Select", "Excellent", "Good", "Average", "Poor"]) != "Select":
        st.success("Thanks for your feedback!")
        if st.button("🔄 Restart"):
            st.session_state.clear()
            st.experimental_rerun()
