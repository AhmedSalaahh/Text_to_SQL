import os
import re
from dotenv import load_dotenv
load_dotenv()

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Database connection (Supabase / any PostgreSQL) ──────────────────────────
DB_URI = os.environ["DATABASE_URL"]
# e.g. postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres

db = SQLDatabase.from_uri(DB_URI)

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# ── Prompt: generate SQL ─────────────────────────────────────────────────────
generate_prompt = ChatPromptTemplate.from_template("""
You are a senior data analyst and SQL expert working with a Northwind e-commerce database.

Given the database schema below, write a correct PostgreSQL query that answers the user's question.

Rules:
- Use ONLY the tables and columns present in the schema
- Only SELECT statements are allowed — never INSERT, UPDATE, DELETE, DROP, or any DDL
- Use PostgreSQL syntax (e.g. ILIKE, DATE_TRUNC, ::date casts, LIMIT) where appropriate
- Do NOT wrap the query in markdown fences or add any explanation
- Return ONLY the raw SQL query

Schema:
{schema}

Question:
{question}
""")

# ── Prompt: fix SQL ──────────────────────────────────────────────────────────
fix_prompt = ChatPromptTemplate.from_template("""
You are a SQL expert. The following PostgreSQL query failed with the error shown below.
Rewrite the query to fix the error.

Rules:
- Only SELECT statements are allowed
- Use PostgreSQL syntax
- Do NOT wrap the query in markdown fences or add any explanation
- Return ONLY the corrected raw SQL query

Schema:
{schema}

Original query:
{sql}

Error:
{error}
""")

sql_chain = generate_prompt | llm | StrOutputParser()
fix_chain  = fix_prompt    | llm | StrOutputParser()


def _clean(sql: str) -> str:
    """Strip markdown fences if the model ignores the instruction."""
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).replace("```", "")
    return sql.strip()


def _safe(sql: str) -> tuple[bool, str]:
    """Return (is_safe, reason). Only bare SELECT statements are allowed."""
    first = sql.strip().split()[0].upper() if sql.strip() else ""
    if first != "SELECT":
        return False, f"Only SELECT queries are permitted (got: {first!r})."
    return True, ""


def generate_and_run(question: str, schema: str) -> dict:
    """
    Returns a dict with keys:
      sql        - the (possibly corrected) SQL string
      result     - raw result string from the DB
      corrected  - bool: True if auto-correction was applied
      error      - str | None: final error message if still failing
    """
    raw_sql = sql_chain.invoke({"schema": schema, "question": question})
    sql = _clean(raw_sql)

    ok, reason = _safe(sql)
    if not ok:
        return {"sql": sql, "result": None, "corrected": False, "error": reason}

    # ── First attempt ────────────────────────────────────────────────────────
    try:
        result = db.run(sql)
        return {"sql": sql, "result": result, "corrected": False, "error": None}
    except Exception as first_err:
        pass

    # ── Auto-correct attempt ─────────────────────────────────────────────────
    fixed_raw = fix_chain.invoke({"schema": schema, "sql": sql, "error": str(first_err)})
    fixed_sql = _clean(fixed_raw)

    ok2, reason2 = _safe(fixed_sql)
    if not ok2:
        return {"sql": fixed_sql, "result": None, "corrected": True, "error": reason2}

    try:
        result = db.run(fixed_sql)
        return {"sql": fixed_sql, "result": result, "corrected": True, "error": None}
    except Exception as second_err:
        return {"sql": fixed_sql, "result": None, "corrected": True, "error": str(second_err)}


def get_schema() -> str:
    return db.get_table_info()
