"""FC entrypoint: serves FastAPI + frontend SPA + weather proxy on a single port."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.http import create_app

PORT = int(os.getenv("PORT", os.getenv("FC_SERVER_PORT", "9000")))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIST_DIR", "/code/frontend"))
QWEATHER_KEY = os.getenv("QWEATHER_API_KEY", "")
QWEATHER_HOST = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")

# ── Xinjiang city → QWeather location ID ──────
XINJIANG_CITIES: dict[str, str] = {
    "乌鲁木齐": "101130101",
    "喀什": "101130901",
    "伊犁": "101131001",
    "阿勒泰": "101131401",
    "吐鲁番": "101130501",
    "塔城": "101131101",
    "库尔勒": "101130601",
    "和田": "101131301",
}

app: FastAPI = create_app()

# ── Weather endpoint ───────────────────────────
_weather_client: httpx.AsyncClient | None = None

def _get_weather_client() -> httpx.AsyncClient:
    global _weather_client
    if _weather_client is None:
        _weather_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _weather_client


@app.get("/api/weather/xinjiang")
async def xinjiang_weather(_req: Request):
    """Fetch real-time weather + warnings for Xinjiang cities from QWeather."""
    if not QWEATHER_KEY:
        raise HTTPException(status_code=503, detail="QWeather API key not configured")

    client = _get_weather_client()
    results: list[dict] = []

    for city, loc_id in XINJIANG_CITIES.items():
        try:
            now_url = f"https://{QWEATHER_HOST}/v7/weather/now"
            warn_url = f"https://{QWEATHER_HOST}/v7/warning/now"
            params = {"location": loc_id, "key": QWEATHER_KEY}

            now_resp = await client.get(now_url, params=params)
            now_data = now_resp.json() if now_resp.status_code == 200 else {}

            warn_resp = await client.get(warn_url, params=params)
            warn_data = warn_resp.json() if warn_resp.status_code == 200 else {}

            now_info = (now_data.get("now") or {})
            warning_list = (warn_data.get("warning") or [])

            temp = now_info.get("temp", "N/A")
            weather_text = now_info.get("text", "")
            wind_dir = now_info.get("windDir", "")
            wind_scale = now_info.get("windScale", "")

            warning_str: str | None = None
            if warning_list and isinstance(warning_list, list) and len(warning_list) > 0:
                warning_str = warning_list[0].get("typeName", "天气预警")

            results.append({
                "city": city,
                "temp": temp,
                "weather": weather_text,
                "wind": f"{wind_dir}{wind_scale}级" if wind_dir else "N/A",
                "warning": warning_str,
            })
        except Exception:
            # fallback on single-city failure
            results.append({
                "city": city,
                "temp": "N/A",
                "weather": "获取失败",
                "wind": "N/A",
                "warning": None,
            })

    return {"code": 200, "data": {"cities": results}}


# ── Frontend SPA ───────────────────────────────
if FRONTEND_DIR.is_dir():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        print(f"[serve] mounted /assets from {assets_dir}", file=sys.stderr)

    index_path = FRONTEND_DIR / "index.html"

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        path = request.url.path
        if path.startswith(("/api/", "/assets/")) or path == "/health":
            return await call_next(request)

        file_path = FRONTEND_DIR / path.lstrip("/")
        if file_path.is_file():
            return FileResponse(str(file_path))

        if index_path.is_file():
            return FileResponse(str(index_path))

        return Response("index.html not found", status_code=500)

    print(f"[serve] SPA fallback ready, index={index_path}", file=sys.stderr)


def main():
    print(f"[serve] starting on 0.0.0.0:{PORT}", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
