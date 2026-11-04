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
    def test_diagnostics_requires_auth_and_is_read_only(self):
        from unittest.mock import patch
        sample = {
            "services": [{
                "key": "local/demo", "server_id": "local", "name": "demo",
                "status": "Up 2 days (unhealthy)", "state": "running",
                "risk": "high", "notes": "DO NOT COPY"
            }],
            "servers": [{
                "id": "local", "label": "Test Ubuntu", "online": True,
                "age_seconds": 11
            }]
        }
        with TestClient(app) as client, patch('dashboard.app.build_state', return_value=sample):
            url = '/api/diagnostics?service_key=local%2Fdemo'
            self.assertEqual(client.get(url).status_code, 401)
            result = client.get(url, auth=('admin','test-password-not-for-use'))
            self.assertEqual(result.status_code, 200, result.text)
            content = result.json()
            self.assertEqual(content['code'], 'unhealthy')
            self.assertFalse(content['execution_enabled'])
            self.assertNotIn('DO NOT COPY', str(content))
            self.assertEqual(client.get('/api/diagnostics?service_key=local%2Fmissing',
                                        auth=('admin','test-password-not-for-use')).status_code, 404)

    def test_recovery_endpoints_authenticated_and_non_executable(self):
        from unittest.mock import patch
        sample = {
            "services": [{
                "key": "local/db", "server_id": "local", "name": "db",
                "status": "Up", "state": "running", "risk": "critical",
                "notes": "SHOULD-NOT-BE-EXPORTED"
            }],
            "servers": [{"id":"local","label":"Host","online":True,"age_seconds":15}]
        }
        with TestClient(app) as client, patch("dashboard.app.build_state", return_value=sample):
            auth = ("admin","test-password-not-for-use")
            self.assertEqual(client.get("/api/recovery/overview").status_code,401)
            overview=client.get("/api/recovery/overview",auth=auth)
            self.assertEqual(overview.status_code,200,overview.text)
            self.assertFalse(overview.json()["execution_enabled"])
            self.assertIsNone(overview.json()["verified_backup_count"])
            self.assertEqual(overview.json()["hosts"][0]["backup_status"],"unknown")
            plan=client.get("/api/recovery/plan?service_key=local%2Fdb",auth=auth)
            self.assertEqual(plan.status_code,200,plan.text)
            self.assertFalse(plan.json()["backup_verified"])
            self.assertFalse(plan.json()["execution_enabled"])
            self.assertNotIn("SHOULD-NOT-BE-EXPORTED",str(plan.json()))
            self.assertEqual(client.get("/api/recovery/plan?service_key=local%2Fmissing",
                                auth=auth).status_code,404)

    def test_manual_low_priority_and_update_check_are_separate(self):
        from unittest.mock import patch
        sample={
            "services":[{
                "key":"local/codepug-test","server_id":"local",
                "name":"codepug-test","image":"redis:7.2.4",
                "minimum_risk":"high","risk":"high","mode":"monitor",
                "status":"exited","state":"exited","notes":""
            }],
            "servers":[{"id":"local","label":"Host","online":True,"age_seconds":12}]
        }
        with TestClient(app) as client, patch("dashboard.app.build_state",return_value=sample):
            auth=("admin","test-password-not-for-use")
            headers={"x-codepug-request":"1"}
            url="/api/policies"
            body={"service_key":"local/codepug-test","risk_override":"low",
                  "mode":"approve","notes":"only test"}
            result=client.post(url,auth=auth,json=body,headers=headers)
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()["risk"],"low")
            self.assertEqual(result.json()["safety_risk"],"high")
            self.assertFalse(result.json()["execution_enabled"])
            rejected=client.post(url,auth=auth,headers=headers,
                json={**body,"mode":"auto"})
            self.assertEqual(rejected.status_code,422)
            check_body={"service_key":"local/codepug-test"}
            self.assertEqual(client.post("/api/updates/check",json=check_body).status_code,401)
            self.assertEqual(client.post("/api/updates/check",auth=auth,
                json=check_body).status_code,403)
            with patch("dashboard.app.check_public_docker_hub",
                return_value={"status":"candidate","current_image":"redis:7.2.4",
                              "candidate_tag":"7.4.2","execution_enabled":False}):
                checked=client.post("/api/updates/check",auth=auth,
                    headers=headers,json=check_body)
            self.assertEqual(checked.status_code,200,checked.text)
            self.assertEqual(checked.json()["candidate_tag"],"7.4.2")
            self.assertFalse(checked.json()["execution_enabled"])

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
                  'alerts_enabled':True,'notify_unhealthy':False,
                  'auto_version_checks':False,'version_check_interval_hours':24}
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
