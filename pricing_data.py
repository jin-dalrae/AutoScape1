"""
Real-world pricing estimates for landscaping plants and materials.
Used to ground the AI recommendations with realistic budget data.
"""

PRICING_DATABASE = {
    # PLANTS (per unit/pot)
    "tree": {
        "15-gallon": "$80 - $150",
        "24-inch box": "$250 - $500",
        "mature": "$800+"
    },
    "shrub": {
        "1-gallon": "$10 - $20",
        "5-gallon": "$30 - $55"
    },
    "bush": {
        "1-gallon": "$10 - $20",
        "5-gallon": "$30 - $55"
    },
    "grass": {
        "1-gallon": "$8 - $15",
        "plug": "$2 - $5"
    },
    "palm": {
        "15-gallon": "$100 - $200",
        "mature (per foot of trunk)": "$100 - $300"
    },
    "bamboo": {
        "5-gallon": "$40 - $80",
        "15-gallon": "$120 - $200"
    },
    "hedge": {
        "5-gallon": "$35 - $60",
        "per linear foot (installed)": "$40 - $100"
    },
    "flower": {
        "4-inch pot": "$3 - $6",
        "1-gallon": "$10 - $15"
    },
    "perennial": {
        "1-gallon": "$12 - $18"
    },
    "topiary": {
        "shaped 5-gallon": "$60 - $120",
        "mature shaped": "$300+"
    },

    # HARDSCAPE (per unit or area)
    "paver": {
        "concrete (per sq ft)": "$5 - $10",
        "brick (per sq ft)": "$8 - $15",
        "stone (per sq ft)": "$15 - $30"
    },
    "gravel": {
        "pea gravel (per cubic yard)": "$40 - $60",
        "decorative rock (per ton)": "$100 - $300",
        "bag (0.5 cu ft)": "$5 - $10"
    },
    "stone": {
        "flagstone (per ton)": "$300 - $600",
        "boulder (each)": "$100 - $500"
    },
    "mulch": {
        "bulk (per cubic yard)": "$30 - $50",
        "bag (2 cu ft)": "$4 - $8"
    },
    "edging": {
        "plastic (per ft)": "$1 - $3",
        "metal (per ft)": "$3 - $8",
        "stone (per ft)": "$5 - $15"
    },
    "retaining wall": {
        "block (per sq ft face)": "$15 - $25",
        "natural stone (per sq ft face)": "$30 - $60"
    },

    # LABOR & INSTALLATION (per unit or as % of materials)
    "site_prep": {
        "demolition & haul (per sq ft)": "$2 - $5",
        "basic clearing": "$300 - $800 lump sum (small yard)"
    },
    "grading": {
        "rough + final grade (per sq ft)": "$1.50 - $4",
        "import soil / amendment (per cubic yard)": "$40 - $80 + delivery"
    },
    "plant_install": {
        "5-gallon shrub/perennial (each)": "$15 - $35 installed",
        "15-gallon tree (each)": "$75 - $150 installed",
        "large specimen (each)": "$200+ installed"
    },
    "hardscape_install": {
        "paver patio (per sq ft installed)": "$12 - $25",
        "gravel path (per sq ft installed)": "$6 - $12",
        "flagstone (per sq ft installed)": "$18 - $35"
    },
    "irrigation": {
        "basic drip / spray system (per sq ft)": "$1.50 - $3.50 installed",
        "full controller + valves (lump)": "$800 - $2,000"
    },
    "cleanup": {
        "final grade + haul (per sq ft)": "$0.75 - $2",
        "small project cleanup": "$200 - $500 lump sum"
    },
    "general_labor": {
        "project management / supervision": "10-15% of total materials + install",
        "permits + inspections (typical residential)": "$150 - $600"
    }
}

