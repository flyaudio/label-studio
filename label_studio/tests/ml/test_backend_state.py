import requests_mock
import pytest
from label_studio.ml.models import MLBackend, MLBackendState
from label_studio.tests.utils import make_project, register_ml_backend_mock


PROJECT_CONFIG = """<View><Image name="image" value="$image_url"/><Choices name="label"
          toName="image"><Choice value="pos"/><Choice value="neg"/></Choices></View>"""


# @pytest.mark.django_db
# def test_health_timeout_degrades_to_disconnected(business_client):
#     """/health 连不上 → DISCONNECTED，不抛异常。"""
#     project = make_project(config=dict(is_published=True, label_config=PROJECT_CONFIG),
#                            user=business_client.user, use_ml_backend=False)

    # with requests_mock.Mocker() as m:
    #     register_ml_backend_mock(m, url='http://fake:9090', health_connect_timeout=True)
    #     backend = MLBackend.objects.create(project=project, url='http://fake:9090', title='offline')
    #     backend.update_state()
    #
    # backend.refresh_from_db()
    # assert backend.state == MLBackendState.DISCONNECTED


# @pytest.mark.django_db
# def test_setup_error_records_error_message(business_client):
#     """/setup 报错 → ERROR 并把错误文字存进 error_message。"""
#     project = make_project(config=dict(is_published=True, label_config=PROJECT_CONFIG),
#                            user=business_client.user, use_ml_backend=False)
#
#     with requests_mock.Mocker() as m:
#         m.get('http://fake:9090/health', json={'status': 'UP'})
#         m.post('http://fake:9090/setup', json={'error': 'schema unsupported'}, status_code=500)
#         backend = MLBackend.objects.create(project=project, url='http://fake:9090', title='bad')
#         backend.update_state()
#
#     backend.refresh_from_db()
#     assert backend.state == MLBackendState.ERROR
#     assert 'schema unsupported' in backend.error_message
