"""
데이터 캐시 유틸리티
파이프라인 실행 중 동일 데이터의 중복 수집을 방지
한 번 수집한 텔레그램/시장 데이터 + 에이전트 분석 결과를 캐싱하여 재사용
"""
from datetime import datetime
from utils.logger import get_logger

log = get_logger("Cache")

# 메모리 캐시 (프로세스 내에서만 유효)
_cache = {}
_cache_timestamps = {}


def get_cache_key(data_type: str, source: str, hours: int) -> str:
    """캐시 키 생성"""
    return f"{data_type}:{source}:{hours}"


def get_cached(data_type: str, source: str, hours: int):
    """캐시된 데이터 반환 (없으면 None)"""
    key = get_cache_key(data_type, source, hours)
    if key in _cache:
        # 캐시 유효시간: 2시간 (파이프라인 내 만료 방지)
        cached_at = _cache_timestamps.get(key)
        if cached_at and (datetime.now() - cached_at).total_seconds() < 7200:
            log.debug(f"HIT — {data_type}/{source} ({hours}h)")
            return _cache[key]
        else:
            # 만료된 캐시 삭제
            del _cache[key]
            del _cache_timestamps[key]
    return None


def set_cache(data_type: str, source: str, hours: int, data):
    """데이터를 캐시에 저장"""
    key = get_cache_key(data_type, source, hours)
    _cache[key] = data
    _cache_timestamps[key] = datetime.now()
    log.debug(f"SET — {data_type}/{source} ({hours}h)")


def clear_cache():
    """전체 캐시 초기화 (파이프라인 시작 시 호출)"""
    _cache.clear()
    _cache_timestamps.clear()
    log.info("캐시 초기화 완료")


def cached_collect(group_name: str, hours: int = 24, limit: int = 30):
    """텔레그램 메시지 수집 (캐시 적용)"""
    cached = get_cached("telegram", group_name, hours)
    if cached is not None:
        return cached

    try:
        from utils.telegram_collector import collect
        result = collect(group_name, hours=hours, limit=limit)
        set_cache("telegram", group_name, hours, result)
        return result
    except Exception as e:
        log.error(f"텔레그램 수집 실패 ({group_name}): {e}")
        return group_name, []


def cached_market_data() -> str:
    """시장 데이터 수집 (캐시 적용)"""
    cached = get_cached("market", "all", 0)
    if cached is not None:
        return cached

    try:
        from utils.market_data import get_all_market_data
        result = get_all_market_data()
        set_cache("market", "all", 0, result)
        return result
    except Exception as e:
        log.error(f"시장 데이터 수집 실패: {e}")
        return ""


def cached_competitor_data(hours: int = 72) -> str:
    """경쟁사 데이터 수집 (캐시 적용)"""
    cached = get_cached("competitor", "all", hours)
    if cached is not None:
        return cached

    try:
        from agents.market_follower_external import collect_data
        result = collect_data(hours=hours)
        set_cache("competitor", "all", hours, result)
        return result
    except Exception as e:
        log.error(f"경쟁사 데이터 수집 실패: {e}")
        return ""


def cached_x_data() -> str:
    """X(Twitter) 데이터 수집 (캐시 적용)"""
    cached = get_cached("x_twitter", "all", 0)
    if cached is not None:
        return cached

    try:
        from utils.x_collector import collect_all_x_data
        result = collect_all_x_data()
        set_cache("x_twitter", "all", 0, result)
        return result
    except Exception as e:
        log.error(f"X 데이터 수집 실패: {e}")
        return ""


def cached_mindshare(hours: int = 24) -> str:
    """Mindshare 산출 결과 (캐시 적용)"""
    cached = get_cached("mindshare", "all", hours)
    if cached is not None:
        return cached

    try:
        from utils.mindshare_calculator import get_mindshare_text
        result = get_mindshare_text(hours=hours)
        set_cache("mindshare", "all", hours, result)
        return result
    except Exception as e:
        log.error(f"Mindshare 산출 실패: {e}")
        return ""


def cached_surf_data() -> str:
    """SurfAI 소셜 분석 데이터 수집 (캐시 적용)"""
    cached = get_cached("surf", "all", 0)
    if cached is not None:
        return cached

    try:
        from utils.surf_collector import collect_all_surf_data
        result = collect_all_surf_data()
        set_cache("surf", "all", 0, result)
        return result
    except Exception as e:
        log.error(f"SurfAI 데이터 수집 실패: {e}")
        return ""


# === 에이전트 분석 결과 캐시 ===
# POC Agent 등에서 이전 에이전트의 분석 결과를 재사용

def save_agent_result(agent_name: str, result: str):
    """에이전트 분석 결과를 캐시에 저장"""
    set_cache("agent_result", agent_name, 0, result)


def get_agent_result(agent_name: str) -> str | None:
    """캐시된 에이전트 분석 결과 반환 (없으면 None)"""
    return get_cached("agent_result", agent_name, 0)
