import random
from datetime import datetime, time, timedelta

import pytest

from core.contracts import Priority
from modules.scheduler import ALGORITHMS, schedule
from modules.scheduler.metrics import daily_hours, evaluate, validate
from modules.scheduler.model import ScheduleSettings

from .conftest import MONDAY, task


@pytest.mark.parametrize("algo", ALGORITHMS)
def test_easy_case_fully_scheduled_and_valid(algo, easy_tasks, sessions, settings):
    r = schedule(easy_tasks, sessions, settings, algo)
    assert r.algorithm == algo
    assert validate(r.blocks, easy_tasks, sessions, settings) == []
    assert r.missing_hours == {}
    hours = {}
    for b in r.blocks:
        hours[b.task_id] = hours.get(b.task_id, 0) + b.hours
    assert hours == {"a": 3, "b": 4, "c": 2}


@pytest.mark.parametrize("algo", ALGORITHMS)
def test_proposed_tasks_never_scheduled(algo, easy_tasks, sessions, settings):
    r = schedule(easy_tasks, sessions, settings, algo)
    assert "p" not in {b.task_id for b in r.blocks}


@pytest.mark.parametrize("algo", ALGORITHMS)
def test_overload_keeps_high_priority(algo, overload_tasks, sessions, settings):
    r = schedule(overload_tasks, sessions, settings, algo)
    assert validate(r.blocks, overload_tasks, sessions, settings) == []
    assert "high" not in r.missing_hours
    assert r.missing_hours["low"] == pytest.approx(2.0)


@pytest.mark.parametrize("algo", ALGORITHMS)
def test_no_confirmed_tasks(algo, sessions, settings):
    r = schedule([], sessions, settings, algo)
    assert r.blocks == [] and r.status == "EMPTY"


@pytest.mark.parametrize("algo", ALGORITHMS)
def test_deadline_before_start_is_missing(algo, sessions, settings):
    tasks = [task("old", datetime(2026, 11, 1), 2)]
    r = schedule(tasks, sessions, settings, algo)
    assert r.blocks == [] and r.missing_hours == {"old": 2.0}


def test_cpsat_beats_edf_when_early_low_priority_blocks_high(sessions, settings):
    """EDF làm việc hạn sớm (ưu tiên thấp) trước, làm thiếu việc ưu tiên cao (SC-004)."""
    tasks = [
        task("low", datetime(2026, 11, 9, 23, 59), 3, Priority.LOW),
        task("high", datetime(2026, 11, 10, 23, 59), 6, Priority.HIGH),
    ]
    edf, cp = (schedule(tasks, sessions, settings, a) for a in ("EDF", "CP-SAT"))
    assert edf.missing_hours == {"high": 3.0}
    assert cp.missing_hours == {"low": 3.0}
    m_edf, m_cp = (evaluate(r, tasks, sessions, settings) for r in (edf, cp))
    assert m_cp["Giờ thiếu (trọng số)"] < m_edf["Giờ thiếu (trọng số)"]


def test_cpsat_balances_load_better_than_edf(easy_tasks, sessions, settings):
    edf, cp = (schedule(easy_tasks, sessions, settings, a) for a in ("EDF", "CP-SAT"))
    assert max(daily_hours(cp.blocks).values()) <= max(daily_hours(edf.blocks).values())
    m_edf, m_cp = (evaluate(r, easy_tasks, sessions, settings) for r in (edf, cp))
    assert m_cp["Độ lệch tải"] <= m_edf["Độ lệch tải"]


def test_cpsat_four_weeks_fifteen_tasks_is_fast_and_valid(sessions):
    """SC-003: 4 tuần × 15 nhiệm vụ trong giới hạn thời gian."""
    rng = random.Random(7)
    s = ScheduleSettings(start=MONDAY, days=28, day_start=time(7), day_end=time(22),
                         max_hours_per_day=4, time_limit_s=10)
    tasks = [task(f"t{i}", datetime.combine(MONDAY, time(23, 59)) + timedelta(days=rng.randint(2, 27)),
                  rng.choice([1, 2, 3, 4, 6]), rng.choice(list(Priority))) for i in range(15)]
    r = schedule(tasks, sessions, s, "CP-SAT")
    assert r.runtime_s < 12
    assert r.status in ("OPTIMAL", "FEASIBLE")
    assert validate(r.blocks, tasks, sessions, s) == []


def test_cpsat_respects_min_block_length(easy_tasks, sessions, settings):
    from modules.scheduler.metrics import short_blocks
    r = schedule(easy_tasks, sessions, settings, "CP-SAT")
    assert short_blocks(r.blocks, easy_tasks, settings) == 0
    assert all(b.hours >= 1 for b in r.blocks)


def test_short_task_may_use_short_block(sessions, settings):
    tasks = [task("tiny", datetime(2026, 11, 12, 23, 59), 0.5)]
    r = schedule(tasks, sessions, settings, "CP-SAT")
    assert r.missing_hours == {} and r.blocks[0].hours == 0.5
