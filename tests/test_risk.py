import unittest
from dashboard.risk import classify,chosen_risk,effective_risk,permitted_mode
class RiskTests(unittest.TestCase):
    def test_database_critical(self):
        self.assertEqual(classify({'name':'lamp-couch_db','image':'mariadb:11'})['minimum'],'critical')
    def test_socket_high(self):
        self.assertEqual(classify({'name':'homarr','image':'homarr:1.0','docker_socket':True})['minimum'],'high')
    def test_latest_medium(self):
        self.assertEqual(classify({'name':'dashboard','image':'dashboard:latest'})['minimum'],'medium')
    def test_raise_not_lower(self):
        self.assertEqual(effective_risk('critical','low'),'critical')
    def test_user_can_choose_low_while_hard_floor_remains_high(self):
        self.assertEqual(chosen_risk('high', 'low'), 'low')
        self.assertEqual(effective_risk('high', 'low'), 'high')
        self.assertFalse(permitted_mode('auto', effective_risk('high','low')))
        self.assertTrue(permitted_mode('approve', effective_risk('high','low')))

    def test_auto_only_low(self):
        self.assertFalse(permitted_mode('auto','medium'))
        self.assertTrue(permitted_mode('auto','low'))
if __name__=='__main__':unittest.main()
