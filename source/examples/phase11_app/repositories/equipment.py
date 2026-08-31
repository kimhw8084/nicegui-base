QUERY = 'SELECT tool_id, chamber, status FROM equipment_health WHERE area = :area'


def fetch_equipment(area: str) -> list[dict]:
    """Placeholder repository boundary; replace with company DB adapter."""
    _ = QUERY, area
    return []
