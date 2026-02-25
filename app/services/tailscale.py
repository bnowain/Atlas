"""Tailscale auto-detection for remote access over Tailscale VPN."""

from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)

_tailscale_ip: str | None = None
_tailscale_hostname: str | None = None


def detect_tailscale() -> tuple[str | None, str | None]:
    """Detect Tailscale IPv4 address and DNS hostname.

    Runs ``tailscale status --json`` once at startup and caches the result.
    Returns (ip, hostname) — both None if Tailscale is not available.
    """
    global _tailscale_ip, _tailscale_hostname

    if _tailscale_ip is not None:
        return _tailscale_ip, _tailscale_hostname

    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.debug("Tailscale not running (exit %d)", result.returncode)
            return None, None

        data = json.loads(result.stdout)

        # Self node is keyed by the current node's public key
        self_key = data.get("Self", {})
        tailscale_ips = self_key.get("TailscaleIPs", [])
        dns_name = self_key.get("DNSName", "")

        # Pick the first IPv4 address (100.x.x.x)
        ipv4 = None
        for ip in tailscale_ips:
            if "." in ip:  # IPv4
                ipv4 = ip
                break

        # DNSName usually ends with a trailing dot — strip it
        hostname = dns_name.rstrip(".") if dns_name else None

        _tailscale_ip = ipv4
        _tailscale_hostname = hostname
        return ipv4, hostname

    except FileNotFoundError:
        logger.debug("Tailscale CLI not found — remote access disabled")
        return None, None
    except subprocess.TimeoutExpired:
        logger.debug("Tailscale CLI timed out")
        return None, None
    except Exception as e:
        logger.debug("Tailscale detection failed: %s", e)
        return None, None


def get_tailscale_origins(ports: list[int]) -> list[str]:
    """Return CORS origin strings for Tailscale IP and hostname.

    If Tailscale is not detected, returns an empty list.
    """
    ip, hostname = detect_tailscale()
    origins: list[str] = []

    if ip:
        for port in ports:
            origins.append(f"http://{ip}:{port}")
    if hostname:
        for port in ports:
            origins.append(f"http://{hostname}:{port}")

    return origins
