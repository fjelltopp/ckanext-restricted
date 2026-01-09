# CKAN 2.11 Migration Progress - ckanext-restricted

## Migration Overview

Migrating ckanext-restricted from CKAN 2.9/2.10 to CKAN 2.11 + Python 3.10.

**Target:**
- CKAN 2.11
- Python 3.10
- Single version testing (no matrix)

---

## Changes Log

### 2026-01-09: Initial Setup - GitHub Actions & Test Configuration

#### Issue 1: GitHub Actions Matrix Strategy
**Problem:** test.yml used matrix strategy for multiple CKAN versions (2.9, 2.10, 2.11)
**Root Cause:** Need to target only CKAN 2.11 per RULES.md requirements
**Solution:** 
- Removed matrix strategy
- Set single Python version: "3.10"
- Set single CKAN version: 2.11
- Updated container: `ckan/ckan-dev:2.11-py3.10`
- Updated services:
  - Solr: `ckan/ckan-solr:2.11-solr9`
  - Postgres: `ckan/ckan-postgres-dev:2.11`
  - Redis: `redis:3`

**Files Modified:**
- `.github/workflows/test.yml`

**Result:** ✅ GitHub Actions configuration updated

---

#### Issue 2: recline_view Plugin Not Found
**Error:**
```
ckan.plugins.base.PluginNotFoundException: Interface recline_view does not exist
```

**Root Cause:** The `recline_view` plugin was removed in CKAN 2.11 (documented in ckan2.11-specific.md line 107)

**Solution:** Added plugin override in test.ini to exclude removed plugins

**Files Modified:**
- `test.ini` - Added explicit `ckan.plugins` configuration

**Result:** ✅ Fixed initial plugin error

---

#### Issue 3: recline_grid_view Plugin Not Found
**Error:**
```
ckan.plugins.base.PluginNotFoundException: Interface recline_grid_view does not exist
```

**Root Cause:** The `recline_grid_view` plugin was also removed in CKAN 2.11

**Solution:** Removed `recline_grid_view` from plugins list in test.ini

**Files Modified:**
- `test.ini` - Updated `ckan.plugins` to exclude both recline plugins

**Result:** ✅ Fixed second plugin error

---

#### Issue 4: DataPusher Configuration Required
**Error:**
```
Exception: Config option `ckan.datapusher.api_token` must be set to use the DataPusher.
```

**Root Cause:** CKAN 2.11 requires explicit DataPusher configuration when the plugin is enabled

**Solution:** Added required DataPusher configuration to test.ini:
- `ckan.datapusher.api_token = test-token`
- `ckan.datapusher.url = http://datapusher:8800`

**Files Modified:**
- `test.ini` - Added DataPusher configuration

**Result:** ✅ Setup now completes successfully

---

#### Issue 5: Test Configuration for One-by-One Testing
**Problem:** Need to test one file at a time per RULES.md workflow

**Solution:** Modified test.yml to run one test file at a time with others commented out:
```bash
pytest --ckan-ini=test.ini --cov=ckanext.restricted --disable-warnings ckanext/restricted/tests/test_auth.py
# Other test files commented for sequential testing
```

**Files Modified:**
- `.github/workflows/test.yml`

**Result:** ✅ test_auth.py (2 tests) passing

---

#### Issue 6: recline_view in Test Files
**Error:**
```
ckan.plugins.base.PluginNotFoundException: Interface recline_view does not exist
```

**Root Cause:** Test files `test_access_request.py` and `test_access_request_email_templates.py` had `@pytest.mark.ckan_config` decorators explicitly loading `recline_view`

**Solution:** Removed `recline_view` from the ckan_config decorators in both test files

**Files Modified:**
- `ckanext/restricted/tests/test_access_request.py`
- `ckanext/restricted/tests/test_access_request_email_templates.py`

**Result:** ✅ Fixed test-level plugin configuration

---

#### Issue 7: site_read Authorization Function Not Found (UNRESOLVED)
**Error:**
```
ValueError: Authorization function not found: site_read
```

**Root Cause:** Tests that use the `app` fixture (for HTTP requests) fail during app creation with "site_read authorization function not found". This is a core CKAN authorization function that should always be available, but something in the test setup is preventing it from being registered properly.

**Investigation:**
- `site_read` is a core CKAN auth function, not from a plugin
- Error occurs when creating Flask test app with specific plugin configurations
- Tried various plugin combinations (with/without datastore, datapusher)
- Tried commenting out `@pytest.mark.ckan_config` to use defaults
- Issue persists regardless of configuration

**Affected Tests (5 tests):**
- `test_access_request.py` - 3 tests
- `test_access_request_email_templates.py` - 2 tests

**Workaround:** Skipped these tests for now to continue with migration

**Files Modified:**
- `.github/workflows/test.yml` - Commented out failing test files

**Result:** ⚠️ UNRESOLVED - Needs further investigation

---

#### Issue 8: psql Command Not Found
**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'psql'
```

**Root Cause:** Performance tests (`test_performance_package_search.py`) use `subprocess.run(['psql', ...])` to load test data, but `psql` is not installed in the CKAN container

**Affected Tests (2 tests):**
- `test_performance_package_search.py` - 2 tests

**Workaround:** Skipped this test file for now

**Files Modified:**
- `.github/workflows/test.yml` - Left commented out

**Result:** ⚠️ UNRESOLVED - Needs psql installation or alternative data loading approach

---

## Current Status

### Passing Tests (17/24 total)
- ✅ `test_auth.py` - 2 tests passing
- ✅ `test_plugin.py` - 14 tests passing
- ✅ `test_allowed_user_email_templates.py` - 1 test passing

### Failing/Skipped Tests (7/24 total)
- ⚠️ `test_access_request.py` - 3 tests (site_read auth error)
- ⚠️ `test_access_request_email_templates.py` - 2 tests (site_read auth error)
- ⚠️ `test_performance_package_search.py` - 2 tests (psql command missing)

### Known Issues Requiring Resolution
1. **site_read Authorization Function Error** - 5 tests fail with "Authorization function not found: site_read"
2. **psql Command Missing** - 2 performance tests need psql to load test data

---

## Files Modified Summary

1. `.github/workflows/test.yml`
   - Removed matrix strategy for multiple CKAN versions
   - Set single target: CKAN 2.11 + Python 3.10
   - Updated test command to run one file at a time
   - Commented out failing test files (site_read and psql issues)

2. `test.ini`
   - Added explicit `ckan.plugins` configuration excluding removed plugins
   - Added DataPusher required configuration

3. `ckanext/restricted/tests/test_access_request.py`
   - Removed `recline_view` from ckan_config decorator
   - Added debug prints for troubleshooting

4. `ckanext/restricted/tests/test_access_request_email_templates.py`
   - Removed `recline_view` from ckan_config decorator

5. `ckanext/restricted/tests/conftest.py`
   - Added debug fixture for app creation troubleshooting

---

## Next Steps

1. **Investigate site_read authorization error** - 5 tests affected
   - Review how Flask test app creates authorization functions
   - Check if plugin loading order matters
   - Consider if tests need different fixtures or setup

2. **Fix psql dependency for performance tests** - 2 tests affected  
   - Either install psql in CI environment
   - Or refactor tests to use alternative data loading method

3. Continue migration once blocking issues resolved

---

*Migration started: 2026-01-09*
