#!/usr/bin/env python3
"""
Clash Aggregator using Subconverter + MaxMind GeoLite2
Process subscriptions in batches to avoid URL length limits
"""

import yaml
import requests
import socket
import os
import tarfile
import geoip2.database
import geoip2.errors
from datetime import datetime
import pytz
from collections import defaultdict
from urllib.parse import quote
import time
import base64

def download_maxmind_db():
    """Download and extract MaxMind GeoLite2 database"""
    license_key = os.environ.get('MAXMIND_LICENSE_KEY')
    if not license_key:
        print("❌ MAXMIND_LICENSE_KEY not found in environment variables")
        return False
    
    print("📥 Downloading MaxMind GeoLite2 database...")
    
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
                    print("✅ MaxMind database downloaded and extracted")
                    return True
        
        print("❌ Could not find .mmdb file in archive")
        return False
        
    except Exception as e:
        print(f"❌ Error downloading MaxMind database: {e}")
        return False

class GeoDetector:
    """Accurate geo-detection using MaxMind GeoLite2"""
    
    def __init__(self, db_path='GeoLite2-City.mmdb'):
        self.reader = geoip2.database.Reader(db_path)
        self.cache = {}
        self.stats = {
            'queries': 0,
            'cache_hits': 0,
            'sg_found': 0
        }
    
    def get_location(self, server):
        """Get country code for server/IP"""
        self.stats['queries'] += 1
        
        if server in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[server]
        
        try:
            if self._is_ip(server):
                ip = server
            else:
                ip = socket.gethostbyname(server)
        except:
            self.cache[server] = 'UN'
            return 'UN'
        
        try:
            response = self.reader.city(ip)
            country_code = response.country.iso_code or 'UN'
            self.cache[server] = country_code
            
            if country_code == 'SG':
                self.stats['sg_found'] += 1
            
            return country_code
            
        except geoip2.errors.AddressNotFoundError:
            self.cache[server] = 'UN'
            return 'UN'
        except Exception:
            self.cache[server] = 'UN'
            return 'UN'
    
    def _is_ip(self, string):
        """Check if string is an IP address"""
        try:
            socket.inet_aton(string)
            return True
        except:
            return False
    
    def print_stats(self):
        """Print statistics"""
        print(f"\n📊 GeoDetector Statistics:")
        print(f"   Total queries: {self.stats['queries']}")
        print(f"   Cache hits: {self.stats['cache_hits']}")
        print(f"   Singapore nodes found: {self.stats['sg_found']}")
    
    def close(self):
        """Close database reader"""
        self.reader.close()

def fetch_single_subscription(url, use_subconverter=True):
    """Fetch a single subscription with fallback"""
    nodes = []
    
    if use_subconverter:
        # Try subconverter first
        endpoints = [
            'https://sub.xeton.dev/sub',
            'https://api.dler.io/sub'
        ]
        
        for endpoint in endpoints:
            try:
                params = {
                    'target': 'clash',
                    'url': url,
                    'insert': 'false',
                    'emoji': 'false',
                    'list': 'true',
                    'udp': 'true'
                }
                
                response = requests.get(endpoint, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = yaml.safe_load(response.text)
                    if data and 'proxies' in data:
                        return data['proxies']
            except:
                continue
    
    # Fallback: Try direct parsing
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'clash-verge/1.0'})
        content = response.text.strip()
        
        # Try as YAML
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
        
        # Try base64 decode
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            data = yaml.safe_load(decoded)
            if isinstance(data, dict) and 'proxies' in data:
                return data['proxies']
            elif isinstance(data, list):
                return data
        except:
            pass
        
    except:
        pass
    
    return nodes

