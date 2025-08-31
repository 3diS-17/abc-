import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from openai import OpenAI

# =========================
# 🔐 Secrets
# =========================
bot_id = st.secrets["botpress"]["chat_api_id"]
BOTPRESS_TOKEN = st.secrets["botpress"]["token"]

OPENAI_API_KEY = st.secrets["openai"]["api_key"]
OPENROUTER_API_KEY = st.secrets["openrouter"]["api_key"]
API_KEY = st.secrets["alpha_vantage"]["api_key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# 📄 App config
# =========================
st.set_page_config(page_title="💸 Multi-LLM Budget Planner", layout="wide")
st.title("💸 Budgeting + Investment Planner (Multi-LLM AI Suggestions)")

# =========================
# 📉 Alpha Vantage helper
# =========================
def get_alpha_vantage_monthly_return(symbol: str):
    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol={symbol}&apikey={API_KEY}"
    )
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        ts = data.get("Monthly Adjusted Time Series") or {}
        if not isinstance(ts, dict) or len(ts) < 2:
            return None
        dates = sorted(ts.keys(), reverse=True)
        close0 = float(ts[dates[0]]["5. adjusted close"])
        close1 = float(ts[dates[1]]["5. adjusted close"])
        if close1 == 0:
            return None
        return (close0 - close1) / close1
    except Exception:
        return None

# =========================
# 🧾 Inputs
# =========================
st.sidebar.header("📊 Monthly Income")
income = st.sidebar.number_input("Monthly income (before tax, $)", min_value=0.0, value=5000.0, step=100.0)
tax_rate = st.sidebar.slider("Tax rate (%)", 0, 50, 20)

st.sidebar.header("📌 Expenses")
housing = st.sidebar.number_input("Housing / Rent ($)", 0.0, 5000.0, 1200.0, 50.0)
food = st.sidebar.number_input("Food / Groceries ($)", 0.0, 5000.0, 500.0, 50.0)
transport = st.sidebar.number_input("Transport ($)", 0.0, 5000.0, 300.0, 50.0)
utilities = st.sidebar.number_input("Utilities ($)", 0.0, 5000.0, 200.0, 50.0)
entertainment = st.sidebar.number_input("Entertainment ($)", 0.0, 5000.0, 200.0, 50.0)
others = st.sidebar.number_input("Other expenses ($)", 0.0, 5000.0, 200.0, 50.0)

st.sidebar.header("📈 Investments")
stocks = st.sidebar.number_input("Stocks investment ($)", 0.0, 5000.0, 500.0, 100.0)
bonds = st.sidebar.number_input("Bonds investment ($)", 0.0, 5000.0, 300.0, 100.0)
real_estate = st.sidebar.number_input("Real estate ($)", 0.0, 5000.0, 0.0, 100.0)
crypto = st.sidebar.number_input("Crypto ($)", 0.0, 5000.0, 0.0, 100.0)
fixed_deposit = st.sidebar.number_input("Fixed deposit ($)", 0.0, 5000.0, 0.0, 100.0)

months = st.sidebar.slider("Projection period (months)", 1, 60, 12)
savings_target = st.sidebar.number_input("Savings target at end of period ($)", 0.0, 1_000_000.0, 10000.0, 500.0)

# =========================
# 📈 Returns (safe defaults)
# =========================
stock_r = get_alpha_vantage_monthly_return("SPY") or 0.01
bond_r  = get_alpha_vantage_monthly_return("AGG") or 0.003
real_r  = 0.004
crypto_r = 0.02
fd_r     = 0.003

# =========================
# 💰 Calculations
# =========================
after_tax_income = income * (1 - tax_rate / 100)
total_exp = housing + food + transport + utilities + entertainment + others
total_inv = stocks + bonds + real_estate + crypto + fixed_deposit
net_flow = after_tax_income - total_exp - total_inv

bal = 0.0
rows = []
for m in range(1, months + 1):
    bal += net_flow
    stock_val = stocks * ((1 + stock_r) ** m - 1) / stock_r if stock_r else stocks * m
    bond_val  = bonds * ((1 + bond_r)  ** m - 1) / bond_r  if bond_r else bonds * m
    real_val  = real_estate * ((1 + real_r) ** m - 1) / real_r if real_r else real_estate * m
    crypto_val = crypto * ((1 + crypto_r) ** m - 1) / crypto_r if crypto_r else crypto * m
    fd_val     = fixed_deposit * ((1 + fd_r) ** m - 1) / fd_r if fd_r else fixed_deposit * m

    net_worth = bal + stock_val + bond_val + real_val + crypto_val + fd_val
    rows.append({
        "Month": m,
        "Balance": bal,
        "Stocks": stock_val,
        "Bonds": bond_val,
        "RealEstate": real_val,
        "Crypto": crypto_val,
        "FixedDeposit": fd_val,
        "NetWorth": net_worth
    })
df = pd.DataFrame(rows)

