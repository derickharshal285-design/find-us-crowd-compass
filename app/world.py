"""Application world: wires many DeviceApps together over a radio transport.

The devices never share state — they only exchange wire bytes. The world is
the only thing that knows positions. This is what makes the transport
swappable: today it is the spec's FakeRadio; on-device it will be BLE scanners
exposed through the phone transport (spec §64: the app calls a transport API,
never BLE APIs directly).
"""
from __future__ import annotations

from typing import Any, Dict

import domain
from devices import DeviceApp
from simulation import FakeRadio


class AppWorld:
    def __init__(self, dt: float = 1.0, radio_range: float = 80.0,
                 packet_loss: float = 0.0, seed: int = 0) -> None:
        self.t: float = 0.0
        self.dt: float = dt
        self.radio = FakeRadio(range_m=radio_range, packet_loss=packet_loss,
                               seed=seed)
        self.devices: Dict[domain.NodeId, DeviceApp] = {}

    def add_device(self, device: DeviceApp, x: float, y: float) -> domain.NodeId:
        self.radio.set_position(device.id, (x, y))
        self.devices[device.id] = device
        return device.id

    def move_to(self, node: Any, x: float, y: float) -> None:
        self.radio.set_position(node, (x, y))

    def set_sos(self, device: Any, sos_id: Any, **kw) -> domain.SOS:
        return self.devices[domain.NodeId(str(device))].start_sos(sos_id, **kw)

    def split_off(self, *names: Any) -> None:
        for n in names:
            self.radio.blocked.add(domain.NodeId(str(n)))

    def reconnect(self, *names: Any) -> None:
        for n in names:
            self.radio.blocked.discard(domain.NodeId(str(n)))

    def step(self, rounds_cap: int = 64) -> int:
        """Advance one unit of world time; exchange until quiet.

        Returns the number of SOS adoptions in the final round."""
        self.t += self.dt
        for dev in self.devices.values():
            dev.begin_tick(self.t)
        for _ in range(rounds_cap):
            adopted = 0
            for src, dev in list(self.devices.items()):
                for blob in dev.outgoing():
                    for dst, payload in self.radio.transmit(src, blob):
                        adopted += self.devices[dst].on_packet(src, payload)
            if adopted == 0:
                break
        return adopted

    def hop_grid(self, sos_id: Any) -> Dict[str, Dict[str, int]]:
        return {str(nid): dev.hop_map(sos_id) for nid, dev in sorted(self.devices.items())}

    def guidance(self, device: Any, sos_id: Any):
        return self.devices[domain.NodeId(str(device))].guidance(sos_id)

    def coverage(self, sos_id: Any) -> float:
        live = [d for d in self.devices.values()
                if d.known_sos(sos_id)]
        if not live:
            return 0.0
        got = sum(1 for d in live
                  if d.sos_engine.hop_of(domain.SosId(str(sos_id)), d.id) is not None)
        return got / len(live)


def _test() -> None:
    from devices import DeviceApp
    w = AppWorld(dt=1.0)
    w.add_device(DeviceApp("T", edge_expire_after=5.0,
                           node_expire_after=10.0), 0.0, 0.0)
    w.add_device(DeviceApp("A", edge_expire_after=5.0,
                           node_expire_after=10.0), 60.0, 0.0)
    w.add_device(DeviceApp("B", edge_expire_after=5.0,
                           node_expire_after=10.0), 120.0, 0.0)
    w.set_sos("T", "SOS-1")
    for _ in range(5):
        w.step()
    grid = w.hop_grid("SOS-1")
    assert grid["T"]["T"] == 0 and grid["A"]["A"] == 1, grid
    assert grid["B"]["B"] == 2, grid
    assert w.coverage("SOS-1") == 1.0
    w.split_off("B")
    for _ in range(12):
        w.step()
    assert w.devices["B"].guidance("SOS-1").mode == "NO_VALID_ROUTE"
    print("world selftest: PASSED")


if __name__ == "__main__":
    _test()