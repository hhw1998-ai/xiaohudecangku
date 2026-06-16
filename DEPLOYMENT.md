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

Render 环境变量里添加：

```text
DATABASE_URL=你的 Supabase Postgres 连接串
```

设置完成后，后端会自动从临时 SQLite 切换到 Supabase/Postgres。没有 `DATABASE_URL` 时仍会使用 SQLite 兜底。

## 4. 注意事项

Render 免费服务会休眠，第一次访问会慢一些。

如果 `/api/health` 返回的 `db` 是 `/tmp/bailing.db`，说明仍在使用临时库；如果返回 `postgres`，说明已经切到 Supabase 持久库。
