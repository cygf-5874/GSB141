"""cuckoofilter.py — 布谷鸟过滤器（Cuckoo Filter）实现（待审）。

本文件是即将送外部评审的待审实现。对外契约见仓库 README.md 的「对外契约」10 条。
评审目标：通读本文件，把违反契约的地方逐条写进 REVIEW.md，不需要改代码。
"""

MAGIC = 0x9E3779B97F4A7C15


def _hash_key(key):
    """把 key（str / bytes / 其它可哈希对象）确定性地映射成 64 位整数。

    不使用内置 hash()（自带随机盐），保证跨进程可复现。
    """
    if isinstance(key, str):
        data = key.encode("utf-8")
    elif isinstance(key, (bytes, bytearray)):
        data = bytes(key)
    else:
        data = str(key).encode("utf-8")
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFFFFFFFFFF
    return h


class CuckooFilter:
    def __init__(self, num_buckets, bucket_size=4, fingerprint_bits=8, max_kicks=500):
        if num_buckets <= 0:
            raise ValueError("num_buckets must be positive")
        self.num_buckets = num_buckets
        self.bucket_size = bucket_size
        self.fingerprint_bits = fingerprint_bits
        self.max_kicks = max_kicks
        self.buckets = [[] for _ in range(num_buckets)]
        self.count = 0
        self.kick_count = 0

    def _fingerprint(self, h):
        # 契约 2：指纹应取哈希的低 fingerprint_bits 位，且不得为 0。
        # BUG(defect ①): 这里直接拿了完整 64 位哈希 h，没有截断到 fingerprint_bits 位，
        #   导致 fp 可能高达 2^64，指纹位宽与「fp != 0」的语义都失真。
        fp = h
        if fp == 0:
            fp = 1
        return fp

    def _i1(self, h):
        return h % self.num_buckets

    def _alt_index(self, i, fp, h=None):
        # 契约 3：alt_index 必须只依赖 fp，且满足自反性
        #   alt_index(alt_index(i, fp), fp) == i。
        # BUG(defect ① 连带): 这里实际用全哈希 h 来算备选桶，而不是只依赖 fp，
        #   因此 alt_index 不再只依赖 fp，自反性在 add/contains 路径上也依赖 h。
        x = h if h is not None else fp
        hh = (x * MAGIC) & 0xFFFFFFFFFFFFFFFF
        hh = hh % self.num_buckets
        return (i ^ hh) % self.num_buckets

    def add(self, key):
        h = _hash_key(key)
        fp = self._fingerprint(h)
        i1 = self._i1(h)
        i2 = self._alt_index(i1, fp, h)
        for b in (i1, i2):
            if len(self.buckets[b]) < self.bucket_size:
                self.buckets[b].append(fp)
                self.count += 1
                return True
        # 两桶都满，踢出一个指纹做重定位。
        # BUG(defect ②): 没有 max_kicks 上限，也不在超限时返回 False，而是
        #   while True 无限迁移，达到容量上限时会死循环（违反契约 4）。
        cur_i = i2
        cur_fp = fp
        while True:
            victim = self.buckets[cur_i][0]
            self.buckets[cur_i][0] = cur_fp
            cur_fp = victim
            self.kick_count += 1
            cur_i = self._alt_index(cur_i, cur_fp, h)
            if len(self.buckets[cur_i]) < self.bucket_size:
                self.buckets[cur_i].append(cur_fp)
                self.count += 1
                return True

    def contains(self, key):
        h = _hash_key(key)
        fp = self._fingerprint(h)
        i1 = self._i1(h)
        i2 = self._alt_index(i1, fp, h)
        return fp in self.buckets[i1] or fp in self.buckets[i2]

    def delete(self, key):
        h = _hash_key(key)
        fp = self._fingerprint(h)
        i1 = self._i1(h)
        # BUG(defect ③): 删除时算备选桶用的是 key 的哈希 h，而不是 fp，
        #   且公式 (i1 + (h & (n-1))) 不满足自反性，于是会去删「别人的桶」
        #   里的指纹（违反契约 3/5）。
        i2 = (i1 + (h & (self.num_buckets - 1))) % self.num_buckets
        if fp in self.buckets[i1]:
            self.buckets[i1].remove(fp)
            self.count -= 1
            return True
        if fp in self.buckets[i2]:
            self.buckets[i2].remove(fp)
            self.count -= 1
            return True
        return False

    def load_factor(self):
        # 契约 6/7：负载因子 = 已占槽数 / 总槽数。
        # BUG(defect ⑥): 这里按「已占桶数 / 桶数」算，漏乘 bucket_size，
        #   于是上界失真、假阳性率口径也跟着失真（违反契约 6/7）。
        occupied_buckets = sum(1 for b in self.buckets if b)
        return occupied_buckets / self.num_buckets

    def stats(self):
        return {
            "num_buckets": self.num_buckets,
            "bucket_size": self.bucket_size,
            "fingerprint_bits": self.fingerprint_bits,
            "count": self.count,
            "kick_count": self.kick_count,
        }

    def snapshot(self):
        rows = []
        for i, b in enumerate(self.buckets):
            rows.append("%d:%s" % (i, ",".join(str(x) for x in b)))
        return "\n".join(rows)

    def to_bytes(self):
        # 契约 9：桶内按 fp % bucket_size 排序存储，存储值 = fp // bucket_size。
        out = bytearray()
        out += self.num_buckets.to_bytes(4, "little")
        out += self.bucket_size.to_bytes(1, "little")
        out += self.fingerprint_bits.to_bytes(1, "little")
        for b in self.buckets:
            items = sorted(b, key=lambda x: x % self.bucket_size)
            for x in items:
                stored = x // self.bucket_size
                out += stored.to_bytes(1, "little")
        return bytes(out)

    def from_bytes(self, data):
        # 契约 9：from_bytes 必须能无损还原 to_bytes 的结果（打包/解包可逆）。
        p = 0
        num_buckets = int.from_bytes(data[p:p + 4], "little"); p += 4
        bucket_size = data[p]; p += 1
        fingerprint_bits = data[p]; p += 1
        self.num_buckets = num_buckets
        self.bucket_size = bucket_size
        self.fingerprint_bits = fingerprint_bits
        self.buckets = [[] for _ in range(num_buckets)]
        self.count = 0
        for bi in range(num_buckets):
            bucket = []
            for slot in range(bucket_size):
                stored = data[p]; p += 1
                # BUG(defect ④): 还原公式写成了 stored * bucket_size + slot，
                #   正确应为 slot * bucket_size + stored（slot 才是排序键），
                #   导致指纹顺序被打乱、往返后 contains 结果变化（违反契约 9）。
                fp = stored * bucket_size + slot
                if fp != 0:
                    bucket.append(fp)
                    self.count += 1
            self.buckets[bi] = bucket
        return self

    def resize(self, new_num_buckets=None):
        if new_num_buckets is None:
            new_num_buckets = self.num_buckets * 2
        # 契约 8/10：扩容重哈希搬迁必须确定性（桶序升序、槽序升序），
        #   不能依赖 set/dict 的迭代顺序。
        # BUG(defect ⑤): 用 set 收集待搬迁指纹，遍历顺序依赖哈希与插入序，
        #   重哈希后各键所在的桶会漂移（违反契约 8/10）。
        items = set()
        for b in self.buckets:
            for fp in b:
                items.add(fp)
        self.num_buckets = new_num_buckets
        self.buckets = [[] for _ in range(new_num_buckets)]
        self.count = 0
        for fp in items:
            self._force_add(fp)
        return True

    def _force_add(self, fp):
        i1 = fp % self.num_buckets
        i2 = self._alt_index(i1, fp)
        for b in (i1, i2):
            if len(self.buckets[b]) < self.bucket_size:
                self.buckets[b].append(fp)
                self.count += 1
                return True
        self.buckets[i1].append(fp)
        self.count += 1
        return True
