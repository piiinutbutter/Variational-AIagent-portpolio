"""
메시지 사전 필터링 유틸리티
Kiwi 한국어 형태소 분석을 활용하여 의미 있는 메시지만 추출
"""
from kiwipiepy import Kiwi
from utils.logger import get_logger

log = get_logger("Filter")

kiwi = Kiwi()

# 중요 키워드 (이 키워드가 포함된 메시지는 무조건 통과)
IMPORTANT_KEYWORDS = {
    # 프로젝트/플랫폼 관련
    "업데이트", "출시", "런칭", "상장", "마이그레이션", "체인",
    "에어드롭", "이벤트", "보상", "리워드", "포인트", "클레임",
    "스테이킹", "언스테이킹", "예치", "출금", "입금",
    # 유저 피드백
    "버그", "오류", "에러", "문제", "불만", "개선", "요청",
    "피드백", "건의", "제안", "불편", "느리", "안됨", "안돼",
    # 시장/거래
    "거래량", "볼륨", "TVL", "유동성", "슬리피지", "수수료",
    "롱", "숏", "레버리지", "청산", "펀딩비",
    # 가격 예측/유저 심리/기대감
    "fdv", "FDV", "시총", "마켓캡", "mcap",
    "가격", "목표가", "고점", "저점", "신고가", "신저점", "ath",
    "달러", "센트", "배", "10x", "100x", "1000x",
    "오를", "오르", "내릴", "내리", "폭등", "폭락", "펌핑", "덤핑",
    "불장", "베어", "불", "곰", "bull", "bear", "pump", "dump",
    "기대", "희망", "걱정", "불안", "두렵", "무섭",
    "존버", "홀딩", "물타기", "손절", "익절", "매수", "매도",
    "언제", "얼마", "몇배", "전망", "예상", "예측",
    "토큰", "코인", "토크노믹스", "tokenomics",
    "tge", "TGE", "vesting", "베스팅", "언락", "unlock",
    # 경쟁사/프로젝트명
    "basedapp", "based", "베이스드",
    "variational", "hyperliquid", "하이퍼리퀴드",
    "edgex", "grvt", "lighter", "라이터",
    # 경쟁/비교
    "경쟁", "비교", "이동", "갈아타", "옮기",
    # 긴급
    "해킹", "익스플로잇", "취약점", "러그", "스캠", "사기",
    "점검", "장애", "중단", "긴급",
    # 영어 키워드
    "airdrop", "update", "launch", "listing", "migration",
    "bug", "error", "stake", "unstake", "claim",
    "volume", "tvl", "liquidity", "funding",
    "hack", "exploit", "rug", "scam",
    # 영어 가격/심리
    "price", "moon", "bullish", "bearish",
    "hold", "sell", "buy", "dip",
    "when", "how much", "prediction",
}

# 잡담 패턴 (이 패턴에 해당하면 제외)
NOISE_PATTERNS = {
    "ㅋㅋ", "ㅎㅎ", "ㄷㄷ", "ㅇㅇ", "ㅠㅠ", "ㅜㅜ",
    "ㄱㄱ", "ㅈㅈ", "ㅂㅂ", "ㄴㄴ",
    "gm", "gn", "good morning", "good night",
    "감사합니다", "감사해요", "고마워", "ㄳ",
    "안녕하세요", "안녕", "반갑", "하이",
}


# 형태소 태그 필터 (set으로 O(1) 조회)
_VALID_TAGS = {"NNG", "NNP", "VV", "VA"}


def extract_keywords(text: str) -> list[str]:
    """Kiwi를 사용하여 텍스트에서 핵심 명사/동사 추출"""
    try:
        tokens = kiwi.tokenize(text)
    except Exception:
        return []
    # 명사(NNG, NNP), 동사(VV), 형용사(VA) 추출
    return [token.form for token in tokens if token.tag in _VALID_TAGS and len(token.form) >= 2]


def is_important(text: str) -> bool:
    """메시지가 분석할 가치가 있는지 판단"""
    text_lower = text.lower()

    # 중요 키워드 포함 여부
    for keyword in IMPORTANT_KEYWORDS:
        if keyword in text_lower:
            return True

    # Kiwi 형태소 분석으로 실질 키워드 수 확인
    keywords = extract_keywords(text)
    # 실질 키워드가 3개 이상이면 의미 있는 문장으로 판단
    if len(keywords) >= 3:
        return True

    return False


def is_noise(text: str) -> bool:
    """잡담/노이즈 메시지인지 판단"""
    text_lower = text.lower().strip()

    # 짧은 잡담 패턴
    for pattern in NOISE_PATTERNS:
        if text_lower == pattern or (text_lower.startswith(pattern) and len(text_lower) < 15):
            return True

    # 이모지만 있는 메시지
    if all(not c.isalnum() and not c.isspace() for c in text):
        return True

    return False


def filter_messages(messages: list[dict]) -> list[dict]:
    """
    메시지 리스트를 필터링하여 의미 있는 메시지만 반환

    messages: [{"sender": ..., "text": ..., "date": ..., "views": ..., "replies": ...}, ...]
    """
    filtered = []
    for msg in messages:
        text = msg["text"]

        # 노이즈 제거
        if is_noise(text):
            continue

        # 중요 메시지 판별
        if is_important(text):
            filtered.append(msg)

    return filtered


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    # 테스트
    test_messages = [
        {"sender": "user1", "text": "ㅋㅋㅋㅋㅋ", "date": "2026-03-30", "views": 0, "replies": 0},
        {"sender": "user2", "text": "에어드롭 언제 나오나요?", "date": "2026-03-30", "views": 10, "replies": 3},
        {"sender": "user3", "text": "gm gm", "date": "2026-03-30", "views": 0, "replies": 0},
        {"sender": "user4", "text": "출금 오류가 계속 발생하고 있습니다 확인 부탁드립니다", "date": "2026-03-30", "views": 20, "replies": 5},
        {"sender": "user5", "text": "ㅇㅇ", "date": "2026-03-30", "views": 0, "replies": 0},
        {"sender": "user6", "text": "이번 업데이트에서 레버리지 최대 배율이 변경되었네요", "date": "2026-03-30", "views": 15, "replies": 2},
    ]

    result = filter_messages(test_messages)
    print(f"원본: {len(test_messages)}개 → 필터링 후: {len(result)}개\n")
    for m in result:
        print(f"  [PASS] {m['text']}")
