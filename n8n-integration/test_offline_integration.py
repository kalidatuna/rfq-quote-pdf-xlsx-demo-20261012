"""Offline contract check for the importable synthetic n8n workflow.

Exercises the exported Execute Command shell with real PDF/CSV inputs in a
temporary directory and the exported Code node with a local Node.js runtime.
Does not require or claim a running n8n server.
"""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
DEMO = HERE.parent  # In-repository integration: the demo is the parent folder
EXPORT = HERE / 'workflow.json'
NODE_RUNNER = r"""
const fs = require('fs');
const [code, data] = JSON.parse(fs.readFileSync(0, 'utf8'));
try {
  const run = new Function('$input', code);
  process.stdout.write(JSON.stringify(run({first: () => ({json: data})})));
} catch (error) {
  process.stderr.write(String(error.message));
  process.exitCode = 2;
}
"""


def workflow():
    return json.loads(EXPORT.read_text(encoding='utf-8'))


def execute_node(wf):
    return next(node for node in wf['nodes']
                if node['type'] == 'n8n-nodes-base.executeCommand')


def parse_node(wf):
    return next(node for node in wf['nodes']
                if node['type'] == 'n8n-nodes-base.code')


def run_js(code, data):
    return subprocess.run(['node', '-e', NODE_RUNNER],
                          input=json.dumps([code, data]), text=True,
                          capture_output=True, check=False, timeout=15)


class OfflineN8NStarterTests(unittest.TestCase):
    def test_export_is_inactive_manual_local_only_workflow(self):
        wf = workflow()
        self.assertFalse(wf['active'])
        self.assertEqual([n['type'] for n in wf['nodes']], [
            'n8n-nodes-base.manualTrigger',
            'n8n-nodes-base.executeCommand',
            'n8n-nodes-base.code',
        ])
        self.assertEqual(wf['nodes'][1]['name'],
                         wf['connections'][wf['nodes'][0]['name']]['main'][0][0]['node'])
        self.assertEqual(wf['nodes'][2]['name'],
                         wf['connections'][wf['nodes'][1]['name']]['main'][0][0]['node'])
        self.assertNotIn('credentials', json.dumps(wf).lower())
        self.assertEqual(parse_node(wf)['parameters']['mode'], 'runOnceForAllItems')

    def test_real_shell_command_and_code_node_from_export(self):
        wf = workflow()
        command = execute_node(wf)['parameters']['command']
        code = parse_node(wf)['parameters']['jsCode']
        with tempfile.TemporaryDirectory(prefix='rfq n8n workspace ') as folder:
            demo_copy = Path(folder) / 'synthetic demo'
            demo_copy.mkdir()
            for filename in ('pipeline.py', 'xlsx_writer.py'):
                shutil.copy2(DEMO / filename, demo_copy / filename)
            shutil.copytree(DEMO / 'samples', demo_copy / 'samples')
            env = {**os.environ, 'RFQ_DEMO_HOME': str(demo_copy)}
            run = subprocess.run(['/bin/sh', '-c', command], env=env,
                                 capture_output=True, text=True,
                                 check=False, timeout=40)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = run_js(code, {'stdout': run.stdout, 'stderr': run.stderr,
                                   'exitCode': run.returncode})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [{
                'json': {'status': 'DRAFT / DO NOT SEND',
                         'rows': 10, 'priced': 2, 'review': 8,
                         'approvedLinesSubtotalUSD': '61.25',
                         'outputRelativePath': 'outputs/quote_n8n_demo.xlsx',
                         'requiresHumanReview': True}
            }])
            self.assertTrue((demo_copy / 'outputs/quote_n8n_demo.xlsx').is_file())
            self.assertEqual(len(list((demo_copy / 'outputs').iterdir())), 1)

    def test_unconfigured_environment_fails_before_generating_quote(self):
        command = execute_node(workflow())['parameters']['command']
        env = {key: val for key, val in os.environ.items() if key != 'RFQ_DEMO_HOME'}
        result = subprocess.run(['/bin/sh', '-c', command], env=env,
                                capture_output=True, text=True, check=False, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RFQ_DEMO_HOME', result.stderr)

    def test_code_node_rejects_bad_count_summary(self):
        code = parse_node(workflow())['parameters']['jsCode']
        summary = ('DEMO ONLY | rows=10 priced=11 review=0 priced_subtotal=61.25 '
                   '| outputs/quote_n8n_demo.xlsx')
        result = run_js(code, {'stdout': summary, 'exitCode': 0})
        self.assertEqual(result.returncode, 2)
        self.assertIn('inconsistent line counts', result.stderr)


if __name__ == '__main__':
    unittest.main()
