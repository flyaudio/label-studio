# Label Studio 开发速查笔记

> 记录本地 `test` conda 环境下，运行测试、验证配置、解读代码时踩过的坑和正确姿势。

---

## 一、环境信息

| 项 | 值 |
|---|---|
| conda 环境 | `test` |
| conda 根目录 | `D:\software\miniconda3` |
| test 环境 Python | `D:\software\miniconda3\envs\test\python.exe` |
| Python / Django / pytest | 3.14.9 / 5.2.18 / 9.0.3 |
| 项目根目录 | `D:\matt\label-studio` |
| Django 代码目录 | `D:\matt\label-studio\label_studio` |
| settings 模块 | `core.settings.label_studio` |

> 注意：Git Bash 里 `conda` 命令未初始化（只有 Anaconda Prompt 里有）。
> 在 Bash 里直接调用环境 Python 即可，无需 `conda activate`。

---

## 二、运行测试的正确姿势

### 1. 跑某个测试文件

```bash
# 在项目根目录 D:\matt\label-studio 下
D:/software/miniconda3/envs/test/python.exe -m pytest label_studio/data_export/tests/urls_test.py -v
```

### 2. 想看测试里的 print 输出

```bash
# 加 -s（= --capture=no），pytest 默认会吞掉通过用例的 stdout
D:/software/miniconda3/envs/test/python.exe -m pytest label_studio/data_export/tests/urls_test.py -v -s
```

### 3. 常见坑：直接 `python xxx_test.py` 会报错

```
ModuleNotFoundError: No module named 'data_export'
```

原因：测试文件用包导入（`from data_export import api`），依赖 `label_studio` 目录在 `sys.path` 里，
以及 Django settings 已配置。这两件事由 `pytest-django` + `pyproject.toml` 自动完成，
**直接 `python` 运行测试文件是跑不通的**，必须用 `python -m pytest`。

---

## 三、三种运行方式 & 路径注意事项

| 方式 | 在哪个目录运行 | 路径由谁处理 |
|---|---|---|
| `python manage.py xxx` | `label_studio\` | manage.py 自己把所在目录加入 sys.path |
| `python -m pytest` | 项目根 `D:\matt\label-studio` | pytest-django 自动处理 |
| `python -c "import ..."` | 需手动保证路径 | 要么 `cd label_studio`，要么设 `PYTHONPATH` |

### `python -c` 验证 App 是否加载（需先 cd 到 label_studio）

```bash
cd label_studio
D:/software/miniconda3/envs/test/python.exe -c "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='core.settings.label_studio'; django.setup(); from django.apps import apps; print(apps.is_installed('data_export'), apps.is_installed('rest_framework'))"
# 期望输出：True True
```

---

## 四、测试启动时的「噪音」说明

跑测试时终端会出现一些输出，**都不是错误**：

| 输出 | 性质 | 处理 |
|---|---|---|
| `=> Database and media directory...` / `Static URL` / `.env` | settings 正常启动信息 | 忽略 |
| 访问 pypi.org 超时的 Traceback + `Can't get latest version` | 版本检查失败（已被 try/except 捕获） | 在 `.env` 加 `LATEST_VERSION_CHECK=False` 关闭 |
| `RuntimeWarning: Accessing the database during app initialization...` | Label Studio 上游在 `AppConfig.ready()` 查库 | 忽略 |

关闭版本检查：编辑 `C:\Users\Administrator\AppData\Local\label-studio\label-studio\.env`，加一行：

```
LATEST_VERSION_CHECK=False
```

---

## 五、代码结构速记（已讲解过的模块）

### 1. `core/settings/` —— 配置中心

- `__init__.py`：空，声明包。
- `base.py`：配置主体（数据库、INSTALLED_APPS、中间件、日志、上传限制、云存储…）。
- `label_studio.py`：入口，`from core.settings.base import *` 继承后做少量覆盖
  （默认 SQLite、生成 SECRET_KEY、初始化 Sentry、功能开关全开）。

核心套路：`get_env()` / `get_bool_env()` / `get_env_list()` 从环境变量读配置，读不到用默认值。

### 2. `INSTALLED_APPS` —— 模块清单

- 位于 `base.py` 第 231 行。
- 四组：Django 内置（admin/auth/sessions…）→ 第三方（rest_framework/django_rq/fsm…）
  → Label Studio 自有业务（core/users/projects/tasks/data_export…）。
- **顺序重要**：`fsm` 必须排在 `projects`、`tasks` 之前。
- 生效链路：声明 → 入口设 `DJANGO_SETTINGS_MODULE` → Django 读配置 → `django.setup()`
  按顺序 import 并初始化每个 App（建表、跑 ready()、注册路由/迁移/模板）。

### 3. `data_export/` —— 数据导出模块

- `urls.py`：路由表，`api/projects/<pk>/export` 等 7 条相对路由 + 1 条 auth 检查。
- 命名空间是**两层嵌套**：`data_export:api-projects:<name>`
  （外层 `app_name='data_export'`，内层 `namespace='api-projects'`）。
- 测试文件：`tests/urls_test.py`（用 6 个测试函数解释路由配置）。

### 导出链路（`ExportAPI` 是同步的）

`GET /api/projects/<pk>/export` → `urls.py` → `ExportAPI.get()`（同步）→
`DataExport.generate_export_file()`（真正实例化 Converter / 读写磁盘）。

- 导出（`ExportAPI`）是**同步**的；格式转换（`ExportConvertAPI`）才走 redis 异步任务。
- 测试文件：`tests/test_export_flow.py`（用 mock 替换 `generate_export_file`，
  验证「请求→路由→视图→参数解析→返回文件」链路，5 个用例）。

### 写测试的两个坑

1. **函数名别用 `①` 这类 Unicode 数字**，Python 函数名不允许，会 `SyntaxError`。
2. `APITestCase` 里的测试方法**必须带 `self` 参数**（它是类方法，不是独立函数）。

---

## 六、反向解析命名空间提醒

`data_export.urls` 的完整反向名称不是 `api-projects:xxx`，而是：

```
data_export:api-projects:xxx
```

例如：`reverse('data_export:api-projects:project-export', args=[7]) == '/api/projects/7/export'`
