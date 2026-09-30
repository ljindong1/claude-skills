"""E2E 보호 — 메시지에 카운터와 CRC 를 넣고, 받은 메시지의 CRC 를 확인한다.

계산식은 OEM마다 다르고 DBC에는 없다. 그래서 "방식(프로파일)" 단위로 만들고,
쓰는 쪽이 고른다. 지금은 :class:`HkmcE2E` 하나가 있다.

    >>> e2e = HkmcE2E()
    >>> guard = e2e.bind(dbc, spec)            # 이 메시지 전용 보호. 배치가 다르면 None
    >>> guard.protect(data, counter=5)         # data(bytearray)에 카운터·CRC 기록
    >>> guard.verify(data)                     # 받은 데이터의 CRC 가 맞나

프로파일은 상태를 갖지 않는다. 메시지별 배치는 ``bind()`` 가 돌려주는 객체가 들고 있어서
부르는 순서에 기댈 것이 없고, 한 프로파일을 여러 버스(DBC)에 같이 써도 섞이지 않는다.

새 방식은 :class:`E2EProfile` 을 상속해 ``bind`` 를 만들고, :class:`E2EBinding` 을
상속해 ``protect`` / ``verify`` 와 ``counter_modulus`` 를 채운다. 메서드를 빠뜨리면
객체를 만들 때 TypeError 가 난다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from CanDbc import CanDbc, MessageSpec

__all__ = ["E2EProfile", "E2EBinding", "HkmcE2E", "crc16_ccitt_false", "crc8_1d"]


# ============================================================ CRC 계산
def _table16(poly: int) -> list[int]:
    table = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poly) if crc & 0x8000 else (crc << 1)
        table.append(crc & 0xFFFF)
    return table


def _table8(poly: int) -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = ((crc << 1) ^ poly) if crc & 0x80 else (crc << 1)
        table.append(crc & 0xFF)
    return table


_T16 = _table16(0x1021)
_T8 = _table8(0x1D)


def crc16_ccitt_false(data: bytes) -> int:
    """CRC-16/CCITT-FALSE — 다항식 0x1021, 초기값 0xFFFF, 반사 없음, 최종 XOR 0.

    표준 검사값: ``crc16_ccitt_false(b"123456789") == 0x29B1``
    """
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ _T16[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
    return crc


def crc8_1d(data: bytes) -> int:
    """CRC-8 — 다항식 0x1D, 초기값 0x00, 반사 없음, 최종 XOR 0xFF."""
    crc = 0x00
    for b in data:
        crc = _T8[crc ^ b]
    return crc ^ 0xFF


# ============================================================ 프로파일
class E2EBinding(ABC):
    """메시지 하나에 묶인 E2E 보호. :meth:`E2EProfile.bind` 가 만든다.

    배치(CRC·카운터 위치, ID 바이트 등)는 만들 때 정해져 있어서 부르는 순서나
    다른 DBC 의 메시지와 섞일 일이 없다.
    """

    #: 카운터가 몇에서 한 바퀴 도는가
    counter_modulus: int

    def __init__(self, spec: MessageSpec) -> None:
        self.spec = spec

    @abstractmethod
    def protect(self, data: bytearray, counter: int) -> None:
        """data 에 카운터와 CRC 를 써 넣는다 (제자리 수정)."""

    @abstractmethod
    def verify(self, data: bytes) -> bool:
        """받은 data 의 CRC 가 맞으면 True."""


class E2EProfile(ABC):
    """E2E 방식. 상태를 갖지 않는다 — 한 인스턴스를 여러 버스·DBC 에 같이 써도 된다."""

    name = "base"

    @abstractmethod
    def bind(self, dbc: CanDbc, spec: MessageSpec) -> E2EBinding | None:
        """이 메시지 전용 보호를 만든다. 이 방식의 배치가 아니면 None."""

    def applies(self, dbc: CanDbc, spec: MessageSpec) -> bool:
        """이 메시지가 이 방식의 배치를 따르는가."""
        return self.bind(dbc, spec) is not None

    def skip_reason(self, dbc: CanDbc, spec: MessageSpec) -> str | None:
        """이 메시지에 보호를 적용하지 않는 이유 (화면용). 적용하면 None."""
        return None if self.applies(dbc, spec) else "배치가 아님"


class _HkmcBinding(E2EBinding):
    counter_modulus = 256

    def __init__(self, spec: MessageSpec, crc_bits: int, id_bytes: bytes) -> None:
        super().__init__(spec)
        self.crc_bits = crc_bits
        self.id_bytes = id_bytes

    def _crc(self, data: bytes) -> int:
        if self.crc_bits == 16:
            return crc16_ccitt_false(bytes(data[2:]) + self.id_bytes)
        return crc8_1d(self.id_bytes + bytes(data[1:8]))

    def protect(self, data: bytearray, counter: int) -> None:
        if self.crc_bits == 16:
            data[2] = counter & 0xFF
            crc = self._crc(data)
            data[0], data[1] = crc & 0xFF, crc >> 8
        else:
            data[1] = counter & 0xFF
            data[0] = self._crc(data)

    def verify(self, data: bytes) -> bool:
        if len(data) < self.spec.length:
            return False
        if self.crc_bits == 16:
            return data[0] | (data[1] << 8) == self._crc(data)
        return data[0] == self._crc(data)


class HkmcE2E(E2EProfile):
    """현대·기아 CAN FD 방식. SP3i PSU CANoe 컨피그의 CAPL(Crc_Calculate_*.cin)에서 옮겼다.

    CRC16 (CRC 신호 16비트, 0번 비트부터)
        바이트 0-1  CRC (하위 바이트 먼저)
        바이트 2    카운터 (8비트, 보낼 때마다 +1, 255 → 0)
        CRC 계산 대상 = 바이트 2 ~ 끝  +  DataID 하위·상위 바이트

    CRC8 (CRC 신호 8비트, 0번 비트부터) — CAPL에 함수는 있으나 쓰는 곳이 없어 **미검증**
        바이트 0    CRC
        바이트 1    카운터 (8비트)
        CRC 계산 대상 = DataID 하위·상위 바이트  +  바이트 1 ~ 7

    DataID
        표준 ID   CAN ID ^ 0xF800 (하위 16비트)
        확장 ID   ((CAN ID >> 8) & 0x7FF) ^ 0xF800 — ID 의 8~18번 비트

    CAPL과 다른 점: CAPL은 16바이트 메시지(CLU_01_20ms)에도 32바이트용 함수를 불러
    ID 바이트가 계산에서 빠진다. 여기서는 길이에 맞는 계산을 한다 (같은 파일의
    16바이트용 함수와 같은 결과).

    실장비 확인 (2026-09-30, PSU DRV 벤치)
        표준 ID — DUT 자체 메시지 4종(0x3C3, 0x3C4, 0x4AB, 0x519)의 CRC 가 모두 일치.
        확장 ID — 0x1E87AB01 의 서로 다른 프레임 2종에 DataID 를 전부 대입하면 둘 다
        0xFFAB 만 맞는다 (표준 ID 방식이면 0xD832 라 틀린다). 위 공식은 이 값과 같다.
        **확인한 확장 ID 는 이것 하나뿐** 이라 공식 자체는 추정이다. 다른 확장 ID 에서
        "CRC 틀림" 이 나오면 공식을 먼저 의심한다.
    """

    name = "HKMC"
    ID_XOR = 0xF800

    def _layout(self, dbc: CanDbc, spec: MessageSpec) -> int | None:
        """CRC 비트 수(16 또는 8). 배치가 맞지 않으면 None."""
        if not spec.crc_signals or not spec.counter_signals:
            return None
        crc_sig = dbc.signal_layout(spec.name, spec.crc_signals[0])
        cnt_sig = dbc.signal_layout(spec.name, spec.counter_signals[0])
        if not (crc_sig.little_endian and cnt_sig.little_endian):
            return None  # 이 프로파일은 인텔 배치만 쓴다
        crc = (crc_sig.lsb, crc_sig.length)
        cnt = (cnt_sig.lsb, cnt_sig.length)
        if crc == (0, 16) and cnt == (16, 8):
            return 16
        if crc == (0, 8) and cnt == (8, 8) and spec.length == 8:
            return 8
        return None

    def data_id(self, spec: MessageSpec) -> int:
        """CRC 뒤에 붙이는 16비트 DataID. 클래스 설명의 표 참고."""
        if spec.extended:
            return ((spec.frame_id >> 8) & 0x7FF) ^ self.ID_XOR
        return (spec.frame_id ^ self.ID_XOR) & 0xFFFF

    def _id_bytes(self, spec: MessageSpec) -> bytes:
        v = self.data_id(spec)
        return bytes((v & 0xFF, v >> 8))

    def bind(self, dbc: CanDbc, spec: MessageSpec) -> E2EBinding | None:
        bits = self._layout(dbc, spec)
        return None if bits is None else _HkmcBinding(spec, bits, self._id_bytes(spec))
