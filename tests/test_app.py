import os
import secrets
import hashlib
import tempfile
import unittest
from pathlib import Path

tmp=tempfile.TemporaryDirectory()
os.environ['CODEPUG_DB']=str(Path(tmp.name)/'test.db')
salt=secrets.token_bytes(16)
rounds=100000
passhash=hashlib.pbkdf2_hmac('sha256',b'test-password-not-for-use',salt,rounds).hex()
os.environ['DASHBOARD_PASSWORD_HASH']=f'pbkdf2_sha256${rounds}${salt.hex()}${passhash}'
from fastapi.testclient import TestClient
from dashboard.app import app

class WebTests(unittest.TestCase):
    def test_auth_and_read(self):
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/state').status_code,401)
            r=client.get('/api/state',auth=('admin','test-password-not-for-use'))
            self.assertEqual(r.status_code,200)
            self.assertFalse(r.json()['execution_enabled'])
    def test_agent_flow(self):
        with TestClient(app) as client:
            auth=('admin','test-password-not-for-use')
            r=client.post('/api/agents',auth=auth,json={'label':'Testhost'},headers={'x-codepug-request':'1'})
            self.assertEqual(r.status_code,200,r.text)
            reg=r.json()
            r=client.post('/api/ingest/'+reg['id'],headers={'Authorization':'Bearer '+reg['token']},json={'collected_at':'2026-11-03T00:00:00+00:00','containers':[{'name':'test','image':'busybox:1','state':'running'}]})
            # Timestamp must be recent; out-of-range reports are rejected.
            self.assertEqual(r.status_code,422)
if __name__=='__main__':unittest.main()
