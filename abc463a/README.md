# ABC463A Shrike 実装仕様

ABC463A を Shrike-Lite 上で実装するための通信仕様、FPGA 側処理仕様、動作確認結果をまとめる。

## 問題

入力として `X`, `Y` が与えられる。

`X:Y` が `16:9` であれば `Yes`、そうでなければ `No` を返す。

判定式は以下とする。

```text
X * 9 == Y * 16
```

FPGA 上では乗算を避け、以下の式で判定する。

```text
(X << 3) + X == (Y << 4)
```

`X`, `Y` は `1000` 以下のため、各値は 10bit で表現する。

## 利用するSPI通信

SPI通信は、Shrike 公式サンプルの `gpio_extender_8bit` をベースにする。

RP2040 から FPGA に対して MOSI でコマンドとデータを送信し、FPGA から RP2040 に対して MISO で応答を返す。

## RP2040 と FPGA の役割

### RP2040

* テストデータを保持する
* SPI で `X`, `Y` を FPGA に送信する
* FPGA から判定結果を読み取る
* 判定結果を `Yes` / `No` として表示する
* 1回の処理にかかった時間を測定する

時間測定は、最初の `MOSI_RESET` 送信直前から、最後の `MOSI_RESET` 送信直後までの経過時間とする。

### FPGA

* SPI で受信した `X` を保持する
* `SET_Y` 受信時に、受信中の `Y` と保存済みの `X` を用いて判定する
* 判定結果を MISO で返す

## MOSI フレーム仕様

MOSI は 16bit の論理フレームとする。

```text
[15:13] CMD   3bit
[12:10] AUX   3bit
[9:0]   DATA  10bit
```

実際の SPI 通信では 8bit ずつ送信する。

```text
byte0 = { CMD[2:0], AUX[2:0], DATA[9:8] }
byte1 = { DATA[7:0] }
```

FPGA 側では、1バイト目を受信した時点で `CMD`, `AUX`, `DATA[9:8]` を一時保持し、2バイト目を受信した時点で 10bit の `DATA` を完成させる。

すべてのコマンドは 2バイト固定フレームとして送信する。`NOP` や `RESET` も例外ではなく、2バイトで送信する。

例:

```text
NOP   = 0x00 0x00
RESET = 0xE0 0x00
```

## CMD 定義

```text
000 NOP
001 SET_X
010 SET_Y
101 DEBUG
111 RESET
```

### NOP

現在の応答状態を読み取る。

`reply_ready == 1` のときは、MISO に `REPLY` を返す。
`NOP` 処理後、`reply_ready` は `0` に戻り、次回以降は `WAIT` を返す。

### SET_X

`DATA` を `X` として FPGA 内部の `x_reg` に保存する。

### SET_Y

`DATA` を `Y` として扱う。

`SET_Y` を受信した時点で `X`, `Y` が揃ったものとし、受信中の `Y` と保存済みの `X` を用いて判定結果を準備する。

### DEBUG

デバッグ用。現在の実装では未使用。

### RESET

内部状態を初期化する。

## MISO 応答仕様

MISO は 8bit とする。

```text
[7]   REPLY / WAIT
[6:1] STATUS
[0]   RESULT
```

通常応答は以下とする。

```text
0x00 = WAIT
0x80 = REPLY + No
0x81 = REPLY + Yes
```

`RESULT` が `1` の場合は `Yes`、`0` の場合は `No` とする。

`REPLY` は one-shot とし、1回読み取られた後は `WAIT` に戻る。

実機確認では、`NOP_REPLY` の2バイト両方で同じ応答が読めることを確認した。

```text
RX=[0x81, 0x81]  REPLY + Yes
RX=[0x80, 0x80]  REPLY + No
```

RP側コードでは、タイミングずれへの保険として `rx[0] | rx[1]` で応答を拾う。

## 通信シーケンス

1回の判定処理は以下の流れとする。

```text
MOSI      MISO      内容
RESET     WAIT      内部状態を初期化
NOP       WAIT      RESET後の確認
SET_X     WAIT      Xを送信
SET_Y     WAIT      Yを送信し、判定結果を準備
NOP       REPLY     判定結果を読み取る
NOP       WAIT      REPLYが消えたことを確認
RESET     WAIT      次の処理に備えて初期化
```

