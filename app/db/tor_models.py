from datetime import UTC, datetime as dt

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.compiles_types import SqliteCompatibleBigInteger


class TorLocation(Base):
    __tablename__ = "tor_locations"
    __table_args__ = (
        UniqueConstraint("node_id", "slug", name="uq_tor_locations_node_slug"),
        UniqueConstraint("node_id", "xray_inbound_port", name="uq_tor_locations_node_xray_port"),
        UniqueConstraint("node_id", "tor_socks_port", name="uq_tor_locations_node_socks_port"),
        UniqueConstraint("node_id", "tor_control_port", name="uq_tor_locations_node_control_port"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[int] = mapped_column(
        SqliteCompatibleBigInteger, ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    base_inbound_tag: Mapped[str] = mapped_column(String(256))

    flag: Mapped[str | None] = mapped_column(String(16), default=None)
    protocol: Mapped[str] = mapped_column(String(32), default="vless")
    security: Mapped[str | None] = mapped_column(String(32), default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    subscription_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    auto_health_check: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    auto_repair: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    xray_inbound_port: Mapped[int | None] = mapped_column(Integer, default=None)
    xray_inbound_tag: Mapped[str | None] = mapped_column(String(256), default=None)
    xray_outbound_tag: Mapped[str | None] = mapped_column(String(256), default=None)
    xray_rule_tag: Mapped[str | None] = mapped_column(String(256), default=None)
    tor_socks_port: Mapped[int | None] = mapped_column(Integer, default=None)
    tor_control_port: Mapped[int | None] = mapped_column(Integer, default=None)
    tor_data_directory: Mapped[str | None] = mapped_column(String(1024), default=None)

    desired_state: Mapped[str] = mapped_column(String(32), default="enabled", server_default="enabled", index=True)
    sync_status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending", index=True)
    desired_country: Mapped[str | None] = mapped_column(String(2), default=None)
    detected_country: Mapped[str | None] = mapped_column(String(2), default=None)
    detected_exit_ip: Mapped[str | None] = mapped_column(String(64), default=None)
    health_status: Mapped[str] = mapped_column(String(32), default="creating", server_default="creating", index=True)
    process_status: Mapped[str] = mapped_column(String(32), default="stopped", server_default="stopped")
    latency_ms: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    restart_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    last_checked_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), default=None)
    last_healthy_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), default=None)
    unavailable_since: Mapped[dt | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default_factory=lambda: dt.now(UTC), init=False)
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default_factory=lambda: dt.now(UTC), init=False)


class TorSettings(Base):
    __tablename__ = "tor_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    feature_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    auto_repair: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    country_verification: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    health_check_interval: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    max_restart_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    restart_backoff: Mapped[str] = mapped_column(String(128), default="60,120,300,600,1800", server_default="60,120,300,600,1800")
    xray_port_start: Mapped[int] = mapped_column(Integer, default=31000, server_default="31000")
    xray_port_end: Mapped[int] = mapped_column(Integer, default=31999, server_default="31999")
    socks_port_start: Mapped[int] = mapped_column(Integer, default=19000, server_default="19000")
    socks_port_end: Mapped[int] = mapped_column(Integer, default=19999, server_default="19999")
    control_port_start: Mapped[int] = mapped_column(Integer, default=20000, server_default="20000")
    control_port_end: Mapped[int] = mapped_column(Integer, default=20999, server_default="20999")
    subscription_policy: Mapped[str] = mapped_column(String(32), default="grace", server_default="grace")
    unhealthy_grace_period: Mapped[int] = mapped_column(Integer, default=900, server_default="900")
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default_factory=lambda: dt.now(UTC), init=False)


class TorLocationEvent(Base):
    __tablename__ = "tor_location_events"

    id: Mapped[int] = mapped_column(SqliteCompatibleBigInteger, primary_key=True, init=False, autoincrement=True)
    location_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    node_id: Mapped[int] = mapped_column(SqliteCompatibleBigInteger, index=True)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64), index=True)
    result: Mapped[str] = mapped_column(String(32), default="success")
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), default_factory=lambda: dt.now(UTC), init=False, index=True)
