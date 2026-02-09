import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from langchain_core.tools import Tool
from langchain_cohere import ChatCohere
from langchain.agents import create_agent
import json

class LogColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_header(title):
    print(f"\n{LogColors.BOLD}{LogColors.HEADER}========== {title} =========={LogColors.END}")

def log_info(msg):
    print(f"{LogColors.BLUE}[INFO]{LogColors.END} {msg}")

def log_success(msg):
    print(f"{LogColors.GREEN}[SUCCESS]{LogColors.END} {msg}")

def log_warning(msg):
    print(f"{LogColors.YELLOW}[WARNING]{LogColors.END} {msg}")

def log_error(msg):
    print(f"{LogColors.RED}[ERROR]{LogColors.END} {msg}")

def log_debug(msg):
    print(f"{LogColors.CYAN}[DEBUG]{LogColors.END} {msg}")

st.set_page_config(layout="wide", page_title="Personal Finance Dashboard")


# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
# def load_data(path):
#     df = path

#     # Safe Date Parsing (DD/MM/YYYY compatible)
#     df["Date"] = pd.to_datetime(
#         df["Date"],
#         dayfirst=True,
#         errors="coerce"
#     )


#     # Feature Engineering
#     df["Month"] = df["Date"].dt.to_period("M").astype(str)
#     df["Year"] = df["Date"].dt.year
#     df["Amount"] = df["Debit"].fillna(0) - df["Credit"].fillna(0)
#     df.info()

#     return df
# import pandas as pd

def load_data(df: pd.DataFrame):

    # Ensure Date is clean string
    df["Date"] = df["Date"].astype(str).str.strip()

    # Parse YYYY-MM-DD explicitly
    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m-%d"
    )

    # Feature Engineering
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Year"] = df["Date"].dt.year

    # Ensure numeric before calculation
    df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
    df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)

    df["Amount"] = df["Debit"] - df["Credit"]

    df.info()

    return df





# =====================================================
# SIDEBAR FILTERS
# =====================================================
if not st.session_state.authenticated:
    page = "🔐 Login"

