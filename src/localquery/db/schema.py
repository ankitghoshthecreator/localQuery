import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = "finance.db"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    signup_date DATE NOT NULL,
    status TEXT NOT NULL -- 'active' or 'inactive'
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_type TEXT NOT NULL, -- 'checking', 'savings', 'credit'
    balance DECIMAL(10, 2) NOT NULL,
    created_at DATE NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_date DATE NOT NULL,
    category TEXT NOT NULL, -- 'groceries', 'utilities', 'entertainment', 'income', 'rent'
    description TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
"""

def setup_db(db_path=DB_PATH):
    """Creates the schema and populates synthetic data if not exists."""
    if os.path.exists(db_path):
        return # Already setup

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(SCHEMA_DDL)
    
    # Generate Synthetic Data
    users = [
        ("Alice", "Smith", "alice@example.com", "2023-01-15", "active"),
        ("Bob", "Jones", "bob@example.com", "2023-02-20", "active"),
        ("Charlie", "Brown", "charlie@example.com", "2022-11-05", "inactive"),
        ("Diana", "Prince", "diana@example.com", "2024-01-10", "active"),
    ]
    cursor.executemany("INSERT INTO users (first_name, last_name, email, signup_date, status) VALUES (?, ?, ?, ?, ?)", users)
    
    # Accounts
    accounts = [
        (1, "checking", 1500.50, "2023-01-16"),
        (1, "savings", 10000.00, "2023-01-20"),
        (2, "checking", 500.00, "2023-02-21"),
        (3, "checking", 0.00, "2022-11-06"),
        (4, "checking", 2500.75, "2024-01-11"),
        (4, "credit", -450.00, "2024-01-15"),
    ]
    cursor.executemany("INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)", accounts)
    
    # Transactions
    categories = ['groceries', 'utilities', 'entertainment', 'income', 'rent']
    transactions = []
    
    # generate random transactions for past year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    for _ in range(200):
        acc_id = random.choice([1, 2, 3, 4, 5, 6])
        amount = round(random.uniform(-500, 1000), 2)
        if amount == 0: amount = 10.0
        
        # Adjust categories based on amount
        cat = 'income' if amount > 0 else random.choice(['groceries', 'utilities', 'entertainment', 'rent'])
        
        t_date = start_date + timedelta(days=random.randint(0, 365))
        transactions.append((acc_id, amount, t_date.strftime("%Y-%m-%d"), cat, f"Dummy transaction {_}"))
        
    cursor.executemany("INSERT INTO transactions (account_id, amount, transaction_date, category, description) VALUES (?, ?, ?, ?, ?)", transactions)
    
    conn.commit()
    conn.close()

def get_schema_description():
    """Returns a textual description of the schema for the LLM."""
    return [
        "Table: users (user_id INTEGER, first_name TEXT, last_name TEXT, email TEXT, signup_date DATE, status TEXT). 'status' can be 'active' or 'inactive'.",
        "Table: accounts (account_id INTEGER, user_id INTEGER, account_type TEXT, balance DECIMAL, created_at DATE). 'account_type' can be 'checking', 'savings', or 'credit'.",
        "Table: transactions (transaction_id INTEGER, account_id INTEGER, amount DECIMAL, transaction_date DATE, category TEXT, description TEXT). 'category' can be 'groceries', 'utilities', 'entertainment', 'income', or 'rent'."
    ]

if __name__ == "__main__":
    setup_db()
    print("Database setup complete.")
