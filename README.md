# shrike-atcoder

Shrike-Lite を使って AtCoder の問題を解く実験用リポジトリです。

RP2040 と 1120-LUT FPGA を組み合わせ、通常はソフトウェアで解く競技プログラミングの問題を、できる範囲でハードウェア寄りに実装します。

## 目的

このリポジトリでは、AtCoder の問題を題材として、以下を試しています。

* RP2040 単体での MicroPython 実装
* RP2040 と FPGA 両方を利用した実装

  * RP2040 から FPGA への SPI 通信
  * FPGA 側での判定回路・FSM 実装
  * RP2040 と FPGA の役割分担
  * 小規模 FPGA で表現できる処理範囲の確認

Shrike-Lite 上で「問題をどのようにハードウェア化するか」を試すことを主な目的としています。

## 使用環境

### ハードウェア

* Shrike-Lite

  * RP2040
  * Renesas FPGA 1120 LUT

### ソフトウェア

* Renesas Forge / Verilog
* Thonny / MicroPython

RP2040 ⇔ FPGA 間の SPI 通信は、Shrike 公式サンプルの `gpio_extender_8bit` をベースにしています。

## 実装方針

Shrike-Lite は小規模 FPGA であるため、すべてを FPGA 側で処理するのではなく、RP2040 と FPGA の役割分担を重視します。

基本方針は以下です。

```text
RP2040:
  入力保持
  テストケース管理
  SPI通信
  結果表示
  複雑な制御

FPGA:
  単純な判定
  小さなFSM
  レジスタ保持
  シンプルな並列処理
```

## bitstream について

動作確認できた実装については、各問題ディレクトリ内の `bitstream/` に FPGA 書き込み用の `.bin` ファイルを置く場合があります。

## 注意

このリポジトリは学習・実験用です。

AtCoder の通常解法として効率的であることよりも、Shrike-Lite 上でどのように実装できるかを重視しています。
