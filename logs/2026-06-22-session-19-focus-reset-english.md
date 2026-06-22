# Session 19: Phase 12 — Reset to English on Focus Change

**Date:** 2026-06-22
**Phase:** 12
**Status:** Complete — confirmed live by the user

---

## Navigation

**Project Docs:** [README](../README.md) | [SPEC](../SPEC.md) | [DESIGN](../DESIGN.md) | [IMPLEMENTATION-GUIDE](../IMPLEMENTATION-GUIDE.md) | [HANDOFF](../HANDOFF.md)

---

## Goal

When the `gcin-everywhere` source is active, make each newly-focused text field start in
**English** rather than carrying a Chinese method across windows/fields. Requested as
"reset to English when the user switches to a different window," chosen to ship **always
on** (no flag).

## What was the question

> Is it possible to detect that the user has switched to a different window and reset to
> English IM for the unified switcher?

Yes — IBus delivers `focus_out`/`focus_in` to the engine on every focus change, and a window
switch is one of those. The engine already overrides both. The important caveat surfaced up
front: **IBus exposes focus, not window identity.** The standard `focus_in` signal carries no
window/app, and even IBus 1.5.27+'s `focus_in_id(object_path, client)` identifies the
toolkit/app, not the individual window. So "reset on focus" necessarily fires on *any* focus
gain — a different window, a different field, or re-entering the same field. That's the
classic per-context IME behavior; the user chose it knowingly ("always on").

## Change

Single branch added to `gcin_engine_focus_in()` in `ibus-engine/gcin_engine.c`. It already
re-registered the panel properties IBus clears on focus change; now, for `allow_switch`
engines, it also resets to English:

```c
static void gcin_engine_focus_in(IBusEngine *e) {
    GcinEngine *ge = (GcinEngine *)e;
    if (ge->allow_switch) {
        ge->chinese_mode = FALSE;          /* every newly-focused field starts in English */
        gcin_core_reset();                 /* discard any pending composition */
        ibus_engine_hide_preedit_text(e);
        ibus_engine_hide_lookup_table(e);
        if (ge->props) {
            ibus_engine_register_properties(e, ge->props);
            update_property(ge);           /* mirrors 英 to the panel + state file */
        }
    }
}
```

- `e->mode` is preserved → `Ctrl+Space` / `Ctrl+Alt+<digit>` resumes the last method.
- `update_property()` already publishes 英 to the IBus property **and** the GNOME-extension
  state file, so the panel indicator updates for free.
- Gated on `allow_switch` → the six single-method engines keep their prior focus behavior.
- No gcin-core changes.

## Build / install / verify

- `make engine` — compiles clean.
- `make install` — engine binary reinstalled (the sudo-only component-XML step failed on a
  bad password, but that file is unchanged, so it didn't matter).
- **Recurring stale-engine gotcha (same as Session 18):** after the service restart, two
  `ibus-engine-gcin` processes existed — one daemon-spawned copy started *before* the install
  (exe shown as `(deleted)`, parent `ibus-daemon`) running the **old code**, and the new
  systemd one. Fix: `kill` the stale PID, `systemctl --user restart ibus-engine-gcin.service`,
  `ibus restart`, then confirm no surviving process has a `(deleted)` exe.
- **User confirmed live:** typing Chinese in one field then switching window/field comes up in
  English (indicator shows 英); `Ctrl+Space` resumes the method.

## Files changed

| File | Change |
|------|--------|
| `ibus-engine/gcin_engine.c` | `gcin_engine_focus_in()` resets `chinese_mode` for the unified engine |
| `README.md` (source) | "Starts in English on every focus" note under gcin Everywhere usage |
| `SPEC.md` | FR11 + success criterion 8 |
| `DESIGN.md` | Decision 10 |
| `IMPLEMENTATION-GUIDE.md` | Phase 12 section + ToC entry |
| `HANDOFF.md` | Status, checklist, key decision, next actions, session log |

## Next

Phase 3 — Windows TSF port (unchanged; `libgcin-core.a` links as-is, only the platform
integration layer changes).
