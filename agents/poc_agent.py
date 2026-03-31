"""
POC Agent
모든 에이전트의 텔레그램 보고를 총 정리하여 상사에게 최종 리포트 작성
주간 1회 (금요일) 실행, 피넛버터 확인 후 상사에게 이메일 발송
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.data_cache import get_agent_result
from utils.logger import get_logger

log = get_logger("POC")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 최종 보고서 작성 에이전트입니다.
피넛버터(한국 매니저)의 상사에게 보낼 주간 종합 리포트를 작성합니다.

리포트 구성:
1. Executive Summary
   - 핵심 성과 3줄 요약
   - 이번 주 의사결정 필요 사항

2. 핵심 지표 대시보드
   - 거래량/이용자/SNS (전주 대비 ↑↓%)
   - 경쟁사 비교

3. 시장 심리 & 커뮤니티 동향
   - Variational 유저 심리
   - 경쟁사 커뮤니티 동향

4. 콘텐츠 & 트렌드
   - 이번 주 트렌드
   - 콘텐츠 성과

5. 마케팅 활동 & 성과
   - 실행한 캠페인 성과
   - 다음 주 계획

6. 전략 성과 분석
   - ROI 분석
   - 채널별 효과

7. 커뮤니티 피드백 요약
   - 주요 질문/불만/제안

8. 제안 & 다음 스텝
   - 데이터 기반 전략 제안
   - 우선순위별 액션 아이템

작성 원칙:
- 구조화 · 시각화 · 간결성 · 근거 기반 · 액션 지향
- 영어로 작성 (상사가 외국인)
- 데이터 수치 포함
- 각 섹션은 핵심만 간결하게
"""


def collect_all_reports(hours: int = 168) -> str:
    """모든 에이전트의 보고 데이터 수집 (캐시 우선, 없으면 직접 수집)"""
    parts = []

    # 1. 시장 분석 (Report Reviewer Agent 최종 보고서)
    log.info("시장 분석 보고서 수집 중...")
    market_report = get_agent_result("market_report")
    if market_report:
        log.info("시장 분석 — 캐시에서 가져옴 (Claude 재호출 없음)")
        parts.append(f"=== 시장 분석 보고서 ===\n{market_report}")
    else:
        try:
            from agents.report_agent import collect_all_data, generate_report
            market_data = collect_all_data(hours=hours)
            if market_data:
                market_report = generate_report(market_data, "주간")
                if market_report:
                    parts.append(f"=== 시장 분석 보고서 ===\n{market_report}")
        except Exception as e:
            log.error(f"시장 분석 수집 실패: {e}")

    # 2. 주간 성과
    log.info("주간 성과 데이터 수집 중...")
    perf_report = get_agent_result("performance_weekly")
    if perf_report:
        log.info("주간 성과 — 캐시에서 가져옴 (Claude 재호출 없음)")
        parts.append(f"=== 주간 성과 분석 ===\n{perf_report}")
    else:
        try:
            from agents.performance_agent_weekly import collect_weekly_data, analyze_weekly
            perf_data = collect_weekly_data(hours=hours)
            if perf_data:
                perf_report = analyze_weekly(perf_data)
                if perf_report:
                    parts.append(f"=== 주간 성과 분석 ===\n{perf_report}")
        except Exception as e:
            log.error(f"주간 성과 수집 실패: {e}")

    # 3. 트렌드
    log.info("트렌드 데이터 수집 중...")
    trend_report = get_agent_result("trend_research")
    if trend_report:
        log.info("트렌드 — 캐시에서 가져옴 (Claude 재호출 없음)")
        parts.append(f"=== 트렌드 분석 ===\n{trend_report}")
    else:
        try:
            from agents.trend_research_agent import collect_trends, analyze_trends
            trend_data = collect_trends(hours=hours)
            if trend_data:
                trend_report = analyze_trends(trend_data)
                if trend_report:
                    parts.append(f"=== 트렌드 분석 ===\n{trend_report}")
        except Exception as e:
            log.error(f"트렌드 수집 실패: {e}")

    return "\n\n".join(parts)


def generate_final_report(all_data: str) -> str:
    """최종 종합 리포트 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 각 에이전트의 보고 데이터를 종합하여 상사에게 보낼 주간 최종 리포트를 작성해줘:\n\n{all_data}",
        max_tokens=4096,
    )
    return result


def run(hours: int = 168):
    """에이전트 실행: 전체 데이터 수집 → 최종 리포트 → 피넛버터에게 전송"""
    log.info("주간 최종 리포트 작성 시작...")
    all_data = collect_all_reports(hours=hours)

    if not all_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 최종 리포트 작성 중...")
    final_report = generate_final_report(all_data)

    if not final_report:
        log.error("최종 리포트 생성 실패.")
        return

    # 성과+종합 보고 채널로 전송 (피넛버터 확인용)
    send_message("performance", f"📋 *[POC Agent - 주간 최종 리포트]*\n\n피넛버터 확인 후 상사에게 이메일 발송 예정\n\n{final_report}")

    log.info("최종 리포트 전송 완료. 피넛버터 확인 후 이메일 발송 대기.")
    return final_report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=168)
