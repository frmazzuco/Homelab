from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request


LOGGER = logging.getLogger("seerr-router")
logging.basicConfig(
    level=os.getenv("SEERR_ROUTER_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

APPRISE_NOTIFY_URL = os.getenv("SEERR_ROUTER_APPRISE_URL", "http://apprise-api:8000/notify/")
SHARED_TOKEN = os.getenv("SEERR_ROUTER_SHARED_TOKEN", "").strip()
HTTP_TIMEOUT_SECONDS = float(os.getenv("SEERR_ROUTER_HTTP_TIMEOUT_SECONDS", "10"))
DEFAULT_DESTINATION_URLS = [
    value.strip()
    for value in os.getenv("SEERR_ROUTER_DEFAULT_URLS", "").split(",")
    if value.strip()
]

UNRESOLVED_TEMPLATE_PATTERN = re.compile(r"^\{\{.+\}\}$")
REQUESTER_FROM_TEXT_PATTERNS = (
    re.compile(r"(?:requested by|solicitado por|pedido por)\s+@?([a-zA-Z0-9._-]+)", re.IGNORECASE),
    re.compile(r"(?:user|usuario)\s*[:=]\s*@?([a-zA-Z0-9._-]+)", re.IGNORECASE),
)

REQUESTER_KEYS = (
    "requester",
    "requester_username",
    "requester_name",
    "requested_by",
    "requested_by_username",
    "request_username",
    "username",
    "user",
)

REQUESTER_PATHS = (
    ("request", "requestedBy", "username"),
    ("request", "requestedBy", "displayName"),
    ("request", "requestedBy", "email"),
    ("requestedBy", "username"),
    ("requestedBy", "displayName"),
    ("notification", "request", "requestedBy", "username"),
)


def normalize_username(value: str) -> str:
    return value.strip().lower().lstrip("@")


def slugify_tag_value(value: str) -> str:
    normalized_value = normalize_username(value)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_value).strip("-")
    return slug or "unknown"


def string_from_payload(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped_value = value.strip()
    if not stripped_value:
        return None
    if UNRESOLVED_TEMPLATE_PATTERN.match(stripped_value):
        return None
    return stripped_value


def candidate_from_value(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("username", "displayName", "display_name", "name", "email"):
            candidate = candidate_from_value(value.get(key))
            if candidate:
                return candidate
        return None

    if isinstance(value, list):
        for item in value:
            candidate = candidate_from_value(item)
            if candidate:
                return candidate
        return None

    return string_from_payload(value)


def nested_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_requester(payload: dict[str, Any]) -> str | None:
    for key in REQUESTER_KEYS:
        candidate = candidate_from_value(payload.get(key))
        if candidate:
            return candidate

    for path in REQUESTER_PATHS:
        candidate = candidate_from_value(nested_value(payload, path))
        if candidate:
            return candidate

    for key in ("message", "subject", "body"):
        text_value = string_from_payload(payload.get(key))
        if not text_value:
            continue
        for pattern in REQUESTER_FROM_TEXT_PATTERNS:
            match = pattern.search(text_value)
            if match:
                return match.group(1)

    return None


def parse_destination_urls(raw_value: Any) -> list[str]:
    if isinstance(raw_value, str):
        return [value.strip() for value in raw_value.split(",") if value.strip()]

    if isinstance(raw_value, list):
        parsed_urls: list[str] = []
        for item in raw_value:
            if isinstance(item, str) and item.strip():
                parsed_urls.append(item.strip())
        return parsed_urls

    return []


def load_user_destination_map() -> dict[str, list[str]]:
    raw_map = os.getenv("SEERR_ROUTER_USER_DESTINATION_MAP", "").strip()
    if not raw_map:
        return {}

    try:
        parsed_map = json.loads(raw_map)
    except json.JSONDecodeError as error:
        raise RuntimeError("SEERR_ROUTER_USER_DESTINATION_MAP precisa ser JSON valido.") from error

    if not isinstance(parsed_map, dict):
        raise RuntimeError("SEERR_ROUTER_USER_DESTINATION_MAP precisa ser um objeto JSON (usuario -> url).")

    normalized_map: dict[str, list[str]] = {}
    for user_key, raw_destinations in parsed_map.items():
        normalized_user = normalize_username(str(user_key))
        if not normalized_user:
            continue
        parsed_urls = parse_destination_urls(raw_destinations)
        if parsed_urls:
            normalized_map[normalized_user] = parsed_urls

    return normalized_map


USER_DESTINATION_MAP = load_user_destination_map()

app = FastAPI(title="Seerr Router", version="1.0.0")


def resolve_destination_urls(requester: str | None) -> tuple[list[str], bool, bool]:
    if requester:
        normalized_requester = normalize_username(requester)
        direct_match = USER_DESTINATION_MAP.get(normalized_requester)
        if direct_match:
            return direct_match, True, False

    if DEFAULT_DESTINATION_URLS:
        return DEFAULT_DESTINATION_URLS, False, True

    return [], False, False


def build_outgoing_payload(
    incoming_payload: dict[str, Any],
    requester: str | None,
    destination_urls: list[str],
) -> dict[str, Any]:
    title = string_from_payload(incoming_payload.get("title"))
    if not title:
        event_name = string_from_payload(incoming_payload.get("notification_type")) or string_from_payload(
            incoming_payload.get("event")
        )
        title = f"Jellyseerr | {event_name}" if event_name else "Jellyseerr"

    body = string_from_payload(incoming_payload.get("body"))
    if not body:
        fallback_fields: list[str] = []
        for key in ("subject", "message", "event", "media_type", "media_tmdbid", "media_tvdbid"):
            value = string_from_payload(incoming_payload.get(key))
            if value:
                fallback_fields.append(f"{key}: {value}")
        body = " | ".join(fallback_fields) if fallback_fields else "Evento recebido do Jellyseerr."

    notification_type = string_from_payload(incoming_payload.get("type")) or "info"
    message_format = string_from_payload(incoming_payload.get("format")) or "text"
    incoming_tag = string_from_payload(incoming_payload.get("tag")) or "media"

    tags = [incoming_tag]
    if requester:
        tags.append(f"requester-{slugify_tag_value(requester)}")

    outgoing_payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "type": notification_type,
        "format": message_format,
        "tag": ",".join(dict.fromkeys(tags)),
    }
    if destination_urls:
        outgoing_payload["urls"] = destination_urls

    return outgoing_payload


async def send_to_apprise(outgoing_payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(APPRISE_NOTIFY_URL, json=outgoing_payload)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Falha de rede ao enviar para Apprise: {error!s}") from error

    if response.status_code >= 400:
        LOGGER.error(
            "Apprise retornou erro status=%s body=%s",
            response.status_code,
            response.text[:400],
        )
        raise HTTPException(status_code=502, detail="Apprise rejeitou a notificacao.")


def validate_shared_token(received_token: str | None) -> None:
    if not SHARED_TOKEN:
        return
    if not received_token or received_token != SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalido.")


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "userRoutes": len(USER_DESTINATION_MAP),
        "fallbackRoutes": len(DEFAULT_DESTINATION_URLS),
    }


@app.post("/webhook/jellyseerr")
async def jellyseerr_webhook(
    request: Request,
    x_seerr_router_token: str | None = Header(default=None),
) -> dict[str, Any]:
    validate_shared_token(x_seerr_router_token)

    try:
        incoming_payload = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Payload JSON invalido: {error!s}") from error

    if not isinstance(incoming_payload, dict):
        raise HTTPException(status_code=400, detail="Payload JSON precisa ser objeto.")

    requester = extract_requester(incoming_payload)
    destination_urls, used_direct_route, used_fallback_route = resolve_destination_urls(requester)
    outgoing_payload = build_outgoing_payload(incoming_payload, requester, destination_urls)
    await send_to_apprise(outgoing_payload)

    LOGGER.info(
        "Notificacao encaminhada requester=%s directRoute=%s fallbackRoute=%s overrideUrls=%s",
        requester or "desconhecido",
        used_direct_route,
        used_fallback_route,
        bool(destination_urls),
    )

    return {
        "ok": True,
        "requester": requester,
        "directRoute": used_direct_route,
        "fallbackRoute": used_fallback_route,
    }
