def get_server_location(server_ip):
    """Get country code using ipinfo.io with debug info"""
    if not server_ip:
        return 'UN'
    
    # Resolve domain to IP if needed
    try:
        socket.inet_aton(server_ip)
        ip = server_ip
    except socket.error:
        try:
            ip = socket.gethostbyname(server_ip)
        except Exception as e:
            print(f"   ⚠️ Cannot resolve {server_ip}: {e}")
            return 'UN'
    
    try:
        # Use ipinfo.io
        response = requests.get(
            f'https://ipinfo.io/{ip}/json',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Debug: Check for bogus/proxy data
            if 'bogon' in data and data['bogon']:
                print(f"   ⚠️ Bogon IP detected: {ip}")
                return 'UN'
            
            country_code = data.get('country', 'UN')
            
            # Debug: Print unexpected country codes
            if country_code and len(country_code) != 2:
                print(f"   ⚠️ Unusual country code for {ip}: {country_code}")
            
            # Debug: Check if this is a known VPN/hosting provider
            org = data.get('org', '').lower()
            if any(provider in org for provider in ['cloudflare', 'amazon', 'google', 'microsoft', 'digitalocean', 'linode']):
                print(f"   📡 {ip} is from {org} (reported as {country_code})")
            
            return country_code.upper()
        else:
            print(f"   ❌ ipinfo.io returned {response.status_code} for {ip}")
            return 'UN'
        
    except Exception as e:
        print(f"   ❌ Error checking {server_ip}: {e}")
        return 'UN'

def main():
    print("🚀 Starting Clash Aggregator with Debug Mode...")
    print("=" * 50)
    
    # Configuration
    ENABLE_HEALTH_CHECK = False  # Disabled for faster debugging
    DEBUG_MODE = True  # Enable detailed logging
    
    # Read source URLs
    with open('sources.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Found {len(urls)} subscription URLs")
    print(f"🔍 Debug Mode: ON - Will show geo-location details")
    
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
    
    # Get geo-location for each node WITH DEBUGGING
    print(f"\n🌍 Checking geo-locations with debugging...")
    country_nodes = defaultdict(list)
    country_stats = defaultdict(int)
    
    # Sample check - let's verify a few nodes in detail
    sample_size = min(10, len(all_nodes))
    print(f"\n🔬 Sampling first {sample_size} nodes for detailed check:")
    
    for idx, node in enumerate(all_nodes[:sample_size], 1):
        server = get_node_server(node)
        original_name = node.get('name', 'Unknown')
        print(f"\n   Node {idx}: {original_name[:30]}...")
        print(f"   Server: {server}")
        
        if server:
            country_code = get_server_location(server)
            flag = get_flag_by_country_code(country_code)
            print(f"   Detected: {flag} {country_code}")
    
    print(f"\n📍 Processing all nodes...")
    
    for idx, node in enumerate(all_nodes, 1):
        if idx % 10 == 0:
            print(f"   Processing {idx}/{len(all_nodes)}...")
        
        server = get_node_server(node)
        if server:
            country_code = get_server_location(server)
            country_nodes[country_code].append(node)
            country_stats[country_code] += 1
        
        # Small delay to avoid rate limiting
        if idx % 5 == 0:
            time.sleep(0.1)
    
    # Show country distribution
    print(f"\n📊 Country Distribution:")
    for country_code, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        flag = get_flag_by_country_code(country_code)
        print(f"   {flag} {country_code}: {count} nodes")
    
    # Check for missing flags
    missing_flags = [cc for cc in country_stats.keys() if get_flag_by_country_code(cc) == '🌍']
    if missing_flags:
        print(f"\n⚠️ Missing flag mappings for: {', '.join(missing_flags)}")
    
    # Rename nodes with clean format
    renamed_nodes = []
    
    # Process Singapore nodes first
    if 'SG' in country_nodes:
        print(f"\n🇸🇬 Processing {len(country_nodes['SG'])} Singapore nodes...")
        for idx, node in enumerate(country_nodes['SG'], 1):
            node['name'] = f"🇸🇬 SG-{idx:03d}"
            renamed_nodes.append(node)
        del country_nodes['SG']
    
    # Process other countries
    for country_code, nodes in country_nodes.items():
        flag = get_flag_by_country_code(country_code)
        if DEBUG_MODE and flag == '🌍':
            print(f"⚠️ Unknown country code: {country_code} ({len(nodes)} nodes)")
        
        for idx, node in enumerate(nodes, 1):
            node['name'] = f"{flag} {country_code}-{idx:03d}"
            renamed_nodes.append(node)
    
    # Create output structure
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
        f.write(f"# Debug Mode: {DEBUG_MODE}\n")
        f.write("# Generated by Clash-Aggregator\n\n")
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully generated clash.yaml")
    print(f"📊 Final output: {len(renamed_nodes)} nodes")
    
    # Final check - sample some renamed nodes
    if DEBUG_MODE and renamed_nodes:
        print(f"\n🔍 Sample of renamed nodes:")
        for node in renamed_nodes[:5]:
            print(f"   {node['name']} -> {node['server']}")

if __name__ == "__main__":
    main()
