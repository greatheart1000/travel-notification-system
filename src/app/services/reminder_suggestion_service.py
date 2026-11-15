from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.modules.integration.weather_provider import WeatherInfo
from app.services.llm_service import polish_travel_message

REGION_TIPS: tuple[tuple[str, str], ...] = (
    (
        "喀纳斯",
        "喀纳斯山区早晚温差大，请备一件保暖外套；区间车排队时间较长，建议提前如厕并带好水和零食。",
    ),
    (
        "禾木",
        "禾木早晚温度偏低，村里步行较多，请穿舒适防滑的鞋，清晨拍摄注意保暖。",
    ),
    (
        "伊犁",
        "草原紫外线强、天气变化快，请做好防晒和防蚊；骑马时听从马队安排，不要独自远离队伍。",
    ),
    (
        "那拉提",
        "那拉提草原风大且天气变化快，请带好外套和雨具，游玩时注意脚下草坡与马道。",
    ),
    (
        "吐鲁番",
        "吐鲁番气温高、空气干燥，请少量多次补水，做好防晒，避免正午长时间暴晒。",
    ),
    (
        "喀什",
        "喀什老城步行较多，请穿舒适的鞋；尊重当地民俗，拍摄当地人前先征得同意。",
    ),
    (
        "塔县",
        "塔县海拔较高，属于高原地区，请放慢节奏、避免剧烈运动；边境地区请随身携带身份证和边防证。",
    ),
    (
        "帕米尔",
        "帕米尔高原海拔较高，请留意高原反应，避免剧烈运动，如有不适及时告知管家。",
    ),
    (
        "阿勒泰",
        "阿勒泰冬季寒冷，请穿防滑保暖鞋；滑雪时佩戴头盔护具，按能力选择雪道。",
    ),
    (
        "库尔勒",
        "南疆风沙较多，请备好口罩和润唇膏，注意补水，拍照时保护好眼睛和相机。",
    ),
    (
        "和田",
        "和田气候干燥、风沙较多，请多喝水，外出时做好防沙防晒。",
    ),
    (
        "乌鲁木齐",
        "乌鲁木齐早晚温差较大，请根据天气增减衣物，长途乘车注意休息。",
    ),
)

SPECIAL_TAGS: tuple[tuple[str, str, str], ...] = (
    ("骑马", "骑马安全提醒", "骑马时请佩戴头盔护具，听从马队和司导指挥，不要擅自策马奔跑。"),
    ("滑雪", "滑雪安全提醒", "滑雪前充分热身，佩戴头盔雪镜，按能力选择雪道，不要越级滑行。"),
    ("高原", "高原安全提醒", "高原地区请放慢节奏，避免剧烈运动，如有头痛胸闷及时告知管家。"),
    ("边境", "边境安全提醒", "边境地区请随身携带身份证和边防证，不擅自离队或拍摄敏感区域。"),
    ("极寒", "防寒保暖提醒", "极寒天气请穿防滑保暖鞋，戴好帽子手套，减少长时间户外停留。"),
    ("无人区", "无人区安全提醒", "无人区请全程跟随车队，不擅自离队，提前确认补给和通信。"),
    ("紫外线", "防晒提醒", "紫外线较强，请涂抹防晒霜、戴帽子和墨镜，及时补水。"),
)


