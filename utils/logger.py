"""
로깅 유틸리티
콘솔 + 파일 동시 출력, 에이전트별 로그 추적

로그 파일 관리:
- 일반 로그: 일자별 자동 회전, 최근 7일분만 보관 (이전 자동 삭제)
- 에러 로그: 일자별 자동 회전, 최근 30일분만 보관
- 단일 파일 최대 10MB 초과 시 즉시 회전
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

# 로그 디렉토리
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 공유 핸들러 (모든 로거가 동일한 파일 핸들러를 재사용)
_shared_handlers_initialized = False
_shared_file_handler = None
_shared_error_handler = None


def _init_shared_handlers():
    """파일 핸들러를 한 번만 생성하여 모든 로거가 공유"""
    global _shared_handlers_initialized, _shared_file_handler, _shared_error_handler

    if _shared_handlers_initialized:
        return

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 일반 로그: 매일 자정에 회전, 7일 보관
    _shared_file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "variational.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    _shared_file_handler.suffix = "%Y-%m-%d"
    _shared_file_handler.setLevel(logging.DEBUG)
    _shared_file_handler.setFormatter(fmt)

    # 에러 로그: 매일 자정에 회전, 30일 보관
    _shared_error_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "errors.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    _shared_error_handler.suffix = "%Y-%m-%d"
    _shared_error_handler.setLevel(logging.ERROR)
    _shared_error_handler.setFormatter(fmt)

    _shared_handlers_initialized = True


def get_logger(name: str) -> logging.Logger:
    """에이전트/모듈별 로거 생성"""
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 재생성 방지
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 공유 핸들러 초기화
    _init_shared_handlers()

    # 포맷
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 콘솔 핸들러 (INFO 이상) — 로거마다 개별 생성
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 2. 파일 핸들러 (공유, DEBUG 이상)
    logger.addHandler(_shared_file_handler)

    # 3. 에러 전용 파일 핸들러 (공유)
    logger.addHandler(_shared_error_handler)

    return logger
