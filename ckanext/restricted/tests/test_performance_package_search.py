# encoding: utf-8
import time

from ckan.tests import helpers
import logging
import pytest
from assertpy import assert_that
from ckan.common import config
import subprocess


log = logging.getLogger(__name__)


@pytest.fixture
def import_performance_data(clean_db, clean_index):
    raw_db_url = config['sqlalchemy.url']
    sql_file = '/usr/lib/ckan/submodules/ckanext-restricted/ckanext/restricted/tests/performance_test_data.sql'
    cmd = [f"psql",  f"{raw_db_url}", "-f", f"{sql_file}", "> /dev/null"]

    log.info(f"Loading performance data using: '{cmd}'")
    subprocess.run(cmd)
    ini_file = "/usr/lib/ckan/submodules/ckanext-restricted/test.ini"

    cmd = ['/usr/local/bin/ckan', '-c', ini_file, 'search-index', 'rebuild']
    log.info(f"Rebuild indexes: {cmd}")
    subprocess.run(cmd)


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
@pytest.mark.usefixtures(u'import_performance_data')
class TestRestrictedSearchPerformance:

    def test_performance(self):
        avg_time = self.get_avg_run_time(self._perform_search)

        log.warning(f"Avg time: {avg_time}")

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
