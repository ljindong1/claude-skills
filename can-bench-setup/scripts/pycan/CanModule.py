"""python-can 래퍼 베이스 클래스.

제품별 자식 클래스가 :class:`CanBase` 를 상속해서 "제품 선언"(채널/비트레이트/ID)과
"제품 로직"(시퀀스·검증)만 작성하면, 연결·수신 디스패치·주기 전송·필터·트레이스·
통계·종료 순서 같은 인프라는 전부 베이스가 책임진다.

설계 요약
---------
* **has-a bus** : ``can.BusABC`` 를 상속하지 않고 내부에 보유한다.
  ``BusABC`` 상속은 새 하드웨어 백엔드를 만들 때 쓰는 것이고, 애플리케이션 추상화에는
  합성이 맞다(python-can 자신의 ``ThreadSafeBus`` 도 프록시 방식이다).
* **Notifier 1개 소유** : 수신은 전부 Notifier 콜백으로 처리하며 ``bus.recv()`` 를
  직접 호출하지 않는다. 프레임은 소비자 하나에게만 가기 때문에, 둘을 섞으면
  서로 프레임을 빼앗는다. Notifier를 프로퍼티로 노출해 isotp/canopen이 공유할 수 있게 한다.
* **종료 순서** : ``notifier.stop()`` → ``bus.shutdown()``.
  ``bus.shutdown()`` 은 Notifier를 멈추지 않는다(hardbyte/python-can#1526).

락 순서 (역방향 획득 금지)
    ``_lifecycle_lock`` → ``_tx_lock`` → ``_rx_lock`` → ``_buffer_cond`` → ``_stats_lock``

    ``_buffer_cond`` 는 링버퍼(``_buffer``)를 보호하는 Condition이며 ``_rx_lock`` 과는
    다른 락이다. 둘을 동시에 보유하지 않는다 — 대기자 평가는 ``_rx_lock`` 아래에서
    스냅샷만 뜨고 락을 놓은 뒤 수행한다. ``_buffer_cond`` 안에서 잡는 락은
    ``_stats_lock`` 하나뿐이다(``_on_frame`` 의 드롭 카운트 경로).

수신 스레드 주의
    ``on_message`` / ``on_error_frame`` / 대기 술어(predicate) / 등록한 리스너는
    모두 **Notifier 수신 스레드**에서 실행된다. 빠르게 끝나야 하고
    ``send()`` / ``wait_for()`` / ``disconnect()`` 를 호출해서는 안 된다.
"""

from __future__ import annotations

import copy
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Iterable, Sequence

import can

from CanErrors import (
    CanConfigError,
    CanConnectionError,
    CanNotConnectedError,
    CanReceiveError,
    CanReceiveTimeout,
    CanSendError,
)
from can_log import CanLogger

__all__ = [
    "CanBase", "CanConfig", "CanMode", "CanStats", "CanWaiter", "AUTO_SERIAL", "pick_vector_serial",
    "BackendProfile", "VectorProfile", "backend_profile", "register_backend",
]

log = CanLogger.get("CanModule")

#: CAN FD가 실제로 전송할 수 있는 페이로드 길이. 9~11, 13~15 같은 길이는 존재하지 않는다.
FD_LENGTHS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)

STD_MASK = 0x7FF
EXT_MASK = 0x1FFFFFFF

#: Vector가 허용하는 rx_queue_size 범위 (2의 거듭제곱이어야 한다)
VECTOR_RX_QUEUE_RANGE = {False: (16, 32768), True: (8192, 524288)}

#: python-can이 gzip 압축을 지원하지 않는 트레이스 확장자
_NO_GZIP_SUFFIX = (".blf", ".db")
_TRACE_SUFFIXES = (".asc", ".blf", ".csv", ".db", ".log", ".mf4", ".trc", ".txt")

#: match 인자로 받을 수 있는 형태
MatchSpec = "int | tuple[int, int] | Callable[[can.Message], bool]"


class CanMode(Enum):
    """버스 동작 모드."""

    CLASSIC = "classic"  #: CAN 2.0A/B, 최대 8바이트
    FD = "fd"  #: CAN FD, 비트레이트 전환 없음
    FD_BRS = "fd_brs"  #: CAN FD + Bit Rate Switch

    @property
    def is_fd(self) -> bool:
        """FD 계열 모드인지 여부."""
        return self is not CanMode.CLASSIC


@dataclass
class CanStats:
    """송수신 통계. :meth:`CanBase.stats` 가 복사본을 돌려준다."""

    tx_count: int = 0
    rx_count: int = 0
    error_frames: int = 0
    dropped: int = 0  #: 링버퍼가 가득 차 버려진 프레임 수
    listener_errors: int = 0
    send_errors: int = 0
    first_rx_ts: float | None = None
    last_rx_ts: float | None = None
    last_tx_ts: float | None = None
    connected_at: float | None = None

    @property
    def rx_rate(self) -> float:
        """연결 이후 평균 수신 프레임/초. 아직 수신이 없으면 0.0."""
        if not self.connected_at or not self.rx_count:
            return 0.0
        elapsed = time.time() - self.connected_at
        return self.rx_count / elapsed if elapsed > 0 else 0.0


@dataclass
class CanConfig:
    """``can.Bus()`` 생성에 필요한 파라미터 일체.

    ``CanBase.default_config()`` 가 클래스 속성으로부터 이 객체를 만들어 준다.
    """

    interface: str = "virtual"
    channel: int | str | Sequence[int] = 0
    mode: CanMode = CanMode.CLASSIC
    bitrate: int = 500_000
    data_bitrate: int = 2_000_000
    timing: Any = None  #: can.BitTiming | can.BitTimingFd. 지정 시 bitrate는 무시된다
    # TODO(범용화 P2): 기본값을 None 으로 (Vector 기본값은 CanConfig.vector() 만 갖게).
    #   CanConfig(interface="vector") 를 app_name 없이 만드는 코드가 앱 채널 → 글로벌 인덱스
    #   방식으로 바뀌므로 호출부를 확인하고 한다. 다른 백엔드에는 넘어가지 않아 지금은 무해하다.
    app_name: str | None = "CANalyzer"  #: Vector 전용. None이면 channel이 글로벌 인덱스
    serial: int | None = None  #: Vector 하드웨어 시리얼 직접 지정
    rx_queue_size: int | None = None  #: Vector 전용. None이면 백엔드 기본값
    receive_own_messages: bool = False
    can_filters: list[dict] | None = None
    ignore_config: bool = True  #: ~/.canrc, can.rc 무시 → 제품 동작의 결정성 확보
    thread_safe: bool = False  #: True면 can.ThreadSafeBus 사용
    extra: dict[str, Any] = field(default_factory=dict)  #: 백엔드 전용 kwargs 탈출구

    # ------------------------------------------------------------------ 생성 헬퍼
    @classmethod
    def virtual(cls, channel: str = "devtest", *, fd: bool = False, **kw: Any) -> CanConfig:
        """하드웨어 없이 개발/테스트에 쓸 virtual 설정을 만든다.

        같은 channel 이름을 쓰는 virtual 버스끼리는 서로의 트래픽을 본다.
        버스 하나로 자기 송신을 확인하려면 ``receive_own_messages=True`` 가 필요하다.
        """
        kw.setdefault("app_name", None)
        return cls(
            interface="virtual",
            channel=channel,
            mode=CanMode.FD if fd else CanMode.CLASSIC,
            **kw,
        )

    @classmethod
    def vector(
        cls,
        channel: int | Sequence[int] = 0,
        *,
        app_name: str | None = "CANalyzer",
        serial: int | None = None,
        fd: bool = False,
        **kw: Any,
    ) -> CanConfig:
        """Vector VN 시리즈용 설정을 만든다.

        채널 지정 방식은 셋 중 하나만 쓴다.

        1. ``app_name="CANalyzer"`` + ``channel=0`` — Vector Hardware Config의 앱 채널
        2. ``serial=<시리얼>`` + ``channel=<장비 내 채널>`` — 장비를 직접 지정
        3. ``app_name=None`` + ``channel=<글로벌 인덱스>`` — 앱 설정 없이 직접 지정
        """
        if serial is not None:
            app_name = None
        return cls(
            interface="vector",
            channel=channel,
            app_name=app_name,
            serial=serial,
            mode=CanMode.FD_BRS if fd else CanMode.CLASSIC,
            **kw,
        )

    # ------------------------------------------------------------------ 검증/변환
    def validate(self) -> None:
        """상호배타·범위 조건을 검사하고 위반 시 :class:`CanConfigError` 를 발생시킨다."""
        # timing과 bitrate를 python-can에 함께 넘기면 조용히 하나만 쓰인다.
        # to_bus_kwargs()가 timing이 있을 때 bitrate 키를 아예 빼므로 여기서는 모호함이 없다.
        if self.mode.is_fd and self.data_bitrate < self.bitrate:
            raise CanConfigError(
                f"data_bitrate({self.data_bitrate})는 bitrate({self.bitrate})보다 "
                "작을 수 없습니다."
            )

        backend_profile(self.interface).validate(self)

    def to_bus_kwargs(self) -> dict[str, Any]:
        """``can.Bus(**kwargs)`` 에 그대로 넘길 수 있는 dict로 변환한다."""
        # interface= 만 사용한다. bustype= 은 4.2.0부터 deprecated이고 5.0.0에서 제거된다.
        kwargs: dict[str, Any] = {
            "interface": self.interface,
            "channel": self.channel,
            "receive_own_messages": self.receive_own_messages,
            "ignore_config": self.ignore_config,
        }

        if self.can_filters:
            kwargs["can_filters"] = self.can_filters

        if self.timing is not None:
            kwargs["timing"] = self.timing
        else:
            kwargs["bitrate"] = self.bitrate

        if self.mode.is_fd:
            # FD_BRS의 BRS는 '버스' 플래그가 아니라 '메시지' 플래그다.
            # 여기서는 fd=True만 넘기고, BRS는 build_message()의 기본값으로 반영된다.
            kwargs["fd"] = True
            if self.timing is None:
                kwargs["data_bitrate"] = self.data_bitrate

        # 백엔드 전용 키는 그 백엔드의 프로파일만 넣는다.
        # 백엔드의 **kwargs 관용성에 기대면 버전에 따라 TypeError가 난다.
        kwargs.update(backend_profile(self.interface).bus_kwargs(self))
        kwargs.update(self.extra)
        return kwargs


