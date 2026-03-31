"""
텔레그램 메시지 전송 유틸리티
모든 에이전트가 공통으로 사용하는 텔레그램 전송 모듈
"""
import time
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNELS
from utils.logger import get_logger

log = get_logger("TG_Sender")

# 텔레그램 메시지 길이 제한
MAX_MESSAGE_LENGTH = 4096


def _split_text(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """UTF-8 안전 분할 — 줄바꿈 기준으로 나눠 메시지 깨짐 방지"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # 줄바꿈 기준으로 분할 (문장 중간 잘림 방지)
        split_pos = text.rfind("\n", 0, max_len)
        if split_pos == -1 or split_pos < max_len // 2:
            # 줄바꿈이 없으면 공백 기준
            split_pos = text.rfind(" ", 0, max_len)
        if split_pos == -1 or split_pos < max_len // 2:
            # 공백도 없으면 최대 길이로 자름
            split_pos = max_len

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")

    return chunks


def _send_single(url: str, channel_id: str, text: str, use_markdown: bool = True) -> tuple[bool, bool]:
    """
    단일 메시지 전송 (재시도 포함)

    Returns: (성공 여부, Markdown 사용 가능 여부)
    """
    payload = {"chat_id": channel_id, "text": text}
    if use_markdown:
        payload["parse_mode"] = "Markdown"

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            return True, use_markdown

        # Markdown 파싱 에러 시 일반 텍스트로 재시도
        if use_markdown and "can't parse entities" in response.text:
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                return True, False  # Markdown 비활성 전파

        # Rate limit 시 대기 후 재시도
        if response.status_code == 429:
            retry_after = int(response.json().get("parameters", {}).get("retry_after", 3))
            log.warning(f"텔레그램 rate limit, {retry_after}초 대기...")
            time.sleep(retry_after)
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                return True, use_markdown

        log.error(f"전송 실패: {response.status_code} - {response.text[:200]}")
        return False, use_markdown

    except requests.RequestException as e:
        log.error(f"네트워크 오류: {e}")
        return False, use_markdown


def send_message(channel_name: str, text: str) -> bool:
    """
    지정된 채널로 텔레그램 메시지 전송

    channel_name: "urgent", "market", "content", "performance", "qa_marketing"
    text: 보낼 메시지 내용
    """
    channel_id = TELEGRAM_CHANNELS.get(channel_name)

    if not channel_id:
        log.error(f"채널 '{channel_name}'을 찾을 수 없습니다.")
        return False

    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = _split_text(text)

    # 단일 메시지
    if len(chunks) == 1:
        ok, _ = _send_single(url, channel_id, chunks[0])
        if ok:
            log.info(f"'{channel_name}' 채널로 메시지 전송 완료")
        return ok

    # 분할 전송 — 첫 청크에서 Markdown 실패 시 나머지도 일반 텍스트
    use_markdown = True
    failed_chunks = []

    for i, chunk in enumerate(chunks):
        ok, use_markdown = _send_single(url, channel_id, chunk, use_markdown)
        if not ok:
            failed_chunks.append(i + 1)
        # 청크 간 짧은 대기 (rate limit 방지)
        if i < len(chunks) - 1:
            time.sleep(0.5)

    if failed_chunks:
        log.error(f"'{channel_name}' 분할 전송 실패 (청크 {failed_chunks}/{len(chunks)})")
        return False

    log.info(f"'{channel_name}' 채널로 메시지 전송 완료 ({len(chunks)}개 분할)")
    return True
