# 基盤の出典とライセンス

既存のHOL Light・s2n-bignum・OCaml/opam環境の出典・固定情報・ライセンスは[既存版の記録](../verified-libc-minimal/THIRD_PARTY.md)、[共有する版](deps.lock)、既存版の`opam-switch.export`を参照する。依存のソースやパッケージを通常の検査から更新せず、固定した状態と版を検査する。

`proofs/resource_composition.ml`の状態更新の補助は、固定したs2n-bignumの`common/execution.ml`と`arm/proofs/arm.ml`の手順をもとに、ステップ数を扱う形へ拡張した。元の指定は`Apache-2.0 OR ISC OR MIT-0`であり、当該ファイルにも出典と指定を記す。合成則はHOLで証明し、新しい公理にはしない。

## QEMU

[公式のライセンス説明](https://www.qemu.org/docs/master/about/license.html)では、QEMU本体はGPL version 2、各部分には別の指定があるとしている。実行ファイルやファームウェアをこのリポジトリへ同梱していない。

この実験で使ったのは、既に導入されていたHomebrewの`qemu-system-aarch64` 10.1.0である。[専用の固定情報](isa-backend.lock.json)に上流タグのコミットと実行ファイルのSHA-256を別々に保存する。この実験で配布バイナリをソースから再ビルドしたことや、上流コミットと配布バイナリの対応を証明したことは意味しない。

- [上流の10.1.0リリース](https://github.com/qemu/qemu/releases/tag/v10.1.0)
- [GDB接続と単一ステップの公式説明](https://www.qemu.org/docs/master/system/gdb.html)
- [GNU GDBのリモートプロトコル](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html)

QEMUはHOLのArmモデルを再利用したものではなく、差分検査の別の実行実装として用いる。比較の一致をQEMU・HOL・実機の全状態の同値とは扱わない。実際に比較した状態と未対象の範囲は[実験記録](reports/m3/isa/README.md)に示す。

## 独立した証明再検査の調査

[最小試行の記録](reports/m3/independent-recheck/README.md)で、固定したHOL Lightに含まれるProofrecordingと、[OpenTheory](https://www.gilith.com/opentheory/)の経路を比較する。独立した検査器の配布・導入を達成したとは扱わない。旧記録系の互換性試行は隔離した`build/`の複製で行い、共有する依存のソースを改変しない。
