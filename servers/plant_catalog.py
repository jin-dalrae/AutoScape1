"""
Dedicated Landscaping Components Catalog for AutoScape
======================================================
This is the structured collection for **all** repeatable landscaping components
(plants + hardscape + materials). Independent from the big visual product image
collection used for generation/inspiration photos.

Workflow context (your 1-2-3):
1. Generate the ideal backyard image (pretty viz, using visual RAG + image gen).
2. Extract components from the design (plants, hardscape, features...).
3. Estimate budget: search this components collection by name to get accurate
   unit pricing, specs, and reference images → build line items + totals.

- Collection default: autoscape-components (override with COMPONENTS_COLLECTION or PLANT_COLLECTION)
- Rich structured payloads + semantic search (name + description + tags + category).
- Supports category/component_type filtering (plant vs hardscape etc.).
- Same shapes for PlantReference / budget, plus general component lookup.
- Seed / upsert here for maintainable, filterable pricing data (no reliance on scraped product metadata).

Payload schema (unified for plants + hardscape + materials):
{
  "component_type": "plant" | "hardscape" | "material",
  "common_name": "Japanese Maple" or "Concrete Pavers",
  "botanical_name": "Acer palmatum" (plants only),
  "category": "tree" | "paver" | "gravel" | "shrub" ...,
  "description": "...",
  "tags": [...],
  "hardiness_zones": [...] (plants),
  "sun": "...", "water": "...",
  "unit": "each" | "sq ft" | "cubic yard" | "linear ft",
  "price_range": "$65 - $95 (5-gallon)" or "$8 - $15 per sq ft",
  "image_url": "reference photo url (curated good shot for palette UI)"
}
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

# Configuration - dedicated components collection (plants + hardscape + materials)
# Prefer COMPONENTS_COLLECTION, fall back to old PLANT_COLLECTION name for compatibility.
COLLECTION_NAME = (
    os.getenv("COMPONENTS_COLLECTION")
    or os.getenv("PLANT_COLLECTION")
    or "autoscape-components"
)
EMBED_MODEL = "Qdrant/clip-ViT-B-32-text"


# Curated seed for plants + hardscape + common materials.
# This is the source of truth for realistic pricing + specs used in budget estimates.
# Add / update here as your pricing knowledge grows. Images are reference shots for the UI palettes.
SEED_COMPONENTS: List[Dict[str, Any]] = [
    # --- PLANTS (component_type: plant) ---
    {
        "component_type": "plant",
        "common_name": "Japanese Maple",
        "botanical_name": "Acer palmatum",
        "category": "tree",
        "description": "Elegant small deciduous tree prized for delicate foliage and spectacular fall color ranging from red to gold. Excellent specimen or understory tree.",
        "tags": ["ornamental tree", "fall color", "japanese garden", "shade tolerant", "container friendly"],
        "hardiness_zones": ["5", "6", "7", "8", "9"],
        "sun": "partial shade to full sun (afternoon shade in hot climates)",
        "water": "moderate, well-drained soil",
        "mature_size": "15-25 ft tall, 15-20 ft wide",
        "unit": "each",
        "image_url": "",
        "price_range": "$65 - $95 (5-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Lavender",
        "botanical_name": "Lavandula angustifolia",
        "category": "perennial",
        "description": "Classic Mediterranean evergreen subshrub with fragrant purple flower spikes. Extremely drought tolerant once established. Great for borders, pots, and pollinators.",
        "tags": ["fragrant", "drought tolerant", "pollinator", "herb", "low maintenance", "full sun"],
        "hardiness_zones": ["5", "6", "7", "8", "9"],
        "sun": "full sun",
        "water": "low once established",
        "mature_size": "1-3 ft tall and wide",
        "unit": "each",
        "image_url": "",
        "price_range": "$10 - $16 (1-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Blue Fescue Grass",
        "botanical_name": "Festuca glauca",
        "category": "grass",
        "description": "Compact cool-season ornamental grass with striking blue-silver foliage. Forms tight clumps. Excellent for modern designs, rock gardens, and edging.",
        "tags": ["ornamental grass", "blue foliage", "drought tolerant", "cool season", "low maintenance"],
        "hardiness_zones": ["4", "5", "6", "7", "8"],
        "sun": "full sun to partial shade",
        "water": "low to moderate",
        "mature_size": "6-10 in tall, 6-12 in wide clumps",
        "unit": "each",
        "image_url": "",
        "price_range": "$5 - $8 (4-inch pot)",
    },
    {
        "component_type": "plant",
        "common_name": "Boxwood",
        "botanical_name": "Buxus sempervirens",
        "category": "shrub",
        "description": "Dense evergreen shrub with small glossy leaves. Classic for formal hedges, topiary, and foundation plantings. Very tolerant of pruning.",
        "tags": ["evergreen shrub", "hedge", "formal", "shade tolerant", "topiary"],
        "hardiness_zones": ["5", "6", "7", "8"],
        "sun": "full sun to partial shade",
        "water": "moderate",
        "mature_size": "3-10 ft tall (pruned to desired height)",
        "unit": "each",
        "image_url": "",
        "price_range": "$25 - $45 (5-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Russian Sage",
        "botanical_name": "Salvia yangii",
        "category": "perennial",
        "description": "Airy perennial with silvery foliage and tall lavender-blue flower spikes in late summer. Extremely heat and drought tolerant. Pollinator magnet.",
        "tags": ["perennial", "drought tolerant", "silver foliage", "late summer bloom", "pollinator"],
        "hardiness_zones": ["4", "5", "6", "7", "8", "9"],
        "sun": "full sun",
        "water": "very low",
        "mature_size": "3-5 ft tall, 2-4 ft wide",
        "unit": "each",
        "image_url": "",
        "price_range": "$12 - $18 (1-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Maidenhair Tree (Ginkgo)",
        "botanical_name": "Ginkgo biloba",
        "category": "tree",
        "description": "Living fossil tree with unique fan-shaped leaves that turn brilliant golden yellow in fall. Extremely resilient, pollution tolerant, and long-lived.",
        "tags": ["shade tree", "fall color", "urban tolerant", "historic", "large tree"],
        "hardiness_zones": ["3", "4", "5", "6", "7", "8", "9"],
        "sun": "full sun",
        "water": "moderate",
        "mature_size": "50-80 ft tall, 30-40 ft wide (narrower cultivars available)",
        "unit": "each",
        "image_url": "",
        "price_range": "$80 - $150 (15-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Coral Bells",
        "botanical_name": "Heuchera",
        "category": "perennial",
        "description": "Mounding perennial grown primarily for stunning foliage in shades of purple, silver, chartreuse, and caramel. Delicate flower spikes in spring.",
        "tags": ["foliage plant", "shade garden", "perennial", "container", "colorful leaves"],
        "hardiness_zones": ["4", "5", "6", "7", "8", "9"],
        "sun": "partial shade to full shade (some sun tolerant)",
        "water": "moderate, well-drained",
        "mature_size": "6-12 in tall foliage, 12-18 in flower spikes",
        "unit": "each",
        "image_url": "",
        "price_range": "$10 - $15 (1-gallon)",
    },
    {
        "component_type": "plant",
        "common_name": "Little Bluestem",
        "botanical_name": "Schizachyrium scoparium",
        "category": "grass",
        "description": "Native prairie grass with blue-green summer foliage that turns coppery red-orange in fall. Fine texture, great movement in the wind. Very low maintenance.",
        "tags": ["native grass", "prairie", "fall color", "drought tolerant", "low maintenance"],
        "hardiness_zones": ["3", "4", "5", "6", "7", "8", "9"],
        "sun": "full sun",
        "water": "low",
        "mature_size": "2-4 ft tall, 1-2 ft wide",
        "unit": "each",
        "image_url": "",
        "price_range": "$8 - $14 (1-gallon)",
    },

    # --- HARDSCAPE & MATERIALS (component_type: hardscape or material) ---
    {
        "component_type": "hardscape",
        "common_name": "Concrete Pavers",
        "botanical_name": "",
        "category": "paver",
        "description": "Precast concrete pavers for patios, walkways, and driveways. Available in many shapes, colors, and textures. Relatively affordable and easy to install/replace.",
        "tags": ["patio", "walkway", "driveway", "durable", "low maintenance"],
        "unit": "sq ft",
        "image_url": "",
        "price_range": "$5 - $10 per sq ft (material only)",
    },
    {
        "component_type": "hardscape",
        "common_name": "Pea Gravel",
        "botanical_name": "",
        "category": "gravel",
        "description": "Small rounded decorative gravel, excellent for pathways, French drains, and mulch alternative in beds. Good drainage, soft underfoot.",
        "tags": ["pathway", "drainage", "mulch alternative", "decorative"],
        "unit": "cubic yard",
        "image_url": "",
        "price_range": "$40 - $60 per cubic yard",
    },
    {
        "component_type": "hardscape",
        "common_name": "Flagstone",
        "botanical_name": "",
        "category": "stone",
        "description": "Natural flat stone slabs for patios, stepping stones, and walkways. Irregular shapes create organic look. Requires good base preparation.",
        "tags": ["patio", "stepping stone", "natural stone", "premium"],
        "unit": "ton",
        "image_url": "",
        "price_range": "$300 - $600 per ton (covers ~100-150 sq ft depending on thickness)",
    },
    {
        "component_type": "material",
        "common_name": "Bark Mulch",
        "botanical_name": "",
        "category": "mulch",
        "description": "Organic wood chip or shredded bark mulch for beds and tree rings. Suppresses weeds, retains moisture, improves soil as it breaks down.",
        "tags": ["bed mulch", "weed suppression", "moisture retention", "organic"],
        "unit": "cubic yard",
        "image_url": "",
        "price_range": "$30 - $50 per cubic yard (bulk)",
    },
    {
        "component_type": "hardscape",
        "common_name": "Plastic Landscape Edging",
        "botanical_name": "",
        "category": "edging",
        "description": "Flexible black plastic edging to separate lawn from beds or contain gravel. Inexpensive and easy DIY. Also available in metal or stone for higher end look.",
        "tags": ["bed border", "lawn separation", "DIY friendly"],
        "unit": "linear ft",
        "image_url": "",
        "price_range": "$1 - $3 per linear foot (material)",
    },
    {
        "component_type": "hardscape",
        "common_name": "Segmental Retaining Wall Block",
        "botanical_name": "",
        "category": "retaining wall",
        "description": "Interlocking concrete blocks for low garden walls, raised beds, and terracing. No mortar required for most residential heights.",
        "tags": ["retaining wall", "raised bed", "terrace", "structural"],
        "unit": "sq ft face",
        "image_url": "",
        "price_range": "$15 - $25 per sq ft face (material + basic install guidance)",
    },

    # --- LABOR (component_type: labor) ---
    # These provide structured, queryable labor pricing instead of pure LLM 30-50% guesses.
    {
        "component_type": "labor",
        "common_name": "Site Preparation & Demolition",
        "botanical_name": "",
        "category": "site_prep",
        "description": "Removal of existing lawn, old materials, debris, and hauling away. Includes basic clearing for new work.",
        "tags": ["demolition", "clearing", "haul away", "prep"],
        "unit": "per sq ft",
        "image_url": "",
        "price_range": "$2 - $5 per sq ft",
    },
    {
        "component_type": "labor",
        "common_name": "Grading & Excavation",
        "botanical_name": "",
        "category": "grading",
        "description": "Rough grading, excavation for patios/walls/beds, slope correction, and soil import or export as needed for proper drainage and levels.",
        "tags": ["grading", "excavation", "drainage", "soil work"],
        "unit": "per sq ft",
        "image_url": "",
        "price_range": "$1.50 - $4 per sq ft",
    },
    {
        "component_type": "labor",
        "common_name": "Plant Installation Labor",
        "botanical_name": "",
        "category": "planting",
        "description": "Professional planting of trees, shrubs, perennials, and grasses including hole prep, backfill, staking larger trees, and initial watering.",
        "tags": ["planting", "installation", "trees", "shrubs"],
        "unit": "per plant",
        "image_url": "",
        "price_range": "$15 - $35 per typical 5-gal plant; $75-150 for 15-gal trees",
    },
    {
        "component_type": "labor",
        "common_name": "Hardscape Installation",
        "botanical_name": "",
        "category": "hardscape_install",
        "description": "Full installation labor for pavers, gravel paths, flagstone, edging, and low retaining walls. Includes base prep, compaction, and jointing.",
        "tags": ["pavers", "patio", "walkway", "installation"],
        "unit": "per sq ft",
        "image_url": "",
        "price_range": "$8 - $18 per sq ft installed (varies by material complexity)",
    },
    {
        "component_type": "labor",
        "common_name": "Irrigation & Drainage Install",
        "botanical_name": "",
        "category": "irrigation",
        "description": "Installation of drip irrigation, spray heads, valves, controller, and basic drainage solutions (French drains, etc.).",
        "tags": ["irrigation", "drip", "drainage", "water management"],
        "unit": "per sq ft or lump sum",
        "image_url": "",
        "price_range": "$1.50 - $3.50 per sq ft or $800-2000 for typical controller + zones",
    },
    {
        "component_type": "labor",
        "common_name": "Final Cleanup & Finish Grade",
        "botanical_name": "",
        "category": "cleanup",
        "description": "Final raking, mulch application touch-up, debris haul, and light final grading after all other work.",
        "tags": ["cleanup", "final grade", "haul", "touch up"],
        "unit": "per sq ft or lump sum",
        "image_url": "",
        "price_range": "$0.75 - $2 per sq ft or $250-600 small project",
    },
    {
        "component_type": "labor",
        "common_name": "Project Management & Permits",
        "botanical_name": "",
        "category": "project_management",
        "description": "Coordination, scheduling, supervision, permit pulling, and inspections. Often 8-15% of total project or fixed fee.",
        "tags": ["management", "permits", "supervision", "overhead"],
        "unit": "percent or lump sum",
        "image_url": "",
        "price_range": "8-15% of materials+install or $400-1200 typical residential",
    },
]


class PlantCatalog:
    """
    Dedicated catalog for landscaping components (plants + hardscape + materials).
    Backwards compatible: find_plant(...) still works and defaults to plant type.
    Use find_component(name, component_type="hardscape") for other items.
    """

    def __init__(self):
        load_dotenv()
        self._load_clients()
        self._ensure_collection()
        logger.info(f"✅ ComponentCatalog (PlantCatalog facade) ready on {COLLECTION_NAME}")

    def _load_clients(self):
        url = os.getenv("QDRANT_URL") or os.getenv("VITE_QUADRANT_ENDPOINT")
        api_key = os.getenv("QDRANT_API_KEY") or os.getenv("VITE_QUADRANT_API_KEY")
        if not url or not api_key:
            raise ValueError("Missing QDRANT credentials (QDRANT_URL / QDRANT_API_KEY)")

        self.client = QdrantClient(url=url, api_key=api_key)

        logger.info("🧠 Loading text embedding model for plants...")
        self.embedder = TextEmbedding(model_name=EMBED_MODEL)
        probe = list(self.embedder.embed(["probe"]))[0]
        self.vector_size = len(probe)
        logger.info(f"   Vector size: {self.vector_size}")

    def _ensure_collection(self):
        if not self.client.collection_exists(COLLECTION_NAME):
            logger.info(f"✨ Creating dedicated components collection '{COLLECTION_NAME}'...")
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("✅ Collection created.")
        else:
            logger.info(f"ℹ️  Using existing components collection '{COLLECTION_NAME}'")

        # Ensure we can filter efficiently on component_type (and category) for plants vs hardscape etc.
        try:
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="component_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Index may already exist or collection may be old; non-fatal
            pass

    def _embed(self, text: str) -> List[float]:
        emb = list(self.embedder.embed([text]))[0]
        return emb.tolist()

    def _build_search_text(self, p: Dict[str, Any]) -> str:
        parts = [
            p.get("common_name", ""),
            p.get("botanical_name", ""),
            p.get("description", ""),
            " ".join(p.get("tags", [])),
            p.get("category", ""),
        ]
        return " ".join([str(x) for x in parts if x]).strip()

    def _to_entry(self, payload: Dict[str, Any], score: float = 0.0) -> Dict[str, Any]:
        """Normalize to the shape expected by budget_calculator_rag + PlantReference UI.
        Also preserves component_type, unit, price_range for labor/hardscape etc.
        """
        common = payload.get("common_name") or payload.get("name", "Unknown Item")
        botanical = payload.get("botanical_name", "")
        specific = f"{common} ({botanical})" if botanical else common

        base = {
            "common_name": common,
            "botanical_name": botanical,
            "specific_name": specific,
            "image_url": payload.get("image_url", ""),
            "score": float(score) if score else 0.0,
            "tags": payload.get("tags", []),
            "original_title": payload.get("common_name", ""),
            "price_estimate": payload.get("price_range", payload.get("price_estimate", "")),
            "description": payload.get("description", ""),
            # Rich structured fields
            "category": payload.get("category", ""),
            "hardiness_zones": payload.get("hardiness_zones", []),
            "sun": payload.get("sun", ""),
            "water": payload.get("water", ""),
            "mature_size": payload.get("mature_size", ""),
            # New for full components (hardscape, labor, etc.)
            "component_type": payload.get("component_type", "plant"),
            "unit": payload.get("unit", ""),
            "price_range": payload.get("price_range", payload.get("price_estimate", "")),
        }
        # carry over any other useful payload
        for k in ("component_type", "unit", "price_range"):
            if k not in base and k in payload:
                base[k] = payload[k]
        return base

    # ------------------------------------------------------------------
    # Public query API (kept compatible with previous callers)
    # ------------------------------------------------------------------

    def find_component(
        self,
        name: str,
        component_type: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across the components collection.
        Optionally filter by component_type ("plant", "hardscape", "material").
        """
        logger.info(
            f"🔎 Searching components for: '{name}'"
            + (f" (type={component_type})" if component_type else "")
        )
        if not name:
            return []

        qvec = self._embed(name)

        query_filter = None
        if component_type:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="component_type",
                        match=models.MatchValue(value=component_type),
                    )
                ]
            )

        hits = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=qvec,
            query_filter=query_filter,
            limit=top_k,
        ).points

        results = [self._to_entry(h.payload or {}, h.score) for h in hits]
        logger.info(f"   Found {len(results)} matches")
        return results

    def find_plant(self, plant_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Convenience wrapper for plants (component_type='plant')."""
        return self.find_component(plant_name, component_type="plant", top_k=top_k)

    def find_plants_batch(self, plant_names: List[str], top_k: int = 2) -> Dict[str, List[Dict]]:
        """Batch lookup."""
        logger.info(f"🌱 Batch lookup for {len(plant_names)} plants...")
        out: Dict[str, List[Dict]] = {}
        for name in plant_names:
            out[name] = self.find_plant(name, top_k=top_k)
        return out

    def find_by_category(self, category: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Category search within plants by default (tree, shrub, paver, gravel, etc.).
        You can also pass a component_type hint if needed.
        """
        logger.info(f"🔎 Category search: {category}")
        hints = {
            "tree": "ornamental shade tree",
            "trees": "ornamental shade tree",
            "shrub": "flowering evergreen shrub hedge",
            "shrubs": "flowering evergreen shrub hedge",
            "perennial": "flowering perennial",
            "perennials": "flowering perennial",
            "grass": "ornamental grass",
            "grasses": "ornamental grass",
            "paver": "concrete paver patio",
            "gravel": "decorative gravel pathway",
            "stone": "natural flagstone",
            "mulch": "bark mulch bed",
            "edging": "landscape edging border",
            "retaining wall": "segmental retaining wall block",
        }
        query = hints.get(category.lower(), category)
        # Default to plant for plant-y categories, otherwise no type filter
        ctype = "plant" if category.lower() in ("tree","trees","shrub","shrubs","perennial","perennials","grass","grasses") else None
        return self.find_component(query, component_type=ctype, top_k=top_k)

    def get_plant_details(self, botanical_name: str) -> Optional[Dict[str, Any]]:
        res = self.find_plant(botanical_name, top_k=1)
        return res[0] if res else None

    # ------------------------------------------------------------------
    # Ingestion / enrichment (for building the collection)
    # ------------------------------------------------------------------

    def upsert_plants(self, plants: List[Dict[str, Any]]) -> int:
        """Embed and upsert a list of plant profile dicts. Returns number upserted."""
        if not plants:
            return 0

        points = []
        for p in plants:
            text = self._build_search_text(p)
            if not text:
                continue
            vector = self._embed(text)
            payload = {k: v for k, v in p.items() if k not in ("vector",)}
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )

        if points:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"✅ Upserted {len(points)} plants into {COLLECTION_NAME}")
        return len(points)

    # ------------------------------------------------------------------
    # Helpers used by higher-level code
    # ------------------------------------------------------------------

    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return {
                "collection": COLLECTION_NAME,
                "points": info.points_count,
                "status": "healthy",
            }
        except Exception as e:
            return {"collection": COLLECTION_NAME, "status": "error", "error": str(e)}


