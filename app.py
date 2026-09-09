import sys
import glob
import os
from localquery.db.schema import setup_db
from localquery.orchestration.pipeline import LocalQueryPipeline

def print_header():
    print("="*60)
    print("LocalQuery - Privacy-First Text-to-SQL with Hybrid RAG")
    print("Type 'exit' or 'quit' to close.")
    print("="*60)

def main():
    # 1. Ensure Database exists
    setup_db()
    
    # 2. Find databases
    db_files = glob.glob("*.db") + glob.glob("data/*.db")
    if not db_files:
        print("No databases found. Run 'python data/generate_dummy_dbs.py'")
        return
        
    print("Available Databases:")
    for i, db in enumerate(db_files):
        print(f"[{i+1}] {db}")
        
    while True:
        try:
            choice = int(input("\nSelect a database number to query: "))
            if 1 <= choice <= len(db_files):
                selected_db = db_files[choice-1]
                break
        except ValueError:
            pass
        print("Invalid choice.")
    
    # 3. Initialize Pipeline
    # Defaulting to a smaller model for the CLI by default if not specified
    pipeline = LocalQueryPipeline(db_path=selected_db, model_name="qwen2.5-coder:3b")
    
    print_header()
    
    while True:
        try:
            user_input = input("\n[You]> ").strip()
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            if not user_input:
                continue
                
            print("\n[LocalQuery is thinking...]")
            result = pipeline.process_query(user_input)
            
            if result["status"] == "needs_clarification":
                print("\n[LocalQuery]> " + result["clarification_question"])
                # We could implement a state machine here, but for simplicity
                # in the MVP we just ask the question and the user asks a new one.
                
            elif result["status"] == "success":
                print("\n[Generated SQL]")
                print(f"```sql\n{result['sql']}\n```\n")
                
                print("[Results]")
                print(result["formatted_result"])
                
            else:
                print(f"\n[Error] {result.get('error', 'Unknown error')}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[Fatal Error] {e}")

if __name__ == "__main__":
    main()