class CanWaiter:
    """조건에 맞는 프레임을 기다리는 1회용 토큰.

    ``send()`` 보다 **먼저** 등록되어야 응답을 놓치지 않는다.
    직접 만들지 말고 :meth:`CanBase.arm` 으로 생성한다.
    """

    __slots__ = ("_owner", "_predicate", "_count", "_rx_only", "_event", "_messages", "_lock")

    def __init__(
        self,
        owner: CanBase,
        predicate: Callable[[can.Message], bool],
        count: int,
        rx_only: bool,
    ) -> None:
        self._owner = owner
        self._predicate = predicate
        self._count = count
        self._rx_only = rx_only
        self._event = threading.Event()
        self._messages: list[can.Message] = []
        self._lock = threading.Lock()

    # -- 수신 스레드에서 호출 --------------------------------------------------
    def _offer(self, msg: can.Message) -> bool:
        """프레임을 평가한다. 조건이 모두 충족되어 완료되면 True를 반환한다."""
        if self._rx_only and not msg.is_rx:
            return False
        if not self._predicate(msg):
            return False
        with self._lock:
            self._messages.append(msg)
            done = len(self._messages) >= self._count
        if done:
            self._event.set()
        return done

    def _release(self) -> None:
        """버스가 닫힐 때 대기 중인 스레드를 깨운다(결과 없음)."""
        self._event.set()

    # -- 사용자 스레드에서 호출 ------------------------------------------------
    def wait(self, timeout: float | None = 1.0) -> can.Message | None:
        """조건에 맞는 첫 프레임을 기다린다. 못 받으면 None."""
        self._event.wait(timeout)
        with self._lock:
            return self._messages[0] if self._messages else None

    def wait_all(self, timeout: float | None = 1.0) -> list[can.Message]:
        """count개가 모일 때까지 기다린 뒤 수집된 프레임을 반환한다."""
        self._event.wait(timeout)
        with self._lock:
            return list(self._messages)

    @property
    def matched(self) -> bool:
        """하나 이상 매칭되었는지 여부."""
        with self._lock:
            return bool(self._messages)

    @property
    def messages(self) -> list[can.Message]:
        """지금까지 수집된 프레임 목록(복사본)."""
        with self._lock:
            return list(self._messages)

    def cancel(self) -> None:
        """대기를 취소하고 레지스트리에서 자신을 제거한다."""
        self._owner._unregister_waiter(self)

    def __enter__(self) -> CanWaiter:
        return self

    def __exit__(self, *exc: Any) -> None:
        # 타임아웃된 waiter가 남으면 이후 모든 프레임이 죽은 술어를 평가하게 되므로
        # 예외 여부와 무관하게 반드시 해제한다.
        self.cancel()


# ============================================================ 장비 고르기
#: 시리얼 자리에 이 값을 두면 꽂힌 장비를 찾아 쓴다
AUTO_SERIAL = "auto"


def _is_virtual(found: dict[str, Any]) -> bool:
    hw_type = found.get("hw_type")
    return "VIRTUAL" in str(getattr(hw_type, "name", hw_type)).upper()


def pick_vector_serial(
    configured: Any, channels: set[int], detected: list[dict[str, Any]]
) -> tuple[int, str | None]:
    """감지된 Vector 장비 중에서 쓸 시리얼을 고른다 → (시리얼, 알릴 말 또는 None).

    ``detected`` 는 :meth:`CanBase.detect` 결과. 필요한 채널을 모두 가진 실물
    장비(virtual 제외)만 후보다.

    * 설정한 시리얼이 후보에 있으면 그대로 쓴다
    * 아니면 후보가 **하나일 때만** 그것을 쓴다 — 장비를 바꿔 끼운 경우. 알릴 말을 돌려준다
    * 후보가 없거나 여럿이면 :class:`CanConfigError` — 어느 장비인지 사람이 정해야 한다
      (잘못 고르면 엉뚱한 장비로 송신한다)
    """
    by_serial: dict[int, set[int]] = {}
    for found in detected:
        if not _is_virtual(found) and found.get("serial") is not None:
            by_serial.setdefault(found["serial"], set()).add(found.get("channel"))
    fits = sorted(s for s, chs in by_serial.items() if channels <= chs)
    listing = ", ".join(f"serial {s} 채널 {sorted(chs)}" for s, chs in sorted(by_serial.items())) or "없음"

    if configured in fits:
        return configured, None
    if len(fits) == 1:
        if configured in (None, AUTO_SERIAL):
            return fits[0], f"장비 자동 선택: serial {fits[0]}"
        return fits[0], (
            f"설정한 serial {configured} 장비가 없어 연결된 serial {fits[0]} 을 씁니다 "
            f"(serial 을 \"{AUTO_SERIAL}\" 로 두면 이 안내가 나오지 않습니다)"
        )
    if not fits:
        raise CanConfigError(
            f"채널 {sorted(channels)} 을 모두 가진 Vector 장비가 없습니다. 감지된 장비: {listing}. "
            "USB 연결, 드라이버, 다른 프로그램(CANoe 등)이 채널을 잡고 있는지 확인하세요."
        )
    raise CanConfigError(
        f"채널 {sorted(channels)} 을 가진 장비가 여러 대입니다: {listing}. 쓸 장비의 시리얼을 지정하세요."
    )


# ============================================================ 백엔드별 처리
class BackendProfile:
    """interface 하나에 딸린 전용 처리를 한곳에 모은다.

    기본 구현은 아무것도 하지 않는다 — python-can 에 공통 키만 넘긴다.
    전용 키·검증·장비 고르기가 필요한 백엔드만 자식 클래스를 만들어
    :func:`register_backend` 로 등록한다. CanBase 와 설정 파일 로더는
    ``if interface == ...`` 분기 없이 :func:`backend_profile` 만 부른다.

    TODO(범용화 P4): 벤더 전용 옵션(app_name/serial/rx_queue_size)이 CanConfig 공통
    필드에 있다. 두 번째 벤더가 생기면 설정 파일 [device] 에 옵션 표를 두고
    :attr:`CanConfig.extra` 로 넘기는 통로를 만든다. Vector 외 백엔드는 실장비로
    아직 확인하지 않았다.
    """

    def validate(self, config: CanConfig) -> None:
        """전용 조건을 검사한다. 위반 시 :class:`CanConfigError`."""

    def bus_kwargs(self, config: CanConfig) -> dict[str, Any]:
        """``can.Bus()`` 에 더 넘길 전용 키."""
        return {}

    def connect_details(self, config: CanConfig) -> list[str]:
        """연결 실패 메시지에 붙일 전용 설정값 (원인 앞)."""
        return []

    def connect_advice(self, config: CanConfig) -> list[str]:
        """연결 실패 메시지 끝에 붙일 점검 안내."""
        return []

    def settings_kwargs(self, device: dict[str, Any]) -> dict[str, Any]:
        """설정 파일 [device] 표 → CanConfig 전용 필드."""
        return {"app_name": None, "serial": None}

    def resolve_device(self, device: dict[str, Any], configs: list[CanConfig]) -> str | None:
        """연결 직전에 장비를 감지해 configs 를 확정한다. 알릴 말을 돌려준다."""
        return None


