#!/usr/bin/env python3
"""Seed a realistic QA workspace for 月亮旅行 and two partner agencies.

The data is fictional, but the names, routes, hotels, phones and message copy
follow how a Xinjiang travel agency actually works. Run against a fresh QA
database with:

    APP_ENV=dev SEED_DEMO_DATA=false SEED_DEMO_USERS=false
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:3001"
PASSWORD = "Demo123456"
TODAY = date(2026, 11, 13)


def call(method: str, path: str, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> {exc.code}: {body[:300]}") from exc


def login(username: str, password: str = PASSWORD) -> str:
    status, body = call("POST", "/api/auth/login", {"username": username, "password": password})
    assert status == 200, body
    return body["data"]["access_token"]


def register(tenant_name: str, username: str, phone: str) -> dict:
    _, code_body = call("POST", "/api/auth/sms-code", {"phone": phone, "purpose": "register"})
    code = code_body["data"]["debug_code"]
    status, body = call(
        "POST",
        "/api/auth/register",
        {
            "tenant_name": tenant_name,
            "username": username,
            "password": PASSWORD,
            "phone": phone,
            "code": code,
        },
    )
    assert status == 201, body
    return body["data"]


def update_user(admin_token: str, username: str, **fields):
    status, body = call(
        "PUT",
        f"/api/admin/users/{username}",
        fields,
        admin_token,
    )
    assert status == 200, body
    return body["data"]


def create_user(admin_token: str, profile: dict) -> dict:
    status, body = call(
        "POST",
        "/api/admin/users",
        {
            "username": profile["username"],
            "display_name": profile["display_name"],
            "password": PASSWORD,
            "email": profile["email"],
            "phone": profile["phone"],
            "role": profile.get("role", "guide"),
        },
        admin_token,
    )
    assert status == 201, body
    return body["data"]


def create_trip(admin_token: str, blueprint: dict) -> str:
    start = TODAY + timedelta(days=blueprint["offset"])
    end = start + timedelta(days=len(blueprint["days"]) - 1)
    status, body = call(
        "POST",
        "/api/trips",
        {
            "destination": blueprint["destination"],
            "team": blueprint["team_id"],
            "team_id": blueprint["team_id"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "participants": blueprint["participants"],
            "status": "planned",
        },
        admin_token,
    )
    assert status == 201, body
    trip_data = body["data"].get("trip", body["data"])
    trip_id = trip_data["id"]
    call(
        "PUT",
        f"/api/trips/{trip_id}",
        {
            "leader_name": blueprint["manager"],
            "contact_phone": blueprint["driver_phone"],
            "itinerary": build_itinerary(start, blueprint),
            "guests": make_guests(blueprint["guest_offset"], blueprint["participants"]),
        },
        admin_token,
    )
    return trip_id


def build_itinerary(start: date, blueprint: dict) -> list[dict]:
    rows = []
    last_index = len(blueprint["days"]) - 1
    for index, (activity, hotel) in enumerate(blueprint["days"]):
        if index == 0 and "接机" in activity:
            transport = "接机"
        elif index == last_index and "送机" in activity:
            transport = "送机"
        else:
            transport = blueprint.get("vehicle", "商务车")
        rows.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "type": transport,
                "activity": activity,
                "breakfast": "×" if index == 0 else "√",
                "lunch": "×" if index == 0 else "√",
                "dinner": "√" if index % 2 == 0 else "×",
                "hotel": hotel,
            }
        )
    return rows


GUEST_NAMES = [
    ("张慧", 34, "女", "13999102418", "zhanghui_88", "无"),
    ("王磊", 41, "男", "13899843651", "wanglei_xj", "无"),
    ("李佳", 29, "女", "13609917632", "lijia_0912", "素食"),
    ("陈思远", 37, "男", "18999950614", "chensiyuan", "无"),
    ("刘洋", 45, "男", "13579881903", "liuyang_trip", "需无烟房"),
    ("赵敏", 32, "女", "15099624178", "zhaomin_33", "带 7 岁儿童"),
    ("周建国", 58, "男", "13999251846", "zhoujianguo", "高血压，避免高强度徒步"),
    ("孙悦", 27, "女", "18699130827", "sunyue_27", "无"),
    ("马丽", 39, "女", "13779081256", "mali_xj", "不吃香菜"),
    ("吴桐", 31, "男", "15999143702", "wutong_31", "无"),
    ("郑凯", 36, "男", "18199850317", "zhengkai", "无"),
    ("何雨", 24, "女", "13659972840", "heyu_24", "无"),
    ("高翔", 43, "男", "13899132045", "gaoxiang", "膝关节不适，减少徒步"),
    ("林芳", 50, "女", "13999087612", "linfang_50", "无"),
    ("罗成", 28, "男", "15899210736", "luocheng", "无"),
    ("许静", 35, "女", "18690817429", "xujing_35", "清真餐"),
    ("蒋涛", 46, "男", "13579926018", "jiangtao", "无"),
    ("唐宁", 30, "女", "13999102718", "tangning", "无"),
    ("邓超", 33, "男", "13899843651", "dengchao", "无"),
    ("曹颖", 26, "女", "13609917632", "caoying", "无"),
    ("彭宇", 40, "男", "18999950614", "pengyu", "带 10 岁儿童"),
    ("苏晴", 38, "女", "13579881903", "suqing", "无"),
    ("韩冬", 52, "男", "15099624178", "handong", "无"),
    ("叶青", 29, "女", "13999251846", "yeqing", "无"),
]


def make_guests(offset: int, count: int) -> list[dict]:
    guests = []
    for index in range(count):
        name, age, gender, phone, wechat, notes = GUEST_NAMES[(offset + index) % len(GUEST_NAMES)]
        guests.append(
            {
                "name": name,
                "age": age,
                "gender": gender,
                "phone": phone,
                "wechat": wechat,
                "idCard": f"65010219880612{index + offset:04d}",
                "notes": notes,
            }
        )
    return guests


def create_template(
    admin_token: str,
    name: str,
    content: str,
    stage: str,
    time_slot: str,
    notification_type: str,
) -> str:
    status, body = call(
        "POST",
        "/api/notifications/templates",
        {
            "name": name,
            "content": content,
            "channel": "wechat_work_group",
            "notification_type": notification_type,
            "is_active": True,
            "stage": stage,
            "time_slot": time_slot,
            "scene": "normal",
        },
        admin_token,
    )
    assert status in (200, 201), body
    data = body.get("data") or {}
    if isinstance(data, dict):
        if data.get("id"):
            return str(data["id"])
        nested = data.get("template")
        if isinstance(nested, dict) and nested.get("id"):
            return str(nested["id"])
    return ""


def create_rule(admin_token: str, name: str, stage: str, slot: str, template_id: str, priority: int):
    status, body = call(
        "POST",
        "/api/notifications/rules",
        {
            "name": name,
            "stage": stage,
            "time_slot": slot,
            "scene": "normal",
            "channels": ["wechat_work_group"],
            "template_id": template_id or None,
            "enabled": True,
            "priority": priority,
            "conditions": {},
        },
        admin_token,
    )
    assert status in (200, 201), body


def set_invoice(admin_token: str, payload: dict):
    status, body = call("PUT", "/api/admin/tenant-profile", payload, admin_token)
    assert status == 200, body


GUIDES_A = [
    {"username": "zhaoyue", "display_name": "赵玥", "phone": "13999102718", "email": "zhaoyue@yueliangtravel.cn"},
    {"username": "wuhaoran", "display_name": "吴昊然", "phone": "13899843651", "email": "wuhaoran@yueliangtravel.cn"},
    {"username": "gulinazha", "display_name": "古丽娜扎", "phone": "13999251846", "email": "gulinazha@yueliangtravel.cn"},
    {"username": "wumaier", "display_name": "吾麦尔", "phone": "13609917632", "email": "wumaier@yueliangtravel.cn"},
    {"username": "linxi", "display_name": "林溪", "phone": "18699130827", "email": "linxi@yueliangtravel.cn"},
    {"username": "ayiguli", "display_name": "阿依古丽", "phone": "15099624178", "email": "ayiguli@yueliangtravel.cn"},
    {"username": "tianye", "display_name": "田野", "phone": "18999950614", "email": "tianye@yueliangtravel.cn"},
    {"username": "hujing", "display_name": "胡静", "phone": "13579881903", "email": "hujing@yueliangtravel.cn"},
]

GUIDES_B = [
    {"username": "kadier", "display_name": "卡迪尔", "phone": "13899132045", "email": "kadier@kashigar-travel.cn"},
    {"username": "mirensha", "display_name": "米仁沙", "phone": "13999087612", "email": "mirensha@kashigar-travel.cn"},
    {"username": "ailin", "display_name": "艾琳", "phone": "15899210736", "email": "ailin@kashigar-travel.cn"},
    {"username": "zhouqi", "display_name": "周琪", "phone": "18690817429", "email": "zhouqi@kashigar-travel.cn"},
    {"username": "sunhao", "display_name": "孙浩", "phone": "13579926018", "email": "sunhao@kashigar-travel.cn"},
]

GUIDES_C = [
    {"username": "yeerlan", "display_name": "叶尔兰", "phone": "13779081256", "email": "yeerlan@yili-outdoor.cn"},
    {"username": "wanglu", "display_name": "王璐", "phone": "15999143702", "email": "wanglu@yili-outdoor.cn"},
    {"username": "liangchen", "display_name": "梁辰", "phone": "18199850317", "email": "liangchen@yili-outdoor.cn"},
    {"username": "songyu", "display_name": "宋雨", "phone": "13659972840", "email": "songyu@yili-outdoor.cn"},
]

TRIPS_A = [
    {
        "destination": "北疆雪境 7 日｜乌鲁木齐·喀纳斯·禾木",
        "team_id": "YL-2026-1120-BJ",
        "offset": 7,
        "vehicle": "商务车",
        "guide": "zhaoyue",
        "manager": "赵玥",
        "concierge": "古丽娜扎",
        "driver": "马建军",
        "driver_phone": "13999104527",
        "participants": 12,
        "guest_offset": 0,
        "days": [
            ("乌鲁木齐地窝堡机场接机，入住酒店", "乌鲁木齐环球国际酒店"),
            ("乌鲁木齐—布尔津，S21 沙漠公路、五彩滩日落", "布尔津旅游宾馆"),
            ("布尔津—禾木，禾木村徒步、日落观景台", "禾木山庄"),
            ("禾木—喀纳斯，三湾徒步、喀纳斯湖", "喀纳斯阅湖酒店"),
            ("喀纳斯—布尔津，白哈巴村、边境公路", "布尔津旅游宾馆"),
            ("布尔津—乌鲁木齐，国际大巴扎", "乌鲁木齐环球国际酒店"),
            ("乌鲁木齐送机", "—"),
        ],
    },
    {
        "destination": "伊犁冬牧 6 日｜赛里木湖·那拉提",
        "team_id": "YL-2026-1125-YL",
        "offset": 12,
        "vehicle": "商务车",
        "guide": "wuhaoran",
        "manager": "吴昊然",
        "concierge": "林溪",
        "driver": "张卫国",
        "driver_phone": "13899810236",
        "participants": 8,
        "guest_offset": 4,
        "days": [
            ("乌鲁木齐接机，入住酒店", "乌鲁木齐环球国际酒店"),
            ("乌鲁木齐—赛里木湖，环湖公路", "赛里木湖点将台酒店"),
            ("赛里木湖—伊宁，六星街、喀赞其", "伊宁天缘国际酒店"),
            ("伊宁—那拉提，河谷草原", "那拉提金陵山庄"),
            ("那拉提—伊宁，伊犁河大桥日落", "伊宁天缘国际酒店"),
            ("伊宁送机", "—"),
        ],
    },
    {
        "destination": "南疆人文 8 日｜喀什古城·帕米尔",
        "team_id": "YL-2026-1130-NJ",
        "offset": 17,
        "vehicle": "越野车",
        "guide": "wumaier",
        "manager": "吾麦尔",
        "concierge": "阿依古丽",
        "driver": "艾力江",
        "driver_phone": "13999260417",
        "participants": 10,
        "guest_offset": 8,
        "days": [
            ("乌鲁木齐飞喀什，入住酒店", "喀什深业丽笙酒店"),
            ("喀什古城、艾提尕尔清真寺、百年老茶馆", "喀什深业丽笙酒店"),
            ("喀什—塔县，白沙湖、喀拉库勒湖", "塔县美巴酒店"),
            ("塔县石头城、阿拉尔金草滩", "塔县美巴酒店"),
            ("塔县—喀什，盘龙古道", "喀什深业丽笙酒店"),
            ("喀什老城、香妃园", "喀什深业丽笙酒店"),
            ("喀什自由活动，选购干果", "喀什深业丽笙酒店"),
            ("喀什送机", "—"),
        ],
    },
    {
        "destination": "吐鲁番暖冬 4 日｜火焰山·库木塔格",
        "team_id": "YL-2026-1205-TLF",
        "offset": 22,
        "vehicle": "商务车",
        "guide": "linxi",
        "manager": "林溪",
        "concierge": "胡静",
        "driver": "王强",
        "driver_phone": "13609928714",
        "participants": 6,
        "guest_offset": 12,
        "days": [
            ("乌鲁木齐—吐鲁番，坎儿井、葡萄沟", "吐鲁番火洲酒店"),
            ("火焰山、柏孜克里克千佛洞", "吐鲁番火洲酒店"),
            ("库木塔格沙漠，沙漠越野", "库木塔格沙漠营地"),
            ("吐鲁番—乌鲁木齐送机", "—"),
        ],
    },
    {
        "destination": "阿勒泰滑雪 5 日｜将军山·禾木",
        "team_id": "YL-2026-1210-ALT",
        "offset": 27,
        "vehicle": "越野车",
        "guide": "tianye",
        "manager": "田野",
        "concierge": "赵玥",
        "driver": "马建军",
        "driver_phone": "13999104527",
        "participants": 9,
        "guest_offset": 16,
        "days": [
            ("乌鲁木齐飞阿勒泰，入住酒店", "阿勒泰金桥大酒店"),
            ("将军山滑雪场全天滑雪", "阿勒泰金桥大酒店"),
            ("阿勒泰—禾木，雪原穿越", "禾木山庄"),
            ("禾木滑雪、村落漫步", "禾木山庄"),
            ("禾木—阿勒泰送机", "—"),
        ],
    },
    {
        "destination": "塔城边境 4 日｜巴克图·小白杨",
        "team_id": "YL-2026-1215-TC",
        "offset": 32,
        "vehicle": "商务车",
        "guide": "hujing",
        "manager": "胡静",
        "concierge": "林溪",
        "driver": "张卫国",
        "driver_phone": "13899810236",
        "participants": 7,
        "guest_offset": 20,
        "days": [
            ("乌鲁木齐—塔城，入住酒店", "塔城宁城宾馆"),
            ("巴克图口岸、红楼博物馆", "塔城宁城宾馆"),
            ("小白杨哨所、巴尔鲁克山", "塔城宁城宾馆"),
            ("塔城—乌鲁木齐送机", "—"),
        ],
    },
    {
        "destination": "库尔勒胡杨 5 日｜轮台·罗布人村寨",
        "team_id": "YL-2026-1220-KEL",
        "offset": 37,
        "vehicle": "商务车",
        "guide": "zhaoyue",
        "manager": "赵玥",
        "concierge": "阿依古丽",
        "driver": "艾力江",
        "driver_phone": "13999260417",
        "participants": 11,
        "guest_offset": 2,
        "days": [
            ("乌鲁木齐—库尔勒，入住酒店", "库尔勒康城建国酒店"),
            ("罗布人村寨、塔里木河", "库尔勒康城建国酒店"),
            ("轮台胡杨林公园", "轮台胡杨林酒店"),
            ("库尔勒—乌鲁木齐", "乌鲁木齐环球国际酒店"),
            ("乌鲁木齐送机", "—"),
        ],
    },
    {
        "destination": "和田人文 6 日｜约特干·达玛沟",
        "team_id": "YL-2026-1225-HT",
        "offset": 42,
        "vehicle": "商务车",
        "guide": "wuhaoran",
        "manager": "吴昊然",
        "concierge": "古丽娜扎",
        "driver": "王强",
        "driver_phone": "13609928714",
        "participants": 8,
        "guest_offset": 6,
        "days": [
            ("乌鲁木齐飞和田，入住酒店", "和田迎宾馆"),
            ("约特干遗址、和田夜市", "和田迎宾馆"),
            ("达玛沟佛教遗址", "和田迎宾馆"),
            ("玉龙喀什河、桑皮纸作坊", "和田迎宾馆"),
            ("和田—乌鲁木齐", "乌鲁木齐环球国际酒店"),
            ("乌鲁木齐送机", "—"),
        ],
    },
]

TRIPS_B = [
    {
        "destination": "帕米尔高原 5 日｜喀什·塔县",
        "team_id": "KS-2026-1121-PM",
        "offset": 8,
        "vehicle": "越野车",
        "guide": "kadier",
        "manager": "卡迪尔",
        "concierge": "米仁沙",
        "driver": "艾尼瓦尔",
        "driver_phone": "13899140527",
        "participants": 8,
        "guest_offset": 1,
        "days": [
            ("喀什接机，入住酒店", "喀什深业丽笙酒店"),
            ("喀什—塔县，白沙湖、喀拉库勒湖", "塔县美巴酒店"),
            ("塔县石头城、金草滩", "塔县美巴酒店"),
            ("塔县—喀什，盘龙古道", "喀什深业丽笙酒店"),
            ("喀什送机", "—"),
        ],
    },
    {
        "destination": "喀什老城非遗 3 日",
        "team_id": "KS-2026-1126-KS",
        "offset": 13,
        "vehicle": "商务车",
        "guide": "mirensha",
        "manager": "米仁沙",
        "concierge": "艾琳",
        "driver": "艾尼瓦尔",
        "driver_phone": "13899140527",
        "participants": 6,
        "guest_offset": 5,
        "days": [
            ("喀什接机，老城漫步", "喀什深业丽笙酒店"),
            ("艾提尕尔、百年老茶馆、土陶作坊", "喀什深业丽笙酒店"),
            ("香妃园、喀什送机", "—"),
        ],
    },
    {
        "destination": "塔县金草滩 4 日｜石头城·阿拉尔",
        "team_id": "KS-2026-1201-TX",
        "offset": 18,
        "vehicle": "越野车",
        "guide": "ailin",
        "manager": "艾琳",
        "concierge": "米仁沙",
        "driver": "玉素甫",
        "driver_phone": "13999081236",
        "participants": 7,
        "guest_offset": 10,
        "days": [
            ("喀什接机，办理边防证", "喀什深业丽笙酒店"),
            ("喀什—塔县，奥依塔克红山", "塔县美巴酒店"),
            ("石头城、阿拉尔金草滩", "塔县美巴酒店"),
            ("塔县—喀什送机", "—"),
        ],
    },
    {
        "destination": "慕士塔格徒步 6 日",
        "team_id": "KS-2026-1206-MSTG",
        "offset": 23,
        "vehicle": "越野车",
        "guide": "zhouqi",
        "manager": "周琪",
        "concierge": "卡迪尔",
        "driver": "玉素甫",
        "driver_phone": "13999081236",
        "participants": 10,
        "guest_offset": 14,
        "days": [
            ("喀什接机，行前说明会", "喀什深业丽笙酒店"),
            ("喀什—布伦口，适应海拔", "布伦口民宿"),
            ("慕士塔格大本营徒步", "慕士塔格营地"),
            ("大本营—塔县", "塔县美巴酒店"),
            ("塔县—喀什，盘龙古道", "喀什深业丽笙酒店"),
            ("喀什送机", "—"),
        ],
    },
    {
        "destination": "莎车非遗手作 3 日",
        "team_id": "KS-2026-1211-SC",
        "offset": 28,
        "vehicle": "商务车",
        "guide": "sunhao",
        "manager": "孙浩",
        "concierge": "艾琳",
        "driver": "艾尼瓦尔",
        "driver_phone": "13899140527",
        "participants": 9,
        "guest_offset": 18,
        "days": [
            ("喀什—莎车，入住酒店", "莎车宾馆"),
            ("十二木卡姆、艾德莱斯绸作坊", "莎车宾馆"),
            ("莎车—喀什送机", "—"),
        ],
    },
    {
        "destination": "英吉沙小刀工坊 2 日",
        "team_id": "KS-2026-1216-YJS",
        "offset": 33,
        "vehicle": "商务车",
        "guide": "kadier",
        "manager": "卡迪尔",
        "concierge": "米仁沙",
        "driver": "艾尼瓦尔",
        "driver_phone": "13899140527",
        "participants": 6,
        "guest_offset": 21,
        "days": [
            ("喀什—英吉沙，小刀工坊", "英吉沙宾馆"),
            ("英吉沙—喀什送机", "—"),
        ],
    },
]

TRIPS_C = [
    {
        "destination": "那拉提雪原 4 日",
        "team_id": "YL-OUT-2026-1122-NLT",
        "offset": 9,
        "vehicle": "越野车",
        "guide": "yeerlan",
        "manager": "叶尔兰",
        "concierge": "王璐",
        "driver": "巴合提",
        "driver_phone": "13779081642",
        "participants": 8,
        "guest_offset": 3,
        "days": [
            ("伊宁接机，入住酒店", "伊宁天缘国际酒店"),
            ("伊宁—那拉提，雪原穿越", "那拉提金陵山庄"),
            ("那拉提河谷草原、哈萨克家访", "那拉提金陵山庄"),
            ("那拉提—伊宁送机", "—"),
        ],
    },
    {
        "destination": "赛里木湖蓝冰 3 日",
        "team_id": "YL-OUT-2026-1127-SLM",
        "offset": 14,
        "vehicle": "商务车",
        "guide": "wanglu",
        "manager": "王璐",
        "concierge": "叶尔兰",
        "driver": "巴合提",
        "driver_phone": "13779081642",
        "participants": 7,
        "guest_offset": 7,
        "days": [
            ("伊宁接机，六星街", "伊宁天缘国际酒店"),
            ("赛里木湖环湖、蓝冰拍摄", "赛里木湖点将台酒店"),
            ("赛里木湖—伊宁送机", "—"),
        ],
    },
    {
        "destination": "昭苏天马 3 日",
        "team_id": "YL-OUT-2026-1202-ZS",
        "offset": 19,
        "vehicle": "商务车",
        "guide": "liangchen",
        "manager": "梁辰",
        "concierge": "宋雨",
        "driver": "阿依肯",
        "driver_phone": "15999150831",
        "participants": 6,
        "guest_offset": 11,
        "days": [
            ("伊宁—昭苏，入住酒店", "昭苏宾馆"),
            ("天马文化园、湿地公园", "昭苏宾馆"),
            ("昭苏—伊宁送机", "—"),
        ],
    },
    {
        "destination": "特克斯八卦城 2 日",
        "team_id": "YL-OUT-2026-1207-TKS",
        "offset": 24,
        "vehicle": "商务车",
        "guide": "songyu",
        "manager": "宋雨",
        "concierge": "王璐",
        "driver": "阿依肯",
        "driver_phone": "15999150831",
        "participants": 5,
        "guest_offset": 15,
        "days": [
            ("伊宁—特克斯，八卦城", "特克斯宾馆"),
            ("特克斯—伊宁送机", "—"),
        ],
    },
    {
        "destination": "喀拉峻徒步 5 日",
        "team_id": "YL-OUT-2026-1212-KLK",
        "offset": 29,
        "vehicle": "越野车",
        "guide": "yeerlan",
        "manager": "叶尔兰",
        "concierge": "梁辰",
        "driver": "巴合提",
        "driver_phone": "13779081642",
        "participants": 10,
        "guest_offset": 19,
        "days": [
            ("伊宁接机，行前说明会", "伊宁天缘国际酒店"),
            ("伊宁—喀拉峻，草原徒步", "喀拉峻营地"),
            ("喀拉峻—琼库什台", "琼库什台民宿"),
            ("琼库什台—特克斯", "特克斯宾馆"),
            ("特克斯—伊宁送机", "—"),
        ],
    },
    {
        "destination": "霍尔果斯口岸 2 日",
        "team_id": "YL-OUT-2026-1217-HRGS",
        "offset": 34,
        "vehicle": "商务车",
        "guide": "wanglu",
        "manager": "王璐",
        "concierge": "宋雨",
        "driver": "阿依肯",
        "driver_phone": "15999150831",
        "participants": 5,
        "guest_offset": 23,
        "days": [
            ("伊宁—霍尔果斯，口岸合作中心", "霍尔果斯宾馆"),
            ("霍尔果斯—伊宁送机", "—"),
        ],
    },
]


def templates_for_tenant(token: str, tenant_code: str):
    entries = [
        (
            "行前3天·证件与集合提醒",
            "【行前提醒】{{ customer_name }}，您参加的{{ destination }}行程将于{{ departure_date }}出发。请确认身份证件、航班或车次时间；新疆早晚温差大，保暖外套请随身携带。",
            "pre_trip",
            "morning",
            "pre_trip_reminder",
            10,
        ),
        (
            "行前1天·航班与物品确认",
            "【行前确认】{{ customer_name }}，明天出发。请再次核对身份证件、集合时间和航班信息，今晚早点休息。",
            "pre_trip",
            "evening",
            "pre_trip_reminder",
            20,
        ),
        (
            "行中早间·天气与集合",
            "【今日行程】{{ customer_name }}，早上好。今天{{ weather_text }}，请按约定时间集合，带好身份证件和随身物品。",
            "in_trip",
            "morning",
            "daily_reminder",
            30,
        ),
        (
            "行中午间·用餐与休息",
            "【午间提醒】{{ customer_name }}，中午好。请注意补水和休息，用餐后按约定时间集合。",
            "in_trip",
            "afternoon",
            "daily_reminder",
            40,
        ),
        (
            "行中晚间·次日行程",
            "【明日安排】{{ customer_name }}，今天行程结束。明日安排：{{ next_day_highlight }}。请早点休息，集合时间以群内通知为准。",
            "in_trip",
            "evening",
            "daily_reminder",
            50,
        ),
        (
            "行后回访·满意度",
            "【行程回访】{{ customer_name }}，感谢您参加{{ destination }}行程。欢迎分享照片和建议，我们会逐条记录。",
            "post_trip",
            "evening",
            "satisfaction",
            60,
        ),
    ]
    for index, (name, content, stage, slot, notification_type, priority) in enumerate(entries):
        template_id = create_template(token, f"{name}", content, stage, slot, notification_type)
        create_rule(token, name, stage, slot, template_id, priority)


def main() -> int:
    tenants = []

    admin_a = login("admin")
    update_user(
        admin_a,
        "admin",
        display_name="陈静",
        email="chenjing@yueliangtravel.cn",
        phone="13999100016",
    )
    set_invoice(
        admin_a,
        {
            "invoice_title": "月亮旅行（乌鲁木齐）旅行社有限公司",
            "tax_id": "91650102MA78XK2L3Q",
            "invoice_address": "乌鲁木齐市天山区解放北路 88 号",
            "invoice_phone": "0991-2826118",
            "invoice_bank_name": "中国银行乌鲁木齐市解放路支行",
            "invoice_bank_account": "1076668890123456789",
            "invoice_email": "finance@yueliangtravel.cn",
        },
    )
    guides_a = [create_user(admin_a, profile) for profile in GUIDES_A]
    create_user(
        admin_a,
        {
            "username": "liyuan",
            "display_name": "李媛",
            "phone": "13999115732",
            "email": "liyuan@yueliangtravel.cn",
            "role": "user",
        },
    )
    tenants.append(
        {
            "code": "A",
            "tenant_id": "tenant-a",
            "admin": "admin",
            "guides": guides_a,
            "trips": TRIPS_A,
        }
    )

    for code, tenant_name, admin_username, admin_name, phone, email, guides, trips in [
        (
            "B",
            "喀什古城旅行社",
            "kashigar_admin",
            "阿不都热依木",
            "13899140021",
            "abudureyimu@kashigar-travel.cn",
            GUIDES_B,
            TRIPS_B,
        ),
        (
            "C",
            "伊犁河谷户外俱乐部",
            "yili_admin",
            "李雪松",
            "13999370062",
            "lixuesong@yili-outdoor.cn",
            GUIDES_C,
            TRIPS_C,
        ),
    ]:
        registered = register(tenant_name, admin_username, phone)
        tenant_id = registered["tenant"]["tenant_id"]
        admin_token = registered["tokens"]["access_token"]
        update_user(
            admin_token,
            admin_username,
            display_name=admin_name,
            email=email,
        )
        set_invoice(
            admin_token,
            {
                "invoice_title": tenant_name,
                "tax_id": f"91650102MA78{code}K2L3Q",
                "invoice_address": "新疆喀什地区喀什市解放南路 66 号"
                if code == "B"
                else "新疆伊犁州伊宁市解放路 128 号",
                "invoice_phone": "0998-2826118" if code == "B" else "0999-8126118",
                "invoice_bank_name": "中国银行喀什分行"
                if code == "B"
                else "中国银行伊犁分行",
                "invoice_bank_account": f"10766688901234567{code}",
                "invoice_email": email,
            },
        )
        tenant_guides = [create_user(admin_token, profile) for profile in guides]
        tenants.append(
            {
                "code": code,
                "tenant_id": tenant_id,
                "admin": admin_username,
                "guides": tenant_guides,
                "trips": trips,
            }
        )

    trip_ids = []
    for tenant in tenants:
        token = login(tenant["admin"])
        guide_by_username = {item["username"]: item for item in tenant["guides"]}
        for index, blueprint in enumerate(tenant["trips"]):
            trip_id = create_trip(token, blueprint)
            guide = guide_by_username[blueprint["guide"]]
            call(
                "PUT",
                f"/api/trips/{trip_id}/assignments",
                {"user_ids": [guide["id"]]},
                token,
            )
            staff = [
                {"role": "manager", "name": blueprint["manager"], "phone": guide["phone"]},
                {"role": "concierge", "name": blueprint["concierge"], "phone": "13999121046"},
                {
                    "role": "driver",
                    "name": blueprint["driver"],
                    "phone": blueprint["driver_phone"],
                    "recipient_channel": "sms" if index == 0 else "",
                    "recipient_address": blueprint["driver_phone"] if index == 0 else "",
                },
            ]
            call("PUT", f"/api/trips/{trip_id}/staff", {"staff": staff}, token)
            trip_ids.append(
                {
                    "tenant": tenant["code"],
                    "trip_id": trip_id,
                    "destination": blueprint["destination"],
                    "guide": guide["display_name"],
                }
            )
        templates_for_tenant(token, tenant["code"])

    admin_a = login("admin")
    _, order_body = call(
        "POST",
        "/api/billing/orders",
        {"plan_code": "starter", "provider": "mock"},
        admin_a,
    )
    paid_order = order_body["data"]["order_no"]
    call("POST", f"/api/billing/orders/{paid_order}/mock-pay", token=admin_a)
    call(
        "POST",
        "/api/billing/orders",
        {"plan_code": "growth", "provider": "mock"},
        admin_a,
    )

    summary = {
        "tenants": [
            {
                "code": t["code"],
                "tenant_id": t["tenant_id"],
                "admin": t["admin"],
                "guides": len(t["guides"]),
            }
            for t in tenants
        ],
        "users": sum(1 + len(t["guides"]) + (1 if t["code"] == "A" else 0) for t in tenants),
        "trips": len(trip_ids),
        "trip_sample": trip_ids[:3],
        "paid_order": paid_order,
        "password": PASSWORD,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
