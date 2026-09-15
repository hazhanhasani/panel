from .base import BaseSubscription
from .clash import ClashConfiguration, ClashMetaConfiguration
from .links import StandardLinks
from .outline import OutlineConfiguration
from .singbox import SingBoxConfiguration
from .wireguard import WireGuardConfiguration
from .xray import XrayConfiguration

__all__ = [
    "BaseSubscription",
    "ClashConfiguration",
    "ClashMetaConfiguration",
    "OutlineConfiguration",
    "SingBoxConfiguration",
    "StandardLinks",
    "WireGuardConfiguration",
    "XrayConfiguration",
]

# Installed after the subscription classes are initialized to avoid circular
# imports through app.core.hosts -> app.subscription.base.
from .tor_hosts import install_tor_host_overlay  # noqa: E402

install_tor_host_overlay()
