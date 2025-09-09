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
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global statistics for debugging
STATS = {
    'total_fetched': 0,
    'after_validation': 0,
    'after_dedup': 0,
    'after_health_check': 0,
    'sg_found': 0,
    'sg_lost_in_geo': 0,
    'parse_errors': 0,
    'health_failures': 0,
    'vless_skipped': 0
}

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
        'ZA': '🇿🇦', 'EG': '🇪🇬', 'KE': '🇰🇪', 'IL': '🇮🇱', 'SA': '🇸🇦'
    }
    return flags.get(code.upper(), '🌍')

def is_singapore_node(node):
    """Check if node is likely Singapore based on multiple signals"""
    server = get_node_server(node)
    name = node.get('name', '').lower()
    
    # Strong indicators for Singapore
    sg_indicators = [
        'singapore', 'sg', '新加坡', 'singapura', 'sgp',
        'sin', 'lion city', '狮城', 'sg01', 'sg02', 'sg03',
        'sg-', '_sg', '-sg', 'aws-sg', 'do-sg', 'vultr-sg'
    ]
    
    # Check node name
    for indicator in sg_indicators:
        if indicator in name:
            return True
    
    # Check server domain
    if server:
        server_lower = server.lower()
        for indicator in sg_indicators:
            if indicator in server_lower:
                return True
        
        # Check Singapore domains
        if '.sg' in server_lower or 'singapore' in server_lower:
            return True
    
    return False

def test_proxy_enhanced(node, quick_mode=False):
    """Enhanced testing with Singapore-aware detection"""
    global STATS
    server = get_node_server(node)
    port = node.get('port')
    
    if not server or not port:
        return None, False
    
    # If quick mode, skip health check
    if quick_mode:
        # Just do geo-location
        country = detect_country_smart(server, node)
        return country, True
    
    # Test TCP connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # Shorter timeout for speed
        
        try:
            ip = socket.gethostbyname(server)
        except:
            STATS['health_failures'] += 1
            return None, False
        
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        if result != 0:
            STATS['health_failures'] += 1
            return None, False
        
        # Get country with Singapore priority
        country = detect_country_smart(server, node)
        return country, True
        
    except:
        STATS['health_failures'] += 1
        return None, False

def detect_country_smart(server, node):
    """Smart country detection with Singapore priority"""
    global STATS
    
    # First, check if it's obviously Singapore
    if is_singapore_node(node):
        STATS['sg_found'] += 1
        return 'SG'
    
    # Try to resolve to IP
    try:
        ip = socket.gethostbyname(server)
    except:
        ip = server
    
    # Singapore IP ranges (common hosting providers in SG)
    sg_ip_patterns = [
        r'^103\.253\.14[4-7]\.',  # Singapore hosting
        r'^103\.28\.5[4-5]\.',    # Singapore servers
        r'^128\.199\.8[0-9]\.',   # DigitalOcean Singapore
        r'^139\.59\.1[0-2][0-9]\.', # DigitalOcean Singapore
        r'^188\.166\.1[7-9][0-9]\.', # DigitalOcean Singapore  
        r'^206\.189\.[0-4][0-9]\.', # DigitalOcean Singapore
        r'^13\.250\.',            # AWS Singapore
        r'^13\.251\.',            # AWS Singapore
        r'^52\.76\.',             # AWS Singapore
        r'^52\.77\.',             # AWS Singapore
        r'^54\.25[1-5]\.',        # AWS Singapore
        r'^175\.41\.',            # AWS Singapore
        r'^46\.137\.2[0-5][0-9]\.', # AWS Singapore
        r'^52\.221\.',            # AWS Singapore
        r'^54\.169\.',            # AWS Singapore
        r'^122\.248\.',           # AWS Singapore
    ]
    
    for pattern in sg_ip_patterns:
        if re.match(pattern, ip):
            STATS['sg_found'] += 1
            return 'SG'
    
    # Check with API
    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,countryCode,country,city',
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('countryCode', 'UN')
                city = data.get('city', '').lower()
                
                # Double-check for Singapore
                if country == 'SG' or 'singapore' in city:
                    STATS['sg_found'] += 1
                    return 'SG'
                
                # If API says it's not SG but we think it is, trust our detection
                if is_singapore_node(node):
                    STATS['sg_lost_in_geo'] += 1
                    return 'SG'  # Override API result
                
                return country.upper()
    except:
        pass
    
    # If all else fails but node indicates Singapore
    if is_singapore_node(node):
        STATS['sg_found'] += 1
        return 'SG'
    
    return 'UN'

