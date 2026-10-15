#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd)}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
RALPH_DIR="$REPO_ROOT/.ralph"
cd "$REPO_ROOT"

hard_fail=0
soft_warning=0
checks_run=0
detected_project=0

log() {
  printf '[ralph-verify] %s\n' "$*"
}

run_check() {
  checks_run=$((checks_run + 1))
  log "RUN: $*"
  if "$@"; then
    log "PASS: $*"
  else
    hard_fail=1
    log "FAIL: $*"
  fi
}

soft_warn() {
  soft_warning=1
  log "SOFT_WARNING: $*"
}

script_exists() {
  python3 - "$1" "$2" <<'PY'
import json
import sys
path, script = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    raise SystemExit(1)
scripts = data.get("scripts", {})
raise SystemExit(0 if script in scripts else 1)
PY
}

has_pytest() {
  command -v pytest >/dev/null 2>&1
}

has_python_tests() {
  [ -d tests ] || [ -d test ] || [ -f pytest.ini ] || [ -f tox.ini ]
}

python_syntax_check() {
  python3 - "$@" <<'PY'
import sys
from pathlib import Path

failed = False
for raw in sys.argv[1:]:
    path = Path(raw)
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    except Exception as exc:
        print(f"{path}: {exc}")
        failed = True
if failed:
    raise SystemExit(1)
PY
}

run_custom_verifier() {
  if [ -f "$RALPH_DIR/custom-verify.sh" ]; then
    checks_run=$((checks_run + 1))
    log "RUN: .ralph/custom-verify.sh"
    set +e
    if [ -x "$RALPH_DIR/custom-verify.sh" ]; then
      custom_output="$("$RALPH_DIR/custom-verify.sh" 2>&1)"
      custom_status=$?
    else
      custom_output="$(bash "$RALPH_DIR/custom-verify.sh" 2>&1)"
      custom_status=$?
    fi
    set -e
    if [ -n "$custom_output" ]; then
      printf '%s\n' "$custom_output"
    fi
    case "$custom_output" in
      *SOFT_WARNING*) soft_warning=1 ;;
    esac
    if [ "$custom_status" -eq 0 ]; then
      log "PASS: .ralph/custom-verify.sh"
    else
      hard_fail=1
      log "FAIL: .ralph/custom-verify.sh"
    fi
  fi
}

run_node_checks() {
  if [ ! -f package.json ]; then
    return
  fi
  detected_project=1
  log "Detected Node/JS/TS project"
  if script_exists package.json test; then
    run_check npm test
  fi
  if script_exists package.json lint; then
    run_check npm run lint
  fi
  if script_exists package.json typecheck; then
    run_check npm run typecheck
  fi
  if script_exists package.json build; then
    run_check npm run build
  fi
}

run_python_checks() {
  if [ ! -f pyproject.toml ] && [ ! -f requirements.txt ] && [ ! -f setup.py ]; then
    return
  fi
  detected_project=1
  log "Detected Python project"
  run_check python3 -m compileall .
  if has_pytest && has_python_tests; then
    run_check pytest
  elif has_python_tests; then
    soft_warn "Python tests appear to exist, but pytest is not available"
  fi
}

run_rust_checks() {
  if [ ! -f Cargo.toml ]; then
    return
  fi
  detected_project=1
  log "Detected Rust project"
  if command -v cargo >/dev/null 2>&1; then
    run_check cargo check
    if [ -d tests ] || find . -path './.git' -prune -o -name '*_test.rs' -type f -print | sed -n '1p' | grep -q .; then
      run_check cargo test
    fi
  else
    soft_warn "Cargo is not available; Rust checks skipped"
  fi
}

run_go_checks() {
  if [ ! -f go.mod ]; then
    return
  fi
  detected_project=1
  log "Detected Go project"
  if command -v go >/dev/null 2>&1; then
    run_check go test ./...
  else
    soft_warn "Go is not available; Go checks skipped"
  fi
}

run_maven_checks() {
  if [ ! -f pom.xml ]; then
    return
  fi
  detected_project=1
  log "Detected Java/Maven project"
  if command -v mvn >/dev/null 2>&1; then
    run_check mvn test
  else
    soft_warn "Maven is not available; Maven checks skipped"
  fi
}

