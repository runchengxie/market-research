import pandas as pd
import pytest


def _series(dates, values):
    return pd.DataFrame({"date": dates, "nav": values})


def test_recovery_separates_peak_trough_and_censored_episode():
    from market_research.recovery import analyze_recovery
    result = analyze_recovery(_series(
        ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"],
        [100, 60, 80, 100, 90, 85],
    ))
    episodes = result["episodes"]
    assert len(episodes) == 2
    assert episodes.iloc[0].peak_date == "2020-01-01"
    assert episodes.iloc[0].trough_date == "2020-01-02"
    assert episodes.iloc[0].recovery_date == "2020-01-06"
    assert episodes.iloc[0].calendar_days == 5
    assert episodes.iloc[0].trading_sessions == 3
    assert episodes.iloc[0].max_drawdown == pytest.approx(-.4)
    assert bool(episodes.iloc[1].censored)
    assert pd.isna(episodes.iloc[1].recovery_date)
    assert result["summary"]["current_underwater_calendar_days"] == 2
    assert result["summary"]["gain_needed_to_recover"] == pytest.approx(100 / 85 - 1)


def test_entry_wait_includes_unrecovered_and_equal_cost_touch():
    from market_research.recovery import analyze_recovery
    result = analyze_recovery(_series(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"], [100, 80, 80, 70]))
    entries = result["entries"]
    assert bool(entries.iloc[0].censored)
    assert entries.iloc[0].calendar_days == 3
    assert entries.iloc[1].breakeven_date == "2020-01-03"
    assert not entries.iloc[1].censored
    assert result["summary"]["longest_completed_underwater_calendar_days"] is None


def test_horizon_counts_mature_windows_not_short_history_as_wins():
    from market_research.recovery import analyze_recovery
    result = analyze_recovery(_series(["2020-01-02", "2021-01-04", "2022-01-04"], [100, 80, 120]))
    one = result["horizons"].set_index("years").loc[1]
    assert one.mature_entries == 2
    assert one.immature_entries == 1
    assert one.loss_fraction == pytest.approx(.5)
    assert one.worst_return == pytest.approx(-.2)
    assert result["horizons"].set_index("years").loc[5].mature_entries == 0
    assert pd.isna(result["horizons"].set_index("years").loc[5].loss_fraction)


@pytest.mark.parametrize("values", [[1, float("nan")], [1, float("inf")], [1, 0], [1, -1]])
def test_invalid_path_does_not_produce_recovery_metrics(values):
    from market_research.recovery import analyze_recovery
    with pytest.raises(ValueError):
        analyze_recovery(_series(["2020-01-01", "2020-01-02"], values))
