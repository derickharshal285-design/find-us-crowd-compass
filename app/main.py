"""Application CLI: run the responder app on the pure-Python verified core.

Usage:
  PYTHONPATH=core python3 app/main.py selftest
  PYTHONPATH=core python3 app/main.py demo
  PYTHONPATH=core python3 app/main.py shell

"demo"    - scripted stadium incident; a responder walks the gradient.
"shell"   - build your own incident interactively.
"""
from __future__ import annotations

import math
import sys
from typing import Dict, List, Optional, Tuple

import domain
from devices import DeviceApp
from world import AppWorld

HELP = """
commands:
  place NAME X Y        put a phone in the world
  sos   NAME [SOS_ID]   start an emergency on that phone
  renew NAME [SOS_ID]   origin refreshes its emergency (version bump)
  end   NAME [SOS_ID]   origin ends its emergency
  step  [N]             advance world time N ticks
  guid  NAME            guidance the responder sees
  move  NAME DX DY      move a phone by a delta
  tele  NAME X Y        teleport a phone
  net                   adjacency + gradient table
  aid   NAME [SOS_ID]   live re-check: every device's guidance for that SOS
  split NAME...         cut a phone off the radio (no packets in/out)
  grid                  per-device adopted hops for every active SOS
  quit|help
""".strip()


def banner(w: AppWorld, sos_id: str) -> None:
    grid = w.hop_grid(sos_id)
    cols = sorted({c for row in grid.values() for c in row})
    print("  " + "".join(f"{c:>6}" for c in cols))
    for nid, row in grid.items():
        print(f"{str(nid):>4}" + "".join(
            f"{row.get(c, '.') if row.get(c) is not None else '.':>6}" for c in cols))


def run_demo() -> None:
    print("=== STADIUM INCIDENT (spec §56–57 scenario) ===")
    print("radio range 80 m, no packet loss, deterministic seed.\n")

    w = AppWorld(dt=1.0, seed=7)
    w.add_device(DeviceApp("T"), 0.0, 0.0)
    for i in range(6):
        deg = i * 60
        rad = math.radians(deg)
        w.add_device(DeviceApp(f"c{i + 1}"), 45 * math.cos(rad), 45 * math.sin(rad))
    w.add_device(DeviceApp("g"), 120.0, 0.0)
    w.add_device(DeviceApp("R", has_direction_sensor=False), 185.0, 0.0)
    w.add_device(DeviceApp("w1"), 320.0, 40.0)
    w.add_device(DeviceApp("w2"), 300.0, -30.0)

    w.set_sos("T", "MAIN")
    for _ in range(6):
        w.step()

    print("hop map of MAIN after 6 ticks (each phone shows its own adopted hop):")
    grid = w.hop_grid("MAIN")
    for nid, row in sorted(grid.items()):
        hop = row.get(str(nid), "-")
        print(f"  {str(nid):>3}  hop {hop}   neighbors: {w.devices[nid].neighbors_text()}")
    print()

    print("responder R walks toward the gradient. honest clues only:\n")
    step_no = 0
    while True:
        step_no += 1
        g = w.devices["R"].guidance("MAIN")
        dist = w.radio.distance("R", "T")
        print(f"t={w.t:4.0f}  R at hop {g.my_hop}  "
              f"physical dist to T {dist if dist is None else round(dist, 1)} m   {g.summary}")
        print(f"          hint: {g.hint}")
        if g.mode == "AT_TARGET" or (dist is not None and dist <= 15):
            break
        if step_no > 40:
            print("  (stopping after 40 steps)")
            break
        if g.mode == "NAVIGATING":
            move_by = 35.0
            w.move_to("R", w.radio.positions[None].get_abs if False else
                      _current_x(w, "R") - move_by, 0.0)
        else:
            w.move_to("R", _current_x(w, "R") - 10.0, 0.0)
        w.step()

    print("\n=== honesty check: far-away phones have no route, not a fake one ===")
    for name in ("w1", "w2"):
        g = w.devices[name].guidance("MAIN")
        print(f"  {name}: [{g.mode}] {g.summary}")


def _pick_sid(w: AppWorld, arg: Optional[str]) -> str:
    if arg:
        return arg
    sids = _active_sids(w)
    return sids[0] if sids else "SOS-N"


