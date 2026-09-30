"""CAN 벤치 — 설정 파일 하나로 연결·깨우기·수신·DBC 대조를 한다 (제품 무관).

제품마다 설정 파일(.toml)을 하나 두고 이 스크립트에 넘긴다. 예: psu_drv.toml

    python can_bench.py psu_drv.toml            계획만 출력 (장비 연결 안 함)
    python can_bench.py psu_drv.toml --listen   받기만 — 버스로 아무것도 보내지 않는다
    python can_bench.py psu_drv.toml --run      깨우기(레스트버스) + 받기 + 판정

    --seconds N     판정에 쓰는 수신 시간 (설정 파일 값 대신). 첫 프레임부터 센다
    --trace DIR     버스마다 .blf 기록과, 판정 결과(.txt)를 남긴다

수신 중 Ctrl+C 로 멈추면 그때까지 받은 것으로 판정을 보여 준다 (종료 코드는 2).

종료 코드: 0 통과 / 1 실패 / 2 설정·연결 오류 또는 중단

설정 파일 구성은 psu_drv.toml 의 주석을 본다. 모르는 항목(오타)이 있으면 멈춘다 —
조용히 무시하면 기본값으로 돌아 실물 ECU 와 같은 ID 를 보내는 일이 생긴다.
DB 경로가 상대 경로면 설정 파일이 있는 폴더 기준이다.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import time
import tomllib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from CanNodeTxCheck import CanNodeTxCheck, CheckReport
from CanDbc import CanDbc
from CanE2E import E2EProfile, HkmcE2E
from CanErrors import CanBaseError, CanConfigError
from CanModule import CanBase, CanConfig, CanMode, backend_profile
from CanRestbus import CanRestbus
from can_log import CanLogger

#: 설정 파일의 e2e 이름 → 방식
E2E_PROFILES: dict[str, type[E2EProfile]] = {"HKMC": HkmcE2E}

#: 설정 파일에 쓸 수 있는 항목. 여기 없는 이름은 오타로 보고 멈춘다
SETTINGS_KEYS: dict[str, frozenset[str]] = {
    "": frozenset({"name", "device", "dut", "run", "bus"}),
    "device": frozenset({"interface", "serial", "app_name"}),
    "dut": frozenset({"node", "e2e"}),
    "run": frozenset({"settle_s", "seconds", "wake_timeout_s", "cycle_tol"}),
    "bus": frozenset({
        "name", "channel", "dbc", "fd", "bitrate", "data_bitrate", "f_clock",
        "sample_point", "data_sample_point", "simulate", "exclude", "pn", "signals",
    }),
}

@dataclass
class BusSetup:
    """버스 하나에 필요한 것 일체."""

    name: str
    config: CanConfig
    dbc: CanDbc
    check: CanNodeTxCheck
    restbus: CanRestbus | None


# ============================================================ 설정
def load_settings(path: str) -> dict[str, Any]:
    """설정 파일을 읽고 필수 항목을 확인한다."""
    if not os.path.isfile(path):
        raise CanConfigError(f"설정 파일이 없습니다: {path}")
    with open(path, "rb") as fh:
        try:
            settings = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise CanConfigError(f"설정 파일 문법 오류: {path} | {exc}") from exc

    for key in ("dut", "bus"):
        if key not in settings:
            raise CanConfigError(f"설정 파일에 [{key}] 가 없습니다: {path}")
    if "node" not in settings["dut"]:
        raise CanConfigError("[dut] 에 node 가 없습니다.")
    _check_keys(settings, "", "맨 위")
    for section in ("device", "dut", "run"):
        _check_keys(settings.get(section, {}), section, f"[{section}]")
    base = os.path.dirname(os.path.abspath(path))
    for i, bus in enumerate(settings["bus"]):
        _check_keys(bus, "bus", f"[[bus]] {i + 1}번째")
        for key in ("name", "channel", "dbc"):
            if key not in bus:
                raise CanConfigError(f"[[bus]] {i + 1}번째에 {key} 가 없습니다.")
        if not os.path.isabs(bus["dbc"]):  # 실행한 폴더가 아니라 설정 파일 기준
            bus["dbc"] = os.path.normpath(os.path.join(base, bus["dbc"]))
    return settings


def _check_keys(table: dict[str, Any], section: str, where: str) -> None:
    """모르는 항목이 있으면 비슷한 이름을 붙여 알린다."""
    known = SETTINGS_KEYS[section]
    for key in table:
        if key not in known:
            near = difflib.get_close_matches(key, known, n=1)
            hint = f" '{near[0]}' 를 쓰려던 것인가요?" if near else ""
            raise CanConfigError(
                f"{where}에 모르는 항목 '{key}'.{hint} 쓸 수 있는 것: {', '.join(sorted(known))}"
            )


def make_e2e(name: str) -> E2EProfile | None:
    if not name:
        return None
    try:
        return E2E_PROFILES[name]()
    except KeyError:
        raise CanConfigError(f"모르는 e2e 방식 {name!r}. 가능한 값: {sorted(E2E_PROFILES)}") from None


def bus_config(device: dict[str, Any], bus: dict[str, Any]) -> CanConfig:
    """[device] + [[bus]] → CanConfig."""
    fd = bus.get("fd", True)
    mode = CanMode.FD_BRS if fd else CanMode.CLASSIC
    bitrate = bus.get("bitrate", 500_000)
    data_bitrate = bus.get("data_bitrate", 2_000_000)
    timing = None
    if bus.get("f_clock"):
        timing = CanBase.make_timing(
            mode,
            bus["f_clock"],
            nom_bitrate=bitrate,
            nom_sample_point=bus.get("sample_point", 80.0),
            data_bitrate=data_bitrate,
            data_sample_point=bus.get("data_sample_point", 75.0),
        )

    # TODO(범용화): interface 를 빼면 vector 로 본다 (벤치 장비 기준). 다른 벤더가 생기면 필수로.
    interface = device.get("interface", "vector")
    return CanConfig(
        interface=interface,
        channel=bus["channel"],
        **backend_profile(interface).settings_kwargs(device),
        mode=mode,
        bitrate=bitrate,
        data_bitrate=data_bitrate,
        timing=timing,
    )


def resolve_device(settings: dict[str, Any], setups: list[BusSetup]) -> str | None:
    """연결 직전에 장비를 감지해 config 를 확정한다 (Vector 는 시리얼). 알릴 말을 돌려준다."""
    device = settings.get("device", {})
    profile = backend_profile(device.get("interface", "vector"))
    return profile.resolve_device(device, [s.config for s in setups])


def build(settings: dict[str, Any], *, listen: bool) -> list[BusSetup]:
    """설정으로 버스별 준비물을 만든다. 장비에는 연결하지 않는다."""
    device = settings.get("device", {})
    dut = settings["dut"]["node"]
    e2e_name = settings["dut"].get("e2e", "")
    run = settings.get("run", {})

    setups = []
    for bus in settings["bus"]:
        dbc = CanDbc.load(bus["dbc"])
        check = CanNodeTxCheck(
            dbc,
            dut,
            cycle_tol=run.get("cycle_tol", 0.10),
            settle_s=run.get("settle_s", 0.0),
            e2e=make_e2e(e2e_name),
        )
        restbus = None
        if not listen:
            restbus = CanRestbus(
                None,  # 연결 뒤에 붙인다
                dbc,
                bus.get("simulate", "all"),
                dut=dut,
                exclude=bus.get("exclude", []),
                e2e=make_e2e(e2e_name),
                pn=bus.get("pn", "none"),
            )
            for message, signals in bus.get("signals", {}).items():
                restbus.set(message, **signals)
        setups.append(BusSetup(bus["name"], bus_config(device, bus), dbc, check, restbus))
    return setups


# ============================================================ 출력
def print_plan(settings: dict[str, Any], setups: list[BusSetup]) -> None:
    dut = settings["dut"]["node"]
    print(f"== {settings.get('name', '')}  시험 대상 {dut} ==")
    for s in setups:
        c = s.config
        rate = f"{c.bitrate // 1000}k" + (f" / {c.data_bitrate // 1000}k BRS" if c.mode.is_fd else "")
        print()
        print(f"[{s.name}]  {c.interface} 채널 {c.channel}  {rate}")
        print(f"  DB   {s.dbc.name}  ({s.dbc.path})")
        issues = s.dbc.validate()
        if issues:  # 시험은 진행한다 — DB 담당자에게 알릴 목록. 전체는 python CanDbc.py <DBC>
            print("  " + s.dbc.validation_report(issues, limit=3).replace("\n", "\n  "))
        if c.timing is not None:
            print(f"  타이밍 {c.timing}")
        print(f"  판정 대상: {dut} 가 보내는 메시지 {len(s.check.expected)}개"
              + (f", CRC 확인 {s.check.e2e.name}" if s.check.e2e else ""))
        if s.restbus:
            print("  " + s.restbus.summary().replace("\n", "\n  "))
            changed = {
                spec.name: s.restbus.get(spec.name)
                for spec in s.restbus.messages
                if s.restbus.get(spec.name) != s.dbc.initial_values(spec.name)
            }
            for name, values in changed.items():
                diff = {k: v for k, v in values.items() if s.dbc.initial_values(name).get(k) != v}
                print(f"  초기값 대신: {name} {diff}")


# ============================================================ 실행
def wait_first_frame(setups: list[BusSetup], timeout: float) -> list[str]:
    """모든 버스에서 프레임이 들어올 때까지 기다린다. 끝까지 조용한 버스 이름을 돌려준다."""
    deadline = time.monotonic() + timeout
    while True:
        silent = [s.name for s in setups if s.check.first_seen is None]
        if not silent or time.monotonic() >= deadline:
            return silent
        time.sleep(0.05)


def run(
    setups: list[BusSetup],
    *,
    seconds: float,
    settle_s: float,
    wake_timeout: float,
    trace_dir: str | None,
    stamp: str,
) -> tuple[list[CheckReport], bool]:
    """연결 → (레스트버스) → 첫 프레임 대기 → 수신 → 판정. (버스별 판정, 중단 여부).

    수신 시간은 첫 프레임부터 센다 — 깨어나는 데 걸린 시간이 판정 시간을 깎지 않게.
    Ctrl+C 로 멈춰도 그때까지 받은 것으로 판정한다.
    """
    buses: list[CanBase] = []
    started: list[CanRestbus] = []
    interrupted = False
    try:
        for s in setups:
            bus = CanBase(s.config, name=s.name)
            bus.connect()
            buses.append(bus)
            bus.add_listener(s.check)
            if trace_dir:
                path = bus.start_trace(f"{s.name}_{stamp}.blf", directory=trace_dir)
                print(f"  기록 {path}")

        for s, bus in zip(setups, buses):
            if s.restbus:
                s.restbus.bus = bus
                s.restbus.start()
                started.append(s.restbus)

        try:
            print(f"  첫 프레임 기다리는 중 (최대 {wake_timeout:g}초)...")
            silent = wait_first_frame(setups, wake_timeout)
            if silent:
                print(f"  {', '.join(silent)}: {wake_timeout:g}초 동안 받은 프레임 없음")
            if len(silent) < len(setups):
                total = settle_s + seconds
                print(
                    f"  첫 프레임부터 {total:g}초 수신 중 (앞 {settle_s:g}초는 판정에서 뺌). "
                    "Ctrl+C 로 멈추면 그때까지로 판정합니다..."
                )
                time.sleep(total)
        except KeyboardInterrupt:
            interrupted = True
            print("\n  중단했습니다. 지금까지 받은 것으로 판정합니다.")
    finally:
        for rb in started:
            rb.stop()
        for bus in buses:
            bus.disconnect()

    return [s.check.report() for s in setups], interrupted


def result_text(reports: list[CheckReport], interrupted: bool) -> tuple[str, int]:
    """판정표 전체와 종료 코드."""
    ok = all(r.passed for r in reports)
    if interrupted:
        # 정해진 시간을 채우지 못했으니 통과로 치지 않는다
        tail = "== 전체 결과: 중단 (판정은 참고용 - " + ("실패 없음) ==" if ok else "실패 있음) ==")
        code = 2
    else:
        tail = "== 전체 결과: " + ("통과 ==" if ok else "실패 ==")
        code = 0 if ok else 1
    return "\n\n".join([r.text() for r in reports] + [tail]), code


def save_result(trace_dir: str, name: str, stamp: str, header: list[str], body: str) -> str:
    """판정 결과를 트레이스 옆에 텍스트로 남긴다. 파일 경로를 돌려준다."""
    os.makedirs(trace_dir, exist_ok=True)
    path = os.path.join(trace_dir, f"{name}_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n\n" + body + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="can_bench", description=__doc__.splitlines()[0])
    ap.add_argument("settings", help="설정 파일 (.toml)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--listen", action="store_true", help="받기만 - 송신 없음")
    mode.add_argument("--run", action="store_true", help="깨우기 + 받기 + 판정 - 버스로 송신한다")
    ap.add_argument("--seconds", type=float, help="판정에 쓰는 수신 시간")
    ap.add_argument("--trace", metavar="DIR", help="버스마다 .blf 기록을 남길 폴더")
    ap.add_argument("--log", default="WARNING", help="로그 수준 (기본 WARNING)")
    a = ap.parse_args(argv)

    CanLogger.setup(a.log)
    try:
        settings = load_settings(a.settings)
        setups = build(settings, listen=a.listen)
    except CanBaseError as exc:
        print(f"[설정 오류] {exc}")
        return 2

    print_plan(settings, setups)
    if not (a.listen or a.run):
        print("\n계획만 출력했습니다. 장비에 연결하지 않았습니다.")
        print("받기만: --listen   깨우기까지: --run")
        return 0

    runs = settings.get("run", {})
    seconds = a.seconds if a.seconds is not None else runs.get("seconds", 10.0)
    settle_s = runs.get("settle_s", 0.0)
    wake_timeout = runs.get("wake_timeout_s", 10.0)
    print()
    if a.run:
        n = sum(len(s.restbus.messages) for s in setups if s.restbus)
        print(f"== 실행: 버스로 송신합니다 (주기 메시지 {n}개 + NM) ==")
    else:
        print("== 받기만: 버스로 아무것도 보내지 않습니다 ==")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    header = [
        f"설정 {os.path.abspath(a.settings)}",
        f"시각 {stamp}  방식 {'--run' if a.run else '--listen'}  수신 {seconds:g}초 (앞 {settle_s:g}초 제외)",
    ]
    try:
        note = resolve_device(settings, setups)
        if note:
            print(f"  {note}")
            header.append(note)
        reports, interrupted = run(
            setups, seconds=seconds, settle_s=settle_s, wake_timeout=wake_timeout,
            trace_dir=a.trace, stamp=stamp,
        )
    except CanBaseError as exc:
        print(f"[연결 오류] {exc}")
        return 2
    except KeyboardInterrupt:  # 연결 도중
        print("\n중단했습니다. 송신을 멈추고 연결을 닫았습니다.")
        return 2

    body, code = result_text(reports, interrupted)
    print()
    print(body)
    if a.trace:
        path = save_result(a.trace, settings.get("name") or "result", stamp, header, body)
        print(f"  결과 {path}")
    return code


if __name__ == "__main__":
    sys.exit(main())
