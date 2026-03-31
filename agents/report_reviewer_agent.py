"""
Report Reviewer Agent
Report Agent가 작성한 보고서를 검토·수정·보완
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.data_cache import save_agent_result
from utils.logger import get_logger

log = get_logger("ReportReviewer")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 보고서 검토 에이전트입니다.

역할:
- Report Agent가 작성한 보고서의 품질 관리
- 오류, 논리적 비약, 데이터 불일치 검토 및 수정
- 누락된 관점이나 인사이트 보완
- 최종 결론과 액션 아이템에 대해 비판적 검토

검토 기준:
1. 정확성 — 데이터와 맞지 않는 주장이 있는지
2. 완전성 — 빠진 중요 포인트가 있는지
3. 실행 가능성 — 액션 아이템이 구체적이고 실행 가능한지
4. 균형성 — 긍정/부정 편향 없이 객관적인지

출력 형식:
1. 검토 요약 (수정/보완 사항 간략 정리)
2. 최종 보고서 (검토 반영 완료 버전)

출력 규칙:
- 한국어로 작성
- 최종 보고서는 피넛버터가 바로 읽을 수 있는 완성본으로 작성
- 긴급 이슈가 있으면 반드시 [긴급] 태그 유지
"""


def review(report: str) -> str:
    """보고서 검토 및 보완"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 보고서를 검토하고 최종 보고서를 작성해줘:\n\n{report}",
        max_tokens=3072,
    )
    return result


def run(hours: int = 24, report_type: str = "일간"):
    """전체 파이프라인: 데이터 수집 → 보고서 작성 → 검토 → 최종 전송"""
    # 1단계: Report Agent가 보고서 생성 (채널 전송 없이 데이터만 받음)
    log.info(f"{report_type} 보고서 파이프라인 시작...")
    log.info("1단계 - Report Agent 보고서 생성 중...")

    from agents.report_agent import collect_all_data, generate_report as create_report
    raw_data = collect_all_data(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다.")
        return

    draft = create_report(raw_data, report_type)
    if not draft:
        log.error("초안 생성 실패.")
        return

    # 2단계: 검토 및 보완
    log.info("2단계 - 보고서 검토 중...")
    final_report = review(draft)

    if not final_report:
        log.error("검토 실패.")
        return

    # 3단계: 최종 보고서 전송
    if "[긴급]" in final_report:
        send_message("urgent", f"🚨 *[긴급 알림]*\n\n{final_report}")

    send_message("market", f"📋 *[{report_type} 최종 보고서 - 검토 완료]*\n\n{final_report}")

    # POC Agent가 재사용할 수 있도록 결과 캐시 저장
    save_agent_result("market_report", final_report)

    log.info(f"{report_type} 최종 보고서 전송 완료.")
    return final_report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=72, report_type="일간")
