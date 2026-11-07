# unsafeの発展 — 操作の細分化から、権限・証明・隔離へ

[メモの一覧へ](README.md) · [所有権とその先](ownership-and-beyond.md) · [GhostCell詳解](ghostcell.md) · [OxCamlのモード詳解](oxcaml-modes.md) · [Hyloと可変値意味論](hylo-mutable-value-semantics.md)

調査日: **2026-11-07**

更新日: **2026-11-07**（置き換えた後に残るものについての考察へのリンクを追加）

続く考察: [unsafeを置き換えた後に、何が残るか](what-remains-of-unsafe.md)。安全な記述を増やした先の限界と、外部との契約・信頼の根を検討する。

対象: `unsafe`の責任を詳しく表す言語機能、危険な操作を減らす型・API、安全性を検査・証明する研究、実行時に被害を隔離する実装。Rustに限らず、D、Swift、Checked C、F*、WebAssembly、CHERIなども扱う。

**こうした研究・実装は多数存在する。** 大きな方向は、操作を分類すること、安全条件を明記すること、権限や状態を型に移すこと、条件を機械で検査すること、失敗の影響を閉じ込めることである。これらは組み合わせられる。

安定した機能、実験的な機能、RFC、議論、研究用処理系を区別して記す。`text`ブロックは概念や擬似構文であり、そのまま使える言語機能ではない。研究の説明と、後半の設計に関する考察も分ける。

## 目次

