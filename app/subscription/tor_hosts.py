from __future__ import annotations

from datetime import UTC, datetime as dt

from sqlalchemy import select

from app.core.hosts import host_manager
from app.db import GetDB, TorLocation, TorSettings
from app.db.models import Node
from app.models.subscription import SubscriptionInboundData

_installed = False


def _is_exposed(location: TorLocation, settings: TorSettings, now: dt) -> bool:
    if not settings.feature_enabled:
        return False
    if not location.enabled or not location.subscription_enabled or location.desired_state != "enabled":
        return False
    if settings.subscription_policy == "always":
        return True
    if settings.subscription_policy == "healthy":
        return location.health_status == "healthy"
    # Safe default: keep an enabled location during transient failure, and hide it
    # only after the configured grace period has elapsed.
    if location.health_status == "healthy" or location.unavailable_since is None:
        return True
    unavailable_since = location.unavailable_since
    if unavailable_since.tzinfo is None:
        unavailable_since = unavailable_since.replace(tzinfo=UTC)
    return (now - unavailable_since).total_seconds() < settings.unhealthy_grace_period


async def _tor_subscription_variants(
    base_hosts: dict[int, SubscriptionInboundData],
) -> list[SubscriptionInboundData]:
    if not base_hosts:
        return []
    async with GetDB() as db:
        settings = await db.get(TorSettings, 1)
        if settings is None or not settings.feature_enabled:
            return []
        rows = await db.execute(
            select(TorLocation, Node)
            .join(Node, Node.id == TorLocation.node_id)
            .where(TorLocation.subscription_enabled.is_(True))
            .order_by(TorLocation.sort_order, TorLocation.display_name, TorLocation.id)
        )
        locations = list(rows.all())

    now = dt.now(UTC)
    # HostManager is already priority-sorted. One canonical public host per base
    # inbound yields one subscription entry per Tor location, matching the UI.
    first_host_by_inbound: dict[str, SubscriptionInboundData] = {}
    for host in base_hosts.values():
        first_host_by_inbound.setdefault(host.inbound_tag, host)

    variants: list[SubscriptionInboundData] = []
    for location, node in locations:
        if not _is_exposed(location, settings, now):
            continue
        if not location.xray_inbound_port:
            continue
        base = first_host_by_inbound.get(location.base_inbound_tag)
        if base is None:
            continue
        # Keep inbound_tag canonical so the existing subscription permission check
        # continues to use the user's real BluePanel inbound membership. Node-side
        # sync expands that membership to this Tor inbound with the same credential.
        remark = f"{location.flag or ''} {location.display_name} - BluePanel".strip()
        variants.append(
            base.model_copy(
                deep=True,
                update={
                    "remark": remark,
                    "address": [node.address],
                    "port": [location.xray_inbound_port],
                    "priority": base.priority + location.sort_order,
                },
            )
        )
    return variants


def install_tor_host_overlay() -> None:
    global _installed
    if _installed:
        return
    original = host_manager.get_hosts

    async def get_hosts_with_tor() -> dict[int | str, SubscriptionInboundData]:
        base_hosts = await original()
        output: dict[int | str, SubscriptionInboundData] = dict(base_hosts)
        variants = await _tor_subscription_variants(base_hosts)
        for index, variant in enumerate(variants):
            output[f"tor:{index}:{variant.remark}"] = variant
        return output

    # HostManager._reset_cache expects this attribute on get_hosts.
    get_hosts_with_tor.cache = original.cache  # type: ignore[attr-defined]
    host_manager.get_hosts = get_hosts_with_tor  # type: ignore[method-assign]
    _installed = True
