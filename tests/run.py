"""tests/run.py — 既有用例（起点全绿）。

这些用例刻意只覆盖「能跑通」的部分，不触发 cuckoofilter.py 里埋的 6 处缺陷：
指纹位宽、踢出上限、删除定位、半排序编解码、扩容确定性、负载因子口径。
跑法： python tests/run.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cuckoofilter import CuckooFilter  # noqa: E402


class _Case:
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


def _t1_init_stats():
    cf = CuckooFilter(100)
    s = cf.stats()
    assert s["num_buckets"] == 100, s
    assert s["bucket_size"] == 4, s
    assert s["fingerprint_bits"] == 8, s
    assert s["count"] == 0, s


def _t2_add_returns_true():
    cf = CuckooFilter(100)
    assert cf.add("alice") is True


def _t3_contains_after_add():
    cf = CuckooFilter(100)
    cf.add("alice")
    assert cf.contains("alice") is True


def _t4_absent_not_contained():
    cf = CuckooFilter(100)
    cf.add("alice")
    cf.add("bob")
    assert cf.contains("zzz-not-added-zzz") is False


def _t5_delete_existing():
    cf = CuckooFilter(100)
    cf.add("alice")
    assert cf.delete("alice") is True
    assert cf.contains("alice") is False


def _t6_delete_absent_noop():
    cf = CuckooFilter(100)
    cf.add("alice")
    before = cf.snapshot()
    assert cf.delete("nope") is False
    assert cf.snapshot() == before, "delete 不应改动表"


def _t7_load_factor_in_range():
    cf = CuckooFilter(100)
    cf.add("a")
    cf.add("b")
    lf = cf.load_factor()
    assert 0.0 <= lf <= 1.0, lf


def _t8_snapshot_deterministic():
    cf = CuckooFilter(50)
    cf.add("x")
    cf.add("y")
    assert isinstance(cf.snapshot(), str)
    assert cf.snapshot() == cf.snapshot()


def _t9_many_added_contained():
    cf = CuckooFilter(100)
    keys = ["k%d" % i for i in range(10)]
    for k in keys:
        cf.add(k)
    for k in keys:
        assert cf.contains(k) is True, k


def _t10_resize_keeps_contained():
    cf = CuckooFilter(64)
    keys = ["r%d" % i for i in range(8)]
    for k in keys:
        cf.add(k)
    cf.resize(128)
    for k in keys:
        assert cf.contains(k) is True, k


def _t11_stats_count_matches():
    cf = CuckooFilter(100)
    for k in ["a", "b", "c"]:
        cf.add(k)
    assert cf.stats()["count"] == 3


def _t12_delete_then_readd():
    cf = CuckooFilter(100)
    cf.add("m")
    assert cf.delete("m") is True
    assert cf.add("m") is True
    assert cf.contains("m") is True


def _t13_snapshot_format_has_buckets():
    cf = CuckooFilter(16)
    cf.add("s1")
    snap = cf.snapshot()
    assert snap.count(":") >= 16, "snapshot 应为按桶序的固定格式"


_CASES = [
    _Case("init_stats", _t1_init_stats),
    _Case("add_returns_true", _t2_add_returns_true),
    _Case("contains_after_add", _t3_contains_after_add),
    _Case("absent_not_contained", _t4_absent_not_contained),
    _Case("delete_existing", _t5_delete_existing),
    _Case("delete_absent_noop", _t6_delete_absent_noop),
    _Case("load_factor_in_range", _t7_load_factor_in_range),
    _Case("snapshot_deterministic", _t8_snapshot_deterministic),
    _Case("many_added_contained", _t9_many_added_contained),
    _Case("resize_keeps_contained", _t10_resize_keeps_contained),
    _Case("stats_count_matches", _t11_stats_count_matches),
    _Case("delete_then_readd", _t12_delete_then_readd),
    _Case("snapshot_format_has_buckets", _t13_snapshot_format_has_buckets),
]


def main():
    passed = 0
    failed = []
    for c in _CASES:
        try:
            c.fn()
            passed += 1
        except Exception as e:  # noqa: BLE001
            failed.append((c.name, repr(e)))
    total = len(_CASES)
    for c in _CASES:
        pass  # 占位，保持顺序清晰
    print("tests: %d/%d passed" % (passed, total))
    if failed:
        for name, err in failed:
            print("FAIL %s  %s" % (name, err))
        sys.exit(1)
    print("ALL GREEN")
    sys.exit(0)


if __name__ == "__main__":
    main()
