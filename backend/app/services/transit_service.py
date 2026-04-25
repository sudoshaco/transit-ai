"""
Transit Service — Routing Layer.

Three-tier strategy (mirrors the LLM router pattern):
  1. Self-hosted db-rest (DBREST_BASE)        -> primary, no rate limit
  2. Public db-rest      (DBREST_PUBLIC)      -> overflow if self-hosted is down
  3. Mock fallback                            -> pitch-safety net, never fails

Address handling:
  - Free-text addresses are resolved via /locations?addresses=true&poi=true
    (HAFAS supports this directly, no separate geocoder needed for db-rest data).
  - Falls back to Nominatim if db-rest cannot resolve.

Enrichment:
  - DB Official APIs (StaDa, FaSta) augment routes with station details
    and accessibility status.
"""

import re
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

import httpx

from app.core.config import settings
from app.models.route import Route, Location, Price, Remark

logger = logging.getLogger(__name__)


class TransitService:
    def __init__(self):
        # Self-hosted db-rest (primary)
        self._primary = httpx.AsyncClient(
            base_url=settings.DBREST_BASE,
            timeout=15.0,
            headers={"User-Agent": "TransitAI/1.0"},
        )
        # Public db-rest (fallback)
        self._fallback = httpx.AsyncClient(
            base_url=settings.DBREST_PUBLIC,
            timeout=15.0,
            headers={"User-Agent": "TransitAI/1.0"},
        )
        # Nominatim (address geocoding fallback)
        self._nominatim = httpx.AsyncClient(
            base_url=settings.NOMINATIM_BASE,
            timeout=10.0,
            headers={"User-Agent": "TransitAI/1.0 (https://github.com/transit-ai)"},
        )

    async def close(self):
        await self._primary.aclose()
        await self._fallback.aclose()
        await self._nominatim.aclose()

    # ------------------------------------------------------------------
    # Provider routing
    # ------------------------------------------------------------------
    async def _get(self, path: str, params: dict) -> Optional[dict | list]:
        """Try primary -> fallback. Return parsed JSON or None."""
        for label, client in (("self-hosted", self._primary), ("public", self._fallback)):
            try:
                r = await client.get(path, params=params)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                logger.warning(f"db-rest [{label}] {path} failed: {e}")
        return None

    # ------------------------------------------------------------------
    # Location / address resolution
    # ------------------------------------------------------------------
    async def search_locations(self, query: str) -> list[Location]:
        data = await self._get(
            "/locations",
            {
                "query": query,
                "results": 8,
                "language": "de",
                "addresses": "true",
                "poi": "true",
                "stops": "true",
            },
        )
        if not data or not isinstance(data, list):
            return []
        return [Location(**loc) for loc in data if isinstance(loc, dict)]

    async def _resolve_query_to_location(self, name: str) -> Optional[dict]:
        """
        Resolve free-text input to a HAFAS location dict suitable for /journeys.

        Returns:
          - {"id": "8011160"} for stations
          - {"latitude": ..., "longitude": ..., "address": "..."} for addresses/POIs
        """
        if not name:
            return None
        cleaned = name.strip()

        # Already a numeric station ID? pass through.
        if re.fullmatch(r"\d{6,9}", cleaned):
            return {"type": "id", "id": cleaned}

        # Try db-rest /locations with addresses + POIs enabled
        data = await self._get(
            "/locations",
            {
                "query": cleaned,
                "results": 1,
                "language": "de",
                "addresses": "true",
                "poi": "true",
                "stops": "true",
            },
        )
        if data and isinstance(data, list) and len(data) > 0:
            loc = data[0]
            if loc.get("type") in ("station", "stop") and loc.get("id"):
                return {"type": "id", "id": str(loc["id"])}
            # Address/POI: return coordinates
            lat = loc.get("latitude") or (loc.get("location") or {}).get("latitude")
            lon = loc.get("longitude") or (loc.get("location") or {}).get("longitude")
            if lat and lon:
                return {
                    "type": "coords",
                    "latitude": lat,
                    "longitude": lon,
                    "address": loc.get("name") or cleaned,
                }

        # Last resort: Nominatim geocoding
        coords = await self._nominatim_geocode(cleaned)
        if coords:
            return {"type": "coords", **coords, "address": cleaned}

        return None

    async def _nominatim_geocode(self, query: str) -> Optional[dict]:
        try:
            r = await self._nominatim.get(
                "/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "de"},
            )
            r.raise_for_status()
            results = r.json()
            if results:
                return {
                    "latitude": float(results[0]["lat"]),
                    "longitude": float(results[0]["lon"]),
                }
        except (httpx.HTTPError, KeyError, ValueError, IndexError) as e:
            logger.warning(f"Nominatim geocoding failed for {query!r}: {e}")
        return None

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    async def fetch_routes(
        self,
        origin: str,
        destination: str,
        departure: Optional[datetime] = None,
        arrival: Optional[datetime] = None,
        preferences: Optional[dict] = None,
    ) -> list[Route]:
        from_loc = await self._resolve_query_to_location(origin)
        to_loc = await self._resolve_query_to_location(destination)

        if not from_loc or not to_loc:
            logger.warning(
                f"Could not resolve: from={origin!r}->{from_loc}, to={destination!r}->{to_loc}"
            )
            return self._mock_routes(origin, destination, reason="resolve_failed")

        params = self._build_journey_params(from_loc, to_loc, departure, arrival, preferences)

        data = await self._get("/journeys", params)
        if not data or not isinstance(data, dict):
            logger.warning("Both db-rest providers failed; returning mock route")
            return self._mock_routes(origin, destination, reason="api_unavailable")

        routes = self._parse_journeys(data.get("journeys", []))
        if not routes:
            return self._mock_routes(origin, destination, reason="no_results")
        return routes

    def _build_journey_params(
        self,
        from_loc: dict,
        to_loc: dict,
        departure: Optional[datetime],
        arrival: Optional[datetime],
        preferences: Optional[dict],
    ) -> dict:
        params: dict = {
            "results": 6,
            "language": "de",
            "stopovers": "true",
            "remarks": "true",
        }

        # Origin
        if from_loc["type"] == "id":
            params["from"] = from_loc["id"]
        else:
            params["from.latitude"] = from_loc["latitude"]
            params["from.longitude"] = from_loc["longitude"]
            params["from.address"] = from_loc.get("address", "Start")

        # Destination
        if to_loc["type"] == "id":
            params["to"] = to_loc["id"]
        else:
            params["to.latitude"] = to_loc["latitude"]
            params["to.longitude"] = to_loc["longitude"]
            params["to.address"] = to_loc.get("address", "Ziel")

        # arrival hat Vorrang: wenn der Nutzer sagt "muss um X da sein",
        # fragen wir HAFAS direkt nach Verbindungen, die spätestens um X ankommen.
        if arrival:
            params["arrival"] = arrival.isoformat()
        elif departure:
            params["departure"] = departure.isoformat()

        if preferences:
            if preferences.get("no_transfers"):
                params["transfers"] = 0
            elif preferences.get("max_transfers") is not None:
                params["transfers"] = preferences["max_transfers"]
            if preferences.get("accessible"):
                params["accessibility"] = "complete"
            if preferences.get("avoid_bus"):
                params["bus"] = "false"

        return params

    # ------------------------------------------------------------------
    # Departures
    # ------------------------------------------------------------------
    async def get_departures(self, station_id: str, limit: int = 10) -> list:
        for label, client in (("self-hosted", self._primary), ("public", self._fallback)):
            try:
                r = await client.get(
                    f"/stops/{station_id}/departures",
                    params={"results": limit, "language": "de"},
                )
                r.raise_for_status()
                data = r.json()
                return data.get("departures", []) if isinstance(data, dict) else data
            except httpx.HTTPError as e:
                logger.warning(f"departures [{label}] failed: {e}")
        return []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _parse_journeys(self, journeys: list) -> list[Route]:
        routes: list[Route] = []
        for journey in journeys:
            legs = journey.get("legs", [])
            if not legs:
                continue

            price_data = journey.get("price")
            price = Price(**price_data) if isinstance(price_data, dict) else None

            remarks_raw = journey.get("remarks", [])
            remarks = [Remark(**r) for r in remarks_raw if isinstance(r, dict)]

            walking_legs = [l for l in legs if not l.get("walking", False)]
            transfers = max(0, len(walking_legs) - 1)

            routes.append(Route(
                duration_minutes=self._calc_duration(legs),
                transfers=transfers,
                departure=legs[0].get("departure"),
                arrival=legs[-1].get("arrival"),
                legs=legs,
                price=price,
                remarks=remarks,
            ))
        return routes

    def _calc_duration(self, legs: list) -> int:
        if not legs:
            return 0
        dep = legs[0].get("departure")
        arr = legs[-1].get("arrival")
        if dep and arr:
            try:
                d = datetime.fromisoformat(dep.replace("Z", "+00:00"))
                a = datetime.fromisoformat(arr.replace("Z", "+00:00"))
                return int((a - d).total_seconds() / 60)
            except (ValueError, TypeError):
                return 0
        return 0

    # ------------------------------------------------------------------
    # Mock fallback (pitch-safety)
    # ------------------------------------------------------------------
    def _mock_routes(self, origin: str, destination: str, reason: str) -> list[Route]:
        """
        Fixed demo routes used when the routing backend is unavailable.
        Marked clearly so the UI / LLM can warn the user.
        """
        now = datetime.now(timezone.utc).replace(microsecond=0)
        dep1 = now + timedelta(minutes=12)
        arr1 = dep1 + timedelta(minutes=98)
        dep2 = now + timedelta(minutes=42)
        arr2 = dep2 + timedelta(minutes=85)

        def _leg(dep_time, arr_time, line, from_name, to_name, walking=False):
            return {
                "departure": dep_time.isoformat(),
                "arrival": arr_time.isoformat(),
                "origin": {"type": "stop", "id": "0", "name": from_name},
                "destination": {"type": "stop", "id": "0", "name": to_name},
                "line": {"name": line, "product": "nationalExpress"},
                "walking": walking,
            }

        mock1 = Route(
            duration_minutes=98,
            transfers=0,
            departure=dep1.isoformat(),
            arrival=arr1.isoformat(),
            legs=[_leg(dep1, arr1, "ICE 374", origin, destination)],
            price=Price(amount=29.90, currency="EUR", hint="Sparpreis (Demo)"),
            remarks=[Remark(type="status", code="DEMO", text=f"Demo-Route ({reason}) — externe API kurzzeitig nicht erreichbar")],
        )
        mock2 = Route(
            duration_minutes=85,
            transfers=1,
            departure=dep2.isoformat(),
            arrival=arr2.isoformat(),
            legs=[
                _leg(dep2, dep2 + timedelta(minutes=40), "RE 4", origin, "Umstieg"),
                _leg(dep2 + timedelta(minutes=45), arr2, "ICE 882", "Umstieg", destination),
            ],
            price=Price(amount=42.50, currency="EUR", hint="Flexpreis (Demo)"),
            remarks=[Remark(type="status", code="DEMO", text=f"Demo-Route ({reason}) — externe API kurzzeitig nicht erreichbar")],
        )
        return [mock1, mock2]
