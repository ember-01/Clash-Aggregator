#!/usr/bin/env python3
"""
Clash Aggregator with Clash + MaxMind
Pre-filters all nodes, tests all alive ones
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
from urllib.parse import quote, unquote
import base64
import gzip
import tarfile
import geoip2.database
import geoip2.errors

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

def download_maxmind_db():
    """Download MaxMind GeoLite2 database"""
    if os.path.exists('GeoLite2-City.mmdb'):
        print("✅ MaxMind database found")
        return True
    
    print("📥 Downloading MaxMind GeoLite2 database...")
    
    license_key = os.environ.get('MAXMIND_LICENSE_KEY', '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')
    
    try:
        url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to download: HTTP {response.status_code}")
            return False
        
        with open("GeoLite2-City.tar.gz", "wb") as f:
            f.write(response.content)
        
        with tarfile.open("GeoLite2-City.tar.gz", "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("GeoLite2-City.mmdb"):
                    member.name = "GeoLite2-City.mmdb"
                    tar.extract(member)
                    print("✅ MaxMind database downloaded")
                    os.remove("GeoLite2-City.tar.gz")
                    return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error downloading MaxMind: {e}")
        return False

class GeoDetector:
    """MaxMind geo-detection"""
    
    def __init__(self, db_path='GeoLite2-City.mmdb'):
        self.reader = geoip2.database.Reader(db_path)
        self.cache = {}
    
    def get_location(self, ip):
        """Get country code for IP"""
        if ip in self.cache:
            return self.cache[ip]
        
        try:
            response = self.reader.city(ip)
            country = response.country.iso_code or 'UN'
            self.cache[ip] = country
            return country
        except:
            self.cache[ip] = 'UN'
            return 'UN'
    
    def close(self):
        self.reader.close()

def quick_tcp_test(node, timeout=1.0):
    """Fast TCP connectivity test"""
    server = node.get('server', '')
    port = node.get('port', 0)
    
    if not server or not port:
        return False
    
    try:
        # DNS resolution
        ip = socket.gethostbyname(server)
        
        # TCP test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        
        return result == 0
    except:
        return False

def pre_filter_all_nodes(nodes, max_workers=100):
    """Pre-filter ALL nodes to find alive ones"""
    print(f"\n⚡ Pre-filtering ALL {len(nodes)} nodes...")
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
                eta = (len(nodes) - completed) / rate if rate > 0 else 0
                print(f"   Progress: {completed}/{len(nodes)} ({len(alive_nodes)} alive, {rate:.0f} nodes/sec, ETA: {eta:.0f}s)")
            
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

class ClashMaxMindTester:
    """Test with Clash + MaxMind for geo"""
    
    def __init__(self, clash_path='./clash', geo_detector=None):
        self.clash_path = clash_path
        self.geo = geo_detector
        self.base_port = 9000
        self.stats = {
            'tested': 0,
            'alive': 0,
            'dead': 0,
            'sg_found': 0
        }
    
    def test_all_nodes(self, nodes, batch_size=50):
        """Test ALL alive nodes"""
        if not nodes:
            return []
        
        print(f"\n🔬 Testing ALL {len(nodes)} alive nodes with Clash + MaxMind...")
        print(f"   Batch size: {batch_size}")
        
        results = []
        start_time = time.time()
        
        # Process ALL nodes in batches
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(nodes) + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} nodes)...")
            batch_results = self._test_batch(batch, self.base_port + batch_num)
            results.extend(batch_results)
            
            # Progress
            elapsed = time.time() - start_time
            rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
            eta = (len(nodes) - self.stats['tested']) / rate if rate > 0 else 0
            
            print(f"   Tested: {self.stats['tested']}/{len(nodes)}")
            print(f"   Alive: {self.stats['alive']}, Dead: {self.stats['dead']}, SG: {self.stats['sg_found']}")
            print(f"   Speed: {rate:.1f} nodes/sec, ETA: {eta:.0f}s")
        
        return results
    
    def _test_batch(self, nodes, port):
        """Test a batch with Clash"""
        results = []
        
        # Create config
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
            
            time.sleep(1.5)
            
            # Test nodes in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for node in nodes:
                    future = executor.submit(self._test_single, node, port)
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
    
    def _test_single(self, node, port):
        """Test single node and get exit IP"""
        result = {'alive': False, 'country': 'UN', 'ip': None}
        
        try:
            # Switch proxy
            controller = f"http://127.0.0.1:{port+1000}"
            requests.put(
                f"{controller}/proxies/test",
                json={'name': node['name']},
                timeout=1
            )
            
            # Get exit IP through proxy
            proxies = {
                'http': f'http://127.0.0.1:{port}',
                'https': f'http://127.0.0.1:{port}'
            }
            
            # Just get IP (faster than geo API)
            response = requests.get(
                'http://ip.sb',  # Returns plain IP
                proxies=proxies,
                timeout=2
            )
            
            if response.status_code == 200:
                exit_ip = response.text.strip()
                
                # Use MaxMind for geo (offline, fast)
                country = self.geo.get_location(exit_ip) if self.geo else 'UN'
                
                result = {
                    'alive': True,
                    'country': country,
                    'ip': exit_ip
                }
        except:
            pass
        
        return result

def fetch_subscription_resilient(url):
    """Fetch with multiple fallback methods"""
    nodes = []
    
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
            
            response = requests.get(endpoint, params=params, timeout=10)
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
        response = requests.get(url, headers=headers, timeout=10)
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
                nodes.append({'type': 'vmess', 'server': 'unknown', 'port': 443, 'name': 'parsed'})
        
    except Exception as e:
        pass
    
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
                    print(f"   ✅ {url[:50]}... : {len(nodes)} nodes")
                else:
                    print(f"   ⚠️ {url[:50]}... : No nodes found")
            except Exception as e:
                print(f"   ❌ {url[:50]}... : {e}")
    
    return all_nodes

def deduplicate_nodes(nodes):
    """Remove duplicates"""
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
        'IT': '🇮🇹', 'ES': '🇪🇸', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮',
        'DK': '🇩🇰', 'PL': '🇵🇱', 'UA': '🇺🇦', 'RO': '🇷🇴', 'CZ': '🇨🇿',
        'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'IE': '🇮🇪', 'NZ': '🇳🇿',
        'ZA': '🇿🇦', 'EG': '🇪🇬', 'IL': '🇮🇱', 'SA': '🇸🇦', 'IR': '🇮🇷'
    }
    return flags.get(code.upper(), '🌍')

def main():
    print("🚀 Clash Aggregator with Clash + MaxMind")
    print("=" * 50)
    
    total_start = time.time()
    
    # Download requirements
    if not download_clash_core():
        print("❌ Cannot proceed without Clash core")
        return
    
    if not download_maxmind_db():
        print("❌ Cannot proceed without MaxMind database")
        return
    
    # Initialize MaxMind
    try:
        geo = GeoDetector('GeoLite2-City.mmdb')
        print("✅ MaxMind GeoLite2 loaded")
    except Exception as e:
        print(f"❌ Failed to load MaxMind: {e}")
        return
    
    # Read sources
    try:
        with open('sources.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Found {len(urls)} subscription URLs")
    except:
        print("❌ Failed to read sources.txt")
        return
    
    # Fetch all subscriptions
    all_nodes = fetch_all_subscriptions(urls)
    
    if not all_nodes:
        print("❌ No nodes fetched")
        return
    
    print(f"\n📊 Total fetched: {len(all_nodes)} nodes")
    
    # Deduplicate
    all_nodes = deduplicate_nodes(all_nodes)
    print(f"📊 After deduplication: {len(all_nodes)} unique nodes")
    
    # Pre-filter ALL nodes
    alive_nodes = pre_filter_all_nodes(all_nodes)
    
    if not alive_nodes:
        print("❌ No alive nodes found")
        return
    
    print(f"\n✅ Will test ALL {len(alive_nodes)} alive nodes")
    
    # Test ALL alive nodes with Clash + MaxMind
    tester = ClashMaxMindTester(geo_detector=geo)
    tested_nodes = tester.test_all_nodes(alive_nodes, batch_size=50)
    
    # Group by country
    country_nodes = defaultdict(list)
    
    for node in tested_nodes:
        result = node.get('test_result', {})
        if result.get('alive'):
            country = result.get('country', 'UN')
            country_nodes[country].append(node)
    
    # Show distribution
    print(f"\n📊 Country Distribution (Real Exit Points):")
    for country, nodes in sorted(country_nodes.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        flag = get_flag_emoji(country)
        print(f"   {flag} {country}: {len(nodes)} nodes")
    
    # Process Singapore
    sg_nodes = country_nodes.get('SG', [])
    print(f"\n🇸🇬 Singapore Nodes: {len(sg_nodes)} (verified exit points)")
    
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
    
    if not all_node_names:
        print("❌ No valid nodes for output")
        return
    
    # Create output
    output = {
        'proxies': renamed_nodes,
        'proxy-groups': create_proxy_groups(all_node_names, sg_node_names),
        'rules': [
            'GEOIP,PRIVATE,DIRECT',
            'MATCH,🔥 ember'
        ]
    }
    
    # Write output with Myanmar timezone
    tz = pytz.timezone('Asia/Yangon')  # Myanmar timezone
    update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S MMT')
    
    total_time = time.time() - total_start
    
    with open('clash.yaml', 'w', encoding='utf-8') as f:
        f.write(f"# Last Update: {update_time}\n")
        f.write(f"# Total Proxies: {len(renamed_nodes)}\n")
        f.write(f"# Singapore Nodes: {len(sg_node_names)}\n")
        f.write(f"# Testing: Clash Core + MaxMind GeoLite2\n")
        f.write(f"# Process Time: {total_time:.1f}s\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
    
    # Cleanup
    geo.close()
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Summary:")
    print(f"   Total alive proxies: {len(renamed_nodes)}")
    print(f"   Singapore nodes: {len(sg_node_names)}")
    print(f"   Total time: {total_time:.1f} seconds")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
