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

DEST_NETWORK = "192.0.2.0"
DEST_MASK = "255.255.255.0"
NEXT_HOP = "Null0"
ROUTE_PATH = f"/data/Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list={DEST_NETWORK},{DEST_MASK}"
RIB_PATH = "/data/Cisco-IOS-XE-native:native/ip/route"

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
    
put_payload = {
    "Cisco-IOS-XE-native:ip-route-interface-forwarding-list": [
        {
            "prefix": DEST_NETWORK,
            "mask": DEST_MASK,
            "fwd-list": [
                {
                    "fwd": NEXT_HOP
                }
            ]
        }
    ]
}

# Create static route with PUT
print("=" * 60)
print("STEP 1: PUT to create static route")
print("=" * 60)

request("PUT", ROUTE_PATH, put_payload)

# Check if PUT executed correctly
print("=" * 60)
print("STEP 2: GET to check static route")
print("=" * 60)

request("GET", ROUTE_PATH)

# Check for RIB insertion with GET
print("=" * 60)
print("STEP 3: GET full static route table")
print("=" * 60)

request("GET", RIB_PATH)

# Remove static route with DELETE
print("=" * 60)
print("STEP 4: DELETE to remove static route")
print("=" * 60)

request("DELETE", ROUTE_PATH)

# Confirm static route deletion with GET
print("=" * 60)
print("STEP 5: GET to confirm static route deletion")
print("=" * 60)

r = request("GET", ROUTE_PATH)
print(r.status_code)
if r.status_code == 404:
    print("=" * 60)
    print("CONFIRM: route deletion")
    print("=" * 60)
else:
    print(f"EXCEPTION: 404 expected, not found. Status code: {r.status_code}")
