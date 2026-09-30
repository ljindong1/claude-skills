"""노드 송신 점검 — 한 노드(ECU)가 실제로 보내는 프레임이 DBC대로인지 판정한다 (제품 무관).

한 노드(ECU)가 보내야 하는 메시지를 DBC에서 뽑아 두고, 실제로 받은 프레임과
메시지별로 비교한다.

    >>> dbc = CanDbc.load("Local_PSU_DRV.dbc")
    >>> check = CanNodeTxCheck(dbc, "GW_PSU_DRV_FD")
    >>> bus.add_listener(check)          # CanBase 에 붙이면 받는 즉시 기록한다
    >>> time.sleep(10)
    >>> print(check.report().text())

저장해 둔 로그 파일도 같은 방법으로 판정한다.

    >>> check.feed(can.LogReader("trace.blf"))

판정 항목
---------
* **수신 여부** — 주기 메시지가 하나도 안 오면 실패. 이벤트·NM 메시지는 조건이
  없으면 안 오는 것이 정상일 수 있어 "정보"로만 남긴다.
* **길이** — DBC 길이와 다르면 실패.
* **형식** — DBC 는 CAN FD 인데 Classic 으로 오거나 그 반대면 실패. 8바이트 이하
  메시지는 길이만으로는 구분되지 않는다.
* **주기** — 평균 간격이 기준 ±허용오차(기본 10%)를 벗어나면 실패.
  평균은 맞는데 기준의 1.5배를 넘는 간격이 있으면 "주의" (한두 프레임 빠진 것).
* **카운터** — 한 값에 멈춰 있거나, 1씩 오르지 않고 건너뛰면 실패.
  최댓값에서 최솟값으로 돌아가는 것은 정상으로 본다 (0~14 에서 도는 카운터도 있다).
  건너뛴 자리에서 간격도 벌어졌다면 프레임이 빠진 것이라 "주의"로 둔다 — DUT 가
  안 보냈는지 이쪽이 놓쳤는지는 여기서 가릴 수 없다. 간격은 정상인데 건너뛰면 실패.
* **CRC** — ``e2e=`` 로 방식(예: :class:`CanE2E.HkmcE2E`)을 주면, 그 배치를 따르는
  메시지의 CRC 가 하나라도 틀리면 실패. 주지 않으면 보지 않는다 (계산식이 DBC에 없다).

DBC 하나 = 버스 하나다. 버스가 둘이면 CanNodeTxCheck 도 둘을 만든다.

문제가 있으면 이유에 **처음 발생한 시각**을 붙인다 (첫 프레임부터 잰 초). 트레이스에서
그 자리를 찾아보면 된다.

기록 방식
    프레임을 쌓아 두지 않고 메시지마다 누적값(개수·간격·카운터 전후 값 등)만 갱신한다.
    몇 시간을 받아도 메모리가 늘지 않고, :meth:`CanNodeTxCheck.report` 는 언제 불러도
    메시지 수에 비례하는 만큼만 일한다.

수신 스레드 주의
    :meth:`CanNodeTxCheck.on_message_received` 는 수신 스레드에서 돈다. 그래서 여기서는
    cantools 디코딩을 하지 않는다 — 카운터는 비트 자리에서 바로 꺼내고, CRC 는 E2E 방식이
    계산한다. 판정(허용오차 비교, 카운터 복귀 판단)은 :meth:`CanNodeTxCheck.report` 에서 한다.
"""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Iterable

import can

from CanDbc import CanDbc, MessageSpec, SignalLayout, _pad
from CanErrors import CanConfigError
from can_log import CanLogger

if TYPE_CHECKING:  # 타입 표기에만 쓴다 - 실행에는 CanE2E 가 필요 없다
    from CanE2E import E2EBinding, E2EProfile

__all__ = ["CanNodeTxCheck", "CheckReport", "MessageResult", "Verdict"]

log = CanLogger.get("CanNodeTxCheck")

#: 평균 주기는 맞는데 이 배수를 넘는 간격이 있으면 "주의" (프레임이 빠졌다는 뜻)
GAP_FACTOR = 1.5


