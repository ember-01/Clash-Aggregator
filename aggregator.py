import yaml
import requests
import base64
import json
import re
from datetime import datetime
import pytz
from collections import defaultdict
import socket
import time

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
        'SY': '🇸🇾', 'IQ': '🇮🇶', 'KW': '🇰🇼', 'BH': '🇧🇭', 'QA': '🇶🇦',
        'OM': '🇴🇲', 'YE': '🇾🇪', 'IR': '🇮🇷', 'MA': '🇲🇦', 'DZ': '🇩🇿',
        'TN': '🇹🇳', 'LY': '🇱🇾', 'SD': '🇸🇩', 'ET': '🇪🇹', 'NG': '🇳🇬',
        'GH': '🇬🇭', 'CI': '🇨🇮', 'SN': '🇸🇳', 'UG': '🇺🇬', 'ZW': '🇿🇼',
        'BW': '🇧🇼', 'MZ': '🇲🇿', 'NA': '🇳🇦', 'AO': '🇦🇴', 'TZ': '🇹🇿',
        'MG': '🇲🇬', 'MU': '🇲🇺', 'RE': '🇷🇪', 'BY': '🇧🇾', 'AL': '🇦🇱',
        'MK': '🇲🇰', 'ME': '🇲🇪', 'BA': '🇧🇦', 'XK': '🇽🇰', 'MT': '🇲🇹',
        'CY': '🇨🇾', 'PA': '🇵🇦', 'CR': '🇨🇷', 'NI': '🇳🇮', 'HN': '🇭🇳',
        'SV': '🇸🇻', 'GT': '🇬🇹', 'BZ': '🇧🇿', 'BO': '🇧🇴', 'PY': '🇵🇾',
        'UY': '🇺🇾', 'GY': '🇬🇾', 'SR': '🇸🇷', 'GF': '🇬🇫', 'JM': '🇯🇲',
        'TT': '🇹🇹', 'BB': '🇧🇧', 'BS': '🇧🇸', 'BM': '🇧🇲', 'DO': '🇩🇴',
        'PR': '🇵🇷', 'VI': '🇻🇮', 'CU': '🇨🇺', 'HT': '🇭🇹', 'GP': '🇬🇵',
        'MQ': '🇲🇶', 'GD': '🇬🇩', 'LC': '🇱🇨', 'VC': '🇻🇨', 'AG': '🇦🇬',
        'DM': '🇩🇲', 'KN': '🇰🇳', 'KY': '🇰🇾', 'TC': '🇹🇨', 'AW': '🇦🇼',
        'FJ': '🇫🇯', 'PG': '🇵🇬', 'SB': '🇸🇧', 'VU': '🇻🇺', 'NC': '🇳🇨',
        'PF': '🇵🇫', 'WS': '🇼🇸', 'GU': '🇬🇺', 'MP': '🇲🇵', 'AS': '🇦🇸',
        'CK': '🇨🇰', 'TO': '🇹🇴', 'PW': '🇵🇼', 'MH': '🇲🇭', 'FM': '🇫🇲',
        'KI': '🇰🇮', 'TL': '🇹🇱', 'BT': '🇧🇹', 'MV': '🇲🇻', 'ZM': '🇿🇲',
        'CD': '🇨🇩', 'CG': '🇨🇬', 'CM': '🇨🇲', 'GA': '🇬🇦', 'GQ': '🇬🇶',
        'CF': '🇨🇫', 'TD': '🇹🇩', 'DJ': '🇩🇯', 'SO': '🇸🇴', 'RW': '🇷🇼',
        'BI': '🇧🇮', 'MW': '🇲🇼', 'LS': '🇱🇸', 'SZ': '🇸🇿', 'KM': '🇰🇲',
        'SC': '🇸🇨', 'GM': '🇬🇲', 'GW': '🇬🇼', 'ML': '🇲🇱', 'MR': '🇲🇷',
        'NE': '🇳🇪', 'BF': '🇧🇫', 'TG': '🇹🇬', 'BJ': '🇧🇯', 'GN': '🇬🇳',
        'SL': '🇸🇱', 'LR': '🇱🇷', 'CV': '🇨🇻', 'ST': '🇸🇹', 'ER': '🇪🇷',
        'SS': '🇸🇸', 'LI': '🇱🇮', 'SM': '🇸🇲', 'VA': '🇻🇦', 'AD': '🇦🇩',
        'MC': '🇲🇨', 'NR': '🇳🇷', 'TV': '🇹🇻', 'NU': '🇳🇺', 'TK': '🇹🇰'
    }
    return flags.get(code.upper(), '🌍')

