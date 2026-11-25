"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import logging

from core.feature_flags import flag_set
from core.permissions import ViewClassPermission, all_permissions
from django.conf import settings
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from ml.models import MLBackend
from ml.serializers import (
    MLBackendRequestSerializer,
    MLBackendSerializer,
    MLBackendTrainRequestSerializer,
    MLInteractiveAnnotatingRequest,
)
from projects.models import Project, Task
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@method_decorator(
    name='post',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Add ML Backend',
        description="""
    Add an ML backend to a project using the Label Studio UI or by sending a POST request using the following cURL 
    command:
    ```bash
    curl -X POST -H 'Content-type: application/json' {host}/api/ml -H 'Authorization: Token abc123'\\
    --data '{{"url": "http://localhost:9090", "project": {{project_id}}}}' 
    """.format(host=(settings.HOSTNAME or 'https://localhost:8080')),
        request=MLBackendRequestSerializer,
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'create',
            'x-fern-audiences': ['public'],
        },
    ),
)
@method_decorator(
    name='get',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='List ML backends',
        description="""
    List all configured ML backends for a specific project by ID.
    Use the following cURL command:
    ```bash
    curl {host}/api/ml?project={{project_id}} -H 'Authorization: Token abc123'
    """.format(host=(settings.HOSTNAME or 'https://localhost:8080')),
        parameters=[
            OpenApiParameter(name='project', type=OpenApiTypes.INT, location='query', description='Project ID'),
        ],
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'list',
            'x-fern-audiences': ['public'],
        },
    ),
)
class MLBackendListAPI(generics.ListCreateAPIView):
    """
    When a GET arrives:
        Calls get_queryset() to fetch objects from the database.
        Passes them to serializer_class(many=True) to convert database models into JSON.
        Returns a 200 OK response with the JSON list.
    When a POST arrives:
        Calls create():
        Passes request data to serializer_class(data=request.data) to validate it.
        If valid, calls perform_create(serializer), which executes serializer.save().
        Returns a 201 Created response with the created object's JSON.
    """
    # What incoming formats are supported (JSON, standard web forms, multipart uploads)
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    # Permission checks: GET requires view permission, POST requires edit/change permission
    permission_required = ViewClassPermission(
        GET=all_permissions.projects_view,
        POST=all_permissions.projects_change,
    )
    # The serializer that converts MLBackend models to/from JSON and validates fields
    serializer_class = MLBackendSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_interactive']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MLBackend.objects.none()

        #Read ?project=<id> from the URL query string
        project_pk = self.request.query_params.get('project')
        # Find the project in the database (or return 404 if not found)
        project = generics.get_object_or_404(Project, pk=project_pk)
        # Check if the current user has permission to view this project
        self.check_object_permissions(self.request, project)
        # Instead of just querying the database, ask the project to refresh
        # the status of its connected ML backends (check if servers are alive)
        # and return that list to be serialized into JSON.
        ml_backends = project.update_ml_backends_state()

        return ml_backends

    def create(self, request, *args, **kwargs):
        # MLBackendSerializer.validate() calls setup() on the submitted URL, handing it the
        # project creator's API token, so authorize the target project before that runs.
        try:
            project = Project.objects.filter(pk=request.data.get('project')).first()
        except (AttributeError, TypeError, ValueError):
            project = None  # malformed payload: let the serializer reject it
        if project is not None:
            self.check_object_permissions(request, project)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Save the new MLBackend record to the database
        ml_backend = serializer.save()
        # Check the ML server's health/status immediately
        ml_backend.update_state()

        project = ml_backend.project

        # In case we are adding the model, let's set it as the default
        # to obtain predictions. This approach is consistent with uploading
        # offline predictions, which would be set automatically.
        if project.show_collab_predictions and not project.model_version:
            project.model_version = ml_backend.title
            project.save(update_fields=['model_version'])


