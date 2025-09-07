import fs from "fs";
import yaml from "js-yaml";
import fetch from "node-fetch";

// === Read sources from sources.txt ===
const sources = fs.readFileSync("sources.txt", "utf8")
  .split("\n")
  .map(line => line.trim())
  .filter(line => line.length > 0);

async function getCountryCode(host) {
  try {
    // DNS lookup
    const ipResp = await fetch(`https://dns.google/resolve?name=${host}`);
    const ipJson = await ipResp.json();
    const ip = ipJson.Answer?.[0]?.data;
    if (!ip) return "UN";

    // IP → country
    const geoResp = await fetch(`http://ip-api.com/json/${ip}?fields=countryCode`);
    const geoJson = await geoResp.json();
    return geoJson.countryCode || "UN";
  } catch (e) {
    return "UN";
  }
}

function flagEmoji(cc) {
  return cc
    .toUpperCase()
    .replace(/./g, char => String.fromCodePoint(127397 + char.charCodeAt()));
}

(async () => {
  let allProxies = [];

  // 1. Fetch all sources
  for (const url of sources) {
    try {
      console.log(`Fetching ${url}`);
      const resp = await fetch(url, { timeout: 15000 }); // 15s timeout
      if (!resp.ok) {
        console.warn(`⚠️ Failed to fetch ${url}: HTTP ${resp.status}`);
        continue;
      }
      const text = await resp.text();
      const data = yaml.load(text);

      if (data.proxies) {
        allProxies.push(...data.proxies);
      } else {
        console.warn(`⚠️ No proxies found in ${url}`);
      }
    } catch (e) {
      console.warn(`⚠️ Error fetching ${url}: ${e.message}`);
    }
  }

  if (allProxies.length === 0) {
    console.error("❌ No proxies collected from any source.");
    process.exit(1);
  }

  // 2. Geolocate and rename
  let counter = {};
  let newProxies = [];
  for (const proxy of allProxies) {
    const host = proxy.server;
    const cc = await getCountryCode(host);
    const flag = flagEmoji(cc);

    if (!counter[cc]) counter[cc] = 1;
    const id = String(counter[cc]).padStart(3, "0");
    counter[cc]++;

    const newProxy = { ...proxy, name: `${flag} ${id}` };
    newProxies.push(newProxy);
  }

  // 3. Save YAML with proxies only
  const result = { proxies: newProxies };
  fs.mkdirSync("output", { recursive: true }); // ensure folder exists
  fs.writeFileSync("output/subscription.yaml", yaml.dump(result), "utf8");

  console.log(`✅ Wrote ${newProxies.length} proxies to output/subscription.yaml`);
})();