def get_server_location(server_ip):
    """Get country code from server IP using ip-api.com"""
    try:
        # First check if it's a valid IP or domain
        if not server_ip:
            return 'UN'
        
        # If it's a domain, get the IP
        try:
            socket.inet_aton(server_ip)
            ip = server_ip
        except socket.error:
            # It's a domain, resolve it
            try:
                ip = socket.gethostbyname(server_ip)
            except:
                return 'UN'
        
        # Query ip-api.com for location (free, no API key needed)
        response = requests.get(
            f'http://ip-api.com/json/{ip}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                country_code = data.get('countryCode', 'UN')
                return country_code
        
        time.sleep(0.5)  # Rate limiting for free API
        return 'UN'
        
    except Exception as e:
        print(f"Error getting location for {server_ip}: {e}")
        return 'UN'

def get_node_server(node):
    """Extract server address from node"""
    if isinstance(node, dict):
        # Common fields for server address
        for field in ['server', 'add', 'address', 'host']:
            if field in node:
                return node[field]
    return None

def parse_base64_nodes(content):
    """Parse base64 encoded node list"""
    nodes = []
    try:
        decoded = base64.b64decode(content).decode('utf-8')
        lines = decoded.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse different protocols
            if line.startswith('vmess://'):
                try:
                    vmess_data = base64.b64decode(line[8:]).decode('utf-8')
                    vmess_node = json.loads(vmess_data)
                    node = {
                        'name': vmess_node.get('ps', 'Unnamed'),
                        'type': 'vmess',
                        'server': vmess_node.get('add', ''),
                        'port': int(vmess_node.get('port', 443)),
                        'uuid': vmess_node.get('id', ''),
                        'alterId': int(vmess_node.get('aid', 0)),
                        'cipher': vmess_node.get('scy', 'auto'),
                        'tls': vmess_node.get('tls', '') == 'tls',
                        'network': vmess_node.get('net', 'tcp')
                    }
                    
                    # Add additional fields if present
                    if vmess_node.get('host'):
                        node['ws-opts'] = {'headers': {'Host': vmess_node['host']}}
                    if vmess_node.get('path'):
                        if 'ws-opts' not in node:
                            node['ws-opts'] = {}
                        node['ws-opts']['path'] = vmess_node['path']
                    
                    nodes.append(node)
                except:
                    continue
                    
            elif line.startswith('ss://'):
                try:
                    # Parse shadowsocks URL
                    ss_data = line[5:]
                    if '#' in ss_data:
                        ss_main, ss_name = ss_data.split('#', 1)
                        ss_name = requests.utils.unquote(ss_name)
                    else:
                        ss_main = ss_data
                        ss_name = 'Unnamed'
                    
                    if '@' in ss_main:
                        ss_decoded = base64.b64decode(ss_main.split('@')[0]).decode('utf-8')
                        cipher, password = ss_decoded.split(':', 1)
                        server_port = ss_main.split('@')[1]
                        server, port = server_port.rsplit(':', 1)
                    else:
                        # Alternative format
                        ss_decoded = base64.b64decode(ss_main).decode('utf-8')
                        parts = ss_decoded.split('@')
                        if len(parts) == 2:
                            cipher_pass = parts[0].split(':', 1)
                            server_port = parts[1].rsplit(':', 1)
                            if len(cipher_pass) == 2 and len(server_port) == 2:
                                cipher, password = cipher_pass
                                server, port = server_port
                            else:
                                continue
                        else:
                            continue
                    
                    node = {
                        'name': ss_name,
                        'type': 'ss',
                        'server': server,
                        'port': int(port),
                        'cipher': cipher,
                        'password': password
                    }
                    nodes.append(node)
                except:
                    continue
                    
            elif line.startswith('trojan://'):
                try:
                    trojan_data = line[9:]
                    if '#' in trojan_data:
                        trojan_main, trojan_name = trojan_data.split('#', 1)
                        trojan_name = requests.utils.unquote(trojan_name)
                    else:
                        trojan_main = trojan_data
                        trojan_name = 'Unnamed'
                    
                    password, server_port = trojan_main.split('@', 1)
                    server, port = server_port.rsplit(':', 1)
                    if '?' in port:
                        port = port.split('?')[0]
                    
                    node = {
                        'name': trojan_name,
                        'type': 'trojan',
                        'server': server,
                        'port': int(port),
                        'password': password,
                        'sni': server,
                        'skip-cert-verify': True
                    }
                    nodes.append(node)
                except:
                    continue
    except:
        pass
    
    return nodes

def fetch_subscription(url):
    """Fetch and decode subscription content"""
    try:
        headers = {
            'User-Agent': 'clash-verge/1.0'
        }
        response = requests.get(url, timeout=10, headers=headers)
        content = response.text.strip()
        
        # Try parsing as YAML first (standard Clash format)
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
        except:
            pass
        
        # Try base64 decode
        nodes = parse_base64_nodes(content)
        if nodes:
            return nodes
        
        # Try direct YAML list
        try:
            data = yaml.safe_load(content)
            if isinstance(data, list):
                return data
        except:
            pass
        
        return []
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def main():
    print("🚀 Starting Clash Aggregator...")
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Found {len(urls)} subscription URLs")
    
    # Collect all nodes
    all_nodes = []
    seen_servers = set()
    
    for idx, url in enumerate(urls, 1):
        print(f"📥 Fetching subscription {idx}/{len(urls)}...")
        nodes = fetch_subscription(url)
        
        for node in nodes:
            if isinstance(node, dict):
                server = get_node_server(node)
                if server and server not in seen_servers:
                    seen_servers.add(server)
                    all_nodes.append(node)
    
    print(f"📊 Collected {len(all_nodes)} unique nodes")
    
    # Get geo-location for each node
    print("🌍 Checking geo-locations...")
    country_nodes = defaultdict(list)
    
    for idx, node in enumerate(all_nodes, 1):
        if idx % 10 == 0:
            print(f"   Processing {idx}/{len(all_nodes)}...")
        
        server = get_node_server(node)
        if server:
            country_code = get_server_location(server)
            country_nodes[country_code].append(node)
    
    # Rename nodes with clean format
    renamed_nodes = []
    
    # Process Singapore nodes first
    if 'SG' in country_nodes:
        print(f"🇸🇬 Processing {len(country_nodes['SG'])} Singapore nodes...")
        for idx, node in enumerate(country_nodes['SG'], 1):
            node['name'] = f"🇸🇬 SG-{idx:03d}"
            renamed_nodes.append(node)
        del country_nodes['SG']
    
    # Process other countries
    for country_code, nodes in country_nodes.items():
        flag = get_flag_by_country_code(country_code)
        print(f"{flag} Processing {len(nodes)} {country_code} nodes...")
        for idx, node in enumerate(nodes, 1):
            node['name'] = f"{flag} {country_code}-{idx:03d}"
            renamed_nodes.append(node)
    
    # Create output structure
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
        f.write("# Generated by Clash-Aggregator\n")
        f.write("# GitHub: https://github.com/YOUR_USERNAME/Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Total nodes: {len(renamed_nodes)}")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
