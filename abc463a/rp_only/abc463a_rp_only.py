def solve(x, y):
    return x * 9 == y * 16

def answer(x, y):
    if solve(x, y):
        return "Yes"
    else:
        return "No"

tests = [
    (800, 450),
    (234, 108),
    (108, 192),
    (16, 9),
    (32, 18),
    (4, 3),
    (1000, 562),
]

for x, y in tests:
    print(x, y, answer(x, y))