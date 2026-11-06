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