- [全体像](#1-unsafeはどの方向へ発展しているか)
- [unsafeの意味と問題の所在](#2-unsafeの意味と問題の所在)
- [責任の境界を詳しくする](#3-責任の境界を詳しくする言語機能)
- [操作の種類と安全条件を指定する](#4-操作の種類と安全条件を指定する)
- [型と権限で必要なunsafeを減らす](#5-型と権限で必要なunsafeを減らす)
- [許される実行を定義する](#6-許される実行を定義する)
- [検査から形式証明へ](#7-検査から形式証明へ)
- [効果と外部資源への権限](#8-効果と外部資源への権限を追跡する)
- [DとSwiftの言語機能](#9-dとswiftの言語機能)
- [他言語との境界を改善する](#10-他言語との境界を改善する)
- [ハードウェアによる発展](#11-ハードウェアによる発展)
- [研究と実装の位置づけ](#12-研究と実装の位置づけ)
- [言語設計への示唆](#13-このリポジトリの言語設計への示唆)
- [資料と確認範囲](#14-資料と確認範囲)

## 1. unsafeは、どの方向へ発展しているか

このメモでは、関連する取り組みを次のように整理する。この分類は、個々の研究が共通のロードマップを採用しているという意味ではない。

| 方向 | 詳しくしたいこと | 代表例 |
| --- | --- | --- |
| 責任の分離 | 誰が条件を保証するか | Rustの`unsafe fn`と`unsafe {}`、Dの`@trusted` |
| 操作の分類 | どの危険な操作を許すか | Granular Unsafe Blocksの議論 |
| 条件の構造化 | 何が成立していれば安全か | Safety Tags、unsafe reasonsの議論 |
| 状態・権限の型付け | どの対象を、いつ、どう扱えるか | `MaybeUninit`、`UnsafeCell`、GhostCell、typestate |
| 意味論の精密化 | どんな実行が未定義動作か | Strict Provenance、Stacked Borrows、Tree Borrows |
| 検査・証明 | 必要な条件は実際に成立するか | Miri、Kani、RustBelt、RefinedRust、Low* |
| 効果・資源権限 | 何を実行し、外部の何に触れるか | Cargo Scan、cap-std |
| 境界・隔離の強化 | 危険な実装を外部へどう接続するか | Swiftのsafe interop、Checked C、RLBox、WebAssembly |
| ハードウェア支援 | 許可外のアクセスを実行時に止めるか | CHERI、Mon CHÉRI |

単に`unsafe`を細かいキーワードへ分割するだけでなく、**人が文章で説明していた責任の一部を、型、注釈、論理、実行時の境界へ移す**発展がある。

## 2. unsafeの意味と問題の所在

### 2.1 Rustのunsafeは、借用検査をすべて無効にするものではない

Rustでは、生ポインタの参照外しやunsafe関数の呼び出しなど、通常の安全な部分では許可されない操作を明示する。`unsafe`の中でも、通常の参照の型検査や借用検査は続く。

また、`unsafe`と書いても、未定義動作が許されるわけではない。実行が安全条件を満たす責任を、言語の通常の検査だけでは引き受けられないという境界である。[Rust Referenceのunsafe](https://doc.rust-lang.org/reference/unsafe-keyword.html)、[Unsafe Rustの説明](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html)

### 2.2 「条件を要求する側」と「条件を満たす側」がある

| 記述 | 主な意味 |
| --- | --- |
| `unsafe fn` | 呼び出し側が守る追加の安全条件を持つ |
| `unsafe { ... }` | 内部の操作に必要な条件を、この文脈で満たしていると主張する |
| `unsafe trait` | 実装者が守る追加の条件を持つ |
| `unsafe impl` | その実装がtraitの条件を満たすと主張する |

ここでいう「主張」は、通常のRustコンパイラがその内容をすべて証明したという意味ではない。たとえば、前の実行時検査、データ構造の不変条件、呼び出し元の契約などが根拠になる。[証明義務の導入と充足を分けるRFC 2585](https://rust-lang.github.io/rfcs/2585-unsafe-block-in-unsafe-fn.html)

### 2.3 ブロックの外に、安全性の根拠がある

たとえば独自の配列が、長さ`len`と容量`capacity`を持つとする。

```text
安全な要素アクセスの前提:
  len <= capacity
  先頭からlen個の要素は初期化済み
  バッファはまだ解放されていない

unsafeなアクセス:
  上の前提を利用して、チェックを省いた操作を行う
```

`len`へ代入する行自体に`unsafe`がなくても、そこで不変条件を壊せば、後のunsafe操作が破綻する。したがって、レビューすべき範囲は、色の付いたブロック内だけとは限らない。状態を変更できる同じモジュールの安全なコードも関係する。[Rustonomicon: Working with Unsafe](https://doc.rust-lang.org/nomicon/working-with-unsafe.html)

### 2.4 メモリ安全性、正しさ、権限は別の問い

メモリを壊さずに、間違った計算や不要なファイル削除を行うプログラムもある。逆に、目的の計算が合っているように見えても、無効なポインタを使っていれば安全ではない。

以下では、Rustの`unsafe`が扱う未定義動作の防止に加え、その周辺にある効果・権限・隔離も調べる。ただし、これらを同じ保証として扱わない。

## 3. 責任の境界を詳しくする言語機能

### 3.1 unsafe関数の内部にも、明示的なunsafeブロックを置く

Rust 2024では、unsafe関数内のunsafe操作を明示的なブロックで囲まないと、`unsafe_op_in_unsafe_fn`がデフォルトで警告する。これは呼び出し側への要求と、実装内で引き受ける責任を分ける変更である。警告をエラーにすることもできる。[Edition Guide](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-op-in-unsafe-fn.html)

```rust
#![deny(unsafe_op_in_unsafe_fn)]

/// # Safety
/// `index`は`values.len()`未満でなければならない。
unsafe fn at(values: &[u8], index: usize) -> u8 {
    // SAFETY: この関数の呼び出し側に要求した境界条件を使う。
    unsafe { *values.get_unchecked(index) }
}

fn checked_at(values: &[u8], index: usize) -> Option<u8> {
    if index >= values.len() {
        return None;
    }
    // SAFETY: 直前の検査でindex < values.len()を確認した。
    Some(unsafe { at(values, index) })
}
```

`at`は条件を呼び出し側へ要求し、`checked_at`は自分で検査して、安全なAPIを提供する。実際の開発では、この例は`values.get(index).copied()`で書ける。ここでunsafeを使うのは、責任の関係を示すためである。

### 3.2 unsafe属性とunsafe extern

Rust 2024には、境界をさらに明示する変更がある。

- `no_mangle`などの属性を`#[unsafe(no_mangle)]`と書き、シンボル名やリンクに関する条件を示す。[unsafe attributes](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-attributes.html)
- `unsafe extern "C"`で、宣言したABIや型が正しいことに対する宣言者の責任を示す。ブロック内の個々の項目には`safe`や`unsafe`を指定できる。[unsafe extern blocks](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-extern.html)

ここでは「外部関数ならすべて同じ危険」という扱いから、**宣言が正しい責任と、その関数を呼び出す条件を分ける**方向が見える。ただし、`safe`と宣言しただけで外部の実装が自動検証されるわけではない。

### 3.3 Unsafe Fields: 不変条件を持つフィールドを示す

RFC 3458は、ライブラリ独自の安全性の不変条件を持つフィールドに、`unsafe`を付ける仕組みを提案する。[RFC 3458](https://rust-lang.github.io/rfcs/3458-unsafe-fields.html)

```text
概念的な宣言:

struct Buffer {
    storage: ...
    unsafe len: usize
        条件: lenは容量以下であり、その範囲は初期化済み
}

lenの構築・変更・取り出しなど、対象となる操作にunsafeを要求する。
```

これは、2.3節の「安全な代入で、後のunsafeの前提を壊せてしまう」という問題を、フィールドの宣言位置まで追えるようにする試みである。

ただし、条件を文章で書けばコンパイラが`len <= capacity`を自動証明する、という機能ではない。型そのものが持つ有効性の条件を緩めるものでもない。たとえば、本来ゼロを許さない型の値をゼロにしてよい、とはならない。

**調査時点では不安定な機能である。** Unstable Bookと追跡issueには`#![feature(unsafe_fields)]`が示されており、RFCの承認と安定版での利用可能性は分けて考える。[Unstable Book](https://doc.rust-lang.org/unstable-book/language-features/unsafe-fields.html)、[追跡issue #132922](https://github.com/rust-lang/rust/issues/132922)

## 4. 操作の種類と、安全条件を指定する

### 4.1 「何を許すか」を細かくする案

2025年のRust Internalsには、Granular Unsafe Blocksという議論がある。たとえば、生ポインタの参照外しとFFI呼び出しだけを許可するような、操作カテゴリ付きのブロックを考える。[提案者の投稿と議論](https://internals.rust-lang.org/t/pre-rfc-granular-unsafe-blocks-a-more-explicit-and-auditable-approach/23022)

```text
提案で検討された構文の例:

unsafe(deref_raw, ffi_call) {
    ...
}
```

これは、**Rustに採用済みの構文として紹介できるものではなく、Pre-RFC段階の議論**である。また、カテゴリに「可変参照の規則違反を許す」を加えればよい、という話でもない。規則に反する未定義動作を許可することは、安全な実行の定義を壊してしまう。

### 4.2 操作カテゴリだけでは、安全条件を表しきれない

生ポインタの読み取り一つでも、必要な条件は複数ある。

```text
操作:
  pからTを読む

その操作に必要な条件の例:
  必要な領域が生存している
  読む範囲が割り当ての内側にある
  必要なアラインメントを満たす
  Tとして有効な値が初期化されている
  別名参照や並行アクセスの規則に反しない
```

「raw readを許す」という指定は、操作の分類である。一方、「この`p`は、この範囲を、この期間に読むために有効である」は、対象と文脈を伴う条件である。[ポインタ操作の安全条件](https://doc.rust-lang.org/std/ptr/index.html#safety)

さらに、複数のポインタ間で領域が重ならないことや、後で二重解放しないことなど、引数間・時間方向の条件もある。2024年のunsafe reasonsの議論でも、個々の要求と、それを満たす理由を対応させる構想が検討されている。[Unsafe reasonsの設計スケッチ](https://internals.rust-lang.org/t/pre-rfc-unsafe-reasons/22093/19)

### 4.3 Safety Tags: 条件を名前付きの項目へ分ける

Safety Tagsは、安全性に関するコメントを、構造のあるタグとして扱う研究・実装である。2025年の論文と2026年の改訂では、レイアウト、ポインタ、有効な内容、別名参照、実行文脈などの条件を分類している。[論文、2026年改訂版](https://arxiv.org/abs/2504.21312v2)

たとえば、「有効なポインタであること」と一文で済ませず、読み取り可能性、アラインメント、初期化などを分け、API側の要求と呼び出し側の確認を対応させる。

```text
API側:
  requires: readable(p, sizeof(T)), aligned(p, T), initialized(p, T)

呼び出し側:
  checked: readable(...)   理由: 所有するバッファの範囲内
  checked: aligned(...)    理由: Tの配列から取得
  checked: initialized(...) 理由: 初期化後に取り出した
```

これは概念説明であり、実際のタグ構文ではない。RFC案では`#[safety::requires(...)]`と`#[safety::checked(...)]`が使われている。[RFC PR #3842](https://github.com/rust-lang/rfcs/pull/3842)

研究の実装`safety-tool`は、注釈と呼び出し先の要求の整合性などを検査する。実際にメモリが生存することまで、タグの名前を一致させるだけで証明するわけではない。**要求を見落としていないことの検査と、その要求が真であることの証明は別である。**[公開実装と目的](https://github.com/safer-rust/safety-tags)

調査時点でRFC PR #3842はOpenであり、Rust標準の採用済み機能とは扱わない。操作カテゴリの案より、APIごとの条件に近づいた方式だが、注釈の正しさや網羅性には人の判断も残る。

## 5. 型と権限で、必要なunsafeを減らす

### 5.1 一つの大きな抜け道より、特定の条件を表す型を使う

Rustの標準ライブラリには、通常の扱いから外れる部分を、個別の型で表す仕組みがある。

| 仕組み | 個別に扱う条件 | それだけでは保証しないこと |
| --- | --- | --- |
| [`UnsafeCell<T>`](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html) | 共有参照の下に、変更しうる内容がある | 排他的な`&mut`の条件や、データ競合の防止 |
| [`MaybeUninit<T>`](https://doc.rust-lang.org/std/mem/union.MaybeUninit.html) | まだ有効な`T`を格納していない領域を表す | 有効な`T`として取り出してよいこと |
| [`ManuallyDrop<T>`](https://doc.rust-lang.org/std/mem/struct.ManuallyDrop.html) | 自動的な破棄を抑制する | 無効な`T`や未初期化の`T`を入れてよいこと |
| [`NonNull<T>`](https://doc.rust-lang.org/std/ptr/struct.NonNull.html) | ポインタがnullではないことを表す | 生存、初期化、参照外し可能性 |
| [`Pin<P>`](https://doc.rust-lang.org/std/pin/index.html) | pinningの契約を通じ、対象を移動させない保証を扱う | 任意のポインタの有効性や、すべての型に対する無条件の移動禁止 |

これらは同じ種類の型ではないが、**どの条件を特別に扱うかを、値の表現やAPIへ局所化する**という点で参考になる。

たとえば`MaybeUninit<T>`を用意するだけなら安全でも、`assume_init`で`T`へ変換するときには、有効な値を初期化済みであるという責任が発生する。単に「未初期化を許すモードにした」だけでは、その後の読み取りまで正当化できない。

### 5.2 GhostCellは、変更の権限をトークンへ移す

[GhostCell](ghostcell.md)では、ノードへの参照を持つことと、今そのノードを変更する権限を持つことを分ける。ライブラリ内部のunsafeを、ブランドとトークンの規則で包み、利用側では通常の借用検査を通じて権限を管理する。[GhostCell原論文](https://plv.mpi-sws.org/rustbelt/ghostcell/paper.pdf)

これは、各操作に毎回「自分が排他的だと信じる」と書く代わりに、その権限を表すトークンを要求する方向である。ただし、その安全なAPI自体の実装には根拠が必要になる。

### 5.3 Typestateと、対象を取り違えないブランド

初期化前と初期化後、接続前と接続後などを異なる型で表し、状態遷移のAPIを通じて必要な条件を作る方法もある。Typestateは、その基本的な発想である。[Rust Embedded Bookの例](https://docs.rust-embedded.org/book/static-guarantees/typestate-programming.html)

また、単なる整数の添字に、どのコンテナのものかを表すブランドを付ける設計なら、別のコンテナとの取り違えを型で制限できる。この考え方は、GhostCellのブランドや、Hyloのグラフ表現についての[既存メモ](hylo-mutable-value-semantics.md#10-所有関係が木でもグラフは表現できる)にもつながる。

ただし、ブランドを付けることと、削除後の有効性や添字の境界まで保証することは別である。どの性質を型に含めるかを決める必要がある。

## 6. 許される実行を定義する

### 6.1 Strict Provenance: アドレスと、アクセスできる根拠を分ける

Rustのポインタは、意味の上で単なる整数アドレスではない。同じ数値のアドレスでも、すでに解放された領域由来のポインタを使ってよいとは限らない。

Strict ProvenanceのAPIは、アドレスを取り出す操作と、元のポインタのprovenanceを保ってアドレスを変える操作などを区別する。`addr`、`with_addr`、`map_addr`などがある。整数変換を通じたExposed Provenanceの経路も別に扱う。[標準ライブラリのProvenanceの説明](https://doc.rust-lang.org/std/ptr/index.html#provenance)

これは、unsafeなコードを自由にするために規則を消すのではなく、**低水準の操作にも、検査・最適化が扱える意味を与える**発展である。これらのAPIを使えば、境界、寿命、別名参照の条件がすべて自動で満たされるわけではない。

### 6.2 Stacked BorrowsとTree Borrows

生ポインタと参照を混ぜて扱う場合、どのアクセスが許されるかを詳しく定める必要がある。Stacked BorrowsとTree Borrowsは、そのための別名参照モデルである。

Tree Borrowsの2025年の研究は、実用的なunsafeコードのパターンを扱いつつ、コンパイラ最適化の根拠を保つことを目指す。既存の静的借用検査器を、単に別の借用検査器へ交換する提案ではない。[Tree Borrowsの研究紹介](https://plf.inf.ethz.ch/research/pldi25-tree-borrows.html)

現行Rust全体の規範的な別名参照仕様が、これらの研究の一つとして完全に確定したとみなしてはいけない。標準ライブラリの説明にも、厳密な規則の未確定部分があることが記されている。[ポインタから参照への変換条件](https://doc.rust-lang.org/std/ptr/index.html#pointer-to-reference-conversion)

### 6.3 Miriで、実行をモデルに照らして検査する

MiriはRustの中間表現を実行し、範囲外アクセス、解放後の使用、未初期化データ、不正な値、別名参照の規則違反などを検出する。Tree Borrowsを選ぶ実験的な設定も提供している。[MiriのREADME](https://github.com/rust-lang/miri)

通常のテストでは正しい結果が出るunsafeコードでも、言語の規則に反する実行を見つけられる点が重要である。ただし、検査した入力・経路・実行モデルに依存し、未実行の経路を含めた全体の正しさの証明ではない。外部ネイティブコードとの連携にも検査範囲の制限がある。

## 7. 検査から形式証明へ

### 7.1 RustBelt: 安全な抽象化として成立する条件を証明する

RustBeltは、Rustを代表する部分言語と、unsafeを内部に使うライブラリの安全性を、分離論理と証明支援系で扱った研究である。

単に「この入力でクラッシュしなかった」ではなく、ライブラリが満たすべき条件を示し、それを満たす拡張を安全なクライアントが利用できるという接続を作る。すべてのRustクレートやrustc全体が証明済みという意味ではない。[RustBelt, POPL 2018](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf)

### 7.2 RefinedRust: 実際のRustコードに、より詳しい仕様を付ける

RefinedRustは、Rustの型に論理的な情報を加えるrefinement typeと、分離論理に基づく検証を組み合わせる。注釈付きのRustコードから、Coq内のモデルと検証へ進み、生成した証明を証明支援系で検査する。2024年の研究には、unsafeなポインタ操作を含む`Vec`の変種の検証がある。[RefinedRustのプロジェクト説明](https://plv.mpi-sws.org/refinedrust/)

```text
通常の型:
  p: ポインタ

より詳しい仕様で表したいこと:
  pは、この領域を所有する
  そこには、論理的な列xsの要素が格納されている
  関数の後では、その列が指定した形に変化する
```

これは、安全条件を列挙するだけでなく、実装がその条件と結果の仕様を満たすことまで検証する方向である。

ただし、**2024年の原論文の対象にも明確な制限がある。** 別名参照モデル、ポインタと整数の変換、有効性条件の一部などは扱わず、並行処理などの機能にも制限がある。現在の実装の全機能や、全種類の未定義動作の証明へ一般化しない。[原論文のNon-goals and limitations](https://iris-project.org/pdfs/2024-pldi-refinedrust.pdf)

### 7.3 Kani: 入力や状態の組み合わせを、モデル検査する

Kaniは、RustコードをCBMCへ接続するモデル検査器である。証明用ハーネスで入力や前提を指定し、サポートするモデル内で安全性やassertionを検査する。生ポインタのアクセスも対象になる。[Kaniの公開実装](https://github.com/model-checking/kani)

有限の範囲を展開する検査では、その展開範囲や前提が結論を制限する。一方、2026年の論文では、関数契約やループ契約などによって検証を広げる仕組みも説明されている。「必ず有限個のテストケースを試すだけの道具」と捉えるのも適切ではない。[Kani, 2026](https://arxiv.org/abs/2607.01504)

注意すべきなのは、KaniがRustのすべての未定義動作を検出するわけではない点である。公式文書は、データ競合、参照の寿命に基づく別名参照規則、無効な値の生成などの制限を列挙している。[検査対象と制限](https://model-checking.github.io/kani/undefined-behaviour.html)

### 7.4 2026年にも、境界の健全性を調べる研究がある

- [Towards verifying unsafe Rust programs against Rust's pointer-aliasing restrictions](https://arxiv.org/abs/2603.28326): unsafeを含むプログラムが別名参照規則に従うことを、モジュール単位で検証する論理に向けた進行中の研究。2026年3月のプレプリントであり、完成済みの汎用検証器とは扱わない。
- [UnsafeChecker](https://arxiv.org/abs/2609.09641): 所有、値の有効性、レイアウトの情報をMIR上で追跡し、安全なAPIから漏れ出す契約違反などを探す静的解析。2026年9月のプレプリント。バグ候補の検出を目的とし、警告がないことを完全な正しさの証明とは扱わない。

### 7.5 Low*とKaRaMeL: 検証した低水準コードを生成する

別の方向として、F*の部分言語Low*で、メモリと計算の条件を検証し、KaRaMeLでCへ抽出する方法がある。既存のunsafeコードを後から調べるだけでなく、検証に向いた記述から低水準の実装を作る。

HACL*は、この方式を使う暗号ライブラリの実例である。対象となるプログラムの制約、仕様・外部呼び出し・抽出先の実行環境などの前提は残る。[KaRaMeLの説明](https://github.com/FStarLang/karamel)、[Low*の位置づけ](https://github.com/FStarLang/karamel/blob/master/book/Introduction.rst)

## 8. 効果と、外部資源への権限を追跡する

### 8.1 効果として表せば、関数を越えて追える

効果の仕組みは、「この関数は何を行いうるか」を型や解析結果へ付け加える。unsafe操作、FFI、ファイル操作、ネットワーク操作などを区別し、呼び出しを通じて追う発想がある。

ここで扱う効果には、メモリ安全な操作も含まれる。たとえばファイルを読むことは、Rustでは通常safeな操作だが、権限や監査の面では重要な効果になる。

### 8.2 Cargo Scan: 言語を変更せず、監査する効果を追う

Cargo Scanは、危険性を調べたい操作を効果として解析し、クレートやモジュールを越えて追う監査支援ツールである。操作の安全性をその場で判断できるか、呼び出し側の条件まで調べる必要があるかを整理し、監査結果を再利用可能なファイルへ記録する。[Auditing Rust Crates Effectively, ESOP 2026](https://arxiv.org/abs/2602.06466)

これは、Rust標準にunsafeの効果型が導入されたという話ではない。また、ツールが分類する「危険性」には、メモリ安全性以外の外部への作用も含まれる。公開実装は開発中とされている。[Cargo Scanの実装](https://github.com/PLSysSec/cargo-scan)

### 8.3 ケイパビリティなら、操作する対象を指定できる

効果が「ファイルへアクセスする可能性」を表すのに対し、ケイパビリティは、「このディレクトリを操作できるハンドル」など、具体的な対象への権限を値として渡す。

cap-stdは、Rustの標準ライブラリに似た操作を、ケイパビリティ中心のAPIへ変える実装である。任意のパスを開く代わりに、与えられた`Dir`から相対的にファイルへアクセスする。[cap-stdの説明](https://github.com/sunfishcode/cap-std)

ただし、同じプロセスのコードが別途`std::fs`やFFIへ自由に到達できるなら、cap-stdを一部で使うだけでプロセス全体を隔離したことにはならない。APIの権限制限と、実行環境の強制的な隔離は分ける必要がある。

## 9. DとSwiftの言語機能

### 9.1 D: checked / unchecked / trustedを分ける

Dには、関数の安全性に関する三つの属性がある。

| 属性 | 位置づけ |
| --- | --- |
| `@safe` | メモリ安全な部分言語の制約を検査する |
| `@system` | 安全性を自動では保証しない操作を含みうる |
| `@trusted` | 実装者の責任で、安全に呼べるインターフェースを提供する |

`@safe`からは`@safe`と`@trusted`を呼べる。`@trusted`は「機械が検証を終えた」という意味ではなく、検査で扱えない実装を安全な境界で包むという約束である。[DのFunction Safety](https://dlang.org/spec/function.html#function-safety)

Rustの安全なラッパー関数と関心は近いが、Dでは信頼する境界が属性として明示される。二値のsafe/unsafeに対し、**検査済みの制約に従うコードと、人が責任を引き受ける安全な境界を区別する**設計例になる。

### 9.2 Swift: unsafeな式や宣言を見えるようにする

Swift 6.2は、オプトインのstrict memory safetyを導入した。unsafeな構文やAPIの使用を診断し、安全な代替へ移すか、ソース中で明示的に認める。[Swift 6.2のリリース説明](https://www.swift.org/blog/swift-6.2-released/)

SE-0458では、`@unsafe`な宣言、`@safe`な境界、式の`unsafe`による明示などを定める。型やシグネチャに含まれるunsafeな要素も、診断の対象になる。[SE-0458: Strict memory safety](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0458-strict-memory-safety.md)

この方式は、ブロック単位だけでなく、**使うAPI・宣言・式のどこで安全性の責任が生じるかを表面に出す**例である。strictモードの診断は警告を基本とし、エラーへ引き上げられる。`unsafe`を添えた式の安全性そのものを自動証明する機能ではない。

## 10. 他言語との境界を改善する

### 10.1 境界の情報を増やす: Checked CとSwift

Checked Cは、Cへ検査付きのポインタや境界情報を追加し、静的に確認できないアクセスに実行時検査を用いる研究・実装である。既存の関数へbounds-safe interfaceを付け、少しずつ移行できるようにする。[Checked Cの概要](https://github.com/checkedc/checkedc/wiki/Checked-C-overview)、[原論文](https://www.microsoft.com/en-us/research/wp-content/uploads/2018/09/checkedc-secdev2018-preprint.pdf)

ただし、境界検査だけで、解放後の使用などもすべて防げるわけではない。公式の説明も、割り当て・解放が正しいという前提を区別している。Checked CはISO Cの採用済み仕様として紹介するものではない。

Swiftのsafe interoperabilityにも、C/C++のポインタと長さの関係や寿命の情報を注釈し、`Span`などの安全なインターフェースへ接続する仕組みがある。元の外部実装や注釈が正しいことは、引き続き境界の前提になる。[Safely Mixing Swift and C/C++](https://www.swift.org/documentation/cxx-interop/safe-interop/)

同文書は、`Span`などの安全なオーバーロードを生成する機能について、Swift 6.2のリリースブランチでは実験的な機能フラグの下にあると説明している。strict memory safety自体の導入と、個々のFFI機能の利用可能性は区別する。

### 10.2 境界の外側を守る: WebAssembly

別の方向は、unsafeを含むコードを、制限された実行環境へ置くことである。WebAssemblyでは、線形メモリの範囲を越えるアクセスを検査し、外部との操作はインポートなどの境界を通す。Wasmtimeは、そのようなサンドボックスを実装する。[Wasmtimeのセキュリティモデル](https://docs.wasmtime.dev/security.html)

ただし、C/C++をWasmへコンパイルしても、ゲストの一つの線形メモリ内で、別のオブジェクトを壊す誤りまでは自動的に消えない。ソース言語の未定義動作も、コンパイル前の正しさの問題として残る。守る単位が、個々の値か、モジュールのメモリ全体かを区別する必要がある。

### 10.3 RLBox: 隔離と、戻り値を信用しない型を組み合わせる

RLBoxは、既存のC/C++ライブラリを細かく隔離し、ホストとの境界をC++の型で扱う枠組みである。Firefoxでの利用も報告されている。[RLBoxの原論文と実装事例](https://www.usenix.org/conference/usenixsecurity20/presentation/narayan)

隔離したライブラリから返る値は、`tainted`な値として扱う。ホストが重要な値として使う前に、その内容を確認するという境界を作る。隔離されていても、戻り値を信用したホストが不正なサイズやポインタを使えば、問題が外へ伝わるためである。[値を検査して取り出すAPI](https://rlbox.dev/chapters/advanced/untainting-apis.html)

この方式では、unsafeな実装を全体として証明する代わりに、**実装を信用する範囲を狭め、境界を越えるデータに追加の規律を課す**。検査側の条件やサンドボックスの実装まで不要になるわけではない。

## 11. ハードウェアによる発展

### 11.1 CHERI: ポインタに権限と境界を持たせる

CHERIは、偽造や不正な権限拡大を防ぐケイパビリティを、ハードウェアのデータ型・命令として扱う方式である。細かなメモリ保護や、ソフトウェアの区画化に使う。[CHERIのプロジェクト説明](https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/index.html)、[公式FAQ](https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-faq.html)

言語の型でなく、実際のロード・ストアの時点に制約を持たせるため、低水準のC/C++コードにも保護を加えられる。ただし、時間的な安全性には、失効やメモリ回収方式との組み合わせが関わる。CHERIという名前だけで、解放後の使用、初期化、型の有効性、すべての別名参照条件を一括して保証するとは言えない。

### 11.2 Mon CHÉRI: 過去の操作に依存する権限を加える

Mon CHÉRIは、CHERIへconditional capabilitiesを追加する研究である。「この場所は、少なくとも一度書き込むまで読めない」というWrite-before-Readのように、過去の操作に依存する方針を扱う。アーキテクチャ拡張、コンパイラ支援、シミュレータやFPGAでの評価が報告されている。[Mon CHÉRI, IEEE S&P 2025](https://arxiv.org/abs/2407.08663v3)

これは「読み取り権限があるか」という固定的な区分を、**状態遷移を伴う権限**へ発展させる例である。ただし、バイトが書き込まれたことと、任意の言語の型として有効な値であることは同義ではない。

## 12. 研究と実装の位置づけ

### 12.1 どこまで機械が確かめるのか

| 段階 | 例 | 主に確かめるもの | 残る責任・前提 |
| --- | --- | --- | --- |
| 明示 | unsafeブロック、Dの`@trusted` | 責任を引き受ける位置 | 安全性の理由そのもの |
| 構造化した明示 | Safety Tags | 要求と確認項目の対応など | 注釈した条件が真であること |
| 型による制限 | typestate、ブランド、権限トークン | 許されたAPIの組み合わせ | 安全なAPIの実装と、型で表さない条件 |
| 動的検査 | Miri、実行時の境界検査 | 対象の実行で起きる違反 | 未検査の実行、モデル外の挙動 |
| 静的なバグ検出 | UnsafeCheckerなど | 解析が追える契約違反の候補 | 見逃し、誤警告、解析対象の制限 |
| モデル検査・演繹的検証 | Kani、RefinedRust | 指定した前提とモデルにおける性質 | モデル、仕様、翻訳、未対応の機能など |
| 実行時の隔離 | WebAssembly、RLBox、CHERI | 境界の外への不正な作用など | 境界内の誤り、与えた権限、実行基盤 |

この表は、すべての方式が同じ保証へ順番に近づく序列ではない。たとえば、証明済みの計算でも、許可された外部出力をしてよいかは別に決める必要がある。

### 12.2 利用可能性を混同しない

| 対象 | 調査時点での位置づけ |
| --- | --- |
| Rust 2024のunsafe関数内の警告、unsafe属性、unsafe extern | 安定した言語・ツールの機能 |
| Rust Unsafe Fields | 不安定な機能。追跡issueとfeature gateあり |
| Granular Unsafe Blocks / unsafe reasons | 言語設計の議論。標準機能ではない |
| Safety Tags / safety-tool | 公開された研究・実装。RFC PRはOpen |
| Miri | 実際に利用される検査ツール。別名参照モデルには実験的部分あり |
| RustBelt / RefinedRust | 対象と仮定を明示した形式化・検証の研究 |
| Kani | 公開されたモデル検査器。検査するUBや対応機能に制限あり |
| Cargo Scan | 公開された監査支援ツール。開発中 |
| Swift strict memory safety | Swift 6.2で導入されたオプトインの機能 |
| Dの三つの安全性属性 | 言語仕様にある機能 |
| Checked C | Cの研究拡張と公開実装 |
| RLBox / Wasmtime | 公開実装があり、実際の隔離に使われる枠組み |
| CHERI / Mon CHÉRI | ハードウェアとソフトウェアを組み合わせる研究・実装。構成ごとに保証を確認する |

## 13. このリポジトリの言語設計への示唆

以下は、調査から導いた考察であり、既存のどれかの言語に実装済みの統一方式でも、採用決定でもない。

### 13.1 まず、三つの問いを分ける

```text
1. この関数は、どの操作を行いうるか。
     例: 生メモリの読み取り、FFI、外部I/O

2. この操作は、どの対象に対して許されるか。
     例: このバッファ、このデバイス、このディレクトリ

3. 今、その操作の安全条件を満たすか。
     例: 生存中、初期化済み、境界内、排他的、適切なABI
```

操作の効果、対象への権限、論理的な条件は互いに関連するが、一つにまとめると何を保証したかがわかりにくくなる。

### 13.2 条件を満たす根拠も、区別して記録する

```text
ある低水準操作の前提:

  初期化済み:       型と状態遷移で保証
  境界内:           実行時検査で確認
  排他的にアクセス: 権限トークンで保証
  外部ABIが正しい:  FFI宣言者が引き受ける
  残る仮定:         明示した信頼境界で引き受ける
```

初めから万能な自動証明器を目指さなくても、どの条件を言語が保証し、どの条件が人の仮定として残っているかを表せる。

ただし、人が書いた根拠を「証明済み」と表示してはいけない。タグの整合性、型検査、実行時検査、論理的な証明では、確かめた内容が異なる。

### 13.3 局所的な条件と、持続する不変条件を分ける

「今このポインタを読める」と、「このデータ構造を使う間ずっと、長さと容量の関係を保つ」は、異なる種類の条件である。

後者は、初期化、変更、破棄、例外やキャンセル、外部コールバックなどの複数の経路に関わる。操作ごとの小さなunsafeブロックを増やすだけで、全体の維持が確認できるとは限らない。

型、モジュールの可視性、状態遷移、検証用の仕様を組み合わせ、誰がその不変条件を変更できるかを制限する必要がある。

### 13.4 既存のメモとのつながり

- [所有権とその先](ownership-and-beyond.md): 所有・借用だけでは表しきれない効果や検証へ広げる。
- [GhostCell](ghostcell.md): 安全性の条件の一部を、権限トークンとブランドへ移す。
- [OxCamlのモード](oxcaml-modes.md): 値の使い方を複数の軸で追跡する。モードを一つ満たせば任意のunsafe操作が正当化されるわけではない。
- [Hyloと可変値意味論](hylo-mutable-value-semantics.md): 通常のモデルで共有を制限し、低水準操作を必要とする境界を整理する。それでも外部資源やFFIの前提は別に残る。

## 14. 資料と確認範囲

### 14.1 読む順序の候補

| 関心 | 最初の資料 | 次に読む資料 |
| --- | --- | --- |
| unsafeの責任を理解する | [Rust Reference](https://doc.rust-lang.org/reference/unsafe-keyword.html) | [RFC 2585](https://rust-lang.github.io/rfcs/2585-unsafe-block-in-unsafe-fn.html) |
| より細かい条件を付ける | [Safety TagsのRFC PR](https://github.com/rust-lang/rfcs/pull/3842) | [注釈と監査の論文](https://arxiv.org/abs/2504.21312v2) |
| 状態を持つフィールドまで追う | [Unsafe Fields RFC](https://rust-lang.github.io/rfcs/3458-unsafe-fields.html) | [追跡issue](https://github.com/rust-lang/rust/issues/132922) |
| unsafe実装を証明する | [RefinedRust](https://plv.mpi-sws.org/refinedrust/) | [RustBelt原論文](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf) |
| 手元のコードを検査する仕組みを知る | [Miri](https://github.com/rust-lang/miri) | [Kaniと制限](https://model-checking.github.io/kani/undefined-behaviour.html) |
| メモリ以外の作用も調べる | [Cargo Scanの論文](https://arxiv.org/abs/2602.06466) | [cap-std](https://github.com/sunfishcode/cap-std) |
| 言語機能の別案を見る | [Dの安全性属性](https://dlang.org/spec/function.html#function-safety) | [Swift SE-0458](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0458-strict-memory-safety.md) |
| 危険な実装を隔離する | [RLBox](https://www.usenix.org/conference/usenixsecurity20/presentation/narayan) | [Wasmtime](https://docs.wasmtime.dev/security.html)、[CHERI](https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/index.html) |

### 14.2 確認範囲

公式ドキュメント、RFCと追跡issue、原論文、研究プロジェクトの公開実装を確認して整理した。RFCが存在すること、実装が存在すること、安定した機能であること、実装全体が証明済みであることを区別した。

3.1節のRust例は、`rustc 1.94.1`、Edition 2024、警告をエラーにする設定でコンパイルした。通常の添字、範囲外、空のスライス、`usize::MAX`を渡す場合の動作を確認した。これは説明例の確認であり、Miriによる検査や形式的な安全性証明ではない。

各検証器、研究用コンパイラ、サンドボックス、ハードウェア環境の導入・実行や、性能比較は行っていない。2026年の新しい研究は、論文が報告する対象と段階に限定して紹介している。
