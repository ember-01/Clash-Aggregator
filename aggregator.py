#!/usr/bin/env python3
"""
Clash Aggregator with Clash Core for accurate testing
Gets real exit location + health check in one go
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
import tempfile
import signal
import base64

def download_clash_core():
    """Download Clash core if not present"""
    if os.path.exists('./clash'):
        print("✅ Clash core found")
        return True
    
    print("📥 Downloading Clash core...")
    
    # Detect architecture
    import platform
    machine = platform.machine().lower()
    
    if 'x86_64' in machine or 'amd64' in machine:
        arch = 'amd64'
    elif 'aarch64' in machine or 'arm64' in machine:
        arch = 'arm64'
    else:
        arch = 'amd64'  # Default
    
    # Download URL for Clash Premium (supports more features)
    url = f"https://github.com/Dreamacro/clash/releases/download/premium/clash-linux-{arch}-2023.08.17.gz"
    
    try:
        # Download
        response = requests.get(url, stream=True)
        with open('clash.gz', 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract
        import gzip
        with gzip.open('clash.gz', 'rb') as f_in:
            with open('clash', 'wb') as f_out:
                f_out.write(f_in.read())
        
        # Make executable
        os.chmod('clash', 0o755)
        os.remove('clash.gz')
        
        print("✅ Clash core downloaded")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download Clash core: {e}")
        return False

class ClashTester:
    """Test proxies using Clash core for real exit location"""
    
    def __init__(self, clash_path='./clash', base_port=9000):
        self.clash_path = clash_path
        self.base_port = base_port
        self.test_results = {}
        self.stats = {
            'tested': 0,
            'alive': 0,
            'dead': 0,
            'sg_found': 0
        }
    
    def test_batch(self, nodes, batch_size=10, max_workers=5):
        """Test nodes in parallel batches"""
        results = []
        total = len(nodes)
        
        print(f"\n🔬 Testing {total} proxies with Clash core...")
        print(f"   Batch size: {batch_size}, Workers: {max_workers}")
        
        # Process in batches
        for i in range(0, total, batch_size * max_workers):
            batch = nodes[i:i + batch_size * max_workers]
            batch_num = (i // (batch_size * max_workers)) + 1
            total_batches = (total + batch_size * max_workers - 1) // (batch_size * max_workers)
            
            print(f"\n📦 Testing batch {batch_num}/{total_batches}...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                
                for j in range(0, len(batch), batch_size):
                    sub_batch = batch[j:j + batch_size]
                    port = self.base_port + (j // batch_size)
                    future = executor.submit(self._test_sub_batch, sub_batch, port)
                    futures.append(future)
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    try:
                        batch_results = future.result()
                        results.extend(batch_results)
                    except Exception as e:
                        print(f"   ❌ Batch error: {e}")
        
        # Print statistics
        print(f"\n📊 Test Results:")
        print(f"   Total tested: {self.stats['tested']}")
        print(f"   Alive: {self.stats['alive']} ({self.stats['alive']*100//max(self.stats['tested'],1)}%)")
        print(f"   Dead: {self.stats['dead']}")
        print(f"   Singapore found: {self.stats['sg_found']}")
        
        return results
    
    def _test_sub_batch(self, nodes, port):
        """Test a sub-batch of nodes with one Clash instance"""
        results = []
        
        # Create test config with all nodes
        config = {
            'mixed-port': port,
            'allow-lan': False,
            'mode': 'global',
            'log-level': 'error',
            'external-controller': f'127.0.0.1:{port+1000}',
            'proxies': nodes,
            'proxy-groups': []
        }
        
        # Create proxy groups for each node
        for node in nodes:
            config['proxy-groups'].append({
                'name': f"test_{node['name']}",
                'type': 'select',
                'proxies': [node['name']]
            })
        
        # Write config
        config_file = f'test-config-{port}.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Start Clash
        process = None
        try:
            process = subprocess.Popen(
                [self.clash_path, '-f', config_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(2)  # Wait for Clash to start
            
            # Test each node
            for node in nodes:
                self.stats['tested'] += 1
                result = self._test_single_node(node, port)
                
                if result['alive']:
                    self.stats['alive'] += 1
                    if result['country'] == 'SG':
                        self.stats['sg_found'] += 1
                else:
                    self.stats['dead'] += 1
                
                # Update node with results
                node['test_result'] = result
                results.append(node)
                
                # Progress
                if self.stats['tested'] % 10 == 0:
                    print(f"   Progress: {self.stats['tested']} tested, {self.stats['alive']} alive")
            
        except Exception as e:
            print(f"   ❌ Error testing batch: {e}")
        finally:
            # Cleanup
            if process:
                process.terminate()
                time.sleep(0.5)
                try:
                    process.kill()
                except:
                    pass
            
            try:
                os.remove(config_file)
            except:
                pass
        
        return results
    
    def _test_single_node(self, node, port):
        """Test a single node through Clash"""
        result = {
            'alive': False,
            'country': 'UN',
            'ip': None,
            'latency': None
        }
        
        try:
            # Switch to this proxy via Clash API
            controller_url = f"http://127.0.0.1:{port+1000}/proxies/GLOBAL"
            requests.put(
                controller_url,
                json={'name': f"test_{node['name']}"},
                timeout=2
            )
            
            # Test connection and get exit IP
            proxies = {
                'http': f'http://127.0.0.1:{port}',
                'https': f'http://127.0.0.1:{port}'
            }
            
            start_time = time.time()
            
            # Try multiple endpoints for reliability
            test_urls = [
                'http://ip-api.com/json',
                'https://ipapi.co/json',
                'http://ip.sb/api/ip'
            ]
            
            for test_url in test_urls:
                try:
                    response = requests.get(
                        test_url,
                        proxies=proxies,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        latency = int((time.time() - start_time) * 1000)
                        
                        if 'ip-api.com' in test_url:
                            data = response.json()
                            result = {
                                'alive': True,
                                'country': data.get('countryCode', 'UN'),
                                'ip': data.get('query'),
                                'latency': latency,
                                'city': data.get('city'),
                                'isp': data.get('isp')
                            }
                        elif 'ipapi.co' in test_url:
                            data = response.json()
                            result = {
                                'alive': True,
                                'country': data.get('country_code', 'UN'),
                                'ip': data.get('ip'),
                                'latency': latency,
                                'city': data.get('city')
                            }
                        else:
                            # ip.sb returns plain IP
                            result = {
                                'alive': True,
                                'country': 'UN',  # Will need MaxMind for this
                                'ip': response.text.strip(),
                                'latency': latency
                            }
                        
                        break
                        
                except:
                    continue
            
        except:
            pass
        
        return result

def fetch_subscriptions_smart(urls):
    """Fetch subscriptions with multiple methods"""
    all_nodes = []
    
    for idx, url in enumerate(urls, 1):
        print(f"\n📥 Fetching {idx}/{len(urls)}: {url[:50]}...")
        nodes = []
        
        # Try subconverter first
        try:
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
                timeout=15
            )
            
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                if data and 'proxies' in data:
                    nodes = data['proxies']
                    print(f"   ✅ Got {len(nodes)} nodes via subconverter")
        except:
            pass
        
        # Fallback to direct fetch
        if not nodes:
            try:
                response = requests.get(url, timeout=10)
                content = response.text
                
                # Try parsing as YAML
                try:
                    data = yaml.safe_load(content)
                    if isinstance(data, dict) and 'proxies' in data:
                        nodes = data['proxies']
                        print(f"   ✅ Got {len(nodes)} nodes (direct)")
                    elif isinstance(data, list):
                        nodes = data
                        print(f"   ✅ Got {len(nodes)} nodes (direct)")
                except:
                    # Try base64 decode
                    try:
                        decoded = base64.b64decode(content).decode('utf-8')
                        data = yaml.safe_load(decoded)
                        if isinstance(data, dict) and 'proxies' in data:
                            nodes = data['proxies']
                            print(f"   ✅ Got {len(nodes)} nodes (base64)")
                    except:
                        pass
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        all_nodes.extend(nodes)
    
    return all_nodes

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
    """Get flag emoji for country code"""
    flags = {
        'SG': '🇸🇬', 'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'HK': '🇭🇰',
        'TW': '🇹🇼', 'CN': '🇨🇳', 'GB': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'NL': '🇳🇱', 'CA': '🇨🇦', 'AU': '🇦🇺', 'IN': '🇮🇳', 'TH': '🇹🇭',
        'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'VN': '🇻🇳', 'TR': '🇹🇷',
        'AE': '🇦🇪', 'RU': '🇷🇺', 'BR': '🇧🇷', 'AR': '🇦🇷', 'MX': '🇲🇽'
    }
    return flags.get(code.upper(), '🌍')

def main():
    print("🚀 Clash Aggregator with Clash Core Testing")
    print("=" * 50)
    
    # Configuration
    ENABLE_TESTING = True  # Set to False to skip testing
    MAX_TEST_NODES = 500   # Limit testing for speed (set to None for all)
    
    # Download Clash core if needed
    if ENABLE_TESTING and not download_clash_core():
        print("⚠️ Continuing without testing...")
        ENABLE_TESTING = False
    
    # Read subscriptions
    try:
        with open('sources.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Found {len(urls)} subscription URLs")
    except:
        print("❌ Failed to read sources.txt")
        return
    
    # Fetch all nodes
    all_nodes = fetch_subscriptions_smart(urls)
    print(f"\n📊 Total fetched: {len(all_nodes)} nodes")
    
    # Deduplicate
    all_nodes = deduplicate_nodes(all_nodes)
    print(f"📊 After deduplication: {len(all_nodes)} unique nodes")
    
    # Test with Clash core
    if ENABLE_TESTING and all_nodes:
        # Limit nodes for testing if configured
        test_nodes = all_nodes[:MAX_TEST_NODES] if MAX_TEST_NODES else all_nodes
        
        if len(test_nodes) < len(all_nodes):
            print(f"⚠️ Testing limited to first {MAX_TEST_NODES} nodes for speed")
        
        tester = ClashTester()
        tested_nodes = tester.test_batch(test_nodes, batch_size=10, max_workers=3)
        
        # Filter only alive nodes
        alive_nodes = [n for n in tested_nodes if n.get('test_result', {}).get('alive')]
        
        # Add untested nodes if we limited testing
        if MAX_TEST_NODES and len(all_nodes) > MAX_TEST_NODES:
            untested = all_nodes[MAX_TEST_NODES:]
            print(f"📝 Adding {len(untested)} untested nodes")
            alive_nodes.extend(untested)
    else:
        alive_nodes = all_nodes
    
    if not alive_nodes:
        print("❌ No alive nodes found")
        return
    
    # Group by country (using test results)
    country_nodes = defaultdict(list)
    
    for node in alive_nodes:
        if 'test_result' in node:
            country = node['test_result'].get('country', 'UN')
        else:
            country = 'UN'
        
        country_nodes[country].append(node)
    
    # Show distribution
    print(f"\n📊 Country Distribution (Real Exit Points):")
    for country, nodes in sorted(country_nodes.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        flag = get_flag_emoji(country)
        print(f"   {flag} {country}: {len(nodes)} nodes")
    
    # Process nodes
    sg_nodes = country_nodes.get('SG', [])
    print(f"\n🇸🇬 Singapore Nodes (Real): {len(sg_nodes)}")
    
    # Show sample SG nodes with details
    if sg_nodes and len(sg_nodes) <= 20:
        print("   Details:")
        for node in sg_nodes[:5]:
            result = node.get('test_result', {})
            print(f"   - {node.get('server')}: {result.get('city')} ({result.get('latency')}ms)")
    
    # Rename nodes
    renamed_nodes = []
    sg_node_names = []
    all_node_names = []
    
    # Singapore first
    for idx, node in enumerate(sg_nodes, 1):
        node_name = f"🇸🇬 SG-{idx:03d}"
        node['name'] = node_name
        node.pop('test_result', None)  # Remove test data
        renamed_nodes.append(node)
        sg_node_names.append(node_name)
        all_node_names.append(node_name)
    
    # Other countries
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
        f.write(f"# Singapore Nodes: {len(sg_node_names)} (Real Exit Points)\n")
        f.write("# Testing: Clash Core (Real Exit Location + Health)\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Summary:")
    print(f"   Total alive proxies: {len(renamed_nodes)}")
    print(f"   Singapore nodes: {len(sg_node_names)} (verified)")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
