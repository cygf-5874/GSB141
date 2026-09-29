"""check/check.py — GSB141 固定验收程序（勿改）。

8 个场景：6 个 finding 命中（逐节核对 REVIEW.md 是否把问题点全）
          + 2 个正确性锚点（核对 src/cuckoofilter.py 里两处最隐蔽的缺陷确凿存在）。

输出：逐场景  PASS <组>/<名>  或  FAIL <组>/<名>  期望=… 实际=…
结尾： 结果：通过 x/8
全过 exit 0，否则 exit 1。
支持 -list 与 --only <组名>；失败不早退。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_PATH = os.path.join(ROOT, "REVIEW.md")
SRC_PATH = os.path.join(ROOT, "src", "cuckoofilter.py")

LINE_RE = re.compile(r"src/cuckoofilter\.py:(\d+)(?:-(\d+))?")
SECTION_RE = re.compile(r"^##\s*(\d+)\.")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _sections(review):
    """返回 {n: text} ，n 为 1..6 的章节序号。"""
    out = {}
    cur = None
    buf = []
    for line in review.splitlines():
        m = SECTION_RE.match(line)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur = int(m.group(1))
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


# 每个 finding 场景：章节号、组/名、同义关键词、调用序列 token
FINDINGS = {
    1: {
        "group": "fingerprint",
        "name": "mask",
        "keywords": ["低", "位宽", "截断", "fingerprint_bits", "掩码", "高位",
                     "全哈希", "alt_index", "自反", "反函数", "候选桶", "指纹"],
        "calls": ["add(", "contains(", "alt_index(", "CuckooFilter("],
    },
    2: {
        "group": "kick",
        "name": "maxkicks",
        "keywords": ["max_kicks", "踢出", "无限", "超限", "上限", "失败",
                     "False", "迁移", "重定位", "次数"],
        "calls": ["add(", "max_kicks"],
    },
    3: {
        "group": "delete",
        "name": "mislocate",
        "keywords": ["删除", "delete", "备选桶", "误删", "哈希", "定位",
                     "fp", "指纹", "key"],
        "calls": ["delete("],
    },
    4: {
        "group": "semisort",
        "name": "codec",
        "keywords": ["semi", "排序", "to_bytes", "from_bytes", "还原", "可逆",
                     "编码", "stored", "槽位", "打包"],
        "calls": ["to_bytes(", "from_bytes("],
    },
    5: {
        "group": "resize",
        "name": "order",
        "keywords": ["扩容", "resize", "重哈希", "翻倍", "确定性", "set",
                     "dict", "顺序", "桶序", "槽序"],
        "calls": ["resize(", "add("],
    },
    6: {
        "group": "load",
        "name": "factor",
        "keywords": ["负载因子", "load_factor", "槽数", "假阳性", "占用",
                     "桶数", "fingerprint_bits", "上界"],
        "calls": ["load_factor("],
    },
}

MASK_TOKEN = "(1 << self.fingerprint_bits) - 1"
LOADBUG_TOKEN = "occupied_buckets / self.num_buckets"


def check_finding(n):
    cfg = FINDINGS[n]
    try:
        review = _read(REVIEW_PATH)
    except FileNotFoundError:
        return False, "REVIEW.md 存在", "文件不存在"
    secs = _sections(review)
    if n not in secs:
        return False, "第 %d 节存在" % n, "章节缺失"
    text = secs[n]
    # 关键词
    if not any(kw in text for kw in cfg["keywords"]):
        return (False, "命中同义关键词之一(%s)" % "/".join(cfg["keywords"][:4]),
                "未写清问题性质")
    # 行范围
    if not LINE_RE.search(text):
        return False, "给出 src/cuckoofilter.py:行范围", "未指到文件与行范围"
    # 调用序列
    if not any(tok in text for tok in cfg["calls"]):
        return (False, "写出可复现调用序列(%s)" % "/".join(cfg["calls"][:3]),
                "未给调用序列")
    return True, "命中关键词+行范围+调用序列", "ok"


def check_anchor_fp():
    try:
        src = _read(SRC_PATH)
    except FileNotFoundError:
        return False, "src/cuckoofilter.py 存在", "文件不存在"
    # 正确性锚点：指纹确凿没有截断到 fingerprint_bits 位（缺陷 ① 存在）
    bug_present = MASK_TOKEN not in src
    if bug_present:
        return True, "指纹未截断到 fingerprint_bits（缺陷①存在）", "ok"
    return False, "指纹未截断到 fingerprint_bits（缺陷①存在）", "已实现截断，缺陷①缺失"


def check_anchor_load():
    try:
        src = _read(SRC_PATH)
    except FileNotFoundError:
        return False, "src/cuckoofilter.py 存在", "文件不存在"
    # 正确性锚点：load_factor 确凿按「已占桶数/桶数」算（缺陷 ⑥ 存在）
    bug_present = LOADBUG_TOKEN in src
    if bug_present:
        return True, "load_factor 按已占桶数/桶数算（缺陷⑥存在）", "ok"
    return False, "load_factor 按已占桶数/桶数算（缺陷⑥存在）", "口径已修正，缺陷⑥缺失"


# 全部 8 个场景
SCENES = [
    ("fingerprint", "mask", lambda: check_finding(1)),
    ("kick", "maxkicks", lambda: check_finding(2)),
    ("delete", "mislocate", lambda: check_finding(3)),
    ("semisort", "codec", lambda: check_finding(4)),
    ("resize", "order", lambda: check_finding(5)),
    ("load", "factor", lambda: check_finding(6)),
    ("anchor", "fpbug", check_anchor_fp),
    ("anchor", "loadbug", check_anchor_load),
]


def main():
    args = sys.argv[1:]
    only = None
    do_list = False
    for a in args:
        if a == "-list":
            do_list = True
        elif a.startswith("--only="):
            only = a.split("=", 1)[1]
        elif a == "--only" and args[args.index(a) + 1:]:
            only = args[args.index(a) + 1]
    # 兼容 `--only <组名>` 分开写
    if "--only" in args:
        i = args.index("--only")
        if i + 1 < len(args):
            only = args[i + 1]

    if do_list:
        for g, n, _ in SCENES:
            print("%s/%s" % (g, n))
        sys.exit(0)

    results = []
    for g, n, fn in SCENES:
        if only is not None and g != only:
            continue
        try:
            passed, expected, actual = fn()
        except Exception as e:  # noqa: BLE001
            passed, expected, actual = False, "无异常", "异常: %r" % e
        results.append((g, n, passed, expected, actual))

    for g, n, passed, expected, actual in results:
        if passed:
            print("PASS %s/%s" % (g, n))
        else:
            print("FAIL %s/%s  期望=%s 实际=%s" % (g, n, expected, actual))

    total = len(results)
    ok = sum(1 for r in results if r[2])
    print("结果：通过 %d/%d" % (ok, total))
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
