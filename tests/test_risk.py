import unittest
from dashboard.risk import classify,effective_risk,permitted_mode
class RiskTests(unittest.TestCase):
    def test_database_critical(self):
        self.assertEqual(classify({'name':'lamp-couch_db','image':'mariadb:11'})['minimum'],'critical')
    def test_socket_high(self):
        self.assertEqual(classify({'name':'homarr','image':'homarr:1.0','docker_socket':True})['minimum'],'high')
    def test_latest_medium(self):
        self.assertEqual(classify({'name':'dashboard','image':'dashboard:latest'})['minimum'],'medium')
    def test_raise_not_lower(self):
        self.assertEqual(effective_risk('critical','low'),'critical')
    def test_auto_only_low(self):
        self.assertFalse(permitted_mode('auto','medium'))
        self.assertTrue(permitted_mode('auto','low'))
if __name__=='__main__':unittest.main()