WEATHER_GUIDANCE: tuple[tuple[tuple[str, ...], str, str, tuple[str, ...]], ...] = (
    (
        ("暴雪", "大雪", "雪"),
        "请穿防滑保暖鞋，减少长时间户外停留，关注集合时间与路线调整。",
        "检查车辆防滑链、轮胎和暖风，预留路上时间，准备室内备选行程。",
        ("司导检查车辆防滑装备", "集合时间提前 15 分钟", "准备室内备选景点"),
    ),
    (
        ("结冰", "道路结冰"),
        "路面湿滑，请穿防滑鞋，行走和上下车时扶稳慢行。",
        "检查路况与高速通行状态，避免急刹，必要时调整行车路线。",
        ("确认高速/景区道路通行状态", "提醒司导低速行驶", "为游客准备防滑提示"),
    ),
    (
        ("雨", "降雨", "暴雨"),
        "请随身携带雨具，注意路面湿滑，户外项目以群内调整通知为准。",
        "检查雨具和车辆雨刮，准备室内备选行程，关注景区开放状态。",
        ("准备雨具和室内备选行程", "关注景区开放状态", "提醒游客注意台阶湿滑"),
    ),
    (
        ("沙尘", "扬沙", "浮尘"),
        "请佩戴口罩和眼镜，减少户外停留，注意保护相机和呼吸道。",
        "关注能见度和景区开放状态，必要时压缩户外项目。",
        ("为游客准备口罩", "调整户外项目顺序", "提醒司导开启内循环"),
    ),
    (
        ("大风", "强风"),
        "请远离湖边、临时搭建物和高处边缘，听从现场工作人员引导。",
        "检查景区索道/游船开放状态，调整户外项目并提醒司导固定行李。",
        ("确认索道/游船状态", "调整户外项目", "提醒司导固定行李"),
    ),
    (
        ("高温", "炎热", "暑"),
        "请少量多次补水，做好防晒，避免正午长时间暴晒。",
        "调整正午户外安排，准备防暑药品和饮用水，关注游客状态。",
        ("调整正午户外安排", "准备防暑药品", "增加补水休息点"),
    ),
    (
        ("大雾", "雾"),
        "能见度较低，请跟紧队伍，注意脚下和集合时间变化。",
        "关注高速封路和能见度，预留路上时间，必要时推迟出发。",
        ("确认高速通行状态", "预留路上时间", "提醒司导开启雾灯"),
    ),
    (
        ("寒潮", "降温", "低温"),
        "请加强保暖，戴好帽子手套，减少长时间户外停留。",
        "提醒司导热车、准备热水，关注游客防寒装备是否齐全。",
        ("提醒游客补充保暖装备", "司导提前热车", "准备热水和姜茶"),
    ),
)


def weather_guidance(weather: WeatherInfo) -> dict[str, Any]:
    text = f"{weather.alert_title or ''} {weather.condition or ''}"
    for keywords, guest_tip, internal_tip, actions in WEATHER_GUIDANCE:
        if any(keyword in text for keyword in keywords):
            return {
                "guest_tip": guest_tip,
                "internal_tip": internal_tip,
                "actions": list(actions),
            }
    return {
        "guest_tip": "请关注天气变化，带好雨具和保暖衣物，集合时间以群内通知为准。",
        "internal_tip": "请司导检查车辆与路线，准备室内备选方案，必要时调整集合时间。",
        "actions": ["关注天气变化", "检查车辆与路线", "准备备选方案"],
    }


def _parse_date(raw: Any) -> date | None:
    value = str(raw or "").strip()[:10]
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def region_guidance(destination: str) -> str:
    text = str(destination or "")
    for keyword, tip in REGION_TIPS:
        if keyword in text:
            return tip
    return "新疆昼夜温差大，请随身带一件外套，注意补水防晒，集合时间以群内通知为准。"


def _tags(trip: dict[str, Any]) -> list[str]:
    raw = trip.get("scene_tags") or trip.get("tags") or []
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _day_for(trip: dict[str, Any], target: str) -> dict[str, Any] | None:
    itinerary = [item for item in (trip.get("itinerary") or []) if isinstance(item, dict)]
    return next(
        (item for item in itinerary if str(item.get("date") or "")[:10] == target),
        None,
    )


def _day_text(day: dict[str, Any] | None) -> str:
    if not day:
        return ""
    activity = str(day.get("activity") or day.get("title") or day.get("route") or "").strip()
    transport = str(day.get("type") or day.get("transport") or "").strip()
    hotel = str(day.get("hotel") or "").strip()
    parts = []
    if activity:
        parts.append(f"今日安排：{activity}。")
    if transport:
        parts.append(f"交通安排：{transport}。")
    if hotel:
        parts.append(f"入住酒店：{hotel}。")
    return "".join(parts)


