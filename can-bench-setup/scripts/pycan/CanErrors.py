"""python-can 래퍼(CanModule)의 예외 계층.

모든 예외는 ``can.CanError``를 상속하므로, 사용하는 쪽에서 ``except can.CanError:``
하나로 이 모듈의 예외와 python-can 자체의 예외를 함께 잡을 수 있다.
베이스 클래스가 python-can의 모든 예외 경로를 감쌀 수는 없기 때문에 내린 선택이다.
"""

import can

__all__ = [
    "CanBaseError",
    "CanConfigError",
    "CanNotConnectedError",
    "CanConnectionError",
    "CanSendError",
    "CanReceiveError",
    "CanReceiveTimeout",
    "CanDbcError",
    "CanUdsError",
]


class CanBaseError(can.CanError):
    """이 모듈에서 발생하는 모든 예외의 최상위 클래스."""


class CanConfigError(CanBaseError):
    """설정 값이 잘못되었거나 서로 배타적인 옵션을 함께 지정했다."""


class CanNotConnectedError(CanBaseError):
    """connect() 이전에 버스가 필요한 기능을 호출했다."""


class CanConnectionError(CanBaseError):
    """버스 또는 Notifier를 여는 데 실패했다."""


class CanSendError(CanBaseError):
    """프레임 전송에 실패했다."""


class CanReceiveError(CanBaseError):
    """Notifier 수신 스레드가 예외로 중단되었다."""


class CanReceiveTimeout(CanBaseError, TimeoutError):
    """기대한 프레임을 제한 시간 안에 받지 못했다."""


class CanDbcError(CanBaseError):
    """DBC 로드/인코딩/디코딩에 실패했거나 cantools가 설치되어 있지 않다."""


class CanUdsError(CanBaseError):
    """UDS 스택 열기/진단 요청에 실패했거나 can-isotp/udsoncan이 설치되어 있지 않다."""
