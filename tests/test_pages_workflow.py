"""Regression cases for Pages job gating, including GitHub's implicit success()."""

import ast
from pathlib import Path
import re
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'pages.yml'


def deploy_condition():
    block = WORKFLOW.read_text(encoding='utf-8').split('\n  deploy:\n', 1)[1]
    expression = re.search(r'^    if: (.+)$', block, re.MULTILINE).group(1)
    return expression.removeprefix('${{').removesuffix('}}').strip()


def eligible(expression, event, operation='build', build='success', catalog='skipped',
             cancelled=False, ref='refs/heads/main', repository='Gon3s/lorcana-coconut-proxies-fr'):
    # This workflow uses only boolean operators, equality and status functions.
    # GitHub adds success() when no explicit status-check function is present.
    upstream_success = build == 'success' and catalog == 'success' and not cancelled
    if not re.search(r'\b(?:always|cancelled|success|failure)\s*\(', expression):
        if not upstream_success:
            return False
    for name, value in {'always': True, 'cancelled': cancelled,
                        'success': upstream_success, 'failure': build == 'failure'}.items():
        expression = expression.replace(f'{name}()', repr(value))
    context = {'github.ref': ref, 'github.repository': repository,
               'github.event_name': event, 'inputs.operation': operation,
               'needs.build.result': build}
    expression = re.sub(r'\b(?:github|inputs|needs)\.[\w.]+',
                        lambda match: repr(context[match.group()]), expression)
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    expression = re.sub(r'!(?!=)', 'not ', expression).strip()

    def evaluate(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BoolOp):
            values = [evaluate(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not evaluate(node.operand)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            return evaluate(node.left) == evaluate(node.comparators[0])
        raise ValueError('Unsupported Pages condition syntax; update the regression cases')

    return bool(evaluate(ast.parse(expression, mode='eval').body))


class PagesWorkflowTests(unittest.TestCase):
    def test_human_merge_publishes_after_build_even_when_catalog_job_is_skipped(self):
        self.assertTrue(eligible(deploy_condition(), 'push'))

    def test_manual_build_publishes_when_catalog_job_is_skipped(self):
        self.assertTrue(eligible(deploy_condition(), 'workflow_dispatch', operation='build'))

    def test_weekly_run_publishes_after_catalog_and_build_succeed(self):
        for event in ('schedule', 'workflow_dispatch'):
            with self.subTest(event=event):
                self.assertTrue(eligible(deploy_condition(), event, operation='weekly', catalog='success'))

    def test_failed_skipped_or_cancelled_build_never_publishes(self):
        for build in ('failure', 'skipped', 'cancelled'):
            with self.subTest(build=build):
                self.assertFalse(eligible(deploy_condition(), 'push', build=build))
        self.assertFalse(eligible(deploy_condition(), 'push', cancelled=True))

    def test_pr_check_only_other_branch_and_other_repo_never_publish(self):
        self.assertFalse(eligible(deploy_condition(), 'pull_request', catalog='success'))
        self.assertFalse(eligible(deploy_condition(), 'workflow_dispatch', operation='check', catalog='success'))
        self.assertFalse(eligible(deploy_condition(), 'push', ref='refs/heads/feature', catalog='success'))
        self.assertFalse(eligible(deploy_condition(), 'push', repository='other/repo', catalog='success'))


if __name__ == '__main__':
    unittest.main()
