# Find Us / Crowd Compass — WHOLE-PROJECT INDEX (one digit = one home)

> **READ FIRST, IN THIS ORDER.** This repo is **RESEARCH-FIRST**: the single
> detailed paper is the deliverable; the native build + mesh are downstream
> artifacts of it. Everything below links to a real on-disk file.

## ⚑ The spine (whole-project renumber: one digit = one home)
| digit | home | what lives there |
|------|------|------------------|
| 00 | `research/00_START_HERE_*` | The numbered entry vignettes (00_START_HERE … 29_IMPLEMENTATION) — 30-part research body |
| 01 | `research/01_PAPER` | **THE single detailed paper**: `01_manuscript.md` (116,607 B) + `.pdf` (122,948 B), §1–§10, honesty-tagged |
| 02 | `research/02_SOURCES` | **Credits ledger** — S-01…S-09, every key `[VERIFIED]/[PARTIAL]/[UNVERIFIED]`, 0 fabricated |
| 03 | `research/03_GAPS` | **Honest gaps** — G-INT integration gap + G-L1.1…G-L6.2, every gap honesty-tagged, EXP:NOT-RUN visible |
| 04 | `research/04_RESEARCH_DUMP` | Full research corpus + unit-test parity |
| 05 | `research/05_FINDINGS` | Findings ledger (findings.md) + REPORT + LITERATURE (archived into primitive/) |
| 06 | `research/06_SITE` / `website/` | **Interactive teaching site** — drag-drop phones, shortest-distance math, Vercel-ready |
| 07 | `research/07_TOOLS` | Build/convert tools (md2pdf.py, renderers) |
| 08 | `research/08_TOOLS` | Mesh skeleton + watchdog (health ledger + mutual gateway) — `[PROPOSED][EXP:NOT-RUN]` |
| — | `research/primitive/` | Superseded-but-kept homes (never deleted, never claimed) |

## ⚑ What to read, to learn the whole thing from the start
1. **The paper** → `research/01_PAPER/01_manuscript.md` (or `.pdf`) — §1–§10, THE detailed deliverable.
2. **Who built what (credits!)** → `research/02_SOURCES/SOURCES.md` — S-01…S-09 ledger, byte-verified.
3. **What is honestly NOT proven** → `research/03_GAPS/GAPS.md` — G-INT + the EXP:NOT-RUN phantom-triple honesty frames.
4. **The research body** → `research/00_START_HERE…29_IMPLEMENTATION` (30 numbered vignettes).
5. **The interactive site** → `website/index.html` (drag-drop phones, shortest-distance math) — or live Vercel URL.

## ⚑ The research is for the WHOLE project — not singular parts
Every open question maps to a home (see `docs/RESEARCH_QUESTIONS.md`: **Q1–Q4 · Level 1–5 · 68 numbered questions · the 3 biggest**). Each numbered vignette, each S-key, each G-key is one atom of ONE project: the infrastructure-independent crowd-mesh that finds people in emergencies. Nothing is a "singular part" deliverable; the paper is the whole.

## ⚑ Honesty constitution (non-negotiable)
- Every claim: `[RES]` / `[PROPOSED]` / `[SPEC]` / `[EXP:NOT-RUN]` / `[UNVERIFIED]`.
- The phantom triple (61.8× / 0.015 ms / 85.3→1.39 mAh/day) appears ONLY inside `[EXP:NOT-RUN]` honesty frames — **never as a result**.
- Zero fabricated citations · zero fabricated DOIs · zero fabricated results.
- E10 (real 2-phone demo) has **not run** — the paper says so. No "works" claim until it runs.

## ⚑ Deploy
- **Website**: static, Vercel-compatible — push `website/` to GitHub, import to Vercel, one deploy. Interactive (drag-drop phones, shortest-distance math) included.
- **Mesh skeleton** (`research/08_TOOLS` + watchdog): pure-Python, runs in Termux; connect two instances and test — `[EXP:NOT-RUN]` until you do.
