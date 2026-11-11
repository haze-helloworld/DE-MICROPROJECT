"""
scripts/generate_keypair.py
Generates an RSA key pair for Snowflake key-pair authentication.
Saves rsa_key.p8 (private) and rsa_key.pub (public) in the project root.

Run from the project root:
    python scripts/generate_keypair.py

After running:
1. Copy the printed public key into Snowflake:
       ALTER USER SVC_INGEST SET RSA_PUBLIC_KEY='<paste here>';
2. Set SNOWFLAKE_PRIVATE_KEY_PATH in your .env to the absolute path of rsa_key.p8
"""

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

PROJECT_ROOT = Path(__file__).parent.parent
PRIVATE_KEY_PATH = PROJECT_ROOT / "rsa_key.p8"
PUBLIC_KEY_PATH  = PROJECT_ROOT / "rsa_key.pub"


def main() -> None:
    # Generate 2048-bit RSA key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key — PKCS8, unencrypted PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key — PEM
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_KEY_PATH.write_bytes(private_pem)
    PUBLIC_KEY_PATH.write_bytes(public_pem)

    print(f"✅ Private key saved to: {PRIVATE_KEY_PATH}")
    print(f"✅ Public  key saved to: {PUBLIC_KEY_PATH}")
    print()

    # Print the public key WITHOUT the PEM header/footer — that's what Snowflake wants
    pub_lines = public_pem.decode().strip().splitlines()
    pub_body  = "".join(line for line in pub_lines if not line.startswith("-----"))

    print("=" * 60)
    print("Paste this into a Snowflake worksheet (as ACCOUNTADMIN):")
    print("=" * 60)
    print(f"ALTER USER SVC_INGEST SET RSA_PUBLIC_KEY='{pub_body}';")
    print("=" * 60)
    print()
    abs_path = str(PRIVATE_KEY_PATH.resolve()).replace("\\", "/")
    print("Then update your .env:")
    print(f"  SNOWFLAKE_PRIVATE_KEY_PATH={abs_path}")


if __name__ == "__main__":
    main()

