#!/usr/bin/env python3

import yaml
import requests
import socket
import os
import subprocess
import time
import concurrent.futures
from datetime import datetime
import pytz
from collections import defaultdict
import base64
import gzip
import re

def download_clash_core():
    """Download Clash core if not present"""
    if os.path.exists('./clash'):
        print("✅ Clash core found")
        return True
    
    urls = [
        "https://github.com/MetaCubeX/mihomo/releases/download/v1.18.0/mihomo-linux-amd64-v1.18.0.gz",
        "https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open('clash.gz', 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                with gzip.open('clash.gz', 'rb') as f_in:
                    with open('clash', 'wb') as f_out:
                        f_out.write(f_in.read())
                
                os.chmod('clash', 0o755)
                os.remove('clash.gz')
                print("✅ Clash core downloaded")
                return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    return False

def is_valid_server(server):
    """Check if server address is valid"""
    if not server:
        return False
    
    # Reject invalid patterns
    invalid_patterns = [
        r'^127\.',           # Localhost
        r'^0\.',              # Invalid
        r'^localhost',        # Localhost
        r'^192\.168\.',       # Private network
        r'^10\.',             # Private network  
        r'^172\.(1[6-9]|2[0-9]|3[01])\.',  # Private network
        r'^::1$',             # IPv6 localhost
        r'^fe80:',            # IPv6 link-local
        r'^fc00:',            # IPv6 private
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, server.lower()):
            return False
    
    # Check if it looks like a valid domain or IP
    if '.' not in server and ':' not in server:
        return False
    
    return True

def clean_control_characters(text):
    """Remove control characters that might break YAML parsing"""
    if not isinstance(text, str):
        return text
    # Remove non-printable characters except standard whitespace
    # This regex matches characters in the ranges [0-8], [11-12], [14-31]
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

def validate_node(node):
    """Validate and clean node configuration"""
    if not isinstance(node, dict):
        return None
    
    # Clean control characters from all string values in the node
    for key, value in node.items():
        if isinstance(value, str):
            node[key] = clean_control_characters(value)
    
    # Check required fields
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    server = node.get('server', '')
    
    # Validate server
    if not is_valid_server(server):
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
    node_type = node.get('type', '').lower()
    
    # Skip problematic types
    if node_type in ['vless', 'reality'] and ('reality-opts' in node or 'flow' in node):
        return None
    
    # Validate required fields by type
    if node_type == 'ss':
        if 'cipher' not in node or 'password' not in node:
            return None
    elif node_type == 'vmess':
        if 'uuid' not in node:
            return None
    elif node_type == 'trojan':
        if 'password' not in node:
            return None
    
    return node

def fetch_subscription_resilient(url):
    """Fetch with multiple fallback methods"""
    nodes = []
    raw_nodes = []
    
    # Method 1: Subconverter
    endpoints = [
        'https://sub.xeton.dev/sub',
        'https://api.dler.io/sub',
        'https://sub.id9.cc/sub'
    ]
    
    for endpoint in endpoints:
        try:
            params = {
                'target': 'clash',
                'url': url,
                'insert': 'false',
                'emoji': 'false',
                'list': 'true'
            }
            
            response = requests.get(endpoint, params=params, timeout=60)
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                if data and 'proxies' in data:
                    return data['proxies']
        except:
            continue
    
    # Method 2: Direct fetch
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=60)
        content = response.text
        
        # Try YAML
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
        
        # Try base64
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            data = yaml.safe_load(decoded)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
            
        # Try as URL list
        lines = content.strip().split('\n')
        for line in lines:
            if line.startswith(('vmess://', 'ss://', 'trojan://')):
                # Basic parsing (you can expand this)
                raw_nodes.append({'type': 'vmess', 'server': 'unknown', 'port': 443, 'name': 'parsed'})
        
    except Exception as e:
        pass
    
    # Validate each node
    for node in raw_nodes:
        if validate_node(node):
            nodes.append(node)

    return nodes

def fetch_all_subscriptions(urls):
    """Fetch all subscriptions with better error handling"""
    all_nodes = []
    
    print(f"\n📥 Fetching {len(urls)} subscriptions...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_subscription_resilient, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                nodes = future.result()
                if nodes:
                    all_nodes.extend(nodes)
                    print(f"\n✅ {url} : {len(nodes)} nodes")
                else:
                    print(f"\n⚠️ {url} : No nodes found")
            except Exception as e:
                print(f"\n   ❌ {url} : {e}")
    
    return all_nodes

def quick_tcp_test(node, timeout=1.5):
    """Quick TCP connectivity test"""
    server = node.get('server', '')
    port = node.get('port', 0)
    
    if not server or not port:
        return False
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Resolve and connect
        ip = socket.gethostbyname(server)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        return result == 0
    except:
        return False

def pre_filter_nodes(nodes, max_workers=50):
    """Pre-filter to find reachable nodes"""
    print(f"\n⚡ Pre-filtering {len(nodes)} valid nodes...")
    reachable = []
    unreachable = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(quick_tcp_test, node): node for node in nodes}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_node):
            completed += 1
            node = future_to_node[future]
            
            try:
                if future.result():
                    reachable.append(node)
                else:
                    unreachable += 1
            except:
                unreachable += 1
    
    print(f"   ✅ Found {len(reachable)} reachable, {unreachable} unreachable")
    return reachable

