"""
한국 커뮤니티 기반 Perp DEX Mindshare 산출기

데이터 소스:
1. 텔레그램 그룹 활성도 (메시지 수 + 조회수 + 댓글수)
2. X(Twitter) 반응량 (좋아요 + RT + 댓글 + 조회수)
3. KOL/뉴스 채널 프로젝트 언급 빈도

가중 평균: 텔레그램 40% + X 40% + KOL 20%

※ 이 지표는 "한국 커뮤니티 기반 관심도 지표"이며, 글로벌 mindshare가 아닙니다.
※ 추적 대상 6개 프로젝트 간 상대 비교용입니다.
"""
from config.groups import COMPETITOR_GROUPS, VARIATIONAL_GROUPS, KOL_CHANNELS, NEWS_CHANNELS
from utils.data_cache import cached_collect
from utils.logger import get_logger

log = get_logger("Mindshare")

# 프로젝트별 키워드 매핑 (텔레그램 KOL/뉴스 채널에서 언급 감지용)
PROJECT_KEYWORDS = {
    "Variational": ["variational", "베리에이셔널", "바리에이셔널"],
    "Hyperliquid": ["hyperliquid", "하이퍼리퀴드", "하퍼", "hl"],
    "edgeX": ["edgex", "엣지엑스"],
    "GRVT": ["grvt", "그래비티"],
    "Lighter": ["lighter", "라이터"],
    "BasedApp": ["basedapp", "based", "베이스드"],
}

# 가중치
WEIGHT_TELEGRAM = 0.4
WEIGHT_X = 0.4
WEIGHT_KOL = 0.2


def _calc_telegram_scores(hours: int = 24) -> dict[str, float]:
    """
    텔레그램 그룹별 활성도 점수 산출
    점수 = 메시지 수 + (총 조회수 / 100) + (총 댓글수 / 10)
    """
    scores = {}

    # Variational (여러 그룹일 경우 합산)
    scores["Variational"] = 0.0
    for group_name in VARIATIONAL_GROUPS:
        _, messages = cached_collect(group_name, hours=hours, limit=100)
        scores["Variational"] += _msg_activity_score(messages)

    # 경쟁사
    for project, group_name in COMPETITOR_GROUPS.items():
        _, messages = cached_collect(group_name, hours=hours, limit=100)
        scores[project] = _msg_activity_score(messages)

    return scores


def _msg_activity_score(messages: list[dict]) -> float:
    """메시지 리스트에서 활성도 점수 산출"""
    if not messages:
        return 0.0
    msg_count = len(messages)
    total_views = sum(m.get("views", 0) for m in messages)
    total_replies = sum(m.get("replies", 0) for m in messages)
    return msg_count + (total_views / 100) + (total_replies / 10)


def _calc_x_scores() -> dict[str, float]:
    """
    X(Twitter) 반응량 기반 점수 산출
    캐시된 X 데이터에서 프로젝트별 반응량 추출
    점수 = 좋아요 + RT×2 + 댓글 + (조회수 / 1000)
    """
    from utils.data_cache import cached_x_data

    scores = {name: 0.0 for name in PROJECT_KEYWORDS}
    x_data = cached_x_data()

    if not x_data or not x_data.strip():
        log.info("X 데이터 없음 — X mindshare 스킵 (유료 API 전환 시 활성화)")
        return scores

    # X 데이터 텍스트에서 프로젝트별 언급/반응 파싱
    lines = x_data.split("\n")
    current_project = None

    for line in lines:
        # "=== ProjectName (@handle) ===" 패턴 감지
        if line.startswith("=== ") and line.endswith(" ==="):
            for project in PROJECT_KEYWORDS:
                if project in line:
                    current_project = project
                    break
            else:
                current_project = None
            continue

        # 트윗 라인 파싱: "(likes: N, RT: N, replies: N, views: N)"
        if current_project and "likes:" in line:
            scores[current_project] += _parse_tweet_score(line)

    return scores


def _parse_tweet_score(line: str) -> float:
    """트윗 라인에서 반응량 점수 추출"""
    score = 0.0
    try:
        # likes
        if "likes:" in line:
            likes_part = line.split("likes:")[1].split(",")[0].strip()
            score += int(likes_part.rstrip(")"))
        # RT
        if "RT:" in line:
            rt_part = line.split("RT:")[1].split(",")[0].strip()
            score += int(rt_part.rstrip(")")) * 2
        # replies
        if "replies:" in line:
            replies_part = line.split("replies:")[1].split(",")[0].strip()
            score += int(replies_part.rstrip(")"))
        # views
        if "views:" in line:
            views_part = line.split("views:")[1].split(",")[0].strip()
            score += int(views_part.rstrip(")")) / 1000
    except (ValueError, IndexError):
        pass
    return score