# SPECIFIC BOTANICAL NAME PRICING
# Based on actual nursery prices for identified species
SPECIFIC_PLANT_PRICING = {
    # Japanese Maples
    "Acer palmatum": {
        "1-gallon": "$25 - $35",
        "5-gallon": "$65 - $95",
        "15-gallon": "$180 - $280"
    },
    "Acer palmatum 'Bloodgood'": {
        "5-gallon": "$75 - $110",
        "15-gallon": "$200 - $350"
    },
    
    # Ornamental Grasses
    "Festuca glauca": {  # Blue Fescue
        "4-inch pot": "$5 - $8",
        "1-gallon": "$12 - $15"
    },
    "Calamagrostis": {  # Reed Grass
        "1-gallon": "$15 - $22",
        "3-gallon": "$30 - $40"
    },
    "Imperata cylindrica": {  # Japanese Blood Grass
        "1-gallon": "$14 - $20"
    },
    
    # Evergreens
    "Picea abies": {  # Norway Spruce
        "5-gallon": "$45 - $70",
        "15-gallon": "$120 - $180"
    },
    "Juniperus": {  # Juniper
        "5-gallon": "$35 - $60",
        "15-gallon": "$90 - $140"
    },
    
    # Flowering Shrubs
    "Adenium obesum": {  # Desert Rose
        "4-inch pot": "$12 - $18",
        "1-gallon": "$25 - $40"
    },
    "Rosa": {  # Rose
        "2-gallon": "$18 - $30",
        "5-gallon": "$40 - $65"
    },
    "Lavandula": {  # Lavender
        "1-gallon": "$10 - $16",
        "3-gallon": "$22 - $35"
    },
    
    # Bamboo
    "Bambusa": {  # Bamboo species
        "5-gallon": "$40 - $75",
        "15-gallon": "$130 - $220"
    },
    
    # Palms
    "Washingtonia": {  # Fan Palm
        "15-gallon": "$110 - $200",
        "per foot of trunk": "$150 - $350"
    },
    
    # Ground Cover
    "Vinca minor": {  # Periwinkle
        "4-inch pot": "$4 - $7",
        "flat (18 plants)": "$25 - $40"
    }
}

def get_pricing_context(search_term: str, tags: list) -> str:
    """
    Get relevant pricing information based on search term and tags.
    """
    relevant_prices = []
    search_term = search_term.lower()
    
    # Check for matches in our database
    for category, prices in PRICING_DATABASE.items():
        # Check if category is in search term or any tag
        if category in search_term or any(category in tag.lower() for tag in tags):
            price_list = ", ".join([f"{k}: {v}" for k, v in prices.items()])
            relevant_prices.append(f"- **{category.title()}**: {price_list}")
            
    if not relevant_prices:
        # Default fallback if nothing specific matches
        return "Standard Landscaping Estimates:\n- Plants (1-5 gal): $10-$50\n- Hardscape: $5-$30 per sq ft"
        
    return "Market Pricing Reference:\n" + "\n".join(relevant_prices)

def get_specific_plant_pricing(botanical_name: str, size: str = "5-gallon") -> str:
    """
    Get specific pricing for a botanical name from RAG data.
    
    Args:
        botanical_name: Scientific name (e.g., "Acer palmatum")
        size: Container size
    
    Returns:
        Price range string or fallback
    """
    # Try exact match first
    if botanical_name in SPECIFIC_PLANT_PRICING:
        prices = SPECIFIC_PLANT_PRICING[botanical_name]
        if size in prices:
            return prices[size]
        # Return first available size if exact match not found
        return list(prices.values())[0]
    
    # Try partial genus match
    genus = botanical_name.split()[0] if botanical_name else ""
    for key in SPECIFIC_PLANT_PRICING:
        if genus and genus in key:
            prices = SPECIFIC_PLANT_PRICING[key]
            if size in prices:
                return prices[size]
            return list(prices.values())[0]
    
    # Fallback to generic pricing
    if "tree" in botanical_name.lower():
        return PRICING_DATABASE["tree"].get(size, "$50 - $100")
    elif "shrub" in botanical_name.lower() or "bush" in botanical_name.lower():
        return PRICING_DATABASE["shrub"].get(size, "$20 - $40")
    
    return "$15 - $30"  # Generic fallback

