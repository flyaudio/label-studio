import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
import pytest
from users.tests.factories import UserFactory
from projects.tests.factories import ProjectFactory
from projects.models import Project
from tasks.models import Task
from tasks.models import Annotation


@pytest.mark.django_db
def test_create_writes_to_db():
    project = ProjectFactory.create()        # Project + 关联的 Organization 都写库了

    assert project.pk is not None           # primary key;已持久化到数据库
    print("pk=", project.pk)
    print("title=", project.title)
    print("description=", project.description)
    print("organization.pk=", project.organization.pk)
    assert project.organization.pk is not None     # 外键 Organization 也自动造好了


@pytest.mark.django_db
def test_override_default_fields():
    # 传入的参数会覆盖工厂里的默认值，没传的字段走工厂默认
    project = ProjectFactory.create(title="我的测试项目")
    assert project.title == "我的测试项目"


def test_build_no_db():
    # build() 只在内存 new 一个对象，不写库——适合不需要落库的快测
    project = ProjectFactory.build(title="内存对象")
    assert project.title == "内存对象"
    assert project.pk is None


@pytest.mark.django_db
def test_batch_create():
    # 批量造 5 个项目
    projects = ProjectFactory.create_batch(5)

    assert len(projects) == 5
    assert len({p.organization.title for p in projects}) == 5


@pytest.mark.django_db
def test_what_project_stores():
    # 建了一个项目：Project 表 1 行
    project = Project.objects.create(
        title="药片缺陷检测",
        label_config="<View><Image name='img'/><RectangleLabels name='bbox'>...</RectangleLabels></View>", #XML 文本
        maximum_annotations=2,
    )
    # 这就是 Project 表存的全部东西：配置 + 元信息
    # 注意：这里没有任何药片图片数据！

    # 你上传了 3 张药片图 → Task 表 3 行（通过 project_id 关联）
    task1 = Task.objects.create(project=project, data={"image": "/upload/001.jpg"})
    task2 = Task.objects.create(project=project, data={"image": "/upload/002.jpg"})
    task3 = Task.objects.create(project=project, data={"image": "/upload/003.jpg"})
    # Task 表存的是"被标的素材"：图片 URL、文本内容、JSON 字段

    # 标注员在 task1 上画了 2 个框 → Annotation 表 1 行
    ann1 = Annotation.objects.create(
        task=task1,
        result=[
            {"type": "rectanglelabels", "from_name": "bbox", "to_name": "img",
             "value": {"x": 10, "y": 20, "width": 30, "height": 40, "rectanglelabels": ["scratch"]}},
            {"type": "rectanglelabels", "from_name": "bbox", "to_name": "img",
             "value": {"x": 50, "y": 60, "width": 20, "height": 20, "rectanglelabels": ["crack"]}},
        ],
    )
    # Annotation 表存的是"画的框、选的标签"——真正的标注结果
    # 通过 task 间接关联到 project

    # 验证三表关系
    assert project.tasks.count() == 3           # 这个项目有 3 个任务
    assert Annotation.objects.filter(task__project=project).count() == 1  # 总共 1 条标注
    assert task1.annotations.count() == 1       # 第 1 张图被标了 1 次
    # 因为 maximum_annotations=2，所以 task1 还需要再标 1 次才算完成


"""
DJANGO_DB=sqlite python -m pytest ./label_studio/projects/tests/test_1.py   --reuse-db --no-migrations -v -s
"""