def _calc_kol_scores(hours: int = 72) -> dict[str, float]:
    """
    KOL/뉴스 채널에서 프로젝트별 언급 빈도 산출
    각 채널의 메시지에서 프로젝트 키워드 매칭 횟수 계산
    """
    scores = {name: 0.0 for name in PROJECT_KEYWORDS}
    channels = KOL_CHANNELS + NEWS_CHANNELS

    for channel in channels:
        _, messages = cached_collect(channel, hours=hours, limit=50)
        if not messages:
            continue

        for msg in messages:
            text_lower = msg.get("text", "").lower()
            for project, keywords in PROJECT_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower:
                        scores[project] += 1
                        break  # 같은 메시지에서 같은 프로젝트 중복 카운트 방지

    return scores


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    """점수를 백분율(%)로 정규화"""
    total = sum(scores.values())
    if total == 0:
        # 데이터 없으면 균등 분배
        count = len(scores)
        return {name: round(100 / count, 1) if count > 0 else 0 for name in scores}
    return {name: round((score / total) * 100, 1) for name, score in scores.items()}


def calculate_mindshare(hours: int = 24) -> dict:
    """
    종합 Mindshare 산출

    Returns:
        {
            "telegram": {"Variational": 18.7, "Hyperliquid": 52.3, ...},
            "x_twitter": {"Variational": 15.2, "Hyperliquid": 48.1, ...},
            "kol": {"Variational": 22.0, "Hyperliquid": 35.5, ...},
            "total": {"Variational": 18.3, "Hyperliquid": 46.2, ...},
            "ranking": [("Hyperliquid", 46.2), ("Variational", 18.3), ...],
        }
    """
    log.info("한국 커뮤니티 Mindshare 산출 시작...")

    # 각 소스별 점수 산출
    tg_raw = _calc_telegram_scores(hours=hours)
    x_raw = _calc_x_scores()
    kol_raw = _calc_kol_scores(hours=min(hours * 3, 168))  # KOL은 더 넓은 범위

    # 정규화 (%)
    tg_pct = _normalize(tg_raw)
    x_pct = _normalize(x_raw)
    kol_pct = _normalize(kol_raw)

    # 가중 평균
    all_projects = list(PROJECT_KEYWORDS.keys())
    total = {}
    for project in all_projects:
        weighted = (
            tg_pct.get(project, 0) * WEIGHT_TELEGRAM
            + x_pct.get(project, 0) * WEIGHT_X
            + kol_pct.get(project, 0) * WEIGHT_KOL
        )
        total[project] = round(weighted, 1)

    # 순위 정렬
    ranking = sorted(total.items(), key=lambda x: x[1], reverse=True)

    log.info("Mindshare 산출 완료")

    return {
        "telegram": tg_pct,
        "x_twitter": x_pct,
        "kol": kol_pct,
        "total": total,
        "ranking": ranking,
    }


def format_mindshare(data: dict) -> str:
    """Mindshare 결과를 보고서용 텍스트로 포맷팅"""
    ranking = data["ranking"]
    tg = data["telegram"]
    x = data["x_twitter"]
    kol = data["kol"]

    lines = []
    lines.append("📊 Perp DEX 한국 커뮤니티 Mindshare")
    lines.append("※ 한국 텔레그램/X/KOL 채널 기반 관심도 지표 (글로벌 mindshare 아님)")
    lines.append("━" * 40)
    lines.append("")

    # 종합 순위 바 차트
    max_score = ranking[0][1] if ranking else 1
    for project, score in ranking:
        bar_len = int((score / max_score) * 14) if max_score > 0 else 0
        bar = "█" * bar_len + "░" * (14 - bar_len)
        lines.append(f"  {project:<14} {bar}  {score:>5.1f}%")

    lines.append("")
    lines.append("── 채널별 상세 ──")
    lines.append("")

    # 텔레그램
    lines.append("  [텔레그램 그룹 활성도] (가중치 40%)")
    for project, score in sorted(tg.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"    {project:<14} {score:>5.1f}%")
    lines.append("")

    # X
    lines.append("  [X(Twitter) 반응량] (가중치 40%)")
    for project, score in sorted(x.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"    {project:<14} {score:>5.1f}%")
    lines.append("")

    # KOL
    lines.append("  [KOL/뉴스 채널 언급] (가중치 20%)")
    for project, score in sorted(kol.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"    {project:<14} {score:>5.1f}%")

    lines.append("")
    lines.append("산출 기준: TG 그룹 메시지·조회·댓글 / X 좋아요·RT·댓글·조회 / KOL 언급 빈도")
    lines.append("가중 평균: 텔레그램 40% + X 40% + KOL 20%")

    return "\n".join(lines)


def get_mindshare_text(hours: int = 24) -> str:
    """Mindshare 산출 + 포맷팅 통합 함수 (에이전트에서 호출용)"""
    try:
        data = calculate_mindshare(hours=hours)
        return format_mindshare(data)
    except Exception as e:
        log.error(f"Mindshare 산출 실패: {e}")
        return ""


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    result = get_mindshare_text(hours=24)
    if result:
        print(result)
    else:
        print("Mindshare 산출 불가")
