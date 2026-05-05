# Testing Guide: gcin-everywhere

**Scope:** Unit tests for `libgcin-core.a` feedkey API, plus manual IBus registration and end-to-end input tests.

**Current test count:** 6 automated unit tests (SKIP until data tables are compiled) + 2 manual test procedures.

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md)

**This Document:**
- [Quick Start](#quick-start)
- [Test Inventory](#test-inventory)
- [Running Tests](#running-tests)
- [Building Data Tables](#building-data-tables)
- [Expected Output](#expected-output)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
cd sources/gcin-everywhere/gcin-core
make test
```

Without compiled data tables: all 6 tests **SKIP** (exit 0) with build instructions printed.

With tables compiled (see [Building Data Tables](#building-data-tables)):

```
gcin-core feedkey tests
Table dir: /tmp/gcin-tables

Cangjie:
  PASS  cangjie: k+space commits 大
  PASS  cangjie: ko+space commits something
  PASS  cangjie: escape after partial input does not commit
  PASS  cangjie: backspace then commit still outputs

Zhuyin:
  PASS  zhuyin: ju4 + 1 commits a character
  PASS  zhuyin: escape after partial input does not commit

6 passed, 0 failed, 0 skipped
```

---

## Test Inventory

### Unit Tests (`gcin-core/test_feedkey.c`)

| # | Test | What It Validates | Pass Criteria |
|---|------|-------------------|---------------|
| 1 | cangjie k+space | Cangjie single-component input (大 = k) | Commits `大` |
| 2 | cangjie ko+space | Cangjie two-component input (大人 = ko) | Commits something non-empty |
| 3 | cangjie escape | Escape clears state without committing | Nothing committed |
| 4 | cangjie backspace+commit | Backspace erases last component; commit still works | Something committed |
| 5 | zhuyin ju4+1 | Zhuyin ㄓㄨˋ triggers candidates; 1 selects first | Something committed |
| 6 | zhuyin escape | Escape clears state without committing | Nothing committed |

### Manual Tests

| # | Test | What It Validates | Pass Criteria |
|---|------|-------------------|---------------|
| M1 | IBus registration | `ibus list-engine \| grep gcin` | Both gcin-cangjie and gcin-zhuyin listed |
| M2 | End-to-end in gedit | Type Cangjie/Zhuyin with gcin engine selected | Characters appear in text editor |

---

## Running Tests

### Unit Tests

```bash
cd sources/gcin-everywhere/gcin-core
make test
# or with custom table dir:
GCIN_TABLE_DIR=/tmp/gcin-tables make test
```

### Manual: IBus registration (Phase 2)

```bash
# Install component XML (requires sudo)
sudo cp sources/gcin-everywhere/ibus-engine/component/gcin.xml /usr/share/ibus/component/

# Run engine in foreground
cd sources/gcin-everywhere/ibus-engine
./ibus-engine-gcin &

# Check registration
ibus list-engine | grep gcin
```

### Manual: End-to-end input (Phase 3+)

1. GNOME Settings → Keyboard → Input Sources → `+` → Chinese (Traditional) → gcin Cangjie
2. Open gedit
3. Switch input to gcin-cangjie (`Super+Space` or `Ctrl+Space`)
4. Type `ko` → candidate list shows 大人 and others → `Space` commits first candidate

---

## Building Data Tables

Data tables must be compiled from gcin source before unit tests can run.

```bash
# Build gcin once to get the table compiler tools
cd sources/gcin-everywhere/gcin
./configure && make

# Create table output directory
mkdir -p /tmp/gcin-tables

# Compile Cangjie table
./cintotab data/cj.cin /tmp/gcin-tables/cj.gtab

# Compile Zhuyin table (Standard/Daqian layout)
./phoconv data/pho.tab2.src /tmp/gcin-tables/pho.tab2

# Copy word-frequency database
cp tsin /tmp/gcin-tables/

# Run tests
cd ../gcin-core
GCIN_TABLE_DIR=/tmp/gcin-tables make test
```

For system-wide install (needed for IBus engine):

```bash
sudo mkdir -p /usr/share/gcin
sudo cp /tmp/gcin-tables/* /usr/share/gcin/
# Then make test (uses /usr/share/gcin by default)
```

---

## Expected Output

### Unit tests — tables not compiled

```
gcin-core feedkey tests
Table dir: /usr/share/gcin

SKIP: data tables not found at '/usr/share/gcin'
  missing: pho.tab2 cj.gtab
Build tables and retry:
  ...
```

Exit code: 0 (skip is not a failure).

### Unit tests — tables present

```
gcin-core feedkey tests
Table dir: /tmp/gcin-tables

Cangjie:
  PASS  cangjie: k+space commits 大
  PASS  cangjie: ko+space commits something
  PASS  cangjie: escape after partial input does not commit
  PASS  cangjie: backspace then commit still outputs

Zhuyin:
  PASS  zhuyin: ju4 + 1 commits a character
  PASS  zhuyin: escape after partial input does not commit

6 passed, 0 failed, 0 skipped
```

Exit code: 0.

### Known: test 2 (cangjie ko) asserts non-empty, not exact

The ko code may commit 大人 or another character sharing that Cangjie code — depends on table version and tsin frequency ordering. Test 1 (k alone → 大) is the exact-match assertion.

---

## Troubleshooting

### `make test` exits with error 255 / `p_err: exit(1)` in log

**Symptom:** Test crashes with `err /usr/share/gcin/pho.tab2` before SKIP message.  
**Cause:** `gcin_core_init()` was called despite missing tables (bug in your local version).  
**Fix:** Ensure `test_feedkey.c` pre-checks files with `stat()` before calling `init`. Current version does this.

### `ibus list-engine | grep gcin` shows nothing

**Symptom:** Engine binary runs but ibus doesn't list it.  
**Cause:** Component XML not installed, or ibus-daemon not restarted.  
**Fix:**
```bash
sudo cp component/gcin.xml /usr/share/ibus/component/
ibus restart
./ibus-engine-gcin &
ibus list-engine | grep gcin
```

### `gcin_core_init` returns but Cangjie test fails with "nothing committed"

**Symptom:** Tests run but commits are empty.  
**Cause:** Table path mismatch — gcin loaded tables from wrong dir, or engine mode not set to Cangjie.  
**Fix:** Check that `GCIN_TABLE_DIR` points to the directory containing `cj.gtab`. Print `TableDir` in stubs if debugging.

---

**Last Updated:** 2026-05-05 (Session 4 — initial test suite)
