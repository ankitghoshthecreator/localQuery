from typing import Dict, Any

from localquery.clarification.engine import ClarificationEngine
from localquery.retrieval.retriever import HybridRetriever
from localquery.llm.client import LocalLLMClient
from localquery.db.executor import DBExecutor
from localquery.db.schema import get_schema_description

class LocalQueryPipeline:
    def __init__(self, model_name: str = "qwen2.5-coder:3b"):
        self.clarification_engine = ClarificationEngine()
        self.retriever = HybridRetriever()
        self.llm_client = LocalLLMClient(model_name=model_name)
        self.db_executor = DBExecutor()
        
        # Initialize and index the schema
        print("Initializing retriever index...")
        schema_docs = get_schema_description()
        self.retriever.index(schema_docs)
        print("Pipeline ready.")

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """
        Processes a user question through the full LocalQuery pipeline.
        Returns a dict containing the result state.
        """
        result = {
            "status": "success",
            "clarification_question": None,
            "sql": None,
            "data": None,
            "formatted_result": None,
            "error": None
        }
        
        try:
            # 1. Clarification Check
            clarification = self.clarification_engine.needs_clarification(user_question)
            if clarification:
                result["status"] = "needs_clarification"
                result["clarification_question"] = clarification
                return result
                
            # 2. Retrieval
            # Since our schema is small, we'll just retrieve the top 3 documents
            context = self.retriever.retrieve(user_question, top_k=3)
            
            # 3. LLM SQL Generation
            sql = self.llm_client.generate_sql(user_question, context)
            if sql.startswith("Error"):
                result["status"] = "error"
                result["error"] = sql
                return result
                
            result["sql"] = sql
            
            # 4. DB Execution
            db_result = self.db_executor.execute_query(sql)
            
            if db_result["error"]:
                result["status"] = "error"
                result["error"] = db_result["error"]
                return result
                
            result["data"] = db_result
            result["formatted_result"] = self.db_executor.format_results(db_result)
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            
        return result
