import json
import logging
import pytest
from data_manager.managers import annotate_predictions_score
from ml.models import MLBackend, MLBackendState
from projects.models import Task
from rest_framework import status
from tasks.models import Prediction

from label_studio.tests.utils import make_project, register_ml_backend_mock
logger = logging.getLogger(__name__)

ORIG_MODEL_NAME = 'basic_ml_backend'
PROJECT_CONFIG = """<View><Image name="image" value="$image_url"/><Choices name="label"
          toName="image"><Choice value="pos"/><Choice value="neg"/></Choices></View>"""


@pytest.fixture
def ml_backend_for_test_api(ml_backend): # 先运行 ml_backend fixture
    register_ml_backend_mock( #覆盖注册
        ml_backend,
        url='https://ml_backend_for_test_api',
        setup_model_version='1.0.0',
    )
    yield ml_backend #把拦截器交给测试函数


@pytest.mark.django_db
def test_ml_backend_set_for_prelabeling(business_client, ml_backend_for_test_api, mock_gethostbyname):
    """
    先造一个空项目，再通过真实 HTTP 接口挂一个假后端，验证 Django 自动把后端标题填进了项目的模型版本字段。** 它测的是 LS 自己的业务逻辑（版本绑定规则）
    """
    project = make_project(
        config=dict(
            is_published=True,
            label_config=PROJECT_CONFIG,
            title='test_ml_backend_creation',
        ),
        user=business_client.user,
    )

    assert project.model_version == ''

    # create ML backend
    response = business_client.post(# 等价于一个已登录浏览器发请求
        '/api/ml/',
        data={
            'project': project.id,
            'title': 'ml_backend_title',
            'url': 'https://ml_backend_for_test_api',
        },
    )
    assert response.status_code == 201

    project.refresh_from_db()
    assert project.model_version == 'ml_backend_title'


