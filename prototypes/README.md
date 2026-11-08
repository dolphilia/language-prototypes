# 試作言語の一覧

[リポジトリの目次へ](../README.md)

各ディレクトリに、試作言語の仕様、参照実装、サンプル、テストをまとめます。
仕様のみの草案と、実行できる参照実装を区別して記載します。

言語の設計を支える基盤の試作として、[検証済みlibcの最小プロトタイプ](verified-libc-minimal/README.md)も置いています。
macOS arm64で2関数の機械語を証明し、Cからの実物・速度・容量を検査します。

| 言語 | 仕様・使い方 | 参照実装 | サンプル | テスト |
| --- | --- | --- | --- | --- |
| Aya（あや）0.1・仕様草案 | [概要](aya/README.md)・[仕様書](aya/spec.md)・[設計判断](aya/design.md) | 未実装 | 仕様書内のコード例 | 仕様書内の適合性表。実行検証は未実施 |
| Tane（たね）0.1 | [README](tane/README.md) | [tane.py](tane/tane.py) | [カウントダウン](tane/examples/countdown.tane)、[加算](tane/examples/add.tane)、[乗算](tane/examples/multiply.tane) | [test_tane.py](tane/tests/test_tane.py) |

[検証済みlibcの発展版](verified-libc-evolution/README.md)はM1〜M3と[全体監査](verified-libc-evolution/reports/audit.md)を完了した。独立した証明再検査の機能は未達であり、調査の完了と区別する。
