"""
License Key Generator — DEVELOPER TOOL (never distribute this file)
====================================================================
Usage:
  python tools/keygen.py --generate                      # create RSA key pair (once)
  python tools/keygen.py --machine                       # print this machine's ID
  python tools/keygen.py --issue <machine_id>            # issue 1-year standard key
  python tools/keygen.py --issue <machine_id> --floating # floating (any machine) key
  python tools/keygen.py --issue <machine_id> --lifetime # no expiry
  python tools/keygen.py --verify <license_key>          # test a key

After --generate, copy the public key content into backend/app/license.py → PUBLIC_KEY_PEM
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

KEYS_DIR  = Path(__file__).parent / "keys"
PRIV_FILE = KEYS_DIR / "private.pem"
PUB_FILE  = KEYS_DIR / "public.pem"


def _require_crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import hashes, serialization
        return True
    except ImportError:
        print("ERROR: run  pip install cryptography  first")
        sys.exit(1)


def cmd_generate():
    _require_crypto()
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if PRIV_FILE.exists():
        print(f"Keys already exist at {KEYS_DIR}/  — delete manually to regenerate.")
        return

    print("Generating RSA-2048 key pair...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    PRIV_FILE.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(b""),
        )
    )
    PUB_FILE.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"[OK] Private key → {PRIV_FILE}  (KEEP SECRET)")
    print(f"[OK] Public key  → {PUB_FILE}")
    print()
    print("Copy this into  backend/app/license.py → PUBLIC_KEY_PEM:")
    print()
    print(PUB_FILE.read_text())


def cmd_machine():
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from app.license import get_machine_id
    mid = get_machine_id()
    print(f"Machine ID: {mid}")


def cmd_issue(machine_id: str, floating: bool, lifetime: bool, tier: str):
    _require_crypto()
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    if not PRIV_FILE.exists():
        print("ERROR: No private key found. Run --generate first.")
        sys.exit(1)

    private_key = serialization.load_pem_private_key(PRIV_FILE.read_bytes(), password=None)

    payload: dict = {
        "machine_id": machine_id if not floating else "*",
        "floating":   floating,
        "tier":       tier,
        "issued_at":  datetime.utcnow().isoformat(),
    }
    if not lifetime:
        payload["expiry"] = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d")

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    signature     = private_key.sign(payload_bytes, padding.PKCS1v15(), hashes.SHA256())
    raw           = payload_bytes + signature
    key           = base64.b64encode(raw).decode()

    # Format with dashes every 32 chars for readability
    formatted = "-".join(key[i:i+32] for i in range(0, len(key), 32))

    print(f"\nLicense Key ({tier.upper()} | {'floating' if floating else machine_id[:16]+'...'} | {'lifetime' if lifetime else payload.get('expiry')}):")
    print()
    print(formatted)
    print()


def cmd_verify(key: str):
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from app.license import validate_license
    ok, msg = validate_license(key.replace("\n", "").replace(" ", ""))
    status = "[VALID]" if ok else "[INVALID]"
    print(f"{status}  {msg}")


def main():
    p = argparse.ArgumentParser(description="SCI Platform License Key Tool")
    p.add_argument("--generate", action="store_true", help="Generate RSA key pair")
    p.add_argument("--machine",  action="store_true", help="Print this machine ID")
    p.add_argument("--issue",    metavar="MACHINE_ID", help="Issue a license key")
    p.add_argument("--verify",   metavar="KEY",        help="Verify a license key")
    p.add_argument("--floating", action="store_true",  help="Issue a floating license")
    p.add_argument("--lifetime", action="store_true",  help="No expiry date")
    p.add_argument("--tier",     default="standard",   choices=["standard", "pro", "enterprise"])

    args = p.parse_args()

    if args.generate:
        cmd_generate()
    elif args.machine:
        cmd_machine()
    elif args.issue:
        cmd_issue(args.issue, args.floating, args.lifetime, args.tier)
    elif args.verify:
        cmd_verify(args.verify)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