def _current_x(w: AppWorld, name: str) -> float:
    return w.radio.positions[domain.NodeId(str(name))][0]


def run_shell() -> None:
    print("crowd-compass application shell. type 'help' for commands.")
    w = AppWorld(dt=1.0)
    while True:
        try:
            line = input("cc> ").strip()
        except EOFError:
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]
        try:
            _dispatch(w, cmd, args)
        except (KeyError, ValueError, IndexError) as exc:
            print(f"  ! {exc}")


def _dispatch(w: AppWorld, cmd: str, a: List[str]) -> None:
    if cmd in ("help", "h"):
        print(HELP)
    elif cmd == "quit":
        raise SystemExit
    elif cmd == "place" and len(a) >= 3:
        w.add_device(DeviceApp(a[0]), float(a[1]), float(a[2]))
        print(f"  placed {a[0]}")
    elif cmd == "sos" and len(a) >= 1 and a[0] in [str(k) for k in w.devices]:
        sid = a[1] if len(a) > 1 else "SOS-N"
        w.set_sos(a[0], sid)
        print(f"  {a[0]} starts {sid}")
    elif cmd == "renew" and len(a) >= 1:
        w.devices[a[0]].renew_sos(_pick_sid(w, a[1] if len(a) > 1 else None))
        print("  renewed")
    elif cmd == "end" and len(a) >= 1:
        w.devices[a[0]].end_sos(_pick_sid(w, a[1] if len(a) > 1 else None))
        print("  ended")
    elif cmd == "step":
        n = int(a[0]) if a else 1
        for _ in range(n):
            w.step()
        print(f"  t={w.t:.0f}")
    elif cmd == "guid" and len(a) >= 1:
        g = w.devices[a[0]].guidance(_pick_sid(w, a[1] if len(a) > 1 else None))
        print(f"  [{g.mode}] {g.summary}")
        if g.hint:
            print(f"  hint: {g.hint}")
    elif cmd == "aid" and len(a) >= 1:
        sid = _pick_sid(w, a[1] if len(a) > 1 else None)
        for nid, dev in sorted(w.devices.items()):
            g = dev.guidance(sid)
            print(f"  {nid}: [{g.mode}] hop={g.my_hop} {g.summary}")
    elif cmd == "move" and len(a) >= 3:
        w.move_to(a[0], _current_x(w, a[0]) + float(a[1]),
                  _current_pos(w, a[0])[1] + float(a[2]))
        print("  moved")
    elif cmd == "tele" and len(a) >= 3:
        w.move_to(a[0], float(a[1]), float(a[2]))
        print("  teleported")
    elif cmd == "net":
        sids = _active_sids(w)
        for nid, dev in sorted(w.devices.items()):
            print(f"  {nid}: {dev.neighbors_text()}")
            for sid in sids:
                hop = dev.sos_engine.hop_of(sid, nid)
                print(f"      {sid} hop={hop}")
    elif cmd == "grid":
        for sid in _active_sids(w):
            print(f"  incident {sid}:")
            banner(w, sid)
    elif cmd == "split" and len(a) >= 1:
        w.split_off(*a)
        print(f"  radio-cut: {', '.join(a)}")
    elif cmd == "reconnect" and len(a) >= 1:
        w.reconnect(*a)
        print(f"  restored: {', '.join(a)}")
    else:
        print("  ? unknown or malformed (see 'help')")


def _current_pos(w: AppWorld, name: str) -> Tuple[float, float]:
    return w.radio.positions[domain.NodeId(str(name))]


def _active_sids(w: AppWorld) -> List[str]:
    sids: Dict[str, None] = {}
    for dev in w.devices.values():
        for sid in dev.sos_engine.events:
            sids[str(sid)] = None
    return sorted(sids)


def main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "selftest"
    if cmd == "selftest":
        _selftest()
    elif cmd == "demo":
        run_demo()
    elif cmd == "shell":
        run_shell()
    else:
        print("unknown command:", cmd)
        print("use: selftest | demo | shell")
        return 1
    return 0


def _selftest() -> None:
    from devices import _test as d
    from guidance import _test as gg
    from world import _test as wt
    d(); gg(); wt()
    print("app selftests: ALL PASSED")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))