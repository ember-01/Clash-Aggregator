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
import urllib.parse
import json

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
    
    invalid_patterns = [
        r'^127\.', r'^0\.', r'^localhost', r'^192\.168\.', 
        r'^10\.', r'^172\.(1[6-9]|2[0-9]|3[01])\.', r'^::1$', 
        r'^fe80:', r'^fc00:',
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, server.lower()):
            return False
    
    if '.' not in server and ':' not in server:
        return False
    
    return True

def clean_control_characters(text):
    """Remove control characters that break YAML parsing"""
    if not isinstance(text, str):
        return text
    # Keep only printable characters and standard whitespace
    return "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

def parse_proxy_uri(uri):
    """Basic parser for vmess, ss, and trojan URIs"""
    try:
        uri = uri.strip()
        if not uri: return None
        
        if uri.startswith('ss://'):
            # ss://method:password@server:port#name
            # or ss://base64(method:password)@server:port#name
            part = uri[5:]
            name = ""
            if '#' in part:
                part, name = part.split('#', 1)
                name = urllib.parse.unquote(name)
            
            if '@' in part:
                auth_part, server_part = part.split('@', 1)
                if ':' not in auth_part: # Base64 encoded auth
                    auth_part = base64.b64decode(auth_part + '==').decode('utf-8')
                method, password = auth_part.split(':', 1)
                server, port = server_part.split(':', 1)
                return {'type': 'ss', 'name': name or server, 'server': server, 'port': int(port), 'cipher': method, 'password': password}

        elif uri.startswith('trojan://'):
            # trojan://password@server:port#name
            part = uri[9:]
            name = ""
            if '#' in part:
                part, name = part.split('#', 1)
                name = urllib.parse.unquote(name)
            auth_part, server_part = part.split('@', 1)
            password = auth_part
            server, port = server_part.split(':', 1)
            if '?' in port: port = port.split('?')[0]
            return {'type': 'trojan', 'name': name or server, 'server': server, 'port': int(port), 'password': password, 'sni': server}

        elif uri.startswith('vmess://'):
            # vmess://base64(json)
            part = uri[8:]
            config = json.loads(base64.b64decode(part + '==').decode('utf-8'))
            return {
                'type': 'vmess', 'name': config.get('ps', 'vmess'), 'server': config.get('add'), 
                'port': int(config.get('port', 443)), 'uuid': config.get('id'), 'alterId': int(config.get('aid', 0)),
                'cipher': 'auto', 'tls': config.get('tls') == 'tls', 'network': config.get('net', 'tcp')
            }
    except:
        pass
    return None

def validate_node(node):
    """Validate and clean node configuration"""
    if not isinstance(node, dict):
        return None
    
    # Clean string fields
    for key in node:
        if isinstance(node[key], str):
            node[key] = clean_control_characters(node[key])
    
    if 'type' not in node or 'server' not in node or 'port' not in node:
        return None
    
    if not is_valid_server(node.get('server')):
        return None
    
    try:
        node['port'] = int(node['port'])
    except:
        return None
    
    return node

def fetch_subscription_resilient(url):
    """Fetch with subconverters and direct parsing fallbacks"""
    nodes = []
    
    # Method 1: Subconverters (Highly reliable for mixed formats)
    endpoints = [
        'https://sub.xeton.dev/sub', 'https://api.dler.io/sub', 
        'https://sub.id9.cc/sub', 'https://url.v1.mk/sub'
    ]
    
    for endpoint in endpoints:
        try:
            params = {'target': 'clash', 'url': url, 'insert': 'false', 'emoji': 'false', 'list': 'true'}
            response = requests.get(endpoint, params=params, timeout=45)
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                if data and 'proxies' in data:
                    return data['proxies']
        except:
            continue
    
    # Method 2: Direct fetch and local parsing (Fallback)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        content = response.text.strip()
        
        # Try as YAML first
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data: return data['proxies']
            if isinstance(data, list) and len(data) > 0 and 'server' in data[0]: return data
        except: pass

        # Try as Base64 encoded list (common for V2Ray/SS)
        try:
            decoded = base64.b64decode(content + '==').decode('utf-8')
            content = decoded
        except: pass
        
        # Parse line by line for URIs
        for line in content.splitlines():
            node = parse_proxy_uri(line)
            if node: nodes.append(node)
            
    except Exception as e:
        print(f"   ⚠️ Direct fetch error for {url}: {e}")
    
    return nodes

def fetch_all_subscriptions(urls):
    all_nodes = []
    print(f"\n📥 Fetching {len(urls)} subscriptions...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_subscription_resilient, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                nodes = future.result()
                if nodes:
                    valid_nodes = [n for n in [validate_node(x) for x in nodes] if n]
                    all_nodes.extend(valid_nodes)
                    print(f"   ✅ {url} : {len(valid_nodes)} nodes")
                else:
                    print(f"   ⚠️ {url} : No nodes found")
            except Exception as e:
                print(f"   ❌ {url} : Error")
    return all_nodes

def quick_tcp_test(node, timeout=1.5):
    server = node.get('server', '')
    port = node.get('port', 0)
    if not server or not port: return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        ip = socket.gethostbyname(server)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        return result == 0
    except: return False

def pre_filter_nodes(nodes, max_workers=50):
    print(f"\n⚡ Pre-filtering {len(nodes)} valid nodes...")
    reachable = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(quick_tcp_test, node): node for node in nodes}
        for future in concurrent.futures.as_completed(future_to_node):
            if future.result(): reachable.append(future_to_node[future])
    print(f"   ✅ Found {len(reachable)} reachable nodes")
    return reachable

