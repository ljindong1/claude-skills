"""python-can 래퍼용 로깅 설정.

설정부터 사용까지 :class:`CanLogger` 한 곳에서 처리한다.

    >>> from can_log import CanLogger
    >>> CanLogger.setup("DEBUG")                          # 콘솔로만
    >>> CanLogger.setup("INFO", file="logs/can.log")      # 자정마다 회전, 30일 보관
    >>> log = CanLogger.get("CanModule")                  # 모듈별 자식 로거
    >>> log.info("연결됨")
    [INFO    | can_tutorial.CanModule | CanModule:512] 14:23:07 > 연결됨

라이브러리 관례를 따라 import 시점에는 핸들러를 붙이지 않는다(NullHandler만 부착).
로그를 실제로 보고 싶을 때만 :meth:`CanLogger.setup` 을 호출한다.

같은 리포의 ``SerialPort/log.py`` 는 import 시점에 홈 디렉터리를 만들고
``logging.Logger`` 를 ``__new__`` 로 싱글턴화하는 외부 SDK 코드라 재사용하지 않았다.
"""

import logging
import logging.handlers
import os

__all__ = ["CanLogger"]


class CanLogger:
    """``can_tutorial`` 로거 트리의 설정을 소유하는 클래스 싱글턴.

    인스턴스를 만들지 않고 클래스메서드로만 쓴다. 싱글턴으로 잡아야 하는 것은
    로거 객체가 아니라 **설정**이기 때문이다. 로거 자체는 ``logging`` 이 이름
    단위로 이미 유일성을 보장한다 — ``logging.getLogger("can_tutorial")`` 은
    어디서 몇 번을 부르든 같은 객체다. 그래서 ``__new__`` 싱글턴을 덧댈 이유가
    없고, 핸들러를 몇 개 붙였는지 같은 프로세스 단위 상태만 여기서 관리한다.

    :meth:`get` 이 돌려주는 것은 래퍼가 아니라 표준 :class:`logging.Logger` 다.
    ``CanBase(logger=...)`` 주입, pytest ``caplog``, ``logging.config.dictConfig``,
    외부 핸들러가 모두 그대로 동작해야 하기 때문이다.

    단, :meth:`setup` 은 기본으로 ``propagate=False`` 를 걸어 상위 로거로
    올려보내지 않는다. 그래서 setup을 부른 뒤에는 상위에서 낚아채는 방식인
    pytest ``caplog`` 가 아무것도 잡지 못한다. 테스트에서 둘을 같이 써야 하면
    ``setup(..., propagate=True)`` 로 열어두거나 :meth:`reset` 을 먼저 부른다.
    (setup을 아예 부르지 않으면 propagate는 True라 caplog가 정상 동작한다.)
    """

    NAME = "can_tutorial"

    #: 어느 제품이 냈는지(name)와 어디서 냈는지(module:lineno)를 함께 남긴다.
    #: 제품 객체를 여러 개 띄우면 module만으로는 구분이 되지 않기 때문이다.
    FORMAT = "[%(levelname)-7s | %(name)s | %(module)s:%(lineno)d] %(asctime)s > %(message)s"
    #: 날짜는 회전된 파일명이 갖고 있으므로 줄에는 시:분:초만 남긴다.
    DATEFMT = "%H:%M:%S"

    DEFAULT_MAX_BYTES = 10 * 1024 * 1024
    DEFAULT_TIME_BACKUPS = 30  #: 날짜 회전 기본 보관 일수
    DEFAULT_SIZE_BACKUPS = 3  #: 크기 회전 기본 보관 개수

    #: 트리의 최상위 로거. 클래스 속성이라 프로세스당 하나다.
    _root = logging.getLogger(NAME)
    _root.addHandler(logging.NullHandler())

    _configured = False

    def __init__(self) -> None:
        raise TypeError(
            "CanLogger는 인스턴스를 만들지 않습니다. "
            'CanLogger.setup(...) / CanLogger.get("이름") 처럼 클래스메서드로 쓰세요.'
        )

    # ================================================================== 설정
    @classmethod
    def setup(
        cls,
        level: "int | str" = logging.INFO,
        *,
        file: "str | os.PathLike[str] | None" = None,
        rotate: str = "time",
        when: str = "midnight",
        backup_count: "int | None" = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        console: bool = True,
        propagate: bool = False,
        quiet_can: bool = True,
    ) -> logging.Logger:
        """콘솔(및 선택적으로 파일) 핸들러를 붙인다.

        재호출은 "추가"가 아니라 **재설정**이다. 이전 핸들러를 걷어내고 새로
        붙이므로 몇 번을 불러도 로그가 중복 출력되지 않는다.

        :param rotate: ``"time"`` 이면 ``when`` 주기마다(기본 자정) 회전하고
            ``backup_count`` 일치를 보관한다. ``"size"`` 면 ``max_bytes`` 를
            넘을 때 회전한다. DEBUG로 프레임을 쏟아붓는 테스트는 하루치가
            수 GB가 될 수 있으므로 그럴 때만 ``"size"`` 를 쓴다.
        :param propagate: 기본값 False. :meth:`setup` 을 불렀다는 것은 출력을
            이쪽이 책임진다는 뜻인데, 상위(root)에도 핸들러가 있으면 같은 줄이
            두 번 찍히기 때문이다. setup을 부르지 않으면 propagate는 True로
            남아 라이브러리 관례대로 앱의 로깅 설정을 그대로 따른다.
        :param quiet_can: True면 python-can 자체 로거를 WARNING으로 낮춘다.
            (vector/virtual 백엔드가 DEBUG에서 프레임마다 로그를 남겨 출력이 묻힌다)
        """
        if rotate not in ("time", "size"):
            raise ValueError(f'rotate는 "time" 또는 "size"여야 합니다: {rotate!r}')

        formatter = logging.Formatter(cls.FORMAT, datefmt=cls.DATEFMT)
        cls.reset()
        cls._root.setLevel(level)
        cls._root.propagate = propagate

        if console:
            stream = logging.StreamHandler()
            stream.setFormatter(formatter)
            cls._root.addHandler(stream)

        if file:
            handler = cls._make_file_handler(file, rotate, when, backup_count, max_bytes)
            handler.setFormatter(formatter)
            cls._root.addHandler(handler)

        if quiet_can:
            logging.getLogger("can").setLevel(logging.WARNING)

        cls._configured = True
        return cls._root

    @classmethod
    def _make_file_handler(
        cls,
        file: "str | os.PathLike[str]",
        rotate: str,
        when: str,
        backup_count: "int | None",
        max_bytes: int,
    ) -> logging.Handler:
        """회전 파일 핸들러를 만든다. 상위 디렉터리가 없으면 만들어 준다."""
        path = os.path.abspath(os.fspath(file))
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if rotate == "size":
            backups = cls.DEFAULT_SIZE_BACKUPS if backup_count is None else backup_count
            return logging.handlers.RotatingFileHandler(
                path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
            )

        backups = cls.DEFAULT_TIME_BACKUPS if backup_count is None else backup_count
        handler = logging.handlers.TimedRotatingFileHandler(
            path, when=when, interval=1, backupCount=backups, encoding="utf-8"
        )
        # 회전된 파일을 can.log.2026-07-29 대신 can_2026-07-29.log 로 만든다.
        # 여기서 handler.suffix 를 직접 덮어쓰면 안 된다 — suffix를 바꿔도
        # 짝이 되는 extMatch 정규식은 따라 바뀌지 않아 getFilesToDelete()가
        # 오래된 파일을 하나도 찾지 못하고, 결과적으로 backupCount가 조용히
        # 무력화된다. namer는 라운드트립으로 검증되는 지원 경로라 안전하다.
        handler.namer = cls._dated_namer
        return handler

    @staticmethod
    def _dated_namer(default_name: str) -> str:
        """``.../can.log.2026-07-29`` → ``.../can_2026-07-29.log``"""
        base, _, date = default_name.rpartition(".")
        stem, ext = os.path.splitext(base)
        return f"{stem}_{date}{ext or '.log'}"

    @classmethod
    def reset(cls) -> None:
        """붙여둔 핸들러를 모두 떼어내고 설정 전 상태로 되돌린다 (NullHandler는 유지)."""
        for handler in list(cls._root.handlers):
            if not isinstance(handler, logging.NullHandler):
                cls._root.removeHandler(handler)
                handler.close()
        cls._root.propagate = True
        cls._configured = False

    @classmethod
    def set_level(cls, level: "int | str") -> None:
        """핸들러 구성은 그대로 두고 레벨만 바꾼다."""
        cls._root.setLevel(level)

    @classmethod
    def is_configured(cls) -> bool:
        """:meth:`setup` 이 호출된 뒤 :meth:`reset` 되지 않았으면 True."""
        return cls._configured

    # ============================================== 런타임 핸들러 (GUI 등)
    @classmethod
    def add_handler(
        cls,
        handler: logging.Handler,
        *,
        level: "int | str | None" = None,
        use_format: bool = True,
    ) -> logging.Handler:
        """실행 중에 핸들러를 추가한다. GUI 텍스트박스 연동 등에 쓴다.

            >>> CanLogger.setup("DEBUG")
            >>> CanLogger.add_handler(TextBoxHandler(widget), level="INFO")

        로거 레벨은 건드리지 않는다. 핸들러를 하나 붙였다고 이미 정해둔 출력
        수준이 바뀌면, DEBUG로 맞춰둔 설정이 조용히 사라지기 때문이다. 이
        핸들러만 다른 수준으로 걸러내고 싶으면 ``level`` 을 준다.

        다만 로거 레벨이 1차 관문이라, 로거가 INFO인데 핸들러만 DEBUG로 줘도
        DEBUG는 오지 않는다. 그때는 :meth:`set_level` 로 로거를 먼저 낮춘다.
        """
        if use_format and handler.formatter is None:
            handler.setFormatter(logging.Formatter(cls.FORMAT, datefmt=cls.DATEFMT))
        if level is not None:
            handler.setLevel(level)
        cls._root.addHandler(handler)
        return handler

    @classmethod
    def remove_handler(cls, handler: logging.Handler) -> None:
        """:meth:`add_handler` 로 붙인 핸들러를 떼어낸다 (close는 호출자 몫)."""
        cls._root.removeHandler(handler)

    # ================================================================== 사용
    @classmethod
    def get(cls, suffix: "str | None" = None) -> logging.Logger:
        """모듈/제품별 자식 로거를 반환한다. suffix가 없으면 최상위 로거를 반환한다."""
        if not suffix:
            return cls._root
        return cls._root.getChild(suffix)
