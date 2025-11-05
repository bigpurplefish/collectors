# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### CRITICAL: Always Follow These Requirements

**Before generating ANY code**, you MUST:

1. **Check Context7** for up-to-date library documentation (use context7 MCP tool)
2. **Read the shared-docs requirements**:
   - @~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md - GUI patterns and threading
   - @~/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md - Project layout standards
   - @~/Code/shared-docs/python/GIT_WORKFLOW.md - Git commit patterns
   - @~/Code/shared-docs/python/TECHNICAL_DOCS.md - General Python standards
3. **Read collector-specific shared docs**:
   - @~/Code/Python/collectors/shared/docs/README.md - Shared utility documentation
4. **Combine external + internal standards**: Both Context7 patterns AND our requirements must be met

### Key Requirements to Remember

- **GUI Development**: MUST follow GUI_DESIGN_REQUIREMENTS.md exactly
  - Use `darkly` theme, queue-based threading, tooltips, auto-save config
  - Never update widgets from worker threads - use queues
- **Project Structure**: main.py at root, code in /src, follow standard Python layout
- **Shared Utilities**: Import from `../shared/src/` for common functions
- **Git Commits**: Include emoji and Co-Authored-By footer


## Project Overview

Tall Tails Dog Product Collector - Magento/Adobe Commerce site collector with variant-aware gallery handling.

## Development

```bash
cd /Users/moosemarketer/Code/Python/collectors/talltails
pyenv local talltails
pip install -r requirements.txt
```
