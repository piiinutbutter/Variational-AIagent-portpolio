"""
Claude API 호출 유틸리티
모든 에이전트가 공통으로 사용하는 LLM 모듈
싱글톤 클라이언트 + exponential backoff 재시도
"""
import time
import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")
import anthropic
from config.settings import ANTHROPIC_API_KEY
from utils.logger import get_logger

log = get_logger("LLM")

# 싱글톤 클라이언트
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic | None:
    """Anthropic 클라이언트 싱글톤"""
    global _client
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return None
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        log.debug("Anthropic 클라이언트 생성 (싱글톤)")
    return _client


def ask_claude(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """
    Claude API에 질문하고 답변을 받음 (재시도 포함)

    system_prompt: 에이전트의 역할/지시사항
    user_message: 분석할 데이터나 질문
    max_tokens: 최대 응답 길이
    """
    client = _get_client()
    if not client:
        return ""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
            )
            log.info(f"Claude API 호출 성공 (토큰: input={response.usage.input_tokens}, output={response.usage.output_tokens})")
            return response.content[0].text

        except anthropic.RateLimitError as e:
            wait = 2 ** attempt * 5  # 10s, 20s, 40s
            log.warning(f"Claude API rate limit (시도 {attempt}/{max_retries}), {wait}초 후 재시도...")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                wait = 2 ** attempt * 3  # 6s, 12s, 24s
                log.warning(f"Claude API 서버 오류 {e.status_code} (시도 {attempt}/{max_retries}), {wait}초 후 재시도...")
                time.sleep(wait)
            else:
                log.error(f"Claude API 오류 (복구 불가): {e}")
                return ""

        except anthropic.APIError as e:
            log.error(f"Claude API 오류: {e}")
            return ""

        except Exception as e:
            log.error(f"예상치 못한 오류: {e}")
            return ""

    log.error(f"Claude API 호출 실패 — {max_retries}회 재시도 후 포기")
    return ""
