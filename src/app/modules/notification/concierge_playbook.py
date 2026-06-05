from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """管家执行流程步骤（用于SOP检查、任务生成）。"""

    stage: str
    timing: str
    checklist: tuple[str, ...] = field(default_factory=tuple)


WORKFLOW_STEPS: tuple[WorkflowStep, ...] = (
    WorkflowStep(
        stage="T-3天出发确认",
        timing="行程出发前三天",
        checklist=(
            "联系游客确认航班信息是否变动",
            "发送证件、气候、着装、饮食温馨提示",
            "打印行程单并发送给司导",
            "行程单纸质留档",
        ),
    ),
    WorkflowStep(
        stage="资源核验",
        timing="行程出发前",
        checklist=(
            "确认酒店按要求预定完成",
            "确认用车车型与司导配套满足游客需求",
            "确认无人机/户外桌椅/相机等特殊资源",
        ),
    ),
    WorkflowStep(
        stage="T-1天风控与建群",
        timing="行程落地前一天",
        checklist=(
            "检查保险购买完成",
            "监督司导短信通知并电话联系游客",
            "建立服务群",
            "向司导发送行程确认单、行程要求、操作流程、好评下团考核与奖励",
        ),
    ),
    WorkflowStep(
        stage="入群欢迎与岗位介绍",
        timing="行程出发前一天（内部沟通后）",
        checklist=(
            "邀请游客进群",
            "监督工作人员自我介绍（职责/服务内容/姓名/联系方式）",
            "发送入群欢迎词与乘机前温馨提示",
        ),
    ),
    WorkflowStep(
        stage="在途日常运营",
        timing="行程进行中每日",
        checklist=(
            "群内发送次日行程简介与注意事项",
            "特殊地区（高原/边境口岸/极寒/强紫外线）发送专项提醒",
            "早中晚发送对应话术（含季节版、雨天版、骑马版、滑雪版）",
            "协调游客、司导、旅行社问题并闭环",
        ),
    ),
    WorkflowStep(
        stage="下团售后",
        timing="行程结束后",
        checklist=(
            "发送欢送词",
            "执行满意度调查并反馈客服销售",
            "高品质游客建档并反馈销售",
            "发送解散群文案并解散群",
        ),
    ),
)


