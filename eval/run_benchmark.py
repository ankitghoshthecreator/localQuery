import time
import psutil
from localquery.db.schema import setup_db
from localquery.orchestration.pipeline import LocalQueryPipeline

TEST_QUERIES = [
    {
        "query": "Show me all active users",
        "type": "simple",
        "expected_sql": "SELECT * FROM users WHERE status = 'active'",
        "expected_clarification": None
    },
    {
        "query": "What is the total balance of all checking accounts?",
        "type": "aggregation",
        "expected_sql": "SELECT SUM(balance) FROM accounts WHERE account_type = 'checking'",
        "expected_clarification": None
    },
    {
        "query": "How much revenue did we make?",
        "type": "ambiguous",
        "expected_sql": None,
        "expected_clarification": "When you say 'revenue/income', are you looking for the gross total, or the net after expenses?"
    },
    {
        "query": "List transactions for Charlie Brown",
        "type": "join",
        "expected_sql": "SELECT t.* FROM transactions t JOIN accounts a ON t.account_id = a.account_id JOIN users u ON a.user_id = u.user_id WHERE u.first_name = 'Charlie' AND u.last_name = 'Brown'",
        "expected_clarification": None
    }
]

def run_benchmark(model_name: str):
    print(f"\n--- Running Benchmark for Model: {model_name} ---")
    
    pipeline = LocalQueryPipeline(db_path='finance.db', model_name=model_name)
    
    results = []
    
    for i, test in enumerate(TEST_QUERIES):
        print(f"\nQuery {i+1}: {test['query']}")
        
        start_time = time.time()
        # memory before
        mem_before = psutil.virtual_memory().used
        
        result = pipeline.process_query(test['query'])
        
        end_time = time.time()
        # memory after
        mem_after = psutil.virtual_memory().used
        
        latency = end_time - start_time
        mem_delta = max(0, mem_after - mem_before) / (1024 * 1024) # MB
        
        # Check correctness
        correct = False
        if test['expected_clarification']:
            correct = (result['status'] == 'needs_clarification' and result['clarification_question'] == test['expected_clarification'])
        else:
            # simple exact match or lowercase match
            if result['status'] == 'success' and result['sql']:
                gen_sql = result['sql'].lower().replace(";", "").strip()
                exp_sql = test['expected_sql'].lower().replace(";", "").strip()
                correct = (gen_sql == exp_sql)
                
        print(f"Latency: {latency:.2f}s | Mem Delta: {mem_delta:.2f} MB | Correct: {correct}")
        
        results.append({
            "latency": latency,
            "correct": correct
        })
        
    # Summary
    total_correct = sum(1 for r in results if r['correct'])
    avg_latency = sum(r['latency'] for r in results) / len(results)
    
    print("\n--- Summary ---")
    print(f"Accuracy: {total_correct}/{len(TEST_QUERIES)} ({total_correct/len(TEST_QUERIES)*100:.1f}%)")
    print(f"Average Latency: {avg_latency:.2f}s")
    
if __name__ == "__main__":
    setup_db()
    
    # Run for configured models
    models = ["qwen2.5-coder:3b"] # can add qwen2.5-coder:7b and llama3.2:3b if downloaded
    for model in models:
        run_benchmark(model)
