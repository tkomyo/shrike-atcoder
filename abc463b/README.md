# ABC463B - Shrike-Lite FPGA Implementation

AtCoder Beginner Contest 463 B を Shrike-Lite で解く実験です。

RP2040 側で入力を整形し、Shrike-Lite FPGA 側では 5bit mask 同士の AND 判定だけを行います。
ABC463B は A〜E の 5 種類の状態を扱うため、MOSI/MISO ともに 1 byte の SPI フレームで処理できます。

## Overview

処理の分担は以下の通りです。

```text
RP2040:
  - AtCoder 入力の整形
  - X と各 S_i を 5bit mask に変換
  - SPI で FPGA に送信
  - FPGA から結果を受信
  - Yes / No を表示

FPGA:
  - X mask を保持
  - 各 S_i mask と X mask の AND を計算
  - 1つでも non-zero なら result を 1 にする
  - 最後に MISO で result を返す
```

FPGA 側は、問題全体を保持せず、`X` と累積結果だけを持つ小さな状態付き判定器として実装しています。

## Problem Mapping

ABC463B の `A`〜`E` を 5bit mask に対応させます。

```text
A -> bit0
B -> bit1
C -> bit2
D -> bit3
E -> bit4
```

`X` は対応する bit だけが 1 の mask に変換します。

```text
X = A -> 00001
X = B -> 00010
X = C -> 00100
X = D -> 01000
X = E -> 10000
```

各 `S_i` は、文字列中の `o` を 1、`x` を 0 として 5bit mask に変換します。

```text
S_i = oxxxx -> 00001
S_i = xoxxx -> 00010
S_i = xxoxx -> 00100
S_i = xxxox -> 01000
S_i = xxxxo -> 10000
S_i = ooooo -> 11111
S_i = xxxxx -> 00000
```

判定は以下です。

```text
if (X_mask & S_mask) != 0:
    result = 1
```

すべての `S_i` についてこの判定を行い、1つでも一致すれば `Yes`、最後まで一致しなければ `No` です。

## SPI Protocol

SPI は 8bit 幅です。

### MOSI

```text
bit7..5 : CMD
bit4..0 : DATA
```

```text
[7:5] CMD
[4:0] DATA
```

### Commands

```text
000 : NOP
001 : SET_X
010 : SET_S
101 : DEBUG
111 : RESET
```

`DEBUG` はコマンド枠として予約していますが、この実装では未使用です。

### MISO

```text
bit7    : STATE / VALID
bit6..1 : AUX
bit0    : DATA / result
```

```text
[7]   valid
[6:1] aux
[0]   result
```

通常の WAIT 応答は以下です。

```text
0x00 = 00000000
```

結果応答は以下です。

```text
0x80 = 10000000  # valid=1, result=0 -> No
0x81 = 10000001  # valid=1, result=1 -> Yes
```

## Command Sequence

1回の判定処理は、必ず `RESET` から開始します。
処理終了後にも `RESET` を送信し、FPGA 内部状態をクリアします。

```text
MOSI              / MISO
------------------------
NOP               / WAIT
RESET             / WAIT or previous reply
NOP               / WAIT

SET_X             / WAIT
SET_S(1)          / WAIT
SET_S(2)          / WAIT or temporary reply
...
SET_S(N)          / WAIT or temporary reply

NOP               / final REPLY

RESET             / previous reply
NOP               / WAIT
```

`SET_S` 受信時に FPGA 側で次回 MISO 用の reply を準備するため、2個目以降の `SET_S` の受信時に暫定 reply が返る場合があります。

RP2040 側では、`SET_S` 中の MISO は正式結果として扱わず、最後の `NOP` の MISO だけを最終結果として採用します。

## FPGA Logic

FPGA 側の主要な状態は以下です。

```text
x_reg        : X の 5bit mask
reply_result : 累積結果
spi_tx_data  : 次回 MISO 用データ
```

基本動作は以下です。

```text
RESET:
  spi_tx_data   <= 0
  x_reg         <= 0
  reply_result  <= 0

SET_X:
  x_reg <= MOSI data

SET_S:
  if (MOSI data & x_reg) != 0:
      reply_result <= 1
      spi_tx_data  <= 0x81
  else:
      spi_tx_data  <= 0x80 or current result

NOP:
  no operation
  prepared spi_tx_data is returned by SPI target
```

`NOP` で結果を作るのではなく、`SET_S` 受信時に次回転送用の MISO データを準備します。
これにより、最後の `SET_S` の次に送る `NOP` で結果を読めます。

## RP2040 Side

RP2040 側では以下を担当します。

```text
- 入力文字列の parse
- X を 5bit mask に変換
- 各 S_i を 5bit mask に変換
- SPI コマンド列の送信
- final NOP の MISO を decode
- Yes / No の出力
- 通信ログの表示
```

MISO decode は以下です。

```text
valid  = (rx >> 7) & 1
aux    = (rx >> 1) & 0b111111
result = rx & 1
```

`result == 1` なら `Yes`、`result == 0` なら `No` です。

## Verification

以下のテストを RP2040 側スクリプトから実行し、すべて PASS しました。

```text
official_sample1
official_sample2
single_yes_A
single_no_A
single_yes_E
all_no_D
first_yes_B
last_yes_C
many_yes_E
all_x_no_C
all_o_yes_D
```

実行結果:

```text
SUMMARY: 11 / 11 passed
```

代表的な final reply は以下です。

```text
Yes case:
  final NOP -> RX=0x81 10000001

No case:
  final NOP -> RX=0x80 10000000

After reset:
  end NOP   -> RX=0x00 00000000
```

## Notes

この実装では、FPGA 側を小さな状態付き判定器として使っています。

ABC463B は、入力全体を FPGA に保持する必要がなく、各 `S_i` を逐次処理しながら結果だけを累積できます。
そのため、Shrike-Lite のような小規模 FPGA でも扱いやすい題材でした。

今回の設計では、RP2040 と FPGA の役割を明確に分けています。

```text
RP2040 = 入力整形・制御・表示・テスト
FPGA   = 5bit AND 判定・結果累積
```

この分担により、FPGA 側の回路規模を小さく保ちながら、AtCoder の問題を実機で処理できました。
