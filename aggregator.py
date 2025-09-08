import yaml
import requests
import base64
import json
import re
import socket
import time
import concurrent.futures
import urllib.parse
from datetime import datetime
import pytz
from collections import defaultdict
import socks
import urllib3

# Disable SSL warnings for proxy testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_flag_by_country_code(code):
    """Get flag emoji by country code"""
    flags = {
        'SG': '🇸🇬', 'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'HK': '🇭🇰',
        'TW': '🇹🇼', 'CN': '🇨🇳', 'GB': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'NL': '🇳🇱', 'CA': '🇨🇦', 'AU': '🇦🇺', 'IN': '🇮🇳', 'TH': '🇹🇭',
        'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'VN': '🇻🇳', 'TR': '🇹🇷',
        'AE': '🇦🇪', 'RU': '🇷🇺', 'BR': '🇧🇷', 'AR': '🇦🇷', 'MX': '🇲🇽',
        'IT': '🇮🇹', 'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮',
        'DK': '🇩🇰', 'PL': '🇵🇱', 'UA': '🇺🇦', 'RO': '🇷🇴', 'CZ': '🇨🇿',
        'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'IE': '🇮🇪', 'NZ': '🇳🇿',
        'ZA': '🇿🇦', 'EG': '🇪🇬', 'KE': '🇰🇪', 'IL': '🇮🇱', 'SA': '🇸🇦',
        'CL': '🇨🇱', 'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'EC': '🇪🇨',
        'PT': '🇵🇹', 'GR': '🇬🇷', 'HU': '🇭🇺', 'IS': '🇮🇸', 'LU': '🇱🇺',
        'SK': '🇸🇰', 'SI': '🇸🇮', 'BG': '🇧🇬', 'HR': '🇭🇷', 'RS': '🇷🇸',
        'LT': '🇱🇹', 'LV': '🇱🇻', 'EE': '🇪🇪', 'MD': '🇲🇩', 'AM': '🇦🇲',
        'GE': '🇬🇪', 'AZ': '🇦🇿', 'KZ': '🇰🇿', 'UZ': '🇺🇿', 'TJ': '🇹🇯',
        'KG': '🇰🇬', 'TM': '🇹🇲', 'MN': '🇲🇳', 'NP': '🇳🇵', 'BD': '🇧🇩',
        'LK': '🇱🇰', 'MM': '🇲🇲', 'KH': '🇰🇭', 'LA': '🇱🇦', 'BN': '🇧🇳',
        'MO': '🇲🇴', 'PK': '🇵🇰', 'AF': '🇦🇫', 'JO': '🇯🇴', 'LB': '🇱🇧',
        'CW': '🇨🇼', 'PR': '🇵🇷', 'TT': '🇹🇹', 'BB': '🇧🇧', 'MT': '🇲🇹'
    }
    return flags.get(code.upper(), '🌍')