def batch_test_with_diagnostics(nodes, max_workers=50, quick_mode=False):
    """Test proxies with detailed diagnostics"""
    print(f"\n🔬 Testing {len(nodes)} proxies...")
    print(f"   Mode: {'Quick (no health check)' if quick_mode else 'Full (with health check)'}")
    
    valid_nodes = []
    country_stats = defaultdict(int)
    sg_nodes_found = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(test_proxy_enhanced, node, quick_mode): node for node in nodes}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_node):
            completed += 1
            if completed % 50 == 0:
                print(f"   Progress: {completed}/{len(nodes)} tested...")
            
            node = future_to_node[future]
            try:
                country, is_alive = future.result()
                
                if is_alive:
                    node['detected_country'] = country
                    valid_nodes.append(node)
                    country_stats[country] += 1
                    
                    if country == 'SG':
                        sg_nodes_found.append(node)
            except:
                pass
    
    print(f"\n   ✅ Testing Complete:")
    print(f"      Valid nodes: {len(valid_nodes)}")
    print(f"      🇸🇬 Singapore nodes found: {len(sg_nodes_found)}")
    
    return valid_nodes, country_stats

def validate_and_clean_node(node, relaxed=False):
    """Validate node - with relaxed mode for keeping more nodes"""
    global STATS
    
    if not isinstance(node, dict):
        return None
    
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    node_type = node.get('type', '').lower()
    
    # In relaxed mode, keep VLESS nodes without reality-opts
    if not relaxed:
        if node_type in ['vless', 'reality'] and ('reality-opts' in node or 'flow' in node):
            STATS['vless_skipped'] += 1
            return None
    else:
        # Only skip if has reality-opts, keep regular VLESS
        if 'reality-opts' in node:
            STATS['vless_skipped'] += 1
            return None
    
    # Validate port
    try:
        port = int(node.get('port', 0))
        if port <= 0 or port > 65535:
            return None
        node['port'] = port
    except:
        return None
    
    # Clean problematic fields
    problematic_fields = [
        '_index', '_type', 'clashType', 'proxies', 'rules',
        'benchmarkUrl', 'reality-opts', 'flow', 'xudp',
        'packet-encoding', 'client-fingerprint', 'fingerprint'
    ]
    for field in problematic_fields:
        node.pop(field, None)
    
    if 'name' not in node:
        node['name'] = 'Unnamed'
    
    STATS['after_validation'] += 1
    return node

def get_node_server(node):
    """Extract server address from node"""
    if isinstance(node, dict):
        for field in ['server', 'add', 'address', 'host']:
            if field in node:
                return node[field]
    return None

def get_node_key(node):
    """Get unique key for node (for better deduplication)"""
    server = get_node_server(node)
    port = node.get('port', '')
    node_type = node.get('type', '')
    
    # Use server+port+type as unique key (not just server)
    return f"{server}:{port}:{node_type}"

# [Keep all parsing functions from before]
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
        STATS['parse_errors'] += 1
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
        STATS['parse_errors'] += 1
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
        STATS['parse_errors'] += 1
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
            
            if decoded.startswith(('vmess://', 'ss://', 'trojan://', 'vless://')):
                nodes.extend(parse_url_node(decoded))
            elif decoded.startswith('{'):
                v2ray_node = json.loads(decoded)
                clash_node = convert_v2ray_to_clash(v2ray_node)
                if clash_node:
                    nodes.append(clash_node)
        except:
            if line.startswith(('vmess://', 'ss://', 'trojan://', 'vless://')):
                nodes.extend(parse_url_node(line))
    
    return nodes

