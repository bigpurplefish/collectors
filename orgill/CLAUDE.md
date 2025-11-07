# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

## Project Overview

Orgill Collector - B2B distributor site requiring authentication with multi-strategy login system.

## Architecture

**collector.py**: Main orchestration with authentication integration

**auth.py**: Authentication system
- `OrgillAuthenticator` class with multi-strategy login
- Session management and cookie persistence
- `login()` with retry logic
- Raises `StrategyLoginError` on failure
- `set_auth()` for credentials
- `attach_session()` for session pooling

**search.py**: Authenticated search
- Uses authenticated session for UPC searches
- B2B-specific search logic

**parser.py**: B2B HTML parsing
- Distributor-specific structure
- Product data, pricing, availability

## Configuration

```python
SITE_CONFIG = {
    "key": "orgill",
    "origin": "https://www.orgill.com",
    "robots": "respect",
    "search": {"upc_overrides": {}}
}
```

## Security

- Credentials NOT persisted in config
- Short-lived sessions
- Explicit `StrategyLoginError` for auth failures

## Notes

- **Authentication required**: Multi-strategy login
- **B2B site**: Different from consumer sites
- **Session management**: Persistent during collection
