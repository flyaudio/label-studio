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

**状态**: 修复已通过自动化验证(见下),待用户在浏览器最终确认。

### 补充:真正的根因(2026-11-10 第二轮排查)

第一轮补丁(跳过 multipart body 读取)后用户重试**仍报同样错误**,继续排查找到真正根因:

**根因**: `ContextLogMiddleware.__call__` / `process_request` 中的 `if 'server_id' not in request:` —— Django 的 `HttpRequest` 是可迭代对象(`__iter__` = `iter(self.readline, b"")`),`in` 判断会**逐行读取并耗尽整个请求体流**(readline 到 EOF),只设置 `_read_started=True`,不缓存 `_body` 也不设置 `_post`。之后 DRF 解析 multipart 时访问 `request.body` → `RawPostDataException`,且 DRF 的 `request.POST` 兜底逻辑不满足(`_post` 未设置)→ 500。

**完整机制**(与所有观察一致):
1. 原始代码:先 `json.loads(request.body)`(≤250MB 时成功缓存 `_body`,`in` 迭代内存副本无害;>250MB 时 `RequestDataTooBig` 被吞)→ 然后 `'server_id' not in request` 迭代读空流 → 500。用户上传(泡罩包装图片批量)很可能 >250MB(`DATA_UPLOAD_MAX_MEMORY_SIZE`,base.py:700)。
2. 第一轮补丁(跳过 multipart 读取)后:小文件也必挂——`in` 迭代成了唯一流消费点。
3. curl 3MB 复现正常:原代码先缓存了 `_body`,`in` 迭代无害。
4. 用探针(包装 `request.read` 记录调用栈)定位:`__call__` 第 216 行 `if 'server_id' not in request:` 触发 readline → 实锤。

**最终修复**(`label_studio/core/middleware.py` `ContextLogMiddleware`):
- `if 'server_id' not in request:` → `if not hasattr(request, 'server_id'):`(`__call__` 与 `process_request` 两处),不再迭代请求对象。
- 保留第一轮的 multipart 跳过逻辑(上传 body 对日志无意义,且避免超限读取)。
- 全库搜索确认无其他 `in request` 成员判断。

**验证**:
- DRF `APIClient.force_authenticate` 驱动真实 import 端点(完整中间件链):
  - 无扩展名文件 → 400 业务校验错误(此前是 500 RawPostDataException)
  - `test_tasks.json` → **201,`task_count: 2`**,上传成功

### 浏览器实测确认(2026-11-10,用户 Windows 浏览器上传)

- 小文件上传(3.7MB):视图入口 `read_started=False`(流完好)→ **201 成功**。RawPostDataException 修复确认。
- 大批量图片(287MB):返回 **400 业务校验错误** `Maximum total size of all files is 262144000 bytes, current size is 287263860 bytes` —— 这是 `TASKS_MAX_FILE_SIZE`(= `DATA_UPLOAD_MAX_MEMORY_SIZE`,250MB,base.py:700-702)的上限拦截,非 bug。可拆分批上传,或调大 `DATA_UPLOAD_MAX_MEMORY_SIZE` 环境变量(同时影响 `TASKS_MAX_FILE_SIZE` 与 Django 内存/临时文件切换阈值)。
- TEMP DEBUG 转储已从 `uploader.py` 删除。

### 问答:label-studio 跑 Ubuntu 服务器、Windows 浏览器上传本地图片

**没有问题**,标准 B/S 架构:图片经 HTTP multipart 上传到 Ubuntu,文件存服务器数据目录(`~/.local/share/label-studio`)。此前上传 500 是服务端中间件 bug,与客户端系统无关(curl/Linux 浏览器同样会触发)。注意点:单次上传 250MB 上限;runserver 仅开发用,生产换 gunicorn;以后配域名需设 `HOST` 环境变量。

### 问答:调大上传上限——改 base.py 与改 .env 是否一样

