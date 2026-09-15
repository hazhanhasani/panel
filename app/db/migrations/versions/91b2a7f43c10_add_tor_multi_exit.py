"""add Tor multi-exit persistence

Revision ID: 91b2a7f43c10
Revises: 48a6bcb8bba1
Create Date: 2026-09-15
"""

from datetime import UTC, datetime as dt

import sqlalchemy as sa
from alembic import op

revision = "91b2a7f43c10"
down_revision = "48a6bcb8bba1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tor_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("feature_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_repair", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("country_verification", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("health_check_interval", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_restart_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("restart_backoff", sa.String(length=128), nullable=False, server_default="60,120,300,600,1800"),
        sa.Column("xray_port_start", sa.Integer(), nullable=False, server_default="31000"),
        sa.Column("xray_port_end", sa.Integer(), nullable=False, server_default="31999"),
        sa.Column("socks_port_start", sa.Integer(), nullable=False, server_default="19000"),
        sa.Column("socks_port_end", sa.Integer(), nullable=False, server_default="19999"),
        sa.Column("control_port_start", sa.Integer(), nullable=False, server_default="20000"),
        sa.Column("control_port_end", sa.Integer(), nullable=False, server_default="20999"),
        sa.Column("subscription_policy", sa.String(length=32), nullable=False, server_default="grace"),
        sa.Column("unhealthy_grace_period", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    settings_table = sa.table(
        "tor_settings",
        sa.column("id", sa.Integer()),
        sa.column("feature_enabled", sa.Boolean()),
        sa.column("auto_repair", sa.Boolean()),
        sa.column("country_verification", sa.Boolean()),
        sa.column("health_check_interval", sa.Integer()),
        sa.column("max_restart_attempts", sa.Integer()),
        sa.column("restart_backoff", sa.String()),
        sa.column("xray_port_start", sa.Integer()),
        sa.column("xray_port_end", sa.Integer()),
        sa.column("socks_port_start", sa.Integer()),
        sa.column("socks_port_end", sa.Integer()),
        sa.column("control_port_start", sa.Integer()),
        sa.column("control_port_end", sa.Integer()),
        sa.column("subscription_policy", sa.String()),
        sa.column("unhealthy_grace_period", sa.Integer()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        settings_table,
        [
            {
                "id": 1,
                "feature_enabled": False,
                "auto_repair": True,
                "country_verification": True,
                "health_check_interval": 60,
                "max_restart_attempts": 5,
                "restart_backoff": "60,120,300,600,1800",
                "xray_port_start": 31000,
                "xray_port_end": 31999,
                "socks_port_start": 19000,
                "socks_port_end": 19999,
                "control_port_start": 20000,
                "control_port_end": 20999,
                "subscription_policy": "grace",
                "unhealthy_grace_period": 900,
                "updated_at": dt.now(UTC),
            }
        ],
    )

    op.create_table(
        "tor_locations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("node_id", sa.BigInteger(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("base_inbound_tag", sa.String(length=256), nullable=False),
        sa.Column("flag", sa.String(length=16), nullable=True),
        sa.Column("protocol", sa.String(length=32), nullable=False, server_default="vless"),
        sa.Column("security", sa.String(length=32), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("subscription_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_health_check", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_repair", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xray_inbound_port", sa.Integer(), nullable=True),
        sa.Column("xray_inbound_tag", sa.String(length=256), nullable=True),
        sa.Column("xray_outbound_tag", sa.String(length=256), nullable=True),
        sa.Column("xray_rule_tag", sa.String(length=256), nullable=True),
        sa.Column("tor_socks_port", sa.Integer(), nullable=True),
        sa.Column("tor_control_port", sa.Integer(), nullable=True),
        sa.Column("tor_data_directory", sa.String(length=1024), nullable=True),
        sa.Column("desired_state", sa.String(length=32), nullable=False, server_default="enabled"),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("desired_country", sa.String(length=2), nullable=True),
        sa.Column("detected_country", sa.String(length=2), nullable=True),
        sa.Column("detected_exit_ip", sa.String(length=64), nullable=True),
        sa.Column("health_status", sa.String(length=32), nullable=False, server_default="creating"),
        sa.Column("process_status", sa.String(length=32), nullable=False, server_default="stopped"),
        sa.Column("latency_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("restart_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_healthy_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unavailable_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("node_id", "slug", name="uq_tor_locations_node_slug"),
        sa.UniqueConstraint("node_id", "xray_inbound_port", name="uq_tor_locations_node_xray_port"),
        sa.UniqueConstraint("node_id", "tor_socks_port", name="uq_tor_locations_node_socks_port"),
        sa.UniqueConstraint("node_id", "tor_control_port", name="uq_tor_locations_node_control_port"),
    )
    op.create_index("ix_tor_locations_node_id", "tor_locations", ["node_id"])
    op.create_index("ix_tor_locations_country_code", "tor_locations", ["country_code"])
    op.create_index("ix_tor_locations_health_status", "tor_locations", ["health_status"])
    op.create_index("ix_tor_locations_sync_status", "tor_locations", ["sync_status"])
    op.create_index("ix_tor_locations_desired_state", "tor_locations", ["desired_state"])

    op.create_table(
        "tor_location_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("node_id", sa.BigInteger(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tor_location_events_location_id", "tor_location_events", ["location_id"])
    op.create_index("ix_tor_location_events_node_id", "tor_location_events", ["node_id"])
    op.create_index("ix_tor_location_events_action", "tor_location_events", ["action"])
    op.create_index("ix_tor_location_events_created_at", "tor_location_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("tor_location_events")
    op.drop_table("tor_locations")
    op.drop_table("tor_settings")
