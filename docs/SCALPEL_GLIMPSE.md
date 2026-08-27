# SCALPEL Glimpse

`scalpel-glimpse` is a read-only terminal calendar for a quick look at live
Taskwarrior planning data. It shares SCALPEL's payload and timezone logic and
does not modify tasks.

## Install

Install SCALPEL normally, then run:

```bash
python3 -m pip install taskwarrior-scalpel
scalpel-glimpse
```

Taskwarrior must be available on `PATH`. For offline or reproducible output,
render a saved payload instead:

```bash
scalpel-glimpse --payload build/payload.json --plain
```

## Views and options

```bash
scalpel-glimpse --view agenda
scalpel-glimpse --view day --date today
scalpel-glimpse --view week --date 2026-08-31
scalpel-glimpse --filter 'status:pending project:work' --days 3 --plain
scalpel-glimpse --show-completed --no-nautical-hooks
```

Use `--tz` for day bucketing and `--display-tz` for displayed times. `--plain`
disables color; `--ascii` also replaces Unicode markers and rules for limited
terminals and pipes. Invalid dates, timezones, and missing executables return
exit code `2` with a short diagnostic.

## Interactive keys

Run `scalpel-glimpse --interactive` in a terminal.

- `a`, `d`, `w`: agenda, day, or week view
- `h`/`l` or arrows: previous/next day
- `j`/`k`: move selection
- `t`: return to today
- `/`: search descriptions, projects, tags, and UUIDs
- `Enter`: show task details; `Esc`: close details/help
- `?`: keyboard help; `q`: quit

The interactive mode is read-only. The terminal is restored by the curses
wrapper when the application exits or is interrupted.
