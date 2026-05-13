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

print("API root:")
print(get("/"))
print("\nHostname:")
print(get("/data/Cisco-IOS-XE-native:native/hostname"))
