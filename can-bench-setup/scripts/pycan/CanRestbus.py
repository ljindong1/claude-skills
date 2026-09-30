"""레스트버스 — 지정한 ECU들인 척 DBC대로 주기 송신한다 (제품 무관).

CANoe 의 IL(자동 송신) + AsrNm + CRC 용 CAPL 이 하던 일을 한다.
시험 대상(DUT) 하나만 실물이고, 나머지 ECU는 이것이 흉내 낸다.

    >>> print(CanRestbus.candidates(dbc, "GW_PSU_DRV_FD"))   # 흉내 낼 후보
    >>> rb = CanRestbus(bus, dbc, "all", dut="GW_PSU_DRV_FD",
    ...                 exclude=["L_PSS_DRV_FD"], e2e=HkmcE2E())  # 실물이 있는 ECU는 뺀다
    >>> rb.set("BDC_FD_02_200ms", BCM_Ign1InSta=1)          # IGN ON
    >>> rb.start()
    >>> rb.stop()

보내는 것
    * 기본은 DUT에게 보내는 ECU **전부** ("all"). 실험대에 실물이 있는 ECU는 exclude 로 뺀다
    * 그 ECU들이 보내는 **주기 메시지 중 DUT가 받는 것만** (dut 를 주지 않으면 전부)
    * 고른 ECU의 NM 메시지 (nm=True, DBC에 NM 정보가 있을 때)
    * 이벤트 메시지는 자동으로 보내지 않는다 — :meth:`CanRestbus.send_event`

신호 값
    처음에는 DBC 초기값(GenSigStartValue). :meth:`CanRestbus.set` 으로 바꾸면
    다음 송신부터 반영된다.

E2E
    e2e 를 주면, 그 방식의 배치를 따르는 메시지 **전부**에 카운터와 CRC 를 넣는다.
    배치가 다른 메시지는 CRC 를 만들 수 없어 DBC 초기값 그대로 나간다. 다만 카운터
    칸이 있으면 카운터는 올린다 — 멈춘 카운터로 DUT가 수신 오류를 내지 않게.
    어느 쪽인지는 시작할 때 경고와 :meth:`CanRestbus.summary` 에 나온다.

주의 — 주기 정확도
    송신 타이밍은 PC(파이썬 스레드)가 잡는다. 수 ms 흔들릴 수 있다.
    깨우기·유지에는 충분하지만, 주기 정밀도 자체를 시험하는 용도는 아니다.
"""

from __future__ import annotations

import threading
from typing import Any, Iterable

import can

from CanDbc import CanDbc, MessageSpec
from CanE2E import E2EBinding, E2EProfile
from CanErrors import CanConfigError, CanDbcError
from CanNm import AsrNm
from can_log import CanLogger

__all__ = ["CanRestbus"]

log = CanLogger.get("CanRestbus")