class ProxyTester:
    """Test proxies and detect real exit locations"""
    
    def __init__(self, clash_path='./clash'):
        self.clash_path = clash_path
        self.base_port = 9000
        
        # Get server's real IP first
        try:
            response = requests.get('http://ip-api.com/json', timeout=5)
            data = response.json()
            self.server_ip = data.get('query')
            self.server_country = data.get('countryCode')
            print(f"\n📍 Server location: {self.server_country} ({self.server_ip})")
        except:
            self.server_ip = None
            self.server_country = None
    
    def test_proxies(self, nodes, batch_size=50):
        """Test proxies in batches"""
        if not nodes:
            return []
        
        print(f"\n🔬 Testing {len(nodes)} proxies...")
        results = []
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(nodes) + batch_size - 1) // batch_size
            
            batch_results = self._test_batch(batch, self.base_port + batch_num)
            results.extend(batch_results)
        
        return results
    
    def _test_batch(self, nodes, port):
        """Test a batch of nodes"""
        results = []
        
        # Create Clash config
        config = {
            'mixed-port': port,
            'allow-lan': False,
            'mode': 'rule',
            'log-level': 'silent',
            'external-controller': f'127.0.0.1:{port+1000}',
            'proxies': nodes,
            'proxy-groups': [{
                'name': 'test',
                'type': 'select',
                'proxies': [n['name'] for n in nodes]
            }],
            'rules': ['MATCH,test']
        }
        
        config_file = f'test-{port}.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        process = None
        try:
            # Start Clash
            process = subprocess.Popen(
                [self.clash_path, '-f', config_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(2)
            
            # Test each node
            for node in nodes:
                result = self._test_single_proxy(node, port)
                
                # Store result
                node['test_result'] = result
                results.append(node)
                
        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except:
                    process.kill()
            
            try:
                os.remove(config_file)
            except:
                pass
        
        return results
    
    def _test_single_proxy(self, node, port):
        """Test single proxy and detect if it's really working"""
        result = {
            'alive': False,
            'is_proxy': False,  # Key field: is traffic going through proxy?
            'country': 'UN',
            'ip': None,
            'city': None
        }
        
        try:
            # Switch to this proxy
            controller = f"http://127.0.0.1:{port+1000}"
            requests.put(
                f"{controller}/proxies/test",
                json={'name': node['name']},
                timeout=1
            )
            
            # Test through proxy
            proxies = {
                'http': f'http://127.0.0.1:{port}',
                'https': f'http://127.0.0.1:{port}'
            }
            
            # Get exit location
            response = requests.get(
                'http://ip-api.com/json?fields=status,countryCode,country,city,query,isp',
                proxies=proxies,
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    exit_ip = data.get('query')
                    country = data.get('countryCode', 'UN')
                    
                    # CRITICAL CHECK: Is this actually going through proxy?
                    if exit_ip and exit_ip != self.server_ip:
                        # Traffic IS going through proxy!
                        result = {
                            'alive': True,
                            'is_proxy': True,
                            'country': country,
                            'ip': exit_ip,
                            'city': data.get('city'),
                            'isp': data.get('isp')
                        }
                    else:
                        # Traffic is going DIRECT (not through proxy)
                        result = {
                            'alive': True,
                            'is_proxy': False,
                            'country': self.server_country,
                            'ip': self.server_ip,
                            'city': 'DIRECT'
                        }
        
        except Exception as e:
            # Connection failed
            pass
        
        return result

def deduplicate_nodes(nodes):
    """Remove duplicate nodes"""
    seen = set()
    unique = []
    
    for node in nodes:
        if not isinstance(node, dict):
            continue
        
        key = f"{node.get('server')}:{node.get('port')}:{node.get('type')}"
        
        if key not in seen:
            seen.add(key)
            unique.append(node)
    
    return unique

def create_proxy_groups(all_names, sg_names):
    """Create proxy groups"""
    return [
        {
            'name': '🔥 ember',
            'type': 'select',
            'proxies': ['🌏 ⚡', '🇸🇬 ⚡']
        },
        {
            'name': '🌏 ⚡',
            'type': 'url-test',
            'proxies': all_names,
            'url': 'https://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'name': '🇸🇬 ⚡',
            'type': 'url-test',
            'proxies': sg_names if sg_names else ['DIRECT'],
            'url': 'https://www.gstatic.com/generate_204',
            'interval': 300
        }
    ]

def get_flag_emoji(code):
    """Get flag emoji for country code"""
    flags = {
        'SG': '🇸🇬', 'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'HK': '🇭🇰',
        'TW': '🇹🇼', 'CN': '🇨🇳', 'GB': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'NL': '🇳🇱', 'CA': '🇨🇦', 'AU': '🇦🇺', 'IN': '🇮🇳', 'TH': '🇹🇭',
        'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'VN': '🇻🇳', 'TR': '🇹🇷',
        'AE': '🇦🇪', 'RU': '🇷🇺', 'BR': '🇧🇷', 'AR': '🇦🇷', 'MX': '🇲🇽',
        'IT': '🇮🇹', 'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮',
        'DK': '🇩🇰', 'PL': '🇵🇱', 'UA': '🇺🇦', 'RO': '🇷🇴', 'CZ': '🇨🇿',
        'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'IE': '🇮🇪', 'NZ': '🇳🇿',
        'ZA': '🇿🇦', 'EG': '🇪🇬', 'IL': '🇮🇱', 'SA': '🇸🇦', 'CL': '🇨🇱',
        'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'EC': '🇪🇨', 'PT': '🇵🇹',
        'GR': '🇬🇷', 'HU': '🇭🇺', 'IS': '🇮🇸', 'LU': '🇱🇺', 'SK': '🇸🇰',
        'SI': '🇸🇮', 'BG': '🇧🇬', 'HR': '🇭🇷', 'RS': '🇷🇸', 'LT': '🇱🇹',
        'LV': '🇱🇻', 'EE': '🇪🇪', 'MD': '🇲🇩', 'AM': '🇦🇲', 'GE': '🇬🇪',
        'AZ': '🇦🇿', 'KZ': '🇰🇿', 'UZ': '🇺🇿', 'BD': '🇧🇩', 'LK': '🇱🇰',
        'MM': '🇲🇲', 'KH': '🇰🇭', 'LA': '🇱🇦', 'MO': '🇲🇴', 'PK': '🇵🇰',
        'CW': '🇨🇼', 'DO': '🇩🇴', 'PA': '🇵🇦', 'CR': '🇨🇷', 'UY': '🇺🇾',
        'IR': '🇮🇷', 'KE': '🇰🇪', 'NG': '🇳🇬', 'TN': '🇹🇳', 'LY': '🇱🇾'
    }
    return flags.get(code.upper(), '❓')

def generate_yaml(filename, proxies, update_time):
    """Helper to generate a Clash YAML file"""
    sg_node_names = [p['name'] for p in proxies if '🇸🇬' in p['name']]
    all_node_names = [p['name'] for p in proxies]
    
    output = {
        'proxies': proxies,
        'proxy-groups': create_proxy_groups(all_node_names, sg_node_names),
        'rules': ['GEOIP,PRIVATE,DIRECT', 'MATCH,🔥 ember']
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(proxies)}\n")
        f.write(f"# Singapore Nodes: {len(sg_node_names)}\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
        f.write("\ntun:\n  enable: true\n  stack: system\n  dns-hijack:\n  - any:53\n  auto-route: true\n  auto-detect-interface: true\n")

def main():
    start_time = time.time()
    if not download_clash_core(): return
    
    try:
        with open('sources.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except: return

    all_nodes = fetch_all_subscriptions(urls)
    if not all_nodes: return
    
    unique_nodes = deduplicate_nodes(all_nodes)
    reachable_nodes = pre_filter_nodes(unique_nodes)
    if not reachable_nodes: return
    
    tester = ProxyTester()
    tested_nodes = tester.test_proxies(reachable_nodes)
    
    real_proxies = [node for node in tested_nodes if node.get('test_result', {}).get('is_proxy')]
    if not real_proxies: return
    
    # Sort and Rename
    country_map = defaultdict(list)
    for node in real_proxies:
        country_map[node['test_result'].get('country', 'UN')].append(node)
    
    # Priority list for node sorting
    priority_countries = ['SG', 'US', 'JP', 'KR', 'HK', 'TW', 'VN']
    prioritized_list = []
    processed_countries = set()
    
    # Add prioritized countries in specific order
    for country_code in priority_countries:
        if country_code in country_map:
            flag = get_flag_emoji(country_code)
            for idx, node in enumerate(country_map[country_code], 1):
                node['name'] = f"{flag} {country_code}-{idx:03d}"
                node.pop('test_result', None)
                prioritized_list.append(node)
            processed_countries.add(country_code)
        
    # Add all remaining countries alphabetically
    for country in sorted(country_map.keys()):
        if country in processed_countries:
            continue
        flag = get_flag_emoji(country)
        for idx, node in enumerate(country_map[country], 1):
            node['name'] = f"{flag} {country}-{idx:03d}"
            node.pop('test_result', None)
            prioritized_list.append(node)

    # Time generation
    tz = pytz.timezone('Asia/Yangon')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S MMT')

    # 1. Full YAML
    generate_yaml('clash.yaml', prioritized_list, update_time)
    print(f"✅ Generated: clash.yaml ({len(prioritized_list)} nodes)")
    
    # 2. Lite YAML (Max 2000)
    lite_nodes = prioritized_list[:2000]
    generate_yaml('clash_lite.yaml', lite_nodes, update_time)
    print(f"✅ Generated: clash_lite.yaml ({len(lite_nodes)} nodes)")

    print(f"\n🚀 Done in {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    main()
    
