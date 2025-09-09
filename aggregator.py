#!/usr/bin/env python3
"""
Clash Aggregator with Fast Clash Core Testing
Optimized for speed while maintaining accuracy
"""

import yaml
import requests
import socket
import os
import subprocess
import json
import time
import concurrent.futures
from datetime import datetime
import pytz
from collections import defaultdict
from urllib.parse import quote
import base64
import threading

def download_clash_core():
    """Download Clash core if not present"""
    if os.path.exists('./clash'):
        print("✅ Clash core found")
        return True
    
    print("📥 Downloading Clash core...")
    
    urls = [
        "https://github.com/MetaCubeX/mihomo/releases/download/v1.18.0/mihomo-linux-amd64-v1.18.0.gz",
        "https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz"
    ]
    
    for url in urls:
        try:
            print(f"   Trying: {url.split('/')[4]}...")
            response = requests.get(url, stream=True, timeout=30)
            
            if response.status_code == 200:
                with open('clash.gz', 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                import gzip
                with gzip.open('clash.gz', 'rb') as f_in:
                    with open('clash', 'wb') as f_out:
                        f_out.write(f_in.read())
                
                os.chmod('clash', 0o755)
                os.remove('clash.gz')
                
                print("✅ Clash core downloaded")
                return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue
    
    return False

def quick_tcp_test(node, timeout=0.5):
    """Ultra-fast TCP connectivity test"""
    server = node.get('server', '')
    port = node.get('port', 0)
    
    if not server or not port:
        return False
    
    try:
        # Quick DNS resolution with cache
        ip = socket.gethostbyname(server)
        
        # Ultra-fast TCP test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        return result == 0
    except:
        return False

def batch_pre_filter(nodes, max_workers=100):
    """Fast parallel pre-filtering of dead nodes"""
    print(f"\n⚡ Pre-filtering {len(nodes)} nodes (removing dead ones)...")
    alive_nodes = []
    dead_count = 0
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_node = {executor.submit(quick_tcp_test, node): node for node in nodes}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_node):
            completed += 1
            node = future_to_node[future]
            
            if completed % 100 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                print(f"   Progress: {completed}/{len(nodes)} ({rate:.0f} nodes/sec)")
            
            try:
                if future.result():
                    alive_nodes.append(node)
                else:
                    dead_count += 1
            except:
                dead_count += 1
    
    elapsed = time.time() - start_time
    print(f"   ✅ Pre-filter done in {elapsed:.1f}s: {len(alive_nodes)} alive, {dead_count} dead")
    return alive_nodes

