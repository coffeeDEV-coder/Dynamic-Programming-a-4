# Assignment 4 — analysis

## Environment and commands

- Language: **Python** (`submission.json` → `Python`), run as `python Python/source/main.py` (JSON Lines on stdin/stdout). There is no compilation step; the interpreter byte-compiles modules on import, which happens before any timed region.
- Runtime and machine used for all measurements in this document: see "Environment used for the measurements" in the search comparison below (Python version, OS, CPU, RAM are printed by `tests/student/bench_search.py`).
- Commands:
  - `python tools/run.py --setup` — transport check (ping).
  - `python tools/run.py --check` — public examples, edge cases and the two-batch state-reset check.
  - `python tests/student/run_student_tests.py` — own tests (`tests/student/student.json`, same format as `tests/public.json`), generated large cases, randomized search cross-check; rewrites `tests/student/tests.md`.
- The final commit URL is recorded in Moodle. Only actual measurements are reported below; nothing was estimated.

## Algorithm explanations

Notation: `n`, `m` are the lengths of the two inputs of a command, `L` is the total length of all patterns, `q` the number of texts, `S` the number of automaton states. Python integers are arbitrary precision, so there is no overflow; all values stay inside the signed 64-bit range required by the contract.

### lcs

- **State.** `dp[i][j]` is the length of a longest common subsequence of the prefixes `a[:i]` and `b[:j]`; `i` and `j` count how many characters of `a` and `b` are considered (`0..n`, `0..m`).
- **Base and transition.** `dp[0][j] = dp[i][0] = 0`. If `a[i-1] == b[j-1]` then `dp[i][j] = dp[i-1][j-1] + 1`, otherwise `max(dp[i-1][j], dp[i][j-1])`.
- **Order.** Rows `i = 1..n`, columns `j = 1..m` ascending, so the three cells a cell depends on (diagonal, above, left) are already filled.
- **Correctness.** If the last characters are equal, some optimal common subsequence matches them (an optimal solution that leaves one of them unmatched can be rearranged to use the pair), giving `1 + dp[i-1][j-1]`. If they differ, at least one of them is unmatched, so the optimum is the better of dropping either one. Induction on `i + j`.
- **Reconstruction and ties.** Walk back from `(n, m)`: equal characters are taken and the walk moves diagonally; otherwise it moves to the larger neighbour, and on equality it moves up (`dp[i-1][j] >= dp[i][j-1]`). The characters are collected in reverse and reversed at the end. The rule is deterministic; for `ABC` / `BAC` it returns `AC`, although `BC` is equally optimal (the validator accepts any valid LCS of the optimal length).
- **Time and memory.** Θ(n·m) cell updates plus O(n+m) for the walk. Memory Θ(n·m): a list of `n+1` Python lists of `m+1` integers (needed for reconstruction). Output length ≤ min(n, m).
- **Boundary test.** `lcs-tie` (`ABC`, `BAC`): two different optima; a wrong step rule would produce a string that is not a common subsequence or whose length differs from `dp[n][m]`. `lcs-both-empty` checks that the walk does not run when `n = m = 0`.

### merge

- **State.** `dp[l][r]` is the minimum total cost of merging the adjacent blocks `l..r` into one block (`0 <= l <= r < n`); `split[l][r]` stores the best last-merge position `k`. `pre` holds prefix sums of `sizes`.
- **Base and transition.** `dp[l][l] = 0`. For `l < r`: `dp[l][r] = min over k in [l, r) of dp[l][k] + dp[k+1][r] + (pre[r+1] - pre[l])`, because the final merge of `l..k` with `k+1..r` costs the size of the whole interval.
- **Order.** By increasing interval length `2..n`; both sub-intervals are strictly shorter, hence ready.
- **Correctness.** Any sequence of merges of adjacent blocks is a binary tree over the ordered blocks; its last merge splits the interval at some `k` into two independent sub-problems whose costs add up, so minimising over `k` is exact (optimal substructure).
- **Reconstruction and ties.** An iterative post-order traversal with an explicit stack starts at `(0, n-1)` and emits `[l, k, r]` after both children, so every merge appears after the merges that create its two blocks; there are exactly `n-1` entries. On ties the first (smallest) `k` is kept (strict `<`). `n = 0` or `n = 1` returns cost 0 and an empty plan.
- **Time and memory.** About n³/6 inner iterations, Θ(n³) (n ≤ 200 ⇒ about 1.3·10⁶); memory Θ(n²) for `dp` and `split` (lists of lists). Output: `n-1` triples.
- **Boundary test.** `merge-zero-in-middle` (`[0, 10⁹, 0]`): zero-size blocks still have to be merged and the cost (2·10⁹) exceeds 32 bits. `merge-zeros-tie`: all splits tie, any valid plan with `n-1` merges is accepted.

