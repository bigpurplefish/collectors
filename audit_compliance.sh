#!/bin/bash

# Compliance audit script for all collector projects
# Checks against COMPLIANCE_CHECKLIST.md requirements

echo "====================================================="
echo "COLLECTOR COMPLIANCE AUDIT"
echo "Date: $(date)"
echo "====================================================="
echo ""

PROJECTS="bradley_caldwell chala coastal ethical fromm ivyclassic kong orgill purinamills talltails"

for project in $PROJECTS; do
    echo "########################################"
    echo "PROJECT: $project"
    echo "########################################"
    echo ""

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
        echo "❌ gui.py MISSING"
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
        # Check if it includes -r requirements.txt
        if grep -q "^-r requirements.txt" "$project/requirements-gui.txt" 2>/dev/null; then
            echo "   ✅ Includes -r requirements.txt"
        else
            echo "   ❌ Missing -r requirements.txt"
        fi
    else
        echo "❌ requirements-gui.txt MISSING"
    fi

    if [ -f "$project/requirements-dev.txt" ]; then
        echo "✅ requirements-dev.txt exists"
        # Check if it includes -r requirements.txt
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
    [ -f "$project/src/__init__.py" ] && echo "✅ /src/__init__.py exists" || echo "❌ /src/__init__.py MISSING"
    [ -d "$project/tests" ] && echo "✅ /tests exists" || echo "❌ /tests MISSING"
    [ -d "$project/input" ] && echo "✅ /input exists" || echo "❌ /input MISSING"
    [ -d "$project/output" ] && echo "✅ /output exists" || echo "❌ /output MISSING"
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

    # .gitkeep Files
    echo "--- .gitkeep Files ---"
    [ -f "$project/input/.gitkeep" ] && echo "✅ input/.gitkeep exists" || echo "❌ input/.gitkeep MISSING"
    [ -f "$project/output/.gitkeep" ] && echo "✅ output/.gitkeep exists" || echo "❌ output/.gitkeep MISSING"
    [ -f "$project/tests/output/.gitkeep" ] && echo "✅ tests/output/.gitkeep exists" || echo "❌ tests/output/.gitkeep MISSING"
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

    # Check README mentions all 3 requirements files
    if [ -f "$project/README.md" ]; then
        if grep -q "requirements-gui.txt" "$project/README.md" && grep -q "requirements-dev.txt" "$project/README.md"; then
            echo "   ✅ README mentions all 3 requirements files"
        else
            echo "   ⚠️  README may not mention all requirements files"
        fi
    fi

    echo ""
    echo ""
done

echo "====================================================="
echo "AUDIT COMPLETE"
echo "====================================================="
