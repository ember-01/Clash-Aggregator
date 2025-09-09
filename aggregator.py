#!/usr/bin/env python3
"""
Debug version to diagnose geo-detection issues
"""

import yaml
import requests
import socket
import os
import subprocess
import time
import json
from datetime import datetime
import pytz

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
    
    return False

def fetch_test_nodes():
    """Fetch a small set of nodes for testing"""
    print("\n📥 Fetching test nodes...")
    
    test_urls = [
        'https://raw.githubusercontent.com/peasoft/NoMoreWalls/refs/heads/master/snippets/nodes.meta.yml',
        'https://raw.githubusercontent.com/mahdibland/V2RayAggregator/refs/heads/master/Eternity.yml'
    ]
    
    all_nodes = []
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            data = yaml.safe_load(response.text)
            
            if isinstance(data, dict) and 'proxies' in data:
                nodes = data['proxies'][:10]  # Take first 10 from each
                all_nodes.extend(nodes)
                print(f"   ✅ Got {len(nodes)} nodes from {url.split('/')[4]}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    return all_nodes

def debug_test_with_clash(nodes):
    """Detailed debug testing with Clash"""
    print("\n" + "="*60)
    print("🔍 DEBUG MODE - Testing with detailed output")
    print("="*60)
    
    if not nodes:
        print("❌ No nodes to test")
        return
    
    # Test only first 5 nodes for debugging
    test_nodes = nodes[:5]
    
    # Create Clash config
    config = {
        'port': 7890,
        'socks-port': 7891,
        'mixed-port': 7892,
        'allow-lan': False,
        'mode': 'global',
        'log-level': 'info',
        'external-controller': '127.0.0.1:9090',
        'proxies': test_nodes,
        'proxy-groups': [{
            'name': 'GLOBAL',
            'type': 'select',
            'proxies': [node['name'] for node in test_nodes]
        }],
        'rules': [
            'MATCH,GLOBAL'
        ]
    }
    
    # Write config
    with open('debug-config.yaml', 'w') as f:
        yaml.dump(config, f)
    
    print("\n📝 Clash config created with ports:")
    print("   HTTP: 7890")
    print("   SOCKS: 7891")
    print("   Mixed: 7892")
    print("   Controller: 9090")
    
    # Start Clash
    print("\n🚀 Starting Clash...")
    process = subprocess.Popen(
        ['./clash', '-f', 'debug-config.yaml'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(3)  # Wait for Clash to start
    
    # Check if Clash is running
    try:
        controller_response = requests.get('http://127.0.0.1:9090/version', timeout=2)
        print(f"✅ Clash is running: {controller_response.json()}")
    except Exception as e:
        print(f"❌ Clash controller not responding: {e}")
        print("\nClash stderr output:")
        stderr = process.stderr.read() if process.stderr else "No stderr"
        print(stderr[:500])
        process.terminate()
        return
    
    # Test each node
    for idx, node in enumerate(test_nodes, 1):
        print(f"\n" + "="*60)
        print(f"📍 Testing Node {idx}/{len(test_nodes)}: {node['name']}")
        print(f"   Type: {node.get('type')}")
        print(f"   Server: {node.get('server')}")
        print(f"   Port: {node.get('port')}")
        print("="*60)
        
        # Switch to this proxy
        try:
            switch_response = requests.put(
                'http://127.0.0.1:9090/proxies/GLOBAL',
                json={'name': node['name']},
                timeout=2
            )
            print(f"✅ Switched to proxy: {node['name']}")
        except Exception as e:
            print(f"❌ Failed to switch proxy: {e}")
            continue
        
        # Define proxy settings
        proxies = {
            'http': 'http://127.0.0.1:7892',
            'https': 'http://127.0.0.1:7892'
        }
        
        # Test 1: Basic connectivity
        print("\n🔹 Test 1: Basic Connectivity")
        try:
            response = requests.get(
                'http://www.google.com/generate_204',
                proxies=proxies,
                timeout=5
            )
            print(f"   ✅ Google 204: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue
        
        # Test 2: Get plain IP
        print("\n🔹 Test 2: Get Exit IP")
        exit_ip = None
        
        # Try multiple IP services
        ip_services = [
            'http://ip.sb',
            'http://icanhazip.com',
            'http://ifconfig.me/ip',
            'http://api.ipify.org'
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, proxies=proxies, timeout=3)
                exit_ip = response.text.strip()
                print(f"   ✅ {service}: {exit_ip}")
                break
            except Exception as e:
                print(f"   ❌ {service}: {e}")
        
        if not exit_ip:
            print("   ⚠️ Could not get exit IP")
            continue
        
        # Test 3: Get geo location from multiple sources
        print("\n🔹 Test 3: Geo-Location Detection")
        
        # Method A: ip-api.com
        print("   📍 Using ip-api.com:")
        try:
            response = requests.get(
                'http://ip-api.com/json',
                proxies=proxies,
                timeout=5
            )
            
            print(f"      Status Code: {response.status_code}")
            print(f"      Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Raw Response: {json.dumps(data, indent=2)}")
                
                country = data.get('countryCode', 'UN')
                city = data.get('city', 'Unknown')
                
                print(f"      📍 Country: {country}")
                print(f"      📍 City: {city}")
                
                # Check for Singapore
                if country == 'SG' or 'singapore' in city.lower():
                    print("      🇸🇬 *** SINGAPORE DETECTED! ***")
            else:
                print(f"      ❌ Bad status: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Method B: ipinfo.io
        print("\n   📍 Using ipinfo.io:")
        try:
            response = requests.get(
                'https://ipinfo.io/json',
                proxies=proxies,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Raw Response: {json.dumps(data, indent=2)}")
                
                country = data.get('country', 'UN')
                city = data.get('city', 'Unknown')
                
                print(f"      📍 Country: {country}")
                print(f"      📍 City: {city}")
                
                if country == 'SG':
                    print("      🇸🇬 *** SINGAPORE DETECTED! ***")
            else:
                print(f"      ❌ Bad status: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Method C: Direct IP lookup (without proxy)
        print("\n   📍 Direct lookup of exit IP (no proxy):")
        try:
            direct_response = requests.get(
                f'http://ip-api.com/json/{exit_ip}',
                timeout=3
            )
            
            if direct_response.status_code == 200:
                data = direct_response.json()
                print(f"      Country: {data.get('countryCode')}")
                print(f"      City: {data.get('city')}")
                print(f"      ISP: {data.get('isp')}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Small delay between tests
        time.sleep(1)
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    process.terminate()
    time.sleep(1)
    try:
        process.kill()
    except:
        pass
    
    try:
        os.remove('debug-config.yaml')
    except:
        pass
    
    print("\n✅ Debug test complete!")

def debug_simple_test():
    """Even simpler test without Clash"""
    print("\n" + "="*60)
    print("🔍 SIMPLE DEBUG - Testing geo APIs directly")
    print("="*60)
    
    print("\n1️⃣ Testing from your server (no proxy):")
    
    # Test 1: Your server's IP
    try:
        response = requests.get('http://ip-api.com/json', timeout=5)
        data = response.json()
        print(f"   Your server location: {data.get('country')} - {data.get('city')}")
        print(f"   Your IP: {data.get('query')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Check some known IPs
    print("\n2️⃣ Testing known Singapore IPs:")
    
    sg_ips = [
        '103.253.144.1',  # Singapore IP
        '13.250.1.1',      # AWS Singapore
        '188.166.179.1',   # DigitalOcean Singapore
    ]
    
    for ip in sg_ips:
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
            data = response.json()
            print(f"   {ip}: {data.get('countryCode')} - {data.get('city')}")
        except Exception as e:
            print(f"   {ip}: Error - {e}")

def main():
    print("🔍 Clash Aggregator - DEBUG MODE")
    print("=" * 60)
    
    # First, test APIs directly
    debug_simple_test()
    
    # Download Clash if needed
    if not download_clash_core():
        print("❌ Cannot proceed without Clash")
        return
    
    # Fetch some test nodes
    test_nodes = fetch_test_nodes()
    
    if not test_nodes:
        print("❌ No test nodes available")
        return
    
    print(f"\n📊 Got {len(test_nodes)} test nodes")
    
    # Run detailed debug test
    debug_test_with_clash(test_nodes)
    
    print("\n" + "="*60)
    print("Debug session complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
