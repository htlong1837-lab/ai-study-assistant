import statistics

from core.contracts import TaskStatus
from experiments.scenarios import SCENARIOS, base_settings, generate, load_ratio, sessions


def test_same_seed_same_data_different_seed_different_data():
    assert generate("Vừa", 3) == generate("Vừa", 3)
    assert generate("Vừa", 3) != generate("Vừa", 4)


def test_task_counts_and_all_confirmed():
    for name, sc in SCENARIOS.items():
        tasks = generate(name, 0)
        assert len(tasks) == sc.n_tasks
        assert all(t.status is TaskStatus.CONFIRMED for t in tasks)
        assert len({t.id for t in tasks}) == len(tasks)


def test_load_ratio_increases_with_scenario():
    s, sess = base_settings(), sessions()
    mean = {name: statistics.mean(load_ratio(generate(name, k), sess, s) for k in range(10))
            for name in SCENARIOS}
    assert mean["Nhẹ"] < mean["Vừa"] < 1 < mean["Quá tải"]