def _counter_raw(data: bytes, layout: SignalLayout) -> int | None:
    """신호 자리에서 raw 값(부호 없음)을 꺼낸다. 데이터가 모자라면 None."""
    if layout.last_byte >= len(data):
        return None
    chunk = bytes(data[layout.first_byte : layout.last_byte + 1])
    if layout.little_endian:
        value = int.from_bytes(chunk, "little") >> (layout.lsb - layout.first_byte * 8)
    else:
        value = int.from_bytes(chunk, "big") >> ((layout.last_byte - layout.lsb // 8) * 8 + layout.lsb % 8)
    return value & ((1 << layout.length) - 1)


class _CounterTrack:
    """카운터 신호 하나의 누적값."""

    __slots__ = ("layout", "modulus", "last", "lo", "hi", "n", "steps")

    def __init__(self, layout: SignalLayout) -> None:
        self.layout = layout
        self.modulus = 1 << layout.length
        self.last = 0
        self.lo = self.hi = 0
        self.n = 0
        #: 1씩 오르지 않은 걸음 (이전 값, 다음 값, 간격 벌어짐) → [횟수, 처음 시각].
        #: 크기는 값 조합 수로 정해진다 — 프레임 수와 무관하다
        self.steps: dict[tuple[int, int, bool], list[float]] = {}

    def add(self, value: int, ts: float, long_gap: bool) -> None:
        if self.n == 0:
            self.lo = self.hi = value
        else:
            self.lo, self.hi = min(self.lo, value), max(self.hi, value)
            if (value - self.last) % self.modulus != 1:
                step = self.steps.get((self.last, value, long_gap))
                if step is None:
                    self.steps[(self.last, value, long_gap)] = [1, ts]
                else:
                    step[0] += 1
        self.last = value
        self.n += 1

    def copy(self) -> _CounterTrack:
        c = _CounterTrack(self.layout)
        c.last, c.lo, c.hi, c.n = self.last, self.lo, self.hi, self.n
        c.steps = {k: list(v) for k, v in self.steps.items()}
        return c


class _Track:
    """메시지 하나의 누적값. 수신 스레드가 갱신하고 report() 가 읽는다 (둘 다 잠금 안에서)."""

    __slots__ = (
        "count", "first_ts", "last_ts", "gap_min", "gap_max", "long_gaps", "long_gap_at",
        "wrong_len", "wrong_len_at", "wrong_fmt", "wrong_fmt_at",
        "crc_checked", "crc_bad", "crc_bad_at", "counters",
    )

    def __init__(self, counters: dict[str, SignalLayout]) -> None:
        self.count = 0
        self.first_ts = self.last_ts = 0.0
        self.gap_min = self.gap_max = 0.0
        self.long_gaps = 0
        self.long_gap_at: float | None = None
        self.wrong_len: Counter[int] = Counter()
        self.wrong_len_at: float | None = None
        self.wrong_fmt = 0
        self.wrong_fmt_at: float | None = None
        self.crc_checked = self.crc_bad = 0
        self.crc_bad_at: float | None = None
        self.counters = {name: _CounterTrack(layout) for name, layout in counters.items()}

    def copy(self) -> _Track:
        """report() 용 사본 — 판정하는 동안 수신이 계속되어도 흔들리지 않게."""
        t = _Track({})
        for name in _Track.__slots__:
            setattr(t, name, getattr(self, name))
        t.wrong_len = Counter(self.wrong_len)
        t.counters = {name: c.copy() for name, c in self.counters.items()}
        return t


class Verdict(Enum):
    """판정. 값은 화면에 쓰는 말이다."""

    PASS = "통과"
    INFO = "정보"
    WARN = "주의"
    FAIL = "실패"

    @property
    def rank(self) -> int:
        """심각도. 클수록 나쁘다."""
        return list(Verdict).index(self)


@dataclass
class MessageResult:
    """메시지 하나의 판정 결과."""

    spec: MessageSpec
    count: int
    verdict: Verdict = Verdict.PASS
    mean_ms: float | None = None
    min_ms: float | None = None
    max_ms: float | None = None
    reasons: list[str] = field(default_factory=list)

    def add(self, verdict: Verdict, reason: str) -> None:
        """이유를 붙이고, 더 나쁜 판정이면 올린다."""
        self.reasons.append(reason)
        if verdict.rank > self.verdict.rank:
            self.verdict = verdict


@dataclass
class CheckReport:
    """판정 결과 전체."""

    bus: str
    node: str
    window_s: float  #: 판정에 쓴 시간 (첫 프레임 ~ 마지막 프레임)
    cycle_tol: float
    results: list[MessageResult]
    unknown: dict[tuple[int, bool], int]  #: DBC에 없는 ID → 개수
    others: int  #: DBC에는 있지만 이 노드가 보내는 것이 아닌 프레임 수
    error_frames: int

    @property
    def failed(self) -> list[MessageResult]:
        return [r for r in self.results if r.verdict is Verdict.FAIL]

    @property
    def passed(self) -> bool:
        """실패가 하나도 없으면 True. 주의·정보는 통과로 본다."""
        return not self.failed

    def counts(self) -> dict[Verdict, int]:
        c = Counter(r.verdict for r in self.results)
        return {v: c.get(v, 0) for v in Verdict}

    def text(self) -> str:
        """사람이 읽는 결과표. 나쁜 것부터."""
        counts = self.counts()
        lines = [
            f"[{self.bus}]  기준 노드 {self.node}  -  {self.window_s:.1f}초 수신, "
            f"주기 허용 ±{self.cycle_tol * 100:.0f}%",
            "  " + "  ".join(f"{v.value} {counts[v]}" for v in reversed(Verdict)),
            "",
            f"  {_pad('판정', 4)}  {_pad('ID', 11)} {_pad('이름', 30)} {_pad('수신', 6, right=True)} "
            f"{_pad('평균주기', 9, right=True)} {_pad('기준', 7, right=True)}  이유",
        ]
        order = sorted(
            self.results,
            key=lambda r: (-r.verdict.rank, r.spec.extended, r.spec.frame_id),
        )
        for r in order:
            mean = f"{r.mean_ms:.1f}ms" if r.mean_ms is not None else "-"
            ref = f"{r.spec.cycle_ms}ms" if r.spec.cycle_ms else "이벤트"
            lines.append(
                f"  {_pad(r.verdict.value, 4)}  {r.spec.id_text:<11} {r.spec.name[:30]:<30} "
                f"{r.count:>6} {mean:>9} {_pad(ref, 7, right=True)}  {' / '.join(r.reasons)}"
            )

        lines.append("")
        if self.unknown:
            total = sum(self.unknown.values())
            lines.append(f"  DBC에 없는 ID {len(self.unknown)}종 {total}개 (주의)")
            for (fid, ext), n in sorted(self.unknown.items()):
                lines.append(f"    {f'0x{fid:08X}' if ext else f'0x{fid:03X}':<11} {n}개")
        if self.others:
            lines.append(f"  다른 노드 메시지 {self.others}개 (판정 대상 아님)")
        if self.error_frames:
            lines.append(f"  에러 프레임 {self.error_frames}개 (주의 - 배선·종단저항·보율·FD 설정)")
        lines.append(f"  결과: {'통과' if self.passed else '실패'}")
        return "\n".join(lines)


class CanNodeTxCheck(can.Listener):
    """한 노드가 보내는 메시지를 DBC와 대조한다.

    ``can.Listener`` 라서 :meth:`CanBase.add_listener` 에 그대로 붙는다.
    """

    def __init__(
        self,
        dbc: CanDbc,
        node: str,
        *,
        kinds: Iterable[str] = ("app", "nm"),
        cycle_tol: float = 0.10,
        settle_s: float = 0.0,
        e2e: E2EProfile | None = None,
    ) -> None:
        """
        kinds     판정할 메시지 종류. 진단(diag)은 요청이 있어야 오므로 기본에서 뺐다.
        cycle_tol 주기 허용오차 (0.10 = ±10%)
        settle_s  첫 프레임 뒤 이 시간 동안 받은 것은 버린다 (깨어나는 동안의 흔들림)
        """
        super().__init__()
        if not 0 < cycle_tol < 1:
            raise CanConfigError(f"cycle_tol 은 0과 1 사이여야 합니다: {cycle_tol}")
        if settle_s < 0:
            raise CanConfigError(f"settle_s 는 0 이상이어야 합니다: {settle_s}")

        self.dbc = dbc
        self.node = node
        self.cycle_tol = cycle_tol
        self.settle_s = settle_s
        self._expected = {s.key: s for s in dbc.tx_of(node, kinds)}  # 노드·종류 검증도 여기서
        self.e2e = e2e
        #: CRC 를 확인할 메시지 → 그 메시지 전용 E2E 보호
        self._guards: dict[tuple[int, bool], E2EBinding] = {}
        if e2e:
            for k, s in self._expected.items():
                guard = e2e.bind(dbc, s)
                if guard is not None:
                    self._guards[k] = guard
        #: key → {카운터 신호: 자리}. 수신 스레드에서 비트로 바로 꺼내려고 미리 구해 둔다
        self._counter_layouts = {
            k: {sig: dbc.signal_layout(s.name, sig) for sig in s.counter_signals}
            for k, s in self._expected.items()
        }
        self._lock = threading.Lock()
        self.reset()

    @property
    def expected(self) -> tuple[MessageSpec, ...]:
        """판정 대상 메시지."""
        return tuple(self._expected.values())

    @property
    def first_seen(self) -> float | None:
        """처음 받은 프레임의 시각 (settle 로 버린 것 포함). 아직 없으면 None.

        버스가 깨어났는지 보는 용도다. 이 노드의 메시지가 아니어도 된다.
        """
        with self._lock:
            return self._first

    def reset(self) -> None:
        """기록을 지운다."""
        with self._lock:
            #: key → 누적값
            self._tracks = {k: _Track(self._counter_layouts[k]) for k in self._expected}
            self._unknown: Counter[tuple[int, bool]] = Counter()
            self._others = 0
            self._errors = 0
            self._first: float | None = None
            self._last: float | None = None

    # ------------------------------------------------------------ 수신 (수신 스레드)
    def on_message_received(self, msg: can.Message) -> None:
        """누적값만 갱신한다. 빨리 끝나야 한다."""
        if msg.is_error_frame:
            with self._lock:
                self._errors += 1
            return
        if msg.is_remote_frame or not msg.is_rx:
            return  # 자기가 보낸 프레임은 판정 대상이 아니다

        ts = msg.timestamp
        key = (msg.arbitration_id, bool(msg.is_extended_id))
        with self._lock:
            if self._first is None:
                self._first = ts
            if ts - self._first < self.settle_s:
                return
            self._last = ts

            track = self._tracks.get(key)
            if track is not None:
                self._update(track, self._expected[key], msg, ts)
            elif self.dbc.lookup(*key) is not None:
                self._others += 1
            else:
                self._unknown[key] += 1

    def _update(self, t: _Track, spec: MessageSpec, msg: can.Message, ts: float) -> None:
        """프레임 하나를 누적값에 반영한다. 잠금 안에서 부른다."""
        data = msg.data
        long_gap = False
        if t.count:
            gap = ts - t.last_ts
            if t.count == 1:
                t.gap_min = t.gap_max = gap
            else:
                t.gap_min, t.gap_max = min(t.gap_min, gap), max(t.gap_max, gap)
            if spec.is_cyclic and gap * 1000 > spec.cycle_ms * GAP_FACTOR:
                long_gap = True
                t.long_gaps += 1
                if t.long_gap_at is None:
                    t.long_gap_at = ts
        else:
            t.first_ts = ts
        t.count += 1
        t.last_ts = ts

        if len(data) != spec.length:
            t.wrong_len[len(data)] += 1
            if t.wrong_len_at is None:
                t.wrong_len_at = ts
        if bool(msg.is_fd) != spec.is_fd:
            t.wrong_fmt += 1
            if t.wrong_fmt_at is None:
                t.wrong_fmt_at = ts
        guard = self._guards.get(spec.key)
        if guard is not None and len(data) == spec.length:
            t.crc_checked += 1
            if not guard.verify(bytes(data)):
                t.crc_bad += 1
                if t.crc_bad_at is None:
                    t.crc_bad_at = ts
        for counter in t.counters.values():
            value = _counter_raw(data, counter.layout)
            if value is not None:
                counter.add(value, ts, long_gap)

    def feed(self, messages: Iterable[can.Message]) -> int:
        """프레임 여러 개를 넣는다 (로그 파일 등). 넣은 개수를 반환한다."""
        n = 0
        for msg in messages:
            self.on_message_received(msg)
            n += 1
        return n

    def stop(self) -> None:
        """Notifier 가 끝날 때 부른다. 할 일 없음."""

    # ------------------------------------------------------------ 판정
    def report(self) -> CheckReport:
        """지금까지 받은 것으로 판정한다. 수신 중에 불러도 된다."""
        with self._lock:
            tracks = {k: t.copy() for k, t in self._tracks.items()}
            unknown = dict(self._unknown)
            others, errors = self._others, self._errors
            origin = self._first
            start = None if self._first is None else self._first + self.settle_s
            window = max(0.0, (self._last or 0.0) - start) if start is not None and self._last else 0.0

        def at(ts: float | None) -> str:
            """처음 발생 시각 꼬리표 (첫 프레임부터 잰 초)."""
            return "" if ts is None or origin is None else f", 처음 {ts - origin:.2f}초"

        results = [self._judge(spec, tracks[key], window, at) for key, spec in self._expected.items()]
        return CheckReport(
            bus=self.dbc.name,
            node=self.node,
            window_s=window,
            cycle_tol=self.cycle_tol,
            results=results,
            unknown=unknown,
            others=others,
            error_frames=errors,
        )

    def _judge(
        self, spec: MessageSpec, t: _Track, window: float, at: Callable[[float | None], str]
    ) -> MessageResult:
        r = MessageResult(spec=spec, count=t.count)

        if not t.count:
            if spec.is_cyclic and spec.kind == "app":
                r.add(Verdict.FAIL, "수신 없음")
            else:
                r.add(Verdict.INFO, "수신 없음 (이벤트·NM - 조건이 없으면 안 올 수 있음)")
            return r

        if t.wrong_len:
            got = ", ".join(f"{length}바이트 {n}개" for length, n in sorted(t.wrong_len.items()))
            r.add(Verdict.FAIL, f"길이 {got} (기준 {spec.length}{at(t.wrong_len_at)})")

        if t.wrong_fmt:
            want, got = ("FD", "Classic") if spec.is_fd else ("Classic", "FD")
            r.add(Verdict.FAIL, f"{got} 로 옴 {t.wrong_fmt}/{t.count}개 (기준 {want}{at(t.wrong_fmt_at)})")

        if spec.is_cyclic:
            self._judge_cycle(r, t, window, at)

        if spec.key in self._guards:
            if t.crc_bad:
                r.add(Verdict.FAIL, f"CRC 틀림 {t.crc_bad}/{t.crc_checked}개 ({at(t.crc_bad_at)[2:]})")
        elif self.e2e and spec.crc_signals:
            # 통과로 보이면 CRC까지 맞은 줄 안다 — 확인하지 못했다는 걸 판정에 남긴다
            r.add(Verdict.INFO, f"CRC 확인 안 함 ({self.e2e.name} {self.e2e.skip_reason(self.dbc, spec)})")

        for signal, counter in t.counters.items():
            self._judge_counter(r, signal, counter, at)

        return r

    def _judge_cycle(
        self, r: MessageResult, t: _Track, window: float, at: Callable[[float | None], str]
    ) -> None:
        cycle = r.spec.cycle_ms
        if t.count < 2:
            if window * 1000 > 2 * cycle:
                r.add(Verdict.FAIL, f"{window:.1f}초 동안 1개만 수신")
            else:
                r.add(Verdict.INFO, "수신 시간이 짧아 주기를 판정하지 못함")
            return

        r.mean_ms = (t.last_ts - t.first_ts) * 1000 / (t.count - 1)
        r.min_ms, r.max_ms = t.gap_min * 1000, t.gap_max * 1000

        low, high = cycle * (1 - self.cycle_tol), cycle * (1 + self.cycle_tol)
        if not low <= r.mean_ms <= high:
            r.add(Verdict.FAIL, f"평균 주기 {r.mean_ms:.1f}ms (허용 {low:.0f}~{high:.0f}ms)")
            return
        if t.long_gaps:
            r.add(
                Verdict.WARN,
                f"간격이 {r.max_ms:.0f}ms 까지 벌어짐 {t.long_gaps}회 (프레임 빠짐{at(t.long_gap_at)})",
            )

    def _judge_counter(
        self, r: MessageResult, signal: str, c: _CounterTrack, at: Callable[[float | None], str]
    ) -> None:
        if c.n < 2:
            return
        if c.lo == c.hi:
            r.add(Verdict.FAIL, f"{signal} 멈춤 (계속 {c.lo})")
            return

        # 최댓값 → 최솟값은 한 바퀴 돈 것. 범위는 끝까지 받아 봐야 알아서 여기서 가린다
        bad: dict[bool, list] = {False: [0, None], True: [0, None]}  # 간격 벌어짐 → [횟수, 처음]
        for (a, b, long_gap), (n, first) in c.steps.items():
            if a == c.hi and b == c.lo:
                continue
            slot = bad[long_gap]
            slot[0] += n
            slot[1] = first if slot[1] is None else min(slot[1], first)

        n, first = bad[False]
        if n:
            r.add(Verdict.FAIL, f"{signal} 건너뜀·역행 {n}회 (간격은 정상{at(first)})")
        n, first = bad[True]
        if n:
            r.add(
                Verdict.WARN,
                f"{signal} 프레임이 빠진 자리에서 건너뜀 {n}회 (안 보냈는지 놓쳤는지는 트레이스로{at(first)})",
            )
