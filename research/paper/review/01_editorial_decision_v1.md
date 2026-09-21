# Editorial Decision & Revision Roadmap — Find Us Manuscript v0.4

Source: academic-paper-reviewer panel (5 seats, read-only). Panel was run on-
platform (single model family), five role-separated seats; per Role-Separation
#610 the seats are not independent error processes — the typed provenance is:
role-separated, same-family, non-independent-by-construction.

## Editorial Decision

**DECISION: MAJOR REVISION** (system-design tier), re-submission-ready only
after the evidence-consolidation work below.

Summary rationale:
- No seat votes Reject; the design record, honesty apparatus, and the
  critique-repair engineering (quantized Trickle congruence, det(R)=+1
  reflection rule, switchable-constraint PGO) are genuine contributions.
- Consensus blocker for flagship systems venues: **zero hardware validation**
  and **[EXP:NOT-RUN] density** across E13/E15/E17/E21/E22 (+E31/E32). The
  paper self-scopes to simulation; that is integrity, but it caps venue fit to
  applied-systems / design-track.
- Methodology seat: analysis is the weakest zone — placeholder metrics (RQ4/RQ11
  "X% / target degrees"), [RES] claims without point estimates, no variance/CI,
  one-line Appendix J, and marker slip "[ESP→EXP]".
- Domain seat: contribution framing (Sec 25.3 "cannot loop", G2/G5 gap claims)
  exceeds the evidence and the cited prior art; ~8/34 references are gesture
  citations; rigidity theory is name-dropped, never applied; nearest-lineage
  works (directed diffusion, DV-hop/APS, Doherty convex, AFL) are missing.
- Devil's Advocate (two CRITICAL adjudicated, both VALIDATED):
  1. Evidence-upgrade: Sec 13.5/25.3 present quantized-congruence and the
     anti-loop property as settled while E31/E32 are NOT-RUN. Adjudicated:
     VALIDATED — must be re-scoped to conditional/lemmas.
  2. Anti-rumor presupposes graph consistency, which fails on direction-less
     1-DoF trees; the loop-suppression argument silently collapses there.
     Adjudicated: VALIDATED with the 17.4/39.1 evidence — re-scope to
     direction-complete subgraphs, else accept the hole.
- Perspective seat: "foreground-service as feature" reads as rhetoric vs the
  notification-flood it must survive; QR OOB onboarding is operationally heroic;
  glanceability/accessibility are unsupported design; privacy claims need an
  at-risk-community governance paragraph.

## Immutable Revision Roadmap (non-ranked)

Note: "Repair/minimum" only — optional/stronger options are reserved.

### A. Evidence integrity (Methodology + DA — highest priority)
1. **Kill the placeholders.** RQ4 "within X% of baseline" and RQ11 "error <
   target degrees" must carry concrete values or be reworded without the hole
   (Sec 11).
2. **Point estimates + spread.** For every [RES] headline, publish the point
   estimate and spread as measured in the repo run registry (run ids are
   anchorable: exp_002_trickle, exp_008..exp_016 ...), or relabel the claim
   "[RES: qualitative]". At minimum cover E3, E9, E14, E11.
3. **Executed→reported audit.** Add one compact table mapping the 18 executed
   runs to the Sec 36 subsections that report them; 8 executed experiments
   (E2/E4/E7/E10/E12/E16/E20/E23) have no numeric surface — led to repo or
   surface them.
4. **Appendix J must be executable config.** Seeds, placement/mobility model,
   churn/participation ratios, trickle constants, propagation/shadowing model,
   timers; pin to a repo commit.
5. **Marker slips.** Fix "[ESP→EXP]" (Sec 35.3); qualify the 1.32/14.23 µAh/s
   constants as model-derived, not measured; reword Sec 21.4 "proof assert" to
   "verification assert (E32 pending)".

### B. Claim scoping (Domain + DA CRITICAL)
6. **Sec 25.3 anti-loop claim → conditional lemma:** prove/state it for
   direction-complete subgraphs with closed walks; explicitly acknowledge the
   tree/no-cycle case and its consequence (loop-suppression not guaranteed
   there) — closes DA-CRITICAL-2.
7. **Sec 13.5/39.3 corrective framing is provisional on E31;** tag E3/RQ4/RQ5
   "provisional until E31" (closes DA-CRITICAL-1).
8. **G2/G5 gap claims:** temper "no single prior work" to "no single prior
   work *in the BLE-advertising/byte-ceiling + navigable-gradient* framing,"
   add the missing prior-art lineage (directed diffusion; DV-hop/APS; Doherty
   convex; AFL) to Sec 7/8 and differentiate.
9. **Rigidity grounding:** state the global-rigidity conditions (anchoring
   requirements) under which VRLG realization is unique; note cycle-consistency
   is necessary, not sufficient.

### C. Platform/human honesty (EIC + Perspective)
10. **Foreground-service claim tone:** drop "earns its notification" rhetoric;
    add the notification-flood-as-storm-class quantification to the storm
    discussion (or retract).
11. **Accessibility/HCI:** cite emergency UI literature and frame locked-jaw
    co-design as required future work, not shipped design.
12. **Governance (privacy):** add a short paragraph on venue-authority
    activation and at-risk communities; temper "privacy architecture"
    (Sec 29.1) to "privacy-preference architecture with open traceability gap."
13. **QR OOB cost:** acknowledge operational cost of fingerprint scanning under
    panic in Sec 39.6; mark it as a pre-arrival pairing feature (not in-crisis).

### D. References (Domain)
14. Add: Intanagonwiwat et al. 2000 (directed diffusion); Niculescu & Nath 2003
    (DV-hop/APS); Doherty et al. 2001 (convex position estimation); Priyantha et
    al. 2005 (AFL). Fix [11] first author (Kimera-Multi); split/fix [15] bridge-
    fy-incident vs USENIX traceability; give [16] venue; either pin or delete
    gesture refs [17][18][22][25][32][34].

### E. Optional (not required for this round)
15. Snapshot consolidation of the 46-section structure into fewer claim tables
    (EIC readability); consider a standalone Honesty Audit appendix.

## DA-CRITICAL adjudication record (mandatory)
- DA-CRITICAL-1 (evidence upgrade in 13.5/25.3): **validated.** Mapped §6-7.
- DA-CRITICAL-2 (anti-rumor presupposes consistency; tree/no-cycle hole):
  **validated.** Mapped §6, B.
- Both block the current "settled" wording; §7 renders them as conditional
  claims, satisfying the blocker. No silent bypass.