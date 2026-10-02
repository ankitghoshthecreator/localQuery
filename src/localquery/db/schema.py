"""
LocalQuery DB Schema
======================
Creates and populates the default finance.db demo database,
and provides utilities for extracting schema information from any SQLite DB.
"""

from __future__ import annotations

import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List

# Default demo database created in the project root
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "finance.db")
# Normalise to a clean path
DB_PATH = os.path.normpath(DB_PATH)

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    email       TEXT    UNIQUE NOT NULL,
    signup_date DATE    NOT NULL,
    status      TEXT    NOT NULL  -- 'active' or 'inactive'
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    account_type TEXT    NOT NULL,  -- 'checking', 'savings', 'credit'
    balance      DECIMAL(10, 2) NOT NULL,
    created_at   DATE    NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL,
    amount          DECIMAL(10, 2) NOT NULL,
    transaction_date DATE   NOT NULL,
    category        TEXT    NOT NULL,  -- 'groceries','utilities','entertainment','income','rent'
    description     TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
"""

_USERS = [
    ("Alice",   "Smith",  "alice@example.com",   "2023-01-15", "active"),
    ("Bob",     "Jones",  "bob@example.com",     "2023-02-20", "active"),
    ("Charlie", "Brown",  "charlie@example.com", "2022-11-05", "inactive"),
    ("Diana",   "Prince", "diana@example.com",   "2024-01-10", "active"),
    ("Eve",     "Taylor", "eve@example.com",     "2023-06-01", "active"),
    ("Frank",   "Castle", "frank@example.com",   "2022-09-15", "inactive"),
]

_ACCOUNTS = [
    (1, "checking", 1_500.50,   "2023-01-16"),
    (1, "savings",  10_000.00,  "2023-01-20"),
    (2, "checking", 500.00,     "2023-02-21"),
    (3, "checking", 0.00,       "2022-11-06"),
    (4, "checking", 2_500.75,   "2024-01-11"),
    (4, "credit",   -450.00,    "2024-01-15"),
    (5, "savings",  7_200.00,   "2023-06-02"),
    (5, "checking", 1_100.00,   "2023-06-05"),
    (6, "checking", 50.00,      "2022-09-16"),
]


def setup_db(db_path: str = DB_PATH) -> None:
    """
    Create the finance demo database schema and seed it with synthetic data.

    If the file already exists, this function is a no-op.

    Args:
        db_path: Path where the SQLite file will be created.
    """
    if os.path.exists(db_path):
        return  # Already set up

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(_SCHEMA_DDL)

    # Seed users
    cursor.executemany(
        "INSERT INTO users (first_name, last_name, email, signup_date, status) "
        "VALUES (?, ?, ?, ?, ?)",
        _USERS,
    )

    # Seed accounts
    cursor.executemany(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) "
        "VALUES (?, ?, ?, ?)",
        _ACCOUNTS,
    )

    # Generate synthetic transactions for the past year
    categories_expense = ["groceries", "utilities", "entertainment", "rent"]
    account_ids = list(range(1, len(_ACCOUNTS) + 1))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    transactions = []

    rng = random.Random(42)  # Deterministic seed for reproducibility
    for i in range(300):
        acc_id = rng.choice(account_ids)
        amount = round(rng.uniform(-800, 2_000), 2)
        if amount == 0:
            amount = 10.0
        category = "income" if amount > 0 else rng.choice(categories_expense)
        t_date = start_date + timedelta(days=rng.randint(0, 364))
        transactions.append(
            (acc_id, amount, t_date.strftime("%Y-%m-%d"), category, f"Txn #{i + 1}")
        )

    cursor.executemany(
        "INSERT INTO transactions "
        "(account_id, amount, transaction_date, category, description) "
        "VALUES (?, ?, ?, ?, ?)",
        transactions,
    )

    conn.commit()
    conn.close()


def extract_schema_from_db(db_path: str) -> List[str]:
    """
    Dynamically extract CREATE TABLE DDL statements from any SQLite database.

    Each table becomes one document in the returned list, making this
    compatible with the :class:`~localquery.retrieval.retriever.HybridRetriever`.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of strings, one per table: ``"Table: <name>\\nSchema:\\n<DDL>"``.

    Raises:
        FileNotFoundError: If *db_path* does not exist.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )

    docs: List[str] = []
    for name, ddl in cursor.fetchall():
        if ddl:  # Skip virtual / shadow tables that have no DDL
            docs.append(f"Table: {name}\nSchema:\n{ddl}")

    conn.close()
    return docs


def get_schema_description() -> List[str]:
    """
    Return a human-readable description of the default finance schema.

    Useful for documentation and testing without a live DB connection.
    """
    return [
        (
            "Table: users (user_id INTEGER, first_name TEXT, last_name TEXT, "
            "email TEXT, signup_date DATE, status TEXT). "
            "status can be 'active' or 'inactive'."
        ),
        (
            "Table: accounts (account_id INTEGER, user_id INTEGER, "
            "account_type TEXT, balance DECIMAL, created_at DATE). "
            "account_type can be 'checking', 'savings', or 'credit'."
        ),
        (
            "Table: transactions (transaction_id INTEGER, account_id INTEGER, "
            "amount DECIMAL, transaction_date DATE, category TEXT, description TEXT). "
            "category can be 'groceries', 'utilities', 'entertainment', 'income', or 'rent'."
        ),
    ]


if __name__ == "__main__":
    setup_db()
    print(f"Finance demo database ready at: {DB_PATH}")