一样。`base.py:700` 的 `DATA_UPLOAD_MAX_MEMORY_SIZE = int(get_env('DATA_UPLOAD_MAX_MEMORY_SIZE', 250 * 1024 * 1024))` 逻辑是"环境变量优先,否则用代码默认值";`TASKS_MAX_FILE_SIZE` 直接引用它。改 base.py 默认值效果完全相同,且适合二次开发(随代码走);但若日后 `.env`/shell 里设置了同名环境变量会覆盖代码值。保存后 StatReloader 自动重启生效。

### 问答:标注页左下角 Previous task 按钮是否有快捷键

**没有**。按钮定义在 `web/libs/editor/src/components/BottomBar/CurrentTask.jsx`(点击调 `store.prevTask`/`nextTask`,仅向宿主事件总线 invoke 事件);编辑器快捷键表 `web/libs/editor/src/core/settings/keymap.json` 中没有任何绑定到任务切换的键,宿主 app 也未注册键盘监听。相关但不同的快捷键:`Ctrl+←/→` 是多图任务内切换图片、`Ctrl+Enter` 提交、`Ctrl+Space` 跳过任务。如需添加:keymap.json 加 `task:prev`/`task:next` 条目 + `AppStore.attachHotkeys()` 里 `hotkeys.addNamed(...)`,注意避开已占用的 `alt+left/right`(图片旋转)。

---

## 2026-11-10 — 新增任务切换快捷键(X-AnyLabeling 对齐:d 下一张 / a 上一张)

**需求**: 标注页底部栏 Previous/Next task 按钮原本无快捷键;要求与 X-AnyLabeling 一致,`d` 切下一张图(下一个任务),`a` 切上一张图(上一个任务)。

**改动**(3 个文件,均在 `web/libs/editor/src/`):
1. `core/settings/keymap.json`: 新增 `task:next`(key `d`)、`task:prev`(key `a`)命名键位条目。已确认 `a`/`d` 单键无冲突(工具键位为 V/B/R/O/E/K/W/P/M/H/U,数字用于区域选择;输入框场景 keymaster 自动切 INPUT_SCOPE 不触发)。
2. `stores/AppStore.js` `attachHotkeys()`: 绑定 `hotkeys.addNamed("task:next"/"task:prev", ...)`,带 `hydrated/isLoading/noTask` 守卫;`nextTask()`/`prevTask()` 自身有 `canGoNextTask`/`canGoPrevTask` 守卫,首个/末个任务时按键为惰性。
3. `components/BottomBar/CurrentTask.jsx`: 两个按钮的 Tooltip 换为 `Hotkey.Tooltip`(name=task:prev/task:next),悬停显示 `a`/`d` 键位提示;移除不再使用的 `Tooltip` import。

**行为差异说明**: 按钮"Next task"在队列末尾会变成"Postpone task"(点击走 `postponeTask`,保存草稿并跳过);快捷键 `d` 只做纯导航(队列末尾时无动作),更贴近 X-AnyLabeling 的"下一张图"语义,避免意外的草稿/跳过副作用。

### 追问与调整(2026-11-11):d 与按钮行为完全一致

用户测试后要求:`d` 与按钮行为完全一致(队列末尾时自动变 Postpone)。

**重构**(消除按钮与快捷键的判断逻辑重复):
- `AppStore.js` views 新增 `nextButtonState` getter:集中原先散在 `CurrentTask.jsx` 的 next/postpone 判断(含企业版 skip 限制、FF_LEAP_1173、review/postpone 接口、requiresAnnotationSubmission 等),导出 `{ canNavigateNext, canPostponeTask, requiresAnnotationSubmission, canSkipOrPostpone }`。
- `AppStore.js` actions 新增 `nextOrPostpone()`:`canNavigateNext` → `nextTask()`,否则 `canPostponeTask` → `postponeTask()`(内部含 hydrated/isLoading/noTask 守卫)。
- `task:next` 快捷键改调 `self.nextOrPostpone()`;`task:prev` 不变。
- `CurrentTask.jsx` 改为消费 `store.nextButtonState`(显示状态与文案)+ `onClick={store.nextOrPostpone}`,删除重复计算和不再使用的 import(MANAGER_ROLES、isDefined、FF_LEAP_1173/isFF)。MANAGER_ROLES 常量移入 AppStore。

