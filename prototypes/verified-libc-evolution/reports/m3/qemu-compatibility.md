# E6aの事前互換性確認

> RETとロード／ストアだけを試した初回の互換性確認の記録。現在の全対象形式の結果は[命令の差分検査](isa/README.md)を参照する。本文の未完了表示はこの準備時点の状態である。

2026-11-08。**全命令の差分検査は未完了**。M1の命令と契約を固定した後段の準備である。

QEMU 10.1.0のTCG、`virt`、`cortex-a72`、ゲストRAM 128MiBで、標準入出力のGDB Remote Serial Protocolから停止・レジスタ設定・メモリ設定・1命令実行・結果取得を確認した。画面、シリアル、モニター、NICは無効とし、外部接続やゲストOSは使っていない。既存の実行ファイルを使い、追加の導入は行っていない。

- RET: PC `0x40000000`から指定したX30の`0x40000010`へ進んだ。
- LDR: `11 22 33 44 55 66 77 88`を読み、X4が`0x8877665544332211`となった。
- STR: 同じ8バイトを出力先へ保存した。
- バイナリの実体・SHA-256、CLI、初期CPSR、target XML、応答を[生データ](qemu-compatibility.json)へ保存した。

これは手で設定した期待結果との互換性確認であり、HOLとの比較や、形式ごとの32境界例・256固定シード例を実行したものではない。再実行可能な正式ツールへの移行、上流のコミットと導入情報の固定、定義された状態の対応、全形式と安全な実機例が次の作業になる。QEMU自体の正しさや、ISAと全CPUの同値も証明していない。

QEMUのGDB接続はレジスタ・メモリの観測と単一命令実行を提供する。[QEMU公式のGDB説明](https://www.qemu.org/docs/master/system/gdb.html)を参照する。レジスタの送受信と並びは[GNU GDBのパケット仕様](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html)と、実際のtarget XMLから定める。機械とCPUの選択は[virtの公式説明](https://www.qemu.org/docs/master/system/arm/virt.html)を参照する。

QEMUは[別のAArch64命令実装](https://github.com/qemu/qemu/blob/v10.1.0/target/arm/tcg/translate-a64.c)を持つ。今回はHOLモデルの関数を再利用するバックエンドではなく、独立した実装の有限比較として検討する。実行環境・物理CPU・仕様解釈への共通の信頼は残る。

ライセンスはインストール済みの`LICENSE`と`COPYING`で確認した。エミュレータ全体はGNU GPL version 2、部分ごとの互換ライセンスもある。ファームウェアは別プログラム・別ライセンスとして区別される。この試作ではQEMU本体やファームウェアをリポジトリへ複製していない。
