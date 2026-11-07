# 所有権とその先 — メモリ管理から権限・並行性・効果へ

[メモの一覧へ](README.md) · [リポジトリの目次へ](../../README.md)

調査日: **2026-11-07**
更新日: **2026-11-07**（GhostCell・OxCaml・Hylo・unsafeの発展の詳細メモへのリンクを追加）

目的: Rustの所有権と借用を出発点に、関連する技術・手法・考え方を整理し、新しいプログラミング言語を設計するための見取り図を作る。

公式ドキュメントと原論文を中心に調査した。実装状況は調査時点の資料に基づく。各節の「設計への示唆」と後半の検討案は、本メモでの考察であり、引用元の結論やこのリポジトリの確定仕様ではない。

## 目次

- [全体像](#1-最初に押さえたい全体像)
- [所有権と借用の基本](#2-所有権と借用は何を解決するのか)
- [歴史的な位置づけ](#3-rustより前からある基礎とrust以後の展開)
- [借用検査の精密化](#4-発展の方向a-借用検査をより精密で使いやすくする)
- [データとアクセス権限の分離](#5-発展の方向b-データの所有とアクセス権限を分ける)
- [値を中心に考える設計](#6-発展の方向c-共有する可変状態を減らし値を中心に考える)
- [自動メモリ管理の改善と組み合わせ](#7-発展の方向d-自動メモリ管理を型情報と組み合わせて改善する)
- [メモリ以外の資源の使い方](#8-発展の方向e-メモリ以外の資源の使い方を型にする)
- [副作用とキャプチャの追跡](#9-発展の方向f-関数の副作用と保持する権限を追う)
- [形式化と検証](#10-発展の方向g-安全性の根拠を形式化し検査可能にする)
- [比較表](#11-比較表-何を得て何を引き受けるか)
- [このリポジトリでの設計の検討案](#12-このリポジトリの言語設計へどうつなげるか)
- [一次資料を読む順序](#13-読む順序の案)

## 1. 最初に押さえたい全体像

所有権は、**ある資源について、誰が責任を持ち、誰がどの操作をしてよいかを決める仕組み**と考えると理解しやすい。メモリだけでなく、ファイル、ロック、通信路にも関係する。

Rustは、所有権・借用・ライフタイムを組み合わせ、低水準のメモリ操作と静的な安全性を両立させる設計を実用化した。その基礎となる発想には、Rust以前から研究されてきた線形型、一意性型、リージョン、資源管理の技法がある。[Rust公式の所有権の説明](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)、[Wadlerの線形型に関する論文紹介](https://homepages.inf.ed.ac.uk/wadler/topics/linear-logic.html)、[Cleanの一意性型](https://clean.cs.ru.nl/download/html_report/CleanRep.2.2_11.htm)

その後の発展を見るときは、次の問いを分けると整理しやすい。

| 問い | 主な考え方 |
| --- | --- |
| 資源をいつ解放するか | RAII、GC、参照カウント、リージョン |
| 参照が指す対象はまだ生きているか | ライフタイム、借用検査、世代付きハンドル |
| 誰が読み書きできるか | 排他的借用、参照ケイパビリティ、権限トークン |
| 別のスレッドやタスクへ渡せるか | 所有権の移譲、隔離、`Send` / `Sync`、`sending` |
| 共有による複雑さをどう減らすか | 不変データ、値セマンティクス、Copy-on-Write |
| 何回・どの順序で操作できるか | 線形型、アフィン型、typestate、セッション型 |
| 関数はどんな作用や権限を使うか | エフェクトシステム、キャプチャ検査 |
| これらの保証をどう確かめるか | 形式化、機械検証、動的検査 |

これらは組み合わせられる。たとえば、GCがメモリを回収する言語でも、型で共有や変更の権限を制限できる。実例としてPonyは、参照ケイパビリティとGCを併用する。[Ponyの参照共有](https://tutorial.ponylang.io/reference-capabilities/passing-and-sharing)、[PonyのGC](https://tutorial.ponylang.io/runtime-basics/garbage-collection.html)

## 2. 所有権と借用は、何を解決するのか

### 2.1 問題の出発点

手動でメモリを管理すると、確保した領域について、解放の責任と参照の有効性を人間が追う必要がある。

| 問題 | 何が起きるか |
| --- | --- |
| 二重解放 | 同じ領域を複数回解放する |
| 解放後使用 | 解放済みの領域を参照する |
| ダングリング参照 | すでに無効になった対象への参照が残る |
| メモリリーク | 不要な領域を回収できない |
| イテレータの無効化 | 走査中のコレクションを変更し、参照先が無効になる |
| データ競合 | 同じ場所への同期されていない並行アクセスに書き込みが含まれる |

ここには二つの問題が重なっている。**対象が生きているかという問題**と、**生きている対象へ複数の経路からどうアクセスするかという問題**である。RustBeltの論文も、所有権の役割を資源の生存とアクセス権限の両面から説明している。[RustBelt, §1](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf)

### 2.2 所有権: 解放の責任を移せるようにする

Rustの基本形では、値の所有者を定め、所有者がスコープを抜けると値を破棄する。所有権は別の変数や関数へ移せる。

```rust
fn main() {
    let first = String::from("hello");
    let second = first; // 所有権を移動する

    // println!("{first}"); // 有効にすると、移動後の使用としてコンパイルエラー
    println!("{second}");
} // secondが所有するStringを破棄する
```

ここで移しているのは、文字列全体を新しく複製することではなく、その値を使い、最終的に破棄する責任である。`Copy`な整数などには複製が認められるため、あらゆる代入で元の変数が使えなくなるわけではない。[Rust公式の所有権・ムーブ・コピーの説明](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)

### 2.3 借用: 責任を移さず、一時的にアクセスさせる

毎回所有権を渡して戻すのは不便なので、参照を使って一時的にアクセスさせる。

- `&T`: 共有して読むための参照。
- `&mut T`: 排他的にアクセスし、変更できる参照。

通常のデータについては、同じ場所への競合するアクセスに対し、**複数の共有参照か、一つの排他的な可変参照か**という規律を設ける。よく「共有 XOR 変更」と呼ばれる考え方である。[Rust公式の参照と借用](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)

```rust
fn main() {
    let mut text = String::from("hello");

    let view = &text;
    println!("{view}"); // viewの最後の使用

    text.push('!'); // この時点では共有借用が終わっているので変更できる
    println!("{text}");
}
```

この原則は「プログラム全体で可変参照を一つしか作れない」という意味ではない。別の場所への借用、構造体の独立したフィールドへの借用、必要な範囲での再借用などを扱える。

また、`&T`を「内部まで絶対に変化しない」と理解するのも正確ではない。`Cell`、`RefCell`、ロックなどの**内部可変性**を通じた変更には、別の規律がある。[内部可変性の説明](https://doc.rust-lang.org/book/ch15-05-interior-mutability.html)

### 2.4 ライフタイム: 参照が有効な範囲を整合させる

ライフタイムは「その参照を使う間、参照先が有効である」ことを検査するための情報である。`'a`のような注釈は、参照どうしの有効期間の関係を表す。注釈を書いても、対象の寿命が延長されるわけではない。[Rust公式のライフタイム](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)

上の例で`view`の借用が最後の使用後に終わっても、その瞬間に`text`が解放されるわけではない。**借用が終わる時点と、所有する値を破棄する時点は別である。** 破棄にはスコープなどの規則がある。[Rust Reference: Destructors](https://doc.rust-lang.org/reference/destructors.html)

### 2.5 Rustでも、すべてを静的に処理するわけではない

| 仕組み | 役割 | 実行時に必要になること |
| --- | --- | --- |
| 所有する値、`Box<T>`、通常の借用 | 一意な所有と一時的なアクセス | 確保・破棄など。借用規則は静的に検査する |
| `Rc<T>` | 単一スレッドでの共有所有 | 参照カウントの更新 |
| `Arc<T>` | スレッド間で使える共有所有の基盤 | アトミックな参照カウントの更新 |
| `RefCell<T>` | 借用の衝突を実行時に検査 | 借用状態の管理。衝突はpanicやエラーになる |
| `Mutex<T>` / `RwLock<T>` | 共有データへのアクセスを同期 | ロック取得・解放、必要に応じた待機 |

`Rc`や`Arc`は、参照先のデータを共同で所有する。各ハンドルの所有と、参照先の共有所有を区別すると、「所有者は一つ」との関係を理解しやすい。`Arc`自体が、中の任意のデータを安全に並行変更できるようにするわけでもない。[標準ライブラリのRcの説明](https://doc.rust-lang.org/std/rc/index.html)、[Arcのスレッド安全性](https://doc.rust-lang.org/std/sync/struct.Arc.html#thread-safety)、[RefCellの説明](https://doc.rust-lang.org/book/ch15-05-interior-mutability.html)

Rustでは、`Send`が「その型の値を別スレッドへ移してよい」、`Sync`が「その型への共有参照を別スレッドからも安全に使える」を表す。所有・借用の規律を、並行処理の境界にも適用するための重要な情報である。ただし、データ競合を防げても、ロックの取り方によるデッドロックや、処理順序の論理的な誤りまで防ぐわけではない。[Rustonomicon: Send and Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html)

Rustの安全性には、コンパイラと、`unsafe`を内部に使うライブラリの実装が必要な条件を守るという前提がある。FFIや独自のポインタ操作まで、コンパイラがすべて自動で証明するわけではない。[RustBeltの検証対象](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf)

さらに、**メモリ安全性とリークの不在は別の性質**である。安全なRustでも`mem::forget`や参照カウントの循環で資源はリークしうる。デストラクタが必ず実行されるという保証もない。[標準ライブラリのforgetの安全性説明](https://doc.rust-lang.org/std/mem/fn.forget.html)

設計への示唆: 「GCなし」「静的検査」「実行時コストなし」「リークなし」を一つの性質として扱わない。どの仕組みがどの保証とコストを持つかを、個別に定義する必要がある。

## 3. Rustより前からある基礎と、Rust以後の展開

以下は代表的な節目であり、発明の優先順位を網羅する年表ではない。後年の項目も、すべてがRustから直接派生したという意味ではない。

| 時期 | 節目 | この調査との関係 |
| --- | --- | --- |
| Rust以前から | C++のRAII | オブジェクトの寿命に、メモリ・ファイル・ロックなどの解放を結びつける |
| 1990 | Wadlerの線形型の論文 | 資源を複製・放棄せず使う規律を、型で表現する |
| 1990年代 | Cleanの一意性型 | 一意に使える値を安全に破壊的更新する |
| 1994 | Tofte–Talpinのリージョン推論 | 領域の生存期間を解析し、領域単位でメモリを管理する |
| 1998 | Clarkeらのownership types | オブジェクト間の参照経路とカプセル化を型で制御する |
| 2015 | Rust 1.0、Ponyのdeny capabilities論文 | 所有・借用や参照権限を、システム開発・並行処理へ結びつける |
| 2018 | RustBelt | Rustの一部と安全な抽象化の根拠を機械検証する |
| 2018〜2022 | RustのNLL導入・移行完了 | 借用の範囲をブロック全体に固定しない解析へ進む |
| 2021 | GhostCell、Perceus、Mutable Value Semanticsの研究 | 権限とデータの分離、精密な参照カウント、値中心の設計が進展する |
| 2023〜2024 | Swiftのnoncopyable types、Swift 6の`sending` | 既存言語へ資源の一意性や安全な移譲を取り込む |
| 2023 | Veronaの領域と参照ケイパビリティの論文 | 領域ごとにメモリ管理と変更権限を制御する |
| 2025 | Tree Borrows論文 | `unsafe`を含むポインタの別名参照規則と最適化の根拠を改善する |
| 2026 | Polonius Alphaのnightly有効化の発表 | 借用解析の精度を高め、従来拒否されていたパターンを受け入れる |

前半の出典: [RAIIの説明](https://www.stroustrup.com/bs_faq2.html#finally)、[線形型の原論文紹介](https://homepages.inf.ed.ac.uk/wadler/topics/linear-logic.html)、[Cleanのマニュアル](https://clean.cs.ru.nl/download/html_report/CleanRep.2.2_11.htm)、[Tofte–Talpin, 1994](https://www.cs.cmu.edu/afs/cs/academic/class/15745-s06/web/handouts/tofte-popl94.pdf)、[Clarkeら, 1998](https://courses.cs.washington.edu/courses/cse590p/00wi/ownership-types.pdf)。後半の技術は次節以降で個別に出典を示す。Rust 1.0の節目は[公式発表](https://blog.rust-lang.org/2015/05/15/Rust-1.0/)を参照。

歴史上のownership typesには、オブジェクトの内部表現が外部から勝手に変更されないよう、参照の到達経路を制御するものもある。**ownershipという名前が同じでも、すべてがRustのムーブと解放の仕組みを指すわけではない。**

## 4. 発展の方向A: 借用検査を、より精密で使いやすくする

### 4.1 NLL: 必要なところまでを借用の範囲にする

NLLはNon-Lexical Lifetimesの略で、ソースコードのブロックだけに縛られず、制御の流れと使用箇所に基づいて借用を解析する。2.3節の「参照を最後に使った後で元の値を変更する」例が、身近な効果である。

Rustでは2018年の導入後に移行が進み、2022年に旧検査器との移行モードが取り除かれた。安全性の規律を保ちながら、受け入れられるプログラムを増やす方向の改善である。[NLLの移行完了に関する公式記事](https://blog.rust-lang.org/2022/08/05/nll-by-default/)

### 4.2 Polonius: 分岐や再借用を、さらに正確に追う

たとえば、次のような処理を考える。

```text
辞書から値を可変に借りる
    見つかった → その参照を返す
    見つからない → 辞書に初期値を挿入してから、参照を返す
```

片方の分岐で参照を返すことが、もう片方の分岐の挿入まで妨げる場合があった。Polonius系の解析は、こうした借用関係をより精密に追う。単に「危険な操作を許す」のではなく、安全なプログラムを解析の粗さで拒否する場面を減らす。[Polonius Alphaの公式発表と具体例](https://blog.rust-lang.org/2026/08/04/enabling-polonius-alpha-on-nightly/)

実装状況: 2026-08-04の公式発表はPolonius Alphaをnightlyで有効化し、安定化に向けて試験するとしている。調査時に参照した2026年のロードマップも安定化を目標としており、本メモでは安定版への導入完了を確認済みとは扱わない。また、Alphaと、さらに精密なFull Poloniusは区別されている。[2026年のロードマップ](https://goals.rust-lang.org/2026/roadmap-borrow-checker-within.html)

同じロードマップには、関数が構造体のどの部分にアクセスするかを表すview typesや、構造体内部への参照を扱う構想もある。これらは設計探索中の項目であり、そのまま現在のRustの機能として読んではいけない。

設計への示唆: 書きにくさの原因が、所有権そのものなのか、解析の精度なのか、関数境界で表せる情報の少なさなのかを分けて考える。

## 5. 発展の方向B: データの所有と、アクセス権限を分ける

### 5.1 ケイパビリティとは何か

ここでいうケイパビリティは、ある操作をしてよいことを表す参照や値である。参照ケイパビリティは「この参照から読み書き・共有してよいか」を制御する。オブジェクトケイパビリティは「そのオブジェクトへの参照を持つことが、どの機能への権限を与えるか」を扱う。関連はあるが、同じ制度ではない。[Ponyの参照ケイパビリティ](https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html)、[オブジェクトケイパビリティ](https://tutorial.ponylang.io/object-capabilities/object-capabilities.html)

### 5.2 Pony: 参照が持つ権限で、安全なアクター間通信を作る

Ponyはアクターモデルと参照ケイパビリティを組み合わせる。アクターは、メッセージを受け取り処理を進める実行単位である。

代表的な参照権限は、変更可能な対象を隔離して渡す`iso`、不変な対象を共有する`val`、アクター内で変更する`ref`、対象の同一性などを扱う`tag`である。これは全6種類の一部であり、単なる4分類ではない。[Pony公式の権限の説明](https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html)

`iso`を別のアクターへ渡す場合、送信元はその対象を読み書きする権限を手放す。`val`なら不変なので共有できる。対象をコピーせず渡す場面でも、別アクターからの競合アクセスを防げる。[Passing and Sharing References](https://tutorial.ponylang.io/reference-capabilities/passing-and-sharing)

この系統の発想は2015年の[Deny Capabilities for Safe, Fast Actors](https://www.doc.ic.ac.uk/~scd/fast-cheap-AGERE.pdf)に整理されている。Ponyでは回収をGCに任せるため、参照権限の静的検査と、メモリ回収方式を別々に設計できることもわかる。[PonyのGC](https://tutorial.ponylang.io/runtime-basics/garbage-collection.html)

### 5.3 GhostCell: 参照を持つことと、変更してよいことを切り離す

詳しい仕組みとコード例は、[GhostCell詳解](ghostcell.md)にまとめた。

グラフや双方向リストでは、一つのノードを複数箇所から参照したい。ところが、そのすべての参照に変更権限まで持たせると衝突する。

GhostCellは、データを保持する`GhostCell`と、アクセス権限を表す`GhostToken`を分ける。同じブランドに属するセルを、対応するトークンで操作する。読み取りにはトークンの共有借用、変更には排他的借用を要求する。

```text
複数の参照 ───→ ノードA ←──→ ノードB
                    ↑           ↑
                    └─ 対応するトークンでアクセス権限を管理する

ノードへの参照を持つだけでは、自由に変更できない。
トークンを排他的に借りた処理が、変更を実行する。
```

これにより、`RefCell`のような実行時の借用カウンタに頼らず、内部共有を持つデータ構造を扱える。ただし、ノードの生存期間や回収方式は別に決める必要がある。同じトークンで管理する複数セルへの同時の可変アクセスにも制約がある。[GhostCell論文, ICFP 2021](https://plv.mpi-sws.org/rustbelt/ghostcell/paper.pdf)

設計への示唆: データを参照する経路が多くても、変更権限まで同じように複製する必要はない。権限を別の値として管理すれば、共有構造を静的に制御する余地が生まれる。

### 5.4 Swift: 既存の言語へ、一意な資源と安全な移譲を加える

Swiftは、既存のARCによる管理に加え、必要な値についてコピーを禁止する仕組みを導入した。Swift 5.9で実装されたnoncopyableな構造体・列挙型では、`~Copyable`を使い、ファイルハンドルなどを一意に所有できる。[Swift Evolution SE-0390](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0390-noncopyable-structs-and-enums.md)

Swift 6ではnoncopyableな型とジェネリクスの組み合わせが拡充された。一意に管理すべき資源のために、常にクラスと共有所有を使う必要がなくなる。[Swift 6公式発表](https://www.swift.org/blog/announcing-swift-6/)

並行処理では、`Sendable`という型の性質と、個々の値を安全に移譲できることを区別する。Swift 6.0で実装された`sending`は、値の到達可能な領域が送信元から適切に切り離されていることを要求し、非`Sendable`な値にも隔離境界を越える道を与える。送信元に競合する利用が残る場合は拒否される。[Swift Evolution SE-0430](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0430-transferring-parameters-and-results.md)

この「領域」はオブジェクト間のつながりを解析する単位であり、後述の「一括解放するメモリ領域」とは区別する。[Swiftのregion-based isolation診断](https://docs.swift.org/compiler/documentation/diagnostics/region-isolation-cross-isolation-data-race)

設計への示唆: 「その型の値なら常に共有してよい」と「いま、この値を相手に渡してよい」は、別の問いとして表現できる。

## 6. 発展の方向C: 共有する可変状態を減らし、値を中心に考える

### 6.1 Mutable Value SemanticsとHylo

詳しくは、[Hyloと可変値意味論](hylo-mutable-value-semantics.md)を参照。コピーとムーブ、projection、借用検査、グラフの表現を掘り下げている。

値セマンティクスは、値を独立したものとして扱えるという性質である。ある値を複製した後、片方の変更がもう片方へ予期せず伝わらない、と考えるとよい。

Mutable Value Semantics（MVS）は、この独立性を保ちながら、値そのものの部分的な変更を認める。すべてを不変にする方法と、自由な共有参照を詳細な型規則で制御する方法の間に、別の設計空間を作る。[Native Implementation of Mutable Value Semantics, 2021](https://arxiv.org/abs/2106.12678)

```text
a = 値 [1, 2, 3]
b = aを複製した独立した値
bの先頭を9に変更する

aは [1, 2, 3] のまま
bは [9, 2, 3] になる
```

これは意味を説明する擬似コードであり、Hyloの代入構文や暗黙コピーの規則を表していない。意味の上で独立していても、実装で毎回全要素をコピーする必要があるとは限らない。

HyloはMVSを基礎とし、任意の場所に保存できる参照を通常のモデルから外して、ライフタイム注釈の複雑さを減らすことを目指す。一方、関数の引数やprojectionを通じた一時的なアクセスは扱う。公式紹介も、Rustの借用との意味上の対応を説明している。[Hyloの設計紹介](https://hylo-lang.org/introduction/)

利点は、ある値がどこから変更されるかを局所的に追いやすいことである。代償として、複雑な共有グラフや同一性を持つオブジェクトをどう表すか、コピーをどこで要求するかが設計課題になる。Hyloは開発中の言語として評価し、設計目標と実装済みの範囲を区別する。[Hyloの実装リポジトリ](https://github.com/hylo-lang/hylo)

### 6.2 Copy-on-Writeと「共有されていないときだけ変更する」

Copy-on-Write（CoW）は、独立した値という意味を保ちながら、変更が必要になるまで内部の記憶領域を共有する実装技法である。共有者がいなければ、その領域を直接更新できる。

所有権や一意性の情報は、この「いま直接書き換えても、ほかの値に影響しないか」の判断に使える。ただし、値セマンティクスという言語の意味と、CoWという実装方式は同義ではない。MVSの研究も、実行時の情報による不要なコピーの回避を検討している。[MVSの実装に関する論文](https://arxiv.org/abs/2106.12678)

設計への示唆: 参照を自由に持てることを最初の前提にせず、独立した値と一時的なアクセスだけで、どこまで使いやすい言語にできるかを検討する価値がある。

## 7. 発展の方向D: 自動メモリ管理を、型情報と組み合わせて改善する

### 7.1 PerceusとKoka: 関数型の書き方で、内部ではその場更新する

参照カウントは古くからある方式だが、Perceusは、制御の流れが明確な中間表現に対し、精密な参照カウント操作と再利用の解析を行う。Kokaで実装され、2021年のPLDIで発表された。

```text
意味の上では:
    新しいリスト = 元のリストの全要素を変換する

実装で再利用できるとき:
    元のノードの記憶領域を使い、更新した値を格納する
```

この方向を論文は**Functional But In-Place（FBIP）**と呼ぶ。関数型の値の変換として記述しながら、安全に再利用できる場合は、その場更新を行う。[Perceus論文の概要, PLDI 2021](https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse-2/)

論文の「garbage free」は、対象のモデルと循環のないプログラムについて、生きた参照だけを保持するという意味である。「メモリ管理の実行時コストがない」「任意の循環を自動回収する」「必ずすべての構造をその場更新する」という意味ではない。循環やスレッド間の参照カウントには追加の仕組みが必要になる。[Perceus技術報告](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/perceus-tr-v4.pdf)

設計への示唆: 所有権に関する厳密な情報を、利用者へすべて注釈させる必要はない。コンパイラ内部の解析と実行時の一意性の確認へ振り分け、表面の言語を簡潔にする設計もある。

### 7.2 リージョン・アリーナ: 個々の値ではなく、まとまりを所有する

リージョンは、複数の値をまとめて管理する領域である。アリーナは、そのような領域へ値を割り当てるためによく使われる実装方式である。たとえば構文木を解析の間だけ保持し、解析の終了時に領域全体を解放する。

型や解析によって、その領域を参照する値が外へ逃げないようにできれば、一括解放後の参照を防げる。リージョン推論はRustより前からある研究であり、Tofte–Talpinの1994年の論文が代表例である。[リージョン推論の原論文](https://www.cs.cmu.edu/afs/cs/academic/class/15745-s06/web/handouts/tofte-popl94.pdf)

領域内に循環があっても、内部の参照だけなら領域全体を解放できる。一方で、一つの値だけが不要になっても領域の終了まで保持される場合があり、個別解放よりメモリ使用量が増えることがある。

### 7.3 Verona: 領域ごとに管理方式と変更権限を選ぶ

Veronaの2023年の研究では、オブジェクトを隔離された領域の森として構成し、領域ごとにメモリ管理方式を選ぶ。スレッドが変更できる領域を制限し、その「変更可能な窓」を明示的に移動させることで、領域間の共有と並行実行を制御する。

個々のオブジェクトの所有関係をすべて追う方式とは異なり、**どの単位を隔離し、その中をどの規律で扱うか**に設計の重心を置く。ここでは研究提案として扱う。[Reference Capabilities for Flexible Memory Management, OOPSLA 2023](https://arxiv.org/abs/2309.02983)

### 7.4 OxCaml: 一つの「所有」に詰め込まず、利用の性質を複数の軸で表す

各軸の意味、modality、mode crossingについては、[OxCamlのモード詳解](oxcaml-modes.md)にまとめた。

OxCamlは、値がどのように使われるかをmodeとして追跡する。型が「何のデータか」を表すのに対し、modeは「どう使えるか」を表す、と公式ドキュメントは説明する。

代表的な軸には、領域の外へ逃げられるかというlocality、別名参照に関するuniqueness、使用回数に関するlinearity、スレッド間の利用に関するportabilityとcontentionがある。ここでのlinearityの軸には`once` / `many`があり、「必ず一度消費する」という一般的な線形型の説明と、名前だけで同一視しない。[OxCamlのmodeの概要](https://oxcaml.org/documentation/modes/intro/)、[uniquenessとaffinityの説明](https://oxcaml.org/documentation/uniqueness/intro/)

局所的な値を領域外へ逃がさないことを静的に検査できれば、局所割り当てなどの最適化に利用できる。GCを持つ言語でも、すべての値を同じ方法で管理する必要はない。ただしOxCamlの拡張を、標準のOCamlですべて利用できる機能と混同してはいけない。[OxCamlのmode reference](https://oxcaml.org/documentation/modes/reference/)

設計への示唆: 一意性、生存期間、スレッド間共有、使用回数は関連していても別の性質である。必要な軸を選び、推論可能な部分を増やす方向が考えられる。

### 7.5 世代付きハンドル: 有効性の一部を実行時に確認する

ポインタを直接保持する代わりに、`(格納位置, 世代番号)`のようなハンドルを持ち、アクセス時に対象がまだ同じ世代かを確認する方法もある。削除された場所へ別の値を入れても、古いハンドルをそのまま有効と扱わないための工夫である。

Rustの`slotmap`は、この発想をグラフのノードやゲームのエンティティに利用できるライブラリである。実際の世代番号は有限なので、周回時の意味も設計事項になる。ライブラリの説明も、周回による論理上の取り違えの可能性と、メモリ安全性を区別している。[slotmapの設計と制限](https://docs.rs/slotmap/latest/slotmap/)

言語全体の方式として探究する例にValeのgenerational referencesもある。ただし、世代検査で解放後の参照を検出できることと、データ競合や操作の論理的な誤りまで防げることは別である。[Valeの参照モデル](https://vale.dev/guide/references)、[Valeの世代検査の説明](https://vale.dev/memory-safe)

設計への示唆: すべての参照の有効性をコンパイル時に証明する設計に加え、実行時の検査で扱える構造を増やす設計も比較対象になる。その場合は、不正なアクセスをどうエラーとして返すかまで含めて考える。

## 8. 発展の方向E: メモリ以外の「資源の使い方」を型にする

### 8.1 線形型とアフィン型を区別する

| 規律 | 基本的な考え方 | 何を表現したいか |
| --- | --- | --- |
| 通常の型 | 値を複製したり使わず捨てたりできる | 一般的なデータ |
| アフィン型 | 使用は高々一回。使わずに手放すことを許す | 複製してはいけない資源 |
| 線形型 | 規定された意味で、ちょうど一回消費する | 消費・引き渡しを忘れてはいけない資源 |
| 一意性型 | 対象を一意に扱えることを保証する | 安全な破壊的更新など |

ここでの「一回」は、変数名をソース中に一度しか書けないという単純な規則ではない。借用による複数回の操作と、所有する資源の消費・引き渡しを区別する必要がある。Rustの非`Copy`な所有値の基本はアフィン的であり、一般的な意味での線形型そのものではない。[Tree Borrows論文のRustの位置づけ](https://research.ralfj.de/papers/2025-pldi-tree-borrows.pdf)、[線形型に関するWadlerの説明](https://homepages.inf.ed.ac.uk/wadler/topics/linear-logic.html)

線形型を導入しても、処理が必ず終了することや、外部機器の操作が必ず成功することまで自動で保証されるわけではない。異常終了や例外をどう扱うかを含め、言語の消費規則と対応させる必要がある。

GHCには9.0.1から`LinearTypes`拡張があり、`a %1 -> b`で線形な引数の使用を表現する。これは「GCを持つHaskellに、資源の利用規律を加える」例でもある。調査時のユーザーガイドでは実験的機能とされている。[GHCのLinearTypes](https://ghc.gitlab.haskell.org/ghc/doc/users_guide/exts/linear_types.html)

### 8.2 Typestate: 使える操作を、現在の状態で変える

所有権があるだけでは、「開いているファイルへ書く」「閉じた後は書かない」といった操作順序までは表せない。Typestateは、資源の状態を型へ反映する考え方である。

```text
open   : Path       -> File<Open>
write  : &mut File<Open>, Bytes -> Result
close  : File<Open> -> File<Closed>
```

これは説明用の擬似的なAPIである。`close`が開いたハンドルを消費し、`File<Closed>`には`write`を提供しなければ、閉じた後の書き込みを型で拒否できる。実際のAPIでは、閉じる際の失敗や、未クローズ時の後始末も設計する。[The Embedded Rust Book: Typestate Programming](https://docs.rust-embedded.org/book/static-guarantees/typestate-programming.html)

ただし、アフィンな値を単に捨てられるなら「必ずcloseを明示的に呼ぶ」ことまでは強制できない。`Drop`で自動処理するのか、線形な消費を要求するのか、エラーを返せる明示的操作を必須にするのかは別の選択である。

### 8.3 セッション型: 通信の手順を型にする

セッション型は、通信路で「何を送信し、何を受信し、どの分岐へ進むか」を表す。

```text
要求を送る → 応答を受け取る → 終了する
```

送受信後に通信路の型を次の状態へ進めれば、同じ状態の通信路を重複して使う誤りや、プロトコル上の順序の不整合を防ぎやすくなる。線形型との関係が深い分野だが、Rust以後に初めて生まれた考え方ではない。[Wadlerのセッション型関連研究](https://homepages.inf.ed.ac.uk/wadler/topics/linear-logic.html)

デッドロック不在や通信の進行まで保証するかは、型システムと通信モデルによる。セッション型を使えば、ネットワーク障害や任意の待ち合わせがすべて解決する、と一般化してはいけない。

設計への示唆: 所有権の対象をメモリブロックに限定しなければ、トランザクション、ロック、通信路、デバイスなどの操作を、型で導けるAPIへ広げられる。

## 9. 発展の方向F: 関数の副作用と、保持する権限を追う

### 9.1 エフェクトシステム: 何をする関数かも表す

通常の関数型が入力と出力を表すのに対し、エフェクトシステムは、入出力、例外、状態変更などの作用も表す。

```text
parse    : Text -> AST                  // 入出力をしない計算
load     : Path -> AST ! {IO, Error}    // 入出力と失敗を伴う計算
```

この表記は説明用であり、特定の言語の構文ではない。所有権が「この値を誰が使えるか」を問うのに対して、エフェクトは「この計算は何を起こすか」を問う。

Kokaは、型と効果の推論、および効果多相を研究・実装してきた。効果ハンドラを組み合わせると、同じ操作の記述に、異なる実行方法を与えられる。たとえば、出力を実際の画面表示にするか、テスト用の記録にするかを切り替えるような使い方である。[Kokaの効果型の研究](https://www.microsoft.com/en-us/research/publication/koka-programming-with-row-polymorphic-effect-types/)、[Koka公式ドキュメント](https://koka-lang.github.io/koka/doc/book.html)

効果の理論はRust以前からあり、所有権の後継に置き換わるものではない。Perceusのように、効果や制御の流れの情報をメモリ管理へ利用する組み合わせもある。[Perceus技術報告](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/perceus-tr-v4.pdf)

### 9.2 キャプチャ検査: 閉じ込めたつもりの権限が、外へ逃げないか

あるスコープ内だけでファイルを使わせる関数があっても、コールバックがファイルを保持するクロージャを返すと、閉じた後の操作が可能になってしまう。

```text
withFile(path, file =>
    return () => file.read() // ファイルを使う権限を、戻り値に持ち出している
)
```

Scala 3のcapture checkingは、値やクロージャがどのケイパビリティへアクセスできるかを型に記録する。単なる引数・戻り値の型だけでは見えない、閉じ込められた参照を追う仕組みである。[ScalaのCapture Checking Basics](https://docs.scala-lang.org/scala3/reference/experimental/capture-checking/basics.html)

さらにseparation checkingでは、変更可能なデータと読み書きの権限の分離を扱う。調査時点の公式資料では、これらは実験的拡張として説明されている。[Tracked Capabilities Overview](https://docs.scala-lang.org/scala3/reference/experimental/capture-checking/overview.html)

設計への示唆: 一時的に渡した資源や権限は、クロージャ、オブジェクトのフィールド、遅延計算を通しても逃げうる。関数呼び出しの表面だけでなく、戻り値が何を保持するかまで考える必要がある。

## 10. 発展の方向G: 安全性の根拠を形式化し、検査可能にする

詳しくは、[unsafeの発展](unsafe-and-beyond.md)を参照。Unsafe Fields、Safety Tags、検証ツール、他言語の設計、隔離技術まで調査している。

### 10.1 RustBelt: 安全な抽象化の内部をどう信頼するか

RustBeltは、Rustを代表する部分言語について安全性を機械検証し、内部で`unsafe`を使うライブラリが、安全な拡張であるために満たすべき条件を示した研究である。基盤には、メモリとアクセス権限を論理的に扱うseparation logicがある。

これは現行のRust全体、コンパイラ全体、すべてのクレートが検証済みだという主張ではない。言語の規則と、安全なAPIの実装の間に、検証可能な接続を作る仕事として重要である。[RustBelt, POPL 2018](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf)

### 10.2 Stacked Borrows / Tree BorrowsとMiri

借用検査器が安全なコードを受け入れるかどうかと、生ポインタを操作する`unsafe`コードのどの実行が許されるかは、別の問題である。

Stacked BorrowsとTree Borrowsは、参照やポインタの別名参照について、許される実行を定義するモデルである。2025年のTree Borrowsの研究は、従来のモデルでは拒否していた実用上のパターンを許しつつ、最適化を正当化することを目指した。[Tree Borrowsの研究紹介](https://plf.inf.ethz.ch/research/pldi25-tree-borrows.html)

Miriは、プログラムを実行して未定義動作を検出するツールで、こうした別名参照規則も実験的に検査する。実行していない経路まで正しいと証明するものではなく、実験的モデルをRustの確定した規範的仕様とも同一視しない。[Miriの説明](https://github.com/rust-lang/miri)、[Tree Borrowsの非規範的な実装メモ](https://github.com/rust-lang/unsafe-code-guidelines/blob/master/wip/tree-borrows.md)

Poloniusが主に**静的な解析の精度**を改善するのに対し、Tree Borrowsは主に**許される実行の意味**を扱う。この二つを、同じ借用検査器の候補として比較するのは適切ではない。

### 10.3 Aeneas: 所有権の制約を、プログラムの証明に利用する

Aeneasの2022年の研究では、Rustの所有・借用に関する制約を利用し、対象プログラムを純粋な関数的表現へ翻訳して検証する。元論文の対象には、`unsafe`や内部可変性などに制限がある。

こうした方法は、メモリの別名参照について繰り返し証明する負担を減らし、アルゴリズムが期待した結果を返すかという性質へ集中しやすくする。[Aeneas: Rust Verification by Functional Translation](https://arxiv.org/abs/2206.07185)

設計への示唆: 型の制約は、危険なプログラムを拒否するためだけでなく、最適化、APIの推論、プログラムの正しさの証明を助ける情報にもなる。

## 11. 比較表: 何を得て、何を引き受けるか

各方式には多数の変種がある。次の表は、前節までの資料をもとに比較軸を整理したもので、実行速度の順位表ではない。

| 方式・方向 | 主な利点 | 主な代償・設計課題 | 例・位置づけ |
| --- | --- | --- | --- |
| 所有権と静的借用 | 参照の有効性と排他性を実行前に検査する | 複雑な共有構造の表現、注釈、保守的な拒否 | Rustの基本機能 |
| GC | 多様な共有・循環構造を扱いやすい | 回収の実行時コスト、回収時期、外部資源の別管理 | 他の権限制御と併用可能 |
| 参照カウント | 共有所有を表し、最後の所有参照の消滅を追える | カウント更新、循環、解放処理の集中 | `Rc` / `Arc`、ARC |
| 精密な参照カウントと再利用 | 関数型の記述と記憶領域の再利用を結びつける | 解析、実行時の共有状態、循環などの扱い | Perceus / Koka |
| リージョン・アリーナ | 一群の値をまとめて管理する | 生存期間の異なる値の混在、領域外参照 | 古典的研究から現行の実装技法まで |
| 参照ケイパビリティ・隔離 | 読み書きや並行処理の権限を制御する | 権限の種類・変換規則、隔離境界の理解 | Pony、Swiftの移譲機能 |
| データと権限トークンの分離 | 内部共有を持つ構造を静的に制御する | トークンの管理、同時アクセスの制約 | GhostCellの研究・API |
| Mutable Value Semantics | 共有可変状態を減らし、局所的に推論する | 共有グラフの表現、コピーの規則と費用 | Hyloなどの開発・研究 |
| modeによる分類 | 生存・共有・利用回数を複数の軸で表す | 軸どうしの相互作用、推論・診断の複雑さ | OxCamlの拡張 |
| 世代付きハンドル | 動的に変わる参照関係を安全なアクセスAPIで扱う | 参照時の検査、無効化エラー、世代の周回 | slotmap、Valeの設計 |
| 線形型・typestate・セッション型 | 消費や操作順序を型へ反映する | 例外・分岐・中断、外部世界との整合 | GHC拡張、RustのAPI設計、通信の研究 |
| 効果・キャプチャ検査 | 関数の作用や持ち出す権限を可視化する | 高階関数の推論、既存APIとの接続 | Koka、Scalaの実験的拡張 |
| 形式化と検証 | 安全性・最適化・機能的正しさの根拠を明確にする | モデルと実装の隔たり、証明と保守の費用 | RustBelt、Tree Borrows、Aeneas |

性能は、割り当て方、共有の形、値の大きさ、スレッド数、コンパイラ、作業負荷で変わる。「静的方式だから常に最速」「GCだから必ず遅い」といった一般化では設計を選べない。

## 12. このリポジトリの言語設計へどうつなげるか

以下は調査を踏まえた検討案であり、採用決定ではない。

### 12.1 最初に決めるのは、利用者へ何を保証したいか

小さな仕様と理解しやすい処理系を目指すなら、最初からRustと同程度の機能をすべて再現することを目標にする必要はない。まず、次の問いへ答えると候補を絞りやすい。

1. メモリ安全性を、どこまでコンパイル時に保証するか。
2. 任意の共有グラフや循環構造を、通常のコードで扱いたいか。
3. ファイルやロックの解放時点を、言語の規則として予測可能にしたいか。
4. 並行処理では、共有メモリ、メッセージ移譲、不変値の共有のどれを中心にするか。
5. 学習しやすさ、処理系の小ささ、性能の予測可能性のどれを優先するか。

### 12.2 小さく試すなら、三つの独立した試作が考えられる

| 試作 | 最小限の仕組み | 確かめたいこと |
| --- | --- | --- |
| A: 自動回収と資源のスコープ管理 | メモリは既存ランタイムへ任せ、ファイルなどには明示的なスコープ管理を用意する | 利用者の負担と実装量を小さくできるか |
| B: 値中心の設計 | 独立した値、明示的な複製、関数呼び出し中だけの排他的な変更 | 永続的な借用参照を入れずに、十分な表現力が得られるか |
| C: 小さな所有権モデル | ムーブ、破棄、限定された借用。任意の借用参照の保存は後回しにする | 規則と診断を理解できる範囲に保てるか |

これらは性能の順位を競う試作ではなく、利用者がどこでつまずくか、どれだけの規則が必要になるかを比較するためのものとする。GCを使う案でも、ファイルのcloseやロックの解放は、メモリ回収と別に検討する。

### 12.3 同じ例題で、表現と失敗の仕方を比べる

- **木・構文木**: 領域単位の管理で、どれだけ簡潔に書けるか。
- **親への参照を持つ木・一般グラフ**: 循環、削除、無効な参照をどう扱うか。
- **ファイル処理**: 成功、途中の失敗、例外のそれぞれで、解放をどう説明するか。
- **共有キャッシュ**: 値の複製、CoW、共有所有、ロックのどこに費用が現れるか。
- **タスク間のデータ移譲**: 渡した後の送信元の操作を、どう制限するか。
- **クロージャを返す関数**: 局所的な参照や権限が外へ逃げないか。

見るべきなのは、正常な例の短さだけではない。誤ったコードがいつ拒否され、どんな説明を受けるか、実行時に失敗する場合はどう回復するかも含めて比較する。

### 12.4 引き続き調べたい問い

1. 借用を関数呼び出しの間に限定した場合、どの実用例で表現力が足りなくなるか。
2. グラフのノードを所有する領域と、ノードを指す世代付きハンドルで、処理系をどこまで小さくできるか。
3. 外部資源にはアフィン型、自動回収するデータには通常の型という組み合わせが、利用者に理解しやすいか。
4. 例外、非同期処理のキャンセル、効果ハンドラによる処理の中断・再開を加えたとき、消費と後始末の規則をどう保つか。
5. 権限トークンやmodeを、明示的な注釈を増やしすぎずに導入できるか。
6. 仕様、静的検査器、実行器の三つで、安全性の説明が食い違わない最小のモデルを作れるか。

## 13. 読む順序の案

全体を理解するには、まず2節で所有と借用を区別し、3節で歴史を確認する。その後、関心に応じて以下の順で一次資料へ進むとよい。

- **Rustの基本を知る**: [所有権](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) → [借用](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) → [ライフタイム](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)。
- **借用検査の先を知る**: [NLL](https://blog.rust-lang.org/2022/08/05/nll-by-default/) → [Polonius Alpha](https://blog.rust-lang.org/2026/08/04/enabling-polonius-alpha-on-nightly/) → [将来のロードマップ](https://goals.rust-lang.org/2026/roadmap-borrow-checker-within.html)。
- **共有と並行処理を考える**: [Ponyの参照共有](https://tutorial.ponylang.io/reference-capabilities/passing-and-sharing) → [Swiftのsending](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0430-transferring-parameters-and-results.md) → [GhostCell](https://plv.mpi-sws.org/rustbelt/ghostcell/paper.pdf)。
- **簡潔な言語モデルを探る**: [Hyloの紹介](https://hylo-lang.org/introduction/) → [Perceusの概要](https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse-2/) → [OxCamlのmode](https://oxcaml.org/documentation/modes/intro/)。
- **メモリ以外へ広げる**: [Typestate](https://docs.rust-embedded.org/book/static-guarantees/typestate-programming.html) → [Kokaの効果型](https://www.microsoft.com/en-us/research/publication/koka-programming-with-row-polymorphic-effect-types/) → [Scalaのキャプチャ検査](https://docs.scala-lang.org/scala3/reference/experimental/capture-checking/basics.html)。
- **保証の根拠を追う**: [RustBelt](https://plv.mpi-sws.org/rustbelt/popl18/paper.pdf) → [Tree Borrows](https://plf.inf.ethz.ch/research/pldi25-tree-borrows.html) → [Aeneas](https://arxiv.org/abs/2206.07185)。
