import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.paypal.client import PayPalSandboxClient


async def test_auth():
    print("[*] Testing PayPal Sandbox Authentication...")
    client = PayPalSandboxClient()
    try:
        token = await client.get_access_token()
        print(f"[SUCCESS] Obtained Sandbox Access Token: {token[:15]}... (Length: {len(token)})")
        return True
    except Exception as e:
        print(f"[FAILED] Error obtaining Sandbox token: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_auth())
    sys.exit(0 if success else 1)