### tree

- **State.** The tree is rooted at vertex 0. `take[v]` is the best weight of an independent set in the subtree of `v` that contains `v`; `skip[v]` is the best weight in that subtree without `v`.
- **Base and transition.** Initially `take[v] = weight[v]`, `skip[v] = 0` (leaf values). A child `c` adds `skip[c]` to `take[parent]` and `max(take[c], skip[c])` to `skip[parent]`.
- **Order.** A BFS order from 0 is built iteratively; vertices are processed in reverse BFS order, so all children of a vertex are processed before the vertex itself is used as a child. No recursion is used because a chain of 100000 vertices would exceed Python's recursion limit.
- **Correctness.** Conflicts exist only on tree edges and the subtrees of different children are independent, so the two recurrences are exact. The answer is `max(take[0], skip[0])`; because `skip` allows the empty set, the result is never negative. The contract guarantees that the graph is a tree (connected), so BFS from 0 reaches every vertex.
- **Reconstruction and ties.** Vertices are visited in BFS order (parents first). A vertex is skipped if its parent was chosen; otherwise it is taken only if `take[v] > skip[v]` (strict). Ties therefore prefer not selecting a vertex, which also gives weight 0 and an empty set for all-zero or all-negative input. The `selected` list is produced in ascending vertex order.
- **Time and memory.** O(n) time and memory: adjacency lists for `n-1` edges, arrays `parent`, `order`, `take`, `skip`, `chosen`. Output: up to `n` indices.
- **Boundary test.** `tree-deep-chain` (n = 100000, weights 1, expected 50000): a recursive implementation overflows the stack. `tree-all-negative` and `tree-tie` check the empty set and independence on equal weights.

### naive

- **Invariant.** Before iteration `i`, `positions` contains exactly the match starts smaller than `i`; start `i` is tested by comparing `text[i+j]` with `pattern[j]` for `j = 0, 1, …` until a mismatch or `j = m`.
- **Base cases.** `m = 0` returns `0..n` (n+1 positions, boundaries including `n`); `m > n` gives an empty range of starts, so `[]`.
- **Correctness.** Every start `0..n-m` is tested independently and completely, so all occurrences, including overlapping ones, are reported in increasing order.
- **Time and memory.** O((n−m+1)·m) worst case (e.g. `a^n` vs `a^(m-1)b`), O(n) when mismatches occur early; O(1) extra memory apart from the output (up to n+1 integers).
- **Boundary test.** `naive-empty-pattern` (`"ab"`, `""` → `[0,1,2]`) and `naive-pattern-longer` detect a missing final boundary and a negative range.

### kmp

- **State.** `pi[i]` is the length of the longest proper prefix of `pattern[:i+1]` that is also its suffix (border). During the search `k` is the length of the longest prefix of the pattern that is a suffix of the text read so far (`k < m`).
- **Transition.** On a mismatch `k = pi[k-1]` repeatedly while `k > 0`; on a match `k += 1`. When `k == m` a match starting at `i − m + 1` is recorded and `k = pi[m-1]`, which keeps overlapping matches. `pi` is built by the same loop on the pattern against itself.
- **Order and correctness.** Text positions are processed left to right and `pi` values are computed before they are used (`pi[k-1]` with `k <= i`). A pattern prefix that is a suffix of the text must be a border of the longer matched prefix, so falling back along `pi` loses no candidate.
- **Time and memory.** O(n + m): `k` increases at most once per character and every fallback decreases it, so total fallbacks ≤ total increments. Memory O(m) for `pi` plus the output. `m = 0` and `m > n` are handled before `pi` is built.
- **Boundary test.** `kmp-overlap-after-match` (`abababa`, `aba` → `[0,2,4]`): a version that restarts from `k = 0` after a full match misses position 2; the mutation experiment below confirmed that the test suite fails for such a version.

