import re
import time
import requests
import json
import os
from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
from flask import Flask, jsonify
from threading import Lock

app = Flask(__name__)
cache_lock = Lock()
cached_data = None
last_update = 0
CACHE_DURATION = 60  # Cache duration in seconds

# Constants
API_URL = "https://nerdvm.racknerd.com/api/client/command.php"
RESOURCE_TYPES = ["hdd", "bw", "mem"]
INFO_TYPES = ["hostname", "ipaddress"]
BYTES_TO_GB = 1024 ** 3
GB_TO_TB = 1024

# Compile regex patterns once
OUTER_PATTERN = re.compile(r'(<(?P<type>\w*?)>.*?</\w*?>)')
INNER_PATTERN = re.compile(r'<.*?>(?P<total>\d*?),(?P<used>\d*?),(?P<free>\d*?),(?P<per>\d*?)</.*?>')
SIMPLE_PATTERN = re.compile(r'<.*?>(?P<string>.*?)</.*?>')

@dataclass
class ServerConfig:
    key: str
    hash_value: str
    should_loop: bool
    sleep_minutes: int

def load_config() -> ServerConfig:
    """Load configuration from environment variables or files."""
    try:
        key = os.getenv("RACKNERD_KEY") or Path("tokens.txt").read_text().splitlines()[0].strip()
        hash_value = os.getenv("RACKNERD_HASH") or Path("tokens.txt").read_text().splitlines()[1].strip()
        
        settings = Path("settings.txt").read_text().splitlines()
        should_loop = settings[0].strip() == "True"
        sleep_minutes = int(settings[1].strip())
        
        return ServerConfig(key, hash_value, should_loop, sleep_minutes)
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")

def convert_bytes_to_readable(value: float) -> tuple[float, str]:
    """Convert bytes to GB or TB with appropriate unit."""
    gb_value = value / BYTES_TO_GB
    if gb_value >= 1000.0:
        return (gb_value / GB_TO_TB, 'TB')
    return (gb_value, 'GB')

def api_response(flags: Dict[str, str], api_url: str) -> Dict[str, Any]:
    """Make API request and parse response."""
    try:
        response = requests.post(api_url, data=flags, timeout=30)
        response.raise_for_status()
        result = {}

        for match in OUTER_PATTERN.finditer(response.text):
            type_name = match.groups()[1]
            if type_name in RESOURCE_TYPES:
                data = INNER_PATTERN.match(match.group()).groupdict()
                processed_data = process_resource_data(data)
                result[type_name] = processed_data
            elif type_name in INFO_TYPES:
                result[type_name] = SIMPLE_PATTERN.match(match.group()).groups()[0]

        return result
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")

def process_resource_data(data: Dict[str, str]) -> Dict[str, Any]:
    """Process resource data with proper conversions."""
    result = {}
    used = float(data['used'])
    total = float(data['total'])

    # Calculate percentage
    if used != 0.0 or total != 0.0:
        result['per'] = (used / total) * 100.0
    else:
        result['per'] = 0.0

    # Convert values
    for key in ['total', 'used', 'free']:
        value = float(data[key])
        display_value, unit = convert_bytes_to_readable(value)
        result[f'{key}_display'] = display_value
        result[f'{key}_mag'] = unit
        result[key] = value

    return result

def get_vps_data():
    """Get VPS data with caching."""
    global cached_data, last_update
    
    current_time = time.time()
    with cache_lock:
        if cached_data and current_time - last_update < CACHE_DURATION:
            return cached_data

        try:
            config = load_config()
            post_flags = {
                "key": config.key,
                "hash": config.hash_value,
                "action": "info",
                "bw": "true",
                "hdd": "true",
                "mem": "true"
            }

            response = api_response(post_flags, API_URL)
            if not response:
                raise RuntimeError("Empty response from the server")
            
            # Format the data in a widget-friendly way
            output = {
                "hostname": response['hostname'],
                "ip": response['ipaddress'],
                "last_update": int(time.time())
            }

            # Resource type to display name mapping
            resource_names = {
                "hdd": "storage",
                "bw": "bandwidth",
                "mem": "memory"
            }

            # Add resource metrics
            for resource_type in RESOURCE_TYPES:
                if post_flags[resource_type] == "true":
                    resource_data = response[resource_type]
                    
                    # Convert to common unit (GB)
                    multiplier = 1024 if resource_data["total_mag"] == "TB" else 1
                    total_gb = resource_data["total_display"] * multiplier
                    used_gb = resource_data["used_display"] * multiplier
                    free_gb = resource_data["free_display"] * multiplier
                    
                    name = resource_names[resource_type]
                    output[name] = {
                        "total": total_gb,
                        "used": used_gb,
                        "free": free_gb,
                        "usage": resource_data["per"]
                    }

            cached_data = output
            last_update = current_time
            return output

        except Exception as e:
            raise RuntimeError(f"Failed to fetch VPS data: {e}")

@app.route('/status')
def status():
    """Return VPS status in JSON format."""
    try:
        return jsonify(get_vps_data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """Return metrics in Prometheus format."""
    try:
        data = get_vps_data()
        prometheus_lines = []
        
        # Add resource metrics
        for resource_type, resource_data in data["resources"].items():
            base_name = f"vps_{resource_type}"
            
            # Total
            prometheus_lines.append(f'# HELP {base_name}_total Total {resource_type} in bytes')
            prometheus_lines.append(f'# TYPE {base_name}_total gauge')
            prometheus_lines.append(f'{base_name}_total {resource_data["total"]["value"]}')
            
            # Used
            prometheus_lines.append(f'# HELP {base_name}_used Used {resource_type} in bytes')
            prometheus_lines.append(f'# TYPE {base_name}_used gauge')
            prometheus_lines.append(f'{base_name}_used {resource_data["used"]["value"]}')
            
            # Percentage
            prometheus_lines.append(f'# HELP {base_name}_percentage_used Percentage of {resource_type} used')
            prometheus_lines.append(f'# TYPE {base_name}_percentage_used gauge')
            prometheus_lines.append(f'{base_name}_percentage_used {resource_data["percentage_used"]}')

        return '\n'.join(prometheus_lines), 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return f'# ERROR: {str(e)}', 500, {'Content-Type': 'text/plain'}

def main():
    """Main execution function."""
    try:
        # Test configuration loading before starting server
        config = load_config()
        print(f"Configuration loaded successfully. Loop: {config.should_loop}, Interval: {config.sleep_minutes}m")
        app.run(host='0.0.0.0', port=3000)
    except Exception as e:
        print(f"Failed to start server: {e}")
        raise

if __name__ == '__main__':
    main()
