"""
텔레그램 모니터링 그룹 중앙 관리
모든 에이전트가 이 파일에서 그룹 정보를 가져감
그룹 추가/삭제 시 이 파일만 수정하면 전체 에이전트에 반영
"""

# === Variational 자체 커뮤니티 ===
VARIATIONAL_GROUPS = [
    "variational_io_KR",
]

# === 경쟁사 Perpetual DEX 한국 커뮤니티 ===
# DeFiLlama/CoinGecko 24h 거래량 기준 상위 Perpetual DEX
COMPETITOR_GROUPS = {
    "Hyperliquid": "Hyperliquid_KR",       # 24h $2.82B (DeFiLlama 1위)
    "edgeX": "edgexkoreachat",             # 24h $1.59B (DeFiLlama 3위)
    "GRVT": "GRVT_farmingchat",            # 24h $986M (DeFiLlama 5위)
    "Lighter": "Lighter_KR",               # 24h $973M (DeFiLlama 6위)
    "BasedApp": "krbased",                 # Hyperliquid 기반 Perpetual DEX SuperApp
    # Aster: 한국 커뮤니티 미발견 (DeFiLlama 2위)
}

# === 한국 크립토 KOL/뉴스 채널 ===
# 트렌드 리서치 전용 소스
KOL_CHANNELS = [
    "WeCryptoTogether",     # 코인같이투자 (4만+ 구독)
    "fireantcrypto",        # 불개미crypto (2만+ 구독, 에어드롭/온체인)
    "minchoisfuture",       # 청년열정(민초) (9천+ 구독, 리서치)
    "marshallog",           # 마샬공유방 (1.9만+ 구독, 경제+크립토)
    "magonia_b",            # 개처물린 마곤
    "fireantgroup",         # 잼민123
    "CryptoFamily_ilhyun",  # 코백남
    "shwhwgsicj",           # KOL 채널
    "pgyinfo",              # PGY 정보 채널
]

NEWS_CHANNELS = [
    "coinnesskr",           # 코인니스 뉴스피드 (실시간 크립토 뉴스)
    "shrimp_notice",        # 새우잡이어선 공지방 (거래소 공지/상장 정보)
    "dogeland01",           # 코인갤러리 (시장 뉴스/호재·악재 공시)
]

# === 조합 그룹 (에이전트별 편의용) ===

def get_trend_groups() -> list[str]:
    """트렌드 리서치용 전체 그룹 (경쟁사 + Variational + KOL + 뉴스)"""
    return (
        list(COMPETITOR_GROUPS.values())
        + VARIATIONAL_GROUPS
        + KOL_CHANNELS
        + NEWS_CHANNELS
    )
