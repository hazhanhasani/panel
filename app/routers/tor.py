from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.tor import (
    TorEventResponse,
    TorLocationCreate,
    TorLocationResponse,
    TorSettingsModel,
    TorSummary,
)
from app.models.tor import TorLocationUpdate
from app.operation.tor import tor_operation
from app.utils import responses

from .authentication import require_permission

router = APIRouter(
    tags=["Tor Locations"],
    prefix="/api/tor",
    responses={401: responses._401, 403: responses._403},
)


def _raise_tor_error(exc: Exception) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail=str(exc).strip("'")) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("/locations", response_model=list[TorLocationResponse])
async def list_tor_locations(
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "read")),
):
    return await tor_operation.list_locations(db, node_id=node_id)


@router.get("/summary", response_model=TorSummary)
async def tor_summary(
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "read")),
):
    return await tor_operation.summary(db)


@router.get("/locations/{location_id}", response_model=TorLocationResponse)
async def get_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "read")),
):
    try:
        return await tor_operation.get_location(db, location_id)
    except Exception as exc:
        _raise_tor_error(exc)


@router.post("/locations", response_model=TorLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_tor_location(
    model: TorLocationCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "create")),
):
    try:
        return await tor_operation.create_location(db, model, actor=admin.username)
    except Exception as exc:
        _raise_tor_error(exc)


@router.patch("/locations/{location_id}", response_model=TorLocationResponse)
async def update_tor_location(
    location_id: str,
    model: TorLocationUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    try:
        return await tor_operation.update_location(db, location_id, model, actor=admin.username)
    except Exception as exc:
        _raise_tor_error(exc)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tor_location(
    location_id: str,
    purge_data: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "delete")),
):
    try:
        await tor_operation.delete_location(db, location_id, actor=admin.username, purge_data=purge_data)
    except Exception as exc:
        _raise_tor_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/locations/{location_id}/enable", response_model=TorLocationResponse)
async def enable_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    try:
        return await tor_operation.set_enabled(db, location_id, True, actor=admin.username)
    except Exception as exc:
        _raise_tor_error(exc)


@router.post("/locations/{location_id}/disable", response_model=TorLocationResponse)
async def disable_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    try:
        return await tor_operation.set_enabled(db, location_id, False, actor=admin.username)
    except Exception as exc:
        _raise_tor_error(exc)


async def _run_action(location_id: str, action: str, db: AsyncSession, admin: AdminDetails):
    try:
        return await tor_operation.action(db, location_id, action, actor=admin.username)
    except Exception as exc:
        _raise_tor_error(exc)


@router.post("/locations/{location_id}/restart", response_model=TorLocationResponse)
async def restart_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    return await _run_action(location_id, "restart", db, admin)


@router.post("/locations/{location_id}/new-identity", response_model=TorLocationResponse)
async def new_tor_identity(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    return await _run_action(location_id, "new_ip", db, admin)


@router.post("/locations/{location_id}/repair", response_model=TorLocationResponse)
async def repair_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    return await _run_action(location_id, "repair", db, admin)


@router.post("/locations/{location_id}/test", response_model=TorLocationResponse)
async def test_tor_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "read")),
):
    return await _run_action(location_id, "test", db, admin)


@router.get("/locations/{location_id}/diagnostics")
async def tor_location_diagnostics(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "read")),
):
    location = await _run_action(location_id, "health", db, admin)
    events = await tor_operation.recent_events(db, location_id, limit=50)
    return {
        "location": TorLocationResponse.model_validate(location),
        "recent_events": [TorEventResponse.model_validate(item) for item in events],
        "limitations": {
            "tcp_primary": True,
            "general_udp_supported": False,
            "quic_may_fail": True,
            "game_voip_recommended": False,
        },
    }


@router.get("/locations/{location_id}/events", response_model=list[TorEventResponse])
async def tor_location_events(
    location_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "logs")),
):
    try:
        await tor_operation.get_location(db, location_id)
        return await tor_operation.recent_events(db, location_id, limit=limit)
    except Exception as exc:
        _raise_tor_error(exc)


@router.post("/reconcile", response_model=list[TorLocationResponse])
async def reconcile_tor(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    return await tor_operation.reconcile_all(db, actor=admin.username)


@router.get("/settings", response_model=TorSettingsModel)
async def get_tor_settings(
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "read")),
):
    return await tor_operation.get_settings(db)


@router.put("/settings", response_model=TorSettingsModel)
async def update_tor_settings(
    model: TorSettingsModel,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "update")),
):
    return await tor_operation.update_settings(db, model)
