from urllib.parse import urlparse, parse_qs

def extract_youtube_id(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return ""
    u = url.strip()

    try:
        parsed = urlparse(u)
    except Exception:
        return ""

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "youtu.be" in host:
        return path.lstrip("/").split("/")[0]

    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if "v" in qs and len(qs["v"]) > 0:
            return qs["v"][0]
        if "/embed/" in path:
            return path.split("/embed/")[-1].split("/")[0]
        if "/shorts/" in path:
            return path.split("/shorts/")[-1].split("/")[0]

    return ""

def is_youtube_url(url: str) -> bool:
    return bool(extract_youtube_id(url))

def build_youtube_urls(url: str, start_sec: int) -> dict:
    vid = extract_youtube_id(url)
    s = int(start_sec) if start_sec and int(start_sec) > 0 else 0

    if not vid:
        return {"embed_url": "", "watch_url": (url or "").strip()}

    embed = f"https://www.youtube.com/embed/{vid}"
    watch = f"https://www.youtube.com/watch?v={vid}"

    if s > 0:
        embed = f"{embed}?start={s}"
        watch = f"{watch}&t={s}s"

    return {"embed_url": embed, "watch_url": watch}
