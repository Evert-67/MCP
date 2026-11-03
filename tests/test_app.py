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
    def test_settings_preferences(self):
        with TestClient(app) as client:
            auth=('admin','test-password-not-for-use')
            state=client.get('/api/state',auth=auth).json()
            self.assertIn('settings',state)
            self.assertIn('agents',state)
            data={'refresh_seconds':30,'offline_after_seconds':600,
                  'alerts_enabled':True,'notify_unhealthy':False}
            r=client.post('/api/settings',auth=auth,json=data)
            self.assertEqual(r.status_code,403)
            r=client.post('/api/settings',auth=auth,json=data,
                          headers={'x-codepug-request':'1'})
            self.assertEqual(r.status_code,200,r.text)
            settings=client.get('/api/state',auth=auth).json()['settings']
            self.assertEqual(settings,data)
            bad={**data,'refresh_seconds':0}
            r=client.post('/api/settings',auth=auth,json=bad,
                          headers={'x-codepug-request':'1'})
            self.assertEqual(r.status_code,422)

    def test_agent_management_and_revocation(self):
        with TestClient(app) as client:
            auth=('admin','test-password-not-for-use')
            headers={'x-codepug-request':'1'}
            r=client.post('/api/agents',auth=auth,json={'label':'New server'},
                          headers=headers)
            self.assertEqual(r.status_code,200,r.text)
            d=r.json()
            url='/api/agent-config/'+d['id']
            self.assertEqual(client.get(url,headers={'Authorization':'Bearer wrong'}).status_code,403)
            r=client.get(url,headers={'Authorization':'Bearer '+d['token']})
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['scan_interval'],120)
            r=client.patch('/api/agents/'+d['id'],auth=auth,
                           headers=headers,json={'label':'Renamed','scan_interval':300})
            self.assertEqual(r.status_code,200,r.text)
            r=client.get(url,headers={'Authorization':'Bearer '+d['token']})
            self.assertEqual(r.json()['scan_interval'],300)
            state=client.get('/api/state',auth=auth).json()
            self.assertEqual(next(a for a in state['agents'] if a['id']==d['id'])['label'],'Renamed')
            self.assertNotIn('token_hash',str(state['agents']))
            r=client.delete('/api/agents/'+d['id'],auth=auth,headers=headers)
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(client.get(url,headers={'Authorization':'Bearer '+d['token']}).status_code,404)

if __name__=='__main__':unittest.main()
