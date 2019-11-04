import unittest
from config import Config


class TestEkaterina(unittest.TestCase):

    def test_config(self):
        config = Config()
        self.assertEqual(config.room_number, 888)
        self.assertIsNotNone(config.db_config)
        self.assertIsNotNone(config.db_config.server)
        self.assertIsNotNone(config.db_config.user)
        self.assertIsNotNone(config.db_config.password)
        self.assertIsNotNone(config.db_config.database)
        self.assertIsNotNone(config.lock_timeout)
        self.assertIsNotNone(config.new_key_check_interval)
        self.assertIsNotNone(config.rfig_key_table_index)


if __name__ == "__main__":
    unittest.main()
