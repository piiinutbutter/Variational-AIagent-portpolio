"""
Performance Agent (Daily)
콘텐츠/이벤트/캠페인의 건별 즉시 성과 측정
게시 후 24~48시간 내 성과 추적
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect, cached_market_data
from config.groups import VARIATIONAL_GROUPS
from utils.logger import get_logger

log = get_logger("Perf_Daily")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 단기 성과 추적 에이전트입니다.

역할:
- Variational 커뮤니티 활성도를 일일 기준으로 추적
- 콘텐츠/이벤트/캠페인 게시 후 반응 측정
- 단기 KPI 변화 감지

출력 형식:
1. 일일 커뮤니티 활성도
   - 메시지 수, 참여 유저 수, 주요 토론 주제
   - 전일 대비 변화 (↑↓)

2. 콘텐츠/이벤트 성과 (해당 시)
   - 게시물별 조회수, 반응, 댓글
   - 유저 반응 요약

3. 주요 지표
   - 커뮤니티 심리 (긍정/중립/부정)
   - 신규 유입 징후
   - 이탈 징후

4. 주의 사항
   - 급격한 변화나 이상 징후

출력 규칙:
- 한국어로 작성
- 수치 중심, 간결하게
- 전일 대비 비교 포함
"""

def collect_performance(hours: int = 24, limit: int = 30) -> str:
    """성과 데이터 수집"""
    all_data = []
    for group_name in VARIATIONAL_GROUPS:
        group, raw_messages = cached_collect(group_name, hours=hours, limit=limit)
        if not raw_messages:
            continue
        # Daily는 필터링 없이 전체 메시지 수도 KPI로 사용
        total_count = len(raw_messages)
        filtered = filter_messages(raw_messages)
        log.debug(f"{group}: 전체 {total_count}개 / 의미있는 메시지 {len(filtered)}개")

        header = f"[성과 데이터 - {group}]\n전체 메시지: {total_count}개 / 의미있는 메시지: {len(filtered)}개\n\n"
        if filtered:
            all_data.append(header + format_messages(group, filtered, hours))
        else:
            all_data.append(header + "의미있는 메시지 없음")
    return "\n\n".join(all_data)


def analyze_performance(raw_data: str) -> str:
    """성과 데이터 분석 (시장 데이터 포함)"""
    log.info("실시간 시장 데이터 수집 중...")
    market_data = cached_market_data()

    combined = raw_data
    if market_data:
        combined = f"=== 실시간 시장 데이터 (거래량/TVL/가격) ===\n{market_data}\n\n=== 커뮤니티 성과 데이터 ===\n{raw_data}"

    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 시장 데이터와 커뮤니티 데이터를 기반으로 일일 성과 리포트를 작성해줘:\n\n{combined}",
        max_tokens=1536,
    )
    return result


def run(hours: int = 24):
    """에이전트 실행: 성과 수집 → 분석 → 텔레그램 전송"""
    log.info("일일 성과 측정 시작...")
    raw_data = collect_performance(hours=hours)

    if not raw_data:
        log.warning("수집된 데이터가 없습니다. (최근 메시지 없음)")
        return

    log.info("Claude 성과 분석 중...")
    report = analyze_performance(raw_data)

    if not report:
        log.error("분석 실패.")
        return

    # 성과+종합 보고 채널로 전송
    send_message("performance", f"📈 *[Performance Agent (Daily) - 일일 성과]*\n\n{report}")

    log.info("일일 성과 리포트 전송 완료.")
    return report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=48)
