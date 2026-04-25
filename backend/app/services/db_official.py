"""
DB API Marketplace Client.

Wraps the four officially booked APIs:
- RIS::Stations  -> Bahnhof-Suche, Geo-Lookup           [API-Key only]
- StaDa          -> Stations-Stammdaten                 [API-Key only]
- Timetables     -> Soll-/Ist-Fahrplan (IRIS)           [mTLS required]
- FaSta          -> Live-Status Aufzüge/Rolltreppen     [API-Key only]

Headers:
    DB-Api-Key:   <api-key>
    DB-Client-Id: <client-id>

Two HTTPX clients are kept side by side: one with mTLS for Timetables,
one without for everything else. Sending a client cert to APIs that don't
expect it triggers HTTP 495 on the DB side.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class DBOfficialClient:
    """Single client to talk to all four DB Marketplace APIs."""

    def __init__(self):
        self.base = settings.DB_API_BASE.rstrip("/")
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "TransitAI/1.0 (DB-Mindbox-PoC)",
        }
        if settings.DB_API_KEY:
            self.headers["DB-Api-Key"] = settings.DB_API_KEY
        if settings.DB_CLIENT_ID:
            self.headers["DB-Client-Id"] = settings.DB_CLIENT_ID

        # Plain client (no mTLS) for StaDa, FaSta, RIS::Stations
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers=self.headers,
        )

        # mTLS client only for Timetables (IRIS)
        self.mtls_client: Optional[httpx.AsyncClient] = None
        if settings.db_mtls_available:
            self.mtls_client = httpx.AsyncClient(
                timeout=15.0,
                headers={**self.headers, "Accept": "application/xml"},
                cert=(settings.DB_CERT_PATH, settings.DB_KEY_PATH),
            )
            logger.info("DB Official Client: mTLS enabled for Timetables")
        else:
            logger.info("DB Official Client: mTLS not configured (cert/key missing)")

    async def close(self):
        await self.client.aclose()
        if self.mtls_client:
            await self.mtls_client.aclose()

    # ----------------------------------------------------------------------
    # RIS::Stations — Bahnhof-Suche, Geo-Lookup
    # ----------------------------------------------------------------------
    async def search_stations(self, query: str, limit: int = 8) -> list[dict]:
        url = f"{self.base}/ris-stations/v1/stop-places/by-name/{query}"
        try:
            r = await self.client.get(url, params={"limit": limit}, headers={"Accept": "application/vnd.de.db.ris+json"})
            r.raise_for_status()
            data = r.json()
            return data.get("stopPlaces", []) if isinstance(data, dict) else []
        except httpx.HTTPError as e:
            logger.warning(f"RIS::Stations search failed for {query!r}: {e}")
            return []

    async def stations_near(self, lat: float, lon: float, radius_m: int = 5000, limit: int = 5) -> list[dict]:
        url = f"{self.base}/ris-stations/v1/stop-places/by-position"
        params = {"latitude": lat, "longitude": lon, "radius": radius_m, "limit": limit}
        try:
            r = await self.client.get(url, params=params, headers={"Accept": "application/vnd.de.db.ris+json"})
            r.raise_for_status()
            data = r.json()
            return data.get("stopPlaces", []) if isinstance(data, dict) else []
        except httpx.HTTPError as e:
            logger.warning(f"RIS::Stations geo lookup failed at {lat},{lon}: {e}")
            return []

    # ----------------------------------------------------------------------
    # StaDa - Station Data
    # ----------------------------------------------------------------------
    async def station_details(self, station_number: int) -> Optional[dict]:
        url = f"{self.base}/station-data/v2/stations/{station_number}"
        try:
            r = await self.client.get(url)
            r.raise_for_status()
            data = r.json()
            results = data.get("result", []) if isinstance(data, dict) else []
            return results[0] if results else None
        except httpx.HTTPError as e:
            logger.warning(f"StaDa fetch failed for {station_number}: {e}")
            return None

    # ----------------------------------------------------------------------
    # Timetables (IRIS) — header-auth, returns XML
    # ----------------------------------------------------------------------
    async def timetable_station(self, pattern: str) -> list[dict]:
        url = f"{self.base}/timetables/v1/station/{pattern}"
        try:
            r = await self.client.get(url, headers={"Accept": "application/xml"})
            r.raise_for_status()
            return _parse_iris_stations(r.text)
        except httpx.HTTPError as e:
            logger.warning(f"Timetables station lookup failed for {pattern!r}: {e}")
            return []

    async def timetable_plan(self, eva_no: str, date_yymmdd: str, hour_hh: str) -> list[dict]:
        url = f"{self.base}/timetables/v1/plan/{eva_no}/{date_yymmdd}/{hour_hh}"
        try:
            r = await self.client.get(url, headers={"Accept": "application/xml"})
            r.raise_for_status()
            return _parse_iris_timetable(r.text)
        except httpx.HTTPError as e:
            logger.warning(f"Timetables plan failed for {eva_no} {date_yymmdd} {hour_hh}: {e}")
            return []

    async def timetable_full_changes(self, eva_no: str) -> list[dict]:
        url = f"{self.base}/timetables/v1/fchg/{eva_no}"
        try:
            r = await self.client.get(url, headers={"Accept": "application/xml"})
            r.raise_for_status()
            return _parse_iris_changes(r.text)
        except httpx.HTTPError as e:
            logger.warning(f"Timetables changes failed for {eva_no}: {e}")
            return []

    # ----------------------------------------------------------------------
    # FaSta - Facility Status
    # ----------------------------------------------------------------------
    async def facilities_at_station(self, station_number: int) -> list[dict]:
        url = f"{self.base}/fasta/v2/stations/{station_number}"
        try:
            r = await self.client.get(url)
            r.raise_for_status()
            data = r.json()
            return data.get("facilities", []) if isinstance(data, dict) else []
        except httpx.HTTPError as e:
            logger.warning(f"FaSta fetch failed for {station_number}: {e}")
            return []

    async def accessibility_report(self, station_number: int) -> dict:
        facilities = await self.facilities_at_station(station_number)
        active = [f for f in facilities if f.get("state") == "ACTIVE"]
        inactive = [f for f in facilities if f.get("state") == "INACTIVE"]
        unknown = [f for f in facilities if f.get("state") not in ("ACTIVE", "INACTIVE")]
        return {
            "station_number": station_number,
            "total": len(facilities),
            "active": len(active),
            "inactive": len(inactive),
            "unknown": len(unknown),
            "fully_accessible": len(facilities) > 0 and len(inactive) == 0,
            "details": facilities,
        }


# ----------------------------------------------------------------------
# IRIS XML parsers (Timetables API)
# ----------------------------------------------------------------------
def _parse_iris_stations(xml_text: str) -> list[dict]:
    out = []
    try:
        root = ET.fromstring(xml_text)
        for station in root.findall(".//station"):
            out.append({
                "name": station.get("name"),
                "eva": station.get("eva"),
                "ds100": station.get("ds100"),
                "db": station.get("db"),
                "creationts": station.get("creationts"),
            })
    except ET.ParseError as e:
        logger.warning(f"IRIS station XML parse error: {e}")
    return out


def _parse_iris_timetable(xml_text: str) -> list[dict]:
    out = []
    try:
        root = ET.fromstring(xml_text)
        for stop in root.findall(".//s"):
            tl = stop.find("tl")
            ar = stop.find("ar")
            dp = stop.find("dp")
            out.append({
                "id": stop.get("id"),
                "category": tl.get("c") if tl is not None else None,
                "trip_type": tl.get("t") if tl is not None else None,
                "owner": tl.get("o") if tl is not None else None,
                "number": tl.get("n") if tl is not None else None,
                "arrival_time": ar.get("pt") if ar is not None else None,
                "arrival_platform": ar.get("pp") if ar is not None else None,
                "arrival_path": ar.get("ppth") if ar is not None else None,
                "departure_time": dp.get("pt") if dp is not None else None,
                "departure_platform": dp.get("pp") if dp is not None else None,
                "departure_path": dp.get("ppth") if dp is not None else None,
                "line": dp.get("l") if dp is not None else (ar.get("l") if ar is not None else None),
            })
    except ET.ParseError as e:
        logger.warning(f"IRIS timetable XML parse error: {e}")
    return out


def _parse_iris_changes(xml_text: str) -> list[dict]:
    out = []
    try:
        root = ET.fromstring(xml_text)
        for stop in root.findall(".//s"):
            ar = stop.find("ar")
            dp = stop.find("dp")
            out.append({
                "id": stop.get("id"),
                "arrival_change_time": ar.get("ct") if ar is not None else None,
                "arrival_change_platform": ar.get("cp") if ar is not None else None,
                "departure_change_time": dp.get("ct") if dp is not None else None,
                "departure_change_platform": dp.get("cp") if dp is not None else None,
            })
    except ET.ParseError as e:
        logger.warning(f"IRIS changes XML parse error: {e}")
    return out


# Singleton
db_official = DBOfficialClient()
