"""
LocalQuery - Privacy-First Text-to-SQL with Hybrid RAG
========================================================
Interactive CLI for querying local SQLite databases using natural language.
No data leaves your machine — all inference runs through Ollama locally.
"""

import sys
import os

# Ensure the src package is importable when running app.py directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import glob
from localquery.db.schema import setup_db
from localquery.orchestration.pipeline import LocalQueryPipeline


def print_banner():
    width = 62
    print("=" * width)
    print("  LocalQuery  ·  Privacy-First Text-to-SQL  ·  Hybrid RAG  ")
    print("  All inference runs locally via Ollama. Zero data egress.  ")
    print("=" * width)
    print("  Commands: 'help' · 'history' · 'clear' · 'exit'")
    print("=" * width)


def print_help():
    print("""
Commands:
  help       - Show this help message
  history    - Show query history for this session
  clear      - Clear the screen
  exit/quit  - Exit LocalQuery

Tips:
  · Ask natural language questions about your database
  · If a question is ambiguous, LocalQuery will ask for clarification
  · After a clarification prompt, type your answer and press Enter
  · LocalQuery only runs SELECT queries — your data is safe
""")


def main():
    print_banner()

    # 1. Ensure finance.db exists (default demo DB)
    setup_db()

    # 2. Find databases in project root and data/ folder
    db_files = sorted(glob.glob("*.db") + glob.glob("data/*.db"))
    if not db_files:
        print("\n[!] No databases found.")
        print("    Run: python data/generate_dummy_dbs.py")
        print("    Or:  python -c \"from src.localquery.db.schema import setup_db; setup_db()\"")
        return

    print("\nAvailable Databases:")
    for i, db in enumerate(db_files, 1):
        size_kb = os.path.getsize(db) // 1024
        print(f"  [{i}] {db}  ({size_kb} KB)")

    # 3. Database selection
    selected_db = None
    while selected_db is None:
        try:
            raw = input("\nSelect a database number to query: ").strip()
            choice = int(raw)
            if 1 <= choice <= len(db_files):
                selected_db = db_files[choice - 1]
            else:
                print(f"    Please enter a number between 1 and {len(db_files)}.")
        except ValueError:
            print("    Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            return

    print(f"\n✓ Connected to: {selected_db}")

    # 4. Initialize Pipeline
    model_name = os.environ.get("LOCALQUERY_MODEL", "qwen2.5-coder:3b")
    print(f"✓ Using model   : {model_name}")
    print("✓ Indexing schema (first run may take a moment)...\n")

    try:
        pipeline = LocalQueryPipeline(db_path=selected_db, model_name=model_name)
    except FileNotFoundError as e:
        print(f"\n[Error] {e}")
        return

    query_history: list[str] = []

    # 5. Main interactive loop
    while True:
        try:
            user_input = input("\n[You]> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        low = user_input.lower()

        # Built-in commands
        if low in ("exit", "quit"):
            print("Goodbye!")
            break
        if low == "help":
            print_help()
            continue
        if low == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            print_banner()
            continue
        if low == "history":
            if not query_history:
                print("  (No queries yet this session.)")
            else:
                print("\n  Session Query History:")
                for idx, q in enumerate(query_history, 1):
                    print(f"  {idx:>3}. {q}")
            continue

        query_history.append(user_input)
        print("\n  [Thinking...]\n")

        result = pipeline.process_query(user_input)

        if result["status"] == "needs_clarification":
            print("  [Clarification needed]")
            print(f"  ❓ {result['clarification_question']}")
            print("  ↳  Please answer above, then press Enter.")

        elif result["status"] == "success":
            print("  [Generated SQL]")
            print(f"  ┌─────────────────────────────────────────────────┐")
            for line in result["sql"].splitlines():
                print(f"  │  {line}")
            print(f"  └─────────────────────────────────────────────────┘\n")

            print("  [Results]")
            for line in result["formatted_result"].splitlines():
                print(f"  {line}")

        else:
            print(f"  [Error] {result.get('error', 'Unknown error')}")
            if "Ollama" in str(result.get("error", "")):
                print("  ↳  Make sure Ollama is running: `ollama serve`")
                print(f"  ↳  And the model is pulled: `ollama pull {model_name}`")


if __name__ == "__main__":
    main()