MESSAGE_TEMPLATES: dict[str, str] = {
    # 说明：MySQL 为主数据源（见 docs/mysql_schema_seed.sql 的 t_notification_template）。
    # 这里保留同名模板用于本地开发/离线回退场景。
    "group_welcome": (
        "欢迎来到美丽的新疆！我是您的专属AI小管家小琪，联系电话17794941155。"
        "新疆的草原、雪山、沙漠，处处是景。一路上我会给您贴心服务，分享景点玩法和地道美食。"
        "要是有任何需求，随时联系我。愿您在新疆玩得开心，收获满满美好回忆！"
    ),
    "pre_flight_notice": (
        "亲爱的游客朋友们：\n"
        "大家好！欢迎大家来到大美新疆。明天，大家就将从全国各地奔赴这片充满魅力的土地。"
        "为了确保大家的旅途顺利，请提前到达机场，国内航班建议提前2小时，国际航班建议提前3小时。"
        "请随身携带身份证/护照等重要证件，行李遵守航司尺寸重量规范，液体单瓶不超过100毫升。"
    ),
    "urumqi_day1_recommendations": (
        "我们的旅途即将开始，今天自由活动给大家推荐：国际大巴扎、新疆美术馆（需预约）、"
        "新疆古生态园·中国汗血宝马基地。新疆和内地有2小时时差，请大家早点休息倒时差。"
    ),
    "xinjiang_general_tips": (
        "🌟【新疆旅行通用须知·8项提醒】\n"
        "① 时差：新疆与内地相差2小时，作息请按当地时间，晚上10点天还亮是正常的；\n"
        "② 物价：景区周边物价偏高，建议提前在市区采购零食饮品；\n"
        "③ 安保：景区、商场进出需安检，请随身携带身份证，配合查验；\n"
        "④ 计量：新疆称重习惯用'斤'，购物时注意区分500g与1斤；\n"
        "⑤ 饮食：清真餐厅为主，猪肉制品较少；手抓饭、烤串、馕均为当地特色，可放心品尝；\n"
        "⑥ 网络：部分景区信号较弱，建议提前下载离线地图，重要联系请提前告知家人；\n"
        "⑦ 气候：昼夜温差大，早晚需备外套，防晒霜和唇膏全季必备；\n"
        "⑧ 语言：当地以普通话和维吾尔语为主，遇到少数民族朋友时微笑示意即可，尊重当地习俗。\n"
        "祝大家旅途愉快，有任何问题随时联系管家！"
    ),
    # ── 分岗位模板：格式 {time_slot}_{season}_{role} ──────────────────────────
    # role: manager=团期负责人  concierge=旅行管家  driver=司机
    # 变量：{{manager_name}} {{manager_phone}} {{concierge_name}} {{concierge_phone}}
    #       {{driver_name}} {{driver_phone}}
    "morning_spring_manager": (
        "大家早上好💐我是本次团期负责人{{manager_name}}（{{manager_phone}}），"
        "春日新疆早晚温差大，今日行程顺利推进，有任何行程问题随时联系我！"
    ),
    "morning_spring_concierge": (
        "亲爱的游客朋友们早上好💐我是旅行管家{{concierge_name}}（{{concierge_phone}}）～"
        "春日早晨凉、中午暖，出发前多备一件外套，身份证随身带，有需要随时找我！"
    ),
    "morning_spring_driver": (
        "各位早上好！我是司机{{driver_name}}（{{driver_phone}}），车辆已就绪。"
        "请大家上车后放好行李、系好安全带，老人小孩不坐前排，安全第一！"
    ),
    "morning_summer_manager": (
        "大家早上好💐团期负责人{{manager_name}}（{{manager_phone}}）在线！"
        "夏日新疆紫外线强，今日行程按计划推进，有问题第一时间找我协调。"
    ),
    "morning_summer_concierge": (
        "亲爱的游客朋友们早上好❤️管家{{concierge_name}}（{{concierge_phone}}）提醒："
        "出门防晒霜、遮阳帽、太阳镜必备，多补水，有需要随时叫我！"
    ),
    "morning_summer_driver": (
        "大家早上好！司机{{driver_name}}（{{driver_phone}}）这里，车辆已检查完毕。"
        "上车后请系好安全带，途中每2小时停车活动，保证大家舒适出行！"
    ),
    "morning_autumn_manager": (
        "大家早上好🌷团期负责人{{manager_name}}（{{manager_phone}}）为大家保驾护航！"
        "秋季早晚凉，请注意添衣，今日行程正常，有需要随时联系我。"
    ),
    "morning_autumn_concierge": (
        "亲爱的游客朋友们早上好🍂管家{{concierge_name}}（{{concierge_phone}}）提醒："
        "秋日早晨凉，厚外套和雨具记得带，身份证随身，有问题找我！"
    ),
    "morning_autumn_driver": (
        "大家早上好！司机{{driver_name}}（{{driver_phone}}）已准备就绪。"
        "秋路有弯道，上车系好安全带，行李放稳，我会开稳保大家安全！"
    ),
    "morning_winter_manager": (
        "大家早上好❄️团期负责人{{manager_name}}（{{manager_phone}}）在！"
        "冬季路面可能结冰，请注意防滑，今日行程有任何调整我会第一时间通知大家。"
    ),
    "morning_winter_concierge": (
        "亲爱的游客朋友们早上好❤️管家{{concierge_name}}（{{concierge_phone}}）提醒："
        "羽绒服、帽子、手套、雪地靴全部穿好，路面湿滑慢走，我陪大家全程！"
    ),
    "morning_winter_driver": (
        "大家早上好！司机{{driver_name}}（{{driver_phone}}），车辆已预热、防滑检查完毕。"
        "冬路湿滑我会放慢车速，上车请系好安全带，老人小孩不坐前排，放心交给我！"
    ),
    "noon_spring_manager": (
        "大家中午好🌷团期负责人{{manager_name}}提醒：中午好好休息，午后行程如有调整我会通知大家，有问题随时联系。"
    ),
    "noon_spring_concierge": (
        "《温馨提示💡》管家{{concierge_name}}提醒：春日午间渐暖，外出防晒补水，"
        "用餐注意卫生，下午行程愉快！"
    ),
    "noon_spring_driver": (
        "大家中午好！司机{{driver_name}}趁午休检查车辆，下午准时出发，用餐后请按时集合，不耽误大家看美景！"
    ),
    "noon_summer_manager": (
        "大家中午好☀️团期负责人{{manager_name}}提醒：午间避免暴晒，有问题随时联系我，下午安排已就绪！"
    ),
    "noon_summer_concierge": (
        "《温馨提示💡》管家{{concierge_name}}提醒：防暑降温及时补水，"
        "饮食清淡避免冰凉，午休好好休息，下午继续精彩！"
    ),
    "noon_summer_driver": (
        "大家中午好！司机{{driver_name}}午休充电，下午提前开空调等大家，用餐后准时集合不要拖延！"
    ),
    "noon_autumn_manager": (
        "大家中午好🍁团期负责人{{manager_name}}提醒：秋日午间温暖，好好用餐休息，下午行程继续，问题随时找我！"
    ),
    "noon_autumn_concierge": (
        "《温馨提示💡》管家{{concierge_name}}提醒：早晚温差大随身带外套，"
        "瓜果美食适量品尝，财物保管好，祝用餐愉快！"
    ),
    "noon_autumn_driver": (
        "大家中午好！司机{{driver_name}}去做车辆检查，下午有弯道路段会放慢车速，用餐后请准时集合！"
    ),
    "noon_winter_manager": (
        "大家中午好❄️团期负责人{{manager_name}}提醒：多喝热汤暖身，下午路况有变化我会提前告知，有问题找我！"
    ),
    "noon_winter_concierge": (
        "《温馨提示💡》管家{{concierge_name}}提醒：趁热就餐、选热饮，"
        "吃完别急着出门避免冷热交替，下午继续暖心之旅！"
    ),
    "noon_winter_driver": (
        "大家中午好！司机{{driver_name}}去预热车辆，下午上车即暖，路面湿滑注意防滑，集合准时我在等！"
    ),
    # ── 原有统一季节模板（兼容旧渠道/短信）─────────────────────────────────
    "morning_spring": (
        "亲爱的游客朋友们早上好💐春日新疆早晚温差大，请注意添衣保暖。"
        "上车后请妥善放置行李并全员系好安全带，行程途中请勿将身体伸出窗外。"
    ),
    "morning_summer": (
        "早上好💐新疆夏季紫外线强、早晚温差大，请携带遮阳帽、太阳镜、防晒霜并及时补水。"
        "上车后请全员系好安全带，老人小孩不建议坐前排。"
    ),
    "morning_autumn": (
        "早上好🌷秋季清晨较冷，请检查行李避免遗漏，并增加外套防寒。"
        "上车后请全员系好安全带，旅途平安顺利。"
    ),
    "morning_winter": (
        "早上好🌷新疆冬季清晨气温极低，请穿戴羽绒服、保暖裤、帽子围巾手套和防滑雪地靴。"
        "路面湿滑请小步慢行，行车全程系安全带。"
    ),
    "noon_spring": (
        "《温馨提示》大家中午好！新疆春季昼夜温差仍较大，请按体感增减衣物。"
        "中午阳光渐强，外出请做好防晒并及时补水，饮食注意卫生，避免肠胃不适。"
    ),
    "noon_summer": (
        "《温馨提示》中午天气炎热，请注意防暑降温、及时补水。"
        "如发现司机疲劳，请及时提醒停车休息；饮食请清淡，避免生冷与高油食物。"
    ),
    "noon_autumn": (
        "《温馨提示》入秋后新疆早晚温差大，请随身携带外套并关注降雨变化。"
        "中午可适当进行户外游览，注意防晒和财物安全，瓜果美食请适量食用。"
    ),
    "noon_winter": (
        "《温馨提示》天气转凉，请尽量趁热用餐并选择温热饮品，"
        "注意室内外温差，避免冷热交替引起不适。"
    ),
    "noon_rainy": (
        "中午好！雨天请检查雨具，注意路面湿滑，放慢脚步；"
        "就餐尽量选择室内，回到酒店及时更换干爽衣物，注意保暖。"
    ),
    "horse_riding_notice": (
        "景区有骑马自费项目，请选择正规马队并听从教练指挥，检查骑具，按规定路线骑行。"
        "其他自费项目请确认具备行业资质与保险。"
    ),
    "ski_day_notice": (
        "明日滑雪请准备保暖与防风防水装备，租用头盔雪镜等护具，滑雪前充分热身并按雪场规定选择雪道。"
    ),
    "evening_next_day_preview": (
        "亲爱的游客朋友们🌷明日将继续精彩行程，请关注天气与集合时间，退房时请带好随身物品。"
    ),
    "issue_coordination_notice": (
        "服务提示：如在行程中遇到车辆、酒店、景区、服务沟通等问题，"
        "请第一时间在群内@管家与司导，我们将联合旅行社快速响应并闭环处理。"
    ),
    "post_trip_survey_notice": (
        "感谢您本次新疆之行的信任与支持！烦请完成满意度问卷，"
        "您的建议将直接用于改进服务并同步客服销售跟进。"
    ),
    "farewell_message": (
        "亲爱的游客朋友们：感谢大家一路的陪伴与支持。若有服务不足之处，"
        "欢迎提出宝贵建议，我们会持续改进。祝您一路平安，生活幸福美满，欢迎再来新疆！"
    ),
    "group_close_message": (
        "感谢大家与我们共赴新疆之旅，一路包容互助、留下珍贵回忆。"
        "本群即将解散，感恩相伴，顺颂时祺。"
    ),
}


def get_template(template_key: str) -> str:
    """根据模板键读取管家话术。"""

    if template_key not in MESSAGE_TEMPLATES:
        raise KeyError(f"template key not found: {template_key}")
    return MESSAGE_TEMPLATES[template_key]
