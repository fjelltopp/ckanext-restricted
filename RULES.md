# Development Workflow Rules

## Core Principles

### 1. Incremental Changes

- Make ONE change at a time
- Don't fix multiple issues in parallel
- Avoid creating "a big mess" by jumping between files

### 2. Documentation-Driven Development

- After each change that improves test results, document it in PROGRESS.md
- Document what was changed AND why
- Include error messages, root causes, and solutions

### 3. Commit After Each Success

- After documenting in PROGRESS.md, commit the changes
- Only move to the next issue after committing
- Keep commits focused and atomic

### 4. Testing Protocol

- **User runs all tests, not Claude**
- User will execute `./run_tests.sh`
- Claude waits for test results before proceeding
- Claude analyzes test results when shared

## Initial Setup

Before starting the iterative fix process, update the project to target CKAN 2.11 + Python 3.10:

1. **Update `.github/workflows/test.yml`** based on a working example (e.g., `test_harvest.yml`):
   - Update GitHub Actions versions (v2 → v6)
   - Remove matrix strategy for multiple Python/CKAN versions
   - Set single Python version: "3.10"
   - Set single CKAN version: 2.11
   - Update container: `ckan/ckan-dev:2.11-py3.10` with `--user root` option
   - Update services to CKAN 2.11 versions:
     - Solr: `ckan/ckan-solr:2.11-solr9`
     - Postgres: `ckan/ckan-postgres-dev:2.11`
     - Redis: `redis:3` (typically unchanged)
   - Keep extension-specific dependencies (e.g., `ckanext-emailasusername` for ckanext-auth)

2. **User runs initial tests** to establish baseline of what needs fixing

This setup step is done once at the start, then the iterative workflow begins.

## Workflow Steps

For each issue:

1. **User runs tests** and shares results (test_results.txt)
2. **Read test output** to identify the error
3. **Analyze the problem**:
   - Read relevant test file
   - Read relevant source code
   - Understand the root cause
4. **Add debug prints** (if needed) to pinpoint the exact issue:
   - Add prints to test to show expected vs actual values
   - Add prints to source code to trace execution
   - User runs tests again with debug output
5. **Make the fix** in code
6. **Remove debug prints** after fixing
7. **Update PROGRESS.md** with:
   - Problem description
   - Root cause analysis
   - Solution applied
   - Files modified
   - Result/outcome
8. **User runs tests** to verify the fix
9. **DO NOT stage or commit until tests pass**
10. **Once tests pass**, stage files with git add
11. **Commit if successful**
12. **Move to next issue**

**IMPORTANT**: Never stage changes with `git add` until the user confirms tests are passing!

### Debug Print Strategy

When adding debug prints:
- Add prints at key decision points
- Show input values, intermediate results, and output values
- Label prints clearly: `print("\n=== DEBUG: TestName ===")`
- Use f-strings for clarity: `print(f"Variable: {var}")`
- Always remove debug prints after issue is resolved

## Commit Message Guidelines

Based on user preferences:

- No references to Claude or Anthropic
- No "Generated with Claude Code" footers
- Focus on the technical change
- Keep it concise and clear

## Testing

- Tests are run by the user only
- Test command: `./run_tests.sh`
- Test results saved to: `test_results.txt`
- Never push unless user explicitly asks

## Branch Strategy

- Never commit to main/master branch
- Current working branch: `toavina/update-python`
- Create feature branches as needed

## Documentation Files

- **PROGRESS.md**: Detailed log of all changes, similar to PROGRESS_CKANEXT_VALIDATION.md
- **RULES.md**: This file - workflow and development rules
- Keep both updated as work progresses

## Files to Never Add, Commit, or Push

**CRITICAL**: The following files are for local development only and must NEVER be added to git, committed, or pushed:

- `RULES.md` - This file! Local workflow documentation that should stay local
- `run_tests.sh` - Local test runner script
- `test_results.txt` - Test output file (any test result files)
- `.actrc` - Local act configuration
- Any `PROGRESS_*.md` files that are project-specific notes

**Why**: These files contain local development workflows, temporary test outputs, and personal notes that are not relevant to other contributors or the public repository.

**If accidentally committed**: Use git history rewriting (rebase/cherry-pick) to create a clean branch without these files, as demonstrated in the branch cleanup process.

## Pattern to Follow

This project follows the same methodical approach used in ckanext-validation migration:

- Batch-by-batch fixes
- Detailed progress tracking
- One issue at a time
- Thorough documentation of root causes
- Clear before/after comparisons
