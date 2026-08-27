#!/usr/bin/env bash

_scalpel_glimpse_complete() {
    local cur prev options views
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    options="--help --version --payload --filter --start --days --workhours --default-duration --max-infer-duration --snap --px-per-min --tz --display-tz --goals --no-nautical-hooks --show-completed --view --date --width --color --no-color --plain --ascii --interactive"
    views="agenda day week"

    case "$prev" in
        --view)
            mapfile -t COMPREPLY < <(compgen -W "$views" -- "$cur")
            return 0
            ;;
        --payload|--goals)
            mapfile -t COMPREPLY < <(compgen -f -- "$cur")
            return 0
            ;;
    esac

    mapfile -t COMPREPLY < <(compgen -W "$options" -- "$cur")
}

complete -F _scalpel_glimpse_complete scalpel-glimpse
