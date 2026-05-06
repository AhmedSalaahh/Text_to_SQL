# Northwind SQL Assistant

A natural-language-to-SQL query engine built with **LangChain**, **GPT-4o**, and **Streamlit**, backed by a hosted **Supabase PostgreSQL** database. 
Ask questions in plain English; the app generates SQL, runs it against a real relational database, and returns a formatted, downloadable table.

---

## Features

| Feature | Detail |
|---|---|
| **NL → SQL** | GPT-4o generates PostgreSQL queries from plain-English questions |
| **SQL safety validation** | Only `SELECT` statements are ever executed |
| **Auto-correction** | If a query fails, the error is fed back to GPT-4o for a second attempt |
| **DataFrame results** | Results rendered as an interactive table via `st.dataframe()` |
| **CSV export** | One-click download of any result set |
| **Query history** | Sidebar log of all questions; click any to re-run |
| **Hosted database** | Supabase PostgreSQL — no local DB setup required |

---

## Project Structure

```
text_to_sql/
app.py # Streamlit UI
chain.py # LangChain LCEL pipeline (generate + auto-fix)
requirements.txt
.env.example # Environment variable template
.gitignore
README.md
```

---

## Getting Started

### 1. Set up Supabase

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Load the Northwind dataset via the Supabase SQL editor:
- Get the dump from [github.com/pthom/northwind_psql](https://github.com/pthom/northwind_psql)
- Paste and run `northwind.sql` in **Supabase → SQL Editor**
4. Copy your connection string from **Project Settings → Database → Connection string → URI** 
Use the **Session mode pooler URL** (port 5432)

### 2. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/northwind-sql-assistant.git
cd northwind-sql-assistant
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres.xxxx:your-password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### 4. Run

```bash
streamlit run app.py
```


---

## Example Questions

- *Top 5 customers by total order value*
- *Monthly revenue for 2024*
- *Which products have never been ordered?*
- *Sales by employee, ranked highest to lowest*
- *Average freight cost by destination country*

---

## Architecture

```
User question


ChatPromptTemplate GPT-4o StrOutputParser

SQL query

Safety validation
(SELECT-only guard)

Supabase PostgreSQL
/ \
OK Error

DataFrame Feed error
+ CSV btn back to GPT-4o

Corrected SQL

Re-execute
```