def fetch_subscriptions_batch(urls, batch_size=3):
    """Fetch subscriptions in batches"""
    all_nodes = []
    total_urls = len(urls)
    
    print(f"\n🔄 Processing {total_urls} subscriptions...")
    
    for i in range(0, total_urls, batch_size):
        batch = urls[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_urls + batch_size - 1) // batch_size
        
        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} URLs):")
        
        # Try batch processing with subconverter
        if len(batch) > 1:
            combined = '|'.join(batch)
            
            try:
                params = {
                    'target': 'clash',
                    'url': quote(combined),
                    'insert': 'false',
                    'emoji': 'false',
                    'list': 'true',
                    'udp': 'true'
                }
                
                response = requests.get(
                    'https://sub.xeton.dev/sub',
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = yaml.safe_load(response.text)
                    if data and 'proxies' in data:
                        nodes = data['proxies']
                        all_nodes.extend(nodes)
                        print(f"   ✅ Batch success: {len(nodes)} nodes")
                        continue
            except Exception as e:
                print(f"   ⚠️ Batch failed, trying individually...")
        
        # Process individually if batch fails
        for idx, url in enumerate(batch, 1):
            print(f"   Processing {idx}/{len(batch)}: {url[:50]}...")
            nodes = fetch_single_subscription(url)
            if nodes:
                all_nodes.extend(nodes)
                print(f"      Got {len(nodes)} nodes")
            else:
                print(f"      ❌ Failed")
            
            time.sleep(0.5)  # Small delay between requests
    
    return all_nodes

def deduplicate_nodes(nodes):
    """Remove duplicate nodes based on server:port:type"""
    seen = set()
    unique_nodes = []
    
    for node in nodes:
        if not isinstance(node, dict):
            continue
        
        server = node.get('server', '')
        port = node.get('port', '')
        node_type = node.get('type', '')
        
        key = f"{server}:{port}:{node_type}"
        
        if key not in seen:
            seen.add(key)
            unique_nodes.append(node)
    
    return unique_nodes

def create_proxy_groups(all_names, sg_names):
    """Create proxy group configuration"""
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
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '🇸🇬 ⚡',
            'type': 'url-test',
            'proxies': sg_names if sg_names else ['DIRECT'],
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'tolerance': 50
        },
        {
            'name': '🌏 ⚖️',
            'type': 'load-balance',
            'proxies': all_names,
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'strategy': 'round-robin'
        },
        {
            'name': '🇸🇬 ⚖️',
            'type': 'load-balance',
            'proxies': sg_names if sg_names else ['DIRECT'],
            'url': 'http://clients3.google.com/generate_204',
            'interval': 300,
            'strategy': 'round-robin'
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
    return flags.get(code.upper(), '🌍')

def main():
    print("🚀 Clash Aggregator with Subconverter + MaxMind")
    print("=" * 50)
    
    # Download MaxMind database if needed
    if not os.path.exists('GeoLite2-City.mmdb'):
        if not download_maxmind_db():
            print("❌ Failed to setup MaxMind database")
            return
    
    # Initialize GeoDetector
    try:
        geo = GeoDetector('GeoLite2-City.mmdb')
        print("✅ MaxMind GeoLite2 database loaded")
    except Exception as e:
        print(f"❌ Failed to load MaxMind database: {e}")
        return
    
    # Read subscription URLs
    try:
        with open('sources.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Found {len(urls)} subscription URLs")
    except Exception as e:
        print(f"❌ Failed to read sources.txt: {e}")
        return
    
    # Fetch all nodes in batches
    all_nodes = fetch_subscriptions_batch(urls, batch_size=3)
    
    if not all_nodes:
        print("❌ No nodes fetched from subscriptions")
        return
    
    print(f"\n📊 Total nodes fetched: {len(all_nodes)}")
    
    # Deduplicate
    all_nodes = deduplicate_nodes(all_nodes)
    print(f"📊 After deduplication: {len(all_nodes)} unique nodes")
    
    # Detect locations with MaxMind
    print(f"\n🌍 Detecting accurate locations with MaxMind...")
    country_nodes = defaultdict(list)
    
    for idx, node in enumerate(all_nodes, 1):
        if idx % 50 == 0:
            print(f"   Progress: {idx}/{len(all_nodes)}...")
        
        server = node.get('server', '')
        if not server:
            continue
        
        country = geo.get_location(server)
        country_nodes[country].append(node)
        
        if idx % 100 == 0:
            time.sleep(0.1)
    
    # Print statistics
    geo.print_stats()
    
    # Show country distribution
    print(f"\n📊 Country Distribution:")
    sorted_countries = sorted(country_nodes.items(), key=lambda x: len(x[1]), reverse=True)
    for country, nodes in sorted_countries[:15]:
        flag = get_flag_emoji(country)
        count = len(nodes)
        print(f"   {flag} {country}: {count} nodes")
    
    # Process Singapore nodes
    sg_nodes = country_nodes.get('SG', [])
    print(f"\n🇸🇬 Singapore Nodes: {len(sg_nodes)}")
    
    # Rename nodes
    renamed_nodes = []
    sg_node_names = []
    all_node_names = []
    
    # Singapore first
    if sg_nodes:
        for idx, node in enumerate(sg_nodes, 1):
            node_name = f"🇸🇬 SG-{idx:03d}"
            node['name'] = node_name
            renamed_nodes.append(node)
            sg_node_names.append(node_name)
            all_node_names.append(node_name)
        del country_nodes['SG']
    
    # Other countries
    for country_code in sorted(country_nodes.keys()):
        nodes = country_nodes[country_code]
        flag = get_flag_emoji(country_code)
        
        for idx, node in enumerate(nodes, 1):
            node_name = f"{flag} {country_code}-{idx:03d}"
            node['name'] = node_name
            renamed_nodes.append(node)
            all_node_names.append(node_name)
    
    if not all_node_names:
        print("❌ No valid nodes after processing")
        return
    
    # Create configuration
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
        f.write("# Parsing: Subconverter (batch) | Geo: MaxMind GeoLite2\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    geo.close()
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Summary:")
    print(f"   Total proxies: {len(renamed_nodes)}")
    print(f"   Singapore nodes: {len(sg_node_names)}")
    print(f"🕐 Updated at {update_time}")

if __name__ == "__main__":
    main()