### rk

- **State.** The hash of a string `s` of length `m` is `Σ ord(s[j])·31^(m-1-j) mod 101` (base 31, modulus 101; the leftmost character has the highest power). `hw` is the hash of the current window `text[i:i+m]`, `hp` the pattern hash, `high = 31^(m-1) mod 101`.
- **Transition.** `hw = ((hw − ord(text[i])·high)·31 + ord(text[i+m])) mod 101`. Python's `%` returns a non-negative result, so no explicit normalisation of negative remainders is needed (in C++/Java it would be).
- **Verification.** Equal hashes only make a window a *candidate*: it is reported only if `text[i:i+m] == pattern`, which compares the actual characters. Equal strings always have equal hashes, so no true match is lost; the character comparison removes false positives caused by the deliberately tiny modulus.
- **Time (candidate-sensitive bound) and memory.** O(n + m + c·m), where `c` is the number of windows whose hash equals the pattern hash (true matches plus false candidates). With modulus 101 about one window in 101 is a false candidate on random data; in the worst case (many matches, or adversarially colliding windows) the bound is Θ((n−m+1)·m). The slice comparison runs in C, so its constant is small, but the bound is unchanged. Extra memory O(m) for the temporary slice.
- **Boundary test.** `rk-collision-rejected`: `ab` and `dj` both hash to 75 and `bc` and `ek` both hash to 6 (`rk-collision-bcek`), so the window at position 0 of `abdj` is a candidate for `dj` and must be rejected; a hash-only version reports `[0, 2]` instead of `[2]`. The mutation experiment confirmed that tests fail when the verification is removed.

### suffix

Doubling (suffix array):

- **State.** After the round with offset `k`, `rank[i]` is the rank of suffix `i` among all suffixes compared by their first `2k` characters (equal prefixes share a rank). Initially `rank[i] = ord(text[i])` (ASCII 32–126).
- **Transition.** The key of suffix `i` is the pair `(rank[i], rank[i+k])` encoded as the single integer `rank[i]·mult + (rank[i+k] + 1 if i+k < n else 0)` with `mult = max(n, 127) + 2`. The `+1` makes a missing second half (suffix shorter than `k`) sort before any real rank, so no sentinel is needed and a suffix that is a prefix of another comes first. `mult` exceeds every possible second component, so integer order equals pair order.
- **Order and termination.** `sa.sort(key=key.__getitem__)` (Timsort, O(n log n) per round) orders suffixes by the keys, new ranks are computed by comparing neighbouring keys, and the offset doubles. The loop stops as soon as all ranks are distinct (`rank[sa[-1]] == n − 1`); this happens after at most ⌈log₂ n⌉ + 1 rounds, because once `2k ≥ n` all suffixes are distinguished by their first `2k` characters.
- **Time and memory.** O(n log² n) worst case, O(n) memory for `sa`, `rank`, `key`, `new_rank`, `lcp` (n ≤ 50000 ⇒ at most 17 rounds). Ordering is by character codes, so uppercase letters sort before lowercase letters.

Kasai (LCP):

