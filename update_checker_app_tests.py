import httplib
import json

from update_checker_app import create_app, db
import unittest


CHECK_ATTRS = ['package_name', 'package_version', 'platform', 'python_version']


class UpdateCheckerAppTestCase(unittest.TestCase):
    def check(self, content_type='application/json', ip_address='127.0.0.1',
              user_agent='python-requests', **json_overrides):
        return self.client.put(
            '/check', data=json.dumps(check_data(**json_overrides)),
            environ_base={'REMOTE_ADDR': ip_address},
            headers={'Content-type': content_type, 'User-Agent': user_agent})

    def setUp(self):
        self.app = create_app('postgresql://@/updatechecker_test')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all(app=self.app)

    def tearDown(self):
        with self.app.app_context():
            db.drop_all(app=self.app)

    def test_check(self):
        response = self.check()
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(['data', 'success'], data.keys())
        self.assertEqual(['upload_time', 'version'], data['data'].keys())
        self.assertTrue(data['success'])
        self.assertEqual('3.6.0', data['data']['version'])

    def test_check__prerelease(self):
        response = self.check(package_version='3.0b1')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(['data', 'success'], data.keys())
        self.assertEqual(['upload_time', 'version'], data['data'].keys())
        self.assertTrue(data['success'])
        self.assertEqual('4.0.0rc3', data['data']['version'])

    def test_check__blank_attribute(self):
        for attribute in CHECK_ATTRS:
            response = self.check(**{attribute: ''})
            self.assertEqual(httplib.BAD_REQUEST, response.status_code)
            self.assertIn('Bad Request', response.get_data())

    def test_check__missing_attribute(self):
        for attribute in CHECK_ATTRS:
            response = self.check(**{attribute: None})
            self.assertEqual(httplib.BAD_REQUEST, response.status_code)
            self.assertIn('Bad Request', response.get_data())

    def test_check__not_requests(self):
        response = self.check(user_agent='not_requests')
        self.assertEqual(httplib.FORBIDDEN, response.status_code)
        self.assertIn('Forbidden', response.get_data())

    def test_packages__multiple_packages(self):
        for package in ['praw', 'prawtools']:
            response = self.check(package_name=package)
            self.assertEqual(httplib.OK, response.status_code)

        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(2, len(data))
        for item in data:
            self.assertEqual(1, item['count'])
            self.assertIn('package', item)
            self.assertEqual(1, data[0]['unique'])
            self.assertIn('version', item)

    def test_packages__multiple_versions(self):
        for i in range(10):
            response = self.check(package_version='3.0.{}'.format(i))
            self.assertEqual(httplib.OK, response.status_code)

        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(10, len(data))
        for item in data:
            self.assertEqual(1, item['count'])
            self.assertIn('package', item)
            self.assertEqual(1, data[0]['unique'])
            self.assertIn('version', item)

    def test_packages__single_entry(self):
        response = self.check()
        self.assertEqual(httplib.OK, response.status_code)

        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual('http://localhost:8080',
                         response.headers.get('Access-Control-Allow-Origin'))
        self.assertEqual(1, len(data))
        self.assertEqual(1, data[0]['count'])
        self.assertEqual('praw', data[0]['package'])
        self.assertEqual(1, data[0]['unique'])
        self.assertIn('version', data[0])

    def test_packages__single_package_multiple_addresses(self):
        for i in range(1, 11):
            response = self.check(ip_address='127.0.0.{}'.format(i))
            self.assertEqual(httplib.OK, response.status_code)

        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(1, len(data))
        self.assertEqual(10, data[0]['count'])
        self.assertEqual('praw', data[0]['package'])
        self.assertEqual(10, data[0]['unique'])
        self.assertIn('version', data[0])

    def test_packages__single_package_single_address(self):
        for _ in range(10):
            response = self.check()
            self.assertEqual(httplib.OK, response.status_code)

        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        data = json.loads(response.get_data())
        self.assertEqual(1, len(data))
        self.assertEqual(10, data[0]['count'])
        self.assertEqual('praw', data[0]['package'])
        self.assertEqual(1, data[0]['unique'])
        self.assertIn('version', data[0])

    def test_packages__no_data(self):
        response = self.client.get('/packages')
        self.assertEqual(httplib.OK, response.status_code)
        self.assertEqual([], json.loads(response.get_data()))

    def test_root(self):
        response = self.client.get('/')
        self.assertEqual(httplib.NO_CONTENT, response.status_code)
        self.assertEqual('', response.get_data())


def check_data(package_name='praw', package_version='3.6.0',
               platform='darwin-16.1.0-x86_64-64bit', python_version='3.5'):
    retval = {}
    for attr in CHECK_ATTRS:
        if locals()[attr] is not None:
            retval[attr] = locals()[attr]
    return retval


if __name__ == '__main__':
    unittest.main()
