# validate_bind_skips.sh — sourced by tools/validate; exercised directly by
# tests/test_skip_record_binding.py (subprocess) so the binding loop itself is
# a tested artifact, not inline script text.
#
# bind_skips: reads RESULTS[] ("STATUS\tNAME\tNOTE" rows), writes
# BOUND_RESULTS[], and sets ANY_FAIL=1 for any environmental SKIP that has no
# OPEN docs/RECORD.md row naming the check (via tools/skip_record_binding.py,
# which requires the backticked `check_name` marker).
#
# Exemption model (evaluator r3 on PR #35 — the note-substring exemption was
# fail-open): quick-mode skips are recorded with the STRUCTURED status QSKIP,
# set ONLY at the two --quick sites in tools/validate. Exemption is keyed off
# that status, never off note text — a SKIP whose note happens to contain
# "--quick" still binds or fails. QSKIP rows are displayed as SKIP in the
# summary (their note carries the quick-mode explanation) and still make the
# run non-green without --allow-skips.

bind_skips() {
  BOUND_RESULTS=()
  local row status name note rid
  for row in "${RESULTS[@]}"; do
    IFS=$'\t' read -r status name note <<< "$row"
    case "$status" in
      SKIP)
        if rid=$("${PY:-python3}" "${REPO_ROOT:-.}/tools/skip_record_binding.py" "$name"); then
          BOUND_RESULTS+=("SKIP"$'\t'"$name"$'\t'"${note:+$note — }${rid}")
        else
          BOUND_RESULTS+=("FAIL"$'\t'"$name"$'\t'"SKIP with no OPEN docs/RECORD.md row — record it or fix the check")
          ANY_FAIL=1
        fi
        ;;
      QSKIP)
        BOUND_RESULTS+=("SKIP"$'\t'"$name"$'\t'"$note")
        ;;
      *)
        BOUND_RESULTS+=("$row")
        ;;
    esac
  done
}
