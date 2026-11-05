"""用「可运行的测试」解释 @register_state_model 装饰器和 ProjectState 类。

跑法（在 label_studio 目录、test 环境）：
    python -m pytest fsm/tests/test_explain_project_state.py -v

这个文件用 5 个测试，从浅到深回答三个问题：
  问题1：@register_state_model('project') 这个装饰器做了什么？
  问题2：import state_models 时发生了什么（"import 即注册"）？
  问题3：ProjectState 是什么？注册后在哪里发挥作用？
"""
import pytest
from django.db import models

from fsm.registry import get_state_model, register_state_model, state_model_registry
from fsm.state_models import ProjectState


# ================= 问题1：装饰器做了什么 =================

def test_装饰器的作用_就是把类登记进一个字典():
    """@register_state_model('名字') 的唯一作用：把被装饰的类，放进一个全局字典。"""

    # 第一步：用一个装饰器，注册一个普通的"假"类
    @register_state_model('my_demo_entity')   # ← 装饰器
    class MyDemoState:                        # ← 被装饰的类（普通类即可）
        pass

    # 第二步：装饰器执行后，全局注册表字典里就多了一条记录
    #         {'my_demo_entity': MyDemoState}
    registered = state_model_registry.get_model('my_demo_entity')

    # 第三步：断言 —— 现在能按名字 'my_demo_entity' 取到这个类了
    assert registered is MyDemoState


# ================= 问题2：import 即注册 =================

def test_import即注册_import后注册表里已有project():
    """import state_models 模块时，@register_state_model('project') 已经自动执行了。"""

    # 关键：本文件顶部 `from fsm.state_models import ProjectState` 这一行，
    # 就已经触发了 state_models.py 顶层代码的执行，
    # 也就是触发了 @register_state_model('project') 装饰器。
    #
    # 所以现在注册表里，'project' 这个名字已经对应 ProjectState 了。
    registered = state_model_registry.get_model('project')

    assert registered is ProjectState


# ================= 问题3：ProjectState 是什么 =================

def test_ProjectState是一张数据库表():
    """ProjectState 的本质：它是一张「数据库表」（继承 models.Model）。"""

    assert issubclass(ProjectState, models.Model)   # 是 Django 模型 = 一张表
    assert ProjectState._meta.db_table == 'fsm_projectstate'  # 表名


def test_ProjectState记录的是项目状态_不是项目本身():
    """ProjectState 和 Project 是两张不同的表，靠外键关联。"""

    # ProjectState 通过外键指向 Project，记录"项目"的"状态"
    project_field = ProjectState._meta.get_field('project')
    assert project_field.related_model._meta.label == 'projects.Project'

    # state 字段只能是 CREATED / IN_PROGRESS / COMPLETED 这些固定值
    assert 'CREATED' in dict(ProjectState._meta.get_field('state').choices)


# ================= 注册后怎么用 =================

def test_注册后被按名字取出使用():
    """注册的意义：框架通过名字 'project' 就能拿到 ProjectState，不需要知道它是谁。"""

    model = get_state_model('project')   # 按名字从注册表取（这就是 state_manager 的用法）
    assert model is ProjectState         # 拿到的是 ProjectState


# ================= 进阶：状态表会"留痕" =================

@pytest.mark.django_db
def test_ProjectState是状态表_每次变化INSERT一条_历史留痕():
    """ProjectState 是真正的表：状态变化是"插入新记录"，而不是"覆盖旧值"。"""
    from projects.tests.factories import ProjectFactory

    project = ProjectFactory()

    # 模拟状态流转：项目从 CREATED 变成 IN_PROGRESS
    ProjectState.objects.create(project=project, state='CREATED')
    ProjectState.objects.create(project=project, state='IN_PROGRESS', previous_state='CREATED')

    # 关键：两条历史记录都还在！（这就是"留痕"——历史不丢失）
    states = list(
        ProjectState.objects.filter(project=project).order_by('id').values_list('state', flat=True)
    )

    assert states == ['CREATED', 'IN_PROGRESS']  # 历史都在
    assert states[-1] == 'IN_PROGRESS'           # 最新一条 = 当前状态
