# M3の完了監査

**E6a・E6bの調査・E7a・E7bの実装と評価、M3のコマンド統合を完了と判定する。** 独立した証明再検査の機能は未達であり、調査の完了と区別する。

| 段階 | 確認した根拠 |
| --- | --- |
| E6a | [有限の命令比較](isa/README.md)。20形式・33エンコーディング、各形式32境界例・256シード例。QEMUと実機の各5,760件、46,080件の閉じた検査。未解決の不一致なし |
| E6b | [実現性調査](independent-recheck/README.md)。2経路を比較し、一つをRETの出力へ試行。固定環境での旧記録版の非互換を再現。出力・正例再生・改変拒否は未達 |
| E7a | [資源の定理](resources/README.md)。基本版・長さ8専用版・M1の任意長と全経路のモデルステップ数、データバイト数、追加・削除の反例。20件 |
| E7b | [有限の探索と確認](search/README.md)。固定5候補、正常4の機能・復帰・保存・アクセス・資源、不正1の具体的な違反。集合の新規51件、選択後の別プロセス21件。固定後は別データ・別順序で各7プロセスの確認 |
| 統合 | [新規実行](verification.json)。46,172回の検査、46,151の異なる検査名。追加公理なし。M1・M2の完了、開始・終了の入力、各段階の新しいnonceを照合 |

検査名の種類は数学的に異なる命題の同値類の数ではない。有限の試験、条件付きの定理、測定、調査の未達を分ける。全CPUでのISA同値、秒数の上限、全入力で最速という結果ではない。

```sh
make -C prototypes/verified-libc-evolution verify-m3
make -C prototypes/verified-libc-evolution measure-m3
python3 prototypes/verified-libc-evolution/tools/audit_m3.py
```
