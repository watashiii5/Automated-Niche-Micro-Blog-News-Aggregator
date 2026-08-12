// AdSense configuration for NichePulse.
//
// Until `client` is set, the site shows neutral "Advertisement" placeholders
// in each slot instead of real ads.
//
// To enable real ads:
//   1. Create an AdSense account, add this site, and get approved.
//   2. Paste your publisher ID (starts with "ca-pub-") into `client` below.
//   3. In your AdSense dashboard create one ad unit per slot below and paste
//      its unit ID into the matching `slot` field.
//   4. Commit and push. The next GitHub Actions build deploys it.
//
// Note: AdSense only serves ads on pages it can crawl. If your blog is behind
// the client-side login gate, Google may refuse to show ads on gated pages.
window.ADSENSE = {
  client: "",
  units: {
    "ad-top":  { slot: "", width: 728, height: 90 },
    "ad-feed": { slot: "", width: 300, height: 250 },
  },
};
