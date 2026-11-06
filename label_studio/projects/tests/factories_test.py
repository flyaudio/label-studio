import factory
import pytest
from projects.models import Project          # 导入真实的 Django 模型


class DemoFactory(factory.Factory):
    class Meta:
        model = dict

    title = factory.Faker("bs")
    description = factory.Faker('paragraph')

# def test_facker():
#     item = DemoFactory()
#     print(item["title"])
#     print(item["description"])



# 注意：如果想「真的创建 Project 存进数据库」，要用 factory.django.DjangoModelFactory
# 并且 model 必须是真实的 Django 模型（from projects.models import Project）。
# 这里只是为了练习 faker，所以用 factory.Factory + dict（不碰数据库）。
class ProjectFactory(factory.Factory):
    title = factory.Faker('bs')
    description = factory.Faker('paragraph')
    is_published = True

    class Meta:
        model = dict

# class ProjectFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Project                       # ← 必须是真实的 Project 模型
#     title = factory.Faker('bs')
#     # 还要补全 Project 的必填字段（organization、created_by 等）

# def test_facker_2():
#     item = ProjectFactory()
#     print(item["title"])
#     print(item["description"])




@pytest.mark.django_db   # ← 关键：声明这个测试要访问数据库
def test_project_has_automatic_id():
    from projects.tests.factories import ProjectFactory as RealProjectFactory

    # 类属性里能看到 id 字段（纯元数据，不碰数据库）
    assert 'id' in [f.name for f in Project._meta.fields]
    id_field = Project._meta.get_field('id')
    assert id_field.primary_key is True
    assert id_field.__class__.__name__ in ('AutoField', 'BigAutoField')

    # 用工厂创建项目（自动填好 organization/created_by 等必填字段），id 自动生成
    # Project.objects.create(title="测试") #要访问数据库
    p = RealProjectFactory()
    print(f"自动生成的 id = {p.id}")
    assert p.id is not None
    assert isinstance(p.id, int)
    assert p.id > 0


# 没有工厂时：每个测试都要手动组装，外键嵌套、字段一多就重复又乱
def test_project_list():
    user = User.objects.create(
        email="t1@example.com", password="x", first_name="a", last_name="b", is_active=True,
    )
    org = Organization.objects.create(title="org1")
    org.users.add(user)
    project = Project.objects.create(
        title="p1", owner=user, organization=org, created_by=user,
    )
    Task.objects.create(project=project, data={"x": 1})
    # ... 真正的测试逻辑


if __name__ == "__main__":
    """
    python -m pytest ./label_studio/projects/tests/factories_test.py -v -s
    """
    # test_facker()
    # test_facker_2()
    test_project_has_automatic_id()
