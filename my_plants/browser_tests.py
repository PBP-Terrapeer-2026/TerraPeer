"""Opt-in real browser suite; setup is documented in README.md."""
import base64
import os
from pathlib import Path
import shutil
import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from .tests import photo_upload


class MyPlantsBrowserTests(StaticLiveServerTestCase):
    def test_real_browser_crud_filters_optimistic_rollback_and_responsive_layout(self):
        get_user_model().objects.create_user('browser-gardener', password='Browser-Test-2026!')
        env = os.environ.copy()
        env['TERRAPEER_TEST_URL'] = self.live_server_url
        env['TERRAPEER_TEST_PHOTO'] = base64.b64encode(photo_upload().read()).decode()
        node = os.environ.get('NODE_BINARY') or shutil.which('node')
        self.assertIsNotNone(node, 'Install Node.js to run the browser suite.')
        result = subprocess.run(
            [node, str(Path(settings.BASE_DIR) / 'tests/browser/my-plants.cjs')],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, encoding='utf-8', timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
