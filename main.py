"""
Variational AI Agent System - 메인 실행 파일
각 에이전트를 스케줄에 맞춰 실행

실행 순서 (DeFiLlama 하루 3회 제한 고려):
1. Trend Research Agent -> Contents Creator Agent (DeFiLlama 1회)
2. Report Reviewer Agent (DeFiLlama 1회)
3. Performance Agent Daily (DeFiLlama 1회)
4. Q&A Agent (DeFiLlama 미사용)
5. Promotion Agent (주 1회)
6. Performance Agent Weekly + POC Agent (주 1회, 금요일)
"""
import sys
import schedule
import time
from utils.data_cache import clear_cache
from utils.telegram_collector import cleanup as tg_cleanup
from utils.telegram_sender import send_message
from utils.logger import get_logger

sys.stdout.reconfigure(encoding="utf-8")
log = get_logger("Main")


def _run_agent(name: str, func, errors: list, **kwargs):
    """에이전트 실행 래퍼 — 실패 시 로그 + 에러 수집"""
    try:
        return func(**kwargs)
    except Exception as e:
        log.error(f"{name} 실패: {e}", exc_info=True)
        errors.append(name)


def daily_pipeline():
    """매일 KST 11:00 실행 - 일일 파이프라인"""
    log.info("=" * 50)
    log.info("일일 에이전트 파이프라인 시작")
    log.info("=" * 50)

    # 파이프라인 시작 시 캐시 초기화 (새 데이터로 수집)
    clear_cache()
    errors = []

    # 1단계: Trend Research -> Contents Creator (DeFiLlama 1/3)
    log.info("[1/4] LINE 2: 트렌드 분석 + 콘텐츠 기획...")
    from agents.contents_creator_agent import run as run_contents
    _run_agent("Contents Creator Agent", run_contents, errors, hours=72)

    # 2단계: Report Reviewer (DeFiLlama 2/3)
    log.info("[2/4] LINE 1: 시장 분석 보고서...")
    from agents.report_reviewer_agent import run as run_report
    _run_agent("Report Reviewer Agent", run_report, errors, hours=24, report_type="일간")

    # 3단계: Performance Daily (DeFiLlama 3/3)
    log.info("[3/4] LINE 4: 일일 성과 측정...")
    from agents.performance_agent_daily import run as run_perf_daily
    _run_agent("Performance Agent Daily", run_perf_daily, errors, hours=24)

    # 4단계: Q&A Agent (DeFiLlama 미사용)
    log.info("[4/4] LINE 3: 커뮤니티 Q&A...")
    from agents.qa_agent import run as run_qa
    _run_agent("Q&A Agent", run_qa, errors, hours=24)

    # 파이프라인 종료 시 텔레그램 연결 정리
    tg_cleanup()

    # 에러 요약 알림
    if errors:
        error_msg = "\n".join(f"- {e}" for e in errors)
        send_message("urgent", f"[일일 파이프라인 오류 요약]\n\n실패한 에이전트:\n{error_msg}")
        log.warning(f"일일 파이프라인 완료 (오류 {len(errors)}건)")
    else:
        log.info("일일 파이프라인 정상 완료")


def weekly_pipeline():
    """매주 금요일 KST 11:30 실행 - 주간 파이프라인"""
    log.info("=" * 50)
    log.info("주간 에이전트 파이프라인 시작")
    log.info("=" * 50)

    # 파이프라인 시작 시 캐시 초기화 (새 데이터로 수집)
    clear_cache()
    errors = []

    # 1단계: Promotion Agent (마케팅 기획)
    log.info("[1/3] LINE 3: 마케팅 기획...")
    from agents.promotion_agent import run as run_promo
    _run_agent("Promotion Agent", run_promo, errors, hours=168)

    # 2단계: Performance Weekly (주간 성과)
    log.info("[2/3] LINE 4: 주간 성과 분석...")
    from agents.performance_agent_weekly import run as run_perf_weekly
    _run_agent("Performance Agent Weekly", run_perf_weekly, errors, hours=168)

    # 3단계: POC Agent (최종 보고서)
    log.info("[3/3] LINE 4: 상사 보고용 최종 리포트...")
    from agents.poc_agent import run as run_poc
    _run_agent("POC Agent", run_poc, errors, hours=168)

    # 파이프라인 종료 시 텔레그램 연결 정리
    tg_cleanup()

    # 에러 요약 알림
    if errors:
        error_msg = "\n".join(f"- {e}" for e in errors)
        send_message("urgent", f"[주간 파이프라인 오류 요약]\n\n실패한 에이전트:\n{error_msg}")
        log.warning(f"주간 파이프라인 완료 (오류 {len(errors)}건)")
    else:
        log.info("주간 파이프라인 정상 완료")


def main():
    """메인 스케줄러"""
    log.info("=" * 50)
    log.info("Variational AI Agent System 시작")
    log.info("11 Agents / 4 Lines / Auto Pipeline")
    log.info("=" * 50)

    # 환경변수 필수 검증
    _validate_env()

    # 일일 파이프라인: 매일 KST 11:00
    # schedule 라이브러리는 시스템 로컬 시간 기준으로 동작
    # Windows(KST) -> "11:00", 클라우드(UTC) -> "02:00"으로 변경 필요
    schedule.every().day.at("11:00").do(daily_pipeline)

    # 주간 파이프라인: 매주 금요일 KST 11:30
    schedule.every().friday.at("11:30").do(weekly_pipeline)

    log.info("스케줄 등록 완료:")
    log.info("  [매일] KST 11:00 - 트렌드->보고서->성과->Q&A")
    log.info("  [금요일] KST 11:30 - 마케팅->주간성과->POC 최종 리포트")
    log.info("대기 중... (Ctrl+C로 종료)")

    # 스케줄러 크래시 복구
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            log.info("사용자에 의해 종료됨")
            break
        except Exception as e:
            log.error(f"스케줄러 루프 오류 (자동 복구): {e}", exc_info=True)
            try:
                send_message("urgent", f"[시스템 오류]\n\n스케줄러 루프에서 오류 발생, 자동 복구 중\n오류: {str(e)[:500]}")
            except Exception:
                pass
            time.sleep(10)  # 짧은 대기 후 루프 재개


def _validate_env():
    """필수 환경변수 검증 — 누락 시 명확한 에러 메시지"""
    from config.settings import (
        ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN,
        TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNELS,
    )

    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_API_ID:
        missing.append("TELEGRAM_API_ID")
    if not TELEGRAM_API_HASH:
        missing.append("TELEGRAM_API_HASH")

    # 채널 검증
    for name, channel_id in TELEGRAM_CHANNELS.items():
        if not channel_id:
            missing.append(f"TG_CHANNEL_{name.upper()}")

    if missing:
        log.error(f"필수 환경변수 누락: {', '.join(missing)}")
        log.error(".env 파일을 확인하세요. (.env.example 참고)")
        sys.exit(1)

    log.info("환경변수 검증 완료 - 모든 필수 변수 설정됨")


if __name__ == "__main__":
    main()
