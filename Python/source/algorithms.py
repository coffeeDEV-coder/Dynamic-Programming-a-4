#LCS
def lcs(request):
    """dp[i][j] = length of LCS of a[:i] and b[:j]."""
    a = request["a"]
    b = request["b"]
    n, m = len(a), len(b)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        ai = a[i - 1]
        row = dp[i]
        prev = dp[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                row[j] = prev[j - 1] + 1
            else:
                left = row[j - 1]
                up = prev[j]
                row[j] = left if left > up else up
    i, j = n, m
    out = []
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    out.reverse()
    return {"length": dp[n][m], "sequence": "".join(out)}


# Interval DP
def merge(request):
    """dp[l][r] = min cost to merge blocks l..r into one block."""
    sizes = request["sizes"]
    n = len(sizes)
    if n <= 1:
        return {"cost": 0, "plan": []}

    pre = [0] * (n + 1)
    for i, x in enumerate(sizes):
        pre[i + 1] = pre[i] + x

    dp = [[0] * n for _ in range(n)]
    split = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for l in range(0, n - length + 1):
            r = l + length - 1
            best = None
            best_k = l
            for k in range(l, r):
                c = dp[l][k] + dp[k + 1][r]
                if best is None or c < best:
                    best = c
                    best_k = k
            dp[l][r] = best + (pre[r + 1] - pre[l])
            split[l][r] = best_k
    plan = []
    stack = [(0, n - 1, False)]
    while stack:
        l, r, visited = stack.pop()
        if l == r:
            continue
        k = split[l][r]
        if visited:
            plan.append([l, k, r])
        else:
            stack.append((l, r, True))
            stack.append((k + 1, r, False)) 
            stack.append((l, k, False))     
    return {"cost": dp[0][n - 1], "plan": plan}
#tree
def tree(request):
    """take[v]: best in subtree of v with v chosen; skip[v]: v not chosen."""
    n = request["n"]
    weights = request["weights"]
    edges = request["edges"]
    if n == 0:
        return {"weight": 0, "selected": []}

    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [-1] * n
    order = [0]
    for v in order:
        pv = parent[v]
        for u in adj[v]:
            if u != pv:
                parent[u] = v
                order.append(u)

    take = list(weights)
    skip = [0] * n
    for v in reversed(order): 
        p = parent[v]
        if p >= 0:
            take[p] += skip[v]
            skip[p] += take[v] if take[v] > skip[v] else skip[v]
    chosen = [False] * n
    for v in order:  
        p = parent[v]
        if p >= 0 and chosen[p]:
            chosen[v] = False
        else:
            chosen[v] = take[v] > skip[v]

    total = take[0] if take[0] > skip[0] else skip[0]
    return {"weight": total, "selected": [v for v in range(n) if chosen[v]]}
#Exact search
def naive(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}
    positions = []
    for i in range(n - m + 1):
        j = 0
        while j < m and text[i + j] == pattern[j]:
            j += 1
        if j == m:
            positions.append(i)
    return {"positions": positions}
def kmp(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}
    if m > n:
        return {"positions": []}
    pi = [0] * m
    k = 0
    for i in range(1, m):
        c = pattern[i]
        while k > 0 and pattern[k] != c:
            k = pi[k - 1]
        if pattern[k] == c:
            k += 1
        pi[i] = k

    positions = []
    k = 0
    for i in range(n):
        c = text[i]
        while k > 0 and pattern[k] != c:
            k = pi[k - 1]
        if pattern[k] == c:
            k += 1
        if k == m:
            positions.append(i - m + 1)
            k = pi[k - 1]  
    return {"positions": positions}
def rk(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}
    if m > n:
        return {"positions": []}

    BASE = 31
    MOD = 101
    high = pow(BASE, m - 1, MOD) 

    hp = 0
    hw = 0
    for i in range(m):
        hp = (hp * BASE + ord(pattern[i])) % MOD
        hw = (hw * BASE + ord(text[i])) % MOD

    positions = []
    for i in range(n - m + 1):
        if hw == hp:
            if text[i:i + m] == pattern:
                positions.append(i)
        if i + m < n:
            hw = ((hw - ord(text[i]) * high) * BASE + ord(text[i + m])) % MOD
    return {"positions": positions}
def suffix(request):
    text = request["text"]
    n = len(text)
    if n == 0:
        return {"sa": [], "lcp": [], "repeated": ""}

    rank = [ord(c) for c in text]
    sa = list(range(n))
    mult = max(n, 127) + 2 
    k = 1
    while True:
        key = [
            rank[i] * mult + (rank[i + k] + 1 if i + k < n else 0)
            for i in range(n)
        ]
        sa.sort(key=key.__getitem__)
        new_rank = [0] * n
        for idx in range(1, n):
            new_rank[sa[idx]] = new_rank[sa[idx - 1]] + (
                1 if key[sa[idx]] != key[sa[idx - 1]] else 0
            )
        rank = new_rank
        if rank[sa[-1]] == n - 1: 
            break
        k *= 2
    lcp = [0] * n
    h = 0
    for i in range(n):
        r = rank[i]
        if r > 0:
            j = sa[r - 1]
            while i + h < n and j + h < n and text[i + h] == text[j + h]:
                h += 1
            lcp[r] = h
            if h > 0:
                h -= 1
        else:
            h = 0
    best = 0
    best_idx = 0
    for i in range(n):
        if lcp[i] > best:
            best = lcp[i]
            best_idx = i
    repeated = text[sa[best_idx]:sa[best_idx] + best] if best > 0 else ""
    return {"sa": sa, "lcp": lcp, "repeated": repeated}
#AHO
def aho(request):
    patterns = request["patterns"]
    texts = request["texts"]
    p = len(patterns)
    go = [{}]
    term = [0] * p  
    for idx, pat in enumerate(patterns):
        s = 0
        for c in pat:
            nxt = go[s].get(c)
            if nxt is None:
                nxt = len(go)
                go.append({})
                go[s][c] = nxt
            s = nxt
        term[idx] = s 
    S = len(go)
    fail = [0] * S
    order = []  
    for c, u in go[0].items():
        fail[u] = 0
        order.append(u)
    head = 0
    while head < len(order):
        v = order[head]
        head += 1
        for c, u in go[v].items():
            f = fail[v]
            while f != 0 and c not in go[f]:
                f = fail[f]
            fail[u] = go[f].get(c, 0)
            order.append(u)
    counts = []
    rev = order[::-1]
    for text in texts:
        if p == 0:
            counts.append([])
            continue
        visit = [0] * S
        s = 0
        for c in text:
            while s != 0 and c not in go[s]:
                s = fail[s]
            s = go[s].get(c, 0)
            visit[s] += 1
        for v in rev:
            cv = visit[v]
            if cv:
                visit[fail[v]] += cv
        counts.append([visit[term[i]] for i in range(p)])
    return {"counts": counts}
