# encoding: utf-8
import time
import os.path

from ckan.tests import helpers
import logging
import pytest
from assertpy import assert_that
from ckan.common import config
import subprocess

import ckanext.restricted.action
import ckanext.restricted.plugin
import ckanext.restricted.tests.old_action


log = logging.getLogger(__name__)


@pytest.fixture
def import_performance_data(clean_db, clean_index):
    raw_db_url = config['sqlalchemy.url']
    ckan_dir = get_ckan_directory()
    sql_file = f'{ckan_dir}/ckanext-restricted/ckanext/restricted/tests/performance_test_data.sql'
    cmd = ['psql',  f'{raw_db_url}', "-f", f'{sql_file}', '> /dev/null']
    cmd = ["find", "/", "-iname", "performance_test_data.sql"]

    log.info(f"Loading performance data using: '{cmd}'")
    subprocess.run(cmd)
    ini_file = f"{ckan_dir}/ckan/test.ini"

    cmd = [get_ckan_binary_path(), '-c', ini_file, 'search-index', 'rebuild']
    log.info(f"Rebuild indexes: {cmd}")
    subprocess.run(cmd)


def get_ckan_directory():
    candidates = ['/usr/lib/ckan/submodules', '/srv/app/src']

    for dir_path in candidates:
        if os.path.isdir(dir_path):
            return dir_path

    raise FileNotFoundError('Cannot find ckan directory')


def get_ckan_binary_path():
    candidates = ['/usr/local/bin/ckan', '/usr/bin/ckan']

    for file_path in candidates:
        if os.path.isfile(file_path):
            return file_path

    raise FileNotFoundError("Cannot find ckan binary")


@pytest.fixture(autouse=True)
def add_old_search_action():
    ckanext.restricted.plugin.RestrictedPlugin.get_actions = Helper.get_actions_with_old_search


class Helper:
    def get_actions_with_old_search(self):
        return {'user_create': ckanext.restricted.action.restricted_user_create_and_notify,
                'resource_view_list': ckanext.restricted.action.resource_view_list,
                'package_show': ckanext.restricted.action.restricted_package_show,
                'resource_search': ckanext.restricted.action.restricted_resource_search,
                'package_search': ckanext.restricted.action.restricted_package_search,
                'restricted_check_access': ckanext.restricted.action.restricted_check_access,
                'package_search_old': ckanext.restricted.tests.old_action.restricted_package_search}


@pytest.mark.usefixtures(u'add_old_search_action')
@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
@pytest.mark.usefixtures(u'import_performance_data')
class TestRestrictedSearchPerformance:

    def test_performance(self):
        avg_time = self.get_avg_run_time(self._perform_search)
        old_avg_time = self.get_avg_run_time(self._perform_old_search)

        log.warning(f"Avg time: {avg_time}, old avg time: {old_avg_time}")

    def get_avg_run_time(self, search_function):
        context = {
            'ignore_auth': False,
            'user': 'test_user_00'
        }

        cumulative_time = 0.0
        iter_count = 10

        for i in range(0, iter_count):
            start = time.perf_counter()
            result = search_function(context)
            end = time.perf_counter()
            cumulative_time += end - start
            assert_that(result['count']).is_equal_to(299)

        return cumulative_time / iter_count

    def _perform_search(self, context):
        return helpers.call_action(
            'package_search',
            context,
            q="title:Dataset"
        )

    def _perform_old_search(self, context):
        return helpers.call_action(
            'package_search_old',
            context,
            q="title:Dataset"
        )