**待验证**: 构建 → collectstatic → 用户重启 runserver 后浏览器实测。

---

## 2026-11-11 — 修复 MST "Failed to resolve reference '3' to type 'User'" 报错

**问题**: 用户在 Data Manager/标注页点击某操作后,页面报 `Error: [mobx-state-tree] Failed to resolve reference '3' to type 'User' (from node: /taskStore/list/8/updated_by/0/user)`。

**根因**:
- DM 任务模型的 `updated_by`/`annotators`/`reviewers` 字段是 `Assignee` 数组,其 `user` 是 `types.reference(User)`(后端只返回 `{'user_id': 3}`,`Assignee.preProcessSnapshot` 将其转为裸 ID 引用)。
- DM 的 UsersStore 初始为空(`users: types.optional(types.array(User), [])`),而填充它的 `fetchUsers`(AppStore.js:626,调 `/api/users` 拉组织成员)在**整个代码库中没有任何调用者**——develop 分支回归/死代码。于是任何引用解析(MST 解引用)都会抛错。
- 触发条件:任务列表中存在 `updated_by=3` 的任务(项目 7 有 5 个,user 3 = test@b.com),UI 渲染/序列化用户信息时解引用失败。
- 与本次会话的快捷键改动无关(改动仅在 editor 库的底部栏/store)。

**修复**(`web/libs/datamanager/src/stores/AppStore.js`):
- `fetchUsers` 加已加载守卫(`self.users.length > 0` 时跳过)。
- `fetchData`(Data Manager 与 Label Stream 的统一初始化入口,app-create.jsx:93 调用)开头 `yield self.fetchUsers()`,try/catch 包裹,加载失败不阻塞页面。用户在任务列表渲染前就位,引用可解析。
- `/api/users` 已验证:返回纯数组,含组织全部 3 个用户(1@qq.com、a@b.com、test@b.com);User MST 模型 preProcessSnapshot 对缺字段有默认值,可安全 push。

**待验证**: 构建 → collectstatic → 用户重启 runserver 后复现原操作。

### 问答:导出标注文件名为何带 `0181e702-` 前缀

上传文件存储时由 `upload_name_generator`(`data_import/models.py:25-31`)统一命名:`8位随机UUID前缀-原文件名`,存入 `upload/<项目ID>/`。前缀是上传时生成的 `uuid.uuid4()[:8]`,用于防止同名文件冲突(多人/多次上传同名文件不互相覆盖)。服务器只保留带前缀的存储名,原文件名未单独记录,因此按任务存储文件名导出的标注 `.txt` 也带前缀。代码库中无 `PRESERVE_FILE_NAME` 类开关。用户暂未要求改;如需保留原名,可改为"仅重名时加前缀"(仅影响新上传)。

---

## 2026-11-11 — 导出选项:是否包含未标注任务(空白标注+对应图片)

**需求**: 导出对话框增加选项,控制"没有标注的图片是否导出空白标注和对应图片"。用户决策:适用于**所有导出格式**、**默认开启**;实际使用格式为 YOLO(txt)与 JSON/CSV。

**方案**(已批准实施):
- 前端 `web/apps/labelstudio/src/pages/ExportPage/ExportPage.jsx`:Form 内新增 `Toggle name="download_all_tasks" defaultChecked`,label "Include unlabeled tasks" + description。`assembleFormData({full, booleansAsNumbers})` 自动把 1/0 作为查询参数发出,无需改 proceedExport。复用了 `components/Form/Elements/Toggle`。
- 后端**零改动**:旧同步导出接口 `GET /api/projects/{pk}/export` 的 `ExportParamSerializer.download_all_tasks`(serializers.py:233)与 `ExportAPI.get` 的 `only_finished` 过滤(api.py:218-231)已存在该参数——`download_all_tasks=1` 时去掉 `annotations__isnull=False` 过滤,未标注任务以 `annotations: []` 进入导出。API 默认保持 False(默认开启仅 UI 层)。
- 顺带清理:`data_export/api.py:223,245` 两行遗留调试 `print()`。

