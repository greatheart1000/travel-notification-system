import os
from datetime import datetime
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# 获取模板目录绝对路径
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def generate_itinerary_pdf(trip_data: dict, itinerary_data: list, guests_data: list) -> bytes:
    """
    根据行程数据生成 PDF 报表的二进制字节流
    """
    template = env.get_template("itinerary_report.html")

    # 准备渲染数据
    context = {
        "title": f"客人名单表 - {trip_data.get('destination', '未知线路')}",
        "print_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trip": trip_data,
        "itinerary": itinerary_data,
        "guests": guests_data,
    }

    html_content = template.render(**context)

    # WeasyPrint 渲染
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)

    return pdf_file.getvalue()