def parse_url_node(url):
    """Parse single URL node - including VLESS support"""
    nodes = []
    
    if url.startswith('vmess://'):
        try:
            vmess_data = base64.b64decode(url[8:]).decode('utf-8')
            vmess_node = json.loads(vmess_data)
            node = convert_v2ray_to_clash(vmess_node)
            if node:
                nodes.append(node)
        except:
            STATS['parse_errors'] += 1
            
    elif url.startswith('vless://'):
        # Basic VLESS parsing (without REALITY)
        try:
            vless_data = url[8:]
            if '#' in vless_data:
                vless_main, vless_name = vless_data.split('#', 1)
                vless_name = urllib.parse.unquote(vless_name)
            else:
                vless_main = vless_data
                vless_name = 'Unnamed'
            
            if '@' in vless_main:
                uuid = vless_main.split('@')[0]
                server_part = vless_main.split('@')[1]
                
                if ':' in server_part:
                    server, port_query = server_part.rsplit(':', 1)
                    port = port_query.split('?')[0]
                    
                    node = {
                        'name': vless_name,
                        'type': 'vless',
                        'server': server,
                        'port': int(port),
                        'uuid': uuid,
                        'udp': True,
                        'skip-cert-verify': True
                    }
                    
                    # Parse query parameters
                    if '?' in port_query:
                        params = urllib.parse.parse_qs(port_query.split('?')[1])
                        if 'security' in params and params['security'][0] == 'tls':
                            node['tls'] = True
                        if 'sni' in params:
                            node['servername'] = params['sni'][0]
                    
                    nodes.append(node)
        except:
            STATS['parse_errors'] += 1
            
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
                method_pass_encoded = ss_main.split('@')[0]
                server_port = ss_main.split('@')[1]
                
                try:
                    padding = 4 - len(method_pass_encoded) % 4
                    if padding != 4:
                        method_pass_encoded += '=' * padding
                    
                    decoded_mp = base64.b64decode(method_pass_encoded).decode('utf-8')
                    
                    if ':' in decoded_mp:
                        cipher, password = decoded_mp.split(':', 1)
                    else:
                        return nodes
                except:
                    method_pass_encoded = urllib.parse.unquote(method_pass_encoded)
                    try:
                        decoded_mp = base64.b64decode(method_pass_encoded + '=' * (4 - len(method_pass_encoded) % 4)).decode('utf-8')
                        if ':' in decoded_mp:
                            cipher, password = decoded_mp.split(':', 1)
                        else:
                            return nodes
                    except:
                        return nodes
                
                if ':' in server_port:
                    server, port_query = server_port.rsplit(':', 1)
                    port = port_query.split('?')[0].split('/')[0]
                else:
                    return nodes
            else:
                try:
                    padding = 4 - len(ss_main) % 4
                    if padding != 4:
                        ss_main += '=' * padding
                    
                    decoded = base64.b64decode(ss_main).decode('utf-8')
                    
                    if '@' in decoded:
                        method_pass, server_port = decoded.split('@', 1)
                        if ':' in method_pass:
                            cipher, password = method_pass.split(':', 1)
                        else:
                            return nodes
                        
                        if ':' in server_port:
                            server, port = server_port.rsplit(':', 1)
                        else:
                            return nodes
                    else:
                        return nodes
                except:
                    return nodes
            
            valid_ciphers = [
                'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
                'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
                'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
                'rc4-md5', 'chacha20', 'chacha20-ietf', 'chacha20-ietf-poly1305',
                'xchacha20-ietf-poly1305'
            ]
            
            if cipher.lower() not in valid_ciphers:
                return nodes
            
            try:
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
                STATS['parse_errors'] += 1
                
        except:
            STATS['parse_errors'] += 1
            
    elif url.startswith('trojan://'):
        try:
            trojan_data = url[9:]
            if '#' in trojan_data:
                trojan_main, trojan_name = trojan_data.split('#', 1)
                trojan_name = urllib.parse.unquote(trojan_name)
            else:
                trojan_main = trojan_data
                trojan_name = 'Unnamed'
            
            if '@' in trojan_main:
                password = trojan_main.split('@')[0]
                server_part = trojan_main.split('@')[1]
                
                if ':' in server_part:
                    server, port_query = server_part.rsplit(':', 1)
                    port = port_query.split('?')[0].split('/')[0]
                else:
                    return nodes
            else:
                return nodes
            
            try:
                node = {
                    'name': trojan_name,
                    'type': 'trojan',
                    'server': server,
                    'port': int(port),
                    'password': password
                }
                nodes.append(node)
            except:
                STATS['parse_errors'] += 1
                
        except:
            STATS['parse_errors'] += 1
    
    return nodes