# @pytest.mark.django_db
# def test_ml_backend_not_set_for_prelabeling(business_client, ml_backend_for_test_api, mock_gethostbyname):
#     """We are not setting it when its already set for another name,
#     for example when predictions were uploaded before"""
#
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_creation',
#         ),
#         user=business_client.user,
#     )
#
#     project.model_version = ORIG_MODEL_NAME
#     project.save()
#
#     # create ML backend
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'ml_backend_title',
#             'url': 'https://ml_backend_for_test_api',
#         },
#     )
#     assert response.status_code == 201
#
#     project.refresh_from_db()
#     assert project.model_version == ORIG_MODEL_NAME
#
#
# @pytest.mark.django_db
# def test_model_version_on_save(business_client, ml_backend_for_test_api, mock_gethostbyname):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_creation',
#         ),
#         user=business_client.user,
#     )
#
#     assert project.model_version == ''
#
#     # create ML backend
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'test_ml_backend_creation_ML_backend',
#             'url': 'https://ml_backend_for_test_api',
#         },
#     )
#     assert response.status_code == 201
#     r = response.json()
#     ml_backend_id = r['id']
#     response = business_client.get(f'/api/ml/{ml_backend_id}')
#     assert response.status_code == 200
#     assert response.json()['state'] == 'CO'
#
#     # select model version in project
#     assert (
#         business_client.patch(
#             f'/api/projects/{project.id}',
#             data=json.dumps({'model_version': 'test_ml_backend_creation_ML_backend'}),
#             content_type='application/json',
#         ).status_code
#         == 200
#     )
#
#     # change ML backend title --> model version should be updated
#     assert (
#         business_client.patch(
#             f'/api/ml/{ml_backend_id}',
#             data=json.dumps(
#                 {
#                     'project': project.id,
#                     'title': 'new_title',
#                     'url': 'https://ml_backend_for_test_api',
#                 }
#             ),
#             content_type='application/json',
#         ).status_code
#         == 200
#     )
#     project.refresh_from_db()
#     assert project.model_version == 'new_title'
#
#
# @pytest.mark.django_db
# def test_model_version_on_delete(business_client, ml_backend_for_test_api, mock_gethostbyname):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_creation',
#         ),
#         user=business_client.user,
#     )
#
#     assert project.model_version == ''
#
#     # create ML backend
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'test_ml_backend_creation_ML_backend',
#             'url': 'https://ml_backend_for_test_api',
#         },
#     )
#     assert response.status_code == 201
#     r = response.json()
#     ml_backend_id = r['id']
#     response = business_client.get(f'/api/ml/{ml_backend_id}')
#     assert response.status_code == 200
#     assert response.json()['state'] == 'CO'
#
#     # select model version in project
#     assert (
#         business_client.patch(
#             f'/api/projects/{project.id}',
#             data=json.dumps({'model_version': 'test_ml_backend_creation_ML_backend'}),
#             content_type='application/json',
#         ).status_code
#         == 200
#     )
#
#     project.refresh_from_db()
#     assert project.model_version == 'test_ml_backend_creation_ML_backend'
#
#     # delete ML backend --> project's model version should be reset
#     assert business_client.delete(f'/api/ml/{ml_backend_id}').status_code == 204
#     project.refresh_from_db()
#     assert project.model_version == ''
#
#
# @pytest.mark.django_db
# def test_predictions_score_uses_backend_model_version_when_project_model_version_is_backend_title(business_client):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_predictions_score_model_version_title_mapping',
#             model_version='My ML Backend',
#         ),
#         user=business_client.user,
#     )
#     MLBackend.objects.create(
#         project=project,
#         title='My ML Backend',
#         model_version='v1',
#         url='http://127.0.0.1:9090',
#     )
#     task = Task.objects.create(project=project, data={'image_url': 'http://example.com/image.jpg'})
#     Prediction.objects.create(
#         task=task,
#         project=project,
#         result=[{}],
#         score=0.87,
#         model_version='v1',
#     )
#
#     annotated_task = annotate_predictions_score(Task.objects.filter(id=task.id)).values('predictions_score').first()
#
#     assert annotated_task['predictions_score'] == pytest.approx(0.87)
#
#
# @pytest.mark.django_db
# def test_predictions_score_uses_project_model_version_from_imported_predictions_without_backend_mapping(
#     business_client,
# ):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_preds_score_imported_no_backend_mapping',
#             model_version='',
#         ),
#         user=business_client.user,
#     )
#     task = Task.objects.create(project=project, data={'image_url': 'http://example.com/image.jpg'})
#
#     response = business_client.post(
#         f'/api/projects/{project.id}/import/predictions',
#         data=[
#             {
#                 'task': task.id,
#                 'result': [
#                     {
#                         'from_name': 'label',
#                         'to_name': 'image',
#                         'type': 'choices',
#                         'value': {'choices': ['pos']},
#                     }
#                 ],
#                 'score': 0.11,
#                 'model_version': 'imported-v1',
#             },
#             {
#                 'task': task.id,
#                 'result': [
#                     {
#                         'from_name': 'label',
#                         'to_name': 'image',
#                         'type': 'choices',
#                         'value': {'choices': ['neg']},
#                     }
#                 ],
#                 'score': 0.89,
#                 'model_version': 'imported-v2',
#             },
#         ],
#         content_type='application/json',
#     )
#     assert response.status_code == 201
#     assert response.json()['created'] == 2
#
#     # Empty string means "no selected model version", so score should be null (not averaged across all predictions).
#     annotated_task = annotate_predictions_score(Task.objects.filter(id=task.id)).values('predictions_score').first()
#     assert annotated_task['predictions_score'] is None
#
#     project.model_version = 'imported-v2'
#     project.save(update_fields=['model_version'])
#
#     annotated_task = annotate_predictions_score(Task.objects.filter(id=task.id)).values('predictions_score').first()
#
#     assert annotated_task['predictions_score'] == pytest.approx(0.89)
#
#
# @pytest.mark.django_db
# def test_ml_backend_local_url_blocked_by_default(business_client, ml_backend_for_test_api):
#     """ML_BLOCK_LOCAL_IP defaults to on, so a backend on a loopback address is rejected."""
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_local_url',
#         ),
#         user=business_client.user,
#     )
#
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'local_ml_backend',
#             'url': 'http://127.0.0.1:9090',
#         },
#     )
#     assert response.status_code == 403
#     assert 'reserved network address' in response.json()['detail']
#
#
# @pytest.mark.django_db
# def test_ml_backend_detail_reports_blocked_url_as_disconnected(business_client):
#     """A backend whose URL is blocked must degrade to DISCONNECTED, not fail the read with 403."""
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_blocked_detail',
#         ),
#         user=business_client.user,
#     )
#     ml_backend = MLBackend.objects.create(project=project, url='http://127.0.0.1:9090')
#
#     response = business_client.get(f'/api/ml/{ml_backend.id}')
#
#     assert response.status_code == 200
#     ml_backend.refresh_from_db()
#     assert ml_backend.state == MLBackendState.DISCONNECTED
#
#
# @pytest.mark.django_db
# def test_security_write_only_payload(business_client, ml_backend_for_test_api, mock_gethostbyname):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_creation',
#         ),
#         user=business_client.user,
#     )
#
#     # create ML backend - fails without password
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'test_ml_backend_creation_ML_backend',
#             'url': 'https://ml_backend_for_test_api',
#             'auth_method': 'BASIC_AUTH',
#             # 'basic_auth_user': 'user',
#             # 'basic_auth_pass': '<SECRET>',
#         },
#     )
#     assert response.status_code == 400
#     r = response.json()
#     assert (
#         r['validation_errors']['non_field_errors'][0]
#         == 'Authentication username and password is required for Basic Authentication.'
#     )
#
#     # create ML backend with username and password
#     response = business_client.post(
#         '/api/ml/',
#         data={
#             'project': project.id,
#             'title': 'test_ml_backend_creation_ML_backend',
#             'url': 'https://ml_backend_for_test_api',
#             'auth_method': 'BASIC_AUTH',
#             'basic_auth_user': 'user',
#             'basic_auth_pass': '<SECRET>',
#         },
#     )
#     assert response.status_code == 201
#     r = response.json()
#     # security check that password is not returned in POST response
#     assert 'basic_auth_pass' not in r
#     ml_backend_id = r['id']
#     response = business_client.get(f'/api/ml/{ml_backend_id}')
#     assert response.status_code == 200
#     # check that password is not returned in GET response
#     assert 'basic_auth_pass' not in response.json()
#
#     # patch ML backend without password - must pass since it uses write_only field for previous password
#     response = business_client.patch(
#         f'/api/ml/{ml_backend_id}',
#         data=json.dumps(
#             {
#                 'project': project.id,
#                 'title': 'new_title_1',
#                 'url': 'https://ml_backend_for_test_api',
#             }
#         ),
#         content_type='application/json',
#     )
#     assert response.status_code == 200
#     # check that password is not returned in PATCH response
#     assert 'basic_auth_pass' not in response.json()
#
#     # patch ML backend with password
#     response = business_client.patch(
#         f'/api/ml/{ml_backend_id}',
#         data=json.dumps(
#             {
#                 'project': project.id,
#                 'title': 'new_title',
#                 'url': 'https://ml_backend_for_test_api',
#                 'basic_auth_pass': '<ANOTHER_SECRET>',
#             }
#         ),
#         content_type='application/json',
#     )
#     # check that password is not returned in PATCH response
#     assert 'basic_auth_pass' not in response.json()
#
#     from ml.models import MLBackend
#
#     ml_backend = MLBackend.objects.get(id=ml_backend_id)
#     assert ml_backend.basic_auth_pass == '<ANOTHER_SECRET>'
#
#
# @pytest.mark.django_db
# def test_ml_backend_predict_test_api_post_random_true(business_client):
#     project = make_project(
#         config=dict(
#             is_published=True,
#             label_config=PROJECT_CONFIG,
#             title='test_ml_backend_creation',
#         ),
#         user=business_client.user,
#         use_ml_backend=True,
#     )
#     Task.objects.create(project=project, data={'image': 'http://example.com/image.jpg'})
#
#     # get ML backend id from project
#     project.refresh_from_db()
#     ml_backend = project.get_ml_backends().first()
#
#     response = business_client.post(f'/api/ml/{ml_backend.id}/predict/test?random=true')
#
#     assert response.status_code == status.HTTP_200_OK
#     r = response.json()
#     assert r['url'] == 'http://localhost:8999/predict'
#     assert r['status'] == 200