class VectorProfile(BackendProfile):
    """Vector XL (VN 시리즈). 채널 지정 3방식과 시리얼 자동 선택을 맡는다."""

    def validate(self, config: CanConfig) -> None:
        if config.serial is not None and config.app_name is not None:
            raise CanConfigError(
                "serial과 app_name을 동시에 지정할 수 없습니다. "
                "장비를 직접 지정하려면 serial만, Vector Hardware Config의 앱 채널을 "
                "쓰려면 app_name만 사용하세요."
            )
        if config.serial is None and config.app_name is None:
            if not isinstance(config.channel, int):
                raise CanConfigError(
                    "app_name=None(글로벌 채널 인덱스 방식)일 때 channel은 정수여야 "
                    f"합니다. 지금 값: {config.channel!r}"
                )

        if config.rx_queue_size is not None:
            size = config.rx_queue_size
            low, high = VECTOR_RX_QUEUE_RANGE[config.mode.is_fd]
            if size & (size - 1) or not (low <= size <= high):
                raise CanConfigError(
                    f"rx_queue_size는 2의 거듭제곱이면서 {low}~{high} 범위여야 합니다"
                    f"({'FD' if config.mode.is_fd else 'Classic'} 기준). 지금 값: {size}"
                )

    def bus_kwargs(self, config: CanConfig) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"app_name": config.app_name}
        if config.serial is not None:
            kwargs["serial"] = config.serial
        if config.rx_queue_size is not None:
            kwargs["rx_queue_size"] = config.rx_queue_size
        return kwargs

    def connect_details(self, config: CanConfig) -> list[str]:
        return [f"app_name={config.app_name!r}", f"serial={config.serial!r}"]

    def connect_advice(self, config: CanConfig) -> list[str]:
        return [
            "Vector XL Driver Library(vxlapi64.dll) 설치 여부와 "
            "Vector Hardware Config의 채널 할당을 확인하세요."
        ]

    def settings_kwargs(self, device: dict[str, Any]) -> dict[str, Any]:
        serial = device.get("serial")
        if serial == AUTO_SERIAL:
            return {"app_name": None, "serial": None}  # resolve_device 가 채운다
        if serial is not None:
            return {"app_name": None, "serial": serial}
        return {"app_name": device.get("app_name"), "serial": None}

    def resolve_device(self, device: dict[str, Any], configs: list[CanConfig]) -> str | None:
        if device.get("app_name"):
            return None  # 앱 채널 방식이면 Vector Hardware Config 가 장비를 정한다
        serial, note = CanBase.find_serial({c.channel for c in configs}, device.get("serial"))
        for config in configs:
            config.serial = serial
        return note


_DEFAULT_PROFILE = BackendProfile()
_PROFILES: dict[str, BackendProfile] = {"vector": VectorProfile()}


def register_backend(interface: str, profile: BackendProfile) -> None:
    """interface 전용 처리를 등록한다. 같은 이름이 있으면 바꾼다."""
    _PROFILES[interface] = profile


def backend_profile(interface: str) -> BackendProfile:
    """interface 의 전용 처리. 등록되지 않았으면 아무것도 하지 않는 기본 처리."""
    return _PROFILES.get(interface, _DEFAULT_PROFILE)


class _PeriodicSender:
    """주기 전송 스레드가 쓰는 송신 창구. :meth:`CanBase.send` 와 같은 길로 보낸다.

    python-can 의 주기 스레드는 이 객체의 ``send()`` 만 부른다. 그래서 주기 프레임도
    트레이스·통계·``on_send`` 에 남는다. 송신 실패는 여기서 삼키고 다음 주기에 다시
    보낸다 — 경고는 끊길 때와 다시 나갈 때 한 번씩만 남긴다.
    """

    def __init__(self, owner: CanBase, key: str) -> None:
        self._owner = owner
        self.key = key
        self.task: can.broadcastmanager.ThreadBasedCyclicSendTask | None = None
        self._failing = False

    def send(self, msg: can.Message, timeout: float | None = None) -> None:
        owner = self._owner
        if not owner.is_connected:  # 끊는 중에 한 주기가 더 돌 수 있다 — 조용히 끝낸다
            if self.task is not None:
                self.task.stop()
            return
        # 태스크는 같은 Message 를 계속 고쳐 쓴다. 훅·트레이스에는 이번 프레임의 사본을 준다
        out = copy.copy(msg)
        out.data = bytearray(msg.data)
        out.timestamp = 0.0
        try:
            owner.send(out, timeout=timeout)
        except CanSendError as exc:
            if not self._failing:
                self._failing = True
                owner.log.warning("주기 전송 '%s' 실패 - 다음 주기에 다시 보냄: %s", self.key, exc)
            return
        if self._failing:
            self._failing = False
            owner.log.info("주기 전송 '%s' 다시 나감", self.key)

    def on_error(self, exc: Exception) -> bool:
        """send() 밖에서 난 예외(modifier_callback 등). True 면 태스크가 계속 돈다."""
        if isinstance(exc, CanNotConnectedError):
            return False
        self._owner.log.warning("주기 전송 '%s' 오류 - 계속 보냄: %s", self.key, exc)
        return True


class _RxOnly(can.Listener):
    """수신 프레임만 넘긴다. 송신을 직접 기록할 때 돌아오는 자기 에코를 거른다."""

    def __init__(self, target: can.Listener) -> None:
        self._target = target

    def on_message_received(self, msg: can.Message) -> None:
        if msg.is_rx or msg.is_error_frame:
            self._target.on_message_received(msg)

    def stop(self) -> None:
        self._target.stop()


class _Dispatcher(can.Listener):
    """CanBase가 Notifier에 등록하는 유일한 리스너.

    통계 → 링버퍼 → 대기자 → 자식 훅 → 사용자 리스너 순으로 팬아웃한다.
    리스너를 Notifier에 직접 등록하지 않고 이 한 겹을 두는 이유는,
    ``Listener.on_error`` 의 기본 구현이 ``NotImplementedError`` 라서
    예외가 한 번 나면 수신 스레드가 죽고 제품이 영구히 조용해지기 때문이다.
    """

    def __init__(self, owner: CanBase) -> None:
        super().__init__()
        self._owner = owner

    def on_message_received(self, msg: can.Message) -> None:
        # 이 메서드에서 예외가 새어 나가면 Notifier 수신 스레드가 죽는다.
        # 모든 팬아웃을 개별적으로 감싼다.
        try:
            self._owner._on_frame(msg)
        except Exception:  # pragma: no cover - 방어적
            log.exception("디스패처 처리 중 예상치 못한 예외")

    def on_error(self, exc: Exception) -> None:
        """수신 스레드의 예외를 받아 기록하고 **정상 반환**한다.

        기본 구현(``NotImplementedError``)을 그대로 두면 수신이 영구 중단된다.
        """
        self._owner._on_rx_error(exc)

    def stop(self) -> None:
        pass


