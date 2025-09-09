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
        'CW': '🇨🇼', 'PR': '🇵🇷', 'TT': '🇹🇹', 'BB': '🇧🇧', 'MT': '🇲🇹',
        'CY': '🇨🇾', 'PA': '🇵🇦', 'CR': '🇨🇷', 'NI': '🇳🇮', 'HN': '🇭🇳'
    }
    return flags.get(code.upper(), '🌍')

def test_proxy_smart(node):
    """Enhanced testing with better geo-detection"""
    server = get_node_server(node)
    port = node.get('port')
    
    if not server or not port:
        return None, False
    
    # Test TCP connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        # Resolve domain to IP
        try:
            ip = socket.gethostbyname(server)
        except:
            return None, False
        
        # Test connection
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        if result != 0:
            return None, False
        
        # Get location with enhanced detection
        country = None
        
        # Special handling for known patterns
        server_lower = server.lower()
        
        # Domain-based hints (more reliable for CDN/relay services)
        domain_hints = {
            '.sg': 'SG', 'singapore': 'SG', 'sgp': 'SG',
            '.jp': 'JP', 'japan': 'JP', 'tokyo': 'JP', 'osaka': 'JP',
            '.kr': 'KR', 'korea': 'KR', 'seoul': 'KR',
            '.hk': 'HK', 'hongkong': 'HK', 'hong-kong': 'HK',
            '.tw': 'TW', 'taiwan': 'TW', 'taipei': 'TW',
            '.us': 'US', 'america': 'US', 'united-states': 'US', 'usa': 'US',
            '.uk': 'GB', 'united-kingdom': 'GB', 'london': 'GB', 'britain': 'GB',
            '.de': 'DE', 'germany': 'DE', 'frankfurt': 'DE', 'berlin': 'DE',
            '.fr': 'FR', 'france': 'FR', 'paris': 'FR',
            '.nl': 'NL', 'netherlands': 'NL', 'amsterdam': 'NL',
            '.ca': 'CA', 'canada': 'CA', 'toronto': 'CA',
            '.au': 'AU', 'australia': 'AU', 'sydney': 'AU',
            '.in': 'IN', 'india': 'IN', 'mumbai': 'IN',
            '.my': 'MY', 'malaysia': 'MY', 'kuala': 'MY',
            '.th': 'TH', 'thailand': 'TH', 'bangkok': 'TH',
            '.vn': 'VN', 'vietnam': 'VN', 'hanoi': 'VN',
            '.id': 'ID', 'indonesia': 'ID', 'jakarta': 'ID',
            '.ph': 'PH', 'philippines': 'PH', 'manila': 'PH',
            '.tr': 'TR', 'turkey': 'TR', 'istanbul': 'TR',
            '.ae': 'AE', 'dubai': 'AE', 'emirates': 'AE',
            '.br': 'BR', 'brazil': 'BR', 'sao-paulo': 'BR',
            '.ru': 'RU', 'russia': 'RU', 'moscow': 'RU',
            '.it': 'IT', 'italy': 'IT', 'milan': 'IT',
            '.es': 'ES', 'spain': 'ES', 'madrid': 'ES',
            '.se': 'SE', 'sweden': 'SE', 'stockholm': 'SE',
            '.no': 'NO', 'norway': 'NO', 'oslo': 'NO',
            '.fi': 'FI', 'finland': 'FI', 'helsinki': 'FI',
            '.pl': 'PL', 'poland': 'PL', 'warsaw': 'PL',
            '.ua': 'UA', 'ukraine': 'UA', 'kiev': 'UA',
            '.za': 'ZA', 'south-africa': 'ZA', 'johannesburg': 'ZA'
        }
        
        # Check domain hints first (more reliable for CDN)
        for hint, cc in domain_hints.items():
            if hint in server_lower:
                country = cc
                break
        
        # If no domain hint, use IP geolocation
        if not country:
            try:
                # Try ip-api.com with more fields
                response = requests.get(
                    f'http://ip-api.com/json/{ip}?fields=status,countryCode,country,city,isp,org,as',
                    timeout=2
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        country = data.get('countryCode', 'UN')
                        
                        # Double-check with city names if available
                        city = data.get('city', '').lower()
                        for hint, cc in domain_hints.items():
                            if hint in city:
                                country = cc
                                break
            except:
                pass
        
        # Fallback to ipinfo.io
        if not country or country == 'UN':
            try:
                response = requests.get(f'https://ipinfo.io/{ip}/json', timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    country = data.get('country', 'UN')
            except:
                pass
        
        if not country:
            country = 'UN'
        
        return country.upper(), True
        
    except:
        return None, False

def batch_test_proxies_smart(nodes, max_workers=30):
    """Test proxies with smart detection"""
    print(f"\n🔬 Testing {len(nodes)} proxies...")
    
    valid_nodes = []
    country_stats = defaultdict(int)
    dead_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(test_proxy_smart, node): node for node in nodes}
        
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
                else:
                    dead_count += 1
            except:
                dead_count += 1
    
    print(f"\n   ✅ Testing Complete:")
    print(f"      Working proxies: {len(valid_nodes)}")
    print(f"      Dead proxies: {dead_count}")
    
    return valid_nodes, country_stats

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

# [Keep all parsing functions - parse_v2ray_json, convert_v2ray_to_clash, etc.]
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
    """Parse single URL node - FIXED SS parsing"""
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
            
            # Extract node name if present
            if '#' in ss_data:
                ss_main, ss_name = ss_data.split('#', 1)
                ss_name = urllib.parse.unquote(ss_name)
            else:
                ss_main = ss_data
                ss_name = 'Unnamed'
            
            # Parse SS URL - there are two formats
            if '@' in ss_main:
                # Format 1: ss://base64(cipher:password)@server:port
                method_pass_encoded = ss_main.split('@')[0]
                server_port = ss_main.split('@')[1]
                
                # Decode the method:password part
                try:
                    # Add padding if needed
                    padding = 4 - len(method_pass_encoded) % 4
                    if padding != 4:
                        method_pass_encoded += '=' * padding
                    
                    # Decode base64
                    decoded_mp = base64.b64decode(method_pass_encoded).decode('utf-8')
                    
                    # Split cipher and password
                    if ':' in decoded_mp:
                        cipher, password = decoded_mp.split(':', 1)
                    else:
                        # Malformed, skip
                        return nodes
                except Exception as e:
                    # Try URL decode first
                    method_pass_encoded = urllib.parse.unquote(method_pass_encoded)
                    try:
                        decoded_mp = base64.b64decode(method_pass_encoded + '=' * (4 - len(method_pass_encoded) % 4)).decode('utf-8')
                        if ':' in decoded_mp:
                            cipher, password = decoded_mp.split(':', 1)
                        else:
                            return nodes
                    except:
                        return nodes
                
                # Parse server and port
                if ':' in server_port:
                    server, port_query = server_port.rsplit(':', 1)
                    # Remove query parameters if present
                    port = port_query.split('?')[0].split('/')[0]
                else:
                    return nodes
                
            else:
                # Format 2: ss://base64(cipher:password@server:port)
                try:
                    # Add padding if needed
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
            
            # Validate cipher method
            valid_ciphers = [
                'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
                'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
                'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
                'rc4-md5', 'chacha20', 'chacha20-ietf', 'chacha20-ietf-poly1305',
                'xchacha20-ietf-poly1305'
            ]
            
            if cipher.lower() not in valid_ciphers:
                print(f"   ⚠️ Invalid SS cipher: {cipher}")
                return nodes
            
            # Create node
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
            except ValueError:
                # Port is not a valid integer
                pass
                
        except Exception as e:
            # Debug output for troubleshooting
            # print(f"   ⚠️ Failed to parse SS URL: {e}")
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
            except ValueError:
                pass
                
        except:
            pass
    
    return nodes

def validate_and_clean_node(node):
    """Validate and clean node configuration - with better SS validation"""
    if not isinstance(node, dict):
        return None
    
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    node_type = node.get('type', '').lower()
    
    # Skip problematic VLESS/REALITY nodes
    if node_type in ['vless', 'reality'] and ('reality-opts' in node or 'flow' in node):
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
        
        # Validate cipher is actually a cipher method, not base64 or malformed
        cipher = node.get('cipher', '')
        valid_ciphers = [
            'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
            'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
            'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
            'rc4-md5', 'chacha20', 'chacha20-ietf', 'chacha20-ietf-poly1305',
            'xchacha20-ietf-poly1305', 'none', 'plain', 'rc4', 'rc4-md5',
            'aes-128-ofb', 'aes-192-ofb', 'aes-256-ofb',
            'aes-128-ccm', 'aes-192-ccm', 'aes-256-ccm',
            '2022-blake3-aes-128-gcm', '2022-blake3-aes-256-gcm',
            '2022-blake3-chacha20-poly1305'
        ]
        
        # Check if cipher looks like base64 or contains colons
        if ':' in cipher or len(cipher) > 30 or cipher.lower() not in valid_ciphers:
            # Try to fix it if it's base64 encoded
            try:
                decoded = base64.b64decode(cipher + '=' * (4 - len(cipher) % 4)).decode('utf-8')
                if ':' in decoded:
                    actual_cipher, actual_password = decoded.split(':', 1)
                    if actual_cipher.lower() in valid_ciphers:
                        node['cipher'] = actual_cipher
                        node['password'] = actual_password
                    else:
                        return None
                else:
                    return None
            except:
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
    
    # Remove problematic fields
    problematic_fields = [
        '_index', '_type', 'clashType', 'proxies', 'rules',
        'benchmarkUrl', 'reality-opts', 'flow', 'xudp',
        'packet-encoding', 'client-fingerprint', 'fingerprint'
    ]
    for field in problematic_fields:
        node.pop(field, None)
    
    # Ensure name exists
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
    """Fetch and decode subscription content - always returns a list"""
    try:
        headers = {
            'User-Agent': 'clash-verge/1.0'
        }
        response = requests.get(url, timeout=10, headers=headers)
        content = response.text.strip()
        
        # Check if content is empty
        if not content:
            print(f"   ⚠️ Empty response from URL")
            return []
        
        # Try parsing as YAML first
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data.get('proxies', [])
            elif isinstance(data, list):
                return data
        except:
            pass
        
        # Try V2Ray JSON format
        if content.startswith('{') or content.startswith('['):
            nodes = parse_v2ray_json(content)
            if nodes:
                return nodes
        
        # Try base64 decode
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
        
        # Try as direct URL list
        nodes = parse_base64_list(content)
        if nodes:
            return nodes
        
        # If nothing worked, return empty list
        return []
        
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
        return []  # Always return a list, even on error

def main():
    print("🚀 Starting Clash Aggregator with Proxy Groups & Rules...")
    print("=" * 50)
    
    # Configuration
    ENABLE_TESTING = True
    EXCLUDE_UNKNOWN = True
    MAX_WORKERS = 30
    
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
        
        # Ensure nodes is always a list
        if nodes is None:
            nodes = []
            print(f"   ⚠️ No valid nodes found")
        else:
            print(f"   Found {len(nodes)} nodes")
        
        for node in nodes:
            cleaned_node = validate_and_clean_node(node)
            if cleaned_node:
                server = get_node_server(cleaned_node)
                if server and server not in seen_servers:
                    seen_servers.add(server)
                    all_nodes.append(cleaned_node)
    
    print(f"\n📊 Collected {len(all_nodes)} unique nodes")
    
    # Check if we have any nodes at all
    if not all_nodes:
        print("\n⚠️ No valid nodes found from any subscription!")
        print("Creating minimal config with DIRECT only...")
        
        # Create minimal output with DIRECT proxy
        output = {
            'proxies': [],
            'proxy-groups': [
                {
                    'name': '🔥 ember',
                    'type': 'select',
                    'proxies': ['DIRECT']
                }
            ],
            'rules': [
                'GEOIP,PRIVATE,DIRECT',
                'MATCH,DIRECT'
            ]
        }
        
        # Write minimal config
        tz = pytz.timezone('Asia/Singapore')
        update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        with open('clash.yaml', 'w', encoding='utf-8') as f:
            f.write(f"# Last Update: {update_time}\n")
            f.write(f"# WARNING: No valid proxies found!\n")
            f.write("# Generated by Clash-Aggregator\n\n")
            yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        print("⚠️ Created minimal config file (DIRECT only)")
        return
    
    # Test proxies
    if ENABLE_TESTING:
        valid_nodes, country_stats = batch_test_proxies_smart(all_nodes, max_workers=MAX_WORKERS)
        
        if not valid_nodes:
            print("\n⚠️ No working proxies found after testing!")
            valid_nodes = all_nodes[:10]  # Use first 10 as fallback
            print(f"   Using first {len(valid_nodes)} nodes as fallback")
            
            # Create fake country stats
            country_stats = defaultdict(int)
            for node in valid_nodes:
                country_stats['UN'] += 1
        
        # Show country distribution
        if country_stats:
            print(f"\n📊 Country Distribution:")
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
        country_nodes = defaultdict(list)
        for node in all_nodes:
            country_nodes['UN'].append(node)
    
    # Rename nodes
    renamed_nodes = []
    sg_node_names = []
    all_node_names = []
    
    # Process Singapore nodes first
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
    
    # Process other countries
    for country_code in sorted(country_nodes.keys()):
        nodes = country_nodes[country_code]
        flag = get_flag_by_country_code(country_code)
        
        for idx, node in enumerate(nodes, 1):
            node_name = f"{flag} {country_code}-{idx:03d}"
            node['name'] = node_name
            node.pop('detected_country', None)
            renamed_nodes.append(node)
            all_node_names.append(node_name)
    
    # Ensure we have at least some nodes for groups
    if not all_node_names:
        all_node_names = ['DIRECT']
    if not sg_node_names:
        sg_node_names = ['DIRECT']
    
    # Create proxy groups
    proxy_groups = create_proxy_groups(all_node_names, sg_node_names)
    
    # Create simple but essential rules
    rules = [
        'GEOIP,PRIVATE,DIRECT',
        'MATCH,🔥 ember'
    ]
    
    # Create output with everything
    output = {
        'proxies': renamed_nodes,
        'proxy-groups': proxy_groups,
        'rules': rules
    }
    
    # Add update time
    tz = pytz.timezone('Asia/Singapore')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Write output file
    with open('clash.yaml', 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(renamed_nodes)}\n")
        f.write(f"# Singapore Nodes: {len(sg_node_names) if sg_node_names != ['DIRECT'] else 0}\n")
        f.write(f"# Proxy Groups: 5 (ember, url-test x2, load-balance x2)\n")
        f.write(f"# Rules: Simple (PRIVATE->DIRECT, ALL->ember)\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Total: {len(renamed_nodes)} proxies")
    print(f"🇸🇬 Singapore: {len(sg_node_names) if sg_node_names != ['DIRECT'] else 0} nodes")
    print(f"📁 Proxy Groups: 5 groups configured")
    print(f"📝 Rules: 2 simple rules (all traffic through proxy)")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