@pytest.mark.django_db
def test_register_backend_connected(business_client, ml_backend_for_test_api, mock_gethostbyname):
    project = make_project(
        config=dict(is_published=True, label_config=PROJECT_CONFIG, title='demo'),
        user=business_client.user,
    )

    resp = business_client.post('/api/ml/', data={
        'project': project.id,
        'title': 'yolo-backend',
        'url': 'https://ml_backend_for_test_api',
    })
    assert resp.status_code == 201

    backend_id = resp.json()['id']
    logger.error(f"backend_id: {resp.json()}")
    # update_state() 走完 health+setup 后，state 应为 Connected('CO')
    detail = business_client.get(f'/api/ml/{backend_id}')
    assert detail.json()['state'] == 'CO'

    project.refresh_from_db()
    # perform_create:112 —— 项目未选模型版本时，新后端 title 成为默认版本
    assert project.model_version == 'yolo-backend'



"""
What These Tests Tell You About the Code:

get_queryset is not just a DB query:
    test_list_requires_project_query_parameter explains why get_object_or_404(Project, pk=project_pk) is needed.
    test_list_updates_backend_health_state explains why project.update_ml_backends_state() is called instead of MLBackend.objects.filter(...).

create is an authorization shield:
    test_create_checks_project_permission_before_external_connection demonstrates why create() was overridden to check permissions on request.data.get('project') before delegating to super().create().

perform_create handles post-creation business side-effects:
    test_perform_create_auto_assigns_default_model_version and test_perform_create_does_not_override_existing_model_version demonstrate the if project.show_collab_predictions and not project.model_version: logic.
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from ml.models import MLBackend, MLBackendState
from projects.models import Project


# ==============================================================================
# 1. GET (List) Business Logic Tests
# ==============================================================================

@pytest.mark.django_db
class TestMLBackendListBusinessLogic:

    def test_list_requires_project_query_parameter(self, business_client):
        """
        Business Rule: ML backends are always project-scoped.
        If a user does not supply ?project=<id>, the endpoint must fail with 404.
        """
        response = business_client.get('/api/ml/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_verifies_project_permissions(self, business_client, project_factory, user_factory):
        """
        Business Rule: A user cannot see ML backends of a project they cannot view.
        """
        other_user = user_factory()
        private_project = project_factory(created_by=other_user)

        # Attempt to list backends for a project the user doesn't belong to
        response = business_client.get(f'/api/ml/?project={private_project.id}')
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_list_updates_backend_health_state(self, business_client, project_factory):
        """
        Business Rule: When fetching the list of ML backends, Label Studio automatically
        refreshes each backend's health/status (project.update_ml_backends_state()).
        """
        project = project_factory(created_by=business_client.user)
        
        with patch.object(Project, 'update_ml_backends_state', return_value=[]) as mock_update_state:
            response = business_client.get(f'/api/ml/?project={project.id}')
            
            assert response.status_code == status.HTTP_200_OK
            # Confirms that calling GET triggers the state refresh method:
            mock_update_state.assert_called_once()


# ==============================================================================
# 2. POST (Create) Business Logic Tests
# ==============================================================================

@pytest.mark.django_db
class TestMLBackendCreateBusinessLogic:

    def test_create_checks_project_permission_before_external_connection(
        self, business_client, project_factory, user_factory
    ):
        """
        Business Rule (Security):
        MLBackendSerializer.validate() sends a network ping (/setup) to the external ML URL.
        To prevent SSRF / token leakage, create() must check project permissions 
        BEFORE allowing the serializer to initiate any network calls.
        """
        other_user = user_factory()
        private_project = project_factory(created_by=other_user)

        with patch('ml.serializers.MLBackendSerializer.validate') as mock_validate:
            payload = {
                'project': private_project.id,
                'title': 'Attacker Backend',
                'url': 'http://malicious-external-host.com:9090'
            }
            response = business_client.post('/api/ml/', data=payload)

            # Must reject with 403 Forbidden
            assert response.status_code == status.HTTP_403_FORBIDDEN
            # CRITICAL: Serializer.validate() was never reached or called!
            mock_validate.assert_not_called()

    def test_perform_create_updates_backend_state(
        self, business_client, project_factory, mock_ml_backend_setup
    ):
        """
        Business Rule: After a new ML backend is saved, its initial connectivity
        state must be checked immediately (ml_backend.update_state()).
        """
        project = project_factory(created_by=business_client.user)

        with patch.object(MLBackend, 'update_state') as mock_update_state:
            payload = {
                'project': project.id,
                'title': 'Object Detection Model',
                'url': 'https://ml.example.com'
            }
            response = business_client.post('/api/ml/', data=payload)

            assert response.status_code == status.HTTP_201_CREATED
            # Verifies perform_create called update_state
            mock_update_state.assert_called_once()

    def test_perform_create_auto_assigns_default_model_version(
        self, business_client, project_factory, mock_ml_backend_setup
    ):
        """
        Business Rule: If collaborative predictions are enabled (show_collab_predictions=True)
        and the project does not yet have a default model_version set, the newly added
        backend's title automatically becomes the project's default model_version.
        """
        project = project_factory(
            created_by=business_client.user,
            show_collab_predictions=True,
            model_version=''  # currently unset
        )

        payload = {
            'project': project.id,
            'title': 'yolov8-classifier',
            'url': 'https://ml.example.com'
        }
        response = business_client.post('/api/ml/', data=payload)
        assert response.status_code == status.HTTP_201_CREATED

        # Refresh project from DB to verify the side effect
        project.refresh_from_db()
        assert project.model_version == 'yolov8-classifier'

    def test_perform_create_does_not_override_existing_model_version(
        self, business_client, project_factory, mock_ml_backend_setup
    ):
        """
        Business Rule: If the project already has an active model_version (e.g. from
        offline uploaded predictions or a previously attached model), adding a new
        ML backend must NOT overwrite it.
        """
        project = project_factory(
            created_by=business_client.user,
            show_collab_predictions=True,
            model_version='existing-v1-model'  # already set
        )

        payload = {
            'project': project.id,
            'title': 'new-v2-model',
            'url': 'https://ml.example.com'
        }
        response = business_client.post('/api/ml/', data=payload)
        assert response.status_code == status.HTTP_201_CREATED

        project.refresh_from_db()
        # Remains the old version, not replaced
        assert project.model_version == 'existing-v1-model'