from examples.phase11_app.repositories.equipment import fetch_equipment


def load_equipment(area: str) -> list[dict]:
    return fetch_equipment(area)
