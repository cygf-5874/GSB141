# GSB141 · 布谷鸟过滤器实现审查（cuckoofilter）

题型：**代码理解**。给你一份 Python 3 的布谷鸟过滤器（Cuckoo Filter）实现，里有若干
违反「对外契约」的缺陷；你的任务只是**审查并把问题逐条写进 `REVIEW.md`**，**不要改源码**。
固定件 `check/check.py` 会读你的 `REVIEW.md` 来判定 6 个方面有没有点全。

## 目录结构

- `src/cuckoofilter.py`：待审实现（埋有缺陷，**勿改**）
- `tests/run.py`：既有用例，起点全绿（`python tests/run.py`）
- `check/check.py`：固定验收程序（**勿改**），`python check/check.py`
- `scripts/check.sh`、`scripts/test.sh`：上述两条命令的封装
- `REVIEW.md`：待填的审查模板（六节，每节四行字段）
- `PROMPT.md`：逐字的 User Prompt
- `requirements.txt`：空文件（只用标准库）

## 对外契约（10 条）

1. `CuckooFilter(num_buckets, bucket_size=4, fingerprint_bits=8)`：表是 `num_buckets` 个桶、
   每桶 `bucket_size` 个槽；提供 `add` / `contains` / `delete` / `load_factor` / `stats` /
   `snapshot` / `to_bytes` / `from_bytes` / `resize`。
2. 指纹：`fp = h & ((1 << fingerprint_bits) - 1)`，且 `fp != 0`（为 0 时置 1）。
3. 两个候选桶：`i1 = h1(key) % num_buckets`、`i2 = alt_index(i1, fp)`，且必须满足自反性
   `alt_index(alt_index(i1, fp), fp) == i1`；`alt_index` 只依赖 `fp`。
4. **踢出有上限**：两桶都满时踢出一个指纹重定位，`max_kicks` 默认 500；超限返回 `False`
   （插入失败），不许无限迁移。
5. **删除安全**：`delete` 只移除**找到的那一处**匹配指纹；没找到时不得改动表（用 `snapshot()`
   校验）；重复删除返回 `False`。
6. **假阳性率**：未插入键的误判比例要落在 `2 * bucket_size / 2**fingerprint_bits` 附近
   （固定件用固定键集标定，带容差）。
7. **负载因子**：`load_factor()` = 已占槽数 / 总槽数；达到 `max_load_factor`（bucket_size=4
   时 0.95）时 `add` 必须返回 `False` 或触发扩容，**不许静默降精度**。
8. **扩容**：槽数翻倍重哈希；搬迁顺序必须**确定性**（桶序升序、槽序升序），重哈希后全部已插入键
   的 `contains` 仍为真。
9. **semi-sorting 桶编码**：桶内指纹按 `fp % bucket_size` 排序存储、存储值是 `fp // bucket_size`；
   `to_bytes` / `from_bytes` 往返后 `contains` 结果不变（打包与解包必须可逆）。
10. 确定性：不许用内置 `hash()`（随机盐）、不许依赖 `set`/`dict` 迭代顺序；`snapshot()` 是按桶序
    的固定格式字符串（Golden）；`stats()` 报桶数/槽数/指纹位数/条目数/踢出数。

## 怎么跑

```bash
python tests/run.py          # 既有用例，起点应全绿
python check/check.py        # 固定件，6 finding + 2 正确性锚点
python check/check.py -list  # 列出 8 个场景
python check/check.py --only anchor   # 只跑 anchor 组
```

## 验收

- `python check/check.py` 退出码 0，8 个场景全过（`fingerprint`/`kick`/`delete`/`semisort`/
  `resize`/`load` 六节 finding + `anchor` 两组正确性锚点）。
- `python tests/run.py` 仍然全绿（不要改 `src/cuckoofilter.py`，也不要改 `tests/`）。
- **不要改 `check/check.py`、不要改 `src/`、不要改 `tests/`**；只写 `REVIEW.md`。
