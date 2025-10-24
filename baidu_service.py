from urllib.parse import quote
from typing import Optional


def _encode(text: str) -> str:
    return quote(text or "")


def _map_mode(transport_mode: Optional[str]) -> str:
    # baidu web supports: driving, transit, walking, cycling
    if not transport_mode:
        return "driving"
    mode = transport_mode.lower()
    if mode in ("driving", "car"):
        return "driving"
    if mode in ("public_transit", "transit", "bus", "metro"):
        return "transit"
    if mode in ("walking", "walk"):
        return "walking"
    if mode in ("cycling", "bike"):
        return "cycling"
    return "driving"


def build_baidu_direction_url_from_names(from_name: str, to_name: str,
                                         from_city: str = None, to_city: str = None,
                                         transport_mode: str = None) -> Optional[str]:
    """Construct Baidu Maps direction URL using names only.

    This uses Baidu web direction page and does not require API keys.
    It relies on Baidu's internal geocoding of names.
    """
    if not to_name:
        return None

    # Include city context if provided to improve matching
    origin = (from_city or "") + (from_name or "") if from_name else (from_city or "")
    destination = (to_city or "") + to_name

    mode = _map_mode(transport_mode)
    base = "https://map.baidu.com/direction"
    url = f"{base}?origin={_encode(origin)}&destination={_encode(destination)}&mode={_encode(mode)}"
    return url

