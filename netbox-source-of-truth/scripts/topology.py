"""One-time seed data for the NetBox source-of-truth lab.

This file bootstraps an empty NetBox. It is NOT the source of truth.

Once populate-netbox.py has run, NetBox owns this data: change an IP address or a
BGP neighbor in the NetBox UI or API, re-run export-netbox.py, re-run render.yml.
Editing this file afterwards changes nothing until you re-run the population
script, and the script will not delete objects you removed from here.

The addressing and AS layout are carried over unchanged from the k8s-metallb-bgp
and ansible-bgp labs, minus the k3s transit links, so the ring is directly
comparable against those host_vars-driven builds.

Ring:  R1 --10.0.1.0/29-- R2 --10.0.2.0/29-- R3 --10.0.3.0/29-- R4 --10.0.4.0/29-- R1
"""

# NetBox organisational objects. Slugs are what nb_inventory groups on.
SITE = {"name": "GNS3 Lab", "slug": "gns3-lab"}
MANUFACTURER = {"name": "Cisco", "slug": "cisco"}
DEVICE_TYPE = {"model": "IOSv", "slug": "iosv"}
DEVICE_ROLE = {"name": "Router", "slug": "router"}
PLATFORM = {"name": "Cisco IOS", "slug": "ios"}

# NetBox interface type slugs.
ETHERNET = "1000base-t"
VIRTUAL = "virtual"

# The interface flagged mgmt becomes the device's primary IPv4 address in NetBox,
# which is what nb_inventory turns into ansible_host.
DEVICES = [
    {
        "name": "R1",
        "interfaces": [
            {
                "name": "Loopback0",
                "type": VIRTUAL,
                "description": "router_id",
                "address": "1.1.1.1/32",
            },
            {
                "name": "GigabitEthernet0/0",
                "type": ETHERNET,
                "description": "to_r2",
                "address": "10.0.1.1/29",
            },
            {
                "name": "GigabitEthernet0/3",
                "type": ETHERNET,
                "description": "to_r4",
                "address": "10.0.4.1/29",
            },
            {
                "name": "GigabitEthernet0/4",
                "type": ETHERNET,
                "description": "mgmt",
                "address": "192.168.0.1/24",
                "mgmt": True,
            },
        ],
        "bgp": {
            "asn": 65001,
            "router_id": "1.1.1.1",
            "neighbors": [
                {
                    "neighbor": "10.0.1.2",
                    "remote_as": 65002,
                    "description": "bgp_to_r2",
                },
                {
                    "neighbor": "10.0.4.4",
                    "remote_as": 65004,
                    "description": "bgp_to_r4",
                },
            ],
            "networks": [
                {"prefix": "1.1.1.1", "mask": "255.255.255.255"},
                {"prefix": "10.0.1.0", "mask": "255.255.255.248"},
                {"prefix": "10.0.4.0", "mask": "255.255.255.248"},
            ],
        },
    },
    {
        "name": "R2",
        "interfaces": [
            {
                "name": "Loopback0",
                "type": VIRTUAL,
                "description": "router_id",
                "address": "2.2.2.2/32",
            },
            {
                "name": "GigabitEthernet0/0",
                "type": ETHERNET,
                "description": "to_r1",
                "address": "10.0.1.2/29",
            },
            {
                "name": "GigabitEthernet0/1",
                "type": ETHERNET,
                "description": "to_r3",
                "address": "10.0.2.2/29",
            },
            {
                "name": "GigabitEthernet0/4",
                "type": ETHERNET,
                "description": "mgmt",
                "address": "192.168.0.2/24",
                "mgmt": True,
            },
        ],
        "bgp": {
            "asn": 65002,
            "router_id": "2.2.2.2",
            "neighbors": [
                {
                    "neighbor": "10.0.1.1",
                    "remote_as": 65001,
                    "description": "bgp_to_r1",
                },
                {
                    "neighbor": "10.0.2.3",
                    "remote_as": 65003,
                    "description": "bgp_to_r3",
                },
            ],
            "networks": [
                {"prefix": "2.2.2.2", "mask": "255.255.255.255"},
                {"prefix": "10.0.1.0", "mask": "255.255.255.248"},
                {"prefix": "10.0.2.0", "mask": "255.255.255.248"},
            ],
        },
    },
    {
        "name": "R3",
        "interfaces": [
            {
                "name": "Loopback0",
                "type": VIRTUAL,
                "description": "router_id",
                "address": "3.3.3.3/32",
            },
            {
                "name": "GigabitEthernet0/1",
                "type": ETHERNET,
                "description": "to_r2",
                "address": "10.0.2.3/29",
            },
            {
                "name": "GigabitEthernet0/2",
                "type": ETHERNET,
                "description": "to_r4",
                "address": "10.0.3.3/29",
            },
            {
                "name": "GigabitEthernet0/4",
                "type": ETHERNET,
                "description": "mgmt",
                "address": "192.168.0.3/24",
                "mgmt": True,
            },
        ],
        "bgp": {
            "asn": 65003,
            "router_id": "3.3.3.3",
            "neighbors": [
                {
                    "neighbor": "10.0.2.2",
                    "remote_as": 65002,
                    "description": "bgp_to_r2",
                },
                {
                    "neighbor": "10.0.3.4",
                    "remote_as": 65004,
                    "description": "bgp_to_r4",
                },
            ],
            "networks": [
                {"prefix": "3.3.3.3", "mask": "255.255.255.255"},
                {"prefix": "10.0.2.0", "mask": "255.255.255.248"},
                {"prefix": "10.0.3.0", "mask": "255.255.255.248"},
            ],
        },
    },
    {
        "name": "R4",
        "interfaces": [
            {
                "name": "Loopback0",
                "type": VIRTUAL,
                "description": "router_id",
                "address": "4.4.4.4/32",
            },
            {
                "name": "GigabitEthernet0/2",
                "type": ETHERNET,
                "description": "to_r3",
                "address": "10.0.3.4/29",
            },
            {
                "name": "GigabitEthernet0/3",
                "type": ETHERNET,
                "description": "to_r1",
                "address": "10.0.4.4/29",
            },
            {
                "name": "GigabitEthernet0/4",
                "type": ETHERNET,
                "description": "mgmt",
                "address": "192.168.0.4/24",
                "mgmt": True,
            },
        ],
        "bgp": {
            "asn": 65004,
            "router_id": "4.4.4.4",
            "neighbors": [
                {
                    "neighbor": "10.0.3.3",
                    "remote_as": 65003,
                    "description": "bgp_to_r3",
                },
                {
                    "neighbor": "10.0.4.1",
                    "remote_as": 65001,
                    "description": "bgp_to_r1",
                },
            ],
            "networks": [
                {"prefix": "4.4.4.4", "mask": "255.255.255.255"},
                {"prefix": "10.0.3.0", "mask": "255.255.255.248"},
                {"prefix": "10.0.4.0", "mask": "255.255.255.248"},
            ],
        },
    },
]
