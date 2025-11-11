# Warrant Canary - Chirp Command

## Overview

The warrant canary feature allows users to verify that the bot is operating normally and without interference. When a user sends the `/chirp` command, the bot responds with "meow" signed with its PGP key.

## How It Works

The warrant canary is implemented as follows:

1. **User sends `/chirp` command** - Anyone can verify the bot is operational
2. **Bot responds with signed "meow"** - The message is cryptographically signed with the bot's private PGP key
3. **Users can verify the signature** - Using the bot's public key, users can verify the response is authentic

If the bot doesn't respond or responds without a valid signature, it may indicate:
- The bot is down
- The bot has been compromised
- The bot's GPG keys have been lost or tampered with

## Setup

### 1. Install Dependencies

The warrant canary requires the `python-gnupg` package, which is already included in `Pipfile`:

```bash
pipenv install
```

### 2. Install GPG

The system needs GPG installed:

```bash
# On Ubuntu/Debian
apt-get install gnupg

# On Alpine (for Docker)
apk add gnupg
```

### 3. Generate GPG Key

Run the key generation script to create a GPG key pair for the bot:

```bash
# Inside the container or environment
cd /app/bot
python generate_gpg_key.py
```

Or with a custom GPG home directory:

```bash
python generate_gpg_key.py --gpg-home /path/to/.gnupg
```

This will:
- Generate a 2048-bit RSA key pair
- Store the keys in `/app/.gnupg` (or specified directory)
- Export the public key to `nyan_bot_public.asc`
- Display the public key for sharing

### 4. Share Public Key

After generating the key, share the public key with your users so they can verify signed messages:

```bash
cat /app/.gnupg/nyan_bot_public.asc
```

Users can import this key with:

```bash
gpg --import nyan_bot_public.asc
```

## Usage

### For Users

To check if the bot is operational:

```
/chirp
```

Expected response:
```
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

meow
-----BEGIN PGP SIGNATURE-----
[signature data]
-----END PGP SIGNATURE-----
```

### Verifying the Signature

1. Copy the signed message
2. Save it to a file (e.g., `response.txt`)
3. Verify with GPG:

```bash
gpg --verify response.txt
```

You should see output indicating the signature is valid:
```
gpg: Good signature from "VLDC Nyan Bot <nyan@vldc.org>"
```

## Troubleshooting

### Bot responds with "meow" without signature

This means:
- GPG keys haven't been generated yet
- The `python-gnupg` package is not installed
- The GPG home directory is not accessible

### No response to `/chirp`

This means the bot is down or not receiving messages.

### Invalid signature

This may indicate:
- The bot has been compromised
- The keys have been replaced
- There's a bug in the signing implementation

## Security Considerations

1. **Private Key Security**: The bot's private key is stored without a passphrase to allow automated signing. Ensure the key directory (`/app/.gnupg`) has appropriate permissions (700).

2. **Key Rotation**: Consider rotating the GPG key periodically and announcing the new public key to users.

3. **Regular Testing**: Users should regularly test the `/chirp` command to ensure it's working as expected.

4. **Public Key Distribution**: Distribute the public key through multiple trusted channels (website, GitHub, etc.) to prevent MITM attacks.

## Implementation Details

- **Skill**: `bot/skills/chirp.py`
- **Key Generation**: `bot/generate_gpg_key.py`
- **Tests**: `bot/tests/chirp_test.py`
- **Key Storage**: `/app/.gnupg` (default)
- **Key Type**: RSA 2048-bit
- **Key Usage**: Signing only
- **Signature Format**: Clear-signed ASCII-armored

## References

- [Warrant Canary on Wikipedia](https://en.wikipedia.org/wiki/Warrant_canary)
- [GnuPG Documentation](https://gnupg.org/documentation/)
- [python-gnupg Documentation](https://gnupg.readthedocs.io/)