def detect_suggestion(
    trip: dict[str, Any],
    weather: WeatherInfo | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any] | None:
    now = today or datetime.now(tz=ZoneInfo("Asia/Shanghai")).date()
    destination = str(trip.get("destination") or "本次行程")
    region_tip = region_guidance(destination)
    start = _parse_date(trip.get("start_date"))
    end = _parse_date(trip.get("end_date"))
    tags = _tags(trip)

    if weather is not None and (weather.alert_title or weather.warning_level):
        alert = weather.alert_title or f"{weather.condition}天气预警"
        guidance = weather_guidance(weather)
        tourist_content = (
            f"【天气提醒】{destination}当前{weather.condition}，{weather.temperature:.0f}℃。"
            f"{alert}。{guidance['guest_tip']}{region_tip}"
        )
        internal_content = (
            f"【内部协同】{destination}当前{weather.condition}，{weather.temperature:.0f}℃，"
            f"{alert}。{guidance['internal_tip']}"
            f"建议动作：{'；'.join(guidance['actions'])}。"
        )
        return {
            "situation": "weather_alert",
            "title": "天气异常提醒",
            "reason": f"检测到{alert}",
            "content": tourist_content,
            "region_tip": region_tip,
            "variants": [
                {
                    "key": "tourist",
                    "title": "游客群通知",
                    "audience": "游客群",
                    "content": tourist_content,
                },
                {
                    "key": "internal",
                    "title": "内部协同提醒",
                    "audience": "司导 / 管家",
                    "content": internal_content,
                },
            ],
            "suggested_actions": guidance["actions"],
        }

    for tag, title, tip in SPECIAL_TAGS:
        if any(tag in value for value in tags):
            content = (
                f"【{title}】{destination}行程包含{tag}场景。{tip}{region_tip}"
            )
            return {
                "situation": "special_scene",
                "title": title,
                "reason": f"行程包含「{tag}」场景",
                "content": content,
                "region_tip": region_tip,
            }

    if start is not None and now < start:
        days = (start - now).days
        if days <= 3:
            first_day = _day_for(trip, start.isoformat())
            content = (
                f"【行前提醒】{destination}行程将于 {start.isoformat()} 出发，还有 {days} 天。"
                f"{_day_text(first_day)}请提前整理证件与行李，保持手机畅通。{region_tip}"
            )
            return {
                "situation": "pre_trip",
                "title": "行前准备提醒",
                "reason": f"距离出发还有 {days} 天",
                "content": content,
                "region_tip": region_tip,
            }
        return None

    if start is not None and end is not None and start <= now <= end:
        day = _day_for(trip, now.isoformat())
        content = (
            f"【今日行程】{destination}，{now.isoformat()}。"
            f"{_day_text(day)}请按约定时间集合，带好证件和随身物品。{region_tip}"
        )
        return {
            "situation": "in_trip",
            "title": "今日行程提醒",
            "reason": "行程进行中",
            "content": content,
            "region_tip": region_tip,
        }

    if end is not None and now > end and (now - end).days <= 3:
        content = (
            f"【行程回访】{destination}行程已经结束。感谢大家的信任与配合，"
            "欢迎在群里分享旅途照片和感受，也欢迎提出宝贵建议。"
        )
        return {
            "situation": "post_trip",
            "title": "行程回访",
            "reason": "行程已结束，适合发送回访",
            "content": content,
            "region_tip": region_tip,
        }

    return None


async def generate_reminder_suggestion(
    trip: dict[str, Any],
    weather: WeatherInfo | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any] | None:
    suggestion = detect_suggestion(trip, weather, today=today)
    if suggestion is None:
        return None
    content, provider = await polish_travel_message(
        suggestion["content"],
        destination=str(trip.get("destination") or ""),
        scene=suggestion["title"],
    )
    variants = suggestion.get("variants")
    if variants:
        variants = [
            {
                **variant,
                "content": content
                if variant.get("key") == "tourist"
                else variant.get("content", ""),
            }
            for variant in variants
        ]
    return {
        **suggestion,
        "content": content,
        "variants": variants,
        "provider": provider,
        "generated_at": datetime.now(tz=ZoneInfo("Asia/Shanghai")).isoformat(),
    }
