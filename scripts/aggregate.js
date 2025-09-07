// aggregate.js (CommonJS version)

const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");
const YAML = require("yaml");

// Read sources.txt (list of URLs)
const sourcesFile = path.join(__dirname, "sources.txt");
const urls = fs.readFileSync(sourcesFile, "utf8")
  .split("\n")
  .map(l => l.trim())
  .filter(l => l && !l.startsWith("#"));

async function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith("https") ? https : http;
    lib.get(url, res => {
      if (res.statusCode !== 200) {
        reject(new Error(`Failed to fetch ${url}: ${res.statusCode}`));
        return;
      }
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => resolve(data));
    }).on("error", reject);
  });
}

(async () => {
  let allProxies = [];

  for (const url of urls) {
    console.log(`🌐 Fetching: ${url}`);
    try {
      const text = await fetchUrl(url);
      const parsed = YAML.parse(text);

      if (parsed && Array.isArray(parsed.proxies)) {
        console.log(`✔ Got ${parsed.proxies.length} proxies`);
        allProxies.push(...parsed.proxies);
      } else {
        console.log(`⚠ No proxies in this file`);
      }
    } catch (err) {
      console.error(`✘ Failed to fetch ${url}: ${err.message}`);
    }
  }

  console.log(`\n✅ Total proxies: ${allProxies.length}`);

  // Ensure output folder
  fs.mkdirSync(path.join(__dirname, "../output"), { recursive: true });

  // Write combined subscription
  const outFile = path.join(__dirname, "../output/subscription.yaml");
  const yaml = YAML.stringify({ proxies: allProxies });
  fs.writeFileSync(outFile, yaml, "utf8");

  console.log(`📦 Wrote subscription to ${outFile}`);
})();