@method_decorator(
    name='patch',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Update ML Backend',
        description="""
    Update ML backend parameters using the Label Studio UI or by sending a PATCH request using the following cURL command:
    ```bash
    curl -X PATCH -H 'Content-type: application/json' {host}/api/ml/{{ml_backend_ID}} -H 'Authorization: Token abc123'\\
    --data '{{"url": "http://localhost:9091"}}' 
    """.format(host=(settings.HOSTNAME or 'https://localhost:8080')),
        request=MLBackendRequestSerializer,
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'update',
            'x-fern-audiences': ['public'],
        },
    ),
)
@method_decorator(
    name='get',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Get ML Backend',
        description="""
    Get details about a specific ML backend connection by ID. For example, make a GET request using the
    following cURL command:
    ```bash
    curl {host}/api/ml/{{ml_backend_ID}} -H 'Authorization: Token abc123'
    """.format(host=(settings.HOSTNAME or 'https://localhost:8080')),
        request=None,
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'get',
            'x-fern-audiences': ['public'],
        },
    ),
)
@method_decorator(
    name='delete',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Remove ML Backend',
        description="""
    Remove an existing ML backend connection by ID. For example, use the
    following cURL command:
    ```bash
    curl -X DELETE {host}/api/ml/{{ml_backend_ID}} -H 'Authorization: Token abc123'
    """.format(host=(settings.HOSTNAME or 'https://localhost:8080')),
        request=None,
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'delete',
            'x-fern-audiences': ['public'],
        },
    ),
)
@method_decorator(name='put', decorator=extend_schema(exclude=True))
class MLBackendDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    serializer_class = MLBackendSerializer
    permission_required = all_permissions.projects_change
    queryset = MLBackend.objects.all()

    def get_object(self):
        ml_backend = super(MLBackendDetailAPI, self).get_object()
        ml_backend.update_state()
        return ml_backend

    def perform_update(self, serializer):
        ml_backend = serializer.save()
        ml_backend.update_state()


@method_decorator(
    name='post',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Train',
        description="""
        After you add an ML backend, call this API with the ML backend ID to start training with 
        already-labeled tasks. 
        
        Get the ML backend ID by [listing the ML backends for a project](api:GET/api/ml/).
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location='path',
                description='A unique integer value identifying this ML backend.',
            ),
        ],
        request=MLBackendTrainRequestSerializer,
        responses={
            200: OpenApiResponse(description='Training has successfully started.'),
            500: OpenApiResponse(
                description='Training error',
                response={
                    'description': 'Error message',
                    'type': 'string',
                    'example': 'Server responded with an error.',
                },
            ),
        },
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'train',
            'x-fern-audiences': ['public'],
        },
    ),
)
class MLBackendTrainAPI(APIView):
    """
User clicks "Start Training" in UI
             │
             ▼
POST /api/ml/5/train
             │
             ▼
[MLBackendTrainAPI]
  ├── 1. Permission check: Can current user edit this project? (403 if not)
  ├── 2. Lookup check: Does MLBackend #5 exist? (404 if not)
  ├── 3. Execute ml_backend.train()
  │       ├── Send /train HTTP request to remote ML container/server
  │       ├── Update local MLBackend state to 'TRAINING' (or 'ERROR')
  │       └── Record training job ID in database
  │
  └── 4. Return 200 OK immediately (Frontend shows "Training in progress...")
    """
    permission_required = all_permissions.projects_change

    def post(self, request, *args, **kwargs):
        # extracts pk from the URL and looks up the MLBackend record. If that backend does not exist or was deleted, it immediately returns 404 Not Found.
        ml_backend = generics.get_object_or_404(MLBackend, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, ml_backend)

        ml_backend.train()
        return Response(status=status.HTTP_200_OK)


@method_decorator(
    name='post',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Test prediction',
        description="""
        After you add an ML backend, call this API with the ML backend ID to run a test prediction on specific task data               
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location='path',
                description='A unique integer value identifying this ML backend.',
            ),
        ],
        responses={
            200: OpenApiResponse(description='Predicting has successfully started.'),
            500: OpenApiResponse(
                description='Predicting error',
                response={
                    'description': 'Error message',
                    'type': 'string',
                    'example': 'Server responded with an error.',
                },
            ),
        },
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'test_predict',
            'x-fern-audiences': ['internal'],
        },
    ),
)
class MLBackendPredictTestAPI(APIView):
    serializer_class = MLBackendSerializer
    permission_required = all_permissions.projects_change

    def post(self, request, *args, **kwargs):
        ml_backend = generics.get_object_or_404(MLBackend, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, ml_backend)

        random = request.query_params.get('random', False)
        if random:
            task = Task.get_random(project=ml_backend.project)
            if not task:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    data={
                        'detail': 'Project has no tasks to run prediction on, import at least 1 task to run prediction'
                    },
                )

            kwargs = ml_backend._predict(task)
            if not kwargs:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    data={
                        'detail': 'ML backend did not return any predictions, check ML backend logs for more details'
                    },
                )
            return Response(**kwargs)

        else:
            return Response(
                status=status.HTTP_501_NOT_IMPLEMENTED,
                data={'error': 'Not implemented - you must provide random=true query parameter'},
            )