def fetch_subscription(url):
    """Fetch and decode subscription content"""
    try:
        headers = {
            'User-Agent': 'clash-verge/1.0'
        }
        response = requests.get(url, timeout=10, headers=headers)
        content = response.text.strip()
        
        if not content:
            return []
        
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data.get('proxies', [])
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

def create_proxy_groups(all_node_names, sg_node_names):
    """Create proxy groups configuration"""
    proxy_groups = [
        {
            'name': '🔥 ember',
            'type': 'select',
            'proxies': [
                '🌏 ⚡',
                '🇸🇬 ⚡',
                '🌏 ⚖️',
                '🇸🇬 ⚖️'
            ]
        },
        {
            'name': '🌏 ⚡',
            'type': 'url-test',
            'proxies': all_node_names,
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '🇸🇬 ⚡',
            'type': 'url-test',
            'proxies': sg_node_names if sg_node_names else ['DIRECT'],
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '🌏 ⚖️',
            'type': 'load-balance',
            'proxies': all_node_names,
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'strategy': 'round-robin'
        },
        {
            'name': '🇸🇬 ⚖️',
            'type': 'load-balance',
            'proxies': sg_node_names if sg_node_names else ['DIRECT'],
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'strategy': 'round-robin'
        }
    ]
    
    return proxy_groups

