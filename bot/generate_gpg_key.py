#!/usr/bin/env python3
"""
Generate GPG key for Nyan bot warrant canary.

This script generates a PGP key pair for the bot to sign warrant canary messages.
Run this script once during bot setup.
"""

import sys
from pathlib import Path

try:
    import gnupg
except ImportError:
    print("Error: python-gnupg is not installed")
    print("Install it with: pip install python-gnupg")
    sys.exit(1)


def generate_bot_key(gpg_home: str = "/app/.gnupg"):
    """
    Generate a GPG key for the Nyan bot.

    Args:
        gpg_home: Directory to store GPG keys (default: /app/.gnupg)
    """
    # Create GPG home directory if it doesn't exist
    gpg_home_path = Path(gpg_home)
    gpg_home_path.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Initialize GPG
    gpg = gnupg.GPG(gnupghome=str(gpg_home_path))

    # Check if key already exists
    keys = gpg.list_keys()
    if keys:
        print("GPG key already exists:")
        for key in keys:
            print(f"  Key ID: {key['keyid']}")
            print(f"  UID: {key['uids']}")
            print(f"  Fingerprint: {key['fingerprint']}")
        return

    # Generate key
    print("Generating GPG key for Nyan bot...")
    input_data = gpg.gen_key_input(
        name_real="VLDC Nyan Bot",
        name_email="nyan@vldc.org",
        key_type="RSA",
        key_length=2048,
        key_usage="sign",
        passphrase="",  # No passphrase for automated signing
    )

    key = gpg.gen_key(input_data)

    if key:
        print("\n✅ GPG key generated successfully!")
        print(f"Key ID: {key}")

        # Export public key for verification
        public_key = gpg.export_keys(str(key))
        if public_key:
            public_key_file = gpg_home_path / "nyan_bot_public.asc"
            with open(public_key_file, "w", encoding="utf-8") as f:
                f.write(public_key)
            print(f"\n📄 Public key exported to: {public_key_file}")
            print("\nPublic key (for verification):")
            print("=" * 80)
            print(public_key)
            print("=" * 80)
            print("\nShare this public key so users can verify signed messages!")
    else:
        print("❌ Failed to generate GPG key")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate GPG key for Nyan bot warrant canary"
    )
    parser.add_argument(
        "--gpg-home",
        default="/app/.gnupg",
        help="Directory to store GPG keys (default: /app/.gnupg)",
    )

    args = parser.parse_args()

    try:
        generate_bot_key(args.gpg_home)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"❌ Error: {exc}")
        sys.exit(1)
