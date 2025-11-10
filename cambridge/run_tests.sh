#!/bin/bash
# Test Runner for Cambridge Collector
#
# Usage:
#   ./run_tests.sh          # Run quick tests only
#   ./run_tests.sh --all    # Run all tests including slow ones

set -e  # Exit on error

echo "================================================================================"
echo "Cambridge Product Collector - Test Suite"
echo "================================================================================"
echo ""

# Verify pyenv virtualenv is active
if [ "$PYENV_VERSION" != "cambridge" ] && [ "$(cat .python-version 2>/dev/null)" == "cambridge" ]; then
    echo "Activating cambridge pyenv virtualenv..."
    eval "$(pyenv init -)"
    pyenv activate cambridge 2>/dev/null || true
    echo ""
fi

# Test 1: Parser Tests (fast)
echo "Running Parser Tests (fast)..."
echo "--------------------------------------------------------------------------------"
python3 tests/test_parsers.py
PARSER_RESULT=$?
echo ""

# Test 2: Portal Search Tests (fast)
echo "Running Portal Search Tests (fast)..."
echo "--------------------------------------------------------------------------------"
python3 tests/test_portal_search.py
PORTAL_SEARCH_RESULT=$?
echo ""

# Test 3: Index Builder (slow, optional)
if [ "$1" == "--all" ]; then
    echo "Running Index Builder Tests (slow)..."
    echo "--------------------------------------------------------------------------------"
    python3 tests/test_index_builder.py
    INDEX_RESULT=$?
    echo ""
else
    echo "Skipping Index Builder Tests (use --all to run)"
    INDEX_RESULT=0
    echo ""
fi

# Test 4: Portal Index Builder (slow, optional)
if [ "$1" == "--all" ]; then
    echo "Running Portal Index Builder Tests (slow)..."
    echo "--------------------------------------------------------------------------------"
    python3 tests/test_portal_index_builder.py
    PORTAL_INDEX_RESULT=$?
    echo ""
else
    echo "Skipping Portal Index Builder Tests (use --all to run)"
    PORTAL_INDEX_RESULT=0
    echo ""
fi

# Test 5: Workflow Test (moderate, optional)
if [ "$1" == "--all" ]; then
    echo "Running End-to-End Workflow Test (moderate)..."
    echo "--------------------------------------------------------------------------------"
    python3 tests/test_workflow.py
    WORKFLOW_RESULT=$?
    echo ""
else
    echo "Skipping Workflow Test (use --all to run)"
    WORKFLOW_RESULT=0
    echo ""
fi

# Summary
echo "================================================================================"
echo "TEST SUMMARY"
echo "================================================================================"

if [ $PARSER_RESULT -eq 0 ]; then
    echo "✓ Parser Tests: PASSED"
else
    echo "✗ Parser Tests: FAILED"
fi

if [ $PORTAL_SEARCH_RESULT -eq 0 ]; then
    echo "✓ Portal Search Tests: PASSED"
else
    echo "✗ Portal Search Tests: FAILED"
fi

if [ "$1" == "--all" ]; then
    if [ $INDEX_RESULT -eq 0 ]; then
        echo "✓ Index Builder Tests: PASSED"
    else
        echo "✗ Index Builder Tests: FAILED"
    fi

    if [ $PORTAL_INDEX_RESULT -eq 0 ]; then
        echo "✓ Portal Index Builder Tests: PASSED"
    else
        echo "✗ Portal Index Builder Tests: FAILED"
    fi

    if [ $WORKFLOW_RESULT -eq 0 ]; then
        echo "✓ Workflow Test: PASSED"
    else
        echo "✗ Workflow Test: FAILED"
    fi
else
    echo "⊘ Index Builder Tests: SKIPPED (use --all)"
    echo "⊘ Portal Index Builder Tests: SKIPPED (use --all)"
    echo "⊘ Workflow Test: SKIPPED (use --all)"
fi

echo "================================================================================"

# Exit with failure if any test failed
if [ $PARSER_RESULT -ne 0 ] || [ $PORTAL_SEARCH_RESULT -ne 0 ] || [ $INDEX_RESULT -ne 0 ] || [ $PORTAL_INDEX_RESULT -ne 0 ] || [ $WORKFLOW_RESULT -ne 0 ]; then
    exit 1
fi

exit 0
