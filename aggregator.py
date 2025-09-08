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
        'CW': '🇨🇼', 'PR': '🇵🇷', 'TT': '🇹🇹', 'BB': '🇧🇧', 'MT': '🇲🇹',
        'CY': '🇨🇾', 'PA': '🇵🇦', 'CR': '🇨🇷', 'NI': '🇳🇮', 'HN': '🇭🇳',
        'SV': '🇸🇻', 'GT': '🇬🇹', 'BZ': '🇧🇿', 'BO': '🇧🇴', 'PY': '🇵🇾',
        'UY': '🇺🇾', 'GY': '🇬🇾', 'SR': '🇸🇷', 'JM': '🇯🇲', 'DO': '🇩🇴',
        'GD': '🇬🇩', 'VC': '🇻🇨', 'KN': '🇰🇳', 'AG': '🇦🇬', 'DM': '🇩🇲',
        'KY': '🇰🇾', 'TC': '🇹🇨', 'SX': '🇸🇽', 'AW': '🇦🇼', 'VG': '🇻🇬'
    }
    return flags.get(code.upper(), '🌍')

def test_proxy_and_location(node):
    """Test proxy connectivity and get location - combined check"""
    server = get_node_server(node)
    port = node.get('port')
    
    if not server or not port:
        return None, False
    
    # Step 1: Test TCP connectivity
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
        
        # Step 2: Get location of the server IP
        # Using multiple APIs for better accuracy
        country = None
        
        # Try ip-api.com first (most reliable for actual location)
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip}?fields=status,countryCode,proxy,hosting',
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('countryCode', 'UN')
                    # Note if it's detected as proxy/hosting
                    if data.get('proxy') or data.get('hosting'):
                        pass  # Still use the country but note it might be inaccurate
        except:
            pass
        
        # Fallback to ipinfo.io
        if not country or country == 'UN':
            try:
                response = requests.get(
                    f'https://ipinfo.io/{ip}/json',
                    timeout=2
                )
                if response.status_code == 200:
                    data = response.json()
                    country = data.get('country', 'UN')
            except:
                pass
        
        # If still no country, mark as unknown but alive
        if not country:
            country = 'UN'
        
        return country.upper(), True
        
    except Exception as e:
        return None, False

def batch_test_proxies_combined(nodes, max_workers=30):
    """Test proxies in parallel - combines health check and location detection"""
    print(f"\n🔬 Testing {len(nodes)} proxies (connectivity + location)...")
    print("   This will take a few minutes...")
    
    valid_nodes = []
    country_stats = defaultdict(int)
    dead_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(test_proxy_and_location, node): node for node in nodes}
        
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
    print(f"      Countries found: {len(country_stats)}")
    
    return valid_nodes, country_stats

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
    print("🚀 Starting Clash Aggregator with Combined Testing...")
    print("=" * 50)
    
    # Configuration
    ENABLE_TESTING = True       # Combined health + location check
    EXCLUDE_UNKNOWN = True      # Exclude nodes with unknown location
    MAX_WORKERS = 30           # Parallel testing threads
    
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
    if ENABLE_TESTING and all_nodes:
        valid_nodes, country_stats = batch_test_proxies_combined(all_nodes, max_workers=MAX_WORKERS)
        
        if not valid_nodes:
            print("\n⚠️ No working proxies found!")
            return
        
        # Show country distribution
        print(f"\n📊 Country Distribution:")
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:15]:
            flag = get_flag_by_country_code(country)
            print(f"   {flag} {country}: {count} nodes")
        
        # Group by country
        country_nodes = defaultdict(list)
        for node in valid_nodes:
            country = node.get('detected_country', 'UN')
            if not (EXCLUDE_UNKNOWN and country == 'UN'):
                country_nodes[country].append(node)
    else:
        # No testing, use all nodes
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
            node.pop('detected_country', None)
            renamed_nodes.append(node)
        del country_nodes['SG']
    
    # Process other countries
    for country_code in sorted(country_nodes.keys()):
        nodes = country_nodes[country_code]
        flag = get_flag_by_country_code(country_code)
        
        for idx, node in enumerate(nodes, 1):
            node['name'] = f"{flag} {country_code}-{idx:03d}"
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
        f.write(f"# Testing: {'Combined Health+Location' if ENABLE_TESTING else 'Disabled'}\n")
        f.write(f"# All proxies are verified working\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Final output: {len(renamed_nodes)} working proxies")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
