"""
Cloud-compatible RAG Enhancement API for Landscaping Design.
Uses Qdrant's scroll/filter instead of fastembed embeddings for cloud deployment.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import os
from dotenv import load_dotenv
import logging
import traceback

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try fastembed first, fall back to keyword search
USE_EMBEDDINGS = False
try:
    from fastembed import TextEmbedding
    text_model = TextEmbedding(model_name="Qdrant/clip-ViT-B-32-text")
    USE_EMBEDDINGS = True
    logger.info("✅ Fastembed loaded - using semantic search")
except Exception as e:
    logger.warning(f"⚠️ Fastembed not available ({e}) - using keyword search fallback")
    text_model = None

from qdrant_client import QdrantClient
from qdrant_client.http import models

# Initialize Qdrant (general collection for materials/hardscape if needed)
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "freepik_landscaping")
PLANT_COLLECTION = os.getenv("PLANT_COLLECTION", "autoscape-plants")

qdrant_client = None
plant_catalog = None

if QDRANT_URL and QDRANT_API_KEY:
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        logger.info(f"✅ Connected to Qdrant (general): {COLLECTION_NAME}")
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")

# Dedicated plants (independent collection, preferred for plantPalette)
try:
    from plant_catalog import PlantCatalog
    plant_catalog = PlantCatalog()
    logger.info(f"✅ Dedicated plants catalog ready: {PLANT_COLLECTION}")
except Exception as e:
    logger.warning(f"⚠️ Could not load dedicated PlantCatalog (will fallback): {e}")

app = FastAPI(title="RAG Enhancement API (Cloud)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DesignItem(BaseModel):
    name: str
    quantity: Union[int, float, str] = 1
    description: Optional[str] = None


class EnhancementRequest(BaseModel):
    plants: List[DesignItem] = []
    hardscape: List[DesignItem] = []
    features: List[DesignItem] = []
    structures: List[DesignItem] = []
    furniture: List[DesignItem] = []
    labor: List[DesignItem] = []  # now supported with structured lookup from components collection


def search_by_keyword(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search Qdrant using keyword matching on payload fields."""
    if not qdrant_client:
        return []
    
    try:
        # Use scroll with keyword filter on specific_name or title
        keywords = query.lower().split()
        
        # Search using scroll and filter results locally
        all_points, _ = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=500,  # Get a batch
            with_payload=True,
            with_vectors=False
        )
        
        # Score each point based on keyword matches
        scored_results = []
        for point in all_points:
            payload = point.payload or {}
            searchable_text = f"{payload.get('specific_name', '')} {payload.get('title', '')} {payload.get('description', '')}".lower()
            
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in searchable_text)
            if matches > 0:
                scored_results.append({
                    "score": matches / len(keywords),
                    "specific_name": payload.get("specific_name"),
                    "title": payload.get("title"),
                    "image_url": payload.get("image_url"),
                    "price_estimate": payload.get("price_estimate"),
                    "description": payload.get("description"),
                    **payload
                })
        
        # Sort by score and return top_k
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


