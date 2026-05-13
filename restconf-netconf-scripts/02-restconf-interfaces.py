import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST = "10.10.20.48"
USER = "developer"
PASSWORD = "C1sco12345"

BASE = f"https://{HOST}/restconf"
HEADERS = {"Accept": "application/yang-data+json"}

def get(path):
    url = f"{BASE}{path}"
    r = requests.get(url, auth=(USER, PASSWORD), headers=HEADERS,
                     verify=False, timeout=15)
    r.raise_for_status()
    return r.json() if r.text else {}

print("=" * 60)
print("ietf-interfaces:interfaces (IETF standard model)")
print("=" * 60)
ietf = get("/data/ietf-interfaces:interfaces")
print(json.dumps(ietf, indent=2))

print()
print("=" * 60)
print("Cisco-IOS-XE-native:native/interface (vendor native model)")
print("=" * 60)
native = get("/data/Cisco-IOS-XE-native:native/interface")
print(json.dumps(native, indent=2))
