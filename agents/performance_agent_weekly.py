"""
Performance Agent (Weekly)
전체 전략의 ROI/성장 추이 분석
주간 1회 실행, POC Agent에게 데이터 제공
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect, cached_market_data, cached_competitor_data, save_agent_result
from config.groups import VARIATIONAL_GROUPS
from utils.logger import get_logger

log = get_logger("Perf_Weekly")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 장기 성과 분석 에이전트입니다.

역할:
- 주간 단위로 전체 전략의 성과를 분석
- Variational vs 경쟁사 성장 추이 비교
- ROI 분석 및 채널별 효과 측정
- POC Agent에게 전달할 핵심 데이터 정리

출력 형식:
1. 주간 핵심 지표
   - 커뮤니티 활성도 추이 (전주 대비 ↑↓%)
   - 메시지 수, 참여 유저 수, 신규 유입 추정

2. 경쟁사 대비 분석
   - 경쟁사 커뮤니티 활성도 비교
   - Variational의 상대적 포지션

3. 채널별 성과
   - Telegram / Discord / X 각 채널 성과
   - 가장 효과적인 채널 분석

4. 전략 성과 평가
   - 이번 주 실행한 전략의 효과
   - 성장 트렌드 (긍정/정체/하락)

5. 다음 주 전략 제안
   - 데이터 기반 개선 방향
   - 집중해야 할 영역

출력 규칙:
- 한국어로 작성
- 수치와 비교 중심
- POC Agent가 최종 보고서에 활용할 수 있도록 구조화
"""

def collect_weekly_data(hours: int = 168, limit: int = 30) -> str:
    """주간 성과 데이터 수집 (Variational + 경쟁사)"""
    parts = []

    # Variational 내부 데이터
    for group_name in VARIATIONAL_GROUPS:
        group, raw_messages = cached_collect(group_name, hours=hours, limit=limit)
        total_count = len(raw_messages) if raw_messages else 0
        filtered = filter_messages(raw_messages) if raw_messages else []
        log.debug(f"{group}: 전체 {total_count}개 / 의미있는 메시지 {len(filtered)}개")

        header = f"[Variational 주간 데이터 - {group}]\n전체 메시지: {total_count}개 / 의미있는 메시지: {len(filtered)}개\n\n"
        if filtered:
            parts.append(header + format_messages(group, filtered, hours))
        else:
            parts.append(header + "의미있는 메시지 없음")

    # 경쟁사 데이터
    log.info("경쟁사 데이터 수집 중...")
    competitor = cached_competitor_data(hours=hours)
    if competitor:
        parts.append(f"=== 경쟁사 주간 데이터 ===\n{competitor}")

    return "\n\n".join(parts)


def analyze_weekly(raw_data: str) -> str:
    """주간 성과 분석 (시장 데이터 포함)"""
    log.info("실시간 시장 데이터 수집 중...")
    market_data = cached_market_data()

    combined = raw_data
    if market_data:
        combined = f"=== 실시간 시장 데이터 (거래량/TVL/가격) ===\n{market_data}\n\n=== 주간 성과 데이터 ===\n{raw_data}"

    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 시장 데이터와 주간 데이터를 기반으로 주간 성과 분석 리포트를 작성해줘:\n\n{combined}",
    )
    return result


def run(hours: int = 168):
    """에이전트 실행: 주간 데이터 수집 → 분석 → 전송 + POC Agent용 반환"""
    log.info("주간 성과 분석 시작...")
    raw_data = collect_weekly_data(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 주간 분석 중...")
    report = analyze_weekly(raw_data)

    if not report:
        log.error("분석 실패.")
        return

    # 성과+종합 보고 채널로 전송
    send_message("performance", f"📊 *[Performance Agent (Weekly) - 주간 성과]*\n\n{report}")

    # POC Agent가 재사용할 수 있도록 결과 캐시 저장
    save_agent_result("performance_weekly", report)

    log.info("주간 성과 리포트 전송 완료 → POC Agent에게 전달.")
    return report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=168)
