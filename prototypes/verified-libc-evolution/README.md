# 検証済みlibcの発展版

[実装計画](../../docs/plans/verified-libc-evolution/README.md) · [実施記録](reports/progress.md) · [要件と証拠](reports/requirements.json) · [全体の監査](reports/audit.md)

状態: **M1・M2・M3と全体の監査を完了**。各段階の正しさ・実物・試験・評価をそろえ、`verify-all`で再実行した。独立した証明再検査の機能は未達であり、E6bは実現性調査として区別する。

実際のarm64機械語から、独立した公開契約の機能・有限復帰・保存・途中アクセスをHOL Lightで検査する。生成器やコンパイラを、ライブラリの正しさを与える公理にはしない。期待命題、空の仮定、許可した基礎公理、入力とバイト列を照合し、新規プロセスのnonceがそろわなければ受理しない。

| 単位 | 内容と結果 |
| --- | --- |
| M1 | [合成と任意長コピー](reports/m1/audit.md)。RETなしの部品、親の合成、元と同じ公開契約。コピー76・埋め込み28で104バイト |
| M2 | [領域・重複・直接呼び出し](reports/m2/audit.md)。memmove、2配置のリンク、実行時検査から入口条件を導く呼び出し元。呼び出し元の専用枠16バイト |
| M3 | [命令の有限比較](reports/m3/isa/README.md)、[再検査の調査](reports/m3/independent-recheck/README.md)、[資源の定理](reports/m3/resources/README.md)、[5候補の探索](reports/m3/search/README.md) |

探索では`ve_opt_u2_mov`を固定した。コピー88・埋め込み28で116バイト。別データの確認で整列済み64・256バイトは元のM1より高速、4096バイトの差は不明、8バイトは約2.5倍遅かった。速度・容量の優位、正しさの証明、調査の未達は別に報告する。M2は元のM1コピーへ結合したままで、選択した候補へ差し替える際はリンク後の再証明が必要である。

## 環境と導入

対象はmacOS / thin arm64 / Mach-O / Apple ABIで、arm64eは対象外。検査環境はmacOS 15.6.1、Apple Clang 17、SDK 26.2、Python 3.14.4、OCaml 5.1.0。CPU名を環境が返さない測定では不明と診断を残し、推定しない。

HOL Light・s2n-bignum・opam環境は、隣の`verified-libc-minimal/.deps/`を共有する。[deps.lock](deps.lock)と既存版の`opam-switch.export`の版・コミット・変更の有無を毎回検査する。既存版のソース、契約、保存済みの報告は発展版から上書きしない。導入は[既存版の手順](../verified-libc-minimal/README.md)の`tools/setup.py`を明示的に実行する。通常の検査はネットワークへ接続しない。

比較用の旧オブジェクトがまだない場合は、固定したopam環境から次の生成対象だけを準備する。旧版の保存済み報告を更新する`verify`・`measure`を、この準備のために実行する必要はない。

```sh
# リポジトリのルートから。依存の導入は別の明示的な操作。
VP_BASE="$PWD/prototypes/verified-libc-minimal"
OPAMROOT="$VP_BASE/.deps/opam-root" opam exec --switch "$VP_BASE/.deps/ocaml" -- \
  make -C "$VP_BASE" build/vp_memcpy_scalar.o build/vp_memcpy.o \
  build/vp_memset.o build/probe_ret.o .deps/s2n-bignum/arm/generic/word_max.o
```

M3のQEMUは[isa-backend.lock.json](isa-backend.lock.json)の10.1.0・実行ファイルSHA-256へ別に固定する。この実験では既存のHomebrewバイナリを利用し、ソースから再ビルドしていない。同じファイルがない場合、固定情報を無視して別の版を受理しない。別のビルドや版を使う場合は、新しい固定情報と環境で再検査する必要がある。上流コミットと配布バイナリのソース対応を証明したとも扱わない。[出典・ライセンス](THIRD_PARTY.md)を参照する。

## 実行

通常は全体の入口を使う。各単位の実際のMake入口と新規の証明・実機検査を実行し、入力が変わった評価は現在の成果物で更新する。証明環境を何度もロードするため、全体は1時間以上を要する。

```sh
make -C prototypes/verified-libc-evolution verify-all
```

個別に進める場合は次を使う。`verify`の証明通過と、測定を含む単位全体の完了は監査で区別する。

```sh
make -C prototypes/verified-libc-evolution verify-m1
make -C prototypes/verified-libc-evolution measure-m1
make -C prototypes/verified-libc-evolution audit-m1

make -C prototypes/verified-libc-evolution verify-m2
make -C prototypes/verified-libc-evolution measure-m2
make -C prototypes/verified-libc-evolution audit-m2

make -C prototypes/verified-libc-evolution verify-m3
make -C prototypes/verified-libc-evolution measure-m3
make -C prototypes/verified-libc-evolution audit-m3
```

`PYTHON=/opt/homebrew/bin/python3`等をMakeへ渡してPython 3.14の実行ファイルを選べる。`verify-all`は子のMakeにも同じPythonを渡す。E6bの隔離した試行はPython 3.14で確認している。

M2は各段階の証明を終了してから、入力の変わった測定だけを更新する。測定中に別の証明プロセスを動かさない。M3は探索結果と選択を固定し、確認結果を見て選び直さない。再測定の各試行は`reports/m3/search/confirmations/`へ保存する。全ケース・生データ・順序・PID・四分位を残し、完全に冷えたキャッシュや全CPUでの最適性を保証しない。

保存した証拠は絶対パスの入力と`build/`内の測定実行ファイルを参照する。同じチェックアウトでの再実行を検証している。別ディレクトリへの移設や`build/`を削除した状態から、保存済みの探索・選択・測定を復元する手順は未検証である。過去の成功記録だけを受理に流用しない。

部分検査の`check-e0`・`check-composition`・`native`と、修正費用だけの`proof-costs`も残す。これらだけで全体の完了にはしない。

選択したライブラリは`build/selected/ve_opt_u2_mov.o`と`ve_selected.h`へ用意する。実行時に証明器をリンクしない。通常のlibc全体の置き換えではなく、非NULL・有効な通常RAM・非折り返し・コピーの非重複等の公開契約が必要である。

## 記録と保証の境界

[全体の監査](reports/audit.md)と[信頼の供給元](reports/trust-boundaries.md)で、論理の条件、物理RAM・OS・ISAの根、検査器・ローダー・測定器を分ける。E6aは有限の比較で、全CPUとの同値定理ではない。E7aはモデルの命令数・データ量で、秒数の上限ではない。E6bは旧記録版の非互換を再現した調査で、独立したカーネルでの証明再生は未達である。

生成物・詳細な証明ログはこの版の`build/`、受理した根拠と全測定値は`reports/`へ置く。統合前の初回の記録は[履歴](reports/history/pre-final-integration-20261109/README.md)へ保存した。履歴の古いハッシュを現在の成功に書き換えない。
