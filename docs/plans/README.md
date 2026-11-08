# 実装計画

[リポジトリの目次へ](../../README.md) · [調査・設計メモ](../notes/README.md)

調査や設計を、小さなプロトタイプとして検証するための計画を置きます。計画ごとにディレクトリを作り、対象範囲、依存、実装手順、完了条件を記録します。

| 計画 | 対象 | 状態 | 作成日 |
| --- | --- | --- | --- |
| [検証済みlibcの発展](verified-libc-evolution/README.md) | 証明合成と任意長コピー、呼び出し条件、重複コピー、リンク、モデルの差分検査、資源と探索の3段階 | 完了・[記録](../../prototypes/verified-libc-evolution/reports/progress.md) | 2026-11-08 |
| [検証済みlibcの最小プロトタイプ](verified-libc-minimal/README.md) | AArch64上の`memcpy`・`memset`、命令マクロ、機械語の証明、成果物の照合、速度・容量の評価 | 完了・[監査結果](../../prototypes/verified-libc-minimal/reports/audit.md) | 2026-11-08 |

