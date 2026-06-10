"""
Dedicated Plant Catalog for AutoScape (root copy for local tools)
===============================================================
Independent plant entity collection. Same implementation as servers/plant_catalog.py.
See servers/plant_catalog.py for full docs and schema.
"""

import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = (
    os.getenv("COMPONENTS_COLLECTION")
    or os.getenv("PLANT_COLLECTION")
    or "autoscape-components"
)
EMBED_MODEL = "Qdrant/clip-ViT-B-32-text"

SEED_COMPONENTS: List[Dict[str, Any]] = [
    {"component_type": "plant", "common_name": "Japanese Maple", "botanical_name": "Acer palmatum", "category": "tree",
     "description": "Elegant small deciduous tree prized for delicate foliage and spectacular fall color.",
     "tags": ["ornamental tree", "fall color", "shade tolerant"], "hardiness_zones": ["5","6","7","8","9"],
     "sun": "partial shade to full sun", "water": "moderate", "mature_size": "15-25 ft",
     "unit": "each", "image_url": "", "price_range": "$65 - $95 (5-gallon)"},
    {"component_type": "plant", "common_name": "Lavender", "botanical_name": "Lavandula angustifolia", "category": "perennial",
     "description": "Fragrant purple flower spikes, extremely drought tolerant.",
     "tags": ["fragrant", "drought tolerant", "full sun"], "hardiness_zones": ["5","6","7","8","9"],
     "sun": "full sun", "water": "low", "mature_size": "1-3 ft",
     "unit": "each", "image_url": "", "price_range": "$10 - $16 (1-gallon)"},
    {"component_type": "plant", "common_name": "Blue Fescue Grass", "botanical_name": "Festuca glauca", "category": "grass",
     "description": "Striking blue-silver ornamental grass forming tight clumps.",
     "tags": ["ornamental grass", "blue foliage", "drought tolerant"], "hardiness_zones": ["4","5","6","7","8"],
     "sun": "full sun to partial shade", "water": "low to moderate", "mature_size": "6-10 in clumps",
     "unit": "each", "image_url": "", "price_range": "$5 - $8 (4-inch pot)"},
    {"component_type": "plant", "common_name": "Boxwood", "botanical_name": "Buxus sempervirens", "category": "shrub",
     "description": "Dense evergreen classic for formal hedges and topiary.",
     "tags": ["evergreen shrub", "hedge", "formal"], "hardiness_zones": ["5","6","7","8"],
     "sun": "full sun to partial shade", "water": "moderate", "mature_size": "3-10 ft (pruned)",
     "unit": "each", "image_url": "", "price_range": "$25 - $45 (5-gallon)"},
    # Hardscape examples (same as servers version)
    {"component_type": "hardscape", "common_name": "Concrete Pavers", "botanical_name": "", "category": "paver",
     "description": "Precast concrete pavers for patios and walkways.",
     "tags": ["patio", "walkway"], "unit": "sq ft", "image_url": "", "price_range": "$5 - $10 per sq ft"},
    {"component_type": "hardscape", "common_name": "Pea Gravel", "botanical_name": "", "category": "gravel",
     "description": "Small rounded decorative gravel for pathways.",
     "tags": ["pathway", "drainage"], "unit": "cubic yard", "image_url": "", "price_range": "$40 - $60 per cubic yard"},

    # Labor examples for root copy
    {"component_type": "labor", "common_name": "Site Preparation & Demolition", "botanical_name": "", "category": "site_prep",
     "description": "Removal of existing lawn, debris, haul away.",
     "tags": ["demolition", "prep"], "unit": "per sq ft", "image_url": "", "price_range": "$2 - $5 per sq ft"},
    {"component_type": "labor", "common_name": "Plant Installation Labor", "botanical_name": "", "category": "planting",
     "description": "Professional planting of trees, shrubs, perennials.",
     "tags": ["planting", "install"], "unit": "per plant", "image_url": "", "price_range": "$15 - $35 per 5-gal"},
    {"component_type": "labor", "common_name": "Hardscape Installation", "botanical_name": "", "category": "hardscape_install",
     "description": "Labor to install pavers, gravel, walls etc.",
     "tags": ["install", "pavers"], "unit": "per sq ft", "image_url": "", "price_range": "$8 - $18 per sq ft installed"},
]


