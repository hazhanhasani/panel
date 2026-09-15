from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ISO_COUNTRY_CODES = frozenset(
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split()
)


class TorLocationCreate(BaseModel):
    node_id: int
    country_code: str
    display_name: str | None = None
    slug: str | None = None
    protocol: str = "vless"
    security: str | None = None
    base_inbound_tag: str | None = None
    subscription_enabled: bool = True
    auto_health_check: bool = True
    auto_repair: bool = True
    sort_order: int = 0
    xray_inbound_port: int | None = Field(default=None, ge=1, le=65535)
    tor_socks_port: int | None = Field(default=None, ge=1, le=65535)
    tor_control_port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in ISO_COUNTRY_CODES:
            raise ValueError("invalid ISO 3166-1 alpha-2 country code")
        return value


class TorLocationUpdate(BaseModel):
    display_name: str | None = None
    country_code: str | None = None
    protocol: str | None = None
    security: str | None = None
    base_inbound_tag: str | None = None
    subscription_enabled: bool | None = None
    auto_health_check: bool | None = None
    auto_repair: bool | None = None
    sort_order: int | None = None
    xray_inbound_port: int | None = Field(default=None, ge=1, le=65535)
    tor_socks_port: int | None = Field(default=None, ge=1, le=65535)
    tor_control_port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if value not in ISO_COUNTRY_CODES:
            raise ValueError("invalid ISO 3166-1 alpha-2 country code")
        return value


class TorLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_id: int
    slug: str
    display_name: str
    country_code: str
    flag: str | None
    protocol: str
    security: str | None
    enabled: bool
    subscription_enabled: bool
    auto_health_check: bool
    auto_repair: bool
    sort_order: int
    base_inbound_tag: str
    xray_inbound_port: int | None
    xray_inbound_tag: str | None
    xray_outbound_tag: str | None
    xray_rule_tag: str | None
    tor_socks_port: int | None
    tor_control_port: int | None
    desired_country: str | None
    detected_country: str | None
    detected_exit_ip: str | None
    health_status: str
    process_status: str
    latency_ms: int
    restart_attempts: int
    desired_state: str
    sync_status: str
    last_checked_at: datetime | None
    last_healthy_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class TorSummary(BaseModel):
    total: int
    healthy: int
    degraded: int
    offline: int
    disabled: int
    node_count: int
    pending: int


class TorSettingsModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_enabled: bool = False
    auto_repair: bool = True
    country_verification: bool = True
    health_check_interval: int = Field(default=60, ge=15, le=3600)
    max_restart_attempts: int = Field(default=5, ge=1, le=20)
    restart_backoff: str = "60,120,300,600,1800"
    xray_port_start: int = Field(default=31000, ge=1, le=65535)
    xray_port_end: int = Field(default=31999, ge=1, le=65535)
    socks_port_start: int = Field(default=19000, ge=1, le=65535)
    socks_port_end: int = Field(default=19999, ge=1, le=65535)
    control_port_start: int = Field(default=20000, ge=1, le=65535)
    control_port_end: int = Field(default=20999, ge=1, le=65535)
    subscription_policy: Literal["always", "healthy", "grace"] = "grace"
    unhealthy_grace_period: int = Field(default=900, ge=0, le=86400)

    @model_validator(mode="after")
    def validate_ranges(self):
        ranges = (
            (self.xray_port_start, self.xray_port_end, "Xray"),
            (self.socks_port_start, self.socks_port_end, "SOCKS"),
            (self.control_port_start, self.control_port_end, "Control"),
        )
        for start, end, name in ranges:
            if start > end:
                raise ValueError(f"{name} port range start must be <= end")
        return self


class TorEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: str | None
    node_id: int
    actor: str
    action: str
    result: str
    detail: str | None
    duration_ms: int | None
    created_at: datetime
