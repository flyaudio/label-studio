import factory
from core.utils.common import load_func
from django.conf import settings
from projects.models import Project


class ProjectFactory(factory.django.DjangoModelFactory):
    # 下面每个属性，对应 Project 表的一个字段
    title = factory.Faker('bs')
    description = factory.Faker('paragraph')
    organization = factory.SubFactory(load_func(settings.ORGANIZATION_FACTORY))
    created_by = factory.SelfAttribute('organization.created_by')
    is_published = True

    class Meta:
        model = Project # 绑定的 Django Model
