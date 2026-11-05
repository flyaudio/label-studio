"""Projects Django App Configuration"""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ProjectsConfig(AppConfig):
    name = 'projects'

    def ready(self): # django.setup()会调用的钩子，做初始化
        """
        Projects app initialization.

        Note: FSM transitions are now registered centrally in fsm/apps.py.
        Do NOT import transitions here to avoid duplicate registration.
        """
        pass