class FastClashTester:
    """Optimized Clash testing with connection pooling"""
    
    def __init__(self, clash_path='./clash'):
        self.clash_path = clash_path
        self.base_port = 9000
        self.stats = {
            'tested': 0,
            'alive': 0,
            'dead': 0,
            'sg_found': 0,
            'start_time': time.time()
        }
    
    def test_all_fast(self, nodes, batch_size=50):
        """Fast testing with single Clash instance"""
        if not nodes:
            return []
        
        print(f"\n🚀 Fast Clash testing {len(nodes)} pre-filtered nodes...")
        print(f"   Batch size: {batch_size}")
        
        results = []
        
        # Process in batches
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(nodes) + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} nodes)...")
            batch_results = self._test_batch_fast(batch, self.base_port + batch_num)
            results.extend(batch_results)
            
            # Show progress
            elapsed = time.time() - self.stats['start_time']
            rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
            eta = (len(nodes) - self.stats['tested']) / rate if rate > 0 else 0
            
            print(f"   Stats: {self.stats['alive']} alive, {self.stats['dead']} dead")
            print(f"   Speed: {rate:.1f} nodes/sec, ETA: {eta:.0f}s")
        
        return results
    
    def _test_batch_fast(self, nodes, port):
        """Test a batch with optimized Clash config"""
        results = []
        
        # Create optimized config
        config = {
            'mixed-port': port,
            'allow-lan': False,
            'mode': 'rule',  # Use rule mode for better performance
            'log-level': 'silent',  # Reduce logging overhead
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
            
            time.sleep(1.5)  # Reduced startup wait
            
            # Test nodes in parallel threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for node in nodes:
                    future = executor.submit(self._test_node_fast, node, port)
                    futures.append((future, node))
                
                for future, node in futures:
                    try:
                        result = future.result(timeout=3)
                        node['test_result'] = result
                        results.append(node)
                        
                        self.stats['tested'] += 1
                        if result['alive']:
                            self.stats['alive'] += 1
                            if result['country'] == 'SG':
                                self.stats['sg_found'] += 1
                        else:
                            self.stats['dead'] += 1
                    except:
                        node['test_result'] = {'alive': False, 'country': 'UN'}
                        results.append(node)
                        self.stats['dead'] += 1
                        self.stats['tested'] += 1
            
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
    
    def _test_node_fast(self, node, port):
        """Fast single node test"""
        result = {'alive': False, 'country': 'UN', 'latency': None}
        
        try:
            # Use controller to switch proxy
            controller = f"http://127.0.0.1:{port+1000}"
            
            # Switch to specific proxy
            requests.put(
                f"{controller}/proxies/test",
                json={'name': node['name']},
                timeout=1
            )
            
            # Quick test with short timeout
            proxies = {
                'http': f'http://127.0.0.1:{port}',
                'https': f'http://127.0.0.1:{port}'
            }
            
            start = time.time()
            
            # Use fastest API
            response = requests.get(
                'http://ip-api.com/json?fields=status,countryCode,query',
                proxies=proxies,
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    result = {
                        'alive': True,
                        'country': data.get('countryCode', 'UN'),
                        'ip': data.get('query'),
                        'latency': int((time.time() - start) * 1000)
                    }
        except:
            pass
        
        return result

def fetch_subscriptions_fast(urls):
    """Fast parallel fetching"""
    all_nodes = []
    
    def fetch_single(url):
        nodes = []
        try:
            # Try subconverter
            params = {
                'target': 'clash',
                'url': url,
                'insert': 'false',
                'emoji': 'false',
                'list': 'true'
            }
            
            response = requests.get(
                'https://sub.xeton.dev/sub',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                if data and 'proxies' in data:
                    nodes = data['proxies']
        except:
            # Try direct fetch as fallback
            try:
                response = requests.get(url, timeout=5)
                data = yaml.safe_load(response.text)
                if isinstance(data, dict) and 'proxies' in data:
                    nodes = data['proxies']
                elif isinstance(data, list):
                    nodes = data
            except:
                pass
        
        return nodes
    
    print(f"\n📥 Fetching {len(urls)} subscriptions in parallel...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_single, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                nodes = future.result()
                if nodes:
                    all_nodes.extend(nodes)
                    print(f"   ✅ {url[:40]}... : {len(nodes)} nodes")
                else:
                    print(f"   ❌ {url[:40]}... : Failed")
            except Exception as e:
                print(f"   ❌ {url[:40]}... : {e}")
    
    return all_nodes

def deduplicate_nodes(nodes):
    """Fast deduplication"""
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
            'proxies': ['🌏 ⚡', '🇸🇬 ⚡', '🌏 ⚖️', '🇸🇬 ⚖️']
        },
        {
            'name': '🌏 ⚡',
            'type': 'url-test',
            'proxies': all_names,
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300
        },
        {
            'name': '🇸🇬 ⚡',
            'type': 'url-test',
            'proxies': sg_names if sg_names else ['DIRECT'],
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300
        },
        {
            'name': '🌏 ⚖️',
            'type': 'load-balance',
            'proxies': all_names,
            'strategy': 'round-robin',
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300
        },
        {
            'name': '🇸🇬 ⚖️',
            'type': 'load-balance',
            'proxies': sg_names if sg_names else ['DIRECT'],
            'strategy': 'round-robin',
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300
        }
    ]

def get_flag_emoji(code):
    """Get flag emoji"""
    flags = {
        'SG': '🇸🇬', 'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'HK': '🇭🇰',
        'TW': '🇹🇼', 'CN': '🇨🇳', 'GB': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'NL': '🇳🇱', 'CA': '🇨🇦', 'AU': '🇦🇺', 'IN': '🇮🇳', 'TH': '🇹🇭',
        'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'VN': '🇻🇳', 'TR': '🇹🇷',
        'AE': '🇦🇪', 'RU': '🇷🇺', 'BR': '🇧🇷', 'AR': '🇦🇷', 'MX': '🇲🇽',
        'IT': '🇮🇹', 'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮'
    }
    return flags.get(code.upper(), '🌍')

def main():
    print("🚀 Fast Clash Aggregator with Optimized Testing")
    print("=" * 50)
    
    # Configuration
    MAX_TEST_NODES = 1000  # Reasonable limit for speed
    
    # Download Clash if needed
    if not download_clash_core():
        print("❌ Cannot proceed without Clash core")
        return
    
    # Read sources
    try:
        with open('sources.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Found {len(urls)} subscription URLs")
    except:
        print("❌ Failed to read sources.txt")
        return
    
    # Fast parallel fetch
    all_nodes = fetch_subscriptions_fast(urls)
    
    if not all_nodes:
        print("❌ No nodes fetched")
        return
    
    print(f"\n📊 Total fetched: {len(all_nodes)} nodes")
    
    # Deduplicate
    all_nodes = deduplicate_nodes(all_nodes)
    print(f"📊 After deduplication: {len(all_nodes)} unique nodes")
    
    # Limit for testing
    test_nodes = all_nodes[:MAX_TEST_NODES] if MAX_TEST_NODES else all_nodes
    if len(test_nodes) < len(all_nodes):
        print(f"⚠️ Testing limited to {MAX_TEST_NODES} nodes for speed")
    
    # FAST PRE-FILTER
    start_time = time.time()
    alive_nodes = batch_pre_filter(test_nodes)
    
    if not alive_nodes:
        print("❌ No alive nodes after pre-filter")
        return
    
    # FAST CLASH TEST (only alive nodes)
    tester = FastClashTester()
    tested_nodes = tester.test_all_fast(alive_nodes, batch_size=50)
    
    # Add untested nodes if any
    if MAX_TEST_NODES and len(all_nodes) > MAX_TEST_NODES:
        untested = all_nodes[MAX_TEST_NODES:]
        print(f"📝 Adding {len(untested)} untested nodes")
        tested_nodes.extend(untested)
    
    # Group by country
    country_nodes = defaultdict(list)
    
    for node in tested_nodes:
        if 'test_result' in node:
            country = node['test_result'].get('country', 'UN')
        else:
            country = 'UN'
        country_nodes[country].append(node)
    
    # Show results
    total_time = time.time() - start_time
    print(f"\n⏱️ Total testing time: {total_time:.1f} seconds")
    
    print(f"\n📊 Country Distribution:")
    for country, nodes in sorted(country_nodes.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        flag = get_flag_emoji(country)
        print(f"   {flag} {country}: {len(nodes)} nodes")
    
    # Process Singapore
    sg_nodes = country_nodes.get('SG', [])
    print(f"\n🇸🇬 Singapore Nodes: {len(sg_nodes)} (verified)")
    
    # Rename nodes
    renamed_nodes = []
    sg_node_names = []
    all_node_names = []
    
    # Singapore first
    for idx, node in enumerate(sg_nodes, 1):
        node_name = f"🇸🇬 SG-{idx:03d}"
        node['name'] = node_name
        node.pop('test_result', None)
        renamed_nodes.append(node)
        sg_node_names.append(node_name)
        all_node_names.append(node_name)
    
    # Others
    for country, nodes in country_nodes.items():
        if country == 'SG':
            continue
        
        flag = get_flag_emoji(country)
        for idx, node in enumerate(nodes, 1):
            node_name = f"{flag} {country}-{idx:03d}"
            node['name'] = node_name
            node.pop('test_result', None)
            renamed_nodes.append(node)
            all_node_names.append(node_name)
    
    # Create output
    output = {
        'proxies': renamed_nodes,
        'proxy-groups': create_proxy_groups(all_node_names, sg_node_names),
        'rules': [
            'GEOIP,PRIVATE,DIRECT',
            'MATCH,🔥 ember'
        ]
    }
    
    # Write output
    tz = pytz.timezone('Asia/Singapore')
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    with open('clash.yaml', 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(renamed_nodes)}\n")
        f.write(f"# Singapore Nodes: {len(sg_node_names)}\n")
        f.write(f"# Testing: Fast Clash Core (Real Exit)\n")
        f.write(f"# Test Time: {total_time:.1f}s\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
    
    print(f"\n✅ Successfully generated clash.yaml")
    print(f"📊 Total: {len(renamed_nodes)} proxies")
    print(f"🇸🇬 Singapore: {len(sg_node_names)} nodes")

if __name__ == "__main__":
    main()
