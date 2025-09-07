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
        'PR': '🇵🇷', 'VI': '🇻🇮', 'CU': '🇨🇺', 'HT': '🇭🇹', 'GP': '🇬🇵'
    }
    return flags.get(code.upper(), '🌍')

def validate_and_clean_node(node, node_index=0):
    """Validate and clean node configuration"""
    if not isinstance(node, dict):
        return None
    
    # Required fields for all proxy types
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    # Clean common fields
    node_type = node.get('type', '').lower()
    
    # Skip REALITY and VLESS nodes with reality-opts to avoid issues
    if node_type in ['vless', 'reality'] and 'reality-opts' in node:
        print(f"   ⚠️ Skipping REALITY/VLESS node #{node_index} due to compatibility issues")
        return None
    
    # Also skip if flow field exists (usually indicates XTLS/REALITY)
    if 'flow' in node and node['flow']:
        print(f"   ⚠️ Skipping node #{node_index} with flow field: {node.get('flow')}")
        return None
    
    # Validate port
    try:
        port = int(node.get('port', 0))
        if port <= 0 or port > 65535:
            return None
        node['port'] = port
    except:
        return None
    
    # Type-specific validation
    if node_type == 'ss':
        if 'cipher' not in node or 'password' not in node:
            return None
            
    elif node_type == 'vmess':
        if 'uuid' not in node:
            return None
        # Ensure alterId is integer
        if 'alterId' in node:
            try:
                node['alterId'] = int(node['alterId'])
            except:
                node['alterId'] = 0
                
    elif node_type == 'trojan':
        if 'password' not in node:
            return None
        # Remove skip-cert-verify if false (can cause issues)
        if 'skip-cert-verify' in node and not node['skip-cert-verify']:
            del node['skip-cert-verify']
            
    elif node_type == 'vless':
        if 'uuid' not in node:
            return None
        # Remove all REALITY related fields
        reality_fields = ['reality-opts', 'flow', 'client-fingerprint']
        for field in reality_fields:
            node.pop(field, None)
            
    elif node_type == 'ssr':
        if 'cipher' not in node or 'password' not in node:
            return None
            
    elif node_type == 'http' or node_type == 'https':
        # HTTP/HTTPS proxies are simpler
        pass
        
    elif node_type == 'socks5':
        # SOCKS5 validation
        pass
        
    elif node_type == 'snell':
        if 'psk' not in node:
            return None
            
    elif node_type == 'tuic':
        if 'token' not in node and 'uuid' not in node:
            return None
            
    elif node_type == 'hysteria':
        if 'auth_str' not in node and 'auth' not in node:
            return None
            
    elif node_type == 'hysteria2' or node_type == 'hy2':
        if 'password' not in node:
            return None
        node['type'] = 'hysteria2'  # Normalize type
        
    elif node_type == 'wireguard' or node_type == 'wg':
        if 'private-key' not in node:
            return None
        node['type'] = 'wireguard'  # Normalize type
    else:
        # Unknown type, skip
        print(f"   ⚠️ Skipping unknown proxy type: {node_type}")
        return None
    
    # Remove problematic fields that might cause issues
    problematic_fields = [
        '_index', '_type', 'clashType', 'proxies', 'rules',
        'benchmarkUrl', 'reality-opts', 'flow', 'xudp',
        'packet-encoding', 'client-fingerprint', 'fingerprint'
    ]
    for field in problematic_fields:
        node.pop(field, None)
    
    # Clean up TLS related fields
    if 'tls' in node and isinstance(node['tls'], str):
        node['tls'] = node['tls'].lower() == 'true' or node['tls'] == '1'
    
    # Ensure name exists
    if 'name' not in node:
        node['name'] = 'Unnamed'
    
    return node