def create_plant_palette(design_plants: List[str]) -> Dict[str, Any]:
    """Helper used in some flows to build a palette from a list of names."""
    catalog = PlantCatalog()
    palette = {"plants": [], "total_count": len(design_plants)}

    for name in design_plants:
        matches = catalog.find_plant(name, top_k=1)
        if matches:
            plant = matches[0]
            palette["plants"].append({
                "requested_name": name,
                "matched_plant": plant,
                "confidence": plant.get("score", 0.0),
            })
    return palette


# ----------------------------------------------------------------------
# One-by-one bootstrap / test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AutoScape Components catalog (plants + hardscape + materials)")
    parser.add_argument("--seed", action="store_true", help="Create/ensure collection + seed curated components (plants + hardscape)")
    parser.add_argument("--stats", action="store_true", help="Show collection stats")
    parser.add_argument("--test", action="store_true", help="Run sample searches (plants + hardscape)")
    args = parser.parse_args()

    catalog = PlantCatalog()

    if args.seed:
        print("\n🌱 Seeding dedicated components collection (plants + hardscape + materials)...")
        count = catalog.upsert_plants(SEED_COMPONENTS)
        print(f"   Seeded/upserted {count} components into {COLLECTION_NAME}.")

    if args.stats or not (args.seed or args.test):
        stats = catalog.get_collection_stats()
        print("\n📊 Components collection stats:")
        print(f"   Collection : {stats.get('collection')}")
        print(f"   Points     : {stats.get('points', 'unknown')}")
        print(f"   Status     : {stats.get('status')}")

    if args.test or not (args.seed or args.stats):
        print("\n🔍 Test: Japanese Maple (plant)")
        for i, p in enumerate(catalog.find_plant("Japanese Maple", top_k=2), 1):
            print(f"  {i}. {p['specific_name']} (score {p['score']:.3f}) | {p.get('category')} | {p.get('price_range')}")

        print("\n🔍 Test: Concrete Pavers (hardscape)")
        for i, p in enumerate(catalog.find_component("concrete pavers", component_type="hardscape", top_k=2), 1):
            print(f"  {i}. {p['specific_name']} | {p.get('price_range')} | unit={p.get('unit')}")

        print("\n🔍 Test category: shrubs (plants)")
        for i, p in enumerate(catalog.find_by_category("shrubs", top_k=2), 1):
            print(f"  {i}. {p['specific_name']}")

        print("\n🔍 Test category: paver (hardscape)")
        for i, p in enumerate(catalog.find_by_category("paver", top_k=2), 1):
            print(f"  {i}. {p['specific_name']} | {p.get('price_range')}")

    print("\n✅ Collection now supports plants + hardscape + materials for budget estimation after image generation.")
