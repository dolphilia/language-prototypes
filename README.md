# newlang

小さな仕様と理解しやすい処理系を目指す、プログラミング言語の設計・試作をまとめます。
各言語の仕様、実装、サンプル、テストは `prototypes/` 内に配置します。
調査したことや設計を考えるためのメモは `docs/notes/` にまとめます。

## 目次

- [Aya（あや）0.1 — 調査に基づく言語仕様案](prototypes/aya/README.md)
- [Ayaの言語仕様書](prototypes/aya/spec.md)
- [Ayaの設計判断と検証計画](prototypes/aya/design.md)
- [調査・設計メモ](docs/notes/README.md)
- [所有権とその先 — メモリ管理から権限・並行性・効果へ](docs/notes/ownership-and-beyond.md)
- [GhostCell詳解 — データとアクセス権限を分離する](docs/notes/ghostcell.md)
- [OxCamlのモード詳解 — 値の使い方を複数の軸で追跡する](docs/notes/oxcaml-modes.md)
- [Hyloと可変値意味論 — 値の独立性を保ちながら、その場で変更する](docs/notes/hylo-mutable-value-semantics.md)
- [unsafeの発展 — 操作の細分化から、権限・証明・隔離へ](docs/notes/unsafe-and-beyond.md)
- [unsafeを置き換えた後に、何が残るか](docs/notes/what-remains-of-unsafe.md)
- [外部世界との接続だけが残る場合のunsafe](docs/notes/unsafe-as-external-contract.md)
- [試作言語の一覧](prototypes/README.md)
- [Tane（たね）0.1 — 言語仕様と設計](prototypes/tane/README.md)
- [Taneの参照実装](prototypes/tane/tane.py)
- [Taneの実行例](prototypes/tane/README.md#実行例)
- [Taneの実行・テスト手順](prototypes/tane/README.md#処理系)

## 試作言語

| 言語 | 概要 | ドキュメント |
| --- | --- | --- |
| Aya（あや）0.1 | 所有する値、権限付き共有領域、モード、効果、外部契約を組み合わせる仕様草案。未実装。 | [概要](prototypes/aya/README.md)・[仕様書](prototypes/aya/spec.md)・[設計判断](prototypes/aya/design.md) |
| Tane（たね） | 自然数の変数と4種類の文だけを持つ、カウンタベースの言語。 | [仕様・使い方](prototypes/tane/README.md) |

## 最初の実行

Python 3を使い、リポジトリルートから次のコマンドを実行します。

```sh
python3 prototypes/tane/tane.py prototypes/tane/examples/countdown.tane
```

`3`、`2`、`1` がそれぞれ別の行に出力されます。
