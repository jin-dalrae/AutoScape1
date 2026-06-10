"""
RAG-Enhanced Budget Calculator.
Uses plant catalog and RAG data for accurate pricing.
"""

from typing import List, Dict, Any
from plant_catalog import PlantCatalog
from pricing_data import get_specific_plant_pricing
import re

def calculate_budget_with_rag(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate budget using the *dedicated* plants collection (autoscape-plants / PLANT_COLLECTION).
    Independent from the general visual product RAG collection.
    """
    
    Args:
        items: List of items with 'name', 'quantity', 'size'
    
    Returns:
        Enhanced budget with RAG images and botanical names
    """
    catalog = PlantCatalog()
    total_low = 0.0
    total_high = 0.0
    breakdown = []
    
    for item in items:
        name = item.get('name', 'Unknown')
        quantity = item.get('quantity', 1)
        size = item.get('size', '5-gallon')
        
        # Query RAG for this plant
        rag_matches = catalog.find_plant(name, top_k=1)
        
        if rag_matches:
            plant = rag_matches[0]
            botanical_name = plant['botanical_name']
            common_name = plant['common_name']
            image_url = plant['image_url']
            
            # Get specific pricing based on botanical name
            price_range_str = get_specific_plant_pricing(botanical_name, size)
        else:
            # Fallback if not in RAG
            botanical_name = ""
            common_name = name
            image_url = ""
            price_range_str = "$15 - $30"
        
        # Parse price range
        low, high = parse_price_range(price_range_str)
        
        item_total_low = low * quantity
        item_total_high = high * quantity
        
        total_low += item_total_low
        total_high += item_total_high
        
        breakdown.append({
            "common_name": common_name,
            "botanical_name": botanical_name,
            "image_url": image_url,
            "quantity": quantity,
            "size": size,
            "unit_price": price_range_str,
            "total_estimate": f"${item_total_low:,.2f} - ${item_total_high:,.2f}",
            "rag_verified": bool(botanical_name)
        })
    
    return {
        "total_low": total_low,
        "total_high": total_high,
        "breakdown": breakdown,
        "rag_enhanced": True
    }

def parse_price_range(price_str: str) -> tuple:
    """Extract low and high price from string like '$10 - $20'."""
    clean_str = price_str.replace('$', '').replace(',', '')
    parts = clean_str.split('-')
    
    if len(parts) == 2:
        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return low, high
        except ValueError:
            pass
    elif len(parts) == 1:
        try:
            val = float(re.sub(r'[^\d.]', '', parts[0]))
            return val, val
        except ValueError:
            pass
    
    return 0.0, 0.0

if __name__ == "__main__":
    # Test with sample items
    test_items = [
        {"name": "Japanese Maple", "quantity": 2, "size": "15-gallon"},
        {"name": "Lavender", "quantity": 10, "size": "1-gallon"},
        {"name": "Blue Fescue Grass", "quantity": 15, "size": "4-inch pot"}
    ]
    
    result = calculate_budget_with_rag(test_items)
    
    print(f"\n💰 RAG-Enhanced Budget: ${result['total_low']:,.2f} - ${result['total_high']:,.2f}\n")
    
    for item in result['breakdown']:
        print(f"✅ {item['common_name']}")
        if item['botanical_name']:
            print(f"   Botanical: {item['botanical_name']}")
        print(f"   Qty: {item['quantity']} × {item['size']}")
        print(f"   Total: {item['total_estimate']}")
        if item['image_url']:
            print(f"   Image: {item['image_url'][:50]}...")
        print()
