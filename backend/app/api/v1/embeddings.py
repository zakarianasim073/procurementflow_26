"""
Tender Embedding and Semantic Search API Router.
Contains /api/embeddings/* endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.post("/embeddings/index")
async def index_tenders_for_search(req: Dict[str, Any]):
    """Index tenders for semantic search using Ollama embeddings."""
    from app.services.tender_embedding import tender_embedding_service
    tenders = req.get("tenders", [])
    count = await tender_embedding_service.index_tenders(tenders)
    return {"success": True, "indexed": count}


@router.post("/embeddings/search")
async def search_tenders_semantic(req: Dict[str, Any]):
    """Semantic search for tenders using Ollama (nomic-embed-text)."""
    from app.services.tender_embedding import tender_embedding_service
    query = req.get("query", "")
    top_k = req.get("top_k", 10)
    if not query:
        return {"success": False, "message": "Query required", "results": []}
    results = await tender_embedding_service.search(query, top_k=top_k)
    return {"success": True, "query": query, "results": results}


@router.post("/embeddings/similar")
async def find_similar_tenders(req: Dict[str, str]):
    """Find tenders similar to a given tender by ID."""
    from app.services.tender_embedding import tender_embedding_service
    tender_id = req.get("tender_id", "")
    if not tender_id:
        return {"success": False, "message": "tender_id required", "results": []}
    results = await tender_embedding_service.find_similar(tender_id)
    return {"success": True, "tender_id": tender_id, "results": results}


@router.get("/embeddings/stats")
async def get_embedding_stats():
    """Get embedding index statistics."""
    try:
        from app.services.tender_embedding import tender_embedding_service

        stats = tender_embedding_service.get_stats()
        return {"success": True, "available": True, **stats}
    except Exception as exc:
        return {
            "success": True,
            "available": False,
            "reason": str(exc),
            "total_indexed": 0,
        }