else:
    st.sidebar.title("🧭 Navigation")

    page = st.sidebar.radio(
        "Go to",
        ["📂 Upload Data","📊 Analytics Dashboard", "🤖 Financial Q&A Chatbot"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **{st.session_state.username}**")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.chat_history = []
        st.rerun()

# =====================================================
# LOGIN PAGE
# =====================================================
if page == "🔐 Login":

    st.markdown("""
    <style>
    .login-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(12px);
        padding: 40px;
        border-radius: 18px;
        max-width: 400px;
        margin: auto;
        margin-top: 120px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown("## 🔐 Welcome")
    st.markdown(
        "<div style='opacity:0.7;margin-bottom:20px;'>Enter your username to continue</div>",
        unsafe_allow_html=True
    )

    username_input = st.text_input("Username")
    
    if st.button("Login", use_container_width=True):
        if username_input:
            st.session_state.authenticated = True
            st.session_state.username = username_input.strip()
            if "df" not in st.session_state:
                    try:
                        print(f"welcome back user: {st.session_state.username}")
                        print(f"loading database user_{st.session_state.username}_improved.csv")
                        st.session_state.df = load_data(pd.read_csv(f"user_{st.session_state.username}_improved.csv"))
                    except FileNotFoundError as e:
                        print("no data set with this name")
                        st.session_state.df = None
                        st.rerun()
        else:
            st.warning("Please enter a valid username.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =====================================================
# LOAD DATA FROM SESSION
# =====================================================
df = st.session_state.df

if df is None:
    st.warning("⚠️ No dataset loaded. Please upload a CSV file.")
    page="📂 Upload Data"

if page=="📂 Upload Data":
    st.title("📂 Upload Transaction Data")
    from graph import app
    from datetime import datetime

    with st.form("upload_form"):

        bank_name = st.selectbox(
            "🏦 Select Bank",
            [
                "SBI",
                "ICICI_Bank",
                "HDFC_Bank",
                "Axis_Bank",
                "Kotak_Bank",
                "Other"
            ]
        )

        uploaded_file = st.file_uploader(
            "Upload Bank Statement (CSV/Excel)",
            type=["csv", "xlsx", "xls"]
        )
        

        submitted = st.form_submit_button("Upload")

    if uploaded_file:
            file_extension = uploaded_file.name.split(".")[-1].lower()

            if file_extension == "csv":
                try:
                    data = pd.read_csv(uploaded_file, encoding="utf-8")
                except UnicodeDecodeError:
                    data = pd.read_csv(uploaded_file, encoding="latin1")

            elif file_extension in ["xlsx", "xls"]:
                data = pd.read_excel(uploaded_file)

            else:
                st.error("Unsupported file type.")


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path=f"original_data/{timestamp}_user_{st.session_state.username}_{bank_name}.csv"
            data.to_csv(path)


            res=app.invoke({"data_path":path})
            new_data=res['dataset']

            if st.session_state.df is None:
                print(f"Welcome New Uesr {st.session_state.username}")
                df_uploaded =load_data(new_data)
                st.session_state.df = df_uploaded
                new_data.to_csv(f"user_{st.session_state.username}_improved.csv")
                st.success(f"✅ File: user_{st.session_state.username}_improved.csv uploaded successfully!")
                st.dataframe(df_uploaded.head())

            else:
                print(f"updating user_{st.session_state.username}_improved.csv database")
                new_data.to_csv(
                        f"user_{st.session_state.username}_improved.csv",
                        mode="a",          # append mode
                        header=False,      # don't write header again
                        index=False
                    )
                print(f"re-loading user_{st.session_state.username}_improved.csv database")
                st.session_state.df = load_data(pd.read_csv(f"user_{st.session_state.username}_improved.csv"))
                
    
    import json
    import os

    st.subheader("🛠 Manual Categorization – Uncategorized Merchants")

    # -----------------------------------------------------
    # Load category rules
    # -----------------------------------------------------
    if os.path.exists("categories.json"):
        with open("categories.json", "r") as file:
            category_options = json.load(file)
    else:
        category_options = {}

    # -----------------------------------------------------
    # Find uncategorized
    # -----------------------------------------------------
    df=st.session_state.df
    try:
        uncategorized_df = df.loc[(df["label"] == "uncategorized") | (df["label"] == "llm")]

        if len(uncategorized_df) == 0:
            st.success("✅ No uncategorized transactions left.")
        elif uncategorized_df['Reciever_Sender'].isna().all():
            st.write(f"Found Few more unique merchants.")
            selected_row = st.selectbox(
                "Select Merchant to Categorize",
                uncategorized_df.index,
                format_func=lambda x: f"{uncategorized_df.loc[x, 'Method']}"
            )

            merchant_name = uncategorized_df.loc[selected_row, "Method"]

            category_list = list(category_options.keys())

            selected_category = st.selectbox(
                "Select Existing Category",
                category_list + ["➕ Create New Category"]
            )

            new_category_name = None

            if selected_category == "➕ Create New Category":
                new_category_name = st.text_input("Enter New Category Name")

            # -------------------------------------------------
            # Save Button
            # -------------------------------------------------
            if st.button("💾 Save Category"):

                final_category = (
                    new_category_name.strip()
                    if selected_category == "➕ Create New Category"
                    else selected_category
                )

                if not final_category:
                    st.warning("Please enter a valid category.")
                    st.stop()

                # Update dataframe
                df.loc[
                    df["Method"] == merchant_name,
                    "label"
                ] = final_category


                # Save dataframe
                df.to_csv(f"user_{st.session_state.username}_improved.csv", index=False)

                st.success("✅ Category updated successfully!")
                st.rerun()
    

        else:

            unique_uncategorized_df = (
                uncategorized_df
                .groupby(["Reciever_Sender", "Method"])["Details"]
                .count()
                .reset_index()
            )

            st.write(f"Found {len(unique_uncategorized_df)} unique merchants.")

            # -------------------------------------------------
            # Select merchant
            # -------------------------------------------------
            selected_row = st.selectbox(
                "Select Merchant to Categorize",
                unique_uncategorized_df.index,
                format_func=lambda x: f"{unique_uncategorized_df.loc[x, 'Reciever_Sender']} ({unique_uncategorized_df.loc[x, 'Method']})"
            )

            merchant_name = unique_uncategorized_df.loc[selected_row, "Reciever_Sender"]

            st.markdown(f"### Merchant: `{merchant_name}`")

            # -------------------------------------------------
            # Category Selection
            # -------------------------------------------------
            category_list = list(category_options.keys())

            selected_category = st.selectbox(
                "Select Existing Category",
                category_list + ["➕ Create New Category"]
            )

            new_category_name = None

            if selected_category == "➕ Create New Category":
                new_category_name = st.text_input("Enter New Category Name")

            # -------------------------------------------------
            # Save Button
            # -------------------------------------------------
            if st.button("💾 Save Category"):

                final_category = (
                    new_category_name.strip()
                    if selected_category == "➕ Create New Category"
                    else selected_category
                )

                if not final_category:
                    st.warning("Please enter a valid category.")
                    st.stop()

                # Update dataframe
                df.loc[
                    df["Reciever_Sender"] == merchant_name,
                    "label"
                ] = final_category

                # Update category rules
                if final_category not in category_options:
                    category_options[final_category] = []

                if merchant_name not in category_options[final_category]:
                    category_options[final_category].append(merchant_name)

                # Save rules
                with open("categories.json", "w") as file:
                    json.dump(category_options, file, indent=4)

                # Save dataframe
                df.to_csv(f"user_{st.session_state.username}_improved.csv", index=False)
                
                st.success("✅ Category updated successfully!")
                st.rerun()
    except:
        st.success("✅ All Categories are up-to-date!")





if page == "📊 Analytics Dashboard":
    st.sidebar.title("🔎 Filters")

    date_range = st.sidebar.date_input(
        "Select Date Range",
        [df["Date"].min(), df["Date"].max()]
    )

    category_filter = st.sidebar.multiselect(
        "Category",
        options=sorted(df["label"].dropna().unique()),
        default=sorted(df["label"].dropna().unique())
    )

    method_filter = st.sidebar.multiselect(
        "Payment Method",
        options=sorted(df["Method"].dropna().unique()),
        default=sorted(df["Method"].dropna().unique())
    )

    log_debug(f"options: {df["Method"].dropna().unique()}")

    filtered_df = df[
        (df["Date"] >= pd.to_datetime(date_range[0])) &
        (df["Date"] <= pd.to_datetime(date_range[1])) &
        (df["label"].isin(category_filter)) &
        (df["Method"].isin(method_filter))
    ]

filtered_df=df

# =====================================================
# HEADER
# =====================================================
if page == "📊 Analytics Dashboard":
    st.title("💰 Personal Finance Analytics Dashboard")
    st.markdown("Analyze income, expenses, spending behavior, and financial health.")

    # =====================================================
    # KPI SECTION
    # =====================================================
    total_income = filtered_df["Credit"].sum()
    total_expense = filtered_df["Debit"].sum()
    log_info(f"total income: {total_income} and total expense: {total_expense}")
    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100) if total_income != 0 else 0
    current_balance = filtered_df["Balance"].iloc[-1] if len(filtered_df) > 0 else 0

    monthly_expense = filtered_df.groupby("Month")["Debit"].sum()
    expense_volatility = monthly_expense.std() if len(monthly_expense) > 1 else 0

    # Custom Financial Health Score (Non-ML)
    health_score = (
        (savings_rate * 0.5) +
        ((1 / (expense_volatility + 1)) * 100 * 0.3) +
        ((net_savings / (total_income + 1)) * 100 * 0.2)
    )

    health_score = max(0, min(100, health_score))

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Income", f"₹{total_income:,.0f}")
    col2.metric("Total Expense", f"₹{total_expense:,.0f}")
    col3.metric("Net Savings", f"₹{net_savings:,.0f}")
    col4.metric("Savings Rate", f"{savings_rate:.2f}%")
    col5.metric("Financial Health Score", f"{health_score:.1f}/100")

    st.divider()

    # =====================================================
    # INCOME VS EXPENSE TREND
    # =====================================================
    monthly = filtered_df.groupby("Month").agg({
        "Debit": "sum",
        "Credit": "sum"
    }).reset_index()

    if len(monthly) > 0:
        fig = px.line(
            monthly,
            x="Month",
            y=["Debit", "Credit"],
            title="📈 Monthly Income vs Expense Trend",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =====================================================
    # CATEGORY & METHOD ANALYSIS
    # =====================================================
    colA, colB = st.columns(2)

    with colA:
        category_data = (
            filtered_df.groupby("label")["Debit"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        if len(category_data) > 0:
            fig2 = px.pie(
                category_data,
                names="label",
                values="Debit",
                title="🥧 Spending by Category"
            )
            st.plotly_chart(fig2, use_container_width=True)

    with colB:
        method_data = (
            filtered_df.groupby("Method")["Debit"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        if len(method_data) > 0:
            fig3 = px.pie(
                method_data,
                names="Method",
                values="Debit",
                title="💳 Spending by Payment Method"
            )
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # =====================================================
    # TOP RECIPIENTS
    # =====================================================
    st.subheader("🏆 Top 10 Expense Recipients")

    top_recipients = (
        filtered_df.groupby("Reciever_Sender")["Debit"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    if len(top_recipients) > 0:
        fig4 = px.bar(
            top_recipients,
            x="Debit",
            y="Reciever_Sender",
            orientation="h",
            title="Top 10 Recipients by Total Expense"
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # =====================================================
    # RECURRING PAYMENT DETECTION (LOGIC ONLY)
    # =====================================================
    st.subheader("🔁 Recurring Payments (Detected by Frequency)")

    recurring = (
        filtered_df.groupby(["Reciever_Sender"])
        .size()
        .reset_index(name="Transaction Count")
    )

    recurring = recurring[recurring["Transaction Count"] >= 3]
    recurring = recurring.sort_values("Transaction Count", ascending=False)

    if len(recurring) > 0:
        st.dataframe(recurring)
    else:
        st.info("No recurring payments detected (≥3 similar transactions).")

    st.divider()

    # =====================================================
    # SPENDING CONCENTRATION VISUAL ANALYSIS
    # =====================================================
    st.subheader("📊 Spending Concentration Analysis")

    expense_data = filtered_df[filtered_df["Debit"] > 0].copy()

    if len(expense_data) > 0 and expense_data["Debit"].sum() > 0:

        expense_data = expense_data.sort_values("Debit", ascending=False).reset_index(drop=True)
        total_spending = expense_data["Debit"].sum()
        total_transactions = len(expense_data)

        # Cumulative %
        expense_data["Cumulative %"] = (
            expense_data["Debit"].cumsum() / total_spending
        ) * 100

        # Threshold calculations
        def transactions_to_reach(percent):
            return expense_data[expense_data["Cumulative %"] <= percent].shape[0]

        t50 = transactions_to_reach(50)
        t80 = transactions_to_reach(80)
        t90 = transactions_to_reach(90)

        pct50 = t50 / total_transactions
        pct80 = t80 / total_transactions
        pct90 = t90 / total_transactions

        top5_ratio = (
            expense_data.head(5)["Debit"].sum() / total_spending
        ) * 100 if total_transactions >= 5 else 0

        # -----------------------------
        # 1️⃣ Progress Bar Visualization
        # -----------------------------
        st.markdown("### 🎯 Transaction Share Needed to Reach Spending Levels")

        col1, col2, col3 = st.columns(3)

        col1.metric("50% Spending", f"{pct50:.1%} of transactions")
        col1.progress(pct50)

        col2.metric("80% Spending", f"{pct80:.1%} of transactions")
        col2.progress(pct80)

        col3.metric("90% Spending", f"{pct90:.1%} of transactions")
        col3.progress(pct90)

        st.divider()

        # -----------------------------
        # 2️⃣ Top 5 Contribution
        # -----------------------------
        st.markdown("### 🏆 Top 5 Transactions Contribution")

        st.metric("Top 5 Contribution to Total Spending", f"{top5_ratio:.2f}%")

        st.divider()

        # -----------------------------
        # 3️⃣ Lorenz Curve (True Visual Concentration)
        # -----------------------------
        st.markdown("### 📈 Spending Inequality Curve (Lorenz Curve)")

        lorenz_data = expense_data.sort_values("Debit")
        lorenz_data["Cumulative Spending %"] = (
            lorenz_data["Debit"].cumsum() / total_spending
        )
        lorenz_data["Cumulative Transactions %"] = (
            np.arange(1, total_transactions + 1) / total_transactions
        )

        import plotly.graph_objects as go

        fig = go.Figure()

        # Lorenz curve
        fig.add_trace(go.Scatter(
            x=lorenz_data["Cumulative Transactions %"],
            y=lorenz_data["Cumulative Spending %"],
            mode="lines",
            name="Actual Spending Distribution"
        ))

        # Perfect equality line
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Perfect Equality",
            line=dict(dash="dash")
        ))

        fig.update_layout(
            xaxis_title="Cumulative % of Transactions",
            yaxis_title="Cumulative % of Spending",
            yaxis_range=[0, 1],
            xaxis_range=[0, 1]
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Not enough expense data for concentration analysis.")

    st.divider()

    # =====================================================
    # TRANSACTION FREQUENCY ANALYSIS
    # =====================================================
    st.subheader("📅 Transaction Frequency Analysis")

    if len(filtered_df) > 0:

        # =====================================================
        # MONTHLY TRANSACTION ANALYZER
        # =====================================================
        st.subheader("📅 Monthly Transaction Analyzer")

        if len(filtered_df) > 0:

            # Create Month-Year column
            filtered_df["Month-Year"] = filtered_df["Date"].dt.to_period("M").astype(str)

            # Month selector
            selected_month = st.selectbox(
                "Select Month",
                sorted(filtered_df["Month-Year"].unique())
            )

            month_df = filtered_df[filtered_df["Month-Year"] == selected_month]

            # ---------------------------------------
            # Daily Transaction Count (within month)
            # ---------------------------------------
            daily_counts = (
                month_df
                .groupby(month_df["Date"].dt.date)
                .size()
                .reset_index(name="Transactions")
            )

            if len(daily_counts) > 0:

                avg_tx_per_day = daily_counts["Transactions"].mean()
                max_tx = daily_counts["Transactions"].max()
                min_tx = daily_counts["Transactions"].min()

                most_active_day = daily_counts.loc[
                    daily_counts["Transactions"].idxmax(), "Date"
                ]

                least_active_day = daily_counts.loc[
                    daily_counts["Transactions"].idxmin(), "Date"
                ]

                col1, col2, col3 = st.columns(3)

                col1.metric("Avg Transactions per Day", f"{avg_tx_per_day:.2f}")
                col2.metric("Most Active Day", f"{most_active_day}")
                col3.metric("Least Active Day", f"{least_active_day}")

                # Daily trend chart
                fig_month = px.bar(
                    daily_counts,
                    x="Date",
                    y="Transactions",
                    title=f"Daily Transactions in {selected_month}"
                )

                st.plotly_chart(fig_month, use_container_width=True)

            else:
                st.info("No transactions available for selected month.")

        else:
            st.info("No data available.")

        st.divider()


        # ---------------------------------------
        # 2️⃣ Day of Week Analysis
        # ---------------------------------------
        weekday_data = filtered_df.copy()
        weekday_data["Day"] = weekday_data["Date"].dt.day_name()

        weekday_counts = (
            weekday_data
            .groupby("Day")
            .size()
            .reindex([
                "Monday","Tuesday","Wednesday",
                "Thursday","Friday","Saturday","Sunday"
            ])
            .reset_index(name="Transactions")
        )

        fig_weekday = px.bar(
            weekday_counts,
            x="Day",
            y="Transactions",
            title="Transactions by Day of Week"
        )

        st.plotly_chart(fig_weekday, use_container_width=True)

    else:
        st.info("No transaction data available for frequency analysis.")

    st.divider()



    # =====================================================
    # RAW DATA
    # =====================================================
    st.subheader("📄 Transaction Data")

    st.dataframe(
        filtered_df.sort_values("Date", ascending=False),
        use_container_width=True
    )
    
if page == "🤖 Financial Q&A Chatbot":

    # =====================================================
    # FINANCIAL Q&A CHATBOT
    # =====================================================
    st.subheader("🤖 Financial Q&A Assistant")

    st.markdown("Ask questions about your transactions. Example:")
    st.markdown("- What is my total spending this month?")
    st.markdown("- How much did I spend on food?")
    st.markdown("- Who is my top counterparty?")
    st.markdown("- What is my average monthly expense?")

    # -----------------------------
    # Tool Definition
    # -----------------------------
    def prompt_builder(user_query):
        prompt=f"""
    You are a Prompt Builder Agent.

    Your task is to reformulate a raw user query into a precise,
    structured, and unambiguous analytical query that will be passed
    to a Pandas Retrieval Agent.

    Dataset name: df
    Dataset structure: {str(filtered_df.columns)}
    User query: {user_query}

    IMPORTANT:
    - The 'date' column is stored as STRING.
    - Format is 'yyyy-mm-dd'.
    - Any date filtering MUST explicitly instruct conversion using:
    pd.to_datetime(df['date'], dayfirst=True)

    ------------------------------------------------
    INSTRUCTIONS
    ------------------------------------------------

    1. Understand the intent.
    2. Identify:
    - Columns
    - Filters
    - Aggregations
    - Sorting
    - Grouping
    - Limits
    3. If date filtering is required:
    - Explicitly state that the 'date' column must be converted
        using pd.to_datetime with dayfirst=True before filtering.
    4. Replace vague language with exact column names.
    5. Make the query deterministic and structured.
    6. Ensure only columns present in {str(filtered_df.columns)} are referenced.
    7. dont capitalize any name all names in database are in lowercase

    ------------------------------------------------
    OUTPUT RULES
    ------------------------------------------------

    Return ONLY the refined analytical query.

    Do NOT return:
    - Pandas code
    - Explanation
    - Markdown
    - Extra commentary

    ------------------------------------------------
    EXAMPLES
    ------------------------------------------------

    User Query:
    "how much did i spend last m
    """

        llm=nexa_ai()
        response=llm.invoke(prompt)
        return response.content
    def python_code_executor(code: str) -> str:
        """
        Executes Python code with access to pandas as pd and dataframe df.
        The code MUST assign the final output to a variable named result.
        """
        local_env = {
            "df": filtered_df,
            "pd": pd
        }

        try:
            exec(code, {}, local_env)
            if "result" not in local_env:
                return "Error: code did not set a result variable."
            return str(local_env["result"])
        except Exception as e:
            return f"Execution error: {e}"

    python_code_executor_tool = Tool(
        name="python_code_executor_tool",
        func=python_code_executor,
        description=(
            "Executes Python pandas code on a DataFrame named df. "
            "Use this tool for any calculations, filtering, grouping, or aggregation. "
            "The code MUST assign the final value to a variable named result."
        ),
    )

    SYSTEM_PROMPT = f"""
    You are a financial data analysis agent.

    You have access to:
    - A pandas DataFrame named df
    - A tool called python_code_executor_tool that executes Python code
    - The DataFrame contains a bank statement that has already been cleaned, parsed, and categorized.

    IMPORTANT RULES:
    1. You MUST use the python_code_executor_tool to answer any question that involves:
    - numbers
    - counts
    - totals
    - filtering
    - grouping
    - trends
    - comparisons
    - dates
    - categories
    2. NEVER answer such questions from memory or intuition.
    3. NEVER fabricate values.
    4. NEVER describe results without computing them.
    5. If computation is required, ALWAYS:
    - write valid Python code
    - operate only on df
    - use pandas idioms
    6. After the tool returns results:
    - summarize the result clearly in plain English
    - do NOT include Python code in the final answer

    DATAFRAME SCHEMA (df):

    Columns:
    {str(filtered_df.columns)}
    date is in DD/MM/YYYY format so rewrite query accordingly

    dataframe information:
    {str(filtered_df.info())}

    GUIDELINES FOR ANALYSIS:
    - csv could be upper or lower, Always without case, convert to lowercase to compare both
    - use category column for category based query
    - Always prefer AMOUNT + DIRECTION over DEPOSITS/WITHDRAWALS
    - Do NOT aggregate BALANCE
    - Do NOT sum text columns
    - Use explicit aggregations (column → function mapping)
    - Use groupby + agg for summaries
    - Use filtering before aggregation
    - Use reset_index() for clean outputs

    COMMON TASK PATTERNS:
    - Total spending → filter DIRECTION == 'DEBIT', then sum AMOUNT
    - Income → filter DIRECTION == 'CREDIT'
    - Category analysis → group by CATEGORY
    - Person/business analysis → group by COUNTERPARTY_NAME
    - Frequency → count rows

    OUTPUT FORMAT:
    - If a tool call is needed → call python_code_executor_tool with ONLY Python code
    - If no computation is needed → answer directly
    - Final answer must be clear, concise, and numeric where applicable

    If the user asks a vague question:
    - infer the most reasonable financial interpretation
    - compute results
    - explain assumptions briefly

    You are precise, cautious, and computation-driven.

    Example:
        User: What is my average monthly expense?
        Tool call arg: import pandas as pd
                        df=pd.read_csv('improved.csv')
                        # Convert \'Date\' column to datetime format
                        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
                        # Filter for debit transactions\\n
                        df_debit = df[df['Debit_Credit'] == 'dr']
                        # Group by month and year, sum expenses, and compute average\\n
                        average_monthly_expense = df_debit.groupby([df_debit['Date'].dt.year, df_debit['Date'].dt.month])['Debit'].sum().mean()
                        result = average_monthly_expense
        output:     42637.792499999996
    """

    if "agent" not in st.session_state:
        from LLM_Gateway import nexa_ai
        llm = nexa_ai()

        ramu = create_agent(
            model=llm,
            tools=[python_code_executor_tool],
            system_prompt=SYSTEM_PROMPT,
        )

    def qa_response(query):
        response = ramu.invoke(
            {"messages": [{"role": "user", "content": query}]}
        )
        print(response)
        return response["messages"][-1].content
# =====================================================
# FINANCIAL Q&A CHATBOT PAGE
# =====================================================

    st.markdown("""
<style>

/* Scrollable chat area */
.chat-container {
    max-height: 500px;
    overflow-y: auto;
    padding-right: 10px;
    margin-bottom: 20px;
}

/* Smooth scrollbar */
.chat-container::-webkit-scrollbar {
    width: 6px;
}

.chat-container::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.2);
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <style>

    /* INPUT FIELD */
    div[data-testid="stTextInput"] > div > div > input {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        border-radius: 14px 0 0 14px !important;
        border: 1px solid #334155 !important;
        border-right: none !important;
        padding: 10px 14px !important;
        height: 42px !important;
    }

    /* INPUT FOCUS */
    div[data-testid="stTextInput"] > div > div > input:focus {
        box-shadow: none !important;
        outline: none !important;
    }

    /* SEND BUTTON */
    div[data-testid="stFormSubmitButton"] > button {
        background: #1e293b !important;
        color: white !important;
        height: 42px !important;
        width: 100% !important;
        padding: 10 !important;
        font-size: 18px !important;
        transition: all 0.2s ease-in-out !important;
    }

    /* HOVER */
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: #000000 !important;
        border: 1px solid #6366f1 !important;
        border-left: none !important;
    }

    /* Remove extra spacing */
    div[data-testid="stFormSubmitButton"] {
        display: flex;
        align-items: stretch;
    }

    </style>
    """, unsafe_allow_html=True)


    with st.form("chat_form", clear_on_submit=True):

        col_input, col_button = st.columns([10, 1])

        with col_input:
            user_query = st.text_input(
                "",
                placeholder="Ask a financial question...",
                label_visibility="collapsed"
            )

        with col_button:
            submitted = st.form_submit_button("🔍")



    if st.button("Clear Chat 🗑", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    # -----------------------------------------------------
    # Handle Submission
    # -----------------------------------------------------
    if submitted and user_query:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.session_state.chat_history.append(("user", user_query))

        with st.spinner("Analyzing your financial data..."):
            try:
                structured_query = prompt_builder(user_query)
                response = qa_response(structured_query)
                answer = response if response else "I couldn't compute that."
            except Exception as e:
                answer = f"⚠️ Error: {e}"

        st.session_state.chat_history.append(("assistant", answer))
        st.rerun()



