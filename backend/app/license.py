"""
Offline RSA-2048 License Validation
====================================
The PRIVATE key stays on the developer's machine.
The PUBLIC key is embedded below for end-user verification.

Workflow:
  Developer:  python tools/keygen.py --generate          # creates keys/
              python tools/keygen.py --issue MACHINE_ID  # prints license key
  End-user:   launch.bat prompts for key → saved to .license
              Every launch validates silently in <1ms
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple

# ── Embed the PUBLIC key here after running: python tools/keygen.py --generate
# ── Leave as-is during development → developer mode (all licenses pass)
PUBLIC_KEY_PEM = b"DEV_MODE"

LICENSE_FILE = Path(__file__).parent.parent.parent / ".license"


def get_machine_id() -> str:
    """Stable hardware-based ID that survives reboots but not OS reinstalls."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["reg", "query",
                 r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography",
                 "/v", "MachineGuid"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "MachineGuid" in line:
                    return line.strip().split()[-1]
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2]
        else:
            p = Path("/etc/machine-id")
            if p.exists():
                return p.read_text().strip()
    except Exception:
        pass
    # Fallback: username + hostname (consistent per user account)
    import socket
    raw = f"{os.getlogin()}@{socket.gethostname()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def validate_license(key: str) -> Tuple[bool, str]:
    """
    Validate a license key string.
    Returns (is_valid: bool, message: str)
    """
    # Developer mode: no public key embedded yet
    if PUBLIC_KEY_PEM == b"DEV_MODE":
        return True, "Developer mode — license validation bypassed"

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.exceptions import InvalidSignature

        raw = base64.b64decode(key.replace("-", "").replace(" ", "").strip())
        if len(raw) < 257:
            return False, "License key too short"

        signature    = raw[-256:]
        payload_bytes = raw[:-256]
        payload      = json.loads(payload_bytes)

        # Machine check (skip for floating licenses)
        if not payload.get("floating"):
            machine_id = get_machine_id()
            if payload.get("machine_id") != machine_id:
                return False, (
                    f"License not valid for this machine.\n"
                    f"  Your Machine ID: {machine_id}\n"
                    f"  Contact support to transfer."
                )

        # Expiry check
        expiry_str = payload.get("expiry")
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.utcnow() > expiry:
                return False, f"License expired on {expiry.strftime('%Y-%m-%d')}"

        # RSA signature verification
        pub = load_pem_public_key(PUBLIC_KEY_PEM)
        pub.verify(signature, payload_bytes, padding.PKCS1v15(), hashes.SHA256())

        tier = payload.get("tier", "standard")
        exp  = expiry_str or "lifetime"
        return True, f"License valid — {tier.upper()} tier · expires {exp}"

    except InvalidSignature:
        return False, "Invalid license key — signature verification failed"
    except Exception as e:
        return False, f"License error: {e}"


def check_license_file() -> Tuple[bool, str]:
    """Check the saved .license file. Returns (ok, message)."""
    if not LICENSE_FILE.exists():
        return False, "no_license"
    key = LICENSE_FILE.read_text().strip()
    if not key or key == "UNLICENSED":
        return False, "no_license"
    return validate_license(key)


def save_license(key: str) -> Tuple[bool, str]:
    """Validate and save a license key. Returns (ok, message)."""
    ok, msg = validate_license(key)
    if ok:
        LICENSE_FILE.write_text(key.strip())
    return ok, msg