class ProxyTester:
    def __init__(self, clash_path='./clash'):
        self.clash_path = clash_path
        self.base_port = 9000
        try:
            response = requests.get('http://ip-api.com/json', timeout=5)
            data = response.json()
            self.server_ip = data.get('query')
            self.server_country = data.get('countryCode')
            print(f"\n📍 Server location: {self.server_country} ({self.server_ip})")
        except:
            self.server_ip = None
    
    def test_proxies(self, nodes, batch_size=50):
        if not nodes: return []
        print(f"\n🔬 Testing {len(nodes)} proxies...")
        results = []
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            results.extend(self._test_batch(batch, self.base_port + batch_num))
        return results
    
    def _test_batch(self, nodes, port):
        results = []
        config = {
            'mixed-port': port, 'allow-lan': False, 'mode': 'rule', 'log-level': 'silent',
            'external-controller': f'127.0.0.1:{port+1000}', 'proxies': nodes,
            'proxy-groups': [{'name': 'test', 'type': 'select', 'proxies': [n['name'] for n in nodes]}],
            'rules': ['MATCH,test']
        }
        config_file = f'test-{port}.yaml'
        with open(config_file, 'w') as f: yaml.dump(config, f)
        
        process = None
        try:
            process = subprocess.Popen([self.clash_path, '-f', config_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            for node in nodes:
                node['test_result'] = self._test_single_proxy(node, port)
                results.append(node)
        finally:
            if process:
                process.terminate()
                process.wait()
            if os.path.exists(config_file): os.remove(config_file)
        return results
    
    def _test_single_proxy(self, node, port):
        result = {'alive': False, 'is_proxy': False, 'country': 'UN', 'ip': None}
        try:
            requests.put(f"http://127.0.0.1:{port+1000}/proxies/test", json={'name': node['name']}, timeout=1)
            proxies = {'http': f'http://127.0.0.1:{port}', 'https': f'http://127.0.0.1:{port}'}
            response = requests.get('http://ip-api.com/json', proxies=proxies, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('query') != self.server_ip:
                    result = {'alive': True, 'is_proxy': True, 'country': data.get('countryCode', 'UN'), 'ip': data.get('query')}
        except: pass
        return result

def deduplicate_nodes(nodes):
    seen = set()
    unique = []
    for node in nodes:
        key = f"{node.get('server')}:{node.get('port')}:{node.get('type')}"
        if key not in seen:
            seen.add(key)
            unique.append(node)
    return unique

def create_proxy_groups(all_names, sg_names):
    return [
        {'name': '🔥 ember', 'type': 'select', 'proxies': ['🌏 ⚡', '🇸🇬 ⚡']},
        {'name': '🌏 ⚡', 'type': 'url-test', 'proxies': all_names, 'url': 'https://www.gstatic.com/generate_204', 'interval': 300},
        {'name': '🇸🇬 ⚡', 'type': 'url-test', 'proxies': sg_names if sg_names else ['DIRECT'], 'url': 'https://www.gstatic.com/generate_204', 'interval': 300}
    ]

def get_flag_emoji(code):
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
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
        f.write("\ntun:\n  enable: true\n  stack: system\n  dns-hijack:\n  - any:53\n  auto-route: true\n  auto-detect-interface: true\n")

import sys

def main():
    # Configuration - allows overriding via command line
    # Usage: python3 aggregator.py [sources_file] [output_name]
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'sources.txt'
    output_base = sys.argv[2] if len(sys.argv) > 2 else 'clash'
    
    print(f"🚀 Running Aggregator: {input_file} -> {output_base}.yaml")
    
    start_time = time.time()
    if not download_clash_core(): return
    
    try:
        with open(input_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print(f"❌ Error reading {input_file}: {e}")
        return

    all_nodes = fetch_all_subscriptions(urls)
    if not all_nodes:
        print("❌ No nodes found in any subscription")
        return
    
    unique_nodes = deduplicate_nodes(all_nodes)
    reachable_nodes = pre_filter_nodes(unique_nodes)
    if not reachable_nodes:
        print("❌ No reachable nodes found")
        return
    
    tester = ProxyTester()
    tested_nodes = tester.test_proxies(reachable_nodes)
    
    real_proxies = [node for node in tested_nodes if node.get('test_result', {}).get('is_proxy')]
    if not real_proxies:
        print("❌ No real working proxies found (all tests failed or went direct)")
        return
    
    country_map = defaultdict(list)
    for node in real_proxies:
        country_map[node['test_result'].get('country', 'UN')].append(node)
    
    priority_countries = ['SG', 'US', 'JP', 'KR', 'HK', 'TW', 'VN']
    prioritized_list = []
    processed_countries = set()
    
    for country_code in priority_countries:
        if country_code in country_map:
            flag = get_flag_emoji(country_code)
            for idx, node in enumerate(country_map[country_code], 1):
                node['name'] = f"{flag} {country_code}-{idx:03d}"
                node.pop('test_result', None)
                prioritized_list.append(node)
            processed_countries.add(country_code)
        
    for country in sorted(country_map.keys()):
        if country in processed_countries: continue
        flag = get_flag_emoji(country)
        for idx, node in enumerate(country_map[country], 1):
            node['name'] = f"{flag} {country}-{idx:03d}"
            node.pop('test_result', None)
            prioritized_list.append(node)

    tz = pytz.timezone('Asia/Yangon')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S MMT')

    # Generate files based on output_base
    generate_yaml(f'{output_base}.yaml', prioritized_list, update_time)
    generate_yaml(f'{output_base}_lite.yaml', prioritized_list[:2000], update_time)
    
    print(f"\n✅ Completed: {len(prioritized_list)} nodes.")
    print(f"🕐 Time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    main()
    
