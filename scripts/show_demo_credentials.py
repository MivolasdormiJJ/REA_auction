"""Decrypt demo credentials locally using a separately stored Fernet key.

Usage:
  python scripts/show_demo_credentials.py path/to/rea-demo-credentials.enc path/to/rea-demo-decryption-key.txt
Never commit the decryption key to GitHub.
"""
import json
import sys
from pathlib import Path

from cryptography.fernet import Fernet

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/show_demo_credentials.py <encrypted_file> <key_file>")
    encrypted = Path(sys.argv[1]).read_text().strip().encode()
    key = Path(sys.argv[2]).read_text().strip().encode()
    data = json.loads(Fernet(key).decrypt(encrypted))
    for account in data["users"]:
        print(f'{account["role"]:8} {account["username"]:16} {account["password"]}')
