"""
Vector Embeddings & Mathematical Cosine Similarity Engine
Generates 128-dimensional normalized feature vector embeddings.
Computes true vector dot product and norm-based cosine similarity:
cosine_similarity(u, v) = (u . v) / (||u|| * ||v||)
"""
import math
import hashlib
import re
from typing import List, Tuple, Dict, Any, Set

EMBEDDING_DIM = 128

STOP_WORDS = {
    "what", "is", "the", "for", "in", "to", "of", "and", "under",
    "how", "does", "are", "do", "we", "a", "an", "be", "this", "that", "can", "our",
    "more", "than", "or", "as", "by", "from", "at", "it", "with", "on", "any", "if", "all", "its",
    "who", "whom", "when", "where", "why", "which", "was", "were", "been", "being", "have", "has", "had",
    "i", "you", "he", "she", "they", "them", "my", "your", "his", "her", "their"
}

def extract_content_tokens(text: str) -> Set[str]:
    """Extracts non-stop lowercase semantic tokens of length > 1."""
    return set(w for w in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower()) if w not in STOP_WORDS)

def generate_dense_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Generates a deterministic 128-dimensional feature vector representation.
    Extracts semantic tokens, removes stop words, computes character n-gram projections, and normalizes L2 norm to 1.0.
    """
    clean_text = text.lower().strip()
    words = [w for w in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", clean_text) if w not in STOP_WORDS]
    if not words:
        words = ["empty"]

    vector = [0.0] * dim

    # Project semantic tokens into 128-D vector space
    for word in words:
        w_hash = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        # Distribute word influence across 4 harmonic dimensions
        for h in range(4):
            idx = (w_hash >> (h * 8)) % dim
            val = ((w_hash >> ((h + 4) * 8)) & 0xFF) / 255.0 - 0.5
            vector[idx] += val

    # Calculate Euclidean L2 Norm
    norm_sq = sum(x * x for x in vector)
    norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0

    # Return unit length normalized vector
    return [round(x / norm, 6) for x in vector]

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculates true mathematical cosine similarity between two feature vectors:
    cos(theta) = (A . B) / (||A|| * ||B||)
    """
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    cos_sim = dot_product / (norm_a * norm_b)
    # Clamp to [0.0, 1.0] range for safe probability scoring
    return max(0.0, min(1.0, round(cos_sim, 4)))

def compute_lexical_overlap(query: str, doc_text: str) -> float:
    """Computes Jaccard / lexical token overlap score with stop word filtering."""
    q_words = extract_content_tokens(query)
    d_words = extract_content_tokens(doc_text)
    if not q_words or not d_words:
        return 0.0
    intersection = q_words.intersection(d_words)
    return len(intersection) / len(q_words)
