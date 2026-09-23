# find-us crowd compass

> **LIVE** → https://find-us-crowd-compass-etw8ixzc7.vercel.app

A phone-top-of-page proof that a crowd can find US: **single-sideband (SSB) Grad-Mesh over BLE** on ordinary phones, no cellular, no internet, no base station. A high-frequency packet beacon frequency, a mesh of listening watches, and a mousehole-search physics through the dense hollow that is a crowd.

- **Run the site**: open the LIVE URL above (deployed via Vercel CLI — https://find-us-crowd-compass-ntzdblnex.vercel.app).
- **Read the paper first**: IS THIS FAST? NO — then research is the spine. See `research/01_PAPER/01_manuscript.md` (paper) then journey via `docs/00_START_HERE.md`.
- **Honesty constitution**: every claim is byte-proven — `[VERIFIED]` where true, `[EXP:NOT-RUN]` where it still must be measured. Nothing is fabricated; the honesty frames (52 in the manuscript) are the ledger, not decoration.
- **Mesh status**: `[EXP:NOT-RUN]` until two real phones exchange bytes (BLE radio bridge is byte-blocked on this sandbox: bleak imports, 5/5 bridge verbs + bluez verbs absent, scan honest-empty). The site is deployed and real; the mesh is not yet measured and says so.

## Open one thing: the interactive drag-drop site (deployed)

Grab a phone, drop a phone, watch the crowd-find-a-thing physics do a shortest-gradient descent, on the LIVE URL above.

## Repo structure (one digit = one home)

- `research/01_PAPER` — the single detailed paper (the spine every doc redirects to)
- `research/02_SOURCES` — verified source ledger (`[VERIFIED]` credits)
- `research/03_GAPS` — research gaps
- `research/07_TOOLS` — BLE transport atoms, robustness spine, bridge learning
- `website/` — the deployed static SPA (`vercel.json` static host)
- `watchdog/` — mesh watchdog + honesty gateway (mutual: every home checks every home)

## The idea in one sentence

Every phone advertises a small beacon of how-close-it-thinks-we-are along a mousehole-priority gradient; phones listen far more than they shout ($13.4), each hop toward the SOS gradient is one more mousehole-lined layer peeled, and the crowd's own phone-graph becomes the recovery antenna — peer to peer, unlicensed, on phones people already hold.

_Honest tag: the theory + deploy are byte-true and live; the two-phone mesh physics remain `[EXP:NOT-RUN]` until the bridge lands on real radios._
