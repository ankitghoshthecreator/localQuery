import ollama
from typing import List
import re

class LocalLLMClient:
    def __init__(self, model_name: str = "qwen2.5-coder:3b"):
        self.model_name = model_name

    def generate_sql(self, question: str, schema_context: List[str]) -> str:
        """
        Generates SQL based on the user's question and retrieved schema context.
        """
        context_str = "\n".join(schema_context)
        
        prompt = f"""You are an expert SQL assistant.
        
Given the following database schema context, write a valid SQLite query to answer the user's question.
Return ONLY the raw SQL query. Do not include markdown formatting like ```sql or any explanations.

Schema Context:
{context_str}

User Question: {question}
SQL Query:"""

        try:
            response = ollama.generate(model=self.model_name, prompt=prompt)
            sql = response.get("response", "").strip()
            
            # Clean up markdown if the model hallucinated it anyway
            sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'```\s*$', '', sql)
            return sql.strip()
            
        except Exception as e:
            # Handle model not found or server down
            return f"Error connecting to Ollama: {str(e)}"