def main():
    global STATS
    
    print("🚀 Starting Clash Aggregator (Diagnostic Mode)...")
    print("=" * 50)
    
    # Configuration
    ENABLE_HEALTH_CHECK = False  # Set to False for more nodes
    RELAXED_VALIDATION = True   # Keep more node types
    QUICK_MODE = True           # Skip health check, just geo
    MAX_WORKERS = 50
    
    print(f"📋 Configuration:")
    print(f"   Health Check: {'Enabled' if ENABLE_HEALTH_CHECK else 'Disabled'}")
    print(f"   Validation: {'Relaxed' if RELAXED_VALIDATION else 'Strict'}")
    print(f"   Mode: {'Quick (no connectivity test)' if QUICK_MODE else 'Full'}")
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"\n📥 Found {len(urls)} subscription URLs")
    
    # Collect all nodes
    all_nodes = []
    seen_node_keys = set()
    
    for idx, url in enumerate(urls, 1):
        print(f"\n📥 Fetching subscription {idx}/{len(urls)}...")
        nodes = fetch_subscription(url)
        
        if nodes is None:
            nodes = []
        
        STATS['total_fetched'] += len(nodes)
        print(f"   Raw nodes: {len(nodes)}")
        
        valid_count = 0
        sg_count = 0
        
        for node in nodes:
            # Check if likely Singapore before validation
            if is_singapore_node(node):
                sg_count += 1
            
            cleaned_node = validate_and_clean_node(node, relaxed=RELAXED_VALIDATION)
            if cleaned_node:
                node_key = get_node_key(cleaned_node)
                
                # Better deduplication (server+port+type)
                if node_key not in seen_node_keys:
                    seen_node_keys.add(node_key)
                    all_nodes.append(cleaned_node)
                    valid_count += 1
        
        print(f"   Valid nodes: {valid_count}")
        print(f"   Potential SG nodes: {sg_count}")
    
    STATS['after_dedup'] = len(all_nodes)
    
    print(f"\n📊 Collection Summary:")
    print(f"   Total fetched: {STATS['total_fetched']}")
    print(f"   After validation: {STATS['after_validation']}")
    print(f"   After deduplication: {STATS['after_dedup']}")
    print(f"   VLESS skipped: {STATS['vless_skipped']}")
    print(f"   Parse errors: {STATS['parse_errors']}")
    
    if not all_nodes:
        print("\n⚠️ No valid nodes found!")
        return
    
    # Test nodes
    if ENABLE_HEALTH_CHECK or QUICK_MODE:
        valid_nodes, country_stats = batch_test_with_diagnostics(
            all_nodes, 
            max_workers=MAX_WORKERS,
            quick_mode=QUICK_MODE
        )
    else:
        # No testing, just use all nodes
        valid_nodes = all_nodes
        country_stats = defaultdict(int)
        for node in valid_nodes:
            country = detect_country_smart(get_node_server(node), node)
            node['detected_country'] = country
            country_stats[country] += 1
    
    STATS['after_health_check'] = len(valid_nodes)
    
    # Show statistics
    print(f"\n📊 Final Statistics:")
    print(f"   Health failures: {STATS['health_failures']}")
    print(f"   Valid nodes after testing: {STATS['after_health_check']}")
    print(f"   🇸🇬 Singapore nodes found: {STATS['sg_found']}")
    print(f"   🇸🇬 Singapore nodes lost in geo: {STATS['sg_lost_in_geo']}")
    
    # Country distribution
    if country_stats:
        print(f"\n🌍 Country Distribution:")
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:15]:
            flag = get_flag_by_country_code(country)
            print(f"   {flag} {country}: {count} nodes")
    
    # Group by country
    country_nodes = defaultdict(list)
    for node in valid_nodes:
        country = node.get('detected_country', 'UN')
        country_nodes[country].append(node)
    
    # Process nodes
    renamed_nodes = []
    sg_node_names = []
    all_node_names = []
    
    # Singapore first
    if 'SG' in country_nodes:
        print(f"\n🇸🇬 Processing {len(country_nodes['SG'])} Singapore nodes...")
        for idx, node in enumerate(country_nodes['SG'], 1):
            node_name = f"🇸🇬 SG-{idx:03d}"
            node['name'] = node_name
            node.pop('detected_country', None)
            renamed_nodes.append(node)
            sg_node_names.append(node_name)
            all_node_names.append(node_name)
        del country_nodes['SG']
    
    # Other countries
    for country_code in sorted(country_nodes.keys()):
        nodes = country_nodes[country_code]
        flag = get_flag_by_country_code(country_code)
        
        for idx, node in enumerate(nodes, 1):
            node_name = f"{flag} {country_code}-{idx:03d}"
            node['name'] = node_name
            node.pop('detected_country', None)
            renamed_nodes.append(node)
            all_node_names.append(node_name)
    
    # Ensure we have nodes for groups
    if not all_node_names:
        all_node_names = ['DIRECT']
    if not sg_node_names:
        sg_node_names = ['DIRECT']
    
    # Create output
    proxy_groups = create_proxy_groups(all_node_names, sg_node_names)
    
    rules = [
        'GEOIP,PRIVATE,DIRECT',
        'MATCH,🔥 ember'
    ]
    
    output = {
        'proxies': renamed_nodes,
        'proxy-groups': proxy_groups,
        'rules': rules
    }
    
    # Write output
    tz = pytz.timezone('Asia/Singapore')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    with open('clash.yaml', 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(renamed_nodes)}\n")
        f.write(f"# Singapore Nodes: {len(sg_node_names)}\n")
        f.write(f"# Mode: {'Quick' if QUICK_MODE else 'Full'} | Health Check: {'On' if ENABLE_HEALTH_CHECK else 'Off'}\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Total: {len(renamed_nodes)} proxies")
    print(f"🇸🇬 Singapore: {len(sg_node_names)} nodes")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
