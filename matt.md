core/settings/ 是 Label Studio 的 Django 配置中心。Django 启动时，会从这里读取「settings 模块」



在 Django 里，一个「App」（应用）就是一个功能独立的 Python 包，里面有自己的 models.py（数据表）、views.py（视图）、urls.py（路由）等。把 App 写进 INSTALLED_APPS，Django 才会：
扫描它的数据模型，生成数据库表；
执行它的 apps.py 里的 ready()；
让它的路由、模板、静态文件、迁移（migrations）生效。



每个 App = apps.py + models.py + urls.py + api.py + serializers.py + mixins.py + migrations/ + tests/



Django 用的是 MVT 三层架构：
    Model（模型）→ models.py —— 数据层
    View（视图）→ views.py / api.py —— 逻辑层
    Template（模板）→ templates/ —— 展示层


https://blog.csdn.net/gitblog_00835/article/details/152396427


annotation_templates/	预定义的标注模板（数据/资源，不是 app）
templates/	            Django 的 HTML 模板文件
tests/	                测试代码
__pycache__/	        Python 字节码缓存，可忽略

主干 5 个：data_import → projects → tasks →（标注）→ data_export，对应「导入数据 → 建项目 → 生成任务 → 标注 → 导出结果」这条核心流程；


# claude
claude --resume 1bff9212-adb6-4eb8-a474-305b4d414eeb


这个目录是开源标注项目label-stuido的clone，是develop分支的clone。
想要基于label-studio做二次开发。现在要把原生的label-studio跑起来。
运行环境是本地的conda环境（/home/znzz/anaconda3/envs/py314/bin/python）。
把你的操作记录下来。后续的问答也是要记录下来

在label-studio的根目录下，我运行了下述命令
```bash
# Install all package dependencies
pip install poetry
poetry install
# Run database migrations
python label_studio/manage.py migrate
python label_studio/manage.py collectstatic   # 收集静态文件
python label_studio/manage.py runserver 0.0.0.0:8080
```

注册账户密码后，浏览器跳转后是白色的页面，没有任何东西。

诊断: 白屏的根因是前端从未构建——web/dist/apps/labelstudio/ 目录不存在。develop 分支的仓库不包含编译好的前端产物，需要先用 bun 构建。
curl -fsSL https://bun.sh/install | bash 2>&1 | tail -5; ~/.bun/bin/bun --version


终端打印如下：
(py314) znzz@znzz:~/ma/label-studio$ python label_studio/manage.py runserver 0.0.0.0:8080
=> Database and media directory: /home/znzz/.local/share/label-studio
	 DATABASES= {'default': {'ENGINE': 'django.db.backends.postgresql', 'USER': 'postgres', 'PASSWORD': 'postgres', 'NAME': 'postgres', 'HOST': 'localhost', 'PORT': 5432}}
=> Static URL is set to: /static/
LOCAL_FILES_DOCUMENT_ROOT auto-configured to /home/znzz/ma/label-studio/mydata and LOCAL_FILES_SERVING_ENABLED set to true.
Read environment variables from: /home/znzz/.local/share/label-studio/.env
get 'SECRET_KEY' casted as <class 'str'> with default type str
	 SECRET_KEY= -p95p)u8wq_^y*pci=#+8f01o_yd6$k^i(m0ulz8m^5fg-ex@k
	 BASE_DATA_DIR= /home/znzz/.local/share/label-studio
[2026-11-10 02:28:58,218] [core.feature_flags.base::<module>::42] [INFO] Read flags from file /home/znzz/ma/label-studio/label_studio/feature_flags.json
/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/db/backends/utils.py:98: RuntimeWarning: Accessing the database during app initialization is discouraged. To fix this warning, avoid executing queries in AppConfig.ready() or when your app modules are imported.
  warnings.warn(self.APPS_NOT_READY_WARNING_MSG, category=RuntimeWarning)
[2026-11-10 02:28:58,702] [fsm.apps::ready::56] [INFO] LSO FSM: Registered LSO transitions (community edition)
=> Database and media directory: /home/znzz/.local/share/label-studio
	 DATABASES= {'default': {'ENGINE': 'django.db.backends.postgresql', 'USER': 'postgres', 'PASSWORD': 'postgres', 'NAME': 'postgres', 'HOST': 'localhost', 'PORT': 5432}}
=> Static URL is set to: /static/
LOCAL_FILES_DOCUMENT_ROOT auto-configured to /home/znzz/ma/label-studio/mydata and LOCAL_FILES_SERVING_ENABLED set to true.
Read environment variables from: /home/znzz/.local/share/label-studio/.env
get 'SECRET_KEY' casted as <class 'str'> with default type str
	 SECRET_KEY= -p95p)u8wq_^y*pci=#+8f01o_yd6$k^i(m0ulz8m^5fg-ex@k
	 BASE_DATA_DIR= /home/znzz/.local/share/label-studio
[2026-11-10 02:28:59,396] [core.feature_flags.base::<module>::42] [INFO] Read flags from file /home/znzz/ma/label-studio/label_studio/feature_flags.json
/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/db/backends/utils.py:98: RuntimeWarning: Accessing the database during app initialization is discouraged. To fix this warning, avoid executing queries in AppConfig.ready() or when your app modules are imported.
  warnings.warn(self.APPS_NOT_READY_WARNING_MSG, category=RuntimeWarning)
