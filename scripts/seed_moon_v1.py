import pymysql


def seed():
    conn = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="123456",
        database="travel_notification_system",
        charset="utf8mb4",
        autocommit=True,
    )
    cursor = conn.cursor()

    # 1. 清理旧数据（可选，保持干净）
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE t_notification_rule_channel")
    cursor.execute("TRUNCATE TABLE t_notification_rule")
    cursor.execute("TRUNCATE TABLE t_notification_template")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # 2. 核心文案模板定义
    templates = [
        # --- 行前阶段 ---
        (
            "tpl-pre-3d",
            "行程前3天-联系确认",
            "sms",
            """亲爱的{{customer_name}}，我是月亮旅行管家。为您确认航班信息：{{flight_info}}。提醒带好证件。新疆近期气候{{climate}}，建议着装：{{dress_code}}。期待您的到来！""",
        ),
        (
            "tpl-pre-1d-welcome",
            "入群欢迎词",
            "wechat_work_group",
            """欢迎来到美丽的新疆！我是您的专属AI小管家小琪，联系电话17794941155。新疆的草原、雪山、沙漠，处处是景。一路上我会给您贴心服务，愿您玩得开心！""",
        ),
        (
            "tpl-pre-1d-tips",
            "乘机注意事项",
            "wechat_work_group",
            """亲爱的游客：明天大家就将奔赴新疆。注意事项：1.行李尺寸重量符合规定；2.重要证件随身携带；3.新疆气候多变注意防晒。国内航班建议提前2小时到达机场。祝旅途愉快！""",
        ),
        (
            "tpl-arrival-urumqi",
            "落地首日-乌鲁木齐推荐",
            "wechat_work_group",
            """旅途即将开始！今日推荐：1.国际大巴扎（美食琳琅满目）；2.新疆美术馆（需提前预约）；3.古生态园（汗血宝马基地）。【温馨提示】新疆有时差，用餐较晚，请随身携带身份证。""",
        ),
        # --- 行中：晨间 (按季节) ---
        (
            "tpl-morning-spring",
            "晨间提示-春季",
            "wechat_work_group",
            """亲爱的游客朋友早上好！春日新疆气候多变，早晚温差大，请务必注意添衣保暖。上车请务必系好安全带，祝您一路平安。""",
        ),
        (
            "tpl-morning-summer",
            "晨间提示-夏季",
            "wechat_work_group",
            """早上好！新疆夏季清晨虽凉爽，但午间紫外线极强，请准备好防晒霜、遮阳帽。记得随时补充水分。上车请系好安全带。""",
        ),
        (
            "tpl-morning-autumn",
            "晨间提示-秋季",
            "wechat_work_group",
            """亲爱的游客早上好！秋季清晨冷峻，请检查行李并增添外套。新的旅程充满精彩，请保持好心情。上车请系好安全带。""",
        ),
        (
            "tpl-morning-winter",
            "晨间提示-冬季",
            "wechat_work_group",
            """早上好！新疆冬季气温极低，建议着保暖羽绒服和防滑雪地靴。路面湿滑，请小步慢走。上车请系好安全带。""",
        ),
        # --- 行中：午间 (按季节) ---
        (
            "tpl-noon-summer",
            "午间提示-夏季防暑",
            "wechat_work_group",
            """时值中午，天气炎热。提示：西瓜消暑虽好，但尽量不要与肉类同食。若发现司机有困倦迹象，请及时提醒休息。注意防暑。""",
        ),
        (
            "tpl-noon-rainy",
            "特殊场景-下雨天",
            "wechat_work_group",
            """中午好！在这个雨天，愿这份温馨提示为您增添安心：1.检查雨具；2.道路湿滑，慢速行驶；3.选择室内餐厅就餐。祝您依然享受新疆雨景。""",
        ),
        # --- 特殊项目 ---
        (
            "tpl-scene-horse",
            "场景提示-骑马项目",
            "wechat_work_group",
            """❗骑马项目提示❗1.选正规马队；2.穿平底鞋长裤；3.不要从马后方靠近；4.如遇惊吓保持冷静，听从教练指挥。安全第一！""",
        ),
        (
            "tpl-scene-ski",
            "场景提示-滑雪日",
            "wechat_work_group",
            """明日滑雪提示：要穿厚羽绒服和防风滑雪服；准备护脸、雪镜、头盔；携带保温杯喝热水；充分热身降低风险。""",
        ),
        # --- 售后 ---
        (
            "tpl-post-farewell",
            "下团欢送词",
            "wechat_work_group",
            """旅程已结束，点点滴滴都成回忆。衷心感谢陪伴，愿您带着满满回忆踏上归程。月亮旅行团队一直在新疆欢迎您的下次到来！""",
        ),
        (
            "tpl-post-dissolve",
            "解散群文案",
            "wechat_work_group",
            """感谢欣然赴约月亮之旅。新疆沙海阔依旧，风里藏着未完的故事。本群即将解散，感恩相伴，顺颂时祺。""",
        ),
    ]

    # 3. 插入模板并获取ID
    tpl_map = {}
    for code, name, channel, content in templates:
        cursor.execute(
            "INSERT INTO t_notification_template (template_code, template_name, channel, content, notification_type) VALUES (%s, %s, %s, %s, 'daily_reminder')",
            (code, name, channel, content),
        )
        tpl_map[code] = cursor.lastrowid

    # 4. 定义规则逻辑
    rules = [
        ("RULE-PRE-3D", "T-3行程确认", "pre_trip", "morning", "normal", tpl_map["tpl-pre-3d"], 10),
        (
            "RULE-PRE-1D-1",
            "T-1进群欢迎",
            "pre_trip",
            "afternoon",
            "normal",
            tpl_map["tpl-pre-1d-welcome"],
            20,
        ),
        (
            "RULE-PRE-1D-2",
            "T-1安检注意事项",
            "pre_trip",
            "evening",
            "normal",
            tpl_map["tpl-pre-1d-tips"],
            21,
        ),
        (
            "RULE-MORNING-AUTO",
            "每日晨间温馨提示",
            "in_trip",
            "morning",
            "normal",
            tpl_map["tpl-morning-summer"],
            30,
        ),  # 逻辑层动态切换季节
        (
            "RULE-WEATHER-RAIN",
            "雨天特殊关怀",
            "in_trip",
            "all_day",
            "weather_alert",
            tpl_map["tpl-noon-rainy"],
            5,
        ),
        (
            "RULE-POST-THANKS",
            "下团欢送",
            "post_trip",
            "evening",
            "normal",
            tpl_map["tpl-post-farewell"],
            100,
        ),
    ]

    for code, name, stage, slot, scene, tid, prio in rules:
        cursor.execute(
            "INSERT INTO t_notification_rule (rule_code, rule_name, stage, time_slot, scene, template_id, priority) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (code, name, stage, slot, scene, tid, prio),
        )

    print("✅ 月亮旅行管家文案与规则库注入完成！")
    conn.close()


if __name__ == "__main__":
    seed()
