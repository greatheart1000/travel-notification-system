from __future__ import annotations

import os
import zipfile
from typing import Iterable


def _build_sheet_xml(headers: list[str], rows: Iterable[list[str]]) -> str:
    def to_col(index: int) -> str:
        value = index + 1
        result = ""
        while value:
            value, mod = divmod(value - 1, 26)
            result = chr(65 + mod) + result
        return result

    body: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    all_rows = [headers, *rows]
    for row_index, row in enumerate(all_rows, start=1):
        body.append(f'<row r="{row_index}">')
        for col_index, cell in enumerate(row):
            col_ref = to_col(col_index)
            text = str(cell)
            body.append(
                f'<c r="{col_ref}{row_index}" t="inlineStr"><is><t>{text}</t></is></c>'
            )
        body.append("</row>")
    body.append("</sheetData></worksheet>")
    return "".join(body)


def _write_sample(path: str, itinerary_rows: list[list[str]], guest_rows: list[list[str]]) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="行程表" sheetId="1" r:id="rId1"/>
    <sheet name="客人表" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="1"><xf xfId="0"/></cellXfs>
</styleSheet>"""

    sheet1 = _build_sheet_xml(
        headers=[
            "team_id",
            "destination",
            "start_date",
            "end_date",
            "date",
            "route",
            "transport",
            "hotel",
        ],
        rows=itinerary_rows,
    )
    sheet2 = _build_sheet_xml(headers=["name", "phone", "notes"], rows=guest_rows)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1)
        archive.writestr("xl/worksheets/sheet2.xml", sheet2)


def main() -> None:
    _write_sample(
        path="docs/samples/trip-import-sample-tested.xlsx",
        itinerary_rows=[
            [
                "TEAM-DEMO-TEST",
                "阿勒泰雪山体验团",
                "2026-07-03",
                "2026-07-06",
                "2026-07-03",
                "乌鲁木齐 -> 富蕴",
                "航班+大巴",
                "富蕴观景酒店",
            ],
            ["", "", "", "", "2026-07-04", "富蕴 -> 可可托海", "旅游巴士", "可可托海山庄"],
            ["", "", "", "", "2026-07-05", "可可托海 -> 阿勒泰", "旅游巴士", "阿勒泰迎宾酒店"],
        ],
        guest_rows=[
            ["赵一", "13800000001", "素食"],
            ["钱二", "13800000002", "靠窗房"],
            ["孙三", "13800000003", "晕车"],
        ],
    )
    _write_sample(
        path="docs/samples/trip-import-sample-verify.xlsx",
        itinerary_rows=[
            [
                "TEAM-DEMO-VERIFY",
                "伊犁花海轻徒步团",
                "2026-08-10",
                "2026-08-13",
                "2026-08-10",
                "乌鲁木齐 -> 伊宁",
                "航班",
                "伊宁花城酒店",
            ],
            ["", "", "", "", "2026-08-11", "伊宁 -> 昭苏", "旅游巴士", "昭苏草原营地"],
        ],
        guest_rows=[["周四", "13900000004", "无"], ["吴五", "13900000005", "儿童餐"]],
    )
    print("Generated sample excel files in docs/samples/")


if __name__ == "__main__":
    main()
