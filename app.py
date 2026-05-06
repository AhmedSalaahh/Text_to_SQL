import ast
import io
import os

import pandas as pd
import streamlit as st

from chain import generate_and_run, get_schema

# Page config 
st.set_page_config(
page_title="Northwind SQL Assistant",
page_icon=None,
layout="wide",
)

# Custom CSS 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
font-family: 'DM Serif Display', serif !important;
}

.stTextInput > div > div > input {
font-family: 'DM Sans', sans-serif;
font-size: 1rem;
border-radius: 8px;
}

.stCodeBlock, code, pre {
font-family: 'DM Mono', monospace !important;
}

.result-card {
background: #f8f7f4;
border-left: 4px solid #2d6a4f;
border-radius: 0 8px 8px 0;
padding: 1rem 1.25rem;
margin-bottom: 1rem;
}

.badge-corrected {
display: inline-block;
background: #fff3cd;
color: #856404;
border: 1px solid #ffc107;
border-radius: 4px;
padding: 2px 8px;
font-size: 0.75rem;
font-weight: 500;
margin-left: 8px;
vertical-align: middle;
}

.badge-error {
display: inline-block;
background: #f8d7da;
color: #842029;
border: 1px solid #f5c2c7;
border-radius: 4px;
padding: 2px 8px;
font-size: 0.75rem;
font-weight: 500;
margin-left: 8px;
vertical-align: middle;
}

.history-item {
background: #ffffff;
border: 1px solid #e8e4dc;
border-radius: 8px;
padding: 0.65rem 0.9rem;
margin-bottom: 0.5rem;
font-size: 0.85rem;
color: #333;
cursor: pointer;
}

.history-item:hover {
background: #f0ece4;
}

.sidebar-header {
font-family: 'DM Serif Display', serif;
font-size: 1.1rem;
color: #2d6a4f;
margin-bottom: 0.75rem;
}

.schema-expander summary {
font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)


# Session state 
if "history" not in st.session_state:
st.session_state.history = [] # list of dicts: {question, sql, result, corrected, error}
if "question_input" not in st.session_state:
st.session_state.question_input = ""


# Sidebar 
with st.sidebar:
st.markdown('<div class="sidebar-header">Query History</div>', unsafe_allow_html=True)

if not st.session_state.history:
st.caption("Your queries will appear here.")
else:
if st.button("Clear history", use_container_width=True):
st.session_state.history = []
st.rerun()

for i, item in enumerate(reversed(st.session_state.history)):
label = item["question"][:55] + ("…" if len(item["question"]) > 55 else "")
status = "[ok]" if not item["error"] else "[err]"
if st.button(f"{status} {label}", key=f"hist_{i}", use_container_width=True):
st.session_state.question_input = item["question"]
st.rerun()

st.divider()
with st.expander(" Database schema", expanded=False):
st.code(get_schema(), language="sql")

st.caption("Northwind · GPT-4o · LangChain · Streamlit")


# Main UI 
st.markdown("# Northwind SQL Assistant")
st.markdown(
"Ask questions about orders, customers, products, and more — "
"in plain English. GPT-4o writes the SQL for you."
)

# Example chips
EXAMPLES = [
"Top 5 customers by total order value",
"Monthly revenue for 2024",
"Which products have never been ordered?",
"Sales by employee, ranked highest to lowest",
"Average order freight by country",
]

st.markdown("**Try an example:**")
cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
if col.button(ex, use_container_width=True):
st.session_state.question_input = ex
st.rerun()

st.divider()

question = st.text_input(
"Your question",
value=st.session_state.question_input,
placeholder="e.g. Which product category generates the most revenue?",
label_visibility="collapsed",
)

run_btn = st.button("Run ↵", type="primary", use_container_width=False)

# Execution 
if run_btn and question.strip():
st.session_state.question_input = ""

with st.spinner("Generating SQL…"):
schema = get_schema()
outcome = generate_and_run(question.strip(), schema)

# Persist to history
st.session_state.history.append({**outcome, "question": question.strip()})

# Show SQL 
corrected_badge = (
'<span class="badge-corrected">auto-corrected</span>'
if outcome["corrected"] else ""
)
st.markdown(f"#### Generated SQL {corrected_badge}", unsafe_allow_html=True)
st.code(outcome["sql"], language="sql")

# Show result or error 
if outcome["error"]:
st.error(outcome["error"])
else:
st.markdown("#### Results")

raw = outcome["result"]

# SQLDatabase.run() returns a string representation of a list of tuples
try:
rows = ast.literal_eval(raw) if raw else []
except Exception:
rows = []

if rows and isinstance(rows, list) and isinstance(rows[0], (list, tuple)):
# Build a DataFrame with generic column names
df = pd.DataFrame(rows)

# Try to infer column names from the SQL
import re as _re
select_match = _re.search(
r"SELECT\s+(.*?)\s+FROM", outcome["sql"],
_re.IGNORECASE | _re.DOTALL,
)
if select_match:
raw_cols = select_match.group(1)
# Strip aliases (AS x), functions, asterisks
col_parts = [c.strip() for c in raw_cols.split(",")]
named = []
for part in col_parts:
alias = _re.search(r"\bAS\s+(\w+)$", part, _re.IGNORECASE)
if alias:
named.append(alias.group(1))
else:
named.append(part.split(".")[-1].strip("() "))
if len(named) == len(df.columns):
df.columns = named

st.dataframe(df, use_container_width=True)

# CSV download 
csv_buf = io.StringIO()
df.to_csv(csv_buf, index=False)
st.download_button(
label=" Download as CSV",
data=csv_buf.getvalue(),
file_name="query_results.csv",
mime="text/csv",
)
else:
# Fallback: show raw string
st.markdown(f'<div class="result-card">{raw}</div>', unsafe_allow_html=True)

elif run_btn and not question.strip():
st.warning("Please enter a question first.")
