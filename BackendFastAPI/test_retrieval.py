import asyncio
from app.services.chat import _dense_search, _sparse_search, _expand_sparse_query
from app.services.workspaces import list_workspaces
from app.utils.vector import to_pgvector
from app.services.ai import AIService
from app.core.config import settings

QUERY = "Summarize the three Problem Statements listed under SDG 11 in Section 4."

async def run_test():
    workspaces = list_workspaces()
    if not workspaces:
        print("No workspaces found!")
        return
        
    WORKSPACE_ID = workspaces[0]['id']
    print(f"Testing Query: {QUERY}\n")
    
    ai = AIService()
    
    # 1. Embed the query
    vector = await ai.embed([QUERY])
    pg_vec = to_pgvector(vector[0], settings.EMBEDDING_DIMENSION)
    
    # 2. Run Dense Search
    dense_results = _dense_search(WORKSPACE_ID, pg_vec, top_k=5)
    
    # 3. Run Sparse Search (Full Text Search)
    expanded = _expand_sparse_query(QUERY)
    sparse_results = _sparse_search(WORKSPACE_ID, QUERY, expanded, top_k=5)
    
    print("--- TOP 5 DENSE RESULTS (Semantic) ---")
    for r in dense_results:
        print(f"Page {r['page_number']} | Score: {r['dense_score']:.3f} | Snippet: {r['context_snippet'][:80]}...")
        
    print("\n--- TOP 5 SPARSE RESULTS (Keyword/BM25) ---")
    for r in sparse_results:
        print(f"Page {r['page_number']} | Score: {r['sparse_score']:.3f} | Snippet: {r['context_snippet'][:80]}...")

if __name__ == "__main__":
    asyncio.run(run_test())