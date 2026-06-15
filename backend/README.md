# 百灵 / 知更真实后端第一版

这个目录把当前静态站点后面的真实能力先搭起来：

- SQLite 数据库：`outputs/bailing.db`
- 每日定时采集：服务启动后每天本地时间 07:00 自动执行
- 手动采集接口：`POST /api/collect/run`
- 信息流接口：`GET /api/items`
- 信源健康接口：`GET /api/sources`
- 采集日志接口：`GET /api/runs`
- 知更工作台接口：
  - `POST /api/watchlists`
  - `GET /api/watchlists`
  - `POST /api/briefs/generate`
  - `GET /api/briefs`
  - `POST /api/impact-matrix`

## 本地启动

```powershell
python backend\server.py
```

启动后访问：

```text
http://127.0.0.1:8765/api/health
```

## 手动触发一次采集

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/collect/run -ContentType 'application/json' -Body '{}'
```

## 生成客户晨报

```powershell
$body = @{
  title = "新能源与汽车政策晨报"
  keywords = @("新能源", "汽车", "中小企业")
  categories = @("产业监管", "公司公告")
  limit = 10
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/briefs/generate -ContentType 'application/json' -Body $body
```

## 云端化需要补的东西

本地后端已经能跑真实逻辑，但要变成 24 小时在线服务，需要接入：

1. 云端运行环境：Render / Railway / Fly.io / Cloudflare Workers / VPS 任选其一。
2. 持久数据库：Supabase Postgres / Neon / Cloudflare D1 / 托管 SQLite。
3. 定时任务：GitHub Actions cron / 云平台 cron / Worker Cron。
4. 账号认证：Supabase Auth / Clerk / 飞书登录 / 自建邮箱验证码。
5. 大模型摘要：OpenAI API 或其他模型 API，用于正式摘要、影响矩阵和 PPT 素材卡生成。