- **State.** `rank` is the inverse permutation of `sa`; `lcp[r]` is the length of the longest common prefix of `sa[r−1]` and `sa[r]` (`lcp[0] = 0`). `h` is the LCP of suffix `i` with its predecessor in `sa` order.
- **Transition and invariant.** Suffixes are processed in text order `i = 0..n−1`. If suffix `i` has LCP `h > 0` with its predecessor, then suffix `i+1` has an LCP of at least `h − 1` with its own predecessor, so `h` is decreased by 1 (never reset to 0) and extended by direct character comparison. `h` increases at most 2n times in total ⇒ O(n). For `rank[i] == 0` the value `h` is reset to 0.
- **Repeated substring.** The longest substring occurring at least twice (overlaps allowed) has the length `max(lcp)`: any common prefix of two suffixes is shared by every suffix between them in sorted order, so the maximum is attained by neighbours. The result is `text[sa[idx] : sa[idx] + best]` for the first index `idx` with the maximal `lcp`; for `best = 0` it is the empty string. Which of several longest repeats is returned is not fixed by the contract (the validator checks the length and that it occurs at least twice).
- **Boundary test.** `suffix-abab` (`sa = [2,0,3,1]`): the suffix `ab` is a prefix of `abab` and must come first. `suffix-all-equal-max` (`a` repeated 50000 times) runs the deepest doubling and the longest Kasai runs; in my mutation experiment a variant that resets `h` to 0 instead of decreasing it exceeded the time limit, which shows the decrement is essential for the linear bound.

### aho

- **State.** The automaton is a trie stored as a list of dictionaries `go[state][char] → child`; `term[idx]` is the terminal state of pattern `idx`; `fail[v]` is the state of the longest proper suffix of the string of `v` that is also a trie node. For each text, `visit[v]` counts how often state `v` is the current state after reading a character.
- **Construction.** Patterns are inserted character by character. Duplicate patterns end in the same state, so they share `term`. `fail` is computed by BFS (shallower states first): for a child `u` of `v` via `c`, follow `fail[v]`, `fail[fail[v]]`, … until a state with a transition on `c` exists (or the root is reached).
- **Scanning.** For each character, follow failure links while there is no transition, then take the transition (or stay at the root). Because the depth grows by at most 1 per character and each failure step decreases it, scanning one text is amortised O(|text|).
- **Counting suffix patterns.** After scanning, `visit` is propagated along the failure links in reverse BFS order (deepest first): `visit[fail[v]] += visit[v]`. Afterwards `visit[s]` equals the number of end positions where the string of `s` occurs, so a pattern that is a suffix of another one (`he` inside `she`) is counted without walking output links per character. The answer for pattern `idx` is `visit[term[idx]]`.
- **Duplicates and reset.** Duplicate patterns give identical counts in separate columns. The automaton (`go`, `fail`) is built once and is read-only afterwards; `visit` is allocated anew and the scanning state starts at the root for every text, so no count or state leaks between texts or between requests. With no patterns every text gets `[]`; with no texts the result is `[]`; an empty text gives zeros.
- **Time and memory.** Construction O(L) (each trie edge is processed once, failure steps amortised along each pattern path). Per text O(|text| + S) because the propagation visits every state, so the total is O(L + Σ|textⱼ| + q·S). Memory O(S) for dictionaries, `fail`, `term` and one `visit` array. Sparse dictionaries are used instead of a 95-column table to keep memory proportional to the number of trie edges.
- **Boundary test.** `aho-suffix-patterns` (`abc`, `bc`, `c` in `abc` → `[1,1,1]`) detects missing failure-link propagation; `aho-reset-between-texts` detects counts or state carried over between texts; `aho-example-duplicates` covers duplicates.


### Environment used for the measurements

- Python 3.12.3 (CPython), Linux-6.18.44-fc-v310-x86_64-with-glibc2.39
- CPU: Intel(R) Xeon(R) Processor @ 2.30GHz, logical cores: 1, RAM: 3.9 GiB

