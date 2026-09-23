# THE WHOLE-PROJECT INFRASTRUCTURE SPINE

One digit = one home; the whole system, not the singular parts:

```
                     ┌───────────────────────────┐
                     │ 00_START_HERE (read-first) │
                     └───────────┬───────────────┘
                                 │ redirect
             ┌───────────────────▼───────────────────┐
             │ 01_PAPER 01_manuscript (THE paper)    │  ← the spine
             └──────┬───────────┬───────────┬───────┘
                    │           │           │
        ┌───────────▼──┐  ┌─────▼────┐  ┌───▼────────┐
        │ 02_SOURCES   │  │ 03_GAPS  │  │ 04_DUMP    │  ← research atoms
        │ S-01..S-09   │  │ G-INT..  │  │ 30 vign.   │
        └───────────┬──┘  └─────┬────┘  └───┬────────┘
                    │           │           │
     ┌──────────────▼───┐       │       ┌───▼────────────┐
     │ 05_FINDINGS      │◀──────┴──────▶│ 06_SITE (Vercel)│
     └──────────────┬───┘      whole    └───┬────────────┘
                    │        project map    │
     ┌──────────────▼───┐       │       ┌───▼────────────┐
     │ 07_TOOLS md2pdf +│───────┴──────▶│ 08_WATCHDOG     │
     │ md2pdf.py render │   phone-hole   watchdog+gateway │
     └──────────────┬───┘   (watchdog)   └───┬───────────┘
                    │           │           │
                    └───────────┴───────────┘
                     mutual gateway: every home checks every home;
                     ghost decays; honesty ledger live
```

`[RES]` homes unique (byte-proven, 0 collisions project-wide). `[PROPOSED]`
watchdog+gateway + interactive mesh site: `[EXP:NOT-RUN]` in the paper's honesty
frames until two real phones are connected and the test is run.