**各格式空白标注行为**(外部依赖 label-studio-sdk 转换器已支持,无需改动):
- JSON: 未标注任务输出 `"annotations": []`
- CSV: 空标注行
- YOLO / YOLO_WITH_IMAGES: 空 .txt(0 字节)+ 图片(带图格式)
- VOC: 跳过未标注任务(用户不用,已知限制)

**验证**(APIClient 驱动,项目 7 子集 5 任务:3 已标注 + 2 未标注):
- YOLO + `download_all_tasks=1`:5 个 txt(2 个空 0 字节);`=0`:仅 3 个已标注 txt ✓
- JSON + `=1`:5 任务,2 个 `annotations: []` ✓;CSV 200 ✓
- YOLO_WITH_IMAGES + `=1`:未标注任务空 txt + 对应 .bmp(3.6MB)均入包 ✓

**注意**: 普通 YOLO 格式不含图片(带图是 YOLO_WITH_IMAGES 的职责);要"对应图片"须选带图格式。

**待验证**: 构建 → collectstatic → 用户重启 runserver + 硬刷新,UI 实测 Toggle 默认勾选、导出对比。

### 用户实测反馈与修复(2026-11-11)

用户用 `YOLO_OBB_WITH_IMAGES` 导出时报 `KeyError: 'image'`(converter.py:1028 `item['input'][data_key]`)。Toggle 工作正常(URL 已带 `download_all_tasks=1`)。

**根因**: 项目 7 中混有此前验证上传功能时(Claude 测试)导入的 2 个**文本任务**(Task 151/152,data 为 `text`)。勾选"包含未标注任务"后它们进入导出,YOLO 转换器对无 `image` 键的任务抛错。属于测试数据污染,非功能缺陷。

**处理**(用户已授权): 删除 Task 151/152(级联删 2 个 AnnotationDraft、2 个 TaskLock)与 FileUpload 151(`9abef379-test_tasks.json`)。**注意 FileUpload 152(`035f0280-Pic_..._2.bmp`)是用户真实上传的图片,保留未动**(ID 巧合,勿混淆)。

**复验**: `YOLO_OBB_WITH_IMAGES + download_all_tasks=1` 子集导出 200:已标注任务 469 字节 OBB txt + 图片;未标注任务 0 字节空 txt + 图片。✓

**教训**: 用测试数据验证功能后应清理,避免污染用户项目;ID 撞号时先查证对象内容再操作。

---

## 2026-11-11 — 标注切图提速:前后各预加载 3 张 + 上传图片 HTTP 缓存

**需求**: 目标检测标注时上一张/下一张图切换太慢(每张 BMP ~3.5MB 经 LAN 每次全量传输)。用户确认:n=3(前后各 3 张),只做代码优化(不做 BMP→PNG)。

**方案**(已批准实施):

1. **后端缓存头**(`label_studio/data_import/api.py` `UploadedFileResponse.get`):
   - 上传文件名含随机 UUID 前缀(`upload_name_generator`)→ URL 不可变,可激进缓存。
   - 新增:`Last-Modified`(文件 mtime)+ `Cache-Control: private, max-age=31536000, immutable`(private 因需登录鉴权);`If-Modified-Since` 未变时返回 **304**(先判断再开文件,避免 304 请求仍全量读文件)。个别存储不支持 mtime 时跳过缓存头。
   - 已验证:200 带缓存头;带 If-Modified-Since 二次请求 → 304 0 字节 ✓

