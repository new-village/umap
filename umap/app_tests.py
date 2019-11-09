import app
import unittest
import json


class UmapTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def api_root_endpoint(self):
        response = self.app.get('/api/')
        data = json.loads(response.get_data(as_text=True))
        assert data["hello"] == "world"


if __name__ == '__main__':
    unittest.main()
