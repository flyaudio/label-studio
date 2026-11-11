"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for
copyright information and LICENSE for a copy of the license.
"""

import logging
import os
import re
from functools import cached_property
from typing import TYPE_CHECKING, Optional
from urllib.parse import unquote, urlparse

import requests
from core.feature_flags import flag_set
from core.utils.io import ssrf_safe_session
from django.conf import settings
from requests.adapters import HTTPAdapter
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from users.models import User

# The converter refuses to fetch Label Studio media without a token. It gets this placeholder instead of a real
# one: ExportMediaAdapter authenticates the requests it lets through.
CONVERTER_ACCESS_TOKEN = 'export-media'

# Label Studio paths that serve task media, relative to the hostname
EXPORT_MEDIA_PATH_RE = re.compile(r'^/(data/upload/|storage-data/uploaded/$|tasks/\d+/presign/$)')


def get_export_hostname(request) -> Optional[str]:
    """Label Studio base URL for the export converter, which fetches media stored in Label Studio there.

    Returns None when there is no trustworthy value: the converter then skips media it would have to fetch
    from Label Studio.
    """
    # With DOMAIN_FROM_REQUEST HOSTNAME is only a subpath
    if settings.HOSTNAME and not settings.DOMAIN_FROM_REQUEST:
        return settings.HOSTNAME
    # A Host header is attacker-controlled unless ALLOWED_HOSTS or the DOMAIN_FROM_REQUEST proxy pins it
    if settings.DOMAIN_FROM_REQUEST or '*' not in settings.ALLOWED_HOSTS:
        return request.build_absolute_uri('/')
    return None


class ExportMediaAdapter(HTTPAdapter):
    """Sends the export converter's requests to Label Studio itself, authenticated as ``user``.

    Task data can point at any Label Studio URL and the response ends up in the export archive, so only
    media paths are fetched, and only as the user who exports: they get no file they couldn't open themselves.
    The credentials are made here for each request, so the converter never holds them.
    """

    def __init__(self, hostname, user, **kwargs):
        super().__init__(**kwargs)
        self.base_path = urlparse(hostname).path.rstrip('/')
        self.user = user

    def is_media_path(self, path) -> bool:
        path = unquote(path)
        # Proxies resolve dot segments, so /data/upload/../api/... would reach the API
        if '\\' in path or any(segment in ('.', '..') for segment in path.split('/')):
            return False
        if not path.startswith(self.base_path + '/'):
            return False
        return bool(EXPORT_MEDIA_PATH_RE.match(path[len(self.base_path) :]))

    @cached_property
    def accepts_jwt(self) -> bool:
        # Same checks as JWTAuthenticationMiddleware: the legacy token is used only where a JWT is not accepted
        org = self.user.active_organization
        jwt_auth = flag_set('fflag__feature_develop__prompts__dia_1829_jwt_token_auth', user=self.user)
        return jwt_auth and org is not None and org.jwt.api_tokens_enabled

    def authorization(self) -> str:
        if self.accepts_jwt:
            # Minted per request: a short-lived token outlives no download, however long the export runs
            return f'Bearer {AccessToken.for_user(self.user)}'
        return f'Token {self.user.auth_token.key}'

    def send(self, request, *args, **kwargs):
        if self.user is None:
            raise requests.exceptions.InvalidURL(f'Export has no user to fetch Label Studio media as: {request.url}')
        if not self.is_media_path(urlparse(request.url).path):
            raise requests.exceptions.InvalidURL(f'Export does not fetch non-media Label Studio URL: {request.url}')
        request.headers['Authorization'] = self.authorization()
        return super().send(request, *args, **kwargs)


def converter_http_session(hostname: Optional[str], user: Optional['User']) -> requests.Session:
    """HTTP session for the export converter's media downloads.

    Task data can point media at any URL, and the fetched bytes end up in the export archive. Requests to
    Label Studio itself (``hostname``) are limited to media paths and authenticated as ``user``, the user who
    exports; without one, none are sent.
    """
    if settings.SSRF_PROTECTION_ENABLED:
        session = ssrf_safe_session()
    else:
        session = requests.Session()
    if hostname:
        parsed = urlparse(hostname)
        # Label Studio's own host may resolve to a private address on self-hosted installs;
        # the trailing slash keeps app.example.com.evil.com from matching the prefix
        session.mount(f'{parsed.scheme}://{parsed.netloc}/', ExportMediaAdapter(hostname, user))
    return session


# Uploaded file names look like <8-hex-uuid>-<original-name>.<ext> (see
# data_import.models.upload_name_generator). The prefix guarantees uniqueness on
# the server; it is cosmetic in exports, so it gets stripped there.
UUID_FILENAME_PREFIX_RE = re.compile(r'^[0-9a-f]{8}-')

TEXT_REFERENCE_EXTENSIONS = {'.json', '.xml', '.txt', '.md', '.yaml', '.yml'}


def strip_uuid_prefixes_from_export(output_dir):
    """Drop the ``uuid8-`` prefix from file names in a multi-file export
    (e.g. YOLO/VOC/COCO archives: images and label files), and update
    references to those names inside text files (notes.json, COCO result.json,
    VOC XML <filename> tags, ...).

    Single-file exports (JSON/CSV) are left untouched: their task data paths
    reference server-side files and must stay valid.

    If two exported files would collide after stripping (same original file
    name uploaded twice), the later one keeps its prefixed name.
    """
    if len(os.listdir(output_dir)) <= 1:
        return

    renames = []
    claimed = set()

    for dirpath, _, filenames in os.walk(output_dir):
        for name in filenames:
            new_name = UUID_FILENAME_PREFIX_RE.sub('', name)
            if new_name == name:
                continue
            old_path = os.path.join(dirpath, name)
            new_path = os.path.join(dirpath, new_name)
            if new_path in claimed:
                logger.warning(
                    'Skipping uuid-strip rename for %s: target name %s already claimed',
                    old_path,
                    new_path,
                )
                continue
            claimed.add(new_path)
            renames.append((old_path, new_path, name, new_name))

    if not renames:
        return

    # Update references inside text files before renaming the files themselves.
    for dirpath, _, filenames in os.walk(output_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.splitext(name)[1].lower() not in TEXT_REFERENCE_EXTENSIONS:
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            updated = content
            for _, _, old_name, new_name in renames:
                updated = updated.replace(old_name, new_name)
            if updated != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(updated)

    for old_path, new_path, _, _ in renames:
        os.replace(old_path, new_path)
