"""AUTOSAR CAN NM 송신 — 네트워크를 깨우고 깨어 있게 한다 (제품 무관).

한 노드분의 NM 메시지를 주기 전송한다. CANoe 의 AsrNm 이 하던 일 중
"깨우고 유지하기"만 한다. 멈추면 상대 ECU는 NM 타임아웃 뒤 잠든다.

    >>> nm = AsrNm(dbc, "CGW_CCU")
    >>> nm.start(bus)          # bus 는 CanBase
    >>> nm.stop(bus)

DBC에서 가져오는 값
    ID      그 노드가 보내는 NM 메시지. 없으면 NmAsrBaseAddress + NmAsrNodeIdentifier
    주기    NmAsrCanMsgCycleTime (기본 100ms)
    노드 ID NmAsrNodeIdentifier

NM 메시지 구성 (AUTOSAR 기본 배치)
    바이트 0   노드 ID
    바이트 1   제어 비트(CBV) — 능동 깨움(AWB, 0x10), 부분 네트워크 정보(PNI, 0x40)
    나머지     0. 부분 네트워크 비트는 DBC의 PNI 신호 위치부터

부분 네트워크(pn)
    "none"  PNI 비트 0, 부분 네트워크 정보 없음 = 전체 네트워크를 깨운다 (기본)
    "all"   PNI 비트 1, 부분 네트워크 비트 전부 1 = 모든 부분 네트워크를 요청한다
    제어기가 부분 네트워크를 쓰는데 "none" 으로 깨지 않으면 "all" 로 바꿔 본다.
    DBC 의 NM 메시지에 PN 비트가 있어도 제어기가 쓰지 않을 수 있다 — 그러면 이 값은
    동작에 영향이 없다. 제어기가 보내는 NM 에 PN 비트가 켜져 있다고 쓰는 것은 아니다.
"""

from __future__ import annotations

import can

from CanDbc import CanDbc
from CanErrors import CanConfigError
from can_log import CanLogger

__all__ = ["AsrNm"]

log = CanLogger.get("CanNm")


class AsrNm:
    """AUTOSAR CAN NM 한 노드분."""

    CBV_AWB = 0x10  #: Active Wakeup Bit
    CBV_PNI = 0x40  #: Partial Network Information Bit
    PN_MODES = ("none", "all")

    def __init__(
        self,
        dbc: CanDbc,
        node: str,
        *,
        pn: str = "none",
        active_wakeup: bool = True,
        brs: bool = True,
    ) -> None:
        if pn not in self.PN_MODES:
            raise CanConfigError(f"pn 은 {self.PN_MODES} 중 하나여야 합니다: {pn!r}")
        self.dbc = dbc
        self.node = node
        self.pn = pn
        self.active_wakeup = active_wakeup

        node_id = dbc.node_attribute(node, "NmAsrNodeIdentifier")
        cycle = dbc.attribute("NmAsrCanMsgCycleTime") or 100
        self.cycle_s = float(cycle) / 1000

        nm_msgs = dbc.tx_of(node, kinds=["nm"])
        if nm_msgs:
            spec = nm_msgs[0]
            self.frame_id, self.extended = spec.frame_id, spec.extended
            self.length, self.is_fd = spec.length, spec.is_fd
            self.name = spec.name
            self._pn_offset = self._find_pn_offset(spec.name)
            if node_id is None:
                node_id = spec.frame_id & 0xFF
        else:
            base = dbc.attribute("NmAsrBaseAddress")
            if base is None or node_id is None:
                raise CanConfigError(
                    f"{dbc.name}: {node} 의 NM 메시지도, NmAsrBaseAddress/NmAsrNodeIdentifier 도 없습니다."
                )
            self.frame_id, self.extended = int(base) + int(node_id), True
            self.length, self.is_fd = 8, False
            self.name = f"NM_{node}"
            self._pn_offset = None

        self.node_id = int(node_id)
        self.brs = brs and self.is_fd
        if pn == "all" and self._pn_offset is None:
            raise CanConfigError(f"{self.name}: DBC에 부분 네트워크(PNI) 신호가 없어 pn='all' 을 쓸 수 없습니다.")

    def _find_pn_offset(self, name: str) -> int | None:
        """DBC에서 PNI 신호가 시작하는 바이트. 없으면 None."""
        starts = [
            self.dbc.signal_layout(name, s).first_byte
            for s in self.dbc.signal_names(name)
            if s.upper().startswith("PNI")
        ]
        return min(starts) if starts else None

    @property
    def key(self) -> str:
        """CanBase 주기 전송 이름."""
        return f"nm:{self.node}"

    def payload(self) -> bytes:
        """NM 메시지 데이터."""
        data = bytearray(self.length)
        data[0] = self.node_id & 0xFF
        cbv = self.CBV_AWB if self.active_wakeup else 0
        if self.pn == "all":
            cbv |= self.CBV_PNI
            for i in range(self._pn_offset, self.length):
                data[i] = 0xFF
        data[1] = cbv
        return bytes(data)

    def message(self) -> can.Message:
        return can.Message(
            arbitration_id=self.frame_id,
            data=self.payload(),
            is_extended_id=self.extended,
            is_fd=self.is_fd,
            bitrate_switch=self.brs,
        )

    def start(self, bus) -> None:
        """주기 전송을 시작한다 — 첫 프레임이 곧 깨움 신호다."""
        bus.send_periodic(self.key, self.message(), self.cycle_s)
        bus.start_periodic(self.key)
        log.info("NM 시작: %s 0x%X 노드ID 0x%02X %dms pn=%s",
                 self.name, self.frame_id, self.node_id, self.cycle_s * 1000, self.pn)

    def stop(self, bus) -> None:
        """주기 전송을 멈춘다. 상대는 NM 타임아웃 뒤 잠든다."""
        bus.stop_periodic(self.key)

    def __repr__(self) -> str:
        return f"<AsrNm {self.name} 0x{self.frame_id:X} id=0x{self.node_id:02X} {self.cycle_s * 1000:.0f}ms pn={self.pn}>"