class CanRestbus:
    """지정한 ECU들을 흉내 내는 송신기. bus 는 연결된 CanBase."""

    def __init__(
        self,
        bus: Any,
        dbc: CanDbc,
        nodes: Iterable[str] | str = "all",
        *,
        dut: str | None = None,
        exclude: Iterable[str] = (),
        e2e: E2EProfile | None = None,
        nm: bool = True,
        pn: str = "none",
        brs: bool = True,
    ) -> None:
        """
        nodes    흉내 낼 ECU 목록. "all" 이면 DUT에게 주기 메시지를 보내는 ECU 전부
                 (:meth:`candidates`) — dut 가 필요하다.
        exclude  빼는 ECU. 실험대에 실물이 붙어 있는 ECU를 여기에 넣는다
                 (같은 ID를 양쪽에서 보내면 충돌한다).
        """
        self.bus = bus
        self.dbc = dbc
        self.dut = dut
        self.e2e = e2e
        self.brs = brs

        exclude = tuple(exclude)
        for node in exclude:
            if node not in dbc.nodes:
                raise CanDbcError(f"{dbc.name}: exclude 의 '{node}' 노드가 없습니다.")
        if isinstance(nodes, str):
            if nodes != "all":
                raise CanConfigError(f"nodes 는 ECU 이름 목록이거나 \"all\" 이어야 합니다: {nodes!r}")
            if dut is None:
                raise CanConfigError('nodes="all" 은 dut 가 있어야 합니다 (누구에게 보내는지 알아야 한다).')
            nodes = [node for node, _ in self.candidates(dbc, dut)]
        self.nodes = tuple(n for n in nodes if n not in exclude)
        self.excluded = exclude
        if not self.nodes:
            raise CanConfigError("흉내 낼 ECU가 없습니다. CanRestbus.candidates() 참고.")
        if dut is not None and dut in self.nodes:
            raise CanConfigError(f"시험 대상 {dut} 를 흉내 낼 수는 없습니다.")

        specs: dict[str, MessageSpec] = {}
        for node in self.nodes:
            for spec in dbc.tx_of(node, kinds=["app"]):  # 노드 이름 검증도 여기서
                if spec.is_cyclic and (dut is None or dut in spec.receivers):
                    specs[spec.name] = spec
        self._specs = specs

        self._lock = threading.Lock()
        self._values = {name: dbc.initial_values(name) for name in specs}
        self._counter = {name: 0 for name in specs}
        #: 카운터·CRC 를 넣는 메시지 → 그 메시지 전용 E2E 보호
        self._protected: dict[str, E2EBinding] = {}
        if e2e:
            for name, spec in specs.items():
                guard = e2e.bind(dbc, spec)
                if guard is not None:
                    self._protected[name] = guard
        self._running: set[str] = set()

        self._nm: list[AsrNm] = []
        if nm:
            for node in self.nodes:
                try:
                    self._nm.append(AsrNm(dbc, node, pn=pn, brs=brs))
                except CanConfigError as exc:
                    log.warning("NM 없이 진행: %s", exc)

        #: E2E 배치는 아니지만 카운터 칸이 있는 메시지 → (카운터 신호, 한 바퀴). 카운터만 올린다
        self._count_only: dict[str, tuple[str, int]] = {}
        unprotected = [n for n, s in specs.items() if s.crc_signals and n not in self._protected]
        if e2e:
            for spec in specs.values():
                self._count_only_of(spec)
            if unprotected:
                log.warning("CRC 칸이 있으나 %s 배치가 아니라 CRC 없이 보냄: %s", e2e.name, unprotected)
            if self._count_only:
                log.warning("%s 배치가 아니라 카운터만 올리고 CRC 는 없이 보냄: %s",
                            e2e.name, sorted(self._count_only))

    # ============================================================ 후보
    @staticmethod
    def candidates(dbc: CanDbc, dut: str) -> list[tuple[str, int]]:
        """DUT가 받는 주기 메시지를 보내는 ECU와 그 개수. 많은 순."""
        counts: dict[str, int] = {}
        for spec in dbc.rx_of(dut, kinds=["app"]):
            if spec.is_cyclic:
                for node in spec.senders:
                    counts[node] = counts.get(node, 0) + 1
        return sorted(counts.items(), key=lambda kv: -kv[1])

    # ============================================================ 조회
    @property
    def messages(self) -> tuple[MessageSpec, ...]:
        """보낼 주기 메시지."""
        return tuple(self._specs.values())

    @property
    def nm(self) -> tuple[AsrNm, ...]:
        return tuple(self._nm)

    def _count_only_of(self, spec: MessageSpec) -> tuple[str, int] | None:
        """E2E 배치가 아닌데 카운터 칸이 있으면 (신호, 한 바퀴). 아니면 None."""
        if not self.e2e or not spec.counter_signals or self.e2e.applies(self.dbc, spec):
            return None
        if spec.name not in self._count_only:
            signal = spec.counter_signals[0]
            self._count_only[spec.name] = (signal, 1 << self.dbc.signal_bits(spec.name, signal))
        return self._count_only[spec.name]

    def _bump(self, name: str, modulus: int) -> int:
        """카운터를 하나 올려 돌려준다. _lock 을 잡고 부른다."""
        self._counter[name] = (self._counter.get(name, 0) + 1) % modulus
        return self._counter[name]

    @property
    def protected(self) -> frozenset[str]:
        """카운터·CRC 를 넣는 메시지 이름."""
        return frozenset(self._protected)

    def get(self, name: str) -> dict[str, Any]:
        """지금 보내고 있는 신호 값."""
        self._require(name)
        with self._lock:
            return dict(self._values[name])

    def _require(self, name: str) -> MessageSpec:
        try:
            return self._specs[name]
        except KeyError:
            raise CanDbcError(
                f"'{name}' 은 이 레스트버스가 보내는 메시지가 아닙니다 "
                f"(흉내 내는 ECU: {', '.join(self.nodes)})."
            ) from None

    # ============================================================ 값 바꾸기
    def set(self, name: str, **signals: Any) -> None:
        """신호 값을 바꾼다. 다음 송신부터 반영된다."""
        self._require(name)
        unknown = set(signals) - set(self._values[name])
        if unknown:
            raise CanDbcError(f"{name}: 없는 신호 {sorted(unknown)}")
        self.dbc.encode(name, {**self._values[name], **signals})  # 범위 검사 — 틀리면 여기서 예외
        with self._lock:
            self._values[name].update(signals)

    # ============================================================ 송신
    def _data(self, spec: MessageSpec) -> bytes:
        """현재 값으로 데이터를 만들고, 보호 대상이면 카운터를 올려 CRC 를 넣는다."""
        with self._lock:
            values = dict(self._values[spec.name])
            guard = self._protected.get(spec.name)
            if guard is not None:
                self._bump(spec.name, guard.counter_modulus)
            elif spec.name in self._count_only:
                signal, modulus = self._count_only[spec.name]
                values[signal] = self._bump(spec.name, modulus)
            counter = self._counter[spec.name]
        data = bytearray(self.dbc.encode(spec.name, values))
        if guard is not None:
            guard.protect(data, counter)
        return bytes(data)

    def _refresh(self, spec: MessageSpec, msg: can.Message) -> None:
        """주기 전송 스레드가 보내기 직전에 부른다."""
        try:
            msg.data[:] = self._data(spec)
        except Exception:  # 여기서 예외가 새면 그 메시지의 주기 전송이 멈춘다
            log.exception("%s 데이터 갱신 실패 - 직전 값으로 보냄", spec.name)

    def _message(self, spec: MessageSpec) -> can.Message:
        return can.Message(
            arbitration_id=spec.frame_id,
            data=self.dbc.encode(spec.name, self._values[spec.name]),
            is_extended_id=spec.extended,
            is_fd=spec.is_fd,
            bitrate_switch=self.brs and spec.is_fd,
        )

    def _start_one(self, spec: MessageSpec) -> None:
        key = f"rb:{spec.name}"
        self.bus.send_periodic(
            key,
            self._message(spec),
            spec.cycle_ms / 1000,
            modifier_callback=lambda m, s=spec: self._refresh(s, m),
        )
        self.bus.start_periodic(key)
        self._running.add(spec.name)

    def start(self) -> None:
        """NM 을 먼저 시작하고(깨움), 이어서 주기 메시지를 시작한다."""
        for nm in self._nm:
            nm.start(self.bus)
        for spec in self._specs.values():
            if spec.name not in self._running:
                self._start_one(spec)
        log.info("레스트버스 시작: %s - 메시지 %d개 (E2E %d개), NM %d개",
                 ", ".join(self.nodes), len(self._running), len(self._protected), len(self._nm))

    def stop(self) -> None:
        """모두 멈춘다. DUT 는 NM 타임아웃 뒤 잠든다."""
        for name in list(self._running):
            self.pause(name)
        for nm in self._nm:
            nm.stop(self.bus)

    def pause(self, name: str) -> None:
        """메시지 하나만 멈춘다 (수신 타임아웃 시험용). CANoe 의 ILNodeControlMsg 에 해당."""
        self._require(name)
        self.bus.stop_periodic(f"rb:{name}")
        self._running.discard(name)

    def resume(self, name: str) -> None:
        """멈춘 메시지를 다시 보낸다."""
        spec = self._require(name)
        if name not in self._running:
            self._start_one(spec)

    def send_event(self, name: str, **signals: Any) -> can.Message:
        """이벤트 메시지를 한 번 보낸다. 흉내 내는 ECU가 보내는 메시지여야 한다."""
        spec = self.dbc.spec(name)
        if not set(spec.senders) & set(self.nodes):
            raise CanDbcError(f"{name} 은 흉내 내는 ECU({', '.join(self.nodes)})가 보내는 메시지가 아닙니다.")
        count_only = self._count_only_of(spec)
        if count_only:
            signal, modulus = count_only
            with self._lock:
                signals = {**signals, signal: self._bump(name, modulus)}
        data = bytearray(self.dbc.encode(name, signals or None))
        guard = self._protected.get(name) or (self.e2e.bind(self.dbc, spec) if self.e2e else None)
        if guard is not None:
            with self._lock:
                counter = self._bump(name, guard.counter_modulus)
            guard.protect(data, counter)
        msg = can.Message(
            arbitration_id=spec.frame_id,
            data=bytes(data),
            is_extended_id=spec.extended,
            is_fd=spec.is_fd,
            bitrate_switch=self.brs and spec.is_fd,
        )
        return self.bus.send(msg)

    def __enter__(self) -> CanRestbus:
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # ============================================================ 리포트
    def summary(self) -> str:
        lines = [
            f"[{self.dbc.name}]  흉내 내는 ECU: {', '.join(self.nodes)}"
            + (f"  →  대상 {self.dut}" if self.dut else ""),
        ]
        if self.excluded:
            lines.append(f"  뺀 ECU (실물): {', '.join(self.excluded)}")
        for nm in self._nm:
            lines.append(f"  NM   0x{nm.frame_id:08X} {nm.name:<34} {nm.cycle_s * 1000:>5.0f}ms  노드ID 0x{nm.node_id:02X} pn={nm.pn}")
        for spec in sorted(self._specs.values(), key=lambda s: (s.extended, s.frame_id)):
            if spec.name in self._protected:
                e2e = "E2E"
            elif spec.name in self._count_only:
                e2e = "카운터만(CRC 없음)"
            else:
                e2e = "CRC칸(초기값)" if spec.crc_signals else ""
            lines.append(f"  주기 {spec.id_text:<10} {spec.name[:34]:<34} {spec.cycle_ms:>5}ms  {e2e}")
        lines.append(f"  합계: 주기 메시지 {len(self._specs)}개 (E2E {len(self._protected)}개), NM {len(self._nm)}개")
        return "\n".join(lines)
