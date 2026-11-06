"""Tests explaining the thin Django page views in projects/views.py.

These views enforce login and choose the HTML shell. React renders the actual
project pages, while project data is served by the API endpoints.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from projects.views import project_list, project_settings


@pytest.mark.parametrize(
    ("view", "view_args", "url", "template_name"),
    [
        pytest.param(project_list, (), "/projects/", "projects/list.html", id="project-list"),
        pytest.param(
            project_settings,
            (12, "general"),
            "/projects/12/settings/general",
            "projects/settings.html",
            id="project-settings",
        ),
    ],
)
def test_project_page_views_require_login_and_render_page_shell(view, view_args, url, template_name):
    """Both page views require an authenticated user and select the expected template."""
    print("url=", url)
    factory = RequestFactory()

    anonymous_request = factory.get(url)
    anonymous_request.user = AnonymousUser()
    anonymous_response = view(anonymous_request, *view_args)

    assert anonymous_response.status_code == 302
    assert anonymous_response["Location"].startswith("/user/login/")

    authenticated_request = factory.get(url)
    authenticated_request.user = SimpleNamespace(is_authenticated=True)
    with patch("projects.views.render", return_value=HttpResponse("page shell")) as render_mock:
        response = view(authenticated_request, *view_args)

    assert response.status_code == 200
    render_mock.assert_called_once_with(authenticated_request, template_name)

"""
python -m pytest ./label_studio/projects/test_views.py -v -s
"""