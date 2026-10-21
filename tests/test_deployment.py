"""Exercise deployment control flow without touching a service or repository."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/update-production.sh'


class DeploymentTests(unittest.TestCase):
    def run_deploy(self, user='jb', dirty='', restart_status='0'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = {
                'id': 'echo "$TEST_USER"',
                'git': '''
echo "git $*" >> "$TEST_LOG"
case "$3" in
    branch) echo production ;;
    status) printf '%s' "$TEST_DIRTY" ;;
    rev-parse) echo abc123 ;;
esac
''',
                'systemctl': '''
echo "systemctl $*" >> "$TEST_LOG"
if [[ "$1" == --no-ask-password ]]; then exit "$TEST_RESTART_STATUS"; fi
''',
                'curl': 'echo curl >> "$TEST_LOG"',
            }
            for name, body in commands.items():
                path = root / name
                path.write_text('#!/bin/bash\n' + body + '\n')
                path.chmod(0o755)
            log = root / 'commands.log'
            log.touch()
            result = subprocess.run(
                ['bash', str(SCRIPT)], capture_output=True, text=True,
                env={**os.environ, 'PATH': f'{root}:/usr/bin:/bin',
                     'TEST_USER': user, 'TEST_DIRTY': dirty,
                     'TEST_RESTART_STATUS': restart_status, 'TEST_LOG': str(log)},
            )
            return result, log.read_text()

    def test_jb_deploys_and_checks_health(self):
        result, log = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('merge --ff-only origin/production', log)
        self.assertIn('systemctl --no-ask-password restart odoo.service', log)
        self.assertIn('curl', log)

    def test_root_and_other_users_are_rejected_before_git(self):
        for user in ('root', 'other'):
            with self.subTest(user=user):
                result, log = self.run_deploy(user=user)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(log, '')

    def test_dirty_checkout_is_rejected_before_fetch_or_restart(self):
        result, log = self.run_deploy(dirty=' M deploy/update-production.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('fetch', log)
        self.assertNotIn('systemctl', log)

    def test_restart_denial_does_not_report_success(self):
        result, log = self.run_deploy(restart_status='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Deployed production:', result.stdout)
        self.assertNotIn('curl', log)
