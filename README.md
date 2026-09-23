# Find Us — Crowd Compass · Repo Manifest (canonical)

> **Orientation: RESEARCH-FIRST.** This repo's spine is *not* the iOS build — it is the
> single detailed paper and the research corpus that justify it. The native build is a
> downstream artifact of the research, not the headline. Papers first; build next.

---

## 1. The single detailed paper (the deliverable)

**ONE canonical manuscript, both homes (repo + Android mirror), byte-matched:**

| Artifact | Home (repo) | Bytes |
|---|---|---|
| Manuscript (Markdown) | `research/01_PAPER/01_manuscript.md` | 116,607 |
| Manuscript (PDF render) | `research/01_PAPER/01_manuscript.pdf` | 122,948 |

The paper is §1–§10, first-principles, and carries the honesty frame in its own
text: the phantom performance triple (61.8× boost / 0.015 ms route / 85.3→1.39
mAh/day) appears **only inside `[EXP:NOT-RUN]` honesty frames** — it is a
*designed hypothetical*, never a reported result stub. The one real gap survives
honestly: the 2-phone end-to-end demo (E10) has **not yet been run**, and the
paper says so.

## 2. The research corpus (the body)

- **30 numbered vignettes** at `research/` root (`00_START_HERE` … `29_IMPLEMENTATION`)
  — the concept-by-concept research body, each honest-tagged.
- **labeled homes** `research/01_PAPER … 07_TOOLS` — the paper, SOURCES ledger,
  GAPS ledger, research dump, findings, tools, all filed, zero loose at root.
- **`INDEX.md`** at top — the directory map.

## 3. The interactive teaching site

- Source: `website/` (self-contained `index.html`, runs the current corpus)
- GitHub Pages: served from the `main` branch's `website/` via `gh-pages`/Pages
  config in `DOCUMENTATION.md`.

## 4. The honest documentation set

- `DOCUMENTATION.md` — the complete, current, research-first documentation.
- `docs/` — per-area docs, all updated to research-first orientation.
- `research/` — the corpus (paper + ledger + numbered vignettes).

## 5. Honesty constitution (non-negotiable)

1. Every claim carries an integrity tag: `[RES]` verified · `[PROPOSED]` design ·
   `[SPEC]` specified · `[EXP:NOT-RUN]` not yet executed · `[UNVERIFIED]`.
2. The phantom triple lives **only** inside `[EXP:NOT-RUN]` frames. Never as a result.
3. Zero fabricated citations · zero fabricated DOIs · zero fabricated results.
4. The integration gap **G-INT** survives as honestly `[PROPOSED] · [EXP:NOT-RUN]`.
5. E10 (the two-phone demo) is the un-run honesty gate — no "works" claim until a
   real-device run happens.
6. Illegitimate or exposed credentials are never used, never persisted, never echoed.

## 6. Status (bytes, verified)

- Latest commit: `a0d6759` — pushed to `main`; verified identical to `origin/main`.
- Paper PDF text re-rendered fresh from the manuscript.
- Site rebuilt + mirrored to `/storage/emulated/0/CrowdCompass/06_SITE/`.
- Secrets audit: 0 token-shaped strings in the tree (shapes `gsk_`, `ghp_`,
  `github_pat_`, `sk-` swept, counts only).
