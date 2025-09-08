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

def check_node_health(node):
    """Check if a node is reachable"""
    server = get_node_server(node)
    port = node.get('port', 443)
    
    if not server or not port:
        return False
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        try:
            ip = socket.gethostbyname(server)
        except:
            return False
        
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        return result == 0
    except:
        return False

def batch_health_check(nodes, max_workers=50):
    """Check health of multiple nodes in parallel"""
    print(f"\n🏥 Starting health check for {len(nodes)} nodes...")
    healthy_nodes = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(check_node_health, node): node for node in nodes}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_node):
            completed += 1
            if completed % 20 == 0:
                print(f"   Checked {completed}/{len(nodes)} nodes...")
            
            node = future_to_node[future]
            try:
                if future.result():
                    healthy_nodes.append(node)
            except:
                pass
    
    print(f"   ✅ {len(healthy_nodes)} healthy nodes found")
    return healthy_nodes

def get_server_location(server_ip, debug=False):
    """Get country code using ipinfo.io with debug info"""
    if not server_ip:
        return 'UN'
    
    # Resolve domain to IP if needed
    try:
        socket.inet_aton(server_ip)
        ip = server_ip
    except socket.error:
        try:
            ip = socket.gethostbyname(server_ip)
        except Exception as e:
            if debug:
                print(f"   ⚠️ Cannot resolve {server_ip}: {e}")
            return 'UN'
    
    try:
        response = requests.get(
            f'https://ipinfo.io/{ip}/json',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Debug: Check for bogus/proxy data
            if debug and 'bogon' in data and data['bogon']:
                print(f"   ⚠️ Bogon IP detected: {ip}")
                return 'UN'
            
            country_code = data.get('country', 'UN')
            
            # Debug: Print unexpected country codes
            if debug and country_code and len(country_code) != 2:
                print(f"   ⚠️ Unusual country code for {ip}: {country_code}")
            
            # Debug: Check if this is a known VPN/hosting provider
            if debug:
                org = data.get('org', '').lower()
                if any(provider in org for provider in ['cloudflare', 'amazon', 'google', 'microsoft', 'digitalocean', 'linode']):
                    print(f"   📡 {ip} is from {org} (reported as {country_code})")
            
            return country_code.upper()
        else:
            if debug:
                print(f"   ❌ ipinfo.io returned {response.status_code} for {ip}")
            return 'UN'
        
    except Exception as e:
        if debug:
            print(f"   ❌ Error checking {server_ip}: {e}")
        return 'UN'

def parse_v2ray_json(content):
    """Parse V2Ray JSON format"""
    nodes = []
    try:
        data = json.loads(content)
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'ps' in item:
                    node = convert_v2ray_to_clash(item)
                    if node:
                        nodes.append(node)
        elif isinstance(data, dict):
            if 'outbounds' in data:
                for outbound in data['outbounds']:
                    if outbound.get('protocol') in ['vmess', 'shadowsocks', 'trojan', 'vless']:
                        node = convert_v2ray_outbound_to_clash(outbound)
                        if node:
                            nodes.append(node)
    except:
        pass
    return nodes

def convert_v2ray_to_clash(v2ray_node):
    """Convert V2Ray node to Clash format"""
    try:
        if v2ray_node.get('net') == 'tcp' and v2ray_node.get('type') == 'http':
            return None
            
        node = {
            'name': v2ray_node.get('ps', 'Unnamed'),
            'type': 'vmess',
            'server': v2ray_node.get('add', v2ray_node.get('address', '')),
            'port': int(v2ray_node.get('port', 443)),
            'uuid': v2ray_node.get('id', ''),
            'alterId': int(v2ray_node.get('aid', 0)),
            'cipher': v2ray_node.get('scy', 'auto')
        }
        
        if v2ray_node.get('tls') == 'tls':
            node['tls'] = True
            if v2ray_node.get('sni'):
                node['sni'] = v2ray_node['sni']
        
        net = v2ray_node.get('net', 'tcp')
        if net and net != 'tcp':
            node['network'] = net
            
        if net == 'ws':
            ws_opts = {}
            if v2ray_node.get('host'):
                ws_opts['headers'] = {'Host': v2ray_node['host']}
            if v2ray_node.get('path'):
                ws_opts['path'] = v2ray_node['path']
            if ws_opts:
                node['ws-opts'] = ws_opts
                
        elif net == 'grpc':
            if v2ray_node.get('path'):
                node['grpc-opts'] = {
                    'grpc-service-name': v2ray_node['path']
                }
        
        return node
    except:
        return None

def convert_v2ray_outbound_to_clash(outbound):
    """Convert V2Ray outbound to Clash format"""
    try:
        protocol = outbound.get('protocol')
        settings = outbound.get('settings', {})
        stream = outbound.get('streamSettings', {})
        
        if protocol == 'vmess':
            vnext = settings.get('vnext', [{}])[0]
            user = vnext.get('users', [{}])[0]
            
            node = {
                'name': outbound.get('tag', 'Unnamed'),
                'type': 'vmess',
                'server': vnext.get('address', ''),
                'port': vnext.get('port', 443),
                'uuid': user.get('id', ''),
                'alterId': user.get('alterId', 0),
                'cipher': user.get('security', 'auto')
            }
            
        elif protocol == 'shadowsocks':
            server = settings.get('servers', [{}])[0]
            node = {
                'name': outbound.get('tag', 'Unnamed'),
                'type': 'ss',
                'server': server.get('address', ''),
                'port': server.get('port', 443),
                'cipher': server.get('method', ''),
                'password': server.get('password', '')
            }
            
        elif protocol == 'trojan':
            server = settings.get('servers', [{}])[0]
            node = {
                'name': outbound.get('tag', 'Unnamed'),
                'type': 'trojan',
                'server': server.get('address', ''),
                'port': server.get('port', 443),
                'password': server.get('password', '')
            }
        else:
            return None
            
        if stream.get('security') == 'tls':
            node['tls'] = True
            tls_settings = stream.get('tlsSettings', {})
            if tls_settings.get('serverName'):
                node['sni'] = tls_settings['serverName']
                
        network = stream.get('network', 'tcp')
        if network != 'tcp':
            node['network'] = network
            
        return node
    except:
        return None

def parse_base64_list(content):
    """Parse pure base64 encoded list"""
    nodes = []
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            decoded = base64.b64decode(line + '=' * (4 - len(line) % 4)).decode('utf-8')
            
            if decoded.startswith(('vmess://', 'ss://', 'trojan://')):
                nodes.extend(parse_url_node(decoded))
            elif decoded.startswith('{'):
                v2ray_node = json.loads(decoded)
                clash_node = convert_v2ray_to_clash(v2ray_node)
                if clash_node:
                    nodes.append(clash_node)
        except:
            if line.startswith(('vmess://', 'ss://', 'trojan://')):
                nodes.extend(parse_url_node(line))
    
    return nodes

def parse_url_node(url):
    """Parse single URL node"""
    nodes = []
    
    if url.startswith('vmess://'):
        try:
            vmess_data = base64.b64decode(url[8:]).decode('utf-8')
            vmess_node = json.loads(vmess_data)
            node = convert_v2ray_to_clash(vmess_node)
            if node:
                nodes.append(node)
        except:
            pass
            
    elif url.startswith('ss://'):
        try:
            ss_data = url[5:]
            if '#' in ss_data:
                ss_main, ss_name = ss_data.split('#', 1)
                ss_name = urllib.parse.unquote(ss_name)
            else:
                ss_main = ss_data
                ss_name = 'Unnamed'
            
            if '@' in ss_main:
                method_pass = ss_main.split('@')[0]
                server_port = ss_main.split('@')[1]
                
                decoded_mp = base64.b64decode(method_pass + '=' * (4 - len(method_pass) % 4)).decode('utf-8')
                cipher, password = decoded_mp.split(':', 1)
                
                server, port = server_port.rsplit(':', 1)
                if '?' in port:
                    port = port.split('?')[0]
                
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
            pass
            
    elif url.startswith('trojan://'):
        try:
            trojan_data = url[9:]
            if '#' in trojan_data:
                trojan_main, trojan_name = trojan_data.split('#', 1)
                trojan_name = urllib.parse.unquote(trojan_name)
            else:
                trojan_main = trojan_data
                trojan_name = 'Unnamed'
            
            password, server_part = trojan_main.split('@', 1)
            server, port = server_part.rsplit(':', 1)
            if '?' in port:
                port = port.split('?')[0]
            
            node = {
                'name': trojan_name,
                'type': 'trojan',
                'server': server,
                'port': int(port),
                'password': password
            }
            nodes.append(node)
        except:
            pass
    
    return nodes

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

def get_node_server(node):
    """Extract server address from node"""
    if isinstance(node, dict):
        for field in ['server', 'add', 'address', 'host']:
            if field in node:
                return node[field]
    return None

def fetch_subscription(url):
    """Fetch and decode subscription content"""
    try:
        headers = {
            'User-Agent': 'clash-verge/1.0'
        }
        response = requests.get(url, timeout=10, headers=headers)
        content = response.text.strip()
        
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
        
        if content.startswith('{') or content.startswith('['):
            nodes = parse_v2ray_json(content)
            if nodes:
                return nodes
        
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            
            if decoded.startswith('{') or decoded.startswith('['):
                nodes = parse_v2ray_json(decoded)
                if nodes:
                    return nodes
            
            nodes = parse_base64_list(decoded)
            if nodes:
                return nodes
        except:
            pass
        
        nodes = parse_base64_list(content)
        if nodes:
            return nodes
        
        return []
        
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
        return []

def main():
    print("🚀 Starting Clash Aggregator with Debug Mode...")
    print("=" * 50)
    
    # Configuration
    ENABLE_HEALTH_CHECK = False  # Disabled for faster debugging
    DEBUG_MODE = True  # Enable detailed logging
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Found {len(urls)} subscription URLs")
    print(f"🔍 Debug Mode: ON - Will show geo-location details")
    
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
    
    if ENABLE_HEALTH_CHECK and all_nodes:
        all_nodes = batch_health_check(all_nodes)
        if not all_nodes:
            print("⚠️ No healthy nodes found! Exiting...")
            return
    
    # Sample check - verify first few nodes in detail
    print(f"\n🌍 Checking geo-locations...")
    
    if DEBUG_MODE and all_nodes:
        sample_size = min(5, len(all_nodes))
        print(f"\n🔬 Sampling first {sample_size} nodes for detailed check:")
        
        for idx, node in enumerate(all_nodes[:sample_size], 1):
            server = get_node_server(node)
            original_name = node.get('name', 'Unknown')
            print(f"\n   Node {idx}: {original_name[:50]}...")
            print(f"   Server: {server}")
            
            if server:
                country_code = get_server_location(server, debug=True)
                flag = get_flag_by_country_code(country_code)
                print(f"   Detected: {flag} {country_code}")
    
    # Process all nodes
    country_nodes = defaultdict(list)
    country_stats = defaultdict(int)
    
    print(f"\n📍 Processing all {len(all_nodes)} nodes...")
    
    for idx, node in enumerate(all_nodes, 1):
        if idx % 10 == 0:
            print(f"   Processing {idx}/{len(all_nodes)}...")
        
        server = get_node_server(node)
        if server:
            country_code = get_server_location(server, debug=False)
            country_nodes[country_code].append(node)
            country_stats[country_code] += 1
        
        if idx % 5 == 0:
            time.sleep(0.1)
    
    # Show country distribution
    if DEBUG_MODE:
        print(f"\n📊 Country Distribution:")
        for country_code, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            flag = get_flag_by_country_code(country_code)
            print(f"   {flag} {country_code}: {count} nodes")
        
        missing_flags = [cc for cc in country_stats.keys() if get_flag_by_country_code(cc) == '🌍']
        if missing_flags:
            print(f"\n⚠️ Missing flag mappings for: {', '.join(missing_flags)}")
    
    # Rename nodes
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
        if DEBUG_MODE and flag == '🌍':
            print(f"⚠️ Unknown country code: {country_code} ({len(nodes)} nodes)")
        
        for idx, node in enumerate(nodes, 1):
            node['name'] = f"{flag} {country_code}-{idx:03d}"
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
        f.write(f"# Debug Mode: {DEBUG_MODE}\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Final output: {len(renamed_nodes)} nodes")
    
    # Final check
    if DEBUG_MODE and renamed_nodes:
        print(f"\n🔍 Sample of final renamed nodes:")
        for node in renamed_nodes[:5]:
            print(f"   {node['name']} -> {node['server']}")

if __name__ == "__main__":
    main()