def search_by_embedding(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search Qdrant using fastembed embeddings."""
    if not qdrant_client or not text_model:
        return []
    
    try:
        # Generate query embedding
        embeddings = list(text_model.embed([query]))
        query_vector = embeddings[0].tolist()
        
        # Search
        search_results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k
        ).points
        
        results = []
        for hit in search_results:
            results.append({
                "score": hit.score,
                "specific_name": hit.payload.get("specific_name"),
                "title": hit.payload.get("title"),
                "image_url": hit.payload.get("image_url"),
                "price_estimate": hit.payload.get("price_estimate"),
                "description": hit.payload.get("description"),
                **hit.payload
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Embedding search failed: {e}")
        return []


def search_plants(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search for plants. Prefer the dedicated independent plants collection when available."""
    if plant_catalog:
        try:
            results = plant_catalog.find_plant(query, top_k=top_k)
            # Normalize a bit for the enhancement response shape
            normalized = []
            for r in results:
                normalized.append({
                    "specific_name": r.get("specific_name") or r.get("common_name"),
                    "title": r.get("common_name"),
                    "image_url": r.get("image_url"),
                    "price_estimate": r.get("price_estimate") or r.get("price_range"),
                    "description": r.get("description"),
                    "category": r.get("category"),
                    **{k: v for k, v in r.items() if k not in ("score",)}
                })
            return normalized
        except Exception as e:
            logger.warning(f"Dedicated plant search failed, falling back: {e}")

    # Fallback to old general-collection search
    if USE_EMBEDDINGS:
        return search_by_embedding(query, top_k)
    return search_by_keyword(query, top_k)


@app.post("/api/enhance-with-rag")
async def enhance_with_rag(request: EnhancementRequest):
    """Enhance a design with RAG data."""
    if not qdrant_client:
        raise HTTPException(status_code=500, detail="Qdrant not connected")
    
    try:
        plant_palette = []
        hardscape_enriched = []
        
        def _enrich_item(item: DesignItem, preferred_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
            """Enrich a single item (plant or hardscape) using the components catalog when available."""
            results = []
            if plant_catalog and preferred_type:
                try:
                    results = plant_catalog.find_component(item.name, component_type=preferred_type, top_k=1)
                except Exception:
                    results = []
            if not results:
                # fall back to the general search_plants (which itself prefers dedicated now)
                results = search_plants(item.name, top_k=1)

            if not results:
                return None

            comp = results[0]

            qty = 1
            if isinstance(item.quantity, (int, float)):
                qty = int(item.quantity)
            elif isinstance(item.quantity, str) and item.quantity.isdigit():
                qty = int(item.quantity)

            unit_price = comp.get('price_estimate') or comp.get('price_range') or '$25'
            try:
                price_num = float(str(unit_price).replace('$', '').replace(',', '').split()[0])
                total = price_num * qty
                total_estimate = f'${total:.0f}'
            except Exception:
                total_estimate = f'{unit_price} x{qty}'

            return {
                "common_name": comp.get('specific_name') or comp.get('title') or comp.get('common_name') or item.name,
                "botanical_name": comp.get('botanical_name', ''),
                "image_url": comp.get('image_url', ''),
                "quantity": qty,
                "size": item.description or ("5-gallon" if preferred_type == "plant" else "standard"),
                "unit_price": unit_price,
                "total_estimate": total_estimate,
                "rag_verified": True,
                "original_name": item.name,
                "description": comp.get('description', ''),
                "component_type": comp.get('component_type') or preferred_type or "unknown",
                "category": comp.get('category', ''),
                "unit": comp.get('unit', ''),
            }

        # Plants (for the visual PlantPalette)
        for plant_item in request.plants:
            enriched = _enrich_item(plant_item, preferred_type="plant")
            if enriched:
                plant_palette.append(enriched)

        # Hardscape + other components (for budget line items)
        for hs_item in request.hardscape:
            enriched = _enrich_item(hs_item, preferred_type="hardscape")
            if enriched:
                hardscape_enriched.append(enriched)

        # We could do the same for features/structures/furniture if they have repeatable pricing
        for feat in request.features:
            enriched = _enrich_item(feat)
            if enriched:
                hardscape_enriched.append(enriched)

        # Labor - now backed by the same structured components collection
        labor_enriched = []
        for labor_item in request.labor:
            enriched = _enrich_item(labor_item, preferred_type="labor")
            if enriched:
                labor_enriched.append(enriched)

        return {
            "success": True,
            "plantPalette": plant_palette,
            "hardscape": hardscape_enriched,   # enriched hardscape + features for budget
            "labor": labor_enriched,          # structured labor (site prep, installation, cleanup, etc.)
            "rag_enhanced": True,
            "search_method": "dedicated_components" if plant_catalog else ("semantic" if USE_EMBEDDINGS else "keyword"),
            "components_collection": PLANT_COLLECTION if plant_catalog else COLLECTION_NAME,
        }
    
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "rag_available": qdrant_client is not None,
        "components_catalog_available": plant_catalog is not None,
        "components_collection": PLANT_COLLECTION,
        "general_collection": COLLECTION_NAME,
        "supported_types": ["plant", "hardscape", "material", "labor"],
        "search_method": "dedicated_components" if plant_catalog else ("semantic" if USE_EMBEDDINGS else "keyword"),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting RAG Enhancement API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
