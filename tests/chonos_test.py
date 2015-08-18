import unittest
import chronos


class ComputeDateBaseTest(unittest.TestCase):
    def test_without_date(self):
        self.assertEqual(chronos.compute_date_base('html data', None), 0)