[2026-11-10 02:28:59,878] [fsm.apps::ready::56] [INFO] LSO FSM: Registered LSO transitions (community edition)
[2026-11-10 02:28:59,880] [django.utils.autoreload::run_with_reloader::667] [INFO] Watching for file changes with StatReloader
[2026-11-10 02:28:59,880] [django.utils.autoreload::run_with_reloader::667] [INFO] Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (1 silenced).
[2026-11-10 02:29:00,118] [io_storages.migrations.0017_auto_20240731_1638::get_operations::135] [INFO] IS_SQLITE: True
November 10, 2026 - 02:29:00
Django version 5.2.19, using settings 'core.settings.label_studio'
Starting development server at http://0.0.0.0:8080/
Quit the server with CONTROL-C.

WARNING: This is a development server. Do not use it in a production setting. Use a production WSGI or ASGI server instead.
For more information on production servers see: https://docs.djangoproject.com/en/5.2/howto/deployment/
[2026-11-10 02:29:03,687] [django.server::log_message::213] [INFO] "GET / HTTP/1.1" 200 31892
[2026-11-10 02:29:03,687] [django.server::log_message::213] [INFO] "GET / HTTP/1.1" 200 31892
[2026-11-10 02:29:03,727] [django.security.SuspiciousFileOperation::log_response::293] [ERROR] The joined path (/main.css) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
Traceback (most recent call last):
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/exception.py", line 55, in inner
    response = get_response(request)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/base.py", line 197, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/sentry_sdk/integrations/django/views.py", line 92, in sentry_wrapped_callback
    return callback(request, *args, **kwargs)
  File "/home/znzz/ma/label-studio/label_studio/core/utils/static_serve.py", line 69, in serve
    fullpath = Path(safe_join(document_root, possible_asset))
                    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/utils/_os.py", line 87, in safe_join
    raise SuspiciousFileOperation(
    ...<2 lines>...
    )
django.core.exceptions.SuspiciousFileOperation: The joined path (/main.css) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
[2026-11-10 02:29:03,727] [django.security.SuspiciousFileOperation::log_response::293] [ERROR] The joined path (/main.css) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
Traceback (most recent call last):
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/exception.py", line 55, in inner
    response = get_response(request)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/base.py", line 197, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/sentry_sdk/integrations/django/views.py", line 92, in sentry_wrapped_callback
    return callback(request, *args, **kwargs)
  File "/home/znzz/ma/label-studio/label_studio/core/utils/static_serve.py", line 69, in serve
    fullpath = Path(safe_join(document_root, possible_asset))
                    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/utils/_os.py", line 87, in safe_join
    raise SuspiciousFileOperation(
    ...<2 lines>...
    )
django.core.exceptions.SuspiciousFileOperation: The joined path (/main.css) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
[2026-11-10 02:29:03,736] [django.security.SuspiciousFileOperation::log_response::293] [ERROR] The joined path (/main.js) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
Traceback (most recent call last):
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/exception.py", line 55, in inner
    response = get_response(request)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/base.py", line 197, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/sentry_sdk/integrations/django/views.py", line 92, in sentry_wrapped_callback
    return callback(request, *args, **kwargs)
  File "/home/znzz/ma/label-studio/label_studio/core/utils/static_serve.py", line 69, in serve
    fullpath = Path(safe_join(document_root, possible_asset))
                    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/utils/_os.py", line 87, in safe_join
    raise SuspiciousFileOperation(
    ...<2 lines>...
    )
django.core.exceptions.SuspiciousFileOperation: The joined path (/main.js) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
[2026-11-10 02:29:03,736] [django.security.SuspiciousFileOperation::log_response::293] [ERROR] The joined path (/main.js) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
Traceback (most recent call last):
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/exception.py", line 55, in inner
    response = get_response(request)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/core/handlers/base.py", line 197, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/sentry_sdk/integrations/django/views.py", line 92, in sentry_wrapped_callback
    return callback(request, *args, **kwargs)
  File "/home/znzz/ma/label-studio/label_studio/core/utils/static_serve.py", line 69, in serve
    fullpath = Path(safe_join(document_root, possible_asset))
                    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/znzz/anaconda3/envs/py314/lib/python3.14/site-packages/django/utils/_os.py", line 87, in safe_join
    raise SuspiciousFileOperation(
    ...<2 lines>...
    )
django.core.exceptions.SuspiciousFileOperation: The joined path (/main.js) is located outside of the base path component (/home/znzz/ma/label-studio/web/dist/apps/labelstudio)
[2026-11-10 02:29:03,738] [django.server::log_message::213] [WARNING] "GET /react-app/main.css HTTP/1.1" 400 148889
[2026-11-10 02:29:03,738] [django.server::log_message::213] [WARNING] "GET /react-app/main.css HTTP/1.1" 400 148889
[2026-11-10 02:29:03,739] [django.server::log_message::213] [WARNING] "GET /react-app/main.js HTTP/1.1" 400 148997
[2026-11-10 02:29:03,739] [django.server::log_message::213] [WARNING] "GET /react-app/main.js HTTP/1.1" 400 148997