最小シーケンスは以下でもよい。

```text
RESET
SET_X
SET_Y
NOP
```

ただし、実機確認では状態確認のために `RESET` 後の `NOP` と、`REPLY` 後の `NOP_CLEAR` を実行している。

## 時間測定

RP側 Python コードでは、1回の処理にかかった時間を測定する。

測定範囲は以下とする。

```text
開始: 最初の MOSI_RESET を送信する直前
終了: 最後の MOSI_RESET を送信した直後
```

測定対象には以下が含まれる。

* 初期 `MOSI_RESET`
* RESET後確認用 `NOP`
* `SET_X`
* `SET_Y`
* 結果読み取り用 `NOP`
* REPLY消去確認用 `NOP`
* 最後の `MOSI_RESET`

現在の MicroPython テストコードでは、1ケースあたりおおむね `7.2 ms` から `7.7 ms` 程度だった。

この時間には、SPI転送だけでなく、Python側の関数呼び出し、CS制御、ログ出力、フレーム間ウェイトなども含まれる。

## FPGA 内部レジスタ

最低限、以下のレジスタを用意する。

```text
state          受信FSMの状態
pending_cmd    1バイト目で受信したCMD
pending_aux    1バイト目で受信したAUX
pending_data   DATA[9:8]

x_reg          Xの保存用

reply_ready    応答可能フラグ
spi_tx_data    MISO送信用データ
```

`x_valid`, `y_valid` は持たない。

また、現在の実装では `y_reg` も持たない。
`SET_Y` の lower byte を受信した時点で、`pending_data` と `spi_rx_data` から `Y` を作り、その場で判定する。

## 受信FSM

SPI は 8bit 単位で受信するため、FPGA 側では 2状態FSMで 16bit フレームを扱う。

```text
ST_IDLE
  upper byte を待つ
  CMD, AUX, DATA[9:8] を保持する
  ST_WAIT_LOW に遷移する

ST_WAIT_LOW
  lower byte を待つ
  DATA[7:0] を受信する
  10bit DATA を完成させる
  pending_cmd に応じて処理する
  ST_IDLE に戻る
```

upper / lower の区別は CMD ではなく、FSM の状態で行う。

## 判定処理

`SET_Y` 受信時に、受信中の `Y` を用いて以下を判定する。

```text
reply_result = ((x_reg << 3) + x_reg) == (rx_data14 << 4)
```

ここで `rx_data14` は、2バイトMOSIフレームから復元した 10bit DATA を 14bit に拡張した値である。

```text
rx_data14 = {4'd0, pending_data, spi_rx_data}
```

`SET_Y` 処理では、判定結果を `spi_tx_data` に設定し、`reply_ready` を `1` にする。

```text
spi_tx_data <= {1'b1, 6'd0, reply_result}
reply_ready <= 1
```

`NOP` 受信時に `reply_ready == 1` であれば、MISO に `REPLY` が返る。

`NOP` 処理後、`reply_ready` は `0` に戻り、`spi_tx_data` は `0x00` に戻る。

## 動作確認結果

`abc463a.bin` を Shrike に書き込み、RP2040 側の `abc463a_spi_test.py` からSPI通信で動作確認した。

確認したテストケースは以下。

|    X |   Y | Expected | FPGA |
| ---: | --: | :------: | :--: |
|   16 |   9 |    Yes   |  Yes |
|   32 |  18 |    Yes   |  Yes |
|    4 |   3 |    No    |  No  |
| 1000 | 562 |    No    |  No  |
| 1000 | 563 |    No    |  No  |
|  800 | 450 |    Yes   |  Yes |
|  234 | 108 |    No    |  No  |
|  108 | 192 |    No    |  No  |

すべてPASS。

`NOP_REPLY` では、MISOの2バイト両方で同じ応答が確認できた。

```text
0x81, 0x81 : REPLY + Yes
0x80, 0x80 : REPLY + No
```

`NOP_CLEAR` では `0x00, 0x00` が返り、one-shot REPLY が消えることを確認した。

## DEBUG

現在の実装では `DEBUG` は未使用。

通信や状態遷移の確認が必要になった場合、`AUX` または `STATUS` を用いて内部状態を返す。
