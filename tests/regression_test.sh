#!/bin/bash
# Google Suite Plugin Regression Test Suite
# Runs against a live Agent Zero container with the Google plugin installed.
#
# Usage:
#   ./regression_test.sh                    # Test against default (agent-zero-dev-latest on port 50084)
#   ./regression_test.sh <container> <port> # Test against specific container
#
# Requires: curl, python3 (for JSON parsing)

CONTAINER="${1:-agent-zero-dev-latest}"
PORT="${2:-50084}"
BASE_URL="http://localhost:${PORT}"

PASSED=0
FAILED=0
SKIPPED=0
ERRORS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

pass() {
    PASSED=$((PASSED + 1))
    echo -e "  ${GREEN}PASS${NC} $1"
}

fail() {
    FAILED=$((FAILED + 1))
    ERRORS="${ERRORS}\n  - $1: $2"
    echo -e "  ${RED}FAIL${NC} $1 — $2"
}

skip() {
    SKIPPED=$((SKIPPED + 1))
    echo -e "  ${YELLOW}SKIP${NC} $1 — $2"
}

section() {
    echo ""
    echo -e "${CYAN}━━━ $1 ━━━${NC}"
}

# Helper: acquire CSRF token + session cookie from the container
CSRF_TOKEN=""
setup_csrf() {
    if [ -z "$CSRF_TOKEN" ]; then
        CSRF_TOKEN=$(docker exec "$CONTAINER" bash -c '
            curl -s -c /tmp/test_cookies.txt \
                -H "Origin: http://localhost" \
                "http://localhost/api/csrf_token" 2>/dev/null
        ' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
    fi
}

# Helper: curl the container's internal API (with CSRF token)
api() {
    local endpoint="$1"
    local data="${2:-}"
    setup_csrf
    if [ -n "$data" ]; then
        docker exec "$CONTAINER" curl -s -X POST "http://localhost/api/plugins/google/${endpoint}" \
            -H "Content-Type: application/json" \
            -H "Origin: http://localhost" \
            -H "X-CSRF-Token: ${CSRF_TOKEN}" \
            -b /tmp/test_cookies.txt \
            -d "$data" 2>/dev/null
    else
        docker exec "$CONTAINER" curl -s "http://localhost/api/plugins/google/${endpoint}" \
            -H "Origin: http://localhost" \
            -H "X-CSRF-Token: ${CSRF_TOKEN}" \
            -b /tmp/test_cookies.txt 2>/dev/null
    fi
}

# Helper: run Python inside the container
pyexec() {
    echo "$1" | docker exec -i "$CONTAINER" bash -c 'cd /a0 && PYTHONPATH=/a0 /opt/venv-a0/bin/python3 -' 2>&1
}

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Google Suite Plugin Regression Test Suite        ║${NC}"
echo -e "${CYAN}║     Container: ${CONTAINER}${NC}"
echo -e "${CYAN}║     Port: ${PORT}${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

# ============================================================
section "T1: Container & Plugin Basics"
# ============================================================

# T1.1: Container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    pass "T1.1 Container is running"
else
    fail "T1.1 Container is running" "Container '${CONTAINER}' not found"
    echo -e "\n${RED}Cannot proceed without a running container.${NC}"
    exit 1
fi

# T1.2: Plugin directory exists
if docker exec "$CONTAINER" test -d /a0/usr/plugins/google; then
    pass "T1.2 Plugin directory exists (/a0/usr/plugins/google/)"
else
    fail "T1.2 Plugin directory exists" "/a0/usr/plugins/google/ not found"
fi

# T1.3: plugin.yaml exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/plugin.yaml; then
    pass "T1.3 plugin.yaml exists"
else
    fail "T1.3 plugin.yaml exists" "File not found"
fi

# T1.4: plugin.yaml name field = "google"
YAML_NAME=$(docker exec "$CONTAINER" cat /a0/usr/plugins/google/plugin.yaml 2>/dev/null | python3 -c "import sys,yaml; print(yaml.safe_load(sys.stdin).get('name',''))" 2>/dev/null)
if [ "$YAML_NAME" = "google" ]; then
    pass "T1.4 plugin.yaml name=google"
else
    fail "T1.4 plugin.yaml name" "Expected 'google', got '$YAML_NAME'"
fi

# T1.5: helpers directory exists
if docker exec "$CONTAINER" test -d /a0/usr/plugins/google/helpers; then
    pass "T1.5 helpers directory exists"
else
    fail "T1.5 helpers directory exists" "Directory not found"
fi

# T1.6: tools directory exists
if docker exec "$CONTAINER" test -d /a0/usr/plugins/google/tools; then
    pass "T1.6 tools directory exists"
else
    fail "T1.6 tools directory exists" "Directory not found"
fi

# ============================================================
section "T2: Required Files"
# ============================================================

# T2.1: initialize.py exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/initialize.py; then
    pass "T2.1 initialize.py exists"
else
    fail "T2.1 initialize.py exists" "File not found"
fi

# T2.2: default_config.yaml exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/default_config.yaml; then
    pass "T2.2 default_config.yaml exists"
else
    fail "T2.2 default_config.yaml exists" "File not found"
fi

# T2.3: google_auth.py exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/helpers/google_auth.py; then
    pass "T2.3 google_auth.py exists"
else
    fail "T2.3 google_auth.py exists" "File not found"
fi

# T2.4: gmail_client.py exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/helpers/gmail_client.py; then
    pass "T2.4 gmail_client.py exists"
else
    fail "T2.4 gmail_client.py exists" "File not found"
fi

# T2.5: calendar_client.py exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/helpers/calendar_client.py; then
    pass "T2.5 calendar_client.py exists"
else
    fail "T2.5 calendar_client.py exists" "File not found"
fi

# T2.6: Config API exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/api/google_config_api.py; then
    pass "T2.6 Config API (google_config_api.py) exists"
else
    fail "T2.6 Config API exists" "File not found"
fi

# ============================================================
section "T3: Python Imports"
# ============================================================

# T3.1: google_auth imports clean
RESULT=$(pyexec "from usr.plugins.google.helpers.google_auth import *; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T3.1 google_auth imports clean"
else
    fail "T3.1 google_auth imports" "$RESULT"
fi

# T3.2: gmail_client imports clean
RESULT=$(pyexec "from usr.plugins.google.helpers.gmail_client import *; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T3.2 gmail_client imports clean"
else
    fail "T3.2 gmail_client imports" "$RESULT"
fi

# T3.3: calendar_client imports clean
RESULT=$(pyexec "from usr.plugins.google.helpers.calendar_client import *; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T3.3 calendar_client imports clean"
else
    fail "T3.3 calendar_client imports" "$RESULT"
fi

# T3.4: drive_client imports clean
RESULT=$(pyexec "from usr.plugins.google.helpers.drive_client import *; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T3.4 drive_client imports clean"
else
    fail "T3.4 drive_client imports" "$RESULT"
fi

# T3.5: sanitize imports clean
RESULT=$(pyexec "from usr.plugins.google.helpers.sanitize import *; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T3.5 sanitize imports clean"
else
    fail "T3.5 sanitize imports" "$RESULT"
fi

# ============================================================
section "T4: CSRF Enforcement"
# ============================================================

# T4.1: Config API rejects no-CSRF
RESULT=$(docker exec "$CONTAINER" curl -s -X POST "http://localhost/api/plugins/google/google_config_api" \
    -H "Content-Type: application/json" \
    -d '{"action":"get"}' 2>/dev/null)
STATUS=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('error',''))
except:
    print('blocked')
" 2>/dev/null)
if [ -n "$STATUS" ]; then
    pass "T4.1 Config API rejects no-CSRF"
else
    fail "T4.1 Config API CSRF rejection" "Request was not rejected"
fi

# T4.2: Test API rejects no-CSRF
RESULT=$(docker exec "$CONTAINER" curl -s -X POST "http://localhost/api/plugins/google/google_test" \
    -H "Content-Type: application/json" \
    -d '{}' 2>/dev/null)
STATUS=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('error',''))
except:
    print('blocked')
" 2>/dev/null)
if [ -n "$STATUS" ]; then
    pass "T4.2 Test API rejects no-CSRF"
else
    fail "T4.2 Test API CSRF rejection" "Request was not rejected"
fi

# T4.3: Config API accepts CSRF
setup_csrf
RESULT=$(api "google_config_api" '{"action":"get"}')
HAS_ERROR=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print('csrf_error' if 'csrf' in str(d.get('error','')).lower() else 'ok')
except:
    print('parse_error')
" 2>/dev/null)
if [ "$HAS_ERROR" = "ok" ]; then
    pass "T4.3 Config API accepts CSRF"
else
    fail "T4.3 Config API with CSRF" "$RESULT"
fi

# T4.4: Test API accepts CSRF
RESULT=$(api "google_test" '{}')
HAS_ERROR=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print('csrf_error' if 'csrf' in str(d.get('error','')).lower() else 'ok')
except:
    print('parse_error')
" 2>/dev/null)
if [ "$HAS_ERROR" = "ok" ]; then
    pass "T4.4 Test API accepts CSRF"
else
    fail "T4.4 Test API with CSRF" "$RESULT"
fi

# ============================================================
section "T5: Config API"
# ============================================================

# T5.1: GET returns config dict
RESULT=$(api "google_config_api" '{"action":"get"}')
IS_DICT=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print('ok' if isinstance(d, dict) else 'not_dict')
except:
    print('parse_error')
" 2>/dev/null)
if [ "$IS_DICT" = "ok" ]; then
    pass "T5.1 Config API GET returns dict"
else
    fail "T5.1 Config API GET" "$RESULT"
fi

# T5.2: Has _auth_status field
HAS_AUTH=$(echo "$RESULT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('ok' if '_auth_status' in d else 'missing')
" 2>/dev/null)
if [ "$HAS_AUTH" = "ok" ]; then
    pass "T5.2 Config has _auth_status field"
else
    fail "T5.2 _auth_status field" "Not found in config response"
fi

# T5.3: Has _has_credentials field
HAS_CRED=$(echo "$RESULT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('ok' if '_has_credentials' in d else 'missing')
" 2>/dev/null)
if [ "$HAS_CRED" = "ok" ]; then
    pass "T5.3 Config has _has_credentials field"
else
    fail "T5.3 _has_credentials field" "Not found in config response"
fi

# T5.4: Has _enabled_services field
HAS_SERVICES=$(echo "$RESULT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('ok' if '_enabled_services' in d else 'missing')
" 2>/dev/null)
if [ "$HAS_SERVICES" = "ok" ]; then
    pass "T5.4 Config has _enabled_services field"
else
    fail "T5.4 _enabled_services field" "Not found in config response"
fi

# T5.5: SET action writes config
RESULT=$(api "google_config_api" '{"action":"set","defaults":{"message_limit":50}}')
SET_OK=$(echo "$RESULT" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print('ok' if d.get('ok') else 'fail')
except:
    print('parse_error')
" 2>/dev/null)
if [ "$SET_OK" = "ok" ]; then
    pass "T5.5 Config API SET writes config"
else
    fail "T5.5 Config API SET" "$RESULT"
fi

# ============================================================
section "T6: Tool Registration"
# ============================================================

# T6.1: plugin.yaml can be parsed
RESULT=$(pyexec "
import yaml
with open('/a0/usr/plugins/google/plugin.yaml') as f:
    d = yaml.safe_load(f)
print('ok' if d.get('name') == 'google' else 'fail')
")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T6.1 plugin.yaml parses correctly"
else
    fail "T6.1 plugin.yaml parse" "$RESULT"
fi

# T6.2: tools directory has 23 .py files
TOOL_COUNT=$(docker exec "$CONTAINER" bash -c 'ls /a0/usr/plugins/google/tools/*.py 2>/dev/null | grep -v __pycache__ | wc -l')
if [ "$TOOL_COUNT" -eq 23 ]; then
    pass "T6.2 tools/ has 23 .py files ($TOOL_COUNT found)"
else
    fail "T6.2 tools/ file count" "Expected 23, got $TOOL_COUNT"
fi

# T6.3: No bare print() in tools
BARE_PRINTS=$(docker exec "$CONTAINER" bash -c 'grep -rn "^\s*print(" /a0/usr/plugins/google/tools/*.py 2>/dev/null | grep -v __pycache__ | grep -v "# debug" | wc -l')
if [ "$BARE_PRINTS" -eq 0 ]; then
    pass "T6.3 No bare print() in tools/"
else
    fail "T6.3 Bare print() in tools/" "$BARE_PRINTS occurrences found"
fi

# T6.4: requires_csrf on all API handlers
RESULT=$(pyexec "
import ast, os, glob
api_dir = '/a0/usr/plugins/google/api'
files = glob.glob(api_dir + '/*.py')
all_csrf = True
for f in files:
    if '__pycache__' in f:
        continue
    src = open(f).read()
    if 'class ' in src and 'ApiHandler' in src:
        if 'requires_csrf' not in src or 'return False' in src:
            all_csrf = False
            print(f'MISSING:{os.path.basename(f)}')
if all_csrf:
    print('ALL_CSRF')
")
if echo "$RESULT" | grep -q "ALL_CSRF"; then
    pass "T6.4 All API handlers have requires_csrf"
else
    fail "T6.4 CSRF on API handlers" "$RESULT"
fi

# T6.5: All tools subclass Tool
RESULT=$(pyexec "
import os, importlib, glob
tool_files = glob.glob('/a0/usr/plugins/google/tools/*.py')
tool_files = [f for f in tool_files if '__pycache__' not in f and '__init__' not in f]
all_ok = True
for f in tool_files:
    name = os.path.splitext(os.path.basename(f))[0]
    try:
        mod = importlib.import_module(f'plugins.google.tools.{name}')
        has_tool = any(
            isinstance(getattr(mod, attr), type) and
            hasattr(getattr(mod, attr), 'execute')
            for attr in dir(mod)
            if not attr.startswith('_')
        )
        if not has_tool:
            all_ok = False
            print(f'NO_TOOL_CLASS:{name}')
    except Exception as e:
        all_ok = False
        print(f'IMPORT_ERROR:{name}:{e}')
if all_ok:
    print('ALL_TOOLS')
")
if echo "$RESULT" | grep -q "ALL_TOOLS"; then
    pass "T6.5 All tools have class subclassing Tool"
else
    fail "T6.5 Tool class check" "$RESULT"
fi

# ============================================================
section "T7: WebUI Files"
# ============================================================

# T7.1: main.html exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/webui/main.html; then
    pass "T7.1 webui/main.html exists"
else
    fail "T7.1 webui/main.html" "File not found"
fi

# T7.2: config.html exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/webui/config.html; then
    pass "T7.2 webui/config.html exists"
else
    fail "T7.2 webui/config.html" "File not found"
fi

# T7.3: main.html uses data-gg= attributes
DATA_ATTRS=$(docker exec "$CONTAINER" grep -c 'data-gg=' /a0/usr/plugins/google/webui/main.html 2>/dev/null)
if [ "$DATA_ATTRS" -ge 3 ]; then
    pass "T7.3 main.html uses data-gg= attributes ($DATA_ATTRS found)"
else
    fail "T7.3 main.html data-gg attributes" "Expected >= 3, got $DATA_ATTRS"
fi

# T7.4: config.html uses data-gg= attributes
DATA_ATTRS=$(docker exec "$CONTAINER" grep -c 'data-gg=' /a0/usr/plugins/google/webui/config.html 2>/dev/null)
if [ "$DATA_ATTRS" -ge 3 ]; then
    pass "T7.4 config.html uses data-gg= attributes ($DATA_ATTRS found)"
else
    fail "T7.4 config.html data-gg attributes" "Expected >= 3, got $DATA_ATTRS"
fi

# ============================================================
section "T8: Prompt Files"
# ============================================================

# T8.1: tool_group.md exists
if docker exec "$CONTAINER" test -f /a0/usr/plugins/google/prompts/tool_group.md; then
    pass "T8.1 tool_group.md exists"
else
    fail "T8.1 tool_group.md" "File not found"
fi

# T8.2: At least 15 agent.system.tool.*.md files
PROMPT_COUNT=$(docker exec "$CONTAINER" bash -c 'ls /a0/usr/plugins/google/prompts/agent.system.tool.*.md 2>/dev/null | wc -l')
if [ "$PROMPT_COUNT" -ge 15 ]; then
    pass "T8.2 At least 15 prompt files ($PROMPT_COUNT found)"
else
    fail "T8.2 Prompt file count" "Expected >= 15, got $PROMPT_COUNT"
fi

# T8.3: All prompt files contain JSON examples
RESULT=$(pyexec "
import glob, os
prompts = glob.glob('/a0/usr/plugins/google/prompts/agent.system.tool.*.md')
missing = []
for p in prompts:
    content = open(p).read()
    if '{' not in content or '}' not in content:
        missing.append(os.path.basename(p))
if missing:
    print('MISSING_JSON:' + ','.join(missing))
else:
    print('ALL_HAVE_JSON')
")
if echo "$RESULT" | grep -q "ALL_HAVE_JSON"; then
    pass "T8.3 All prompt files contain JSON examples"
else
    fail "T8.3 Prompt JSON examples" "$RESULT"
fi

# ============================================================
section "T9: Service Client Modules"
# ============================================================

# T9.1: drive_client.py has DriveClient class
RESULT=$(pyexec "from usr.plugins.google.helpers.drive_client import DriveClient; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T9.1 DriveClient class exists in drive_client.py"
else
    fail "T9.1 DriveClient class" "$RESULT"
fi

# T9.2: contacts_client.py has ContactsClient class
RESULT=$(pyexec "from usr.plugins.google.helpers.contacts_client import ContactsClient; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T9.2 ContactsClient class exists in contacts_client.py"
else
    fail "T9.2 ContactsClient class" "$RESULT"
fi

# T9.3: tasks_client.py has TasksClient class
RESULT=$(pyexec "from usr.plugins.google.helpers.tasks_client import TasksClient; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T9.3 TasksClient class exists in tasks_client.py"
else
    fail "T9.3 TasksClient class" "$RESULT"
fi

# T9.4: date_utils.py has parse_datetime function
RESULT=$(pyexec "from usr.plugins.google.helpers.date_utils import parse_datetime; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T9.4 parse_datetime function exists in date_utils.py"
else
    fail "T9.4 parse_datetime function" "$RESULT"
fi

# T9.5: sanitize.py has validate_email_address function
RESULT=$(pyexec "from usr.plugins.google.helpers.sanitize import validate_email_address; print('ok')")
LAST=$(echo "$RESULT" | tail -1)
if [ "$LAST" = "ok" ]; then
    pass "T9.5 validate_email_address function exists in sanitize.py"
else
    fail "T9.5 validate_email_address function" "$RESULT"
fi

# ============================================================
section "T10: Security"
# ============================================================

# T10.1: No hardcoded credentials in Python files
RESULT=$(docker exec "$CONTAINER" bash -c '
    grep -rn "AIza\|ya29\.\|GOCSPX-\|client_secret.*[A-Za-z0-9_-]\{20,\}" \
        /a0/usr/plugins/google/helpers/*.py \
        /a0/usr/plugins/google/tools/*.py \
        /a0/usr/plugins/google/api/*.py 2>/dev/null | \
    grep -v __pycache__ | grep -v "# example" | grep -v "# placeholder" | wc -l
')
if [ "$RESULT" -eq 0 ]; then
    pass "T10.1 No hardcoded credentials in Python files"
else
    fail "T10.1 Hardcoded credentials" "$RESULT matches found"
fi

# T10.2: .gitignore covers credentials.json and token.json
CRED_IGNORED=$(docker exec "$CONTAINER" bash -c 'grep -c "credentials.json\|token.json" /a0/usr/plugins/google/.gitignore 2>/dev/null')
if [ "$CRED_IGNORED" -ge 2 ]; then
    pass "T10.2 .gitignore covers credentials.json and token.json"
else
    # Also check if exists in source dir
    CRED_IGNORED_SRC=$(grep -c "credentials.json\|token.json" "$(dirname "$0")/../.gitignore" 2>/dev/null)
    if [ "$CRED_IGNORED_SRC" -ge 2 ]; then
        pass "T10.2 .gitignore covers credentials.json and token.json"
    else
        fail "T10.2 .gitignore coverage" "credentials.json/token.json not in .gitignore"
    fi
fi

# T10.3: All API handlers return True from requires_csrf
RESULT=$(pyexec "
import warnings; warnings.filterwarnings('ignore')
import importlib
apis = [
    'plugins.google.api.google_config_api',
    'plugins.google.api.google_test',
]
all_csrf = True
for api_mod in apis:
    mod = importlib.import_module(api_mod)
    for name in dir(mod):
        cls = getattr(mod, name)
        if isinstance(cls, type) and hasattr(cls, 'requires_csrf'):
            if not cls.requires_csrf():
                all_csrf = False
                print(f'FALSE_CSRF:{api_mod}.{name}')
if all_csrf:
    print('ALL_CSRF')
")
if echo "$RESULT" | grep -q "ALL_CSRF"; then
    pass "T10.3 All API handlers return True from requires_csrf"
else
    fail "T10.3 requires_csrf check" "$RESULT"
fi

# T10.4: No bare print() in helpers/ or api/
BARE_PRINTS=$(docker exec "$CONTAINER" bash -c '
    grep -rn "^\s*print(" \
        /a0/usr/plugins/google/helpers/*.py \
        /a0/usr/plugins/google/api/*.py 2>/dev/null | \
    grep -v __pycache__ | grep -v "# debug" | wc -l
')
if [ "$BARE_PRINTS" -eq 0 ]; then
    pass "T10.4 No bare print() in helpers/ or api/"
else
    fail "T10.4 Bare print() in helpers/api" "$BARE_PRINTS occurrences found"
fi

# ============================================================
# T11: Skills
# ============================================================
section "T11: Skills"

EXPECTED_SKILLS="google-communicate google-daily-briefing google-drive google-research google-schedule google-tasks google-sheets"

# T11.1: All 7 skill directories exist
SKILL_COUNT=$(docker exec "$CONTAINER" bash -c 'ls -d /a0/usr/plugins/google/skills/google-*/ 2>/dev/null | wc -l')
if [ "$SKILL_COUNT" -eq 7 ]; then
    pass "T11.1 All 7 skill directories exist"
else
    fail "T11.1 Skill directories" "Expected 7, found $SKILL_COUNT"
fi

# T11.2: Every skill has a SKILL.md file
MISSING_SKILLS=""
for skill in $EXPECTED_SKILLS; do
    if ! docker exec "$CONTAINER" test -f "/a0/usr/plugins/google/skills/$skill/SKILL.md"; then
        MISSING_SKILLS="$MISSING_SKILLS $skill"
    fi
done
if [ -z "$MISSING_SKILLS" ]; then
    pass "T11.2 Every skill has a SKILL.md file"
else
    fail "T11.2 Missing SKILL.md" "Missing:$MISSING_SKILLS"
fi

# T11.3: Every SKILL.md has valid YAML frontmatter (starts with ---)
BAD_FRONTMATTER=""
for skill in $EXPECTED_SKILLS; do
    FIRST_LINE=$(docker exec "$CONTAINER" head -1 "/a0/usr/plugins/google/skills/$skill/SKILL.md" 2>/dev/null)
    if [ "$FIRST_LINE" != "---" ]; then
        BAD_FRONTMATTER="$BAD_FRONTMATTER $skill"
    fi
done
if [ -z "$BAD_FRONTMATTER" ]; then
    pass "T11.3 All SKILL.md files have YAML frontmatter"
else
    fail "T11.3 Bad frontmatter" "Missing ---:$BAD_FRONTMATTER"
fi

# T11.4: Every SKILL.md has required fields (name, triggers, allowed_tools)
MISSING_FIELDS=""
for skill in $EXPECTED_SKILLS; do
    FILE="/a0/usr/plugins/google/skills/$skill/SKILL.md"
    for field in "name:" "triggers:" "allowed_tools:"; do
        if ! docker exec "$CONTAINER" grep -q "$field" "$FILE" 2>/dev/null; then
            MISSING_FIELDS="$MISSING_FIELDS $skill/$field"
        fi
    done
done
if [ -z "$MISSING_FIELDS" ]; then
    pass "T11.4 All SKILL.md files have required fields (name, triggers, allowed_tools)"
else
    fail "T11.4 Missing fields" "$MISSING_FIELDS"
fi

# T11.5: All allowed_tools reference real tools
BAD_TOOLS=$(docker exec "$CONTAINER" bash -c '
REAL_TOOLS=$(ls /a0/usr/plugins/google/tools/*.py 2>/dev/null | while read f; do basename "$f" .py; done)
BAD=""
for skill in google-communicate google-daily-briefing google-drive google-research google-schedule google-tasks google-sheets; do
    FILE="/a0/usr/plugins/google/skills/$skill/SKILL.md"
    ALLOWED=$(sed -n "/^allowed_tools:/,/^[a-z]/p" "$FILE" 2>/dev/null | grep "  - " | sed "s/  - //" | tr -d "\"" | tr -d "\r")
    for tool in $ALLOWED; do
        tool=$(echo "$tool" | tr -d " ")
        if ! echo "$REAL_TOOLS" | grep -q "^${tool}$"; then
            BAD="$BAD $skill->$tool"
        fi
    done
done
echo "$BAD"
')
if [ -z "$(echo "$BAD_TOOLS" | tr -d ' ')" ]; then
    pass "T11.5 All allowed_tools reference existing tool files"
else
    fail "T11.5 Invalid tool references" "$BAD_TOOLS"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  TEST RESULTS                       ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════╣${NC}"
TOTAL=$((PASSED + FAILED + SKIPPED))
echo -e "${CYAN}║${NC}  Total:   ${TOTAL}"
echo -e "${CYAN}║${NC}  ${GREEN}Passed:  ${PASSED}${NC}"
echo -e "${CYAN}║${NC}  ${RED}Failed:  ${FAILED}${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}Skipped: ${SKIPPED}${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

if [ "$FAILED" -gt 0 ]; then
    echo -e "\n${RED}Failed tests:${NC}${ERRORS}"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}${FAILED} test(s) failed.${NC}"
    exit 1
fi