# =========================
# 📋 Summary
# =========================
st.subheader("📋 Summary")
colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Income (gross)", f"${income:,.2f}")
colB.metric("After tax income", f"${after_tax_income:,.2f}")
colC.metric("Expenses", f"${total_exp:,.2f}")
colD.metric("Investments", f"${total_inv:,.2f}")
colE.metric("Net Cash Flow", f"${net_flow:,.2f}/mo")

# =========================
# 📊 Charts
# =========================
st.subheader("📈 Net Worth Growth")
fig = px.line(
    df,
    x="Month",
    y=["Balance", "Stocks", "Bonds", "RealEstate", "Crypto", "FixedDeposit", "NetWorth"],
    markers=True,
    title="Net Worth & Investments Over Time",
)
fig.add_hline(y=savings_target, line_dash="dash", line_color="red", annotation_text="Target")
st.plotly_chart(fig, use_container_width=True)

st.subheader("🧾 Expense Breakdown")
exp_s = pd.Series({
    "Housing": housing,
    "Food": food,
    "Transport": transport,
    "Utilities": utilities,
    "Entertainment": entertainment,
    "Others": others
})
st.plotly_chart(px.pie(names=exp_s.index, values=exp_s.values, title="Expense Breakdown"), use_container_width=True)

st.subheader("💼 Investment Breakdown")
inv_s = pd.Series({
    "Stocks": stocks,
    "Bonds": bonds,
    "RealEstate": real_estate,
    "Crypto": crypto,
    "FixedDeposit": fixed_deposit
})
st.plotly_chart(px.pie(names=inv_s.index, values=inv_s.values, title="Investment Breakdown"), use_container_width=True)

# =========================
# 🤖 AI Suggestions
# =========================
st.subheader("🤖 AI Suggestions")
col1, col2 = st.columns(2)

prompt = f"""
You are a budgeting coach. Use concise bullet points.

Gross income: ${income}
Tax rate: {tax_rate}%
After-tax income: ${after_tax_income}
Expenses: ${total_exp}
Investments: ${total_inv}
Net cash flow: ${net_flow}/mo
Savings target after {months} months: ${savings_target}
Projected net worth: ${df['NetWorth'].iloc[-1]}

Advise: (1) expense cuts, (2) investment allocation, (3) reaching savings target.
"""

if col1.button("Generate OpenAI Suggestion"):
    with st.spinner("OpenAI generating..."):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            out = resp.choices[0].message.content
            st.write(out)
        except Exception as e:
            st.error(f"OpenAI error: {e}")

if col2.button("Generate DeepSeek Suggestion"):
    with st.spinner("DeepSeek generating..."):
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek/deepseek-r1:free",
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            out = res.json()["choices"][0]["message"]["content"]
            st.write(out)
        except Exception as e:
            st.error(f"OpenRouter error: {e}")

# =========================
# 💬 Botpress Text Chat
# =========================
st.subheader("🤖 Ask Your Financial Assistant (Botpress)")

# Safely initialize conversation
if "conversation_id" not in st.session_state:
    try:
        init = requests.post(
            "https://chat.botpress.cloud/v1/chat/conversations",
            headers={
                "Authorization": f"Bearer {BOTPRESS_TOKEN}",
                "X-Bot-Id": bot_id,
            },
            timeout=20
        )
        init.raise_for_status()
        st.session_state.conversation_id = init.json().get("id")
    except Exception as e:
        st.error(f"❌ Failed to create Botpress conversation: {e}")
        st.stop()

# Get user message
user_message = st.text_input("Type your message to the Botpress agent:", key="botpress_input")

if st.button("Send to Botpress"):
    if not user_message.strip():
        st.warning("⚠️ Please enter a message before sending.")
    elif "conversation_id" not in st.session_state:
        st.error("❌ No active conversation. Please reload the app.")
    else:
        payload = {
            "type": "text",
            "role": "user",
            "payload": {"text": user_message}
        }

        try:
            res = requests.post(
                f"https://chat.botpress.cloud/v1/chat/conversations/{st.session_state.conversation_id}/messages",
                json=payload,
                headers={
                    "Authorization": f"Bearer {BOTPRESS_TOKEN}",
                    "X-Bot-Id": bot_id,
                    "Content-Type": "application/json"
                },
                timeout=20
            )
            res.raise_for_status()
            st.success("✅ Message sent to Botpress!")
        except Exception as e:
            st.error(f"❌ Failed to send message: {e}")
            st.stop()

        # Fetch Botpress reply
        try:
            reply_res = requests.get(
                f"https://chat.botpress.cloud/v1/chat/conversations/{st.session_state.conversation_id}/messages",
                headers={
                    "Authorization": f"Bearer {BOTPRESS_TOKEN}",
                    "X-Bot-Id": bot_id,
                },
                timeout=20
            )
            reply_res.raise_for_status()
            data = reply_res.json()
            messages = data.get("messages", [])
            replies = [m.get("payload", {}).get("text", "") for m in messages if m.get("role") == "assistant" and m.get("type") == "text"]
            if replies and replies[-1]:
                st.info(f"🤖 Botpress: {replies[-1]}")
            else:
                st.warning("⚠️ Botpress sent no reply.")
        except Exception as e:
            st.error(f"❌ Failed to fetch reply: {e}")
