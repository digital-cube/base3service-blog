from base import test
import unittest
import importlib

import os

current_file_folder = os.path.dirname(os.path.realpath(__file__))

id_user = '00000000-0000-0000-0000-000000000001'
id_session = '00000000-0000-0000-0000-000000000002'
random_uuid = '00000000-0000-0000-0000-000000000003'
mockJWT = '123456'


def token2user(_):
    return {
        'id': id_session,
        'id_user': id_user,
        'permissions': 0
    }


class SetUpTestblBlogServiceBase(test.BaseTest):

    def prefix(self):
        return '/api/blog'

    def setUp(self):
        from base import registry, orm, app, config

        config.load_from_yaml(current_file_folder + f'/../config/config.{os.getenv("ENVIRONMENT", "local")}.yaml')
        config.conf['db']['database'] = f"test_{config.conf['db']['database']}"

        importlib.import_module('orm.models')
        registry.test = True

        orm = orm.init_orm(config.conf['db'])

        orm.clear_database()
        orm.create_db_schema()

        importlib.import_module('api.blog')

        config.init_logging()
        self.my_app = app.make_app(debug=True)

        super().setUp()
        registry.test_port = self.get_http_port()


if __name__ == '__main__':
    unittest.main()
