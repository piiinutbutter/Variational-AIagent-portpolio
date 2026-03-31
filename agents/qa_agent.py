"""
Q&A Agent
Market Follower Agent (Internal)이 수집한 커뮤니티 질문/피드백에 대해 최적의 답변 구상
최종 답변 초안을 Q&A+마케팅 채널로 전송
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect
from config.groups import VARIATIONAL_GROUPS
from utils.logger import get_logger

log = get_logger("QA")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 커뮤니티 Q&A 에이전트입니다.

역할:
- Variational 한국 커뮤니티에서 올라온 질문과 피드백을 수집
- 각 질문에 대해 최적의 답변 방향을 고민하고 답변 초안을 작성
- 피넛버터(한국 매니저)가 바로 사용할 수 있는 답변 제공

출력 형식:
1. 질문/피드백 목록
   각 항목마다:
   - 원본 질문/피드백 요약
   - 질문 유형 (기능 문의 / 버그 리포트 / 불만 / 제안 / 일반 질문)
   - 긴급도 (🔴높음 / 🟡중간 / 🟢낮음)
   - 답변 초안

2. 공통 이슈 정리
   - 반복적으로 나오는 질문/불만이 있으면 정리
   - 본사에 전달해야 할 피드백 별도 표시

답변 작성 원칙:
- Variational의 공식 입장에 맞게 작성
- 친절하되 정확하게
- 모르는 내용은 "확인 후 안내드리겠습니다"로 처리 (거짓 답변 금지)
- 기술적 질문은 가능한 쉽게 풀어서 설명
- 한국어로 작성
"""

def collect_questions(hours: int = 24, limit: int = 30) -> str:
    """커뮤니티에서 질문/피드백 수집"""
    all_data = []
    for group_name in VARIATIONAL_GROUPS:
        group, raw_messages = cached_collect(group_name, hours=hours, limit=limit)
        if not raw_messages:
            continue
        filtered = filter_messages(raw_messages)
        log.debug(f"{group}: {len(raw_messages)}개 → {len(filtered)}개")
        if filtered:
            all_data.append(format_messages(group, filtered, hours))
    return "\n\n".join(all_data)


def generate_answers(raw_data: str) -> str:
    """질문/피드백에 대한 답변 초안 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 Variational 커뮤니티 데이터에서 질문과 피드백을 찾아 답변 초안을 작성해줘:\n\n{raw_data}",
    )
    return result


def run(hours: int = 24):
    """에이전트 실행: 질문 수집 → 답변 생성 → 텔레그램 전송"""
    log.info("커뮤니티 질문 수집 시작...")
    raw_data = collect_questions(hours=hours)

    if not raw_data:
        log.warning("수집된 질문/피드백이 없습니다. (최근 메시지 없음)")
        return

    log.info("Claude 답변 작성 중...")
    answers = generate_answers(raw_data)

    if not answers:
        log.error("답변 생성 실패.")
        return

    # Q&A+마케팅 채널로 전송
    send_message("qa_marketing", f"💬 *[Q&A Agent - 커뮤니티 답변 초안]*\n\n{answers}")

    log.info("답변 초안 전송 완료.")
    return answers


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=168)
