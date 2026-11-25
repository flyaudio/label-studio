"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

from django.urls import include, path

from . import api

app_name = 'ml'

# ML backend CRUD
_api_urlpatterns = [
    # All ml backends
    """
    GET request: List all items (returns a JSON array of items),e.g /api/ml/?project=123&is_interactive=true
    POST request: Create a new item (receives JSON and saves a new record to the database).   
    """
    path('', api.MLBackendListAPI.as_view(), name='ml-list'),
    path('<int:pk>', api.MLBackendDetailAPI.as_view(), name='ml-detail'),
    path('<int:pk>/train', api.MLBackendTrainAPI.as_view(), name='ml-train'),
    path('<int:pk>/predict/test', api.MLBackendPredictTestAPI.as_view(), name='ml-predict-test'),
    path(
        '<int:pk>/interactive-annotating',
        api.MLBackendInteractiveAnnotating.as_view(),
        name='ml-interactive-annotating',
    ),
    path('<int:pk>/versions', api.MLBackendVersionsAPI.as_view(), name='ml-versions'),
]

urlpatterns = [
    path('api/ml/', include((_api_urlpatterns, app_name), namespace='api')),# 外层前缀：'api/ml/'
]
