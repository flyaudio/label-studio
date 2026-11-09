"""用「可运行的测试」解释 fsm/queryset_mixins.py 的 FSMStateQuerySetMixin。

跑法（在 label-studio 根目录、test 环境）：
    python -m pytest label_studio/fsm/tests/test_explain_queryset_mixins.py -v -s

这份文件用 4 个测试回答一个问题：
    FSMStateQuerySetMixin 的 with_state() 到底做了什么、解决了什么问题？

结论先行：
    with_state() 用「一条带子查询的 SQL」，把一批对象各自的「当前状态」
    一次性查出来，避免「循环逐个查」造成的 N+1 查询问题。
"""
import pytest
from django.db import connection, models
from django.test.utils import CaptureQueriesContext

from fsm.queryset_mixins import FSMStateQuerySetMixin
from fsm.state_models import TaskState  # import 即注册：registry 里登记了 'task'
from projects.tests.factories import ProjectFactory
from tasks.models import Task
from tasks.tests.factories import TaskFactory


# 演示用：把 mixin 和 Django QuerySet 拼在一起，得到一个带 with_state() 的查询集。
# （真实项目里，data_manager/managers.py 正是这样定义 TaskQuerySet 的：
#   class TaskQuerySet(FSMStateQuerySetMixin, models.QuerySet): ...）
class DemoTaskQuerySet(FSMStateQuerySetMixin, models.QuerySet):
    pass


def _make_tasks_with_states(project, n=3):
    """造 n 个 task，并给每个 task 造两条状态历史（CREATED -> IN_PROGRESS）。"""
    for _ in range(n):
        task = TaskFactory(project=project)
        TaskState.objects.create(task=task, state='CREATED', project_id=project.id)
        TaskState.objects.create(task=task, state='IN_PROGRESS', project_id=project.id)


# ========== 测试1：with_state 做了什么 ==========

@pytest.mark.django_db
def test_with_state_给每个任务批量查出当前状态():
    project = ProjectFactory()

    t1 = TaskFactory(project=project)
    t2 = TaskFactory(project=project)

    # t1 走了完整流转：CREATED -> IN_PROGRESS -> COMPLETED（3 条历史）
    TaskState.objects.create(task=t1, state='CREATED', project_id=project.id)
    TaskState.objects.create(task=t1, state='IN_PROGRESS', project_id=project.id)
    TaskState.objects.create(task=t1, state='COMPLETED', project_id=project.id)
    # t2 只有 1 条历史：CREATED
    TaskState.objects.create(task=t2, state='CREATED', project_id=project.id)

    # 关键：with_state() 之后，每个 task 对象会多出一个 current_state 字段
    tasks = DemoTaskQuerySet(model=Task).filter(project=project).with_state() #DemoTaskQuerySet查询的是Task这张表
    state_map = {t.id: t.current_state for t in tasks}

    # t1 的最新一条是 COMPLETED，t2 的最新一条是 CREATED
    assert state_map[t1.id] == 'COMPLETED' # t1 的最新一条是 COMPLETED
    assert state_map[t2.id] == 'CREATED'   # t2 的最新一条是 CREATED


# ========== 测试2：N+1 对比 ==========

@pytest.mark.django_db
def test_循环逐个查是N加1次_with_state只查1次():
    project = ProjectFactory()
    _make_tasks_with_states(project, n=5)   # 5 个 task

    # 笨办法：循环里每个 task 都去查一次状态表
    with CaptureQueriesContext(connection) as naive:
        for t in Task.objects.filter(project=project):
            TaskState.objects.filter(task=t).order_by('-id').first()
    naive_count = len(naive.captured_queries)

    # 聪明办法：with_state() 一条 SQL 搞定
    with CaptureQueriesContext(connection) as smart:
        list(DemoTaskQuerySet(model=Task).filter(project=project).with_state())
    smart_count = len(smart.captured_queries)

    print(f'\n[查询次数对比] 循环逐个查 = {naive_count} 次，with_state() = {smart_count} 次')

    # 循环方式 = 1(查task) + 5(每个task查一次状态) = 6 次；with_state = 1 次
    assert smart_count == 1
    assert naive_count > smart_count


# ========== 测试3：没有状态时 current_state 是 None ==========

@pytest.mark.django_db
def test_没有状态记录的任务_current_state为None():
    project = ProjectFactory()
    t = TaskFactory(project=project)   # 造了 task，但没造 TaskState

    tasks = list(DemoTaskQuerySet(model=Task).filter(project=project).with_state())
    assert tasks[0].id == t.id
    assert tasks[0].current_state is None   # 没状态 -> None，不会报错


# ========== 测试4：FSM 关闭时零开销 ==========

def test_FSM关闭时_with_state零开销原样返回(settings):
    settings.FSM_ENABLED = False   # 关掉 FSM 开关

    qs = DemoTaskQuerySet(model=Task).all().with_state()

    # 关闭时 with_state 直接 return self，没有做任何 annotate
    assert 'current_state' not in qs.query.annotations