|Case|n|m|Seed/generator|Algorithm|Run 1|Run 2|Run 3|Run 4|Run 5|Median|Correct outputs checked|
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---|
|random-planted|1000|100|seed 3026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|naive|0.060|0.059|0.059|0.059|0.059|**0.059**|yes: equal to reference and to the other two (1 matches)|
|random-planted|1000|100|seed 3026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|kmp|0.074|0.058|0.056|0.055|0.055|**0.056**|yes: equal to reference and to the other two (1 matches)|
|random-planted|1000|100|seed 3026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|rk|0.111|0.105|0.105|0.106|0.136|**0.106**|yes: equal to reference and to the other two (1 matches)|
|random-planted|2000|200|seed 4026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|naive|0.133|0.137|0.124|0.119|0.119|**0.124**|yes: equal to reference and to the other two (1 matches)|
|random-planted|2000|200|seed 4026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|kmp|0.109|0.109|0.110|0.109|0.126|**0.109**|yes: equal to reference and to the other two (1 matches)|
|random-planted|2000|200|seed 4026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|rk|0.225|0.227|0.256|0.219|0.216|**0.225**|yes: equal to reference and to the other two (1 matches)|
|random-planted|3000|300|seed 5026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|naive|0.181|0.179|0.179|0.178|0.179|**0.179**|yes: equal to reference and to the other two (1 matches)|
|random-planted|3000|300|seed 5026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|kmp|0.170|0.168|0.165|0.167|0.182|**0.168**|yes: equal to reference and to the other two (1 matches)|
|random-planted|3000|300|seed 5026; random.Random(seed) text over {A,C,G,T}; pattern = text slice of length m at a seeded random start|rk|0.326|0.341|0.329|0.326|0.344|**0.329**|yes: equal to reference and to the other two (1 matches)|
|repetitive-all-match|1000|100|text 'a'*n, pattern 'a'*m (deterministic, no seed)|naive|3.339|3.389|3.367|3.331|3.338|**3.339**|yes: equal to reference and to the other two (901 matches)|
|repetitive-all-match|1000|100|text 'a'*n, pattern 'a'*m (deterministic, no seed)|kmp|0.086|0.099|0.086|0.084|0.084|**0.086**|yes: equal to reference and to the other two (901 matches)|
|repetitive-all-match|1000|100|text 'a'*n, pattern 'a'*m (deterministic, no seed)|rk|0.156|0.158|0.157|0.191|0.162|**0.158**|yes: equal to reference and to the other two (901 matches)|
|repetitive-all-match|2000|200|text 'a'*n, pattern 'a'*m (deterministic, no seed)|naive|14.489|13.614|13.777|13.472|13.605|**13.614**|yes: equal to reference and to the other two (1801 matches)|
|repetitive-all-match|2000|200|text 'a'*n, pattern 'a'*m (deterministic, no seed)|kmp|0.176|0.202|0.173|0.171|0.171|**0.173**|yes: equal to reference and to the other two (1801 matches)|
|repetitive-all-match|2000|200|text 'a'*n, pattern 'a'*m (deterministic, no seed)|rk|0.329|0.335|0.344|0.335|0.338|**0.335**|yes: equal to reference and to the other two (1801 matches)|
|repetitive-all-match|3000|300|text 'a'*n, pattern 'a'*m (deterministic, no seed)|naive|31.784|38.245|32.805|36.480|34.942|**34.942**|yes: equal to reference and to the other two (2701 matches)|
|repetitive-all-match|3000|300|text 'a'*n, pattern 'a'*m (deterministic, no seed)|kmp|0.322|0.320|0.299|0.338|0.306|**0.320**|yes: equal to reference and to the other two (2701 matches)|
|repetitive-all-match|3000|300|text 'a'*n, pattern 'a'*m (deterministic, no seed)|rk|0.501|0.507|0.504|0.824|0.794|**0.507**|yes: equal to reference and to the other two (2701 matches)|
|repetitive-near-miss|1000|100|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|naive|3.379|3.665|3.550|3.497|3.402|**3.497**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|1000|100|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|kmp|0.081|0.081|0.081|0.085|0.081|**0.081**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|1000|100|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|rk|0.107|0.122|0.108|0.106|0.106|**0.107**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|2000|200|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|naive|22.099|14.049|13.972|13.908|14.067|**14.049**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|2000|200|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|kmp|0.198|0.165|0.165|0.163|0.164|**0.165**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|2000|200|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|rk|0.248|0.236|0.233|0.236|0.232|**0.236**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|3000|300|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|naive|37.956|37.621|36.205|36.269|35.639|**36.269**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|3000|300|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|kmp|0.336|0.283|0.281|0.283|0.301|**0.283**|yes: equal to reference and to the other two (0 matches)|
|repetitive-near-miss|3000|300|text 'a'*n, pattern 'a'*(m-1)+'b' (deterministic, no seed)|rk|0.328|0.361|0.322|0.324|0.404|**0.328**|yes: equal to reference and to the other two (0 matches)|

