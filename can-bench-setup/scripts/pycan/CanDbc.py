"""DBC 레이어 — cantools 기반, 제품 무관.

DBC 파일 하나를 읽어 메시지 명세(:class:`MessageSpec`)로 정리하고,
수신 프레임 디코딩과 송신 프레임 인코딩을 제공한다.

제품과 무관하게 쓴다. "어느 ECU 기준으로 볼지"는 호출하는 쪽이 노드 이름으로
정한다.

    >>> dbc = CanDbc.load("FD_B2.dbc")
    >>> tx = dbc.tx_of("GW_PSU_DRV_FD")       # 이 노드가 보내는 메시지
    >>> rx = dbc.rx_of("GW_PSU_DRV_FD")       # 이 노드가 받는 메시지
    >>> print(dbc.summary("GW_PSU_DRV_FD"))

DBC 하나 = 버스 하나다. 버스가 둘이면 CanDbc도 둘을 만든다.

설계 메모
---------
* **조회 키는 (frame_id, extended)** 다. 표준 ``0x123`` 과 확장 ``0x123`` 은 서로
  다른 프레임인데 ``dict[int, ...]`` 로 두면 조용히 덮어쓴다.
* **속성값은 정의까지 따라가 해석한다.** cantools는 열거형 속성을 인덱스(정수)로
  돌려주고, 메시지에 속성이 없으면 아무것도 주지 않는다. 그런데 DBC에서는
  "속성 없음"이 "정의의 기본값"이라는 뜻이다. 둘 다 여기서 풀어 준다.
* **주기 메시지 판정.** 주기 값(GenMsgCycleTime)은 기본값 때문에 이벤트 메시지에도
  숫자가 붙어 있을 수 있다. 송신 유형(GenMsgSendType)이 정의된 DBC에서는
  그 값에 "Cyclic"이 들어 있어야 주기 메시지로 본다.
* **수신 노드는 신호 단위** 로 적혀 있다. DBC 작성자가 받는 쪽을 비워 두는 경우가
  흔해서, :meth:`CanDbc.rx_of` 는 DBC에 적힌 만큼만 안다.
* **멀티플렉스 메시지.** 신호 값은 모든 분기 것을 들고 있어도 된다. 인코딩할 때
  선택자 값에 맞는 분기의 신호만 쓰고 나머지는 버린다 (CANoe IL과 같은 방식).
* **DBC 결함은 막지 않고 알린다.** 초기값이 비트 수를 넘는 등 결함이 있어도 보정해서
  동작한다 (보정한 값은 추정값이라 경고를 남긴다). 결함 목록은 :meth:`CanDbc.validate`
  로 따로 본다 — DB 담당자에게 알려 고치게 하는 용도다.
* **OEM 관례는 클래스 속성과 훅으로 바꾼다.** 종류 판정은 :attr:`CanDbc.KIND_ATTRIBUTES`,
  주기 판정은 ``*_ATTRIBUTE`` 속성, 판정 논리 자체는 ``_classify`` / ``_cycle`` 를
  자식 클래스에서 덮어쓴다.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

import can

from CanErrors import CanDbcError
from can_log import CanLogger

__all__ = ["CanDbc", "MessageSpec", "DecodedFrame", "SignalLayout", "DbcIssue", "KINDS"]

log = CanLogger.get("CanDbc")

#: 기본 메시지 종류. 대조할 때 진단·NM 을 앱 메시지와 섞지 않기 위해 나눈다.
#: 자식 클래스가 :attr:`CanDbc.KIND_ATTRIBUTES` 를 늘리면 :attr:`CanDbc.kinds` 도 늘어난다.
KINDS = ("app", "nm", "diag", "tp")

#: DBC 관례상 "받는 쪽 없음" 자리표시자
_NO_NODE = "Vector__XXX"


def _pad(text: str, width: int, *, right: bool = False) -> str:
    """터미널 표시 폭 기준으로 채운다. 한글은 한 글자가 두 칸이라 ``:<n`` 이 어긋난다."""
    shown = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    fill = " " * max(0, width - shown)
    return fill + text if right else text + fill


def _import_cantools() -> Any:
    """cantools를 지연 임포트한다 — 없는 PC에서도 ``import CanDbc`` 는 성공해야 한다."""
    try:
        import cantools
    except ImportError as exc:
        raise CanDbcError(
            'cantools가 설치되어 있지 않습니다. uv pip install "cantools==42.0.3"'
        ) from exc
    return cantools


@dataclass(frozen=True)
class MessageSpec:
    """DBC 메시지 하나의 명세. 대조의 기준이 된다."""

    name: str
    frame_id: int
    extended: bool
    is_fd: bool
    length: int  #: 바이트
    senders: tuple[str, ...]
    receivers: frozenset[str]  #: 신호별 수신 노드의 합집합
    cycle_ms: int | None  #: 주기 메시지만 값이 있다. 이벤트 메시지는 None
    send_type: str | None
    kind: str  #: :attr:`CanDbc.kinds` 중 하나
    crc_signals: tuple[str, ...]
    counter_signals: tuple[str, ...]

    @property
    def key(self) -> tuple[int, bool]:
        """조회 키 (frame_id, extended)."""
        return (self.frame_id, self.extended)

    @property
    def is_cyclic(self) -> bool:
        """주기 메시지인지 여부."""
        return self.cycle_ms is not None

    @property
    def id_text(self) -> str:
        """표시용 ID. 확장 ID는 8자리, 표준 ID는 3자리."""
        return f"0x{self.frame_id:08X}" if self.extended else f"0x{self.frame_id:03X}"


@dataclass(frozen=True)
class SignalLayout:
    """신호 하나가 데이터 안에서 차지하는 자리.

    비트 번호는 바이트 순서와 무관한 표준 번호다 — ``바이트 * 8 + 바이트 안 비트``
    (바이트 안 비트 0 = 최하위). DBC의 시작 비트는 인텔이면 LSB, 모토로라면 MSB라서
    그대로 비교하면 틀린다. 그래서 여기서는 둘 다 LSB 번호로 맞춰 준다.
    """

    lsb: int  #: 최하위 비트의 번호
    length: int  #: 비트 수
    little_endian: bool  #: 인텔이면 True, 모토로라면 False
    first_byte: int  #: 차지하는 첫 바이트
    last_byte: int  #: 차지하는 마지막 바이트


@dataclass(frozen=True)
class DbcIssue:
    """DBC 결함 하나. :meth:`CanDbc.validate` 가 돌려준다.

    결함이 있어도 CanDbc는 동작한다 (보정하거나 건너뛴다). 이 목록은 DB 담당자에게
    알려 고치게 하려는 것이다.
    """

    code: str  #: 결함 종류 — :attr:`CanDbc.ISSUE_CODES` 중 하나
    message: str | None  #: 메시지 이름. DB 전체에 관한 것이면 None
    signal: str | None  #: 신호 이름. 메시지 단위면 None
    detail: str  #: 사람이 읽는 설명

    def __str__(self) -> str:
        where = ".".join(p for p in (self.message, self.signal) if p) or "<DB>"
        return f"[{self.code}] {where}: {self.detail}"


@dataclass
class DecodedFrame:
    """디코딩 결과.

    ``can.Message`` 는 ``__slots__`` 라 결과를 붙일 수 없어서 따로 감싼다.
    """

    spec: MessageSpec
    signals: dict[str, Any]
    msg: can.Message

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def timestamp(self) -> float:
        return self.msg.timestamp


class CanDbc:
    """DBC 파일 하나를 감싼다.

    CRC·카운터 신호 이름, 종류·주기를 판정하는 속성 이름은 OEM마다 다르므로
    클래스 속성으로 두었다 — 다르면 자식 클래스에서 바꾼다. 판정 논리 자체가
    다르면 :meth:`_classify` / :meth:`_cycle` 를 덮어쓴다.
    """

    #: CRC 신호 이름 패턴 (대소문자 무시). ``_`` 뒤에서 시작해 이름 끝까지 맞아야 한다 —
    #: 그냥 ``crc`` 로 찾으면 ``ENG_CrctEngTqVal``(Correct), ``ccRC_…`` 까지 걸린다.
    #: 예: ``EMS_Crc1Val``, ``GATEWAY_CrcVal``, ``PSUex_DRV_cCrc2Val``, ``X_CRC``.
    #: 앞에 붙는 ``c`` 는 ``Val`` 로 끝날 때만 허용한다 — ``AMP_…_ccRC`` 는 CRC가 아니다.
    CRC_PATTERN: str = r"(?:^|_)(?:c?crc\d*val(?:ue)?|crc\d*)$"
    #: 얼라이브 카운터 신호 이름 패턴 (대소문자 무시). 규칙은 :attr:`CRC_PATTERN` 과 같다.
    #: 예: ``EMS_AlvCnt1Val``, ``VCMS_AliveCounter2Value``, ``X_Alive_Counter``, ``X_MsgCnt``
    COUNTER_PATTERN: str = (
        r"(?:^|_)(?:alv|alive_?)(?:cnt|counter)\d*(?:val(?:ue)?)?$"
        r"|(?:^|_)msg_?(?:cnt|counter)\d*$"
    )

    #: 종류 판정 규칙. 앞에서부터 보고, 나열한 속성 중 하나라도 Yes 면 그 종류다.
    #: 어디에도 안 맞으면 ``"app"``. 종류를 늘리려면 여기에 항목을 더한다.
    KIND_ATTRIBUTES: dict[str, tuple[str, ...]] = {
        "diag": ("DiagRequest", "DiagResponse", "DiagState"),
        "nm": ("NmAsrMessage", "NmMessage"),
        "tp": ("TpMessage",),
    }
    #: 주기(ms) 속성
    CYCLE_TIME_ATTRIBUTE: str = "GenMsgCycleTime"
    #: 송신 유형 속성. DBC에 정의돼 있으면 값이 :attr:`CYCLIC_SEND_TYPE_PATTERN` 에 맞아야 주기 메시지다
    SEND_TYPE_ATTRIBUTE: str = "GenMsgSendType"
    #: 주기 송신 유형 이름 패턴 (대소문자 무시)
    CYCLIC_SEND_TYPE_PATTERN: str = r"cyclic"
    #: 신호 초기값 속성. 신호에 값이 없을 때 정의의 기본값(raw)을 쓴다
    START_VALUE_ATTRIBUTE: str = "GenSigStartValue"
    #: NM 메시지 ID 범위 속성 (DB 전체). ``NmAsrMessage`` 가 빠진 NM 메시지를 ID로 찾는다
    NM_BASE_ATTRIBUTE: str = "NmAsrBaseAddress"
    NM_COUNT_ATTRIBUTE: str = "NmAsrMessageCount"

    def __init__(self, db: Any, *, path: str | None = None) -> None:
        """cantools Database를 받아 명세를 만든다. 파일은 :meth:`load` 로 연다."""
        self._db = db
        self.path = path
        self._defs = db.dbc.attribute_definitions if db.dbc else {}
        self._crc_re = re.compile(self.CRC_PATTERN, re.IGNORECASE)
        self._cnt_re = re.compile(self.COUNTER_PATTERN, re.IGNORECASE)
        self._cyclic_re = re.compile(self.CYCLIC_SEND_TYPE_PATTERN, re.IGNORECASE)
        self._nm_range = self._nm_id_range()
        self._initials: dict[tuple[int, bool], dict[str, Any]] = {}  #: key → 초기값 (처음 쓸 때 만든다)

        self._specs: list[MessageSpec] = []
        self._by_key: dict[tuple[int, bool], MessageSpec] = {}
        self._by_name: dict[str, MessageSpec] = {}
        self._cmsg: dict[tuple[int, bool], Any] = {}  #: key → cantools Message
        self._load_issues: list[DbcIssue] = []  #: 읽으면서 건너뛴 것 (validate 가 함께 보고)

        for cmsg in db.messages:
            spec = self._make_spec(cmsg)
            # 같은 키나 이름이 두 번이면 DBC 자체가 잘못된 것이다. 나중 것이 이기면
            # 어느 쪽으로 대조했는지 알 수 없게 되므로 먼저 것을 둔다.
            dup = self._by_key.get(spec.key) or self._by_name.get(spec.name)
            if dup is not None:
                code = "duplicate_id" if dup.key == spec.key else "duplicate_name"
                detail = f"{spec.id_text} - 먼저 나온 {dup.name}({dup.id_text})만 쓰고 이것은 무시합니다"
                log.warning("%s %s: %s", code, spec.name, detail)
                self._load_issues.append(DbcIssue(code, spec.name, None, detail))
                continue
            self._specs.append(spec)
            self._by_key[spec.key] = spec
            self._by_name[spec.name] = spec
            self._cmsg[spec.key] = cmsg

    # ============================================================ 생성
    @classmethod
    def load(cls, path: str, *, strict: bool = True) -> CanDbc:
        """DBC 파일을 연다.

        strict=True 면 신호가 서로 겹치는 등 DBC 결함을 오류로 본다. OEM DBC가
        이 검사에 걸리면 strict=False 로 다시 연다 — 대신 겹친 신호의 디코딩 값은
        믿을 수 없다.
        """
        if not os.path.isfile(path):
            raise CanDbcError(f"DBC 파일이 없습니다: {path}")
        cantools = _import_cantools()
        try:
            db = cantools.database.load_file(path, database_format="dbc", strict=strict)
        except Exception as exc:
            hint = " strict=False 로 다시 열어 보세요." if strict else ""
            raise CanDbcError(f"DBC를 읽지 못했습니다: {path} | {exc}.{hint}") from exc
        dbc = cls(db, path=path)
        log.info("DBC 로드: %s (메시지 %d개, 노드 %d개)", dbc.name, len(dbc), len(dbc.nodes))
        return dbc

    @classmethod
    def from_string(cls, text: str, *, strict: bool = True) -> CanDbc:
        """DBC 문자열로 만든다 (테스트용)."""
        cantools = _import_cantools()
        try:
            db = cantools.database.load_string(text, database_format="dbc", strict=strict)
        except Exception as exc:
            raise CanDbcError(f"DBC 문자열을 읽지 못했습니다: {exc}") from exc
        return cls(db)

    # ============================================================ 속성 해석
    def _resolve(self, attrs: Mapping[str, Any] | None, name: str) -> Any:
        """속성값을 해석한다 — 없으면 정의의 기본값, 열거형이면 라벨."""
        definition = self._defs.get(name)
        attr = attrs.get(name) if attrs else None
        if attr is None:
            value = definition.default_value if definition is not None else None
        else:
            value = attr.value
        choices = getattr(definition, "choices", None)
        if choices and isinstance(value, int) and 0 <= value < len(choices):
            value = choices[value]
        return value

    def attribute(self, name: str) -> Any:
        """DB 전체 속성값 (예: ``DBName``, ``VersionNumber``)."""
        return self._resolve(self._db.dbc.attributes if self._db.dbc else None, name)

    def message_attribute(self, message: str, name: str) -> Any:
        """메시지 속성값 (예: ``GenMsgCycleTime``). OEM 전용 속성도 이걸로 읽는다."""
        cmsg = self._cmsg[self.spec(message).key]
        return self._resolve(cmsg.dbc.attributes if cmsg.dbc else None, name)

    def _nm_id_range(self) -> range | None:
        """NM 메시지 ID 범위 (base, base + 개수). DB에 base 속성이 없으면 None."""
        base = self.attribute(self.NM_BASE_ATTRIBUTE)
        if not isinstance(base, int) or base <= 0:
            return None
        count = self.attribute(self.NM_COUNT_ATTRIBUTE)
        return range(base, base + (count if isinstance(count, int) and count > 0 else 256))

    # ------------------------------------------------ 판정 훅 (자식 클래스에서 덮어쓴다)
    def _classify(self, attr: Callable[[str], Any], cmsg: Any) -> str:
        """메시지 종류.

        ``attr(이름)`` 은 해석된 메시지 속성값을, ``cmsg`` 는 cantools 메시지를 준다
        (신호 속성·ID로 판정할 때 쓴다). 속성으로 정해지지 않으면 ID가 NM 범위
        (:attr:`NM_BASE_ATTRIBUTE`) 안일 때 ``"nm"`` 이다 — DBC 작성자가
        ``NmAsrMessage`` 를 빠뜨린 NM 메시지가 실제로 있다.
        """

        def yes(name: str) -> bool:
            return str(attr(name)).lower() in ("yes", "1", "true")

        for kind, names in self.KIND_ATTRIBUTES.items():
            if any(yes(n) for n in names):
                return kind
        if self._nm_range is not None and cmsg.frame_id in self._nm_range:
            return "nm"
        return "app"

    def _cycle(self, attr: Callable[[str], Any], cmsg: Any) -> int | None:
        """주기(ms). 주기 메시지가 아니면 None."""
        cycle = attr(self.CYCLE_TIME_ATTRIBUTE)
        cycle = int(cycle) if isinstance(cycle, (int, float)) and cycle > 0 else None
        send_type = attr(self.SEND_TYPE_ATTRIBUTE)
        if send_type is not None and not self._cyclic_re.search(str(send_type)):
            return None
        return cycle

    @property
    def kinds(self) -> tuple[str, ...]:
        """이 DBC에서 쓸 수 있는 메시지 종류."""
        return ("app", *self.KIND_ATTRIBUTES)

    def _make_spec(self, cmsg: Any) -> MessageSpec:
        attrs = cmsg.dbc.attributes if cmsg.dbc else None

        def attr(name: str) -> Any:
            return self._resolve(attrs, name)

        send_type = attr(self.SEND_TYPE_ATTRIBUTE)
        cycle = self._cycle(attr, cmsg)
        kind = self._classify(attr, cmsg)
        if kind not in self.kinds:
            raise CanDbcError(f"{cmsg.name}: 알 수 없는 종류 '{kind}'. 가능한 값: {self.kinds}")

        receivers = frozenset(
            r for sig in cmsg.signals for r in (sig.receivers or []) if r != _NO_NODE
        )
        names = [sig.name for sig in cmsg.signals]
        return MessageSpec(
            name=cmsg.name,
            frame_id=cmsg.frame_id,
            extended=bool(cmsg.is_extended_frame),
            is_fd=bool(cmsg.is_fd),
            length=cmsg.length,
            senders=tuple(s for s in cmsg.senders if s != _NO_NODE),
            receivers=receivers,
            cycle_ms=cycle,
            send_type=None if send_type is None else str(send_type),
            kind=kind,
            crc_signals=tuple(n for n in names if self._crc_re.search(n)),
            counter_signals=tuple(n for n in names if self._cnt_re.search(n)),
        )

    # ============================================================ 조회
    @property
    def name(self) -> str:
        """DB 이름. DBName 속성이 없으면 파일 이름."""
        name = self.attribute("DBName")
        if name:
            return str(name)
        return os.path.splitext(os.path.basename(self.path))[0] if self.path else "<dbc>"

    @property
    def nodes(self) -> tuple[str, ...]:
        """DBC에 선언된 노드 이름."""
        return tuple(n.name for n in self._db.nodes)

    @property
    def specs(self) -> tuple[MessageSpec, ...]:
        """모든 메시지 명세."""
        return tuple(self._specs)

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, key: object) -> bool:
        return key in self._by_key or key in self._by_name

    def spec(self, name: str) -> MessageSpec:
        """이름으로 명세를 찾는다. 없으면 :class:`CanDbcError`."""
        try:
            return self._by_name[name]
        except KeyError:
            raise CanDbcError(f"{self.name}: '{name}' 메시지가 없습니다.") from None

    def lookup(self, frame_id: int, extended: bool = False) -> MessageSpec | None:
        """(frame_id, extended)로 명세를 찾는다. 없으면 None."""
        return self._by_key.get((frame_id, extended))

    def _check_node(self, node: str) -> None:
        if node not in self.nodes:
            raise CanDbcError(
                f"{self.name}: '{node}' 노드가 없습니다. 있는 노드: {', '.join(self.nodes)}"
            )

    def _kind_filter(self, specs: Iterable[MessageSpec], kinds: Iterable[str] | None) -> list[MessageSpec]:
        if kinds is None:
            return list(specs)
        wanted = set(kinds)
        unknown = wanted - set(self.kinds)
        if unknown:
            raise CanDbcError(f"알 수 없는 종류: {sorted(unknown)}. 가능한 값: {self.kinds}")
        return [s for s in specs if s.kind in wanted]

    def tx_of(self, node: str, kinds: Iterable[str] | None = None) -> list[MessageSpec]:
        """node 가 보내는 메시지."""
        self._check_node(node)
        return self._kind_filter((s for s in self._specs if node in s.senders), kinds)

    def rx_of(self, node: str, kinds: Iterable[str] | None = None) -> list[MessageSpec]:
        """node 가 받는 메시지 — DBC 신호에 수신 노드로 적힌 것만."""
        self._check_node(node)
        return self._kind_filter(
            (s for s in self._specs if node in s.receivers and node not in s.senders), kinds
        )

    # ============================================================ 디코드 / 인코드
    def decode(self, msg: can.Message, *, strict: bool = False) -> DecodedFrame | None:
        """수신 프레임을 신호 값으로 푼다.

        DBC에 없는 프레임, 에러 프레임, 리모트 프레임은 None.
        디코딩 실패는 strict=False 면 None, True 면 :class:`CanDbcError`.
        """
        if msg.is_error_frame or msg.is_remote_frame:
            return None
        key = (msg.arbitration_id, bool(msg.is_extended_id))
        spec = self._by_key.get(key)
        if spec is None:
            return None
        try:
            signals = self._cmsg[key].decode(bytes(msg.data), allow_truncated=not strict)
        except Exception as exc:
            if strict:
                raise CanDbcError(
                    f"{self.name}: {spec.name}({spec.id_text}) 디코딩 실패 "
                    f"(len={len(msg.data)}, DBC={spec.length}): {exc}"
                ) from exc
            log.debug("디코딩 실패 %s: %s", spec.name, exc)
            return None
        return DecodedFrame(spec=spec, signals=dict(signals), msg=msg)

    def decode_bytes(self, name: str, data: bytes, *, raw: bool = False) -> dict[str, Any] | None:
        """이름으로 지정한 메시지의 데이터를 푼다. 실패하면 None (잘린 프레임은 있는 신호만).

        raw=True 면 배율·값 테이블을 적용하지 않은 정수를 준다 (카운터 비교용).
        """
        try:
            return dict(
                self._cmsg[self.spec(name).key].decode(
                    bytes(data), decode_choices=not raw, scaling=not raw, allow_truncated=True
                )
            )
        except CanDbcError:
            raise
        except Exception as exc:
            log.debug("디코딩 실패 %s: %s", name, exc)
            return None

    def _signal(self, name: str, signal: str) -> Any:
        for sig in self._cmsg[self.spec(name).key].signals:
            if sig.name == signal:
                return sig
        raise CanDbcError(f"{name}: '{signal}' 신호가 없습니다.")

    def signal_names(self, name: str) -> tuple[str, ...]:
        """메시지의 신호 이름들."""
        return tuple(sig.name for sig in self._cmsg[self.spec(name).key].signals)

    def signal_bits(self, name: str, signal: str) -> int:
        """신호의 비트 수. 카운터가 몇에서 한 바퀴 도는지 알 때 쓴다."""
        return self._signal(name, signal).length

    def signal_layout(self, name: str, signal: str) -> SignalLayout:
        """신호의 자리 — LSB 비트 번호, 비트 수, 바이트 순서, 차지하는 바이트 범위."""
        sig = self._signal(name, signal)
        if sig.byte_order == "little_endian":
            lsb = sig.start
            first, last = lsb // 8, (lsb + sig.length - 1) // 8
            return SignalLayout(lsb, sig.length, True, first, last)
        # 모토로라: 시작 비트는 MSB. 비트를 따라 내려가면 바이트 안에서 7→0 으로 가다
        # 다음 바이트의 7로 넘어간다. 그 순서대로 매긴 일련번호로 LSB 를 찾는다.
        msb_seq = (sig.start // 8) * 8 + (7 - sig.start % 8)
        lsb_seq = msb_seq + sig.length - 1
        lsb = (lsb_seq // 8) * 8 + (7 - lsb_seq % 8)
        return SignalLayout(lsb, sig.length, False, sig.start // 8, lsb_seq // 8)

    def node_attribute(self, node: str, name: str) -> Any:
        """노드 속성값 (예: ``NmAsrNodeIdentifier``)."""
        self._check_node(node)
        n = next(n for n in self._db.nodes if n.name == node)
        return self._resolve(n.dbc.attributes if n.dbc else None, name)

    @staticmethod
    def _raw_range(sig: Any) -> tuple[int, int] | None:
        """신호 비트 수로 담을 수 있는 raw 범위. float 신호는 None."""
        if sig.is_float:
            return None
        if sig.is_signed:
            return -(1 << (sig.length - 1)), (1 << (sig.length - 1)) - 1
        return 0, (1 << sig.length) - 1

    def _start_raw(self, sig: Any) -> Any:
        """DBC에 적힌 초기값의 raw. 신호에 없으면 속성 정의의 기본값(정의도 없으면 0)."""
        value = sig.initial
        if value is None:
            definition = self._defs.get(self.START_VALUE_ATTRIBUTE)
            raw = definition.default_value if definition is not None else 0
            return raw if isinstance(raw, (int, float)) else 0
        if isinstance(value, (int, float)):
            return round(sig.scaled_to_raw(value))
        return value.value  # 값 테이블 라벨(NamedSignalValue) — raw 를 들고 있다

    def _initial(self, message: str, sig: Any) -> Any:
        """신호 하나의 초기값(물리값).

        신호에 GenSigStartValue 가 없으면 속성 정의의 기본값(raw, 정의도 없으면 0)을
        물리값으로 바꿔 쓴다. 오프셋이 있으면 raw 0 이 물리값 0 이 아니고, 그 값이
        [min, max] 밖일 수 있어서 범위 안으로 당긴다 — 안 그러면 인코딩이 거부된다.

        raw 값이 신호 비트 수에 들어가지 않으면(예: 4비트 신호에 21) 비트 범위로
        당기고 경고를 남긴다. DBC 결함이다 — 그대로 두면 메시지 전체를 못 만들어서
        보내기는 하지만, 당긴 값은 DB 작성자의 뜻이라는 근거가 없는 **추정값** 이다.
        결함 목록은 :meth:`validate` 로 본다.
        """
        value = sig.initial
        raw = self._start_raw(sig)
        bounds = self._raw_range(sig)
        if bounds is not None and not bounds[0] <= raw <= bounds[1]:
            fixed = min(max(raw, bounds[0]), bounds[1])
            log.warning(
                "%s.%s: 초기값 raw %s 가 %d비트 범위 [%d, %d] 밖 - 추정값 %d 로 보냅니다 (DBC 결함)",
                message, sig.name, raw, sig.length, bounds[0], bounds[1], fixed,
            )
            raw, value = fixed, None

        if value is not None:
            return value
        value = sig.raw_to_scaled(raw, decode_choices=False)
        if sig.minimum is not None and value < sig.minimum:
            value = sig.minimum
        if sig.maximum is not None and value > sig.maximum:
            value = sig.maximum
        return value

    def initial_values(self, name: str) -> dict[str, Any]:
        """메시지의 신호 초기값 (물리값). 멀티플렉스 메시지는 모든 분기의 신호가 들어 있다.

        메시지마다 처음 한 번만 계산한다 (초기값 경고도 한 번만 나온다). 돌려주는 dict 는
        복사본이라 고쳐도 된다.
        """
        key = self.spec(name).key
        if key not in self._initials:
            self._initials[key] = {sig.name: self._initial(name, sig) for sig in self._cmsg[key].signals}
        return dict(self._initials[key])

    def encode(self, name: str, signals: Mapping[str, Any] | None = None) -> bytes:
        """신호 값을 바이트로 만든다. 주지 않은 신호는 초기값을 쓴다.

        멀티플렉스 메시지는 선택자 값에 맞는 분기의 신호만 쓰고, 다른 분기의
        신호 값은 무시한다. 선택자를 바꾸려면 선택자 신호도 같이 준다.
        """
        cmsg = self._cmsg[self.spec(name).key]
        values = self.initial_values(name)
        if signals:
            unknown = set(signals) - set(values)
            if unknown:
                raise CanDbcError(f"{name}: 없는 신호 {sorted(unknown)}")
            values.update(signals)
        try:
            if cmsg.is_multiplexed():
                values = cmsg.gather_signals(values)
            return cmsg.encode(values)
        except Exception as exc:
            raise CanDbcError(f"{name} 인코딩 실패: {exc}") from exc

    def build(
        self,
        name: str,
        signals: Mapping[str, Any] | None = None,
        *,
        brs: bool = True,
    ) -> can.Message:
        """전송용 ``can.Message`` 를 만든다.

        DBC에는 BRS 정보가 없으므로 인자로 받는다 (FD 메시지에만 적용).
        """
        spec = self.spec(name)
        return can.Message(
            arbitration_id=spec.frame_id,
            data=self.encode(name, signals),
            is_extended_id=spec.extended,
            is_fd=spec.is_fd,
            bitrate_switch=brs and spec.is_fd,
        )

    # ============================================================ 검증
    #: 결함 종류와 설명 (보고서 순서이기도 하다)
    ISSUE_CODES: dict[str, str] = {
        "duplicate_id": "프레임 ID가 겹침 - 뒤의 메시지를 무시함",
        "duplicate_name": "메시지 이름이 겹침 - 뒤의 메시지를 무시함",
        "start_value_bits": "초기값이 신호 비트 수에 안 들어감 - 추정값으로 보냄",
        "start_value_range": "초기값이 신호 [min, max] 밖",
        "nm_attribute": "NM 메시지인데 NM 속성이 없음 - ID 범위로 NM 으로 봄",
        "e2e_incomplete": "CRC와 카운터 중 하나만 있음",
        "no_receiver": "수신 노드가 적혀 있지 않음 - rx_of 에 안 나옴",
    }

    def validate(self) -> list[DbcIssue]:
        """DBC 결함 목록. 결함이 있어도 CanDbc는 동작한다 — DB 담당자에게 알리는 용도다.

        cantools가 strict 로드에서 잡는 결함(신호 겹침 등)은 여기 없다 — 그건 로드가 실패한다.
        """
        issues = list(self._load_issues)
        nm_attrs = self.KIND_ATTRIBUTES.get("nm", ())
        for spec in self._specs:
            cmsg = self._cmsg[spec.key]
            for sig in cmsg.signals:
                issues.extend(self._check_start_value(spec.name, sig))

            if spec.kind == "nm" and nm_attrs:
                attrs = cmsg.dbc.attributes if cmsg.dbc else None
                if not any(str(self._resolve(attrs, n)).lower() in ("yes", "1", "true") for n in nm_attrs):
                    issues.append(DbcIssue(
                        "nm_attribute", spec.name, None,
                        f"{spec.id_text} 가 NM 범위 안인데 {'/'.join(nm_attrs)} 가 Yes 가 아닙니다",
                    ))
            if bool(spec.crc_signals) != bool(spec.counter_signals):
                have = "CRC " + ", ".join(spec.crc_signals) if spec.crc_signals else "카운터 " + ", ".join(spec.counter_signals)
                issues.append(DbcIssue("e2e_incomplete", spec.name, None, f"{have} 만 있습니다"))
            if not spec.receivers:
                issues.append(DbcIssue("no_receiver", spec.name, None, "어느 신호에도 수신 노드가 없습니다"))

        order = list(self.ISSUE_CODES)
        return sorted(issues, key=lambda i: (order.index(i.code), i.message or "", i.signal or ""))

    def _check_start_value(self, message: str, sig: Any) -> list[DbcIssue]:
        raw = self._start_raw(sig)
        bounds = self._raw_range(sig)
        if bounds is not None and not bounds[0] <= raw <= bounds[1]:
            kind = "signed" if sig.is_signed else "unsigned"
            return [DbcIssue(
                "start_value_bits", message, sig.name,
                f"raw {raw} - {sig.length}비트 {kind} 범위는 [{bounds[0]}, {bounds[1]}]",
            )]
        if sig.minimum is None or sig.maximum is None or sig.minimum >= sig.maximum:
            return []
        if sig.choices and raw in sig.choices:
            return []  # 값 테이블에 이름이 있는 값(예: 31 "Invalid")은 범위 밖이어도 일부러 둔 것이다
        value = sig.raw_to_scaled(raw, decode_choices=False)
        if not sig.minimum <= value <= sig.maximum:
            return [DbcIssue(
                "start_value_range", message, sig.name,
                f"{value} - 범위는 [{sig.minimum}, {sig.maximum}]",
            )]
        return []

    def validation_report(self, issues: list[DbcIssue] | None = None, *, limit: int | None = None) -> str:
        """:meth:`validate` 결과를 종류별로 묶은 글. limit 을 주면 종류마다 그만큼만 보인다."""
        issues = self.validate() if issues is None else issues
        if not issues:
            return f"[{self.name}] DBC 결함 없음"
        lines = [f"[{self.name}] DBC 결함 {len(issues)}건"]
        for code, text in self.ISSUE_CODES.items():
            group = [i for i in issues if i.code == code]
            if not group:
                continue
            lines.append(f"  {code} {len(group)}건 - {text}")
            shown = group if limit is None else group[:limit]
            lines.extend(f"    {i}" for i in shown)
            if len(shown) < len(group):
                lines.append(f"    … 외 {len(group) - len(shown)}건")
        return "\n".join(lines)

    def node_issues(
        self, node: str, issues: list[DbcIssue] | None = None
    ) -> list[tuple[DbcIssue, str]]:
        """노드가 보내거나 받는 메시지의 결함 → [(결함, "보냄"|"받음"|"보냄·받음")].

        제어기 개발 쪽이 보는 범위다 — 다른 ECU끼리의 메시지 결함은 DB 담당이 볼 일이다.
        메시지에 묶이지 않은 결함(DB 전체)은 넣지 않는다.

        관계는 **메시지 단위** 로 본다. 신호 하나의 결함(초기값 등)이어도 노드가 그 메시지를
        받으면 "받음" 이다 — 노드가 그 신호 자체는 쓰지 않을 수 있다 (예: FD_B2 의
        HU_USM_07_00ms 는 DUT 가 받지만 결함 신호 MDLZone1~3Set 의 수신 노드는 없다).
        TODO: 신호 결함은 노드가 그 신호를 받을 때만 넣기.
        """
        self._check_node(node)
        issues = self.validate() if issues is None else issues
        found = []
        for issue in issues:
            if issue.message is None or issue.message not in self._by_name:
                continue
            spec = self._by_name[issue.message]
            roles = [r for r, ok in (("보냄", node in spec.senders), ("받음", node in spec.receivers)) if ok]
            if roles:
                found.append((issue, "·".join(roles)))
        return found

    def node_report(self, node: str, issues: list[DbcIssue] | None = None) -> str:
        """:meth:`node_issues` 를 종류별로 묶은 글. 나머지 결함은 개수만 적는다."""
        issues = self.validate() if issues is None else issues
        mine = self.node_issues(node, issues)
        if not mine:
            lines = [f"[{self.name}] {node} 관련 DBC 결함 없음"]
        else:
            lines = [f"[{self.name}] {node} 관련 DBC 결함 {len(mine)}건"]
            for code, text in self.ISSUE_CODES.items():
                group = [(i, role) for i, role in mine if i.code == code]
                if group:
                    lines.append(f"  {code} {len(group)}건 - {text}")
                    lines.extend(f"    ({role}) {i}" for i, role in group)
        rest = len(issues) - len(mine)
        if rest:
            lines.append(f"  그 밖의 DB 결함 {rest}건 - 다른 ECU 것. 전체 목록은 --all")
        return "\n".join(lines)

    # ============================================================ 리포트
    def summary(self, node: str) -> str:
        """node 기준 송신·수신 메시지 표."""
        lines = [f"[{self.name}]  기준 노드 {node}"]
        for title, specs in (("보내는 메시지", self.tx_of(node)), ("받는 메시지", self.rx_of(node))):
            lines.append("")
            lines.append(f"  {title} {len(specs)}개")
            lines.append(
                f"  {_pad('ID', 11)} {_pad('이름', 34)} {_pad('길이', 4, right=True)} "
                f"{_pad('주기', 7, right=True)}  {_pad('종류', 5)} CRC/카운터"
            )
            for s in sorted(specs, key=lambda x: (x.extended, x.frame_id)):
                cycle = f"{s.cycle_ms}ms" if s.cycle_ms else "이벤트"
                e2e = "있음" if (s.crc_signals or s.counter_signals) else "-"
                lines.append(
                    f"  {s.id_text:<11} {s.name[:34]:<34} {s.length:>4} "
                    f"{_pad(cycle, 7, right=True)}  {s.kind:<5} {e2e}"
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<CanDbc {self.name} messages={len(self)} nodes={len(self.nodes)}>"


def main(argv: list[str] | None = None) -> int:
    """DBC 자체 검증을 명령행에서 돌린다. 종료 코드: 0 결함 없음 / 1 결함 있음 / 2 오류.

        python CanDbc.py <DBC 파일>                     DB 전체 결함 목록 (DB 담당용)
        python CanDbc.py <DBC 파일> <노드 이름>          그 노드가 보내고 받는 메시지의 결함만
        python CanDbc.py <DBC 파일> <노드 이름> --table  + 그 노드의 송신·수신 표
        python CanDbc.py <DBC 파일> <노드 이름> --all    + 뒤에 DB 전체 결함 목록 (DB 담당 전달용)
        python CanDbc.py <DBC 파일> ... --out 결과.txt   파일(UTF-8)로도 남긴다

    노드 이름을 주면 종료 코드도 그 노드 관련 결함으로 정한다 (--all 이어도).
    """
    import argparse

    ap = argparse.ArgumentParser(prog="CanDbc", description="DBC 자체 검증 (결함 목록)")
    ap.add_argument("dbc", help="DBC 파일")
    ap.add_argument("node", nargs="?", help="노드 이름. 주면 그 노드 관련 결함만 보인다")
    ap.add_argument("--table", action="store_true", help="노드의 송신·수신 표도 보인다")
    ap.add_argument("--all", action="store_true", help="노드 관련 결함 뒤에 DB 전체 결함 목록도 붙인다")
    ap.add_argument("--out", metavar="FILE", help="결과를 이 파일로도 남긴다 (UTF-8)")
    a = ap.parse_args(argv)

    try:
        dbc = CanDbc.load(a.dbc)
        parts = [f"DBC {os.path.abspath(a.dbc)}"]
        issues = dbc.validate()
        if a.node:
            if a.table:
                parts.append(dbc.summary(a.node))
            parts.append(dbc.node_report(a.node, issues))
            found = len(dbc.node_issues(a.node, issues))
            if a.all:
                parts.append("--- 참고: DB 전체 결함 (다른 ECU 것 포함) ---\n" + dbc.validation_report(issues))
        else:
            parts.append(dbc.validation_report(issues))
            found = len(issues)
    except CanDbcError as exc:
        print(f"[오류] {exc}")
        return 2
    text = "\n\n".join(parts)

    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\n결과 {os.path.abspath(a.out)}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
