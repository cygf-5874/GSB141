cuckoofilter 是 Python 3 的布谷鸟过滤器实现（只用标准库，requirements.txt 留空），下周过外部评审，评审前先对一遍契约。用例 python tests/run.py、固定件 python check/check.py。README 的 10 条对外契约包括：指纹取哈希低位且非零；两候选桶互为反函数且只依赖指纹；踢出有上限、超限返 False；删除只移除找到处、没找到不改表；未插入键误判率近理论值；负载因子=已占槽/总槽；扩容按桶序槽序确定性重哈希；半排序编解码可逆；snapshot 固定格式、stats 报桶数槽数指纹位数条目数与踢出数；禁用内置 hash() 与 set/dict 迭代顺序。src/cuckoofilter.py 待审，tests/run.py 全绿但覆盖不到不变式，REVIEW.md 是待填模板（六节，每节写触发条件/实际行为/根因/该怎么改并指到文件与行范围）。

任务：通读源码，把违反契约处逐条写进 REVIEW.md，不改代码。

验收：python check/check.py 退出码 0、8 场景全过（六节 finding + anchor 两组正确性锚点）；python tests/run.py 仍全绿（不改 src/cuckoofilter.py、不改 tests/、不改 check/）。

约束：只写 REVIEW.md；每条落到具体文件、行范围与可复现调用序列，无落点形容词算没写；六节分别覆盖指纹与候选桶、踢出与失败返回、删除定位、半排序编解码、扩容确定性、负载因子与假阳性率。