run_make_checks() {
  if [ ! -f Makefile ]; then
    return
  fi
  detected_project=1
  log "Detected Makefile"
  if grep -Eq '^test[[:space:]]*:' Makefile; then
    if command -v make >/dev/null 2>&1; then
      run_check make test
    else
      soft_warn "make is not available; Makefile test target skipped"
    fi
  else
    soft_warn "Makefile exists but no test target was detected"
  fi
}

run_godot_checks() {
  if [ ! -f project.godot ]; then
    return
  fi
  detected_project=1
  log "Detected Godot project"
  if command -v godot >/dev/null 2>&1; then
    run_check godot --headless --path . --quit
  else
    soft_warn "Godot CLI is not available; headless project check skipped"
  fi

  checks_run=$((checks_run + 1))
  log "RUN: Godot static sanity checks"
  if python3 - <<'PY'
from pathlib import Path
import re
import sys

root = Path(".")
errors = []
warnings = []

for path in root.rglob("*.gd"):
    if any(part in {".git", ".ralph"} for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for idx, line in enumerate(text.splitlines(), 1):
        leading = line[: len(line) - len(line.lstrip(" \t"))]
        if " " in leading and "\t" in leading:
            errors.append(f"{path}:{idx}: mixed tabs/spaces indentation")
        if "Variant inference" in line or "type inference warning" in line:
            warnings.append(f"{path}:{idx}: warning marker found in source comment/text")
        if "\r" in line:
            errors.append(f"{path}:{idx}: carriage return in GDScript line")

resource_re = re.compile(r'path="res://([^"]+)"')
for path in list(root.rglob("*.tscn")) + list(root.rglob("*.tres")):
    if any(part in {".git", ".ralph"} for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for match in resource_re.finditer(text):
        resource = match.group(1)
        if resource.endswith((".gd", ".cs", ".tscn", ".tres")):
            target = root / resource
            if not target.exists():
                errors.append(f"{path}: missing resource path res://{resource}")

if warnings:
    print("SOFT_WARNING: possible Godot warning references:")
    for item in warnings[:20]:
        print(item)
if errors:
    print("FAIL: Godot static checks found issues:")
    for item in errors[:50]:
        print(item)
    raise SystemExit(1)
print("PASS: Godot static sanity checks")
PY
  then
    log "PASS: Godot static sanity checks"
  else
    hard_fail=1
    log "FAIL: Godot static sanity checks"
  fi
}

run_static_sanity_checks() {
  log "Running static sanity checks"
  found=0
  while IFS= read -r script; do
    [ -n "$script" ] || continue
    found=1
    run_check bash -n "$script"
  done < <(find . -path './.git' -prune -o -path './.ralph/logs' -prune -o -name '*.sh' -type f -print)

  while IFS= read -r json_file; do
    [ -n "$json_file" ] || continue
    found=1
    run_check python3 -m json.tool "$json_file"
  done < <(find . -path './.git' -prune -o -path './.ralph/logs' -prune -o -name '*.json' -type f -print)

  python_files=()
  while IFS= read -r py_file; do
    [ -n "$py_file" ] || continue
    python_files+=("$py_file")
  done < <(find . -path './.git' -prune -o -path './.ralph/logs' -prune -o -name '*.py' -type f -print)
  if [ "${#python_files[@]}" -gt 0 ]; then
    found=1
    run_check python_syntax_check "${python_files[@]}"
  fi

  if [ "$found" -eq 0 ]; then
    soft_warn "No project-specific verifier detected and no static files found to check"
  fi
}

run_custom_verifier
run_node_checks
run_python_checks
run_rust_checks
run_go_checks
run_maven_checks
run_godot_checks
run_make_checks

if [ "$detected_project" -eq 0 ] || [ "$checks_run" -eq 0 ]; then
  run_static_sanity_checks
fi

if [ "$hard_fail" -ne 0 ]; then
  echo "FAIL"
  exit 1
fi

if [ "$soft_warning" -ne 0 ]; then
  echo "SOFT_WARNING"
  exit 0
fi

echo "PASS"
