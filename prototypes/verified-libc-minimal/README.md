# 検証済みlibcの最小プロトタイプ

[実装計画](../../docs/plans/verified-libc-minimal/README.md) · [完了監査](reports/audit.md) · [実施記録](reports/progress.md) · [実測値](reports/measurements.md) · [残る信頼](reports/trust.md)

macOS arm64上で、2関数の実際の機械語をHOL Lightで検査する試作。
基本版はバイトループ、最適化は長さ8・両アドレスが8バイト整列したコピーだけ。
最適化版と埋め込みの命令本体は計92バイトで、スタック・ヒープ・実行時の証明処理を使わない。
最新の全検査の状況は[実施記録](reports/progress.md)を参照。

## 現在の環境

対象はmacOS arm64（arm64eを除く）。OCaml 5.1.0、opam、XcodeのClangとSDK、Python 3.9以降、Makeを使う。
HOL Lightとs2n-bignumの依存はプロジェクト内に置く。
確認した機器はM1 Pro、macOS 15.6.1、Apple Clang 17.0.0、SDK 26.2。

```sh
# 依存取得・構築を行う、明示的なネットワーク操作
python3 prototypes/verified-libc-minimal/tools/setup.py

# 新規の証明、成果物、Cの試験、意図した破壊の拒否
make -C prototypes/verified-libc-minimal verify

# verifyの後で速度・容量を測る
make -C prototypes/verified-libc-minimal measure
```

`setup.py`はSDKを明示し、システムOCamlのCコンパイラにApple Clangを使わせる。
依存の取得・導入を通常の検証から自動実行しない。システムのswitchは変更せず、
`.deps/`の隔離したopam環境を使う。コミットと全パッケージの版は`deps.lock`と
`opam-switch.export`へ固定する。証明環境の読み込みと破壊試験には数分ずつかかる。

`make native`は実機の試験だけ、`make p0`は最初の接続例だけで、全体の検査を代替しない。

## 呼び出し条件

宣言は[include/vp_memory.h](include/vp_memory.h)。通常のlibcは置き換えない。

```c
void *vp_memcpy(void *dst, const void *src, size_t n); // 選択した最適化版
void *vp_memcpy_scalar(void *dst, const void *src, size_t n); // 比較用基本版
void *vp_memset(void *dst, int c, size_t n);
```

- 非NULLの通常RAMを渡す。必要な権限を呼び出し中維持し、並行した変更・解放、MMIOを扱わない。
- アドレスと長さの加算は折り返さず、コピーの入力・出力は重複しない。出力は実行コードと重ならない。
- `n==0`はデータアクセスを行わず元の`dst`を返す。NULLを許す契約は含まない。
- 埋め込みは`int`の低8ビットを使う。引数レジスタの不要な上位ビットへ特定の値を要求しない。
- Apple arm64の保存レジスタとSPを保存する。変更範囲はPC、X3、コピーのX4、フラグ、イベント、出力領域だけ。

C規格の全要件を満たすlibcや、Cプログラム全体の形式検証とは主張しない。

## 検査すること

[proofs/specs.ml](proofs/specs.ml)の公開契約は生成器から独立している。
事前条件を満たす任意の64ビット長に対し、結果、戻り値、有限ステップでの復帰、
許可した部分以外の保存を証明する。ループでは処理済み長さ`i`と`n-i`を使う。
途中の読み書きはモデルのイベントで別に追い、最終状態の保存だけから推測しない。
[proofs/boundaries.ml](proofs/boundaries.ml)では、ゼロ長でデータアクセスがないイベント列と、
高速経路のビット検査が8バイト整列を表すことも独立した定理で確認する。

| 実装 | 機能・終了・保存 | アクセス範囲 |
| --- | --- | --- |
| 基本版コピー | `VP_MEMCPY_SCALAR_CORRECT` | `VP_MEMCPY_SCALAR_ACCESSES` |
| 埋め込み | `VP_MEMSET_CORRECT` | `VP_MEMSET_ACCESSES` |
| 最適化版コピー | `VP_MEMCPY_CORRECT` | `VP_MEMCPY_ACCESSES` |

[generator/main.ml](generator/main.ml)が固定レジスタのマクロからアセンブリを作る。
CopyByte、FillByte、Copy8を別々に証明し、ループの添字付きの形も検査する。
展開した関数は、その文脈で改めて命令の意味から検査する。最適化版に埋め込む
基本版は関数定理を再利用する。汎用の証明合成器やレジスタ割り当て器は作らない。

1関数1オブジェクト、コードの再配置・外部参照・定数表なしに限定する。
HOL LightがMach-Oの命令バイトをリテラルと照合し、その命令列の定理を作る。
Pythonがリンク後のシンボルの開始から終了までの全バイトを抽出して比較し、
LLVMによる表示とも位置を照合する。thin arm64以外や不正な範囲を拒否する。
抽出処理自体は未検証の信頼基盤に含む。

証明処理は新規プロセスで行い、期待した閉じた命題と、追加公理がないことを確認する。
例外後に対話処理が継続しても成功扱いしない。毎回結果を消して新しいnonceと照合し、
検査中にソース・成果物が変わった場合も中断する。

Cの試験は境界長、16通りずつの入力・出力のずれ、固定シードの乱数、負の埋め込み値、
入力保存・戻り値・番兵・ガードページ・保存レジスタを調べる。
試験範囲と、定理が扱う任意の長さは区別する。

破壊試験は戻り値・保存レジスタ・終了条件・余分な読み書き・短い高速経路を変更する。
オブジェクトとHOL側の期待命令を一緒に更新した上で、元の契約の証明が失敗することを調べる。
追加公理、開いた定理、違う命題、定理欠落、例外後の継続、成果物改変も拒否する。

`build/verification.json`は最新の全検査の時刻・定理・nonce・入力ハッシュを保存する。
証明ログ・生成物・逆アセンブルは`build/`へ置き、Git管理しない。
性能の条件と生データは[測定方法](benchmarks/method.md)と[測定報告](reports/measurements.md)にある。
この機器では整列済み8バイトコピーが改善し、多くの他の長さではlibcに届かない。
ケースごとに判定し、実用libcの完成とは報告しない。

依存の出典・ライセンスは[THIRD_PARTY.md](THIRD_PARTY.md)を参照。

## 次に検証したいこと

[発展方向と次の実験](../../docs/notes/verified-libc-next-experiments.md)に、部品の証明合成、
任意長の8バイトループ、呼び出し条件の導出、重複コピー、リンク、モデルと実機の対応を整理した。
[発展版の実装・検証計画](../../docs/plans/verified-libc-evolution/README.md)に段階・成果物・通過条件を具体化した。
発展版は計画済み・実装未着手であり、現在の保証範囲や測定結果へ含めない。
