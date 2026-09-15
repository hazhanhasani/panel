import asyncio
import re
import time
import uuid
from datetime import UTC, datetime as dt

from BluePanelNodeBridge import NodeAPIError
from BluePanelNodeBridge.common import service_pb2 as service
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import on_startup
from app.core.manager import core_manager
from app.db import GetDB, TorLocation, TorLocationEvent, TorSettings
from app.db.crud.node import get_node_by_id
from app.models.protocol import ProxyProtocol
from app.models.tor import TorLocationCreate, TorLocationResponse, TorLocationUpdate, TorSettingsModel, TorSummary
from app.node import node_manager
from app.utils.logger import get_logger

logger = get_logger("tor-operation")
_SLUG_RE = re.compile(r"[^a-z0-9-]+")
_reconcile_lock = asyncio.Lock()


def _country_flag(code: str) -> str:
    code = code.upper()
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)


def _safe_slug(value: str) -> str:
    value = _SLUG_RE.sub("-", value.lower().strip()).strip("-")
    return value[:64] or "location"


def _from_unix(value: int) -> dt | None:
    return dt.fromtimestamp(value, UTC) if value and value > 0 else None


class TorOperation:
    async def get_settings(self, db: AsyncSession) -> TorSettings:
        settings = await db.get(TorSettings, 1)
        if settings is None:
            settings = TorSettings(id=1)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    async def update_settings(self, db: AsyncSession, model: TorSettingsModel) -> TorSettings:
        settings = await self.get_settings(db)
        for key, value in model.model_dump().items():
            setattr(settings, key, value)
        settings.updated_at = dt.now(UTC)
        await db.commit()
        await db.refresh(settings)
        return settings

    async def _event(
        self,
        db: AsyncSession,
        *,
        location: TorLocation | None,
        node_id: int,
        actor: str,
        action: str,
        result: str = "success",
        detail: str | None = None,
        started: float | None = None,
    ) -> None:
        duration_ms = int((time.monotonic() - started) * 1000) if started is not None else None
        db.add(
            TorLocationEvent(
                location_id=location.id if location else None,
                node_id=node_id,
                actor=actor,
                action=action,
                result=result,
                detail=detail,
                duration_ms=duration_ms,
            )
        )

    async def list_locations(self, db: AsyncSession, node_id: int | None = None) -> list[TorLocation]:
        stmt = select(TorLocation).order_by(TorLocation.sort_order, TorLocation.display_name, TorLocation.id)
        if node_id is not None:
            stmt = stmt.where(TorLocation.node_id == node_id)
        return list((await db.execute(stmt)).scalars().all())

    async def get_location(self, db: AsyncSession, location_id: str) -> TorLocation:
        location = await db.get(TorLocation, location_id)
        if location is None:
            raise KeyError("Tor location not found")
        return location

    async def summary(self, db: AsyncSession) -> TorSummary:
        locations = await self.list_locations(db)
        offline_states = {"tor_down", "xray_error", "unreachable", "error", "cleanup_failed"}
        return TorSummary(
            total=len(locations),
            healthy=sum(item.health_status == "healthy" for item in locations),
            degraded=sum(item.health_status in {"degraded", "country_mismatch"} for item in locations),
            offline=sum(item.health_status in offline_states for item in locations),
            disabled=sum(not item.enabled or item.health_status == "disabled" for item in locations),
            node_count=len({item.node_id for item in locations}),
            pending=sum(item.sync_status != "synced" for item in locations),
        )

    async def _resolve_base_inbound(self, node_id: int, requested: str | None, protocol: str) -> tuple[str, str | None]:
        async with GetDB() as db:
            db_node = await get_node_by_id(db, node_id, load_usage_logs=False)
        if db_node is None:
            raise ValueError("Node not found")
        core = await core_manager.get_core(db_node.core_config_id or 1)
        if core is None:
            raise ValueError("Node has no usable core configuration")
        inbounds = getattr(core, "inbounds_by_tag", {})
        if requested:
            inbound = inbounds.get(requested)
            if inbound is None:
                raise ValueError("Base inbound tag is not available on this node core")
            if str(inbound.get("protocol", "")).lower() != protocol.lower():
                raise ValueError("Base inbound protocol does not match requested protocol")
            return requested, inbound.get("tls")
        for tag, inbound in inbounds.items():
            if str(inbound.get("protocol", "")).lower() == protocol.lower():
                return tag, inbound.get("tls")
        raise ValueError(f"Node core has no {protocol} inbound suitable for Tor location")

    async def _bridge(self, db: AsyncSession, node_id: int):
        db_node = await get_node_by_id(db, node_id, load_usage_logs=False)
        if db_node is None:
            raise ValueError("Node not found")
        bridge = await node_manager.get_node(node_id)
        if bridge is None:
            bridge = await node_manager.update_node(db_node)
        return bridge

    @staticmethod
    def _spec(location: TorLocation) -> service.TorLocationSpec:
        return service.TorLocationSpec(
            id=location.id,
            slug=location.slug,
            display_name=location.display_name,
            country_code=location.country_code,
            enabled=location.enabled,
            subscription_enabled=location.subscription_enabled,
            sort_order=location.sort_order,
            base_inbound_tag=location.base_inbound_tag,
            xray_inbound_port=location.xray_inbound_port or 0,
            xray_inbound_tag=location.xray_inbound_tag or "",
            xray_outbound_tag=location.xray_outbound_tag or "",
            xray_rule_tag=location.xray_rule_tag or "",
            tor_socks_port=location.tor_socks_port or 0,
            tor_control_port=location.tor_control_port or 0,
            auto_repair=location.auto_repair,
        )

    @staticmethod
    def _apply_actual(location: TorLocation, actual: service.TorLocation) -> None:
        location.slug = actual.slug or location.slug
        location.display_name = actual.display_name or location.display_name
        location.country_code = (actual.country_code or location.country_code).upper()
        location.enabled = actual.enabled
        location.subscription_enabled = actual.subscription_enabled
        location.sort_order = actual.sort_order
        location.base_inbound_tag = actual.base_inbound_tag or location.base_inbound_tag
        location.xray_inbound_port = actual.xray_inbound_port or None
        location.xray_inbound_tag = actual.xray_inbound_tag or None
        location.xray_outbound_tag = actual.xray_outbound_tag or None
        location.xray_rule_tag = actual.xray_rule_tag or None
        location.tor_socks_port = actual.tor_socks_port or None
        location.tor_control_port = actual.tor_control_port or None
        location.tor_data_directory = actual.tor_data_directory or None
        location.desired_country = actual.desired_country or location.country_code
        location.detected_country = actual.detected_country or None
        location.detected_exit_ip = actual.detected_exit_ip or None
        location.health_status = actual.health_status or "error"
        location.process_status = actual.process_status or "stopped"
        location.latency_ms = actual.latency_ms
        location.restart_attempts = actual.restart_attempts
        location.last_checked_at = _from_unix(actual.last_checked_at)
        location.last_healthy_at = _from_unix(actual.last_healthy_at)
        location.last_error = actual.last_error or None
        location.sync_status = "synced"
        location.updated_at = dt.now(UTC)
        if location.health_status == "healthy":
            location.unavailable_since = None
        elif location.unavailable_since is None:
            location.unavailable_since = dt.now(UTC)

    async def create_location(
        self, db: AsyncSession, model: TorLocationCreate, actor: str
    ) -> TorLocation:
        settings = await self.get_settings(db)
        if not settings.feature_enabled:
            raise PermissionError("Tor Multi-Exit is disabled in settings")

        db_node = await get_node_by_id(db, model.node_id, load_usage_logs=False)
        if db_node is None:
            raise ValueError("Node not found")
        protocol = model.protocol.strip().lower()
        if ProxyProtocol.from_value(protocol) is None:
            raise ValueError("Unsupported protocol")
        base_tag, detected_security = await self._resolve_base_inbound(
            model.node_id, model.base_inbound_tag, protocol
        )
        country = model.country_code.upper()
        location_id = str(uuid.uuid4())
        slug = _safe_slug(model.slug or f"{country.lower()}-{location_id[:8]}")
        location = TorLocation(
            id=location_id,
            node_id=model.node_id,
            slug=slug,
            display_name=model.display_name or country,
            country_code=country,
            base_inbound_tag=base_tag,
            flag=_country_flag(country),
            protocol=protocol,
            security=model.security or detected_security,
            enabled=True,
            subscription_enabled=model.subscription_enabled,
            auto_health_check=model.auto_health_check,
            auto_repair=model.auto_repair,
            sort_order=model.sort_order,
            xray_inbound_port=model.xray_inbound_port,
            tor_socks_port=model.tor_socks_port,
            tor_control_port=model.tor_control_port,
            desired_state="enabled",
            sync_status="pending",
            desired_country=country,
            health_status="creating",
            process_status="stopped",
        )
        db.add(location)
        await db.flush()
        started = time.monotonic()
        await self._event(db, location=location, node_id=location.node_id, actor=actor, action="create_requested")
        await db.commit()

        try:
            bridge = await self._bridge(db, location.node_id)
            actual = await bridge.create_tor_location(self._spec(location))
            self._apply_actual(location, actual)
            await self._event(
                db, location=location, node_id=location.node_id, actor=actor, action="created", started=started
            )
        except Exception as exc:
            location.sync_status = "pending"
            location.last_error = str(exc)
            location.health_status = "unreachable"
            await self._event(
                db,
                location=location,
                node_id=location.node_id,
                actor=actor,
                action="create_deferred",
                result="pending",
                detail=str(exc),
                started=started,
            )
            logger.warning("Tor location create deferred id=%s node=%s: %s", location.id, location.node_id, exc)
        await db.commit()
        await db.refresh(location)
        return location

    async def update_location(
        self, db: AsyncSession, location_id: str, model: TorLocationUpdate, actor: str
    ) -> TorLocation:
        location = await self.get_location(db, location_id)
        data = model.model_dump(exclude_unset=True)
        if "country_code" in data and data["country_code"]:
            data["country_code"] = data["country_code"].upper()
            location.desired_country = data["country_code"]
            location.flag = _country_flag(data["country_code"])
        if "base_inbound_tag" in data or "protocol" in data:
            protocol = data.get("protocol") or location.protocol
            if ProxyProtocol.from_value(str(protocol).lower()) is None:
                raise ValueError("Unsupported protocol")
            base, security = await self._resolve_base_inbound(
                location.node_id, data.get("base_inbound_tag") or location.base_inbound_tag, str(protocol)
            )
            data["base_inbound_tag"] = base
            data["protocol"] = str(protocol).lower()
            if data.get("security") is None and security:
                data["security"] = security
        for key, value in data.items():
            setattr(location, key, value)
        location.sync_status = "pending"
        location.updated_at = dt.now(UTC)
        await self._event(db, location=location, node_id=location.node_id, actor=actor, action="update_requested")
        await db.commit()
        return await self.reconcile_location(db, location, actor=actor, action="updated")

    async def set_enabled(self, db: AsyncSession, location_id: str, enabled: bool, actor: str) -> TorLocation:
        location = await self.get_location(db, location_id)
        location.enabled = enabled
        location.desired_state = "enabled" if enabled else "disabled"
        location.sync_status = "pending"
        if not enabled:
            location.health_status = "disabled"
        await self._event(
            db,
            location=location,
            node_id=location.node_id,
            actor=actor,
            action="enable_requested" if enabled else "disable_requested",
        )
        await db.commit()
        return await self.reconcile_location(db, location, actor=actor, action="enabled" if enabled else "disabled")

    async def action(self, db: AsyncSession, location_id: str, action: str, actor: str) -> TorLocation:
        location = await self.get_location(db, location_id)
        bridge = await self._bridge(db, location.node_id)
        methods = {
            "restart": bridge.restart_tor_location,
            "new_ip": bridge.new_tor_identity,
            "repair": bridge.repair_tor_location,
            "test": bridge.test_tor_location,
            "health": bridge.get_tor_health,
        }
        if action not in methods:
            raise ValueError("Unsupported Tor action")
        started = time.monotonic()
        try:
            actual = await methods[action](location.id)
            self._apply_actual(location, actual)
            await self._event(
                db, location=location, node_id=location.node_id, actor=actor, action=action, started=started
            )
        except Exception as exc:
            location.last_error = str(exc)
            location.sync_status = "pending" if action in {"repair", "restart"} else location.sync_status
            await self._event(
                db,
                location=location,
                node_id=location.node_id,
                actor=actor,
                action=action,
                result="error",
                detail=str(exc),
                started=started,
            )
            await db.commit()
            raise
        await db.commit()
        await db.refresh(location)
        return location

    async def delete_location(
        self, db: AsyncSession, location_id: str, actor: str, purge_data: bool = False
    ) -> None:
        location = await self.get_location(db, location_id)
        location.desired_state = "deleted"
        location.sync_status = "pending"
        location.subscription_enabled = False
        await self._event(db, location=location, node_id=location.node_id, actor=actor, action="delete_requested")
        await db.commit()
        started = time.monotonic()
        try:
            bridge = await self._bridge(db, location.node_id)
            await bridge.delete_tor_location(location.id, purge_data=purge_data)
            await self._event(
                db, location=location, node_id=location.node_id, actor=actor, action="deleted", started=started
            )
            await db.execute(delete(TorLocation).where(TorLocation.id == location.id))
        except Exception as exc:
            location.last_error = str(exc)
            location.sync_status = "pending"
            location.health_status = "deleting"
            await self._event(
                db,
                location=location,
                node_id=location.node_id,
                actor=actor,
                action="delete_deferred",
                result="pending",
                detail=str(exc),
                started=started,
            )
            logger.warning("Tor location delete deferred id=%s: %s", location.id, exc)
        await db.commit()

    async def reconcile_location(
        self, db: AsyncSession, location: TorLocation, actor: str = "system", action: str = "reconciled"
    ) -> TorLocation:
        if location.desired_state == "deleted":
            await self.delete_location(db, location.id, actor=actor)
            raise KeyError("Tor location deleted")
        try:
            bridge = await self._bridge(db, location.node_id)
            if location.desired_state == "disabled" or not location.enabled:
                actual = await bridge.disable_tor_location(location.id)
            else:
                try:
                    actual = await bridge.get_tor_location(location.id)
                    actual = await bridge.update_tor_location(self._spec(location))
                except NodeAPIError as exc:
                    if getattr(exc, "status", None) not in {404, "404"}:
                        raise
                    actual = await bridge.create_tor_location(self._spec(location))
            self._apply_actual(location, actual)
            await self._event(db, location=location, node_id=location.node_id, actor=actor, action=action)
        except Exception as exc:
            location.sync_status = "pending"
            location.last_error = str(exc)
            if location.health_status not in {"disabled", "deleting"}:
                location.health_status = "unreachable"
            await self._event(
                db,
                location=location,
                node_id=location.node_id,
                actor=actor,
                action=action,
                result="pending",
                detail=str(exc),
            )
            logger.warning("Tor reconcile deferred id=%s node=%s: %s", location.id, location.node_id, exc)
        await db.commit()
        await db.refresh(location)
        return location

    async def reconcile_all(self, db: AsyncSession, actor: str = "system") -> list[TorLocation]:
        if _reconcile_lock.locked():
            return await self.list_locations(db)
        async with _reconcile_lock:
            locations = await self.list_locations(db)
            results: list[TorLocation] = []
            for location in locations:
                if location.desired_state == "deleted":
                    try:
                        await self.delete_location(db, location.id, actor=actor)
                    except Exception:
                        logger.exception("Failed to reconcile deletion for Tor location %s", location.id)
                    continue
                results.append(await self.reconcile_location(db, location, actor=actor))
            return results

    async def recent_events(self, db: AsyncSession, location_id: str, limit: int = 100) -> list[TorLocationEvent]:
        stmt = (
            select(TorLocationEvent)
            .where(TorLocationEvent.location_id == location_id)
            .order_by(TorLocationEvent.created_at.desc(), TorLocationEvent.id.desc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())


async def _tor_reconcile_loop() -> None:
    while True:
        try:
            async with GetDB() as db:
                settings = await tor_operation.get_settings(db)
                interval = max(30, settings.health_check_interval)
                if settings.feature_enabled:
                    await tor_operation.reconcile_all(db)
        except Exception:
            logger.exception("Tor background reconciliation failed")
            interval = 60
        await asyncio.sleep(interval)


@on_startup
async def start_tor_reconciliation() -> None:
    async with GetDB() as db:
        settings = await tor_operation.get_settings(db)
        if settings.feature_enabled:
            await tor_operation.reconcile_all(db)
    asyncio.create_task(_tor_reconcile_loop())


tor_operation = TorOperation()
