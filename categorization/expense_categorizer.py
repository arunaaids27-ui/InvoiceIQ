from typing import List, Dict, Any
import streamlit as st
from categorization.taxonomy import EXPENSE_TAXONOMY


@st.cache_resource(show_spinner=False)
def get_semantic_engine():
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    categories = []
    descriptions = []

    if isinstance(EXPENSE_TAXONOMY, list):
        for item in EXPENSE_TAXONOMY:
            cat_name = item.get("category") or item.get("name") or "General"
            desc = item.get("description", "")
            examples = item.get("examples", [])
            ex_str = ", ".join(examples) if isinstance(examples, list) else str(examples)
            categories.append(cat_name)
            descriptions.append(f"{cat_name}: {desc} Examples: {ex_str}")
    elif isinstance(EXPENSE_TAXONOMY, dict):
        for cat_name, details in EXPENSE_TAXONOMY.items():
            categories.append(cat_name)
            if isinstance(details, dict):
                desc = details.get("description", "")
                examples = details.get("examples", [])
                ex_str = ", ".join(examples) if isinstance(examples, list) else str(examples)
                descriptions.append(f"{cat_name}: {desc} Examples: {ex_str}")
            else:
                descriptions.append(f"{cat_name}: {str(details)}")
    
    taxonomy_embeddings = model.encode(descriptions)
    return model, categories, taxonomy_embeddings, cosine_similarity


def categorize_invoice_items(line_items: List[Dict[str, Any]], vendor_name: str = "") -> List[Dict[str, Any]]:
    if not line_items:
        return []

    model, categories, taxonomy_embeddings, cosine_similarity = get_semantic_engine()

    item_texts = []
    for item in line_items:
        desc = item.get("description", "")
        context = f"Vendor: {vendor_name} | Item: {desc}" if vendor_name else desc
        item_texts.append(context)

    item_embeddings = model.encode(item_texts)
    similarities = cosine_similarity(item_embeddings, taxonomy_embeddings)

    categorized_items = []
    for idx, item in enumerate(line_items):
        item_copy = dict(item)
        sim_scores = similarities[idx]
        
        ranked_indices = sim_scores.argsort()[::-1][:3]
        top_matches = []
        for r_idx in ranked_indices:
            top_matches.append({
                "category": categories[r_idx],
                "score": round(float(sim_scores[r_idx]) * 100, 1)
            })
            
        best_match = top_matches[0]
        item_copy["assigned_category"] = best_match["category"]
        item_copy["category_confidence"] = best_match["score"]
        item_copy["rag_top_matches"] = top_matches
        categorized_items.append(item_copy)

    return categorized_items