def get_server_location(server_ip):
    """Get country code from server IP using ip-api.com"""
    try:
        if not server_ip:
            return 'UN'
        
        # If it's a domain, get the IP
        try:
            socket.inet_aton(server_ip)
            ip = server_ip
        except socket.error:
            try:
                ip = socket.gethostbyname(server_ip)
            except:
                return 'UN'
        
        # Query ip-api.com for location
        response = requests.get(
            f'http://ip-api.com/json/{ip}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                country_code = data.get('countryCode', 'UN')
                return country_code
        
        time.sleep(0.5)  # Rate limiting
        return 'UN'
        
    except Exception as e:
        return 'UN'

def get_node_server(node):
    """Extract server address from node"""
    if isinstance(node, dict):
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
                
            # Parse vmess://
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
                        'cipher': vmess_node.get('scy', 'auto')
                    }
                    
                    # TLS
                    if vmess_node.get('tls') == 'tls':
                        node['tls'] = True
                    
                    # Network type
                    if vmess_node.get('net'):
                        node['network'] = vmess_node['net']
                        
                    # WebSocket options
                    if vmess_node.get('net') == 'ws':
                        ws_opts = {}
                        if vmess_node.get('host'):
                            ws_opts['headers'] = {'Host': vmess_node['host']}
                        if vmess_node.get('path'):
                            ws_opts['path'] = vmess_node['path']
                        if ws_opts:
                            node['ws-opts'] = ws_opts
                    
                    nodes.append(node)
                except:
                    continue
                    
            # Parse ss://
            elif line.startswith('ss://'):
                try:
                    ss_data = line[5:]
                    if '#' in ss_data:
                        ss_main, ss_name = ss_data.split('#', 1)
                        ss_name = requests.utils.unquote(ss_name)
                    else:
                        ss_main = ss_data
                        ss_name = 'Unnamed'
                    
                    if '@' in ss_main:
                        method_pass = ss_main.split('@')[0]
                        server_port = ss_main.split('@')[1]
                        
                        try:
                            decoded_mp = base64.b64decode(method_pass + '=' * (4 - len(method_pass) % 4)).decode('utf-8')
                            cipher, password = decoded_mp.split(':', 1)
                        except:
                            continue
                            
                        if ':' in server_port:
                            server, port = server_port.rsplit(':', 1)
                            if '?' in port:
                                port = port.split('?')[0]
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
                    
            # Parse trojan://
            elif line.startswith('trojan://'):
                try:
                    trojan_data = line[9:]
                    if '#' in trojan_data:
                        trojan_main, trojan_name = trojan_data.split('#', 1)
                        trojan_name = requests.utils.unquote(trojan_name)
                    else:
                        trojan_main = trojan_data
                        trojan_name = 'Unnamed'
                    
                    if '@' in trojan_main:
                        password = trojan_main.split('@')[0]
                        server_part = trojan_main.split('@')[1]
                        
                        if ':' in server_part:
                            server, port = server_part.rsplit(':', 1)
                            if '?' in port:
                                port = port.split('?')[0]
                        else:
                            continue
                    else:
                        continue
                    
                    node = {
                        'name': trojan_name,
                        'type': 'trojan',
                        'server': server,
                        'port': int(port),
                        'password': password
                    }
                    nodes.append(node)
                except:
                    continue
                    
            # Skip vless:// for now (often has REALITY issues)
            elif line.startswith('vless://'):
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
        
        # Try parsing as YAML first
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
        
        # Try base64 decode
        nodes = parse_base64_nodes(content)
        if nodes:
            return nodes
        
        return []
        
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
        return []

def main():
    print("🚀 Starting Clash Aggregator...")
    print("=" * 50)
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Found {len(urls)} subscription URLs")
    
    # Statistics
    stats = {
        'total_fetched': 0,
        'valid_nodes': 0,
        'skipped_reality': 0,
        'invalid_nodes': 0
    }
    
    # Collect all nodes
    all_nodes = []
    seen_servers = set()
    
    for idx, url in enumerate(urls, 1):
        print(f"\n📥 Fetching subscription {idx}/{len(urls)}...")
        print(f"   URL: {url[:50]}...")
        nodes = fetch_subscription(url)
        stats['total_fetched'] += len(nodes)
        
        for node_idx, node in enumerate(nodes):
            # Validate and clean the node
            cleaned_node = validate_and_clean_node(node, node_idx)
            if cleaned_node:
                server = get_node_server(cleaned_node)
                if server and server not in seen_servers:
                    seen_servers.add(server)
                    all_nodes.append(cleaned_node)
                    stats['valid_nodes'] += 1
            else:
                stats['invalid_nodes'] += 1
    
    print(f"\n📊 Statistics:")
    print(f"   Total nodes fetched: {stats['total_fetched']}")
    print(f"   Valid nodes: {stats['valid_nodes']}")
    print(f"   Invalid/skipped nodes: {stats['invalid_nodes']}")
    
    # Get geo-location for each node
    print(f"\n🌍 Checking geo-locations for {len(all_nodes)} nodes...")
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
        print(f"\n🇸🇬 Processing {len(country_nodes['SG'])} Singapore nodes...")
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
        f.write("# Note: REALITY/VLESS nodes with flow are excluded for compatibility\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Final output: {len(renamed_nodes)} nodes")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
