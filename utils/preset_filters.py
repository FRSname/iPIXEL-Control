"""
Preset search and filter utilities
"""

from typing import List, Dict, Any


def filter_presets(presets: List[Dict[str, Any]], search_query: str, category: str = 'all') -> List[Dict[str, Any]]:
    """
    Filter presets based on search query and category
    
    Args:
        presets: List of preset dictionaries
        search_query: Search string to match against preset names
        category: Category to filter by ('all', 'text', 'image', 'clock', etc.)
    
    Returns:
        Filtered list of presets
    """
    filtered = presets
    
    # Filter by category
    if category != 'all':
        filtered = [p for p in filtered if p.get('type', '') == category]
    
    # Filter by search query
    if search_query.strip():
        query_lower = search_query.lower()
        filtered = [
            p for p in filtered 
            if query_lower in p.get('name', '').lower() or 
               query_lower in p.get('description', '').lower()
        ]
    
    return filtered


def get_preset_categories(presets: List[Dict[str, Any]]) -> List[str]:
    """
    Get unique categories from presets
    
    Args:
        presets: List of preset dictionaries
    
    Returns:
        List of unique category names
    """
    categories = set()
    for preset in presets:
        preset_type = preset.get('type', 'other')
        categories.add(preset_type)
    
    return ['all'] + sorted(list(categories))
