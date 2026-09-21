# Research Corpus — Index

Everything about *what*, *why*, and *how much we actually measured*. Papers,
specs and experiments are separate from app code.

## Where to start
- `01_EXECUTIVE_SUMMARY_CONCISE.md` — the 5-minute version.
- `paper/01_manuscript.md` + `paper/01_manuscript.pdf` — **v0.5, the full paper** (46 sections, ~34 printed pages, through a 5-seat review round).
- `paper/ip/00_ip_analysis.md` — candidate-property (IP) review v1.0.
- `research-log.md` — chronological cycle log.
- `research-state.yaml` — machine-readable project state.

## Numbered working docs (01–30)
| Doc | Topic |
| --- | --- |
| 00 | Read this first (the MOC) |
| 01 | Executive summary |
| 02 | Topological gradient field pivot |
| 03 | Critical physical hazards |
| 04 | Terminal navigation & radical stress tests |
| 05 | Problem dependency audit (12 sub-problems) |
| 06 | Tiny packet specification |
| 07 | Rigorous critique & mathematical corrections |
| 08 | Plain-English navigation guide |
| 09 | Progressive navigation resolution |
| 10 | Master chat-QA & onboarding reference |
| 11 | Dynamic relative coordinate math & calibration |
| 12 | The newcomer problem: why SLAM fails and how we fix it |
| 13 | The vector displacement reality check |
| 14 | Brutal real-world teardown & critique |
| 15 | Engineering solutions for real-world failures |
| 16 | Technical navigation edge cases & heterogeneity |
| 17 | Data-mule mesh partition healing |
| 18 | BLE advertising transport reality |
| 19 | Async schedule mesh operating model |
| 20 | Packet v2 wire format |
| 21 | Async trickle mesh design |
| 22 | Anti-spoofing envelope MAC |
| 23 | RF confirmation-wall alerts |
| 24 | Storm backoff protocol |
| 25 | PDR activity-gating spec |
| 26 | Terminal handoff protocol |
| 27 | Ghost-gradient resolution |
| 28 | Multilevel baro & stairwell |
| 29 | Implementation blueprint v1 |
| 30 | (spec appendix) |

## Folder reference
- `paper/` — manuscript + IP + review panel artifacts (+ generated PDFs via `md2pdf.py`).
- `findings.md` — consolidated findings capture.
- `QUES/` — questionnaire / master-spec notes (`CrowdCompass_Master_Spec.md`).

> Honesty rule: every claim in the corpus carries an evidence band
> (implemented / measured / model / field-open / not-run). Nothing in this repo
> pretends a field deployment has happened — see `paper/01_manuscript.md` §46.