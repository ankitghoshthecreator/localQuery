import pytest
from localquery.retrieval.retriever import HybridRetriever

# A realistic schema corpus similar to what the pipeline would index
SCHEMA_DOCS = [
    "Table: users\nSchema:\nCREATE TABLE users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT UNIQUE, signup_date DATE, status TEXT)",
    "Table: accounts\nSchema:\nCREATE TABLE accounts (account_id INTEGER PRIMARY KEY, user_id INTEGER, account_type TEXT, balance DECIMAL(10,2), created_at DATE, FOREIGN KEY(user_id) REFERENCES users(user_id))",
    "Table: transactions\nSchema:\nCREATE TABLE transactions (transaction_id INTEGER PRIMARY KEY, account_id INTEGER, amount DECIMAL(10,2), transaction_date DATE, category TEXT, description TEXT, FOREIGN KEY(account_id) REFERENCES accounts(account_id))",
]


def test_retriever_indexing_and_search():
    """Dense + sparse fusion should return the most relevant document for an account query."""
    retriever = HybridRetriever()
    docs = [
        "Table users: contains user_id, first_name, email, signup_date",
        "Table accounts: contains account_id, user_id, account_type, balance",
        "Table transactions: contains transaction_id, account_id, amount, category",
    ]
    retriever.index(docs)

    results = retriever.retrieve("What is the account balance?", top_k=1)
    assert len(results) == 1
    assert "accounts" in results[0].lower()


def test_retriever_empty_docs():
    """Retriever should return empty list when corpus is empty."""
    retriever = HybridRetriever()
    retriever.index([])
    results = retriever.retrieve("users")
    assert results == []


def test_retriever_top_k_limit():
    """top_k should cap the number of returned documents."""
    retriever = HybridRetriever()
    retriever.index(SCHEMA_DOCS)
    results = retriever.retrieve("balance transactions users", top_k=2)
    assert len(results) <= 2


def test_retriever_returns_all_when_top_k_exceeds_corpus():
    """If top_k > number of docs, return all docs (no out-of-bounds)."""
    retriever = HybridRetriever()
    retriever.index(SCHEMA_DOCS)
    results = retriever.retrieve("any query", top_k=100)
    assert len(results) == len(SCHEMA_DOCS)


def test_retriever_transaction_query():
    """A query about transactions should surface the transactions table."""
    retriever = HybridRetriever()
    retriever.index(SCHEMA_DOCS)
    results = retriever.retrieve("Show me all transactions for last month", top_k=2)
    joined = " ".join(results).lower()
    assert "transactions" in joined


def test_retriever_users_query():
    """A query about active users should surface the users table."""
    retriever = HybridRetriever()
    retriever.index(SCHEMA_DOCS)
    results = retriever.retrieve("List all active users", top_k=1)
    assert "users" in results[0].lower()


def test_retriever_single_doc():
    """Edge case: indexing and retrieving from a single document."""
    retriever = HybridRetriever()
    retriever.index(["Table: only_table\nSchema:\nCREATE TABLE only_table (id INTEGER)"])
    results = retriever.retrieve("query the table", top_k=3)
    assert len(results) == 1
    assert "only_table" in results[0]


def test_retriever_is_reindexable():
    """Calling index() a second time should replace the old corpus."""
    retriever = HybridRetriever()
    retriever.index(SCHEMA_DOCS)
    new_docs = ["Table: inventory (item_id, name, quantity)"]
    retriever.index(new_docs)
    results = retriever.retrieve("inventory items", top_k=1)
    assert len(results) == 1
    assert "inventory" in results[0].lower()