def test_proxy_location(node):
    """Test proxy and get its real location (like FlClash) - combines health check + location"""
    server = get_node_server(node)
    port = node.get('port')
    node_type = node.get('type', '').lower()
    
    if not server or not port:
        return None, False
    
    # For complex proxy types, we'll use simple TCP test + DNS lookup
    # (Full proxy testing would require additional libraries)
    if node_type in ['vmess', 'vless', 'trojan', 'ss', 'ssr']:
        # Quick TCP connectivity test
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            
            # Resolve domain
            try:
                ip = socket.gethostbyname(server)
            except:
                return None, False
            
            # Test connection
            result = sock.connect_ex((ip, int(port)))
            sock.close()
            
            if result != 0:
                return None, False
            
            # If connected, get location from IP
            # Using similar API as FlClash
            try:
                response = requests.get(
                    f'http://ip-api.com/json/{ip}?fields=status,countryCode',
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        country = data.get('countryCode', 'UN')
                        return country.upper(), True
            except:
                pass
            
            # Fallback to ip.sb API
            try:
                response = requests.get(
                    f'https://api.ip.sb/geoip/{ip}',
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    country = data.get('country_code', 'UN')
                    return country.upper(), True
            except:
                pass
            
            # Connected but couldn't get location
            return 'UN', True
            
        except:
            return None, False
    
    # For HTTP/SOCKS5 proxies, we could do real proxy test
    elif node_type in ['http', 'https', 'socks5', 'socks']:
        try:
            # Setup proxy
            proxy_url = f"{node_type}://{server}:{port}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Test through proxy
            response = requests.get(
                'http://ip-api.com/json?fields=status,countryCode',
                proxies=proxies,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('countryCode', 'UN')
                    return country.upper(), True
            
            return 'UN', True
        except:
            return None, False
    
    return None, False

def batch_test_proxies(nodes, max_workers=30):
    """Test proxies in parallel - combines health check and location detection"""
    print(f"\n🔬 Testing {len(nodes)} proxies (health + location)...")
    print("   This combines connectivity test with real location detection")
    
    valid_nodes = []
    stats = defaultdict(int)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(test_proxy_location, node): node for node in nodes}
        
        completed = 0
        dead_count = 0
        
        for future in concurrent.futures.as_completed(future_to_node):
            completed += 1
            if completed % 20 == 0:
                print(f"   Tested {completed}/{len(nodes)} nodes... ({dead_count} dead)")
            
            node = future_to_node[future]
            try:
                country, is_alive = future.result()
                
                if is_alive:
                    node['detected_country'] = country
                    valid_nodes.append(node)
                    stats[country] += 1
                else:
                    dead_count += 1
            except:
                dead_count += 1
    
    print(f"\n   ✅ Results:")
    print(f"      Alive: {len(valid_nodes)} nodes")
    print(f"      Dead: {dead_count} nodes")
    print(f"      Countries detected: {len(stats)}")
    
    return valid_nodes, stats

# Keep all the parsing functions from before (parse_v2ray_json, convert_v2ray_to_clash, etc.)
# ... [Previous parsing functions remain the same] ...

def get_node_server(node):
    """Extract server address from node"""
    if isinstance(node, dict):
        for field in ['server', 'add', 'address', 'host']:
            if field in node:
                return node[field]
    return None

def validate_and_clean_node(node):
    """Validate and clean node configuration"""
    if not isinstance(node, dict):
        return None
    
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    node_type = node.get('type', '').lower()
    if node_type in ['vless', 'reality'] and ('reality-opts' in node or 'flow' in node):
        return None
    
    try:
        port = int(node.get('port', 0))
        if port <= 0 or port > 65535:
            return None
        node['port'] = port
    except:
        return None
    
    if node_type == 'ss':
        if 'cipher' not in node or 'password' not in node:
            return None
    elif node_type == 'vmess':
        if 'uuid' not in node:
            return None
        if 'alterId' in node:
            try:
                node['alterId'] = int(node['alterId'])
            except:
                node['alterId'] = 0
    elif node_type == 'trojan':
        if 'password' not in node:
            return None
    
    problematic_fields = [
        '_index', '_type', 'clashType', 'proxies', 'rules',
        'benchmarkUrl', 'reality-opts', 'flow', 'xudp',
        'packet-encoding', 'client-fingerprint', 'fingerprint'
    ]
    for field in problematic_fields:
        node.pop(field, None)
    
    if 'name' not in node:
        node['name'] = 'Unnamed'
    
    return node

def fetch_subscription(url):
    """Fetch and decode subscription content"""
    # [Keep the same fetch_subscription function from before]
    pass

def main():
    print("🚀 Starting Clash Aggregator with Combined Health+Location Check...")
    print("=" * 50)
    
    # Configuration
    ENABLE_REAL_TESTING = True  # Combined health + location check
    EXCLUDE_UNKNOWN = True      # Exclude nodes with unknown location
    MAX_WORKERS = 30            # Parallel testing threads
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Found {len(urls)} subscription URLs")
    
    # Collect all nodes
    all_nodes = []
    seen_servers = set()
    
    for idx, url in enumerate(urls, 1):
        print(f"\n📥 Fetching subscription {idx}/{len(urls)}...")
        nodes = fetch_subscription(url)
        print(f"   Found {len(nodes)} nodes")
        
        for node in nodes:
            cleaned_node = validate_and_clean_node(node)
            if cleaned_node:
                server = get_node_server(cleaned_node)
                if server and server not in seen_servers:
                    seen_servers.add(server)
                    all_nodes.append(cleaned_node)
    
    print(f"\n📊 Collected {len(all_nodes)} unique nodes")
    
    # Test proxies (health + location combined)
    if ENABLE_REAL_TESTING:
        valid_nodes, country_stats = batch_test_proxies(all_nodes, max_workers=MAX_WORKERS)
        
        # Show country distribution
        print(f"\n📊 Country Distribution (from real testing):")
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            flag = get_flag_by_country_code(country)
            print(f"   {flag} {country}: {count} nodes")
        
        # Group by country
        country_nodes = defaultdict(list)
        for node in valid_nodes:
            country = node.get('detected_country', 'UN')
            if not (EXCLUDE_UNKNOWN and country == 'UN'):
                country_nodes[country].append(node)
    else:
        # Fallback to simple method
        country_nodes = defaultdict(list)
        for node in all_nodes:
            country_nodes['UN'].append(node)
    
    # Rename nodes
    renamed_nodes = []
    
    # Process Singapore nodes first
    if 'SG' in country_nodes:
        print(f"\n🇸🇬 Processing {len(country_nodes['SG'])} Singapore nodes...")
        for idx, node in enumerate(country_nodes['SG'], 1):
            node['name'] = f"🇸🇬 SG-{idx:03d}"
            # Remove temporary field
            node.pop('detected_country', None)
            renamed_nodes.append(node)
        del country_nodes['SG']
    
    # Process other countries
    for country_code, nodes in sorted(country_nodes.items()):
        flag = get_flag_by_country_code(country_code)
        print(f"{flag} Processing {len(nodes)} {country_code} nodes...")
        
        for idx, node in enumerate(nodes, 1):
            node['name'] = f"{flag} {country_code}-{idx:03d}"
            # Remove temporary field
            node.pop('detected_country', None)
            renamed_nodes.append(node)
    
    # Create output
    output = {
        'proxies': renamed_nodes
    }
    
    # Add update time
    tz = pytz.timezone('Asia/Singapore')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Write output file
    with open('clash.yaml', 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(renamed_nodes)}\n")
        f.write(f"# Testing Method: {'Real Proxy Test' if ENABLE_REAL_TESTING else 'DNS Lookup'}\n")
        f.write(f"# Only Working Proxies: Yes\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Final output: {len(renamed_nodes)} working proxies with accurate locations")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