2. **前端跨任务预加载**(`web/libs/datamanager/src/sdk/lsf-sdk.js` `LSFWrapper`):
   - 新增常量 `IMAGE_PREFETCH_WINDOW = 3`、`getImageUrlsFromTask`(取 `task.data.image`,兼容数组/多图)、`prefetchAdjacentTaskImages`(整体 try/catch,best-effort)、`peekAdjacentPageImageUrls` + `fetchTaskPageImageUrls`(边界预取)。
   - 挂载点:`setLSFTask` 中 `setHydrated(true)` 之后调用(不 await)。
   - 逻辑:从 `taskStore.list` 收集当前任务 ±3 的图片 URL → `imageCache.load(url, "anonymous")`(复用已有 blob 缓存:并发 4 队列、去重、跨任务保留,命中后切图即时显示)。
   - **边界**:当前任务距列表末尾 ≤3 且还有更多页时,直接 `apiCall("tasks", {page+1, page_size, view/query})` peek 下一页的 URL(**不入 store**——`setList` 的 `reload:true` 会替换整个列表,故不能用 `fetchPage`),按页 memo;用户进入已 peek 页后自动推进 peek 下一页。
   - blob 缓存容量 10(±3+当前≈7),超出的靠 HTTP 缓存头兜底(重取即 304)。

**验证**:
- 后端:200 带 `Cache-Control`/`Last-Modified`;If-Modified-Since → 304 0 字节 ✓(APIClient)
- 用户浏览器实测(终端日志):任务加载后相邻图片自动预取 ✓(第 59-62 张的请求自动发出)
- **发现并修复边界 bug**: 用户标注到最后一页时,peek 推进逻辑请求了不存在的 page 4(79 任务仅 3 页)→ 404 "Invalid page"(无害但嘈杂)。修复:推进前检查 `nextPage <= taskStore.totalPages`。已重建部署(main-CGuTu5hw.js)。

**待验证**: 用户硬刷新后再实测切图速度,确认 404 消失。

---

## 2026-11-11 — 导出文件去掉 uuid 前缀(存储端保留 uuid)

**用户决策**: label-studio 存储端保留 uuid 机制;导出文件(图片文件名 + 标注文件名)去掉 `uuid-` 前缀。

**实现**(纯后端,两条导出路径共用):
- `data_export/functions.py` 新增 `strip_uuid_prefixes_from_export(output_dir)`:
  - 单文件导出(JSON/CSV)跳过——其中 task data 路径指向服务器文件,必须保持有效。
  - 多文件导出(YOLO/VOC/COCO 归档):遍历输出目录,文件名匹配 `^[0-9a-f]{8}-` 的去掉前缀(`os.replace`);**先**更新文本文件(.json/.xml/.txt/.md/.yaml/.yml)中对旧文件名的引用(notes.json、COCO result.json、VOC XML `<filename>` 标签等),**再**重命名。
  - 防碰撞:去前缀后同名(同名文件上传两次)时,后一个保留带前缀名并记 warning,不覆盖。
- 挂载点:`data_export/models.py` `generate_export_file`(旧同步导出,UI 所用)与 `data_export/mixins.py` `convert_file`(快照异步转换)在 `converter.convert` 之后、归档之前调用。

**验证**(APIClient,YOLO_OBB_WITH_IMAGES 子集):
- zip 条目:`labels/Pic_..._2.txt`、`images/Pic_..._2.bmp`(无 uuid)✓;未标注任务空 txt 同样去前缀 ✓
- notes.json 无 uuid 残留 ✓;JSON 导出的 data.image 路径保持不变(含 uuid,服务器路径仍有效)✓

**待用户验证**: 浏览器重新导出,确认图片与标注文件名无 uuid 前缀(后端改动,StatReloader 自动生效,无需重启/硬刷新)。

- [x] 白屏修复(用户已重启 runserver,页面正常)
- [x] RawPostDataException 修复(自动化验证 201 + 浏览器实测 201)
- [x] 删除 `uploader.py` TEMP DEBUG 转储
- [ ] 287MB 大批量上传:用户决定拆分批上传或调大 `DATA_UPLOAD_MAX_MEMORY_SIZE`
