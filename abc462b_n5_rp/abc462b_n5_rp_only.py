# abc462b_rp.py
# MicroPython / CPython 両対応のつもり
# RUN_TESTS=True なら内蔵テストを実行
# RUN_TESTS=False なら標準入力から解く

import sys

RUN_TESTS = True


def solve(data):
    tokens = data.split()
    if not tokens:
        return ""

    p = 0
    n = int(tokens[p])
    p += 1

    # received_by[r] = 人 r+1 にギフトを送った人たち
    received_by = [[] for _ in range(n)]

    for giver in range(1, n + 1):
        k = int(tokens[p])
        p += 1

        for _ in range(k):
            receiver = int(tokens[p])
            p += 1
            received_by[receiver - 1].append(giver)

    out_lines = []

    for givers in received_by:
        if len(givers) == 0:
            out_lines.append("0")
        else:
            line = str(len(givers))
            for g in givers:
                line += " " + str(g)
            out_lines.append(line)

    return "\n".join(out_lines)


def clean(s):
    return "\n".join(s.strip().splitlines())


TEST_CASES = [
    (
        # 基本ケース
        """\
4
2 2 3
1 3
0
1 1
""",
        """\
1 4
1 1
2 1 2
0
""",
    ),
    (
        # 誰にも送らないケース
        """\
3
0
0
0
""",
        """\
0
0
0
""",
    ),
    (
        # 全員が自分以外に送るケース
        """\
3
2 2 3
2 1 3
2 1 2
""",
        """\
2 2 3
2 1 3
2 1 2
""",
    ),
    (
        # N=1
        """\
1
0
""",
        """\
0
""",
    ),
    (
        # 少し混ぜたケース
        """\
5
3 2 3 5
1 5
2 1 2
0
1 1
""",
        """\
2 3 5
2 1 3
1 1
0
2 1 2
""",
    ),
]


def run_tests():
    ok_count = 0

    for i, case in enumerate(TEST_CASES, 1):
        inp, expected = case
        got = solve(inp)
        expected = clean(expected)

        if got == expected:
            print("case", i, "OK")
            ok_count += 1
        else:
            print("case", i, "NG")
            print("--- input ---")
            print(inp)
            print("--- expected ---")
            print(expected)
            print("--- got ---")
            print(got)

    print("passed", ok_count, "/", len(TEST_CASES))


def main():
    data = sys.stdin.read()
    ans = solve(data)
    if ans:
        print(ans)


if RUN_TESTS:
    run_tests()
else:
    main()