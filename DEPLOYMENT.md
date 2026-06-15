# 百灵 / 知更上线部署步骤

## 1. 推到 GitHub

在 GitHub 新建一个仓库，建议名称：

```text
bailing-zhigeng
```

本地执行：

```powershell
git init
git add .
git commit -m "Deployable bailing zhigeng backend"
git branch -M main
git remote add origin https://github.com/你的用户名/bailing-zhigeng.git
git push -u origin main
```

## 2. Render 部署后端

1. 打开 Render Dashboard。
2. New -> Blueprint。
3. 选择刚刚的 GitHub 仓库。
4. Render 会读取 `render.yaml`。
5. 点击 Apply / Deploy。

部署完成后会得到一个类似这样的地址：

```text
https://bailing-zhigeng-api.onrender.com
```

验证：

```text
https://你的Render地址/api/health
```

## 3. Supabase 数据库

现在仓库里已经准备了：

```text
backend/supabase_schema.sql
```

在 Supabase 项目里：

1. SQL Editor
2. New query
3. 粘贴 `backend/supabase_schema.sql`
4. Run

当前 Render 第一版仍使用 SQLite 快速上线。Supabase 表先建好，下一步把后端存储从 SQLite 切到 Supabase/Postgres。

## 4. 注意事项

Render 免费服务会休眠，第一次访问会慢一些。

当前 `render.yaml` 使用 `/tmp/bailing.db`，适合验证后端 API，但不适合长期保存历史数据。正式版要切到 Supabase。

