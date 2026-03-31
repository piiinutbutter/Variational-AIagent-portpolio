"""
시장 데이터 수집 유틸리티
DeFiLlama + CoinGecko API를 활용한 실시간 Perp DEX 데이터
무료 API — 키 불필요
DeFiLlama: 하루 최대 3회 호출 제한
"""
import time
import os
import json
from datetime import datetime, date
import requests
from utils.logger import get_logger

log = get_logger("MarketData")

# DeFiLlama 일일 호출 제한 (최대 3회/일)
DEFILLAMA_DAILY_LIMIT = 3
DEFILLAMA_COUNTER_FILE = os.path.join(os.path.dirname(__file__), "..", ".defillama_counter.json")


def _get_defillama_count() -> tuple[str, int]:
    """오늘 DeFiLlama 호출 횟수 확인"""
    try:
        with open(DEFILLAMA_COUNTER_FILE, "r") as f:
            data = json.load(f)
            return data.get("date", ""), data.get("count", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return "", 0


def _increment_defillama_count():
    """DeFiLlama 호출 횟수 증가"""
    today = date.today().isoformat()
    current_date, count = _get_defillama_count()
    if current_date != today:
        count = 0
    count += 1
    with open(DEFILLAMA_COUNTER_FILE, "w") as f:
        json.dump({"date": today, "count": count}, f)


def _can_call_defillama() -> bool:
    """DeFiLlama 호출 가능 여부"""
    today = date.today().isoformat()
    current_date, count = _get_defillama_count()
    if current_date != today:
        return True
    return count < DEFILLAMA_DAILY_LIMIT

# 모니터링 대상 Perpetual DEX
MONITORED_DEXES = [
    "hyperliquid", "aster", "edgex", "grvt", "lighter", "variational",
]

# CoinGecko Perp DEX ID (거래량 추적용)
COINGECKO_PERP_DEXES = {
    "Hyperliquid": "hyperliquid_futures",
    "edgeX": "edgex",
    "GRVT": "grvt",
    "Lighter": "lighter",
    "Aster": "aster_futures",
    # Variational은 CoinGecko ID 확인 후 추가
}

# CoinGecko 토큰 ID (가격/시총 추적용)
TOKEN_IDS = {
    "Hyperliquid": "hyperliquid",
    "dYdX": "dydx-chain",
}


def get_perp_dex_volumes() -> str:
    """DeFiLlama에서 Perpetual DEX 거래량 순위 가져오기 (하루 최대 3회)"""
    if not _can_call_defillama():
        log.warning(f"DeFiLlama 일일 호출 한도({DEFILLAMA_DAILY_LIMIT}회) 도달. 스킵.")
        return ""

    try:
        _increment_defillama_count()
        url = "https://api.llama.fi/overview/derivatives?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
        response = requests.get(url, timeout=20)

        # Rate limit 시 재시도
        if response.status_code == 429:
            log.warning("DeFiLlama rate limit, 5초 후 재시도...")
            time.sleep(5)
            response = requests.get(url, timeout=20)

        if response.status_code != 200:
            log.warning(f"DeFiLlama 응답 코드: {response.status_code}")
            return ""

        data = response.json()
        protocols = data.get("protocols", [])
        if not protocols:
            return ""

        # total24h 또는 dailyVolume 필드 사용
        def get_volume(p):
            return p.get("total24h", 0) or p.get("dailyVolume", 0) or 0

        sorted_protocols = sorted(protocols, key=get_volume, reverse=True)

        output = "[DeFiLlama Perpetual DEX 거래량 순위]\n\n"
        output += f"{'순위':<4} {'프로토콜':<25} {'24h 거래량':<18} {'변화율':<10}\n"
        output += "-" * 60 + "\n"

        variational_rank = None

        for i, p in enumerate(sorted_protocols):
            name = p.get("name", "Unknown")
            volume = get_volume(p)
            change = p.get("change_1d", 0) or 0
            name_lower = name.lower()

            if "variational" in name_lower:
                variational_rank = i + 1

            is_monitored = any(dex in name_lower for dex in MONITORED_DEXES)

            if i < 10 or is_monitored:
                if volume >= 1e9:
                    vol_str = f"${volume/1e9:.2f}B"
                elif volume >= 1e6:
                    vol_str = f"${volume/1e6:.1f}M"
                else:
                    vol_str = f"${volume/1e3:.0f}K"
                chg_str = f"{change:+.1f}%" if change else "N/A"
                marker = " ⭐" if is_monitored else ""
                output += f"{i+1:<4} {name:<25} {vol_str:<18} {chg_str:<10}{marker}\n"

        if variational_rank:
            output += f"\n📍 Variational 현재 순위: {variational_rank}위"

        return output

    except Exception as e:
        log.error(f"DeFiLlama API 실패: {e}")
        return ""


def get_perp_dex_tvl() -> str:
    """DeFiLlama /protocols 엔드포인트에서 TVL 데이터 가져오기 (하루 최대 3회)"""
    if not _can_call_defillama():
        log.warning(f"DeFiLlama 일일 호출 한도({DEFILLAMA_DAILY_LIMIT}회) 도달. 스킵.")
        return ""

    try:
        _increment_defillama_count()
        url = "https://api.llama.fi/protocols"
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return ""

        data = response.json()

        output = "[DeFiLlama TVL 데이터 (모니터링 대상)]\n\n"
        output += f"{'프로토콜':<25} {'TVL':<15} {'1d 변화':<10} {'7d 변화':<10}\n"
        output += "-" * 60 + "\n"

        found = []
        for p in data:
            name = p.get("name", "").lower()
            if any(dex in name for dex in MONITORED_DEXES):
                tvl = p.get("tvl", 0) or 0
                change_1d = p.get("change_1d", 0) or 0
                change_7d = p.get("change_7d", 0) or 0

                if tvl >= 1e9:
                    tvl_str = f"${tvl/1e9:.2f}B"
                elif tvl >= 1e6:
                    tvl_str = f"${tvl/1e6:.1f}M"
                else:
                    tvl_str = f"${tvl/1e3:.0f}K"

                found.append({
                    "name": p.get("name"),
                    "tvl": tvl,
                    "tvl_str": tvl_str,
                    "change_1d": change_1d,
                    "change_7d": change_7d,
                })

        # TVL 높은 순 정렬
        found.sort(key=lambda x: x["tvl"], reverse=True)
        for f in found:
            output += f"{f['name']:<25} {f['tvl_str']:<15} {f['change_1d']:+.1f}%{'':>4} {f['change_7d']:+.1f}%\n"

        return output if found else ""

    except Exception as e:
        log.error(f"DeFiLlama TVL API 실패: {e}")
        return ""


def get_token_prices() -> str:
    """CoinGecko에서 토큰 가격/시총/변화율 가져오기"""
    if not TOKEN_IDS:
        return ""

    try:
        ids = ",".join(TOKEN_IDS.values())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        response = requests.get(url, timeout=15)
        data = response.json()

        output = "[CoinGecko 토큰 가격 데이터]\n\n"
        output += f"{'토큰':<15} {'가격':<12} {'24h 변화':<10} {'시총':<15}\n"
        output += "-" * 55 + "\n"

        for name, cg_id in TOKEN_IDS.items():
            if cg_id in data:
                info = data[cg_id]
                price = info.get("usd", 0)
                change = info.get("usd_24h_change", 0) or 0
                mcap = info.get("usd_market_cap", 0) or 0

                price_str = f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
                chg_str = f"{change:+.2f}%"
                mcap_str = f"${mcap/1e9:.2f}B" if mcap >= 1e9 else f"${mcap/1e6:.0f}M"

                output += f"{name:<15} {price_str:<12} {chg_str:<10} {mcap_str:<15}\n"

        return output

    except Exception as e:
        log.error(f"CoinGecko API 실패: {e}")
        return ""


def get_all_market_data() -> str:
    """전체 시장 데이터 수집 (DeFiLlama + CoinGecko)
    DeFiLlama는 volumes 또는 TVL 중 하나만 호출 (1회/파이프라인)"""
    parts = []

    log.info("DeFiLlama 거래량 데이터 수집 중...")
    volumes = get_perp_dex_volumes()
    if volumes:
        parts.append(volumes)

    # 거래량 실패 시 TVL로 대체 (단, 한도 초과가 아닌 경우만)
    if not volumes and _can_call_defillama():
        log.info("DeFiLlama TVL 데이터로 대체 수집 중...")
        tvl = get_perp_dex_tvl()
        if tvl:
            parts.append(tvl)

    log.info("CoinGecko 토큰 가격 데이터 수집 중...")
    prices = get_token_prices()
    if prices:
        parts.append(prices)

    return "\n\n".join(parts)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    result = get_all_market_data()
    if result:
        print(result)