class CanBase:
    """python-can 래퍼 베이스 클래스.

    자식 클래스는 클래스 속성으로 제품을 선언하고, 필요한 훅만 오버라이드한다.
    추상 메서드는 없으므로 이 클래스 자체도 그대로 인스턴스화할 수 있다.

        >>> with CanBase(CanConfig.virtual("demo", receive_own_messages=True)) as bus:
        ...     bus.send(0x123, b"\\x01\\x02")
    """

    # ------------------------------------------------------------ 제품 선언 (자식이 채운다)
    #: 자식이 반드시 재선언한다. 이 기본값은 "아직 안 정함" 표식으로도 쓰인다
    #: (:meth:`__init_subclass__` 참조).
    PRODUCT_NAME: str = "CanBase"

    # 인터페이스
    INTERFACE: str = "virtual"
    CHANNEL: int | str | Sequence[int] = 0
    APP_NAME: str | None = None  #: Vector 전용. None이면 CHANNEL이 글로벌 인덱스
    SERIAL: int | None = None
    IGNORE_CONFIG: bool = True

    # 비트레이트
    MODE: CanMode = CanMode.CLASSIC
    BITRATE: int = 500_000
    DATA_BITRATE: int = 2_000_000
    F_CLOCK: int | None = None  #: 지정하면 bitrate 대신 BitTiming 객체를 계산해 사용한다
    SAMPLE_POINT: float = 80.0
    DATA_SAMPLE_POINT: float = 75.0
    VALID_CLOCKS: Sequence[int] | None = None  #: 하드웨어가 지원하는 f_clock 목록

    # 동작
    DEFAULT_EXTENDED_ID: bool = False  #: python-can의 기본값(True)을 뒤집는다
    RECEIVE_OWN_MESSAGES: bool = False
    RX_QUEUE_SIZE: int | None = None
    NOTIFIER_TIMEOUT: float = 0.2  #: 종료 지연시간 ≈ 이 값
    NOTIFIER_STOP_TIMEOUT: float = 5.0  #: 수신 스레드 join 예산
    RX_BUFFER_MAXLEN: int = 10_000
    THREAD_SAFE: bool = False
    SEND_TIMEOUT: float | None = 1.0

    # 트레이스
    TRACE_DIR: str = "trace"
    TRACE_SUFFIX: str = ".asc"

    # DBC (CanBase.dbc 가 읽는다) / UDS (예정) 자리
    DBC_PATH: str | None = None
    UDS_TX_ID: int | None = None
    UDS_RX_ID: int | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """자식 클래스가 PRODUCT_NAME을 선언했는지 클래스 정의 시점에 확인한다.

        PRODUCT_NAME은 :attr:`name` 의 기본값이 되어 로거 이름, 트레이스 파일명,
        모든 예외 메시지에 실린다. 빼먹어도 예외 없이 동작하기 때문에, 여러 제품을
        한 프로세스에서 돌릴 때 로그와 트레이스가 전부 "CanBase"로 뭉개져
        어느 쪽이 남긴 기록인지 구분할 수 없게 된다. 그 실수를 하드웨어 연결은
        커녕 인스턴스 생성보다도 전에 드러낸다.

        검사는 ``class`` 문이 **실행**될 때 일어난다. 모듈 최상위 클래스는 곧
        import 시점이지만, 함수 안에서 정의하는 클래스는 그 함수를 호출해야
        검사된다.
        """
        super().__init_subclass__(**kwargs)
        # 자식이 선언하지 않으면 상속으로 CanBase의 기본값이 그대로 보인다.
        if cls.PRODUCT_NAME == CanBase.PRODUCT_NAME:
            raise TypeError(
                f"{cls.__name__}는 PRODUCT_NAME 클래스 속성을 선언해야 합니다. "
                "로거 이름과 트레이스 파일명에 쓰입니다. "
                '예: PRODUCT_NAME = "SeatECU"'
            )

    # ============================================================ 생성 / 설정
    def __init__(
        self,
        config: CanConfig | None = None,
        *,
        name: str | None = None,
        autoconnect: bool = False,
        logger: Any = None,
    ) -> None:
        """설정을 확정하고 내부 상태를 준비한다. **I/O는 수행하지 않는다.**

        하드웨어가 없어도 객체를 만들고 검사할 수 있어야 하며, 연결 실패는
        통제된 호출 지점(:meth:`connect`)에서 드러나야 하기 때문이다.
        """
        self.name = name or self.PRODUCT_NAME
        self.log = logger or CanLogger.get(self.name)
        self._config = config if config is not None else self.default_config()

        self._bus: can.BusABC | None = None
        self._notifier: can.Notifier | None = None
        self._dispatcher: _Dispatcher | None = None

        self._lifecycle_lock = threading.RLock()
        self._tx_lock = threading.RLock()
        self._rx_lock = threading.Lock()
        self._stats_lock = threading.Lock()

        self._buffer: deque[can.Message] = deque(maxlen=self.RX_BUFFER_MAXLEN)
        self._buffer_cond = threading.Condition(threading.Lock())
        self._waiters: list[CanWaiter] = []
        self._listeners: dict[str, Any] = {}
        self._listener_seq = 0

        self._periodic: dict[str, can.broadcastmanager.CyclicSendTaskABC] = {}
        self._periodic_send_lock = threading.Lock()  #: 주기 스레드들이 번갈아 보내게 한다
        self._filters: list[dict] | None = self._config.can_filters

        self._trace_writer: Any = None
        self._trace_listener: Any = None  #: Notifier 에 붙인 것 (writer 또는 에코를 거르는 감싸개)
        self._trace_path: str | None = None
        self._trace_tx: bool = True

        self._stats = CanStats()
        self._dbc: Any = None  #: dbc 프로퍼티가 처음 쓸 때 읽는다

        if autoconnect:
            self.connect()

    @classmethod
    def default_config(cls, **overrides: Any) -> CanConfig:
        """클래스 속성(INTERFACE/CHANNEL/BITRATE 등)으로부터 CanConfig를 생성한다."""
        timing = None
        if cls.F_CLOCK:
            timing = cls.make_timing(
                cls.MODE,
                cls.F_CLOCK,
                nom_bitrate=cls.BITRATE,
                nom_sample_point=cls.SAMPLE_POINT,
                data_bitrate=cls.DATA_BITRATE,
                data_sample_point=cls.DATA_SAMPLE_POINT,
                valid_clocks=cls.VALID_CLOCKS,
            )

        config = CanConfig(
            interface=cls.INTERFACE,
            channel=cls.CHANNEL,
            mode=cls.MODE,
            bitrate=cls.BITRATE,
            data_bitrate=cls.DATA_BITRATE,
            timing=timing,
            app_name=cls.APP_NAME,
            serial=cls.SERIAL,
            rx_queue_size=cls.RX_QUEUE_SIZE,
            receive_own_messages=cls.RECEIVE_OWN_MESSAGES,
            ignore_config=cls.IGNORE_CONFIG,
            thread_safe=cls.THREAD_SAFE,
        )
        return replace(config, **overrides) if overrides else config

    @property
    def config(self) -> CanConfig:
        """현재 설정 객체."""
        return self._config

    @staticmethod
    def make_timing(
        mode: CanMode,
        f_clock: int,
        *,
        nom_bitrate: int,
        nom_sample_point: float = 80.0,
        data_bitrate: int | None = None,
        data_sample_point: float = 75.0,
        valid_clocks: Sequence[int] | None = None,
    ) -> Any:
        """샘플포인트 기반으로 재현 가능한 비트타이밍 객체를 만든다.

        ``bitrate=`` 만 넘기면 백엔드가 자기 기본 세그먼트로 타이밍을 계산하므로
        하드웨어(f_clock)가 다르면 샘플포인트가 달라진다. 같은 샘플포인트를
        보장해야 하는 ECU라면 이 헬퍼로 만든 timing 객체를 쓴다.
        """
        if mode.is_fd:
            if data_bitrate is None:
                raise CanConfigError("FD 모드에서는 data_bitrate가 필요합니다.")
            timing = can.BitTimingFd.from_sample_point(
                f_clock=f_clock,
                nom_bitrate=nom_bitrate,
                nom_sample_point=nom_sample_point,
                data_bitrate=data_bitrate,
                data_sample_point=data_sample_point,
            )
        else:
            timing = can.BitTiming.from_sample_point(
                f_clock=f_clock, bitrate=nom_bitrate, sample_point=nom_sample_point
            )
        if valid_clocks:
            timing = can.util.check_or_adjust_timing_clock(timing, valid_clocks)
        return timing

    @classmethod
    def detect(
        cls, interfaces: str | Iterable[str] | None = None, timeout: float = 5.0
    ) -> list[dict]:
        """연결 가능한 어댑터 목록을 조회한다 (``can.detect_available_configs`` 래퍼).

        내부적으로 모든 백엔드 모듈을 import해 탐색하므로, 드라이버가 없는 PC에서는
        경고 로그가 시끄럽게 나올 수 있다. 예외는 삼키고 빈 목록을 돌려준다.
        """
        try:
            return list(can.detect_available_configs(interfaces=interfaces, timeout=timeout))
        except Exception as exc:  # 백엔드 import 실패 등
            log.debug("어댑터 탐색 실패: %s", exc)
            return []

    # TODO(범용화 P3): Vector 전용이다 (detect(["vector"]) 고정, 규칙은 pick_vector_serial).
    #   두 번째 벤더가 생기면 find_device(interface, channels) 로 바꾸고 판단을
    #   BackendProfile 로 옮긴다. 장비마다 식별 필드가 달라 실장비 감지 결과를 보고 설계한다.
    @classmethod
    def find_serial(cls, channels: Iterable[int], configured: Any = None) -> tuple[int, str | None]:
        """지금 꽂힌 Vector 장비 중 channels 를 모두 가진 것의 시리얼 → (시리얼, 알릴 말).

        장비를 바꿔 끼울 때마다 시리얼을 고치지 않으려고 쓴다. 규칙은
        :func:`pick_vector_serial`. 장비를 감지하므로 1초쯤 걸린다.
        """
        return pick_vector_serial(configured, set(channels), cls.detect(["vector"]))

    # ============================================================ 라이프사이클
    @property
    def is_connected(self) -> bool:
        """버스가 열려 있는지 여부."""
        return self._bus is not None

    @property
    def bus(self) -> can.BusABC:
        """내부 python-can Bus 객체. 미연결이면 :class:`CanNotConnectedError`."""
        if self._bus is None:
            raise CanNotConnectedError(
                f"{self.name}: 아직 연결되지 않았습니다. connect()를 먼저 호출하세요."
            )
        return self._bus

    @property
    def notifier(self) -> can.Notifier:
        """이 인스턴스가 소유한 단 하나의 Notifier.

        isotp/canopen 처럼 같은 버스를 읽어야 하는 라이브러리에 넘겨 공유한다.
        (python-can 4.6부터 한 버스에 Notifier를 둘 이상 붙일 수 없다)
        """
        if self._notifier is None:
            raise CanNotConnectedError(f"{self.name}: 아직 연결되지 않았습니다.")
        return self._notifier

    def connect(self) -> CanBase:
        """버스와 Notifier를 열고 내부 디스패처를 등록한다. 이미 연결되어 있으면 no-op."""
        with self._lifecycle_lock:
            if self._bus is not None:
                return self

            config = self.on_before_connect(self._config) or self._config
            self._config = config
            config.validate()

            kwargs = config.to_bus_kwargs()
            try:
                if config.thread_safe:
                    self._bus = can.ThreadSafeBus(**kwargs)
                else:
                    self._bus = can.Bus(**kwargs)
            except (can.CanInitializationError, can.CanInterfaceNotImplementedError) as exc:
                raise CanConnectionError(self._connect_error_hint(config, exc)) from exc
            except OSError as exc:
                # Vector XL Driver Library(vxlapi64.dll) 부재가 여기로 온다.
                raise CanConnectionError(self._connect_error_hint(config, exc)) from exc

            try:
                self._check_fd_support(config)
                self._attach_notifier()
                self._reapply_filters()
                self._stats.connected_at = time.time()
                self.log.info(
                    "연결 완료: %s / channel=%s / %s",
                    config.interface,
                    config.channel,
                    config.mode.value,
                )
                self.on_after_connect()
            except BaseException:
                # 여기서 정리하지 않으면 드라이버 핸들이 열린 채 남고, 나중에 GC 시점에
                # python-can이 "was not properly shut down" 을 뱉는 추적 불가 버그가 된다.
                self._teardown(run_hooks=False, quiet=True)
                raise

            return self

    def _connect_error_hint(self, config: CanConfig, exc: BaseException) -> str:
        """어느 채널에서 왜 실패했는지 알 수 있는 메시지를 만든다.

        Vector 원시 에러는 ``XL_ERR_HW_NOT_PRESENT`` 처럼 채널 정보가 없다.
        """
        profile = backend_profile(config.interface)
        parts = [
            f"{self.name}: 버스를 열지 못했습니다",
            f"interface={config.interface!r}",
            f"channel={config.channel!r}",
            *profile.connect_details(config),
            f"원인: {type(exc).__name__}: {exc}",
            *profile.connect_advice(config),
        ]
        return " | ".join(parts)

    def _check_fd_support(self, config: CanConfig) -> None:
        """FD 모드인데 백엔드가 FD를 보고하지 않으면 경고한다.

        예외를 던지지 않는 이유: virtual 백엔드는 ``fd=True`` 로 열어도
        ``protocol`` 을 ``CAN_20`` 으로 보고하지만 FD 프레임은 정상적으로 통과시킨다.
        """
        if not config.mode.is_fd:
            return
        protocol = getattr(self._bus, "protocol", None)
        if protocol not in (can.CanProtocol.CAN_FD, can.CanProtocol.CAN_FD_NON_ISO):
            self.log.warning(
                "FD 모드로 설정했지만 백엔드가 보고한 프로토콜은 %s 입니다 "
                "(virtual 백엔드는 정상입니다. 실제 하드웨어라면 FD 지원 여부를 확인하세요).",
                protocol,
            )

    def _attach_notifier(self) -> None:
        """디스패처 하나만 붙인 Notifier를 생성한다."""
        existing = can.Notifier.find_instances(self._bus)
        if existing:
            raise CanConfigError(
                "이 버스에는 이미 다른 Notifier가 붙어 있습니다. "
                "python-can 4.6부터 버스 하나에 Notifier는 하나만 허용됩니다. "
                "isotp/canopen 등은 CanBase.notifier 프로퍼티를 공유해서 사용하세요."
            )
        self._dispatcher = _Dispatcher(self)
        try:
            self._notifier = can.Notifier(
                self._bus, [self._dispatcher], timeout=self.NOTIFIER_TIMEOUT
            )
        except ValueError as exc:
            raise CanConfigError(f"Notifier 생성 실패: {exc}") from exc

    def disconnect(self) -> None:
        """안전한 순서로 종료한다. **예외를 던지지 않는다.**

        ``__exit__`` 에서 호출되므로 원래 예외를 가리면 안 된다.
        """
        with self._lifecycle_lock:
            if self._bus is None and self._notifier is None:
                return
            self._teardown(run_hooks=True, quiet=False)

    def _teardown(self, *, run_hooks: bool, quiet: bool) -> None:
        """종료 순서 — 이 순서가 이 클래스의 핵심 정확성 요구사항이다."""
        level = self.log.debug if quiet else self.log.warning

        def step(what: str, fn: Callable[[], Any]) -> None:
            try:
                fn()
            except Exception:
                level("종료 중 '%s' 단계에서 예외 발생", what, exc_info=True)

        if run_hooks:
            step("on_before_disconnect", self.on_before_disconnect)

        step("stop_all_periodic", self.stop_all_periodic)
        # 트레이스를 Notifier보다 먼저 닫아야 파일 경로를 돌려줄 수 있고 flush가 결정적이다.
        step("stop_trace", self.stop_trace)

        if self._notifier is not None:
            notifier, self._notifier = self._notifier, None
            # notifier.stop()은 수신 스레드를 join한 뒤 모든 리스너의 stop()을 부른다.
            step("notifier.stop", lambda: notifier.stop(self.NOTIFIER_STOP_TIMEOUT))

        if self._bus is not None:
            bus, self._bus = self._bus, None
            # 반드시 Notifier를 멈춘 뒤에. bus.shutdown()은 Notifier를 건드리지 않는다.
            step("bus.shutdown", bus.shutdown)

        self._dispatcher = None
        # 대기 중인 스레드를 깨우지 않으면 wait_for(timeout=None)이 영구히 멈춘다.
        step("release_waiters", self._release_all_waiters)

        if run_hooks:
            step("on_after_disconnect", self.on_after_disconnect)
            self.log.info("연결 종료: %s", self.name)

    def reconnect(self) -> CanBase:
        """disconnect 후 connect를 수행한다. 리스너/필터는 유지되고 수신 버퍼는 비워진다."""
        with self._lifecycle_lock:
            self.disconnect()
            self.clear_buffer()
            return self.connect()

    def __enter__(self) -> CanBase:
        return self.connect()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.disconnect()

    def __del__(self) -> None:
        # disconnect()를 부르지 않는다. 인터프리터 종료 시점에는 모듈 전역이 이미
        # None일 수 있고, __del__에서 스레드를 join하면 데드락 위험이 있다.
        # python-can의 BusABC.__del__도 경고만 남긴다.
        if getattr(self, "_bus", None) is not None:
            try:
                self.log.warning(
                    "%s가 정상 종료되지 않았습니다. with 문이나 disconnect()를 사용하세요.",
                    self.name,
                )
            except Exception:
                pass

    def __repr__(self) -> str:
        state = "connected" if self.is_connected else "disconnected"
        return (
            f"<{type(self).__name__} {self.name} {state} "
            f"{self._config.interface}:{self._config.channel} {self._config.mode.value}>"
        )

    # ============================================================ 송신 (TX)
    def build_message(
        self,
        arb_id: int,
        data: bytes | bytearray | Sequence[int] | None = None,
        *,
        extended: bool | None = None,
        fd: bool | None = None,
        brs: bool | None = None,
        remote: bool = False,
        dlc: int | None = None,
        pad: bool = True,
        pad_value: int = 0x00,
        check: bool = True,
    ) -> can.Message:
        """전송용 ``can.Message`` 를 만든다.

        확장 ID / FD / BRS 기본값은 클래스 속성과 설정에서 가져오므로,
        제품 코드는 ``build_message(0x123, b"\\x01")`` 처럼만 쓰면 된다.
        """
        if extended is None:
            # python-can의 Message는 is_extended_id 기본값이 True다.
            # 11비트 프레임을 29비트로 내보내는 사고를 이 한 줄이 막는다.
            extended = self.DEFAULT_EXTENDED_ID
        if fd is None:
            fd = self._config.mode.is_fd
        if brs is None:
            brs = self._config.mode is CanMode.FD_BRS and fd

        payload = bytearray(data or b"")
        if pad and fd:
            payload = self._pad_fd(payload, pad_value)

        try:
            return can.Message(
                arbitration_id=arb_id,
                data=bytes(payload),
                is_extended_id=extended,
                is_remote_frame=remote,
                is_fd=fd,
                bitrate_switch=brs,
                dlc=dlc,
                check=check,
            )
        except ValueError as exc:
            raise CanConfigError(
                f"메시지 생성 실패 (id=0x{arb_id:X}, len={len(payload)}, "
                f"extended={extended}, fd={fd}, brs={brs}): {exc}"
            ) from exc

    @staticmethod
    def _pad_fd(payload: bytearray, pad_value: int) -> bytearray:
        """FD가 실제로 전송할 수 있는 길이까지 패딩한다 (9~11바이트 같은 길이는 없다)."""
        length = len(payload)
        if length in FD_LENGTHS:
            return payload
        for valid in FD_LENGTHS:
            if valid > length:
                return payload + bytearray([pad_value] * (valid - length))
        return payload  # 64 초과는 그대로 두고 check=True가 잡게 한다

    def send(
        self,
        arb_id_or_msg: int | can.Message,
        data: bytes | Sequence[int] | None = None,
        *,
        timeout: float | None = None,
        **msg_kwargs: Any,
    ) -> can.Message:
        """단일 프레임을 전송하고 실제로 보낸 Message 객체를 반환한다.

        timeout=None이면 ``SEND_TIMEOUT``(기본 1초)을 쓴다. python-can의 기본값은
        무한 대기라, TX 버퍼가 가득 찬 bus-off 채널에서 테스트가 영구 정지한다.
        정말로 무한 대기가 필요하면 ``float("inf")`` 를 넘긴다.

        전송에 성공하면 비어 있던 ``msg.timestamp`` 에 호스트 시각을 채워 넣는다
        (수신 프레임과 달리 송신 프레임은 백엔드가 채워주지 않는다).
        """
        if isinstance(arb_id_or_msg, can.Message):
            msg = arb_id_or_msg
        else:
            msg = self.build_message(arb_id_or_msg, data, **msg_kwargs)

        bus = self.bus
        effective_timeout = self.SEND_TIMEOUT if timeout is None else timeout

        with self._tx_lock:
            try:
                bus.send(msg, timeout=effective_timeout)
            except can.CanError as exc:
                with self._stats_lock:
                    self._stats.send_errors += 1
                raise CanSendError(
                    f"{self.name}: 전송 실패 (id=0x{msg.arbitration_id:X}): {exc}"
                ) from exc

        now = time.time()
        # 송신 프레임은 백엔드가 timestamp를 채워주지 않는다(수신 프레임과 달리).
        # 비어 있으면 호스트 시각을 넣어 트레이스가 0.0000으로 찍히지 않게 한다.
        if not msg.timestamp:
            msg.timestamp = now
        msg.is_rx = False  # python-can 기본값은 True — 그대로 두면 트레이스에 Rx 로 찍힌다
        with self._stats_lock:
            self._stats.tx_count += 1
            self._stats.last_tx_ts = now

        self._feed_trace_tx(msg)
        self._safe_hook("on_send", self.on_send, msg)
        return msg

    def send_many(
        self,
        msgs: Iterable[can.Message],
        *,
        gap: float = 0.0,
        timeout: float | None = None,
    ) -> int:
        """여러 프레임을 순차 전송하고 성공한 개수를 반환한다."""
        sent = 0
        for msg in msgs:
            self.send(msg, timeout=timeout)
            sent += 1
            if gap:
                time.sleep(gap)
        return sent

    # ------------------------------------------------------------ 주기 전송
    def send_periodic(
        self,
        key: str,
        msgs: can.Message | Sequence[can.Message],
        period: float,
        *,
        duration: float | None = None,
        autostart: bool = False,
        modifier_callback: Callable[[can.Message], None] | None = None,
    ) -> can.broadcastmanager.CyclicSendTaskABC:
        """이름(key)을 붙여 주기 전송 태스크를 만든다.

        autostart 기본값이 python-can과 반대로 False다. True면 페이로드를 채우기 전에
        첫 프레임이 나가는 경쟁 상태가 생기므로, :meth:`start_periodic` 으로 명시 시작한다.

        주기 프레임도 :meth:`send` 와 같은 길로 나간다 — 트레이스·통계·``on_send`` 에 남고,
        송신이 실패해도 태스크가 죽지 않고 다음 주기에 다시 보낸다. python-can 기본 스레드는
        ``bus.send`` 예외 한 번에 조용히 끝나서, 레스트버스 메시지 하나가 소리 없이 끊겼다.

        예외: 백엔드가 주기 전송을 직접 하고(하드웨어·커널 타이머) ``modifier_callback`` 이
        없으면 백엔드에 맡긴다. 이 경우 송신은 트레이스·통계에 남지 않는다.
        """
        bus = self.bus
        with self._tx_lock:
            # 같은 key를 재사용하면서 기존 태스크를 멈추지 않으면 버스 부하가 조용히 2배가 된다.
            self.stop_periodic(key)
            if self._backend_schedules(bus, modifier_callback):
                task = bus.send_periodic(
                    msgs,
                    period,
                    duration=duration,
                    store_task=True,
                    autostart=autostart,
                    modifier_callback=modifier_callback,
                )
            else:
                sender = _PeriodicSender(self, key)
                task = can.broadcastmanager.ThreadBasedCyclicSendTask(
                    sender,  # type: ignore[arg-type]  # send() 만 쓰는 창구
                    self._periodic_send_lock,
                    msgs,
                    period,
                    duration=duration,
                    on_error=sender.on_error,
                    autostart=False,
                    modifier_callback=modifier_callback,
                )
                sender.task = task
                if autostart:
                    task.start()
            self._periodic[key] = task
        return task

    @staticmethod
    def _backend_schedules(bus: Any, modifier_callback: Any) -> bool:
        """백엔드가 주기 전송을 직접 하는가 (하드웨어·커널 타이머). 기본 스레드면 False."""
        if modifier_callback is not None:
            return False  # 매번 데이터를 바꾸려면 어차피 스레드가 보낸다
        backend = type(getattr(bus, "__wrapped__", bus))  # ThreadSafeBus 는 프록시다
        impl = getattr(backend, "_send_periodic_internal", None)
        return impl is not None and impl is not can.BusABC._send_periodic_internal

    def start_periodic(self, key: str) -> bool:
        """생성된 주기 전송 태스크를 시작한다. 없으면 False."""
        with self._tx_lock:
            task = self._periodic.get(key)
            if task is None:
                return False
            if isinstance(task, can.broadcastmanager.RestartableCyclicTaskABC):
                task.start()
                return True
        self.log.warning("'%s' 태스크는 재시작을 지원하지 않는 백엔드입니다.", key)
        return False

    def modify_periodic(
        self, key: str, msgs: can.Message | Sequence[can.Message]
    ) -> bool:
        """주기 전송 데이터를 갱신한다.

        백엔드가 ``ModifiableCyclicTaskABC`` 를 지원하지 않으면 태스크를 재생성해
        대체하고 False를 반환한다(전송에 짧은 공백이 생겼음을 호출자가 알 수 있도록).
        """
        with self._tx_lock:
            task = self._periodic.get(key)
            if task is None:
                raise CanConfigError(f"'{key}' 이름의 주기 전송 태스크가 없습니다.")
            if isinstance(task, can.ModifiableCyclicTaskABC):
                task.modify_data(msgs)
                return True

            period = getattr(task, "period", None)
            if period is None:
                raise CanConfigError(
                    f"'{key}' 태스크는 데이터 수정도 재생성도 불가능합니다."
                )
            self.log.debug("'%s'는 modify_data 미지원 → 재생성으로 대체합니다.", key)
            self.send_periodic(key, msgs, period, autostart=True)
            return False

    def stop_periodic(self, key: str) -> bool:
        """지정한 주기 전송을 중지하고 등록을 해제한다."""
        with self._tx_lock:
            task = self._periodic.pop(key, None)
        if task is None:
            return False
        try:
            task.stop()
        except Exception:
            self.log.debug("'%s' 주기 전송 중지 실패", key, exc_info=True)
        return True

    def stop_all_periodic(self) -> None:
        """등록된 모든 주기 전송을 중지한다."""
        with self._tx_lock:
            keys = list(self._periodic)
        for key in keys:
            self.stop_periodic(key)

    @property
    def periodic_keys(self) -> tuple[str, ...]:
        """현재 등록된 주기 전송 key 목록."""
        with self._tx_lock:
            return tuple(self._periodic)

    def flush_tx(self) -> bool:
        """TX 버퍼 비우기를 시도한다. 백엔드가 지원하지 않으면 False.

        많은 백엔드가 ``NotImplementedError`` 를 던지므로 날것으로 노출하지 않는다.
        """
        bus = self.bus  # 미연결이면 CanNotConnectedError가 그대로 올라간다
        try:
            bus.flush_tx_buffer()
            return True
        except (NotImplementedError, can.CanError) as exc:
            self.log.debug("flush_tx_buffer 미지원: %s", exc)
            return False

    # ============================================================ 수신 (RX)
    def _on_frame(self, msg: can.Message) -> None:
        """디스패처가 넘긴 프레임을 팬아웃한다 (**수신 스레드**에서 실행)."""
        now = msg.timestamp or time.time()
        with self._stats_lock:
            self._stats.rx_count += 1
            self._stats.last_rx_ts = now
            if self._stats.first_rx_ts is None:
                self._stats.first_rx_ts = now
            if msg.is_error_frame:
                self._stats.error_frames += 1

        # 링버퍼: 가득 차면 deque가 조용히 오래된 것을 버리므로 직접 세어 눈에 보이게 한다.
        with self._buffer_cond:
            if self._buffer.maxlen and len(self._buffer) == self._buffer.maxlen:
                with self._stats_lock:
                    self._stats.dropped += 1
            self._buffer.append(msg)
            self._buffer_cond.notify()

        self._evaluate_waiters(msg)

        self._safe_hook("on_message", self.on_message, msg)
        if msg.is_error_frame:
            self._safe_hook("on_error_frame", self.on_error_frame, msg)

        # 사용자 리스너: 하나가 터져도 나머지와 수신 자체는 계속되어야 한다.
        with self._rx_lock:
            listeners = list(self._listeners.values())
        for listener in listeners:
            try:
                if isinstance(listener, can.Listener):
                    listener.on_message_received(msg)
                else:
                    listener(msg)
            except Exception as exc:
                with self._stats_lock:
                    self._stats.listener_errors += 1
                self.log.warning("리스너 예외: %s", exc, exc_info=True)
                self._safe_hook("on_listener_error", self.on_listener_error, exc)

    def _evaluate_waiters(self, msg: can.Message) -> None:
        """대기자들에게 프레임을 제시한다.

        술어는 임의의 사용자 코드이므로 **락을 놓은 상태에서** 평가한다
        (락을 쥔 채 부르면 술어가 buffer_len 등을 만질 때 데드락).
        """
        with self._rx_lock:
            waiters = list(self._waiters)
        if not waiters:
            return

        finished = []
        for waiter in waiters:
            try:
                if waiter._offer(msg):
                    finished.append(waiter)
            except Exception as exc:
                self.log.warning("대기 조건 평가 중 예외: %s", exc, exc_info=True)
                finished.append(waiter)

        if finished:
            with self._rx_lock:
                for waiter in finished:
                    if waiter in self._waiters:
                        self._waiters.remove(waiter)

    def _on_rx_error(self, exc: Exception) -> None:
        """수신 스레드에서 올라온 예외를 기록한다."""
        with self._stats_lock:
            self._stats.listener_errors += 1
        self.log.error("수신 스레드 예외: %s", exc, exc_info=exc)
        self._safe_hook("on_listener_error", self.on_listener_error, exc)

    def _safe_hook(self, name: str, fn: Callable[..., Any], *args: Any) -> None:
        """훅 호출을 감싼다. 훅의 예외가 수신을 죽이면 안 된다."""
        try:
            fn(*args)
        except Exception:
            self.log.warning("훅 '%s' 실행 중 예외", name, exc_info=True)

    # ------------------------------------------------------------ 리스너 레지스트리
    def add_listener(
        self,
        listener: can.Listener | Callable[[can.Message], Any],
        *,
        name: str | None = None,
    ) -> str:
        """수신 리스너를 등록하고 해제용 핸들을 반환한다.

        Notifier가 아니라 CanBase가 레지스트리를 소유하므로, disconnect 후에도
        등록이 유지되어 :meth:`reconnect` 시 그대로 살아난다.
        """
        with self._rx_lock:
            self._listener_seq += 1
            handle = name or f"listener-{self._listener_seq}"
            self._listeners[handle] = listener
        return handle

    def remove_listener(self, handle: str) -> bool:
        """핸들로 리스너를 해제한다."""
        with self._rx_lock:
            return self._listeners.pop(handle, None) is not None

    def clear_listeners(self) -> None:
        """등록된 사용자 리스너를 모두 해제한다."""
        with self._rx_lock:
            self._listeners.clear()

    @property
    def listener_handles(self) -> tuple[str, ...]:
        """등록된 리스너 핸들 목록."""
        with self._rx_lock:
            return tuple(self._listeners)

    # ------------------------------------------------------------ 버퍼
    def recv(self, timeout: float | None = 1.0) -> can.Message | None:
        """내부 수신 버퍼에서 프레임 하나를 꺼낸다.

        ``bus.recv()`` 는 **절대 호출하지 않는다.** Notifier와 경쟁하면
        프레임을 서로 빼앗기 때문이다.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._buffer_cond:
            while not self._buffer:
                if deadline is None:
                    self._buffer_cond.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._buffer_cond.wait(remaining)
            return self._buffer.popleft()

    def drain(self, max_count: int | None = None) -> list[can.Message]:
        """수신 버퍼에 쌓인 프레임을 모두(또는 max_count만큼) 꺼내 반환한다."""
        with self._buffer_cond:
            if max_count is None:
                messages = list(self._buffer)
                self._buffer.clear()
                return messages
            messages = []
            while self._buffer and len(messages) < max_count:
                messages.append(self._buffer.popleft())
            return messages

    def clear_buffer(self) -> int:
        """수신 버퍼를 비우고 버린 프레임 수를 반환한다."""
        with self._buffer_cond:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    @property
    def buffer_len(self) -> int:
        """현재 수신 버퍼에 쌓인 프레임 수."""
        with self._buffer_cond:
            return len(self._buffer)

    # ------------------------------------------------------------ 필터
    def set_filters(self, filters: list[dict] | None) -> None:
        """하드웨어/커널 레벨 수신 필터를 설정한다. None이면 해제한다."""
        self._filters = list(filters) if filters else None
        if self._bus is not None:
            self._bus.set_filters(self._filters)

    def filter_ids(
        self,
        ids: Iterable[int],
        *,
        extended: bool | None = None,
        mask: int | None = None,
    ) -> None:
        """CAN ID 목록으로 필터를 새로 구성한다 (기존 필터는 대체된다)."""
        extended = self.DEFAULT_EXTENDED_ID if extended is None else extended
        if mask is None:
            mask = EXT_MASK if extended else STD_MASK
        self.set_filters(
            [{"can_id": i, "can_mask": mask, "extended": extended} for i in ids]
        )

    def add_filter_id(
        self, arb_id: int, *, extended: bool | None = None, mask: int | None = None
    ) -> None:
        """기존 필터를 유지한 채 ID 하나를 추가한다.

        필터를 가산적으로 다룰 수 있어야 하는 이유: 앱 ID만 필터링해 둔 상태에서
        UDS를 열면 ECU 응답 ID가 하드웨어 필터에서 잘려 아무 단서 없이 타임아웃한다.
        """
        if self._filters is None:
            self.log.debug("필터가 설정되어 있지 않아 추가할 필요가 없습니다.")
            return
        extended = self.DEFAULT_EXTENDED_ID if extended is None else extended
        if mask is None:
            mask = EXT_MASK if extended else STD_MASK
        entry = {"can_id": arb_id, "can_mask": mask, "extended": extended}
        if entry not in self._filters:
            self.set_filters(self._filters + [entry])

    def _reapply_filters(self) -> None:
        """reconnect 후 캐시해 둔 필터를 다시 적용한다."""
        if self._filters and self._bus is not None:
            self._bus.set_filters(self._filters)

    @property
    def filters(self) -> list[dict] | None:
        """현재 적용된 필터(복사본)."""
        return list(self._filters) if self._filters else None

    # ------------------------------------------------------------ 대기 헬퍼
    @staticmethod
    def _as_predicate(match: Any) -> Callable[[can.Message], bool]:
        """int / (id, mask) / 호출가능 객체를 술어 함수로 정규화한다."""
        if callable(match):
            return match
        if isinstance(match, tuple):
            arb_id, mask = match
            return lambda m: (m.arbitration_id & mask) == (arb_id & mask)
        if isinstance(match, int):
            return lambda m: m.arbitration_id == match
        raise CanConfigError(
            f"match는 int, (id, mask) 튜플, 또는 호출 가능 객체여야 합니다: {match!r}"
        )

    def arm(
        self,
        match: Any,
        *,
        count: int = 1,
        rx_only: bool = True,
    ) -> CanWaiter:
        """수신 대기 조건을 **전송 전에** 등록한다.

        ``send()`` 후에 ``wait_for()`` 를 부르면 그 사이에 도착한 응답을 놓친다.
        with 문과 함께 쓰거나 :meth:`request` 를 사용한다.
        """
        waiter = CanWaiter(self, self._as_predicate(match), count, rx_only)
        with self._rx_lock:
            self._waiters.append(waiter)
        return waiter

    def _unregister_waiter(self, waiter: CanWaiter) -> None:
        with self._rx_lock:
            if waiter in self._waiters:
                self._waiters.remove(waiter)

    def _release_all_waiters(self) -> None:
        with self._rx_lock:
            waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            waiter._release()

    def wait_for(
        self,
        match: Any,
        *,
        timeout: float | None = 1.0,
        rx_only: bool = True,
        search_buffer: bool = False,
    ) -> can.Message | None:
        """조건에 맞는 프레임을 기다린다. 못 받으면 None.

        요청-응답에는 :meth:`request` 를 쓴다. 이 메서드는 비요청 트래픽을
        기다릴 때 사용한다.
        """
        predicate = self._as_predicate(match)

        if search_buffer:
            with self._buffer_cond:
                for msg in self._buffer:
                    if (not rx_only or msg.is_rx) and predicate(msg):
                        return msg

        with self.arm(predicate, rx_only=rx_only) as waiter:
            return waiter.wait(timeout)

    def expect(self, match: Any, *, timeout: float | None = 1.0, **kw: Any) -> can.Message:
        """:meth:`wait_for` 와 같지만 타임아웃 시 :class:`CanReceiveTimeout` 을 던진다."""
        self.raise_if_rx_dead()
        msg = self.wait_for(match, timeout=timeout, **kw)
        if msg is None:
            self.raise_if_rx_dead()
            raise CanReceiveTimeout(
                f"{self.name}: {timeout}초 안에 조건에 맞는 프레임을 받지 못했습니다 "
                f"(match={match!r})."
            )
        return msg

    def request(
        self,
        request: can.Message | int,
        match: Any,
        *,
        data: bytes | Sequence[int] | None = None,
        timeout: float = 1.0,
        rx_only: bool = True,
        **msg_kwargs: Any,
    ) -> can.Message | None:
        """응답 조건을 먼저 등록한 뒤 요청을 전송하고 응답을 기다린다.

        **요청-응답에는 이 메서드를 쓴다.** ``send()`` 후 ``wait_for()`` 는
        그 사이에 도착한 빠른 응답을 놓치는 경쟁 상태가 있다(실제로 간헐 실패한다).
        """
        with self.arm(match, rx_only=rx_only) as waiter:
            self.send(request, data, **msg_kwargs)
            return waiter.wait(timeout)

    # ============================================================ 트레이스
    def start_trace(
        self,
        filename: str | None = None,
        *,
        directory: str | None = None,
        rotate_bytes: int = 0,
        append: bool = False,
        trace_tx: bool = True,
    ) -> str:
        """송수신 프레임을 파일로 기록하기 시작하고 실제 파일 경로를 반환한다.

        trace_tx=True면 :meth:`send` (주기 전송 포함)가 writer에 직접 프레임을 먹인다.
        ``receive_own_messages=False`` 이면 자기 송신이 수신되지 않아 트레이스에 남지
        않기 때문이다. 단 이 경우 타임스탬프는 하드웨어 시각이 아니라 호스트 시각이라
        수신 프레임과 완벽히 인터리브되지는 않는다.

        이때 수신 쪽으로 돌아오는 자기 송신 에코(``is_rx=False``)는 기록하지 않는다 —
        같은 프레임이 두 번 찍히지 않게. 에코는 비동기라 기다려야 하지만 직접 기록은
        :meth:`send` 가 끝나는 순간 남는다.
        """
        if self._trace_writer is not None:
            raise CanConfigError(f"{self.name}: 이미 트레이스가 진행 중입니다.")

        path = self._resolve_trace_path(filename, directory)
        self._validate_trace_suffix(path)

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        if rotate_bytes > 0:
            writer = can.SizedRotatingLogger(base_filename=path, max_bytes=rotate_bytes)
        else:
            writer = can.Logger(path, append=append)

        # writer는 우리 레지스트리가 아니라 Notifier에 직접 붙인다.
        # 그래야 notifier.stop()이 리스너 stop()을 부르며 자연스럽게 flush된다.
        listener = _RxOnly(writer) if trace_tx else writer
        self.notifier.add_listener(listener)
        self._trace_writer = writer
        self._trace_listener = listener
        self._trace_path = path
        self._trace_tx = trace_tx
        self.log.info("트레이스 시작: %s", path)
        return path

    def _resolve_trace_path(self, filename: str | None, directory: str | None) -> str:
        if filename and os.path.isabs(filename):
            return filename
        folder = directory or self.TRACE_DIR
        if filename:
            return os.path.join(folder, filename)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(folder, f"{self.name}_{stamp}{self.TRACE_SUFFIX}")

    @staticmethod
    def _validate_trace_suffix(path: str) -> None:
        """python-can이 처리할 수 있는 확장자인지 미리 확인한다."""
        base, suffix = os.path.splitext(path)
        gzipped = suffix == ".gz"
        if gzipped:
            suffix = os.path.splitext(base)[1]
        if suffix not in _TRACE_SUFFIXES:
            raise CanConfigError(
                f"지원하지 않는 트레이스 확장자입니다: {suffix!r}. "
                f"사용 가능: {', '.join(_TRACE_SUFFIXES)}"
            )
        if gzipped and suffix in _NO_GZIP_SUFFIX:
            raise CanConfigError(f"python-can은 {suffix}.gz 압축을 지원하지 않습니다.")

    def stop_trace(self) -> str | None:
        """트레이스를 종료하고 flush한 뒤 파일 경로를 반환한다. 중복 호출은 no-op."""
        writer, self._trace_writer = self._trace_writer, None
        path, self._trace_path = self._trace_path, None
        if writer is None:
            return None

        listener, self._trace_listener = self._trace_listener, None
        if self._notifier is not None:
            try:
                self._notifier.remove_listener(listener)
            except (ValueError, KeyError):
                pass  # 이미 제거됨
        try:
            writer.stop()
        except Exception:
            self.log.debug("트레이스 writer 종료 실패", exc_info=True)

        self.log.info("트레이스 종료: %s", path)
        return path

    @property
    def is_tracing(self) -> bool:
        """트레이스 기록 중인지 여부."""
        return self._trace_writer is not None

    @property
    def trace_path(self) -> str | None:
        """현재 트레이스 파일 경로."""
        return self._trace_path

    def _feed_trace_tx(self, msg: can.Message) -> None:
        """송신 프레임을 트레이스 writer에 직접 먹인다."""
        writer = self._trace_writer
        if writer is None or not self._trace_tx:
            return
        try:
            writer.on_message_received(msg)
        except Exception:
            self.log.debug("트레이스 TX 기록 실패", exc_info=True)

    def play_trace(
        self,
        path: str,
        *,
        realtime: bool = True,
        skip: float = 60.0,
        id_map: dict[int, int] | None = None,
    ) -> int:
        """저장된 트레이스 파일을 재생 전송하고 전송한 프레임 수를 반환한다."""
        reader = can.LogReader(path)
        source: Iterable[can.Message] = (
            can.MessageSync(reader, timestamps=realtime, skip=skip) if realtime else reader
        )
        sent = 0
        try:
            for msg in source:
                if msg.is_error_frame:
                    continue
                if id_map and msg.arbitration_id in id_map:
                    msg = can.Message(
                        arbitration_id=id_map[msg.arbitration_id],
                        data=msg.data,
                        is_extended_id=msg.is_extended_id,
                        is_fd=msg.is_fd,
                        bitrate_switch=msg.bitrate_switch,
                    )
                self.send(msg)
                sent += 1
        finally:
            reader.stop()
        return sent

    # ============================================================ 진단 / 헬스
    @property
    def stats(self) -> CanStats:
        """통계 스냅샷(복사본)을 반환한다."""
        with self._stats_lock:
            return replace(self._stats)

    def reset_stats(self) -> None:
        """통계 카운터를 초기화한다 (connected_at은 유지)."""
        with self._stats_lock:
            connected_at = self._stats.connected_at
            self._stats = CanStats(connected_at=connected_at)

    def get_state(self) -> can.BusState | None:
        """버스 상태를 조회한다. 백엔드가 지원하지 않으면 None.

        ``bus.state`` 는 백엔드에 따라 ``NotImplementedError`` 를 던지므로
        날것으로 노출하지 않는다.
        """
        if self._bus is None:
            return None
        try:
            return self._bus.state
        except (NotImplementedError, can.CanError, AttributeError) as exc:
            self.log.debug("버스 상태 조회 미지원: %s", exc)
            return None

    def check_rx_alive(self, max_silence: float = 5.0) -> bool:
        """마지막 수신 이후 경과 시간이 임계값 이내인지 확인한다."""
        with self._stats_lock:
            last = self._stats.last_rx_ts
        if last is None:
            return False
        return (time.time() - last) <= max_silence

    def notifier_exception(self) -> Exception | None:
        """Notifier 수신 스레드에서 마지막으로 발생한 예외.

        수신이 죽었음을 알아챌 수 있는 사실상 유일한 수단이다.
        """
        if self._notifier is None:
            return None
        return getattr(self._notifier, "exception", None)

    def raise_if_rx_dead(self) -> None:
        """수신 스레드가 예외로 죽었으면 :class:`CanReceiveError` 를 던진다."""
        exc = self.notifier_exception()
        if exc is not None:
            raise CanReceiveError(
                f"{self.name}: 수신 스레드가 예외로 중단되었습니다: {exc}"
            ) from exc

    def health(self) -> dict[str, Any]:
        """연결 상태/버스 상태/통계/예외를 한 dict로 모은다 (로그·리포트용)."""
        stats = self.stats
        state = self.get_state()
        return {
            "name": self.name,
            "product": self.PRODUCT_NAME,
            "connected": self.is_connected,
            "interface": self._config.interface,
            "channel": self._config.channel,
            "mode": self._config.mode.value,
            "bus_state": state.name if state else None,
            "tx_count": stats.tx_count,
            "rx_count": stats.rx_count,
            "error_frames": stats.error_frames,
            "dropped": stats.dropped,
            "listener_errors": stats.listener_errors,
            "send_errors": stats.send_errors,
            "rx_rate": round(stats.rx_rate, 1),
            "rx_alive": self.check_rx_alive(),
            "buffer_len": self.buffer_len,
            "periodic": list(self.periodic_keys),
            "tracing": self._trace_path,
            "rx_exception": repr(self.notifier_exception()),
        }

    # ============================================================ 자식 클래스 훅
    # 모두 no-op 기본 구현이다. 필요한 것만 오버라이드하면 된다.

    def on_before_connect(self, config: CanConfig) -> CanConfig | None:
        """버스 생성 직전. 수정한 CanConfig를 반환하면 그것이 사용된다."""
        return None

    def on_after_connect(self) -> None:
        """Notifier 가동 후. 웨이크업 프레임 전송, 필터 설정, 하트비트 시작 등."""

    def on_before_disconnect(self) -> None:
        """종료 직전. 슬립 프레임 전송, 주기 전송 중지 등."""

    def on_after_disconnect(self) -> None:
        """버스가 닫힌 후. 제품 상태 정리."""

    def on_message(self, msg: can.Message) -> None:
        """모든 수신 프레임. **수신 스레드에서 실행되므로 빠르게 끝나야 하고
        send()/wait_for()/disconnect()를 호출하면 안 된다.**"""

    def on_error_frame(self, msg: can.Message) -> None:
        """에러 프레임 수신. **수신 스레드에서 실행된다.**"""

    def on_listener_error(self, exc: Exception) -> None:
        """리스너/수신 스레드에서 예외 발생. **수신 스레드에서 실행된다.**"""

    def on_send(self, msg: can.Message) -> None:
        """전송 성공 직후. 호출자 스레드에서 실행된다."""

    def describe(self) -> dict[str, Any]:
        """리포트용 제품 식별 정보."""
        return {
            "product": self.PRODUCT_NAME,
            "name": self.name,
            "interface": self._config.interface,
            "channel": self._config.channel,
            "mode": self._config.mode.value,
            "bitrate": self._config.bitrate,
            "data_bitrate": self._config.data_bitrate if self._config.mode.is_fd else None,
        }

    # ============================================================ 확장점 (DBC / UDS)
    @property
    def dbc(self) -> Any:
        """DBC_PATH 의 :class:`CanDbc.CanDbc` (처음 쓸 때 한 번 읽는다).

        DBC_PATH 가 없거나 cantools 가 없거나 파일을 못 읽으면 CanDbcError.
        """
        if self._dbc is None:
            from CanErrors import CanDbcError

            if not self.DBC_PATH:
                raise CanDbcError(
                    f"{self.name}: DBC_PATH 가 없습니다. 클래스 속성에 DBC 경로를 적거나 "
                    "CanDbc.load() 로 따로 만들어 쓰세요."
                )
            from CanDbc import CanDbc

            self._dbc = CanDbc.load(self.DBC_PATH)
        return self._dbc

    @property
    def uds(self) -> Any:
        """UDS 헬퍼 (다음 단계에서 구현). 지금은 항상 CanUdsError."""
        from CanErrors import CanUdsError

        raise CanUdsError(
            "UDS 레이어는 아직 구현되지 않았습니다. "
            'uv pip install "can-isotp==2.0.7" "udsoncan==1.26.1" 후 '
            "CanUds.py를 추가하세요."
        )
