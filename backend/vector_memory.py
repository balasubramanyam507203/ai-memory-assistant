import numpy as np
import faiss
from typing import List, Dict, Any, Tuple

from db import load_long_memories_with_embeddings

def search_long_memories(session_id: str, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
    ids, texts, embs = load_long_memories_with_embeddings(session_id=session_id)

    if len(ids) == 0:
        return []
    
    # Convert to float32 numpy arrays for FAISS
    X = np.array(embs, dtype="float32")
    q = np.array([query_embedding], dtype="float32")

    dim = X.shape[1]
    index = faiss.IndexFlatIP(dim)  #inner product
    #Normalise for cosine-like Similarity
    faiss.normalize_L2(X)
    faiss.normalize_L2(q)

    index.add(X)
    scores, neighbors = index.search(q, min(k, len(ids)))

    results = []
    for score, idx in zip(scores[0], neighbors[0]):
        if idx == -1:
            continue
        results.append({
            "id": ids[idx],
            "text": texts[idx],
            "score": float(score),
        })
    
    return results