@method_decorator(
    name='post',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Request Interactive Annotation',
        description="""
        Send a request to the machine learning backend set up to be used for interactive preannotations to retrieve a
        predicted region based on annotator input. 
        See [set up machine learning](https://labelstud.io/guide/ml.html#Get-interactive-preannotations) for more.
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location='path',
                description='A unique integer value identifying this ML backend.',
            ),
        ],
        request=MLInteractiveAnnotatingRequest,
        responses={
            200: OpenApiResponse(description='Interactive annotation has succeeded.'),
        },
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'predict_interactive',
            'x-fern-audiences': ['public'],
        },
    ),
)
class MLBackendInteractiveAnnotating(APIView):
    """
    Send a request to the machine learning backend set up to be used for interactive preannotations to retrieve a
    predicted region based on annotator input.
    """

    permission_required = all_permissions.tasks_view

    def _error_response(self, message, log_function=logger.info):
        log_function(message)
        return Response({'errors': [message]}, status=status.HTTP_200_OK)

    def _get_task(self, ml_backend, validated_data):
        return generics.get_object_or_404(Task, pk=validated_data['task'], project=ml_backend.project)

    def _get_credentials(self, request, context, project):
        if flag_set('ff_back_dev_2362_project_credentials_060722_short', request.user):
            context.update(
                project_credentials_login=project.task_data_login,
                project_credentials_password=project.task_data_password,
            )
        return context

    def post(self, request, *args, **kwargs):
        """
        Send a request to the machine learning backend set up to be used for interactive preannotations to retrieve a
        predicted region based on annotator input.
        """
        ml_backend = generics.get_object_or_404(MLBackend, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, ml_backend)
        serializer = MLInteractiveAnnotatingRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = self._get_task(ml_backend, serializer.validated_data)
        context = self._get_credentials(request, serializer.validated_data.get('context', {}), task.project)

        result = ml_backend.interactive_annotating(task, context, user=request.user)

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


@method_decorator(
    name='get',
    decorator=extend_schema(
        tags=['Machine Learning'],
        summary='Get model versions',
        description='Get available versions of the model.',
        responses={
            200: OpenApiResponse(
                description='List of available versions.',
                response={
                    'type': 'object',
                    'properties': {
                        'versions': {
                            'type': 'array',
                            'items': {
                                'type': 'string',
                            },
                        },
                        'message': {
                            'type': 'string',
                        },
                    },
                },
            ),
        },
        extensions={
            'x-fern-sdk-group-name': 'ml',
            'x-fern-sdk-method-name': 'list_model_versions',
            'x-fern-audiences': ['public'],
        },
    ),
)
class MLBackendVersionsAPI(generics.RetrieveAPIView):
    # TODO(jo): implement this view with a serializer and replace the handwritten schema above with it
    permission_required = all_permissions.projects_change

    def get(self, request, *args, **kwargs):
        ml_backend = generics.get_object_or_404(MLBackend, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, ml_backend)
        versions_response = ml_backend.get_versions()
        if versions_response.status_code == 200:
            result = {'versions': versions_response.response.get('versions', [])}
            return Response(data=result, status=200)
        elif versions_response.status_code == 404:
            result = {'versions': [ml_backend.model_version], 'message': 'Upgrade your ML backend version to latest.'}
            return Response(data=result, status=200)
        else:
            result = {'error': str(versions_response.error_message)}
            status_code = versions_response.status_code if versions_response.status_code > 0 else 500
            return Response(data=result, status=status_code)
