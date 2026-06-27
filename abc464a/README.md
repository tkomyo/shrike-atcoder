# ABC464A - Shrike-Lite FPGA 実装

AtCoder Beginner Contest 464 A を Shrike-Lite で解く実験です。

RP2040 から入力文字列 `S` を 1 文字ずつ SPI で FPGA へ送り、FPGA 側では `signed [7:0] diff` で `E` と `W` の差分を蓄積します。最後に `EOD` を送り、その次の `NOP` で `East` / `West` の結果を読みます。

## 問題概要

入力文字列 `S` は `E` と `W` のみからなります。

```text
1 <= |S| <= 99
|S| は奇数
E の数と W の数は一致しない
```

判定は次の通りです。

```text
E が多い -> East
W が多い -> West
```

## SPI プロトコル

1 SPI frame は 1 byte です。

```text
MOSI:
  bit7..5 : CMD
  bit4..1 : reserved
  bit0    : DATA
```

CMD 仕様:

```text
000 : NOP / READ
001 : DATA
010 : EOD
101 : DEBUG
111 : RESET
```

`DATA` コマンドでは `bit0` が文字を表します。

```text
bit0 = 1 -> E
bit0 = 0 -> W
```

## FPGA 側の処理

FPGA 側では `signed [7:0] diff` を持ち、受信した文字に応じて差分を更新します。

```text
RESET:
  diff = 0
  reply_reg = 0x00

DATA bit0=1:
  diff += 1

DATA bit0=0:
  diff -= 1

EOD:
  diff > 0 なら reply_reg = 0x81
  それ以外なら reply_reg = 0x80

DEBUG:
  reply_reg = diff[7:0]
```

`EOD` や `DEBUG` と同じ SPI 転送では結果を読みません。コマンド送信後、次の `NOP` で `reply_reg` を読みます。

## MISO 応答

```text
0x00 : WAIT / CLEAR
0x81 : East
0x80 : West
その他 : DEBUG 用の signed 8-bit diff
```

`EOD` 後の次の `NOP` で次の値を読みます。

```text
0x81 -> East
0x80 -> West
```

`DEBUG` 後の次の `NOP` では、`signed 8-bit` の `diff` 値を読みます。

## 通信シーケンス

各テストケースは次の流れで実行します。

```text
RESET
NOP              -> clear 確認
DATA char1
DATA char2
...
DEBUG            -> 必要な場合のみ
NOP              -> DEBUG diff 読み出し
EOD
NOP              -> result 読み出し
RESET
NOP              -> clear 確認
```

## RP2040 側

MicroPython テストは次のファイルです。

```text
firmware/micropython/abc464a_test.py
```

SPI 設定:

```text
SPI0
baudrate = 1_000_000
polarity = 0
phase = 0
SCK  = GP2
MOSI = GP3
MISO = GP0
CS   = GP1
FPGA reset = GP14
```

主な補助関数:

```text
make_frame(cmd, bit=0)
spi_xfer(byte)
send_reset()
send_nop()
send_data(ch)
send_eod()
send_debug()
read_result()
read_debug_diff()
run_case(name, s, expected)
measure_case(name, s, expected, repeat=1)
run_timing_tests()
run_tests()
```

## テストケース

公式サンプル、単一文字、独自ケース、長さ 99 の境界ケース、DEBUG 確認を含めています。

```text
EEWEW                     -> East
WWWWWWW                   -> West
E                         -> East
W                         -> West
EEEWW                     -> East
EEWWW                     -> West
E * 50 + W * 49           -> East
E * 49 + W * 50           -> West
EWE debug diff = +1       -> East
WWE debug diff = -1       -> West
```

実機テスト結果:

```text
SUMMARY: 10 / 10 passed
```

## リソース使用量

```text
CLB LUT5s: 84/1120
CLBs:      14/140
FFs:       45
BRAM:      0/8
```

## タイミング測定

`run_timing_tests()` では、`print` ログの時間が SPI 通信時間に混ざらないように `log=False` で測定します。

測定対象は次の 1 ケース全体です。`hw_reset()` は測定対象に含めません。

```text
RESET -> NOP -> DATA列 -> EOD -> NOP result -> RESET -> NOP
```

実測値:

```text
len=1   avg約2.2ms
len=5   avg約3.5ms
len=99  avg約38〜40ms
```

## AI支援について

この実装は AI 支援を受けて作成しました。

* 解法方針、RP2040 と FPGA の役割分担、SPI プロトコル、最終確認はリポジトリ管理者が判断しました。
* ChatGPT は設計相談、レビュー、Codex への実装指示作成に使用しました。
* Codex は Verilog、MicroPython テストコード、README の作成・修正支援に使用しました。
* 最終的に Renesas Forge で合成し、Shrike-Lite 実機で動作確認しました。
