# 开发记录 (dev log)

label-studio develop 分支二次开发的操作与问答记录。由 Claude Code 维护,每次操作/问答后追加。

---

## 2026-11-10 — 首次跑通原生 label-studio(修复白屏)

**问题**: 注册后浏览器跳转白屏。终端报 `SuspiciousFileOperation: The joined path (/main.css) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)`,`GET /react-app/main.css` 与 `GET /react-app/main.js` 返回 400。

**根因**: 前端从未构建。develop 分支源码仓库不包含编译好的前端产物,`web/dist/apps/labelstudio/` 目录不存在。页面引用的 `/react-app/main.css`、`/react-app/main.js` 全部请求失败导致白屏。日志中的 `SuspiciousFileOperation` 只是缺失 manifest 时 `label_studio/core/utils/static_serve.py:69` 兜底逻辑的副作用错误(manifest 兜底路径 `/react-app/main.css` 被剥掉前缀后残留前导 `/`,`safe_join` 拒绝绝对路径),不是根因。

**执行的操作**:

1. 安装 bun 1.4.4(官方安装脚本,装到 `~/.bun/bin`,`.bashrc` 已更新 PATH;此前机器上只有 node v22 + npm)
   ```bash
   curl -fsSL https://bun.sh/install | bash
   ```
2. 安装前端依赖(1639 个包)
   ```bash
   cd web && bun install --frozen-lockfile
   ```
3. 构建前端(产物 → `web/dist/apps/labelstudio/`;vite 插件同时把 manifest 写入 `label_studio/core/static/js/manifest.json`)
   ```bash
   cd web && bun run build
   ```
4. 重新收集静态文件(使 manifest 进入 `label_studio/core/static_build/js/manifest.json`)
   ```bash
   python label_studio/manage.py collectstatic --noinput
   ```
5. 验证:临时起 8081 实例,确认页面引用哈希资源 URL,`main.js`/`style.css` 返回 200 后关闭。

**后续注意点**:

- `manifest_assets.py` 在导入时加载 manifest 到模块级变量 → 每次构建前端后必须**重启 runserver**,否则仍渲染未哈希 URL 而 400。
- 改前端代码 → `bun run build` + 重启 Django 生效;开发期可用 HMR:`bun run dev` + `FRONTEND_HMR=true`(见 `web/README.md`)。
- `runserver` 直接服务 `web/dist`(`core/urls.py:50`),纯前端改动不需要重新 collectstatic。
- 环境: conda env `py314`(`/home/znzz/anaconda3/envs/py314/bin/python`,Django 5.2.19);本地 postgres(postgres/postgres@localhost:5432);数据目录 `/home/znzz/.local/share/label-studio`。

---

## 2026-11-10 — 修复文件上传 500(RawPostDataException)

**问题**: 浏览器 "Upload Files" 时报 `You cannot access body after reading from request's data stream`(HTTP 500,`POST /api/projects/5/import`)。

**根因分析**:
- `core.middleware.py` 的 `ContextLogMiddleware.__call__` 在每个请求进视图**之前**无条件执行 `json.loads(request.body)`,把请求流读掉(裸 `except:` 吞掉所有异常)。
- DRF 3.18.3 的 `_load_stream` 发现 Django 侧 `_read_started=True` 且无 `_body` 缓存时,会访问 `request.body` → Django 5.2 抛 `RawPostDataException`;DRF 的兜底逻辑仅在 `request.POST` 已被 Django 解析时才生效(此处不满足),于是 500。
- Django 5.2.19 的 `body` 属性新增了 `DATA_UPLOAD_MAX_MEMORY_SIZE`(本项目设置 250MB,`base.py:700`)相关的读取限制逻辑,multipart 大文件上传时中间件的预读取更容易失败,异常被裸 except 吞掉后请求进入不可恢复状态。
- 用 wsgiref+Django WSGIRequest 独立脚本复现:curl 的 3MB/6MB multipart(新连接与 keep-alive 复用)读取均正常,用户浏览器失败的具体底层异常未完全定位,但根因(中间件预读 body)已确认。

**修改** (`label_studio/core/middleware.py` `ContextLogMiddleware`):
- multipart/form-data 请求体不再读取(文件上传 body 对上下文日志无意义,且预读会破坏 DRF 解析)。
- 其他类型保留原行为,但把裸 `except:` 改为 `except Exception as exc:` 并加 `logger.debug` 诊断日志。

**验证**:
- 语法检查通过;8081 测试实例上 multipart POST 到 DRF 视图正常(403 认证失败,无 500、无 traceback)。
- 用户 8080 服务器经 StatReloader 自动重启生效(新进程启动时间与补丁保存时间一致)。

**状态**: 待用户在浏览器重新上传验证。

---

## 待办 / 用户确认项

- [ ] 用户在终端重启 runserver 并刷新浏览器确认白屏修复(操作时服务器仍在旧进程运行)
- [ ] 用户在浏览器重新上传文件,确认 RawPostDataException 修复
