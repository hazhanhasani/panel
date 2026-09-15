"""add Tor multi-exit persistence

Revision ID: 91b2a7f43c10
Revises: 48a6bcb8bba1
Create Date: 2026-09-15
"""

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
    op.execute(
        sa.text(
            "INSERT INTO tor_settings (id, feature_enabled, auto_repair, country_verification, health_check_interval, "
            "max_restart_attempts, restart_backoff, xray_port_start, xray_port_end, socks_port_start, socks_port_end, "
            "control_port_start, control_port_end, subscription_policy, unhealthy_grace_period, updated_at) "
            "VALUES (1, false, true, true, 60, 5, '60,120,300,600,1800', 31000, 31999, 19000, 19999, "
            "20000, 20999, 'grace', 900, CURRENT_TIMESTAMP)"
        )
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
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
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
