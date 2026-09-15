import ipaddress
import os
import socket
import ssl

import uvicorn
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from app import create_app  # noqa: F401
from app.nats import require_nats_if_multiworker
from app.utils.logger import LOGGING_CONFIG, get_logger
from config import logging_settings, runtime_settings, server_settings

logger = get_logger("uvicorn-main")

workers = server_settings.workers or 1
if workers < 1:
    logger.warning(f"Invalid UVICORN_WORKERS value '{server_settings.workers}', defaulting to 1.")
    workers = 1
elif workers > 1:
    require_nats_if_multiworker(workers)


def check_and_modify_ip(ip_address: str) -> str:
    """Validate and preserve the configured bind host.

    BluePanel is commonly installed in Docker with host networking. In that setup
    ``0.0.0.0`` is intentional and must not be rewritten to localhost, otherwise
    the installer reports success while the dashboard is unreachable remotely.
    """
    host = str(ip_address or "").strip()
    if not host:
        raise ValueError("UVICORN_HOST cannot be empty")

    if host == "localhost":
        return host

    try:
        ipaddress.ip_address(host)
    except ValueError:
        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError(f"Invalid UVICORN_HOST: {host}") from exc

    return host


def validate_cert_and_key(cert_file_path, key_file_path, ca_type: str = "public"):
    if not os.path.isfile(cert_file_path):
        raise ValueError(f"SSL certificate file '{cert_file_path}' does not exist.")
    if not os.path.isfile(key_file_path):
        raise ValueError(f"SSL key file '{key_file_path}' does not exist.")

    try:
        context = ssl.create_default_context()
        context.load_cert_chain(certfile=cert_file_path, keyfile=key_file_path)
    except ssl.SSLError as e:
        raise ValueError(f"SSL Error: {e}")

    try:
        with open(cert_file_path, "rb") as cert_file:
            cert_data = cert_file.read()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        if ca_type == "public" and cert.issuer == cert.subject:
            raise ValueError("The certificate is self-signed and not issued by a trusted CA.")

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Certificate verification failed: {e}")


if __name__ == "__main__":
    valid_ca_types = ("public", "private")
    ca_type = server_settings.ssl_ca_type
    if ca_type not in valid_ca_types:
        logger.warning(
            f"Invalid UVICORN_SSL_CA_TYPE value '{server_settings.ssl_ca_type}'. "
            f"Expected one of {valid_ca_types}. Defaulting to 'public'."
        )
        ca_type = "public"

    bind_args = {}

    if server_settings.ssl_certfile and server_settings.ssl_keyfile:
        validate_cert_and_key(server_settings.ssl_certfile, server_settings.ssl_keyfile, ca_type=ca_type)

        bind_args["ssl_certfile"] = server_settings.ssl_certfile
        bind_args["ssl_keyfile"] = server_settings.ssl_keyfile

        if server_settings.uds:
            bind_args["uds"] = server_settings.uds
        else:
            bind_args["host"] = check_and_modify_ip(server_settings.host)
            bind_args["port"] = server_settings.port

    else:
        if server_settings.uds:
            bind_args["uds"] = server_settings.uds
        else:
            host = check_and_modify_ip(server_settings.host)
            if host in {"0.0.0.0", "::"}:
                logger.warning(
                    "BluePanel is listening on all interfaces without application-level TLS. "
                    "Use a firewall and preferably terminate HTTPS at a trusted reverse proxy."
                )
            bind_args["host"] = host
            bind_args["port"] = server_settings.port

    if runtime_settings.debug:
        bind_args["uds"] = None
        bind_args["host"] = "0.0.0.0"

    effective_log_level = logging_settings.level
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        LOGGING_CONFIG["loggers"][logger_name]["level"] = effective_log_level

    uvicorn.run(
        "main:create_app",
        factory=True,
        **bind_args,
        workers=workers,
        reload=runtime_settings.debug,
        log_config=LOGGING_CONFIG,
        log_level=effective_log_level.lower(),
        loop=server_settings.loop,
        proxy_headers=server_settings.proxy_headers,
        forwarded_allow_ips=server_settings.forwarded_allow_ips,
    )
