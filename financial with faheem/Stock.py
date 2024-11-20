import streamlit as st
import pandas as pd
import requests
import openai
import os
from dotenv import load_dotenv
import yfinance as yf

# Load environment variables from .env file
load_dotenv()

# Fetch API keys from the environment
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Class for the Financial Advisor Bot
class FinancialAdvisorBot:
    def __init__(self):
        self.expenses = pd.DataFrame(columns=["Date", "Category", "Amount"])
        self.retirement_plan = {
            "current_age": None,
            "retirement_age": None,
            "current_savings": None,
            "monthly_contribution": None,
            "savings_goal": None,
        }

    @staticmethod
    def get_current_inflation():
        """Fetch the latest inflation rate from Alpha Vantage."""
        try:
            url = f"https://www.alphavantage.co/query?function=INFLATION&apikey={ALPHA_VANTAGE_API_KEY}"
            response = requests.get(url)
            data = response.json()
            if 'data' in data:
                inflation_rate = data['data'][0]['value']  # Adjust according to API response
                return float(inflation_rate)
            else:
                st.error("Unable to fetch inflation data.")
                return None
        except Exception as e:
            st.error(f"Error fetching inflation data: {e}")
            return None

    def add_expense(self, date, category, amount):
        """Add an expense to the tracker."""
        new_expense = {"Date": date, "Category": category, "Amount": amount}
        self.expenses = pd.concat([self.expenses, pd.DataFrame([new_expense])], ignore_index=True)

    def get_expense_summary(self):
        """Summarize expenses by category."""
        summary = self.expenses.groupby("Category")["Amount"].sum().reset_index()
        return summary

    def set_retirement_plan(self, current_age, retirement_age, current_savings, monthly_contribution, savings_goal):
        """Set or update retirement plan details."""
        self.retirement_plan.update({
            "current_age": current_age,
            "retirement_age": retirement_age,
            "current_savings": current_savings,
            "monthly_contribution": monthly_contribution,
            "savings_goal": savings_goal,
        })

    def project_retirement_savings(self):
        """Project savings considering inflation."""
        inflation_rate = self.get_current_inflation() or 0
        years_to_retirement = self.retirement_plan["retirement_age"] - self.retirement_plan["current_age"]
        adjusted_goal = self.retirement_plan["savings_goal"] * ((1 + inflation_rate / 100) ** years_to_retirement)

        return {
            "inflation_rate": inflation_rate,
            "adjusted_goal": adjusted_goal,
            "years_to_retirement": years_to_retirement,
        }

    def suggest_stocks(self, investment_amount, years):
        """Suggest stocks for long-term investment."""
        try:
            # Example top companies for long-term investments (you can customize this)
            stock_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
            stock_data = {}

            for ticker in stock_tickers:
                stock = yf.Ticker(ticker)
                info = stock.info
                price = info.get("currentPrice", None)
                if price:
                    stock_data[ticker] = {
                        "Name": info["shortName"],
                        "Current Price": price,
                        "Market Cap": info["marketCap"],
                        "52 Week High": info["fiftyTwoWeekHigh"],
                        "52 Week Low": info["fiftyTwoWeekLow"],
                    }

            stock_df = pd.DataFrame.from_dict(stock_data, orient="index")
            stock_df["Suggested Investment"] = investment_amount / len(stock_tickers)

            return stock_df
        except Exception as e:
            st.error(f"Error fetching stock data: {e}")
            return None

    def generate_financial_advice(self, prompt):
        """Get financial advice from the LLM (OpenAI)."""
        inflation_rate = self.get_current_inflation()
        if inflation_rate is not None:
            inflation_context = f"The current annual inflation rate is {inflation_rate:.2f}%. Please consider this in your calculations."
        else:
            inflation_context = "I couldn't retrieve the current inflation rate. Proceed without inflation adjustment."

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial advisor bot."},
                {"role": "assistant", "content": inflation_context},
                {"role": "user", "content": prompt}
            ]
        )
        return response["choices"][0]["message"]["content"]

# Streamlit App
bot = FinancialAdvisorBot()

st.title("Financial Advisor AI Bot")
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Go to", ["Home", "Expense Tracker", "Retirement Planner", "Stock Suggestions", "Ask Financial Advice"])

if menu == "Home":
    st.write("""
    Welcome to the Financial Advisor AI Bot!  
    Use this app to track your expenses, plan for retirement, and get personalized financial advice.
    """)

elif menu == "Expense Tracker":
    st.header("Expense Tracker")
    
    with st.form("Add Expense"):
        date = st.date_input("Date")
        category = st.text_input("Category")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            bot.add_expense(date, category, amount)
            st.success(f"Added: {category} - ${amount} on {date}")
    
    if not bot.expenses.empty:
        st.write("### Expense Summary")
        st.dataframe(bot.get_expense_summary())
    else:
        st.write("No expenses recorded yet.")

elif menu == "Retirement Planner":
    st.header("Retirement Planner")
    
    with st.form("Set Retirement Plan"):
        current_age = st.number_input("Current Age", min_value=0, step=1)
        retirement_age = st.number_input("Retirement Age", min_value=0, step=1)
        current_savings = st.number_input("Current Savings", min_value=0.0, step=1000.0)
        monthly_contribution = st.number_input("Monthly Contribution", min_value=0.0, step=100.0)
        savings_goal = st.number_input("Savings Goal", min_value=0.0, step=10000.0)
        submitted = st.form_submit_button("Set Plan")
        if submitted:
            bot.set_retirement_plan(current_age, retirement_age, current_savings, monthly_contribution, savings_goal)
            st.success("Retirement plan updated!")

    if bot.retirement_plan["current_age"] is not None:
        projection = bot.project_retirement_savings()
        st.write(f"### Adjusted Savings Goal with Inflation ({projection['inflation_rate']:.2f}%):")
        st.write(f"${projection['adjusted_goal']:.2f}")

elif menu == "Stock Suggestions":
    st.header("Stock Suggestions")
    
    with st.form("Suggest Stocks"):
        investment_amount = st.number_input("Total Investment Amount", min_value=0.0, step=1000.0)
        years = st.number_input("Investment Time Horizon (years)", min_value=1, step=1)
        submitted = st.form_submit_button("Get Suggestions")
        if submitted:
            stocks = bot.suggest_stocks(investment_amount, years)
            if stocks is not None:
                st.write("### Suggested Stocks for Long-Term Investment")
                st.dataframe(stocks)

elif menu == "Ask Financial Advice":
    st.header("Financial Advice")
    user_prompt = st.text_area("Enter your financial question:")
    if st.button("Get Advice"):
        advice = bot.generate_financial_advice(user_prompt)
        st.write("### Advice:")
        st.write(advice)
