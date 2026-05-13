import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST = "10.10.20.48"
USER = "developer"
PASSWORD = "C1sco12345"

BASE = f"https://{HOST}/restconf"
HEADERS_GET = {"Accept": "application/yang-data+json"}
HEADERS_WRITE = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

LOOPBACK_NUM = 10
LOOPBACK_PATH = f"/data/Cisco-IOS-XE-native:native/interface/Loopback={LOOPBACK_NUM}"

def request(method, path, payload=None):
    url = f"{BASE}{path}"
    headers = HEADERS_WRITE if payload else HEADERS_GET
    r = requests.request(
        method, url,
        auth=(USER, PASSWORD),
        headers=headers,
        json=payload,
        verify=False,
        timeout=15,
    )
    print(f"{method} {path} -> {r.status_code}")
    if r.text:
        try:
            print(json.dumps(r.json(), indent=2))
        except ValueError:
            print(r.text)
    print()
    return r

# 1. CREATE the loopback with PUT (replace semantics, idempotent)
print("=" * 60)
print(f"STEP 1: PUT to create Loopback{LOOPBACK_NUM}")
print("=" * 60)
create_payload = {
    "Cisco-IOS-XE-native:Loopback": {
        "name": LOOPBACK_NUM,
        "description": "Created via RESTCONF lab",
        "ip": {
            "address": {
                "primary": {
                    "address": "192.168.200.1",
                    "mask": "255.255.255.0"
                }
            }
        }
    }
}
request("PUT", LOOPBACK_PATH, create_payload)

# 2. READ back to verify
print("=" * 60)
print("STEP 2: GET to verify creation")
print("=" * 60)
request("GET", LOOPBACK_PATH)

# 3. PATCH to merge a new description, leave IP untouched
print("=" * 60)
print("STEP 3: PATCH to update description (merge semantics)")
print("=" * 60)
patch_payload = {
    "Cisco-IOS-XE-native:Loopback": {
        "name": LOOPBACK_NUM,
        "description": "Updated via PATCH"
    }
}
request("PATCH", LOOPBACK_PATH, patch_payload)

# 4. READ back to confirm description changed AND IP survived
print("=" * 60)
print("STEP 4: GET to confirm merge preserved the IP")
print("=" * 60)
request("GET", LOOPBACK_PATH)

# 5. DELETE the loopback
print("=" * 60)
print("STEP 5: DELETE the loopback")
print("=" * 60)
request("DELETE", LOOPBACK_PATH)

# 6. READ back, expect 404
print("=" * 60)
print("STEP 6: GET to confirm deletion (expect 404)")
print("=" * 60)
request("GET", LOOPBACK_PATH)
