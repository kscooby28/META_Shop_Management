/* Node driver for the credentials suite (WO15).
 * Run directly with node, or through tests/test_credentials.py.
 * Exits nonzero on the first failure. Canary values prove no credential
 * value reaches any fetch call, any log line, or any rendered presence
 * line: fetch throws if touched, console output is captured, and every
 * rendered string is scanned for the canaries. */
"use strict";

const Credentials = require("../web/credentials.js");

let count = 0;
function ok(cond, name) {
  count += 1;
  if (!cond) {
    console.error("FAIL " + count + ": " + name);
    process.exitCode = 1;
  } else {
    console.log("ok " + count + " - " + name);
  }
}
function throws(fn, name) {
  count += 1;
  try {
    fn();
    console.error("FAIL " + count + " (no throw): " + name);
    process.exitCode = 1;
  } catch (err) {
    console.log("ok " + count + " - " + name + " [" + err.message + "]");
  }
}
function memStore(backing) {
  const data = backing || {};
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
  };
}

// Any network attempt fails loudly.
global.fetch = () => { throw new Error("network touched"); };
global.XMLHttpRequest = function () { throw new Error("network touched"); };

// Capture every log line for the canary scan.
const logged = [];
for (const level of ["log", "error", "warn", "info"]) {
  const real = console[level];
  console[level] = (...args) => {
    logged.push(args.map(String).join(" "));
    real.apply(console, args);
  };
}

const CANARIES = ["canary-shop-user-1", "canary-shop-pass-2", "canary-email-key-3",
  "canary-store-user-4", "canary-store-pass-5", "canary-ebay-dev-6", "canary-ebay-auth-7"];
const rendered = [];
function leakScan(name) {
  const hay = rendered.join("\n") + "\n" + logged.join("\n");
  ok(CANARIES.every((c) => hay.indexOf(c) < 0), name);
}

// ---- both profiles: save, presence, clear ----
const store = memStore();
const empty = Credentials.presence(store, "shop");
ok(Object.keys(empty).length === 3 && Object.keys(empty).every((k) => empty[k] === false),
  "shop profile starts all not-set");
const diyEmpty = Credentials.presence(store, "diy");
ok(Object.keys(diyEmpty).length === 4 && Object.keys(diyEmpty).every((k) => diyEmpty[k] === false),
  "diy profile starts all not-set");

Credentials.saveCreds(store, "shop", {
  distributorUser: CANARIES[0], distributorPass: CANARIES[1], emailApiKey: CANARIES[2],
});
const shopGot = Credentials.presence(store, "shop");
ok(shopGot.distributorUser && shopGot.distributorPass && shopGot.emailApiKey,
  "shop credentials save and read back as set");
Credentials.saveCreds(store, "diy", {
  storeUser: CANARIES[3], storePass: CANARIES[4], ebayDevKey: CANARIES[5], ebayAuth: CANARIES[6],
});
const diyGot = Credentials.presence(store, "diy");
ok(diyGot.storeUser && diyGot.storePass && diyGot.ebayDevKey && diyGot.ebayAuth,
  "diy credentials save and read back as set");

for (const line of Credentials.presenceLines(store)) rendered.push(line.text);
ok(rendered.some((t) => t === "Distributor username: set"), "presence renders set, not the value");
ok(rendered.every((t) => t.endsWith("set") || t.endsWith("not set")), "every presence line is set/not-set only");

Credentials.clearCreds(store, "shop");
ok(Object.keys(Credentials.presence(store, "shop")).every((k) => !Credentials.presence(store, "shop")[k]),
  "clearing the shop profile unsets every field");
ok(Credentials.presence(store, "diy").ebayDevKey === true, "clearing shop leaves diy alone");

// ---- mock distributor + store logins ----
const noShop = memStore();
throws(() => Credentials.mockDistributorLogin(noShop), "distributor mock needs the login first");
Credentials.saveCreds(noShop, "shop", { distributorUser: "demo-supplier-user", distributorPass: "demo-only" });
const dist = Credentials.mockDistributorLogin(noShop);
rendered.push(JSON.stringify(dist));
ok(dist.demo === true && /demo/i.test(dist.supplier) && /demo/i.test(dist.note),
  "mock distributor login returns a demo-labeled session");
ok(JSON.stringify(dist).indexOf("demo-supplier-user") < 0,
  "mock distributor session withholds the username");
const noStore = memStore();
throws(() => Credentials.mockStoreLogin(noStore), "store mock needs the login first");
Credentials.saveCreds(noStore, "diy", { storeUser: "demo-store-user", storePass: "demo-only" });
const st = Credentials.mockStoreLogin(noStore);
rendered.push(JSON.stringify(st));
ok(st.demo === true && /demo/i.test(st.store) && /demo/i.test(st.note),
  "mock store login returns a demo-labeled session");
ok(JSON.stringify(st).indexOf("demo-store-user") < 0,
  "mock store session withholds the username");

// ---- mock new-vs-used price check ----
const known = Credentials.mockNewPrice("rear differential");
rendered.push(JSON.stringify(known));
ok(known.known === true && known.demo === true && typeof known.newPrice === "number" &&
  /demo-mock/i.test(known.source), "mock new price is labeled demo-mock fiction");
const unknown = Credentials.mockNewPrice("left-handed smoke shifter");
rendered.push(JSON.stringify(unknown));
ok(unknown.known === false && /never guessed/i.test(unknown.note),
  "unknown part reads unknown, never guessed");

// ---- the gate: mock eBay post ----
const gate = memStore();
throws(() => Credentials.mockEbayPost({ draft: { title: "x" }, approval: null, storage: gate }),
  "mock post without any approval throws");
throws(() => Credentials.mockEbayPost({ draft: { title: "x" }, approval: { approved: false }, storage: gate }),
  "mock post with a denied approval throws");
throws(() => Credentials.mockEbayPost(
  { draft: { title: "x" }, approval: { approved: true, draftId: "d1" }, storage: gate }),
  "mock post with approval but no eBay credentials throws");
Credentials.saveCreds(gate, "diy", { ebayDevKey: "demo-dev-key", ebayAuth: "demo-auth" });
const posted = Credentials.mockEbayPost(
  { draft: { title: "Rear differential" }, approval: { approved: true, draftId: "d1" }, storage: gate });
rendered.push(JSON.stringify(posted));
ok(posted.demo === true && posted.adapter === "mock-ebay-developer-api",
  "approved + credentialed mock post returns a demo listing");
ok(/demo mock/i.test(posted.listing.status) && /^mock-ebay-/.test(posted.listing.id),
  "mock listing id and status are demo-marked");
ok(/cha-ching/i.test(posted.chaching) && /demo mock/i.test(posted.chaching),
  "mock cha-ching is labeled demo");

// ---- the never-leaves rule ----
leakScan("no canary value reached any render, log, or mock output");

console.log("ALL " + count + " credentials checks ran");