Times are in milliseconds (ms) per call. Hash-equal windows for RK (base 31, mod 101) versus true matches:

|Case|n|m|Windows|Hash-equal windows|True matches|False candidates|
|---|---:|---:|---:|---:|---:|---:|
|random-planted|1000|100|901|7|1|6|
|random-planted|2000|200|1801|20|1|19|
|random-planted|3000|300|2701|28|1|27|
|repetitive-all-match|1000|100|901|901|901|0|
|repetitive-all-match|2000|200|1801|1801|1801|0|
|repetitive-all-match|3000|300|2701|2701|2701|0|
|repetitive-near-miss|1000|100|901|0|0|0|
|repetitive-near-miss|2000|200|1801|0|0|0|
|repetitive-near-miss|3000|300|2701|0|0|0|

### Observations

- **Random text (`random-planted`).** With a 4-letter alphabet most windows mismatch at the first or second character, so naive does little work: its medians (0.059 / 0.124 / 0.179 ms for n = 1000 / 2000 / 3000) are within about 14% of KMP's (0.056 / 0.109 / 0.168 ms). RK is about 1.8 times slower than naive here (0.106 / 0.225 / 0.329 ms): every window costs a rolling-hash update with several interpreted arithmetic operations and two `ord` calls, while naive usually spends one comparison. This is a constant-factor effect of this implementation in Python, not a statement about the algorithms in general.
- **Repetitive text, naive.** On `repetitive-all-match` the naive median grows from 3.339 to 34.942 ms (×10.5) and on `repetitive-near-miss` from 3.497 to 36.269 ms (×10.4) when both n and m grow by a factor of 3. The number of character comparisons, (n−m+1)·m, grows ×9 over the same sizes, so the measured growth (×10.5 and ×10.4) is of the same order as the growth of the work, a little above it; I did not investigate the small excess (timer noise and cache effects are possible explanations, not verified). KMP and RK are about 69–128 times faster than naive on these inputs (KMP 0.320 ms and 0.283 ms; RK 0.507 ms and 0.328 ms at n = 3000).
- **KMP.** Its medians grow with n only (all-match ×3.7, near-miss ×3.5 for n ×3, a little more than the factor 3), and the results are far less sensitive to the pattern structure than naive's, which is consistent with the O(n + m) bound; on random text it does not beat naive because the failure function is rarely needed.
- **RK and the small modulus.** In `random-planted` the hash is equal for 7, 20 and 28 windows out of 901, 1801 and 2701, while only 1 is a true match; the 6, 19 and 27 false candidates (about 0.7–1.1% of the windows, close to 1/101) are exactly the extra verifications caused by modulus 101. They are rejected by the character comparison, so the output stays correct. With a larger modulus false candidates would be much rarer, but this observation concerns only the deliberately small modulus used in this assignment and must not be generalised to production hash implementations. In `repetitive-all-match` every window is a true match and therefore a candidate, so RK verifies all of them; the cost stays small because the slice comparison runs in C. In `repetitive-near-miss` the pattern hash differs from the window hash, so no window is a candidate and verification never runs; this is a lucky case for this particular pattern and does not show the worst case of RK, where many colliding windows (e.g. the `ab`/`dj` collision pair used in the tests) would each cost a full comparison.
- **Limits of these measurements.** One machine, small sizes, interpreted Python, five runs per cell: individual runs can deviate from the others (see the raw run columns), which is why medians are reported. The numbers illustrate relative behaviour on these inputs; they do not prove the asymptotic complexity of any algorithm.

## Sources and AI assistance

- Claude and Gemini were used to help memorize the structure of the code, gave examples and templates for creating own test cases