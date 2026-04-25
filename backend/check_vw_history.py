import os
from dotenv import load_dotenv
from carconnectivity import carconnectivity

load_dotenv()

username = os.environ.get("VW_USERNAME")
password = os.environ.get("VW_PASSWORD")

if not username or not password:
    print("No credentials found.")
    exit(1)

cc_config = {
    "carConnectivity": {
        "connectors": [
            {
                "type": "volkswagen",
                "config": {
                    "username": username,
                    "password": password
                }
            }
        ]
    }
}

cc = carconnectivity.CarConnectivity(cc_config)
cc.startup()

garage = cc.get_garage()
if hasattr(cc, 'fetch_all'):
    cc.fetch_all()

children = getattr(garage, 'children', None)
vehicles = getattr(garage, 'vehicles', None)
items = children if children else vehicles

if items:
    vehicle = items[0] if isinstance(items, list) else list(items.values())[0] if isinstance(items, dict) else items[0]
    print(f"Vehicle: {vehicle.name}")
    import json
    
    # Try to extract the dictionary representation
    v_dict = vehicle.as_dict() if hasattr(vehicle, 'as_dict') else str(vehicle)
    
    # Write to a file so we can inspect it completely
    with open('/tmp/vw_full_dump_history_check.json', 'w') as f:
        json.dump(v_dict, f, indent=2, default=str)
    
    print("Dumped vehicle data to /tmp/vw_full_dump_history_check.json")
    
    # Check specifically for trip or history keywords
    def search_dict(d, keywords, path=""):
        found = []
        if isinstance(d, dict):
            for k, v in d.items():
                if any(kw in k.lower() for kw in keywords):
                    found.append((f"{path}.{k}", type(v).__name__))
                found.extend(search_dict(v, keywords, f"{path}.{k}"))
        elif isinstance(d, list):
            for i, v in enumerate(d):
                found.extend(search_dict(v, keywords, f"{path}[{i}]"))
        return found
        
    findings = search_dict(v_dict, ['trip', 'history', 'route', 'destination', 'temperature', 'log', 'record', 'drive'])
    print("Findings for historical keywords:")
    for path, t in findings:
        print(f" - {path} ({t})")
else:
    print("No vehicles found in garage.")
