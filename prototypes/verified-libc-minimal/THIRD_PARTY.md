# 再利用する証明基盤

依存のソースは`.deps/`へ明示的に取得し、Git管理しない。取得した版は
[deps.lock](deps.lock)、OCamlパッケージとそのソースのメタデータは
[opam-switch.export](opam-switch.export)に記録する。

- HOL Light: John Harrisonほか。MITライセンス。依存内の`LICENSE`を参照。
- s2n-bignum: Amazon.com, Inc. or its affiliatesほか。対象の共通・AArch64証明コードは
  Apache-2.0 / ISC / MIT-0の選択ライセンス。各ファイルのSPDX表示と`LICENSE`を参照。
- OCamlパッケージ群: 各パッケージのライセンスとソース情報はopamのメタデータを参照。

本試作はs2n-bignumのAArch64モデル、Mach-O取り込み、プログラム論理、証明タクティックを
利用する。自作の関数の正しさを、同ライブラリの名称や既存の暗号関数の証明だけから
推論するものではない。自作の各命令列について別に証明する。
