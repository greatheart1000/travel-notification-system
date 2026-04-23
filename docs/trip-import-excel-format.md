# 行程管理 Excel 导入格式（双表）

点击“Excel导入”后，系统会新增 **1 个旅行团**（一次导入一个文件），并自动写入：

- 行程表（sheet：`行程表` 或 `itinerary`）；
- 客人表（sheet：`客人表` 或 `guests`）。

## 1) 行程表（必填）

Sheet 名建议：`行程表`。

首行表头：

| 列名 | 是否必填 | 说明 |
| --- | --- | --- |
| `team_id` | 必填 | 团号（整份文件唯一） |
| `destination` | 必填 | 团名称/线路名 |
| `start_date` | 必填（可在首行填写） | 出发日期，建议 `YYYY-MM-DD` |
| `end_date` | 必填（可在首行填写） | 结束日期，建议 `YYYY-MM-DD` |
| `date` | 选填 | 行程日期（每天一行） |
| `route` | 选填 | 当日路线，例如 `乌鲁木齐 -> 布尔津` |
| `transport` | 选填 | 交通方式 |
| `hotel` | 选填 | 当晚酒店 |

说明：

- 第 2 行起，每行代表 1 天行程。
- `team_id/destination/start_date/end_date` 可只在首行填写，后续行留空。

## 2) 客人表（选填）

Sheet 名建议：`客人表`。

首行表头：

| 列名 | 是否必填 | 说明 |
| --- | --- | --- |
| `name` | 建议必填 | 客人姓名 |
| `phone` | 建议必填 | 手机号 |
| `notes` | 选填 | 备注/特殊要求 |

说明：

- 每行 1 位客人。
- 系统会将客人数量同步为团人数。

## 3) 样例文件（通过脚本生成，避免仓库提交二进制）

执行下面命令会在 `docs/samples/` 下生成 2 个 `.xlsx`：

```bash
PYTHONPATH=src python scripts/generate_trip_import_samples.py
```

生成文件：

- 自测样例：`docs/samples/trip-import-sample-tested.xlsx`
- 验证样例：`docs/samples/trip-import-sample-verify.xlsx`
