from ncclient import manager
from ncclient.operations.rpc import RPCError

HOST = "10.10.20.48"
PORT = 830
USER = "developer"
PASSWORD = "C1sco12345"
DEST_NETWORK = "192.0.2.0"
DEST_MASK = "255.255.255.0"
NEXT_HOP = "Null0"

put_payload = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <ip>
                <route>
                    <ip-route-interface-forwarding-list>
                        <prefix>{DEST_NETWORK}</prefix>
                        <mask>{DEST_MASK}</mask>
                        <fwd-list>
                            <fwd>{NEXT_HOP}</fwd>
                        </fwd-list>
                    </ip-route-interface-forwarding-list>
                </route>
            </ip>
        </native>
    </config>
"""

filter_payload = f"""
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <ip>
                <route>
                    <ip-route-interface-forwarding-list>
                        <prefix>{DEST_NETWORK}</prefix>
                        <mask>{DEST_MASK}</mask>
                    </ip-route-interface-forwarding-list>
                </route>
            </ip>
        </native>
"""

filter_routes = """
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <ip>
                <route>
                </route>
            </ip>
        </native>
"""

delete_payload = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <ip>
                <route>
                    <ip-route-interface-forwarding-list xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="delete">
                        <prefix>{DEST_NETWORK}</prefix>
                        <mask>{DEST_MASK}</mask>
                    </ip-route-interface-forwarding-list>
                </route>
            </ip>
        </native>
    </config>
"""

with manager.connect(
    host=HOST,
    port=PORT,
    username=USER,
    password=PASSWORD,
    hostkey_verify=False,
    device_params={"name": "iosxe"},
) as m:
    # all operations happen inside this block
    
    # step 1 operations
    # Create static route with PUT
    print("=" * 60)
    print("STEP 1 INITIATING")
    print("=" * 60)
    try:
        response = m.edit_config(target="running", config=put_payload)
        print("=" * 60)
        print("STEP 1 OK")
        print("=" * 60)
        print(response)
    except RPCError as e:
        print(f"STEP 1 FAILED: {e}")

    # step 2 operations
    # Check for route creation with GET
    print("=" * 60)
    print("STEP 2 INITIATING")
    print("=" * 60)
    try:
        response = m.get_config(source="running", filter=("subtree", filter_payload))
        print("=" * 60)
        print("STEP 2 OK")
        print("=" * 60)
        print(response)
    except RPCError as e:
        print(f"STEP 2 FAILED: {e}")

    # step 3 operations
    # Check route config with GET
    print("=" * 60)
    print("STEP 3 INITIATING")
    print("=" * 60)
    try:
        response = m.get_config(source="running", filter=("subtree", filter_routes))
        print("=" * 60)
        print("STEP 3 OK")
        print("=" * 60)
        print(response)
    except RPCError as e:
        print(f"STEP 3 FAILED: {e}")
        
    # step 4 operations
    # Delete route with edit-config
    print("=" * 60)
    print("STEP 4 INITIATING")
    print("=" * 60)
    try:
        response = m.edit_config(target="running", config=delete_payload)
        print("=" * 60)
        print("STEP 4 OK")
        print("=" * 60)
        print(response)
    except RPCError as e:
        print(f"STEP 4 FAILED: {e}")
        
    # step 5 operations
    # Confirm route deletion
    print("=" * 60)
    print("STEP 5 INITIATING")
    print("=" * 60)
    try:
        response = m.get_config(source="running", filter=("subtree", filter_payload))
        if DEST_NETWORK in str(response):
            print("STEP 5 EXCEPTION: route still present")
        else:
            print("STEP 5 CONFIRMED: route deleted")
        print(response)
    except RPCError as e:
        print(f"STEP 5 FAILED: {e}")
