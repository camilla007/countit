from countit.collector import MAX_ACTIVE_GAP_SECONDS, active_delta


def test_active_delta_excludes_idle_gaps():
    assert active_delta(None, 10) == 0
    assert active_delta(10, 11.5) == 1.5
    assert active_delta(10, 30) == MAX_ACTIVE_GAP_SECONDS
    assert active_delta(10, 9) == 0
