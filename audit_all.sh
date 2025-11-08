#!/bin/bash

# Extended audit for cambridge and techobloc

PROJECTS="cambridge/pdf_parser cambridge/pdf_editor techobloc"

for project in $PROJECTS; do
    echo "########################################"
    echo "PROJECT: $project"
    echo "########################################"
    echo ""

    if [ ! -d "$project" ]; then
        echo "❌ Directory does not exist"
        continue
    fi

    # Entry Points
    echo "--- Entry Points ---"
    if [ -f "$project/main.py" ]; then
        echo "✅ main.py exists"
    else
        echo "❌ main.py MISSING"
    fi

    if [ -f "$project/gui.py" ]; then
        echo "✅ gui.py exists"
    else
        echo "⚠️  gui.py missing (may be CLI-only)"
    fi
    echo ""

    # Requirements Files
    echo "--- Requirements Files ---"
    if [ -f "$project/requirements.txt" ]; then
        echo "✅ requirements.txt exists"
    else
        echo "❌ requirements.txt MISSING"
    fi

    if [ -f "$project/requirements-gui.txt" ]; then
        echo "✅ requirements-gui.txt exists"
        if grep -q "^-r requirements.txt" "$project/requirements-gui.txt" 2>/dev/null; then
            echo "   ✅ Includes -r requirements.txt"
        else
            echo "   ❌ Missing -r requirements.txt"
        fi
    else
        echo "⚠️  requirements-gui.txt missing (may not need GUI)"
    fi

    if [ -f "$project/requirements-dev.txt" ]; then
        echo "✅ requirements-dev.txt exists"
        if grep -q "^-r requirements.txt" "$project/requirements-dev.txt" 2>/dev/null; then
            echo "   ✅ Includes -r requirements.txt"
        else
            echo "   ❌ Missing -r requirements.txt"
        fi
    else
        echo "❌ requirements-dev.txt MISSING"
    fi
    echo ""

    # Directory Structure
    echo "--- Directory Structure ---"
    [ -d "$project/src" ] && echo "✅ /src exists" || echo "❌ /src MISSING"
    [ -f "$project/src/__init__.py" ] && echo "✅ /src/__init__.py exists" || echo "⚠️  /src/__init__.py missing"
    [ -d "$project/tests" ] && echo "✅ /tests exists" || echo "❌ /tests MISSING"
    [ -d "$project/input" ] && echo "✅ /input exists" || echo "⚠️  /input missing"
    [ -d "$project/output" ] && echo "✅ /output exists" || echo "⚠️  /output missing"
    echo ""

    # Tests Directory Files
    echo "--- Tests Directory Files ---"
    if [ -d "$project/tests" ]; then
        [ -f "$project/tests/__init__.py" ] && echo "✅ tests/__init__.py exists" || echo "❌ tests/__init__.py MISSING"
        [ -f "$project/tests/README.md" ] && echo "✅ tests/README.md exists" || echo "❌ tests/README.md MISSING"
        [ -f "$project/tests/.gitignore" ] && echo "✅ tests/.gitignore exists" || echo "❌ tests/.gitignore MISSING"
        [ -d "$project/tests/output" ] && echo "✅ tests/output/ exists" || echo "❌ tests/output/ MISSING"
    else
        echo "⚠️  Skipping (tests/ doesn't exist)"
    fi
    echo ""

    # Configuration Files
    echo "--- Configuration Files ---"
    [ -f "$project/.gitignore" ] && echo "✅ .gitignore exists" || echo "❌ .gitignore MISSING"
    [ -f "$project/.python-version" ] && echo "✅ .python-version exists" || echo "❌ .python-version MISSING"
    echo ""

    # Documentation
    echo "--- Documentation ---"
    [ -f "$project/README.md" ] && echo "✅ README.md exists" || echo "❌ README.md MISSING"
    [ -f "$project/CLAUDE.md" ] && echo "✅ CLAUDE.md exists" || echo "❌ CLAUDE.md MISSING"
    echo ""
    echo ""
done

echo "====================================================="
echo "AUDIT COMPLETE"
echo "====================================================="