class PlantCatalog:
    """Dedicated catalog for plant entities (independent collection)."""

    def __init__(self):
        load_dotenv()
        self._load_clients()
        self._ensure_collection()
        logger.info(f"✅ PlantCatalog (dedicated) ready: {COLLECTION_NAME}")

    def _load_clients(self):
        url = os.getenv("QDRANT_URL") or os.getenv("VITE_QUADRANT_ENDPOINT")
        api_key = os.getenv("QDRANT_API_KEY") or os.getenv("VITE_QUADRANT_API_KEY")
        if not url or not api_key:
            raise ValueError("Missing QDRANT credentials")
        self.client = QdrantClient(url=url, api_key=api_key)
        self.embedder = TextEmbedding(model_name=EMBED_MODEL)
        probe = list(self.embedder.embed(["probe"]))[0]
        self.vector_size = len(probe)

    def _ensure_collection(self):
        if not self.client.collection_exists(COLLECTION_NAME):
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
            )
            logger.info(f"✨ Created {COLLECTION_NAME}")
        else:
            logger.info(f"ℹ️ Using {COLLECTION_NAME}")

        # Payload indexes for component_type / category filtering (plants vs hardscape etc.)
        try:
            self.client.create_payload_index(collection_name=COLLECTION_NAME, field_name="component_type", field_schema=models.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(collection_name=COLLECTION_NAME, field_name="category", field_schema=models.PayloadSchemaType.KEYWORD)
        except Exception:
            pass

    def _embed(self, text: str) -> List[float]:
        return list(self.embedder.embed([text]))[0].tolist()

    def _build_search_text(self, p: Dict[str, Any]) -> str:
        parts = [p.get("common_name",""), p.get("botanical_name",""), p.get("description",""), " ".join(p.get("tags",[]))]
        return " ".join(str(x) for x in parts if x).strip()

    def _to_entry(self, payload: Dict[str, Any], score: float = 0.0) -> Dict[str, Any]:
        common = payload.get("common_name") or "Unknown Item"
        botanical = payload.get("botanical_name", "")
        specific = f"{common} ({botanical})" if botanical else common
        return {
            "common_name": common,
            "botanical_name": botanical,
            "specific_name": specific,
            "image_url": payload.get("image_url", ""),
            "score": float(score) if score else 0.0,
            "tags": payload.get("tags", []),
            "price_estimate": payload.get("price_range", ""),
            "description": payload.get("description", ""),
            "category": payload.get("category", ""),
            "hardiness_zones": payload.get("hardiness_zones", []),
            "sun": payload.get("sun", ""),
            "water": payload.get("water", ""),
            "mature_size": payload.get("mature_size", ""),
            "component_type": payload.get("component_type", "plant"),
            "unit": payload.get("unit", ""),
            "price_range": payload.get("price_range", ""),
        }

    def find_component(self, name: str, component_type: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        if not name: return []
        qvec = self._embed(name)
        qf = None
        if component_type:
            qf = models.Filter(must=[models.FieldCondition(key="component_type", match=models.MatchValue(value=component_type))])
        hits = self.client.query_points(collection_name=COLLECTION_NAME, query=qvec, query_filter=qf, limit=top_k).points
        return [self._to_entry(h.payload or {}, h.score) for h in hits]

    def find_plant(self, plant_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self.find_component(plant_name, component_type="plant", top_k=top_k)

    def find_plants_batch(self, plant_names: List[str], top_k: int = 2) -> Dict[str, List[Dict]]:
        return {name: self.find_plant(name, top_k=top_k) for name in plant_names}

    def find_by_category(self, category: str, top_k: int = 10) -> List[Dict[str, Any]]:
        hints = {"trees":"ornamental tree", "shrubs":"flowering shrub", "perennials":"flowering perennial", "grasses":"ornamental grass", "paver":"concrete paver", "gravel":"pea gravel"}
        ctype = "plant" if category.lower() in ("trees","shrubs","perennials","grasses") else None
        return self.find_component(hints.get(category.lower(), category), component_type=ctype, top_k=top_k)

    def get_plant_details(self, botanical_name: str) -> Optional[Dict[str, Any]]:
        r = self.find_plant(botanical_name, top_k=1)
        return r[0] if r else None

    def upsert_plants(self, plants: List[Dict[str, Any]]) -> int:
        pts = []
        for p in plants:
            txt = self._build_search_text(p)
            if not txt: continue
            pts.append(models.PointStruct(id=str(uuid.uuid4()), vector=self._embed(txt), payload=p))
        if pts:
            self.client.upsert(collection_name=COLLECTION_NAME, points=pts)
        return len(pts)

    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return {"collection": COLLECTION_NAME, "points": info.points_count, "status": "healthy"}
        except Exception as e:
            return {"collection": COLLECTION_NAME, "status": "error", "error": str(e)}


def create_plant_palette(design_plants: List[str]) -> Dict[str, Any]:
    catalog = PlantCatalog()
    palette = {"plants": [], "total_count": len(design_plants)}
    for name in design_plants:
        m = catalog.find_plant(name, top_k=1)
        if m:
            palette["plants"].append({"requested_name": name, "matched_plant": m[0], "confidence": m[0].get("score", 0)})
    return palette


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()

    cat = PlantCatalog()
    if a.seed:
        n = cat.upsert_plants(SEED_COMPONENTS)
        print(f"Seeded {n} components (plants + hardscape) into {COLLECTION_NAME}")
    if a.stats or not any([a.seed, a.test]):
        print(cat.get_collection_stats())
    if a.test or not any([a.seed, a.stats]):
        print("Test Japanese Maple (plant):", [p["specific_name"] for p in cat.find_plant("Japanese Maple", 2)])
        print("Test pavers (hardscape):", [p["specific_name"] for p in cat.find_component("pavers", component_type="hardscape", top_k=2)])
        print("Test category paver:", [p["specific_name"] for p in cat.find_by_category("paver", 2)])
