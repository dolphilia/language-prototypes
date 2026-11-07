# GhostCell詳解 — データとアクセス権限を分離する

[メモの一覧へ](README.md) · [所有権とその先](ownership-and-beyond.md) · [リポジトリの目次へ](../../README.md)

調査日: **2026-11-07**

対象: ICFP 2021のGhostCell研究と、公開クレート`ghost-cell` **0.2.6**。コード例はこの版を前提とする。論文の研究用実装、公開クレートの基本API、実験的な拡張を区別して説明する。

## 目次

- [まず何を実現するものか](#1-まず何を実現するものか)
- [解決したい問題](#2-解決したい問題)
- [セル・トークン・ブランド](#3-セルとトークンとブランドの三つに分ける)
- [最小のコード例](#4-最小のコード例)
- [なぜ安全にできるのか](#5-なぜ安全にできるのか)
- [ブランドを作る仕組み](#6-ブランドを作る仕組み)
- [循環するデータ構造の例](#7-循環するデータ構造の例)
- [使い方に現れる制約](#8-使い方に現れる制約)
- [スレッド間での利用](#9-スレッド間での利用)
- [性能とゼロコストの意味](#10-性能とゼロコストの意味)
- [形式検証の範囲](#11-形式検証の範囲)
- [他の方式との比較](#12-他の方式との比較)
- [言語設計への示唆](#13-このリポジトリの言語設計への示唆)
- [資料とコード例の確認方法](#14-資料とコード例の確認方法)

## 1. まず何を実現するものか

GhostCellは、**データを指す参照と、その中身へアクセスする権限を別々に管理する、Rust向けのライブラリAPI**である。

グラフや双方向リストのように、一つのノードへ複数の経路から到達できるデータ構造を、安全なAPIを使って変更するための研究から生まれた。Joshua Yanovski、Hoang-Hai Dang、Ralf Jung、Derek Dreyerによる論文がICFP 2021で発表され、RustBeltプロジェクトの一部として公開されている。[研究プロジェクトのページ](https://plv.mpi-sws.org/rustbelt/ghostcell/)

理解の中心になるのは、次の一文である。

**同じデータを指す参照はいくつ持っていてもよいが、中身を変更するには、対応するトークンを排他的に借りなければならない。**

Rustの借用検査器を変更するのではなく、既存の型・ライフタイム・借用規則に、ライブラリ側のAPIを組み合わせる。公開クレートでは通常のRustコードから利用できる。[公開実装のREADME](https://github.com/matthieu-m/ghost-cell)

### このメモで分けて考える三つの責任

| 責任 | 具体的な問い | 担当するもの |
| --- | --- | --- |
| データの所有と回収 | ノードを誰が保持し、いつ破棄するか | `Box`、`Rc`、`Arc`、アリーナなど |
| データへの到達 | どのノードから、どのノードを参照するか | 参照、リンク、ハンドルなど |
| 中身へのアクセス権限 | いま、そのノードを読んだり変更したりできるか | `GhostCell`と`GhostToken` |

GhostCellの主題は三つ目である。この区別を保つと、「循環参照を扱える」と「循環した所有関係を自動で回収する」を混同せずに済む。これは本メモ全体を読むための整理である。

## 2. 解決したい問題

### 2.1 参照が増えると、普通の変更が難しくなる

木であれば、根から子へ向かって所有権を持たせる設計が自然である。一方、親への参照や隣接ノードへの参照も必要になると、一つのノードへ複数の経路からアクセスすることになる。

```text
木に親への参照も付けると:

       親
      /  \
     ↓    ↓
    子A  子B
     └─→ 親 ←─┘

親や子を指す参照が、別々の場所に存在する。
それでも、ノードの値やリンクを変更したい。
```

Rustの通常の共有参照`&T`は、そこから中身を自由に変更する権限を与えない。そのため、こうした構造では内部可変性の仕組みがよく使われる。[Rust公式: 内部可変性](https://doc.rust-lang.org/book/ch15-05-interior-mutability.html)

### 2.2 RefCellなら、衝突の確認を実行時に行う

`Rc<RefCell<Node>>`なら、`Rc`が共有所有を、`RefCell`が借用状態の検査を担当する。異なるセルなら、それぞれを同時に可変借用することもできる。

ただし、同じセルを読み取り中に可変借用するなど、借用規則に違反した場合は、`borrow_mut`が実行時にpanicする。`try_borrow_mut`ならエラーとして扱える。[RefCellのAPI](https://doc.rust-lang.org/std/cell/struct.RefCell.html)

GhostCellは、借用の衝突を確認する場所を、セルごとの実行時状態から、**トークンに対するコンパイル時の借用検査**へ移す。

## 3. セルとトークンとブランドの三つに分ける

### 3.1 GhostCell: データを包む

`GhostCell<'brand, T>`は、型`T`の値を包む。参照先の中身を変更できるかどうかは、セルへの共有参照だけでは決まらない。

### 3.2 GhostToken: アクセス権限を表す

`GhostToken<'brand>`は、同じブランドのセル群へアクセスするための権限を表す。一つのトークンで、整数のセル、文字列のセル、ノードのセルなど、異なる型のセルをまとめて管理できる。[GhostTokenのAPI](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostToken.html)

### 3.3 ブランド: 対応関係を型で表す

`'brand`は、そのセルとトークンが対応することを表す印である。実行時の文字列や整数IDではなく、Rustのライフタイム引数を利用する。

```text
同じブランド 'b

  参照1 ──→ GhostCell<'b, NodeA> ──→ NodeAのデータ
  参照2 ──→       ↑
  参照3 ──→ GhostCell<'b, NodeB> ──→ NodeBのデータ

  GhostToken<'b>
     &token      → 中身の共有借用 &T を得る
     &mut token  → 中身の排他的借用 &mut T を得る
```

`&GhostCell`を持つことと、`&T`を得ることは別である。前者は「箱の場所を知っている」、後者は「いま中身を読む権限を持つ」に対応する。この区別は、変更中にもセル自体への参照を保持できる理由になる。[GhostCellの借用API](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostCell.html)

## 4. 最小のコード例

Cargoの依存関係を次のように指定する。クレート名はハイフン付きの`ghost-cell`、Rustコードでの名前はアンダースコアの`ghost_cell`である。

```toml
[dependencies]
ghost-cell = "=0.2.6"
```

次のプログラムでは、二つの共有参照から同じセルを指し、一方を使って変更した結果を、もう一方から読み取る。

```rust
use ghost_cell::{GhostCell, GhostToken};

fn main() {
    let answer = GhostToken::new(|mut token| {
        let cell = GhostCell::new(10);
        let first = &cell;
        let second = &cell;

        *first.borrow_mut(&mut token) += 5;

        // 中身への可変借用はすでに終わっている。
        *second.borrow(&token)
    });

    assert_eq!(answer, 15);
    println!("{answer}");
}
```

出力は`15`になる。`cell`自体を`mut`と宣言する必要はない。変更する際に排他的に借りるものは、この呼び出しでは`token`だからである。

`GhostToken::new`はトークンを直接返さず、トークンを受け取るクロージャを実行する。新しく生成されたブランドを、そのクロージャの内側で使わせるためのAPIになっている。[GhostToken::new](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostToken.html#method.new)

## 5. なぜ安全にできるのか

### 5.1 中心となるのは、二つの関数の型

型の関係を見やすく書くと、基本APIは次の形を持つ。ここでは実装本体を省略している。

```text
borrow<'a>(
    &'a GhostCell<'brand, T>,
    &'a GhostToken<'brand>
) -> &'a T

borrow_mut<'a>(
    &'a GhostCell<'brand, T>,
    &'a mut GhostToken<'brand>
) -> &'a mut T
```

戻り値の`'a`が、セルとトークンの両方の借用に結びついている。中身への参照を使い続ける間、必要なセルとトークンの借用も維持される。[0.2.6の基本API実装](https://docs.rs/ghost-cell/0.2.6/src/ghost_cell/ghost_cell.rs.html)

### 5.2 共有読み取りは、複数あってよい

読み取りに必要な`&GhostToken`は共有できる。同じブランドの複数セルから、同時に`&T`を得られる。

### 5.3 変更する間は、トークンをほかのアクセスへ使えない

変更には`&mut GhostToken`が必要になる。中身への可変参照を使っている間、同じトークンを使う新しい共有借用・可変借用は作れない。

```rust,compile_fail
use ghost_cell::{GhostCell, GhostToken};

fn main() {
    GhostToken::new(|mut token| {
        let cell = GhostCell::new(10);
        let reading = cell.borrow(&token);

        *cell.borrow_mut(&mut token) = 20; // エラー: tokenは共有借用中

        println!("{reading}"); // この使用まで、共有借用が必要
    });
}
```

`reading`を最後に使う行を、変更の前へ移せば、この衝突は解消できる。コンパイラは、変数の宣言だけでなく、参照が必要とされる範囲を調べる。

### 5.4 内部ではUnsafeCellを使う

公開実装は、中身の格納に`UnsafeCell<T>`を使う。これは共有参照を通じた内部可変性の基盤である。ただし、`UnsafeCell`自体には借用の衝突やデータ競合を防ぐ機能はない。[UnsafeCellの安全性と別名参照規則](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html)

GhostCellの実装者は、トークンとブランドの規則によって、内部の生ポインタから安全な`&T`や`&mut T`を作れることを保証する。利用者のコード例には`unsafe`が現れなくても、ライブラリ内部には`unsafe`がある。

### 5.5 トークンなしで使える経路もある

セルそのものを排他的に借りられる場合は、`get_mut(&mut self)`から中身の`&mut T`を得られる。セルを所有している場合は、`into_inner(self)`で値を取り出せる。

したがって、「トークンなしでは、いかなる状況でも中身に触れない」という説明は強すぎる。**共有されたセルの中身へアクセスするときに、別のトークンで権限を管理する**のが中心である。[get_mutとinto_inner](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostCell.html#method.get_mut)

## 6. ブランドを作る仕組み

この節は、基本的な使い方を理解するうえでは後から読んでもよい。

ブランドを使う発想には、HaskellのSTモナドなど、型付き関数型言語での先行技法がある。GhostCellの研究は、その発想をRustの借用と組み合わせて利用する。[研究の位置づけ](https://plv.mpi-sws.org/rustbelt/ghostcell/)

### 6.1 なぜライフタイムを識別の印にできるのか

普通のライフタイム引数は、参照の有効期間の関係を表す。GhostCellでは、その機能を使って、セルとトークンの対応関係も表す。

重要なのは、「同じ時間だけ生きていれば同じブランド」という意味ではないことである。異なる呼び出しから作られたブランドを、都合よく同じものとして扱えないようにAPIを設計する。

### 6.2 for<'brand>で、呼び出し側に選ばせない

`GhostToken::new`が受け取るクロージャには、概念的に次の条件が付く。

```text
for<'brand> FnOnce(GhostToken<'brand>) -> R
```

`for<'brand>`は「どのブランドを渡されても処理できる」という条件である。クロージャ側が、あらかじめ都合のよいブランドを指定することを許さない。このような高階の量化を、higher-ranked trait bound（HRTB）と呼ぶ。[Rust Reference: higher-ranked trait bounds](https://doc.rust-lang.org/reference/trait-bounds.html#higher-ranked-trait-bounds)

この仕組みと、ブランドの不変性、トークンの生成経路の制限を組み合わせて、呼び出しごとに区別されるブランドを扱う。実行時に番号を発行して照合する方式ではない。[GhostTokenのコンストラクタ実装](https://docs.rs/ghost-cell/0.2.6/src/ghost_cell/ghost_cell.rs.html)

### 6.3 不変性で、ブランドの取り替えを防ぐ

Rustでは、長く有効な共有参照を、より短い期間だけ使うことができる。しかしブランドまで自由に短縮して合わせられると、別のトークンを同じセルへ対応させてしまう危険がある。

そのため、公開実装はブランドをinvariant（不変）にするマーカーを持つ。0.2.6では、次の形の`PhantomData`が使われている。

```text
PhantomData<fn(&'brand ()) -> &'brand ()>
```

関数の入力と出力に同じライフタイムを使い、ブランドに関する都合のよい型変換を防ぐ。`PhantomData`自体が実際の関数や参照を格納するわけではない。[実装のInvariantLifetime](https://docs.rs/ghost-cell/0.2.6/src/ghost_cell/ghost_cell.rs.html)、[Rustonomiconのvarianceの説明](https://doc.rust-lang.org/nomicon/subtyping.html)、[PhantomData](https://doc.rust-lang.org/std/marker/struct.PhantomData.html)

### 6.4 ブランド・セルの寿命・借用期間は同じではない

| 情報 | 何を表すか |
| --- | --- |
| `'brand` | どのセルとトークンが対応するか |
| セル自体の生存期間 | セルを格納する変数・所有者が、いつまで有効か |
| `borrow`の`'a` | 得られた中身の参照を、どの範囲で使えるか |

ブランドが合っていても、すでに破棄されたセルへアクセスしてよいことにはならない。実際の参照先の有効性も、通常のRustの借用規則で守られる。

### 6.5 ゼロサイズでも、トークンを自由に複製してよいわけではない

トークンは`Copy`や`Clone`を実装していない。記憶領域をほとんど必要としないことと、同じ権限を自由に複製できることは別である。通常のムーブでトークンを渡す場合も、元の変数から引き続き同じ値を使えるわけではない。[GhostTokenの実装するtrait](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostToken.html)

また、トークン自身がセル群を格納・所有しているわけではない。トークンを破棄することを、セル群の一括解放と同一視してはいけない。

## 7. 循環するデータ構造の例

次の例は、二つのノードが互いを指す小さなグラフである。GhostCellのAPIを説明するために、本メモ用に作成した。

設計を三つに分けている。

- ノードの生存は、変数`a`と`b`が保持する`Rc`で支える。
- グラフの辺は`Weak`で表し、辺そのものはノードを生存させない。
- ノードの訪問回数やリンクの変更は、同じトークンで制御する。

```rust
use ghost_cell::{GhostCell, GhostToken};
use std::rc::{Rc, Weak};

type Link<'brand> = Rc<GhostCell<'brand, Node<'brand>>>;

struct Node<'brand> {
    name: &'static str,
    visits: u32,
    next: Option<Weak<GhostCell<'brand, Node<'brand>>>>,
}

fn make_node<'brand>(name: &'static str) -> Link<'brand> {
    Rc::new(GhostCell::new(Node {
        name,
        visits: 0,
        next: None,
    }))
}

fn main() {
    GhostToken::new(|mut token| {
        let a = make_node("A");
        let b = make_node("B");

        a.borrow_mut(&mut token).next = Some(Rc::downgrade(&b));
        b.borrow_mut(&mut token).next = Some(Rc::downgrade(&a));

        let mut current = Rc::clone(&a);
        for _ in 0..4 {
            {
                let node = current.borrow_mut(&mut token);
                node.visits += 1;
                println!("{}: {}", node.name, node.visits);
            } // 中身への可変借用を終える

            let next = current
                .borrow(&token)
                .next
                .as_ref()
                .and_then(Weak::upgrade)
                .expect("aとbが、この例のノードを生存させている");
            current = next;
        }

        assert_eq!(a.borrow(&token).visits, 2);
        assert_eq!(b.borrow(&token).visits, 2);
    });
}
```

出力:

```text
A: 1
B: 1
A: 2
B: 2
```

複数の`Rc`や`Weak`が同じノードを指しても、中身を操作する権限はトークンで管理される。`Rc`の参照カウントや`Weak::upgrade`の処理がなくなるわけではない。

もし辺もすべて強い`Rc`にして、ノード同士の循環だけで互いを所有させれば、GhostCellを使っていてもリークしうる。`Weak`は対象の値を生存させず、`upgrade`はすでに値が破棄されていれば`None`を返す。[標準ライブラリのWeakの説明](https://doc.rust-lang.org/std/rc/struct.Weak.html)

実際のグラフライブラリでは、ノード集合を所有するコンテナを設ける、アリーナでまとめて保持するなど、用途に応じた所有モデルを選ぶ必要がある。

## 8. 使い方に現れる制約

### 8.1 同じトークンの別セルも、アクセスが連動する

基本の`borrow_mut`では、セルAの中身を可変借用すると、トークン全体を可変借用する。その参照を使っている間は、同じトークンでセルBの中身を新しく借用することもできない。

```rust,compile_fail
use ghost_cell::{GhostCell, GhostToken};

fn main() {
    GhostToken::new(|mut token| {
        let a = GhostCell::new(10);
        let b = GhostCell::new(20);

        let left = a.borrow_mut(&mut token);
        let right = b.borrow_mut(&mut token); // エラー: tokenを再び可変借用

        *left += *right; // leftとrightの両方が必要
    });
}
```

`a`と`b`が別のセルでも、この書き方は拒否される。セルごとに独立した借用状態を持つ`RefCell`との大きな違いである。

一方、順に処理して前の借用を終わらせればよい場合は、基本APIで扱える。単に数値を読み取るだけなら、値をコピーしてから変更する方法もある。

複数フィールドを同時に変更したいだけなら、`GhostCell<(A, B)>`のように一つの値へまとめ、一度の可変借用から通常のフィールド分割を使う設計も考えられる。これはトークンを分裂させる方法ではなく、借用の単位を選び直す方法である。

### 8.2 複数の可変借用をまとめて取得する拡張

公開クレート0.2.6には、`experimental-multiple-mutable-borrows`という明示的なfeatureがある。これを有効にすると、`GhostBorrowMut`から複数の可変借用を一度に得るAPIを使える。[クレートのfeature定義](https://docs.rs/crate/ghost-cell/0.2.6/source/Cargo.toml)

```toml
[dependencies]
ghost-cell = { version = "=0.2.6", features = ["experimental-multiple-mutable-borrows"] }
```

以下は、このfeatureを有効にした場合だけのコード例である。

```rust
use ghost_cell::{GhostBorrowMut, GhostCell, GhostToken};

fn main() {
    GhostToken::new(|mut token| {
        let a = GhostCell::new(10);
        let b = GhostCell::new(20);

        {
            let (left, right) = (&a, &b).borrow_mut(&mut token).unwrap();
            *left += *right;
            *right = 0;
        }

        assert_eq!(*a.borrow(&token), 30);
        assert_eq!(*b.borrow(&token), 0);

        // 同じセルを二重に指定した場合は、参照を返さずエラーにする。
        assert!((&a, &a).borrow_mut(&mut token).is_err());
    });
}
```

参照の組`(&a, &b)`は、実際には同じ場所を指す可能性がある。そのため、この経路では実行時に重複・重なりを検査する。対して、セルが格納された配列・スライスなど、構造上の非重複を利用できる経路もある。**拡張のすべての呼び出しを、検査コストなしと説明してはいけない。**

この説明と上の例は、配布された0.2.6の`src/ghost_borrow_mut.rs`を確認したもの。取得したソースのコミットは`956df44625bda13793defc4a826431ad9ab7789c`である。[対応する複数借用の実装](https://github.com/matthieu-m/ghost-cell/blob/956df44625bda13793defc4a826431ad9ab7789c/src/ghost_borrow_mut.rs)

実験的拡張について、クレートの説明は設計・実装の形式証明がないことを明記している。論文で示された基本方式の安全性を、そのまま拡張全体の検証済みという意味に広げない。[クレートのSafety節](https://docs.rs/ghost-cell/0.2.6/ghost_cell/#safety)

### 8.3 新しく生成されたブランドを、そのまま外へ返せない

新しいトークンと結びついたセルを、`GhostToken::new`の戻り値としてそのまま取り出そうとすると拒否される。

```rust,compile_fail
use ghost_cell::{GhostCell, GhostToken};

fn main() {
    let _outside = GhostToken::new(|mut token| {
        let cell = GhostCell::new(10);
        *cell.borrow_mut(&mut token) = 15; // このトークンのブランドに結びつける
        cell // エラー: 新しく生成されたブランドを外へ持ち出す
    });
}
```

4節のように、ブランドを含まない計算結果を返すことはできる。中身を所有したセルから`into_inner`で取り出した値も、その値自身が新しいブランドに依存しなければ返せる。[GhostToken::newの制約](https://docs.rs/ghost-cell/0.2.6/ghost_cell/ghost_cell/struct.GhostToken.html#method.new)

クロージャ内でトークンとセル群を同じ構造体へ格納すること自体が、一律に禁止されるわけではない。難しいのは、新しく生成するブランドを隠したまま、通常のコンストラクタの戻り値として外へ提供するようなAPIである。処理をクロージャへ渡す設計や、呼び出し側からトークンを受け取る設計が必要になることがある。

### 8.4 同じブランドは、同じグラフという意味ではない

同じブランドのセル群は、同じトークンで管理されるというだけである。二つの独立したグラフを同じブランドに属させることもできるが、その場合はアクセス権限の制約も共有する。

別ブランドに分ければ権限を分離できる一方で、ブランドをまたぐリンクや、動的に生成する多数のグラフを一様な型のコンテナへまとめるAPIは難しくなる。ブランドの粒度は、安全性だけでなく使い勝手と並行性にも関係する。これは基本APIから読み取れる設計上のトレードオフである。

### 8.5 可変参照を保持する走査には注意が必要

「次のノードへ進むための参照を、中身の借用から取り出す」「その後で同じトークンを可変借用する」という操作は、参照の生存期間によって拒否される場合がある。

7節では、ノードを所有する`Rc`を手元に保持し、次のノードへ進む際にも`Weak::upgrade`で新しい`Rc`を得ている。中身の借用から得た参照を、そのまま次の変更まで持ち越す設計を避けている。

公開実装には`experimental-ghost-cursor`もあるが、追加の安全性検討が必要な拡張として扱われている。特に、あるノードの変更によって別ノードの最後の所有経路を消せる場合、単なる参照だけを残すと解放後使用につながりうる。基本APIの制約を、無条件に迂回してよいわけではない。[GhostCursorの実装と安全性の説明](https://github.com/matthieu-m/ghost-cell/blob/956df44625bda13793defc4a826431ad9ab7789c/src/ghost_cursor.rs)

## 9. スレッド間での利用

### 9.1 トークンを共有して、並行に読む

0.2.6では、`GhostToken`は`Send`と`Sync`を実装する。`GhostCell<T>`については、`Send`に`T: Send`、`Sync`に`T: Send + Sync`が必要になる。中に任意の型を入れれば、そのままスレッド間共有できるわけではない。[Send / Syncの実装](https://docs.rs/ghost-cell/0.2.6/src/ghost_cell/ghost_cell.rs.html)

次の例は、スコープ付きスレッドで読み取りを共有し、両方のスレッドが終わってから変更する。

```rust
use ghost_cell::{GhostCell, GhostToken};

fn main() {
    GhostToken::new(|mut token| {
        let cell = GhostCell::new(10);

        std::thread::scope(|scope| {
            let first = scope.spawn(|| *cell.borrow(&token));
            let second = scope.spawn(|| *cell.borrow(&token));
            assert_eq!(first.join().unwrap() + second.join().unwrap(), 20);
        });

        *cell.borrow_mut(&mut token) += 1;
        assert_eq!(*cell.borrow(&token), 11);
    });
}
```

`std::thread::scope`は、スレッドがスコープ内のデータを借り、スコープ終了までに終了する使い方を提供する。そのため、この例ではブランドを含む値に`'static`を要求する必要がない。[スコープ付きスレッド](https://doc.rust-lang.org/std/thread/fn.scope.html)

### 9.2 複数の書き手を、自動で同時実行させる仕組みではない

トークンの共有参照を配れることと、トークンの可変参照を複数配れることは別である。基本APIのまま、同じトークンを使う複数の書き手へ同時に権限を与えることはできない。

実行時に権限を受け渡したい場合には、`Mutex<GhostToken<_>>`や`RwLock<GhostToken<_>>`などと組み合わせる設計も考えられる。ロックをセルごとに置くのか、セル群を管理するトークンに置くのかによって、競合と処理のまとめやすさが変わる。類似のcell-owner方式について、qcellもこの比較を説明している。[qcellのRwLockとの比較](https://docs.rs/qcell/0.5.5/qcell/#multi-threaded-use-rwlock)

GhostCellを使うだけで、あらゆる並行処理がロック不要になるとはいえない。どの権限を、どの実行単位へ、いつ渡すかの設計は残る。

## 10. 性能とゼロコストの意味

### 10.1 省けるのは、基本的な借用状態の管理

0.2.6の基本実装では、トークンはゼロサイズの型であり、セルは`UnsafeCell<T>`とゼロサイズのブランドマーカーからなる。セルには`repr(transparent)`が指定されている。`borrow`と`borrow_mut`には、参照カウントや借用カウンタを更新する処理がない。[基本実装の型定義と借用処理](https://docs.rs/ghost-cell/0.2.6/src/ghost_cell/ghost_cell.rs.html)

この意味で、GhostCellは実行時の借用検査の追加コストを省く。トークンの共有・排他という制約は、コンパイル時に検査される。

### 10.2 データ構造全体のコストは残る

以下の処理が、自動的になくなるわけではない。

- `Rc` / `Arc`による共有所有の管理。
- ノードの確保・解放と、ポインタをたどるためのメモリアクセス。
- トークンへロックを付けた場合の同期・待機。
- 実験的な複数借用で必要になる重複検査。
- コレクションの境界検査や、アルゴリズム自体の計算。

また、内部の`UnsafeCell`には、周囲の型のレイアウト最適化に影響する場合がある。`GhostCell<T>`そのものの表現が`T`に対応していても、任意の外側の型まで同じサイズ・同じ最適化になるとは限らない。[UnsafeCellのメモリレイアウト](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html#memory-layout)

### 10.3 ベンチマークの読み方

研究では、リンク構造やグラフに関する比較と測定結果が公開されている。[公開ベンチマーク](https://plv.mpi-sws.org/rustbelt/ghostcell/benchmarks/report/index.html)

それらを、任意のプログラムで`RefCell`やロックより必ず速いという結論へ広げることはできない。比較するなら、同じデータ配置・所有方式・操作・競合条件にそろえ、借用検査の差と、ノード配置や回収方式の差を切り分ける必要がある。これは測定を行う際の本メモでの方針である。

## 11. 形式検証の範囲

### 11.1 論文が確かめたもの

論文は、RustBeltを拡張し、Irisの分離論理を用いて、GhostCellのAPIが安全なRustの拡張となることをCoqで機械検証している。コードの利用例だけでなく、型が許す使い方全体に対する根拠を与える研究である。[GhostCell論文, 特に§4](https://plv.mpi-sws.org/rustbelt/ghostcell/paper.pdf)

証明では、実行時に格納されない論理上の状態を使って、トークンとセルの権限の整合性を表す。論文中の論理的な状態やロックの説明を、実行時に隠れたロックテーブルが存在するという意味に読んではいけない。

### 11.2 研究用実装と、公開クレートを区別する

| 対象 | 確認できる位置づけ |
| --- | --- |
| 原論文と研究用のRust / Coqソース | 研究のAPI・意味・証明を追うための資料 |
| `ghost-cell` 0.2.6の基本API | 研究に基づく別の公開実装。作者が安全性条件への対応を確認したと説明している |
| `GhostBorrowMut`、`GhostCursor`などの実験的拡張 | クレートが明示的なfeatureで分けている拡張。基本研究と同じ証明が付いているとは扱わない |
| このメモのコード例 | 掲載例のコンパイル・動作を確認したもの。一般的な安全性の形式証明ではない |

公開クレートのSafety節は、研究用実装と自身の実装の関係、および拡張の未証明という区別を明記している。[クレートのSafety節](https://docs.rs/ghost-cell/0.2.6/ghost_cell/#safety)

### 11.3 保証の対象に含まれないもの

GhostCellを使っていても、次の性質は別に検討する必要がある。

- 循環した共有所有によるリークがないこと。
- グラフのリンクの貼り方やアルゴリズムが、目的どおり正しいこと。
- 任意のロックの組み合わせでデッドロックしないこと。
- 任意の外部ライブラリや`unsafe`コードが安全であること。
- 将来追加されるAPIや拡張も、既存の証明の対象であること。

型が守るアクセス権限の規律と、アプリケーションの論理的な正しさを分けて評価する必要がある。

## 12. 他の方式との比較

| 方式 | 共有されたデータの変更をどう制御するか | 得意な場面・主な代償 |
| --- | --- | --- |
| 通常の`&mut T` | データそのものを排他的に借りる | 単純で局所的。自由に共有されたノードを直接変更する用途には制約がある |
| `Cell<T>` | 値の出し入れなど、参照を長く貸さないAPIで制御する | 小さな値の置換など。通常の`&mut T`を共有参照から自由に返す仕組みではない |
| `RefCell<T>` | セルごとに実行時の借用状態を検査する | 動的な構造を扱いやすい。借用衝突は実行時の失敗になる |
| `Mutex<T>` / `RwLock<T>` | 実行時の同期でアクセスを制御する | 複数スレッドの動的な競合を調整できる。同期や待機の費用がある |
| GhostCellの基本API | 対応するトークンの借用を静的に検査する | セルの共有と権限を分離できる。同一トークン内でアクセスが連動する |
| qcellの`LCell` | ライフタイムで対応づけたownerを借りる | GhostCellと近い系統。APIや複数借用の設計を比較する価値がある |
| qcellの`QCell` | ownerの借用は静的に検査し、セルとの対応はIDで確認する | 動的にownerを作りやすい。実行時の対応確認がある |
| アリーナ・世代付きハンドル | コンテナが所有し、借用やハンドル検査で操作する | 所有と削除の単位を整理できる。GhostCellとは別の設計軸で、併用も考えられる |

比較の参照先: [標準ライブラリのCell群](https://doc.rust-lang.org/std/cell/)、[Mutex](https://doc.rust-lang.org/std/sync/struct.Mutex.html)、[RwLock](https://doc.rust-lang.org/std/sync/struct.RwLock.html)、[qcellの比較表](https://docs.rs/qcell/0.5.5/qcell/#comparison-of-cell-types)、[世代付きハンドルの例としてのslotmap](https://docs.rs/slotmap/1.1.1/slotmap/)。

**GhostCellが合いやすいと考えられる条件**は、内部共有を持つ構造があり、トークンを渡すAPIが許容でき、操作を短い借用に分けられることである。

**先に別の方式も比較したい条件**は、多数のノードの可変参照を同時に保持する、セルごとに独立して書き込みを並行実行する、ブランドを含む状態を自由に外へ返す、といった要求が中心にある場合である。これらは本メモの制約整理に基づく判断の目安であり、方式の一律な優劣ではない。

## 13. このリポジトリの言語設計への示唆

以下は調査結果からの考察であり、GhostCell論文の追加の主張や、このリポジトリの採用決定ではない。

### 13.1 所有者と、変更する権限の保持者を分けられる

多くの共有構造を扱うとき、「そのノードを指せるなら、同時にそのノードを変更できる」とする必要はない。到達経路と変更権限を別の値にすれば、グラフの形とアクセスの規律を別々に設計できる。

ただし、所有と回収が不要になるわけではない。仕様では「生存を支えるもの」「対象を識別するもの」「操作を許すもの」を、それぞれ定義する必要がある。

### 13.2 検査単位の大きさは、仕様の簡潔さと自由度を左右する

一つのトークンで大きな構造を管理すると、規則をまとめやすい。一方、別ノードの操作まで連動する。

セルごとの権限に細分化すると、同時操作の余地は増えるが、権限の分割・結合、所有経路の維持、重複の判定が複雑になる。単純さを目指す言語では、まず粗い単位で試し、必要な例題で不足を確かめる方法が考えられる。

### 13.3 ブランドは、軽量な「取り違え防止」にも使える

セルとトークンの対応づけは、たとえば「このグラフのノードハンドル」「このデータベース接続のトランザクション」「この計算コンテキストの値」を、別の対象と混ぜないための設計へつながる。

ただし、ブランドが一致するだけで、有効なノード番号や未解放の資源であることまで自動で証明できるわけではない。何をそのブランドの不変条件とするか、どの操作がそれを維持するかまで設計する必要がある。

### 13.4 ライブラリで表せることと、使いやすいことは別に評価する

GhostCellは、言語本体へ新しい借用検査器を追加せずとも、強い規律をライブラリで表せる例である。一方、利用者にはブランドを含む型、トークンの受け渡し、クロージャの範囲といった負担が現れる。

新しい言語を考える際には、同じ規律を明示的なトークンとして見せるか、コンテキスト引数として補うか、特別な構文で表すかを比較できる。構文を省略する場合も、誰がどの権限を使っているかを診断で説明できることが望ましい。

### 小さく試すなら

まず、二つのノードが循環する例、親を参照する木、ノード削除、二つのノードの同時更新を同じモデルで記述する。正常に書けるかだけでなく、次の誤りをどの段階で説明できるかも確認するとよい。

1. 別のブランドのトークンを使う。
2. 読み取り中に同じ権限で変更する。
3. 可変借用を残して、別ノードの借用を始める。
4. ノードの最後の所有経路を消した後も、その参照を使おうとする。
5. 新しく作ったブランドを、外へ持ち出そうとする。

## 14. 資料とコード例の確認方法

### 一次資料を読む順序

- [研究ページ](https://plv.mpi-sws.org/rustbelt/ghostcell/): 研究の目的、著者、論文と成果物への入口。
- [原論文](https://plv.mpi-sws.org/rustbelt/ghostcell/paper.pdf): §2のブランド、§3のGhostCell APIと構造の例、§4の証明、§5の比較を参照。
- [研究用のRust / Coqソース](https://gitlab.mpi-sws.org/FP/ghostcell): 論文に対応する実装・証明を追う資料。
- [ICFP 2021の成果物アーカイブ](https://zenodo.org/records/5036838): 研究時点の成果物を参照する入口。
- [公開クレート0.2.6のAPI](https://docs.rs/ghost-cell/0.2.6/ghost_cell/): 実際に利用するAPIとSafety節。
- [公開実装のリポジトリ](https://github.com/matthieu-m/ghost-cell): 実装方針、ソース、開発状況の確認先。
- [qcellの比較](https://docs.rs/qcell/0.5.5/qcell/): ブランドの表現方式を変えた設計の比較先。

### このメモの検証範囲

コード例は、配布された`ghost-cell` 0.2.6のソースを用い、Rust 1.94.1・edition 2021で確認した。

- 通常のコード例: 最小例、循環グラフ、スコープ付きスレッドのコンパイルと実行。
- 実験的なコード例: 複数可変借用featureを有効にした場合の実行と、同じセルの重複指定のエラー。
- `rust,compile_fail`と表記した例: 読み取りと変更の衝突、別セルへの二重可変借用、ブランドの持ち出しが拒否されること。

型の関係を説明する`text`ブロックは、実行用プログラムではない。検証は掲載例の挙動を確認するもので、クレート全体の監査や形式証明を追加したという意味ではない。
