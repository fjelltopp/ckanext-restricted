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

## Current Status

### Passing Tests (2/24 total)
- ✅ `test_auth.py` - 2 tests passing

### Remaining Test Files to Enable
- `test_plugin.py` - next to test
- `test_allowed_user_email_templates.py`
- `test_access_request.py`
- `test_access_request_email_templates.py`
- `test_performance_package_search.py` - requires psql command

---

## Files Modified Summary

1. `.github/workflows/test.yml`
   - Removed matrix strategy for multiple CKAN versions
   - Set single target: CKAN 2.11 + Python 3.10
   - Updated test command to run one file at a time

2. `test.ini`
   - Added explicit `ckan.plugins` configuration excluding removed plugins
   - Added DataPusher required configuration

---

## Next Steps

1. Enable `test_plugin.py` in test.yml
2. Run tests and fix any issues
3. Continue one file at a time until all tests pass
4. Address `test_performance_package_search.py` psql dependency issue

---

*Migration started: 2026-01-09*
