"""
Agent 2: MLS Inventory Matcher
Evaluates property database against buyer criteria (budget, location, bedrooms).
Ranks properties with granular match scoring.
"""
from typing import List
from .schemas import QualifiedLead, PropertyListing

MLS_DATABASE = [
    {
        "mls_id": "MLS-ATX-8821",
        "address": "4812 Barton Springs Terrace",
        "city": "Austin, TX",
        "price": 625000.00,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "sqft": 2180,
        "features": "Pool, modern kitchen, close to tech corridor"
    },
    {
        "mls_id": "MLS-ATX-9014",
        "address": "1208 Mueller Greenway Blvd",
        "city": "Austin, TX",
        "price": 589000.00,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1940,
        "features": "Solar equipped, walk to parks, EV charging"
    },
    {
        "mls_id": "MLS-ATX-7740",
        "address": "7402 Westlake Highland Drive",
        "city": "Austin, TX",
        "price": 890000.00,
        "bedrooms": 4,
        "bathrooms": 3.5,
        "sqft": 3150,
        "features": "Panoramic hill country views, luxury finishes"
    },
    {
        "mls_id": "MLS-SEA-4412",
        "address": "2214 Queen Anne Avenue N",
        "city": "Seattle, WA",
        "price": 720000.00,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1850,
        "features": "Space needle views, craftsman architecture"
    },
    {
        "mls_id": "MLS-SEA-5509",
        "address": "810 Ballard Locks Way",
        "city": "Seattle, WA",
        "price": 645000.00,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "sqft": 1420,
        "features": "Rooftop deck, walkable neighborhood"
    },
    {
        "mls_id": "MLS-ATX-9988",
        "address": "1404 Scenic Loop",
        "city": "Austin, TX",
        "price": 1250000.00,
        "bedrooms": 5,
        "bathrooms": 4.5,
        "sqft": 4500,
        "features": "Gated luxury estate, pool, private hill country vista"
    },
    {
        "mls_id": "MLS-SEA-9910",
        "address": "902 Magnolia Bluff Way",
        "city": "Seattle, WA",
        "price": 1450000.00,
        "bedrooms": 4,
        "bathrooms": 3.5,
        "sqft": 3800,
        "features": "Waterfront views, executive chef kitchen"
    }
]

def match_properties_for_lead(lead: QualifiedLead, max_results: int = 2) -> List[PropertyListing]:
    """
    Finds and ranks MLS properties aligning with lead's location, budget, and bedroom count.
    STRICT FILTER: Property price must be <= lead.budget. Budget $800k will never match $1.25M.
    """
    matches = []
    lead_city = lead.location.split(",")[0].lower()

    for prop in MLS_DATABASE:
        # STRICT Price Filter: Listing price must never exceed buyer budget
        if prop["price"] > lead.budget:
            continue

        prop_city = prop["city"].split(",")[0].lower()
        if lead_city not in prop_city and prop_city not in lead_city:
            continue

        # Bedroom check (allow within 1 bedroom)
        if prop["bedrooms"] < (lead.bedrooms - 1):
            continue

        # Granular match scoring
        price_ratio = prop["price"] / lead.budget if lead.budget > 0 else 1.0
        score = 80
        if 0.85 <= price_ratio <= 1.0:
            score += 10  # within 15% of max budget
        if prop["bedrooms"] == lead.bedrooms:
            score += 10  # exact bedroom match

        score = min(98, score)
        note = f"{prop['bedrooms']} Bed / {prop['bathrooms']} Bath in {prop['city']} | List: ${prop['price']:,.0f} (Target: ${lead.budget:,.0f})"

        matches.append(PropertyListing(
            mls_id=prop["mls_id"],
            address=prop["address"],
            city=prop["city"],
            price=prop["price"],
            bedrooms=prop["bedrooms"],
            bathrooms=prop["bathrooms"],
            sqft=prop["sqft"],
            match_score=score,
            match_notes=note
        ))

    matches.sort(key=lambda x: x.match_score, reverse=True)
    return matches[:max_results]
