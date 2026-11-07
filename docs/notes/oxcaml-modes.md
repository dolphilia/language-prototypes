# OxCamlのモード詳解 — 値の使い方を複数の軸で追跡する

[メモの一覧へ](README.md) · [所有権とその先](ownership-and-beyond.md) · [GhostCell詳解](ghostcell.md) · [リポジトリの目次へ](../../README.md)

調査日: **2026-11-07**

対象: OxCamlの公式ドキュメント、および2024年のモードによるメモリ管理、2025年のデータ競合防止、2026年のMode Crossingに関する研究。

コードは、公式資料の構文を使った読解用の断片である。省略した型・関数の定義を含み、単独で実行できるプログラムとは限らない。この環境には標準OCaml 5.1.0があるが、OxCaml処理系はなく、モード付きコードのコンパイルは行っていない。設計への示唆は、本メモでの考察として分けて記す。

## 目次

- [まず何をする仕組みか](#1-まず何をする仕組みか)
- [型とモードの違い](#2-型とモードは何が違うのか)
- [モードの軸と過去・未来](#3-モードの軸と過去と未来の意味)
- [Localityと局所割り当て](#4-locality-値が領域の外へ逃げられるか)
- [UniquenessとLinearity](#5-uniquenessとlinearity-別名参照と利用回数を分ける)
- [ContentionとPortability](#6-contentionとportability-データ競合を防ぐ)
- [その他の軸](#7-効果や可変状態を扱う軸)
- [Submoding](#8-submoding-安全な方向へ制約を弱める)
- [Modalityと深さ](#9-modality-コンテナと中身の関係を表す)
- [Mode CrossingとKind](#10-mode-crossingとkind-型の性質に応じて制約を越える)
- [推論と互換性](#11-推論と既存ocamlとの互換性)
- [研究の進展と実装状況](#12-研究の進展と実装状況)
- [Rust・GhostCellとの比較](#13-rustやghostcellとはどう関係するか)
- [言語設計への示唆](#14-このリポジトリの言語設計への示唆)
- [資料と確認範囲](#15-資料と確認範囲)

## 1. まず何をする仕組みか

OxCamlのモードは、**値の型とは別に、その値をどう使えるかをコンパイラが追跡する仕組み**である。

たとえば、値について次のようなことを区別する。

- この値を、現在の処理の外へ持ち出してよいか。
- この値には、ほかの利用可能な参照経路があるか。
- このクロージャを、繰り返し呼んでよいか。
- この値を、別の実行領域へ渡してよいか。
- 並行処理で共有された値の、どの部分へアクセスしてよいか。

これらを一つの「所有している／していない」という分類へ押し込めず、複数の独立した軸として扱う。

背景にあるのは、OCamlの型推論やGCによる使いやすさを保ちながら、割り当ての制御と安全な並行処理を加えるという方針である。OxCamlは、必要な機能を使う箇所に応じて複雑さを引き受ける設計を目指している。[OxCamlの設計方針](https://oxcaml.org/)

モードは、実行時に値へ付ける状態フラグではない。コンパイラがプログラムの利用関係を調べ、安全な割り当てや操作の条件を静的に確認するための情報である。[モードによるメモリ管理の研究](https://homepages.inf.ed.ac.uk/slindley/papers/mode-inference.pdf)

## 2. 型とモードは、何が違うのか

### 2.1 型はデータを、モードは利用の条件を表す

| 情報 | 主な問い | 例 |
| --- | --- | --- |
| 型（type） | どんなデータで、どんな構造を持つか | `int`、`string`、`int list` |
| モード（mode） | この値を、どんな条件で使えるか | `local`、`unique`、`portable` |
| カインド（kind） | 型がどんな性質・表現・モード越境能力を持つか | `value mod portable`など |

`x : string @ local`では、`x`の型は`string`、モードは`local`である。公式資料は、型そのものにモードが付くという説明と、値が型とモードを持つという説明を区別している。ただし、関数の型には、引数や結果のモードの条件も現れる。[モードの公式概説](https://oxcaml.org/documentation/modes/intro/)

### 2.2 関数の型は、値の受け渡しの契約になる

```ocaml
val inspect : string @ local -> int
```

この型は、関数が受け取った文字列を、その所属する領域の外へ逃がさないという契約を表す。文字列の型を別のデータ型へ変更しているわけではない。

また、関数自体も値なので、関数を表すクロージャにもモードがある。

```ocaml
val inspect : string @ local -> int
val use_callback : (string -> int) @ portable -> unit
```

前者の`local`は文字列の引数の受け取り方を、後者の`portable`は引数として受け取る関数値そのものの持ち運び方を制約する。この区別は、クロージャが何を捕捉しているかを考えるときに重要になる。

`@`の位置と括弧には注意が必要である。`a -> b @ portable`は結果`b`の条件、`(a -> b) @ portable`は関数値の条件を表す。[モードの構文](https://oxcaml.org/documentation/modes/syntax/)

## 3. モードの軸と過去と未来の意味

### 3.1 一つの値は、複数の軸の情報を持つ

現在の公式資料に現れる主な軸を整理すると、次のようになる。最初は上の5軸を理解し、残りは必要になったところで読むとよい。

| 軸 | 主なモード | 主に追跡するもの |
| --- | --- | --- |
| Locality | `global` / `local` | 領域からの持ち出し |
| Uniqueness | `unique` / `aliased` | 別名参照と一意な利用 |
| Linearity / Affinity | `many` / `once` | 主にクロージャの反復利用 |
| Contention | `uncontended` / `shared` / `corrupted` / `contended` | スレッド間共有に伴うアクセス条件 |
| Portability | `portable` / `shareable` / `corruptible` / `nonportable` | 主にクロージャを実行領域間で渡せる条件 |
| Forkable | `forkable` / `unforkable` | 関数が親スタックの共有値へアクセスする条件 |
| Yielding | `unyielding` / `yielding` | 親スタックで扱われる効果の実行 |
| Visibility | `read_write` / `read` / `write` / `immutable` | 可変部分の読み書き権限 |
| Statefulness | `stateless` / `reading` / `writing` / `stateful` | クロージャが捕捉した可変状態への作用 |

この表は、公式の[軸の説明](https://oxcaml.org/documentation/modes/intro/)と[構文の一覧](https://oxcaml.org/documentation/modes/syntax/)に基づく。軸の追加が続いているため、古い論文に登場する軸の数を、そのまま現行設計の全体と考えない。

### 3.2 Past / Futureは、実装予定の区別ではない

公式資料のpast modeは、それまでに別名参照や共有が生じたかなど、**値の来歴に関わる性質**を追う。一方、future modeは、今後その値を逃がす、繰り返す、別スレッドへ渡すなどの**利用を許すかどうか**を追う。

`future`は「将来のバージョンで実装される」という意味ではない。また、`past`も、実行時に履歴を記録するという意味ではない。[モード概説の定義](https://oxcaml.org/documentation/modes/intro/)

たとえば、過去の別名参照を制御するuniquenessと、今後クロージャを複数回使えるかを制御するlinearityを分けることで、独立したデータと高階関数の両方を扱える。[2024年のモード計算体系](https://homepages.inf.ed.ac.uk/slindley/papers/mode-inference.pdf)

## 4. Locality: 値が領域の外へ逃げられるか

### 4.1 globalとlocal

`global`な値は、現在の領域の外へ持ち出せる。`local`な値は、その値が所属する領域の制約を守って使う必要がある。

ここでいう`global`は、グローバル変数、全スレッドへの公開、プログラム終了までの生存を意味しない。関数から返す、長く生きるデータ構造へ保存するなど、現在の領域を越えられるという性質である。

領域は、典型的には関数本体やループ本体などのスコープに対応する。領域外へ逃げない値は、局所的なスタック割り当ての候補になる。[局所割り当ての概説](https://oxcaml.org/documentation/stack-allocation/intro/)

### 4.2 local引数は、関数が守る約束

```ocaml
let sum_pair (pair : (int * int) @ local) =
  let x, y = pair in
  x + y
```

この関数は、受け取った組を読み取って整数を返す。組そのものを保持して外へ持ち出す必要はない。

呼び出し側は、スタックに置いた組も、通常のヒープ上の組も渡せる。`local`な引数の指定は、「この引数は必ずスタック上に存在する」という要求ではなく、関数がその引数をどう扱うかの約束である。[local引数の説明](https://oxcaml.org/documentation/stack-allocation/intro/#local-parameters)

### 4.3 stack_は、局所割り当てを要求する

```ocaml
type point = { x : int; y : int }

let magnitude_squared x y =
  let p = stack_ { x; y } in
  p.x * p.x + p.y * p.y
```

`stack_`は、その直後の割り当てをスタック上で行うことを要求する。領域の外へ逃げるため実現できない場合、ヒープへ黙って切り替えるのではなく、エラーにするための制御でもある。

```ocaml
(* 拒否されることを意図した説明例。pそのものが領域外へ逃げる。 *)
let bad x y =
  let p = stack_ { x; y } in
  p
```

一方、`local`の意味は非脱出という静的な条件であり、あらゆる値について特定の物理配置を約束するものではない。配置を要求する構文と、利用を制約するモードを分けて読む必要がある。[割り当てと領域のリファレンス](https://oxcaml.org/documentation/stack-allocation/reference/)

### 4.4 「localな結果を返す」ための仕組みもある

局所的な値を返す処理がすべて不可能になるわけではない。`exclave_`など、呼び出し元の領域で結果を作るための仕組みがある。

これは、自分の消滅する領域に置いた値への参照を返してよいという意味ではない。どの領域が結果の生存を支えるかを変える設計である。配置する領域の選び方は、使用するスタック領域の大きさにも影響する。[localな結果とexclave_](https://oxcaml.org/documentation/stack-allocation/reference/)

`int`のような値が`local`から外へ出られる例外については、10節のmode crossingで説明する。

## 5. UniquenessとLinearity: 別名参照と利用回数を分ける

### 5.1 uniqueは、一意に消費できる値を表す

`unique`は、別の参照経路による利用と衝突せず、その値を一意に扱えるという情報である。通常の共有が許される側は`aliased`である。

例として、外部資源の解放APIを考える。

```ocaml
val free : resource @ unique -> unit
```

`free`が一意な値を要求すれば、別の利用可能な参照を残したまま解放する操作を防げる。この`free`はAPIの例であり、任意のOCaml値を解放する組み込み命令ではない。[uniquenessの導入](https://oxcaml.org/documentation/uniqueness/intro/)

一意性は、実行時に物理的なポインタの本数を数える方式ではない。コンパイラは、どの経路が後から使われるか、どのフィールドが消費されたか、利用が同じ分岐で起きるかなどを解析する。[uniquenessの解析規則](https://oxcaml.org/documentation/uniqueness/reference/)

### 5.2 GCがあるので、一意性を手放す選択もできる

一意に構築したデータを、その後は通常の共有可能なOCamlの値として使う設計もできる。たとえば、構築中だけ一意なアクセスを使い、完成後は共有するという二段階の使い方である。

`unique`を手放した後の値も、通常のヒープ上のデータであればGCが生存と回収を管理する。OxCamlは、すべての値について利用者に手動解放を要求する設計ではない。[一意な利用と共有利用の混在](https://oxcaml.org/documentation/uniqueness/reference/#mixing-unique-and-aliased-uses)

### 5.3 一意な値を消費するクロージャは、繰り返せない

```ocaml
val defer_free : resource @ unique -> (unit -> unit) @ once
```

`defer_free`が、資源を捕捉し、後で`free`するクロージャを返すとする。このクロージャを二度呼べると、同じ資源を二度消費できてしまう。

そのため、主に関数値の利用回数を追う軸として、`once`と`many`を区別する。`once`は高々一度、`many`は繰り返し使える側である。[クロージャとonce](https://oxcaml.org/documentation/uniqueness/intro/)

**ここでのonceは、必ず一度実行するという保証ではない。** 使わずに捨てることの禁止、終了の保証、後始末の成功まで含む規則ではなく、アフィンな利用制約として読む必要がある。論文ではこの軸をaffinityとも呼ぶ。

### 5.4 uniqueとonceは同じ意味ではない

| 情報 | 主な役割 |
| --- | --- |
| `unique` | そのデータを一意に消費・操作できるか |
| `once` | 捕捉した資源などを、関数の反復利用で複製しないか |

関数を含まない通常のデータについて、`once`を一律な「変数名を一回しか書けない規則」と考えると誤解する。関数を含まない型は、この軸を越境できる場合がある。

また、一意な引数を消費する関数を何度も使いたいなら、消費後の値を新たな結果として返し、次の呼び出しへ渡す必要がある。破壊的更新のように見える操作でも、APIが値を受け取り返す形になることがある。[uniqueな値の受け渡しでの注意点](https://oxcaml.org/documentation/uniqueness/pitfalls/)

### 5.5 borrow_で、一意性を一時的に貸す

現在の個別ドキュメントは、`borrow_`で一意な値を一時的に`aliased`かつ`local`として使う方法を説明している。

```ocaml
(* inspectはlocalな引数を取り、consumeはuniqueな引数を取るAPIとする。 *)
let inspect_then_consume x =
  inspect (borrow_ x);
  consume x
```

借用した経路が外へ逃げず、借用の間に元の値を一意に使わなければ、借用終了後に一意な利用へ戻れる。個別資料は、関数の引数、`let`の右辺、`match`の対象など、構文上の借用領域も定めている。[borrow_の説明](https://oxcaml.org/documentation/uniqueness/borrow/)

通常の`aliased`利用で永続的に一意性を手放すことと、この一時的な借用は区別する。原理としては、localityの「逃がさない」という性質が、一意性を後で回復する条件を支えている。

## 6. ContentionとPortability: データ競合を防ぐ

### 6.1 「共有されても触ってよい部分」と「実行できる関数」を分ける

通常の可変値を複数の実行領域から自由に読み書きすれば、データ競合が起きうる。OxCamlでは、主に二つの軸を組み合わせてこれを制御する。

- **Contention**: 共有に関する状況を踏まえて、その値へどうアクセスできるか。
- **Portability**: 特にクロージャを、別の実行領域へ安全に持ち運べるか。

一方だけでは、クロージャに隠れた共有状態まで制御することは難しい。[並行処理の公式チュートリアル](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-1/)

### 6.2 uncontendedとcontended

`uncontended`な値は、通常の可変部分へアクセスできる側である。`contended`では、ほかの実行領域のアクセスを考慮し、保護されていない可変部分を読み書きできない。

ただし、値の存在自体が使えなくなるわけではない。不変なフィールドを読むなど、安全性を保てる操作は可能である。

```ocaml
type account = {
  name : string;
  mutable balance : int;
}

val account_name : account @ contended -> string
val account_balance : account @ uncontended -> int
```

前者は不変な`name`を読み、後者は可変な`balance`を読むAPIを表す。ここで`contended`は「実行時に現在、競合が発生している」という測定結果ではない。アクセスを許すための静的な分類である。[contendedのアクセス規則](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-1/)

### 6.3 portableは、隠れた状態の持ち出しを制御する

問題は、データを引数として渡す場合だけではない。

```text
counter = 可変のカウンタ

callback = () => counterを読み書きする
```

このクロージャを別スレッドへ渡すと、元のスレッドも同じカウンタを操作できてしまう。型が単に`unit -> unit`であるだけでは、捕捉した参照が見えない。

`portable`な関数を検査するときは、捕捉する値にも適切な共有条件を課す。その結果、保護されていない可変状態を、元の`uncontended`な権限のまま持ち出す経路を防ぐ。[Data Race Freedom à la Mode](https://plv.mpi-sws.org/drfcaml/paper.pdf)

### 6.4 中間モードは、単なる強弱の一直線ではない

公式資料には、さらに次の中間モードがある。

```text
Contention:                 Portability:

        contended                  nonportable
        /       \                  /         \
    shared    corrupted       shareable   corruptible
        \       /                  \         /
       uncontended                    portable
```

`shared`と`corrupted`、`shareable`と`corruptible`は、それぞれ異なる方向の読み書き制約を区別する中間点である。互いを単純な上位・下位とすることはできない。本メモの基本例は`uncontended` / `contended`と`portable` / `nonportable`に絞る。[各軸の定義](https://oxcaml.org/documentation/modes/intro/)

### 6.5 可変状態の共有には、アトミック操作やカプセルを使う

並行に変更する必要がある状態には、モードと連携するアトミック操作、ロック、カプセルなどのAPIを使う。

カプセルは、データと、そのデータへアクセスする権限をブランドで関連づける。`unique`なキーでアクセスする経路や、キーをロックへ渡して動的に排他アクセスする経路を設ける。

```text
ブランド 'k のデータ ─── アクセスには、対応する権限が必要

  uniqueなキー ───────→ 一意な権限を使って操作
       または
  キーを保持するロック ──→ ロック取得中だけ操作
```

カプセル内に可変状態があっても、外側のラッパーを安全に共有できるよう、取り出し操作を制御する。[カプセルの公式チュートリアル](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-2/)

ライブラリの型の宣言も重要である。同じような名前のアトミック型でも、モード越境の情報を持つライブラリと、従来のインターフェースのものとを、無条件に同じようには扱えない。公式チュートリアルも使用する`Atomic`の実装を区別している。[チュートリアルのアトミック操作の説明](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-1/)

## 7. 効果や可変状態を扱う軸

この節の定義は、現在の[公式のモード概説](https://oxcaml.org/documentation/modes/intro/)に基づく。追加の軸も、基本の5軸と組み合わせて利用条件を表す。

### 7.1 Forkable

`forkable` / `unforkable`は、関数が親スタックの共有値へアクセスする条件を扱う。単に`portable`であれば、スコープ付きの並行実行に関する条件がすべて決まる、というわけではない。

### 7.2 Yielding

`yielding` / `unyielding`は、親スタックで扱われる効果を関数が実行できるかを扱う。`unyielding`は、任意の副作用がないことや、例外を一切起こさないことの一般的な宣言ではない。

### 7.3 VisibilityとStatefulness

Visibilityは、値の可変部分へ読む・書く・両方・どちらもしないというアクセス条件を表す。Statefulnessは、クロージャが捕捉した可変状態に対し、どの作用を行えるかを表す。

```text
値へのアクセス条件:            捕捉した状態への作用:

        immutable                       stateful
        /       \                       /      \
      read     write                reading   writing
        \       /                       \      /
        read_write                      stateless
```

Visibilityの`immutable`は、「このアクセス経路では可変部分に触れない」という条件である。対象そのものが物理的に不変なデータ型へ変わるわけではない。また、`stateless`が主に扱うのは捕捉した状態であり、引数経由の変更やあらゆる入出力まで禁止する一般的な純粋性と同一視しない。

Contentionがデータ競合を避けるための軸であるのに対し、Visibilityは、スレッド安全な操作であっても可変部分へのアクセスを制限する。この違いにより、並行安全性とは別の作用の制御を表せる。

## 8. Submoding: 安全な方向へ制約を弱める

### 8.1 強い条件を満たす値を、控えめな使い方へ渡せる

次の矢印は「左側の値を、右側のモードとして使ってよい」という意味である。

```text
global       → local
unique       → aliased
many         → once
portable     → nonportable
uncontended  → contended
```

たとえば、領域外へ持ち出せる値を、持ち出さない関数へ渡しても安全である。繰り返し使える関数を、一度しか使わない場面へ渡しても安全である。一意な値の一意性を手放して、共有可能な値として扱うこともできる。

このような関係がsubmodingである。通常、逆向きの変換はできない。すでに共有された値を、単に注釈を書いて一意な値へ戻せるわけではない。[uniquenessのmode crossingとの区別](https://oxcaml.org/documentation/uniqueness/intro/#mode-crossing)

### 8.2 「強い」は、関数の立場で見ると紛らわしい

`local`な引数を取る関数は、関数の実装側から見ると「外へ逃がさない」という強い約束をする。一方、渡す値の側から見ると、`global`な値も`local`な値も受け入れる柔軟な入口になる。

モードを「性能が高い順」「所有権が強い順」と一列に並べるより、**値に必要な保証と、利用者へ与える権限**を分けて読むほうがわかりやすい。

## 9. Modality: コンテナと中身の関係を表す

### 9.1 モードは、原則として内部へ伝わる

`local`なコンテナの内部にもlocalityの制約が伝わる。`unique`なコンテナでは、一意性を持つ内部構造として扱う。こうした性質をdeep、つまり深く適用される性質と呼ぶ。

ところが、外側は局所的でも、中には長く使える文字列を持ちたい場合がある。外側だけが一意でも、要素のデータは共有したい場合もある。

この関係を表すために、フィールドへ**modality**を指定する。

### 9.2 @と@@の違い

```ocaml
type packet = {
  temporary : string;
  stable : string @@ global;
}
```

`packet`がlocalな値であっても、`stable`はglobalな内容を持つフィールドとして宣言されている。適切な内容を入れて構築すれば、外側の局所性に引きずられず、取り出した値を扱える。

| 表記 | 主な意味 |
| --- | --- |
| `x : t @ local` | この値`x`の利用条件 |
| `field : t @@ global` | 外側のコンテナと、そのフィールドのモードの関係 |

`@@ global`が、すでにスタック上にある値を自動でヒープへコピーするわけではない。宣言が要求する条件を満たす内容を格納しなければならない。[フィールドのmodalityの構文](https://oxcaml.org/documentation/modes/syntax/#record-fields)

### 9.3 共有可能な要素を持つ、一意な骨組み

```ocaml
type 'a shared_payload = {
  payload : 'a @@ aliased;
}
```

このようなラッパーを使うと、外側のデータ構造は一意に扱いながら、`payload`は共有された値として扱う、という設計ができる。

一意なリストの全要素についてまで一意性を要求すると使いにくい場合に、ノードの骨組みと要素の共有を分ける発想である。[uniquenessとmodality](https://oxcaml.org/documentation/uniqueness/intro/#modalities)

### 9.4 単なる上書き指定ではなく、モード間の写像

厳密には、modalityは外側のモードから内側のモードを求める変換として扱われる。

- futureの軸では、外側のモードとフィールドの条件から、共通の下側の条件を取る。
- pastの軸では、共通の上側の条件を取る。
- 中間点を持つ軸では、全順序上の最小・最大ではなく、束のmeet・joinを使う。

たとえば、`@@ portable`なフィールドは、外側が`nonportable`でもportableな内容を保持し、取り出すための契約になる。一方、`@@ shared`なフィールドは、外側が`uncontended`でもsharedな側へ制約する。[modalityの計算規則](https://oxcaml.org/documentation/modes/reference/#modalities)

### 9.5 可変フィールドには追加の規則がある

可変フィールドは、通常の不変フィールドと同じデフォルトではない。構築時と読み取り時のmodalityに加え、代入時には別の規則もある。

そのため、`@@ local`などを一つ付ければ、任意の局所的な値を`ref`や配列へ何度でも保存できると考えてはいけない。調査時の構文資料は、代入に`global`かつ`many`な値を要求する規則などを説明している。[可変フィールドの規則](https://oxcaml.org/documentation/modes/syntax/#record-fields)

## 10. Mode CrossingとKind: 型の性質に応じて制約を越える

### 10.1 型ごとに、そもそも問題にならない軸がある

たとえば、`int`は通常のOCamlでは即値として表現され、特定の局所的な割り当てへの参照を持たない。そのため、localityの制約をそのまま課す必要がない。

また、深く不変な文字列などは、通常の可変フィールドの競合を起こさない。関数を含まないデータは、クロージャが隠し持つ状態に関する制約と無関係な場合がある。

こうした**型の性質を根拠に、通常のsubmodingだけでは行けない方向へ使えるようにすること**がmode crossingである。[Mode Crossing, ICFP 2026](https://people.mpi-sws.org/~bpeters/papers/mode-crossing.pdf)

### 10.2 実行時の変換ではない

```text
通常は不可:
  nonportableな関数 → portableな関数

型の性質から許せる例:
  nonportableとして扱われたint → portableとして利用
```

後者では、値をスキャンして共有状態がないか調べたり、複製したりしているわけではない。型の静的な性質から安全だと判断する。

これは、制約を無視する抜け道ではなく、必要以上の制限を避けるための仕組みである。2026年の研究は、型を見ず一律にモードを追うことで起きる、明らかに安全なプログラムの拒否を課題としている。[Mode Crossingの研究概要](https://icfp26.sigplan.org/details/icfp-2026-icfp-papers/9/Mode-Crossing)

### 10.3 kindが、型の越境能力を記録する

抽象型では、利用者から内部表現が見えない。中身を隠しながらmode crossingを利用するには、インターフェースに必要な性質を表す必要がある。

```ocaml
type message : value mod portable contended
```

これは、`message`という型の表現や越境能力に関する情報である。特定の変数がいまportableなモードを持つという宣言とは異なる。

`value`は通常のOCamlの値に対応する表現の分類であり、`mod ...`はモードに関する境界情報を記述する。kind全体には、このほかにも表現や型引数への依存に関する要素がある。[kindの概説](https://oxcaml.org/documentation/kinds/intro/)

### 10.4 mode・modality・modal kindを区別する

| 概念 | 付ける対象・役割 | 読み方 |
| --- | --- | --- |
| mode | 値や引数・結果の利用 | この値を、どう使えるか |
| modality | フィールドなどの内外の関係 | このコンテナから取り出す値を、どう扱えるか |
| modal kind / modal bound | 型が持つ性質 | この型の値は、どのモード制約を安全に越えられるか |

たとえば、`t @ portable`と`type t : value mod portable`は同義ではない。前者は値の条件、後者は型が提供する越境の根拠を表す。[kindの構文と境界](https://oxcaml.org/documentation/kinds/syntax/)

### 10.5 すべての不変値が、すべての軸を越えるわけではない

文字列には可変フィールドがなくても、その記憶領域の寿命は依然として重要である。整数リストが関数を含まなくても、リストのノードが一意に扱えるかは別の問題である。

ある軸を越境できる理由を、別の軸へそのまま適用してはいけない。型引数を持つコンテナでは、要素型の性質も影響する。[kindと型引数の関係](https://oxcaml.org/documentation/kinds/intro/)

逆に、即値の整数で実装された資源ハンドルでも、抽象型で内部表現を隠し、越境能力を公開しないことで、その資源に必要な利用制約を維持する設計が考えられる。

## 11. 推論と既存OCamlとの互換性

### 11.1 必要な情報を、できるだけ推論する

すべての値に全モードを書かなければならないわけではない。コンパイラは、割り当て、関数呼び出し、捕捉する変数、利用回数などから制約を集める。

メモリ管理のモードに関する2024年の研究は、クロージャを含めてモードを推論する計算体系を示している。2026年の研究は、型・kindを介した越境を含む制約の処理へ進んでいる。[2024年のモード推論](https://homepages.inf.ed.ac.uk/slindley/papers/mode-inference.pdf)、[2026年のkindの推論](https://people.mpi-sws.org/~bpeters/papers/mode-crossing.pdf)

ただし、実際のコンパイラには推論の境界がある。localな引数を別ファイルの関数へ渡したい場合は、`.mli`のインターフェースにもlocalityの条件が必要になる。一意な戻り値も、モジュールの境界で明示的な契約が必要になる場合がある。[割り当ての推論の範囲](https://oxcaml.org/documentation/stack-allocation/intro/#inference)、[uniqueな戻り値の注意点](https://oxcaml.org/documentation/uniqueness/pitfalls/#annotating-unique-return-values)

### 11.2 省略された条件にはlegacy modeがある

従来のOCamlの関数型にも、モードに関する暗黙の条件を与えられるよう、各軸には互換性のためのlegacy modeがある。調査時の構文資料で、矢印型の省略時に挙げられているのは次の組である。

```text
global aliased many nonportable uncontended
forkable unyielding stateful read_write
```

たとえば、古い`string -> int`という宣言から、自動的に「localな文字列も受け取る」「関数自体がportable」といった強い契約まで得られるわけではない。[矢印型とlegacy mode](https://oxcaml.org/documentation/modes/syntax/#arrow-types)

### 11.3 省略の規則と、推論の規則も同じではない

モードの表記には、利用者の注釈を減らすための含意がある。たとえば、`local`の表記は、対応する指定が省略されていれば`unforkable`や`yielding`を補う。`immutable`から`contended`を補う規則もある。

これは表面構文の省略を補う規則であり、解析のすべての場所で同じ含意が機械的に成り立つという意味ではない。また、modalityを省略した軸の恒等変換と、legacy modeのデフォルトは別である。[モード表記の含意と省略](https://oxcaml.org/documentation/modes/syntax/#implications)

## 12. 研究の進展と実装状況

### 12.1 研究は、段階的に対象を広げている

| 時期 | 一次資料 | このメモに関係する進展 |
| --- | --- | --- |
| 2023 | [Jane StreetのLocalityの解説](https://blog.janestreet.com/oxidizing-ocaml-locality/) | GCのある言語へ、領域と非脱出の制約を加える考え方を紹介 |
| 2024 | [Oxidizing OCaml with Modal Memory Management](https://homepages.inf.ed.ac.uk/slindley/papers/mode-inference.pdf) | Locality・Uniqueness・Affinityの組み合わせ、推論、安全性の計算体系 |
| 2025 | [Data Race Freedom à la Mode](https://plv.mpi-sws.org/drfcaml/paper.pdf) | Contention・Portabilityによるデータ競合防止、カプセルや同期APIとの接続 |
| 2026 | [Mode Crossing](https://people.mpi-sws.org/~bpeters/papers/mode-crossing.pdf) | 型に応じた越境、modal kind、再帰型・抽象型、実装と推論 |

論文の計算体系が検証されたことと、現行コンパイラの全機能・全最適化が、そのまま証明済みであることは別である。2025年と2026年の研究は、IrisとRocqを用いた形式的な根拠を示しているが、対象と仮定は各論文で確認する必要がある。

### 12.2 現在の説明と、古い構想の記述を混ぜない

古い記事には、現在とは異なるモード名や構文が登場する。たとえば2023年の所有権の記事にある`shared`を、現在のcontention軸の`shared`とそのまま同じものとして読んではいけない。[当時の所有権の解説](https://blog.janestreet.com/oxidizing-ocaml-ownership/)

OxCamlの公式紹介も、拡張機能について安定性や後方互換性を約束しないと明記している。既存OCamlとの互換性の方針と、OxCaml独自拡張の版をまたぐ安定性は別である。[OxCamlの利用上の位置づけ](https://oxcaml.org/)

公式資料の中にも更新時期の差がある。調査時点では、一般的な説明には借用や上書き更新を将来の拡張として扱う記述が残る一方、個別の[Borrowingページ](https://oxcaml.org/documentation/uniqueness/borrow/)には`borrow_`の構文と制約が説明されている。

本メモは、個別の機能説明を優先して仕組みを整理した。上書きによる記憶領域の再利用などを、インストール可能な任意の版で利用できる機能と断定してはいない。具体的な採用時には、処理系とライブラリの版をそろえる必要がある。

### 12.3 GCと併用する仕組みとして読む

局所割り当てによって、その割り当てに伴うGCの負担を減らせても、プログラム全体からGCや実行時コストが消えるわけではない。カプセルにロックを使えば同期の費用があるし、データ構造の配置やアルゴリズムの費用も残る。

モードは、性能を改善する操作を安全に行うための情報である。性能の向上量や停止時間の性質は、対象プログラムと使用する機能ごとに評価する必要がある。[OxCamlの割り当て制御の方針](https://oxcaml.org/)

## 13. RustやGhostCellとは、どう関係するか

| 観点 | Rustの所有・借用 | GhostCell | OxCamlのモード |
| --- | --- | --- | --- |
| 主な仕組み | 所有値・参照・ライフタイム | セルとブランド付きトークン | 複数の利用条件の軸と推論 |
| アクセス権限 | 所有・借用の型へ結びつく | 共有されたセルと権限を分ける | 値・クロージャ・フィールド・型の性質から条件を計算する |
| メモリ回収 | 所有値の破棄を基本とし、共有所有なども併用 | 回収方式は別に必要 | GCを基礎に、局所割り当てや一意な利用を加える |
| 一時的な利用 | 借用 | トークンの共有・排他借用 | LocalityやUniquenessと借用の組み合わせ |
| 並行処理 | `Send` / `Sync`などと組み合わせる | トークンの受け渡しと同期を設計する | Contention・Portabilityなどで捕捉状態も追う |

この比較は、それぞれの設計の重心を整理したもので、一対一の機能対応表ではない。RustとGhostCellの詳細は、[所有権のメモ](ownership-and-beyond.md)と[GhostCellのメモ](ghostcell.md)も参照。

特に近いのは、OxCamlのカプセルとGhostCellの発想である。どちらも、データへ到達することと、そのデータを変更する権限を持つことを分け、ブランドで対応づける。

一方、カプセルのキー・パスワード・ロックのAPIと、GhostCellのトークンのAPIは同じものではない。モードによる条件やGCのある環境も含め、異なる設計として比較する必要がある。[OxCamlのカプセル](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-2/)、[GhostCellの研究](https://plv.mpi-sws.org/rustbelt/ghostcell/)

## 14. このリポジトリの言語設計への示唆

以下は調査を踏まえた考察であり、採用決定ではない。

### 14.1 「所有権」を複数の問いへ分解する

所有しているかどうかだけでは、生存、共有、変更、反復利用、並行実行のすべてを説明しきれない。

小さな言語を設計する場合も、まず「何を禁止したいのか」を個別に定めるとよい。たとえば、局所的な値の持ち出しだけを制限する案と、資源の一意な消費まで追う案では、必要な規則が異なる。

### 14.2 GCを使いながら、資源や共有の規律を加えられる

メモリ回収をGCへ任せることと、型やモードで安全性を高めることは両立する。ファイルハンドル、トランザクション、データを構築する途中の状態など、特定の値だけに追加の規律を設ける設計を検討できる。

その場合も、`once`や`unique`の指定だけで「必ずcloseする」ことまで保証したと考えず、自動的な後始末、異常終了、使わずに捨てることの意味を別に定める必要がある。

### 14.3 クロージャを加えると、データだけの規則では足りなくなる

関数値は、引数や戻り値の型に現れない状態を捕捉する。一意な資源、局所的なデータ、共有してはいけない可変状態を、クロージャが隠して持ち出す経路を考える必要がある。

OxCamlがUniquenessとLinearity、ContentionとPortabilityを分ける理由は、この問題を理解するうえで参考になる。

### 14.4 深い制約と、例外を宣言する仕組みをセットで考える

コンテナ全体へ一律に制約を伝えるだけでは、共有してよい要素を持つ一意な構造や、長く生きるデータを持つ局所的な構造が扱いにくい。

例外を認める場合には、内容を格納する時点の条件と、取り出した値へ与える条件の両方を定める必要がある。Modalityは、この契約を表す方法の一例になる。

### 14.5 軸を増やすほど、診断と説明が重要になる

独立した軸は、理論上は組み合わせやすい。しかし、利用者が受け取るエラーは、複数の軸、型抽象、関数境界、クロージャの捕捉が絡んだものになる。

最初の試作では、Localityのような一つの軸から始め、どの例題で追加の軸が必要になるかを確かめる方法が考えられる。推論で省略できることと、利用者へ説明しなくてよいことは同じではない。

### 比較に使える小さな例題

1. 局所的な組を関数へ渡し、整数だけを返す。
2. 局所的な値を捕捉したクロージャを、外へ返そうとする。
3. 一意な資源を捕捉したクロージャを、二度呼ぼうとする。
4. 不変データと可変データを、同じ並行APIへ渡そうとする。
5. 一意なコンテナに、共有された要素を格納する。
6. 抽象型の表現を隠しながら、安全な越境だけを公開する。

こうした例で、正常なコードの短さだけでなく、拒否の理由を簡潔に説明できるか、境界で何を注釈させるかも比較するとよい。

## 15. 資料と確認範囲

### 読む順序

- [公式のモード概説](https://oxcaml.org/documentation/modes/intro/): 型との違い、各軸の定義、submodingの入口。
- [局所割り当ての概説](https://oxcaml.org/documentation/stack-allocation/intro/): `local`、`stack_`、関数境界での契約。
- [uniquenessの概説](https://oxcaml.org/documentation/uniqueness/intro/): 一意な消費、`once`、深い制約。
- [借用の個別資料](https://oxcaml.org/documentation/uniqueness/borrow/): `borrow_`と借用領域。
- [並行処理チュートリアル第1部](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-1/): ContentionとPortabilityを具体例で読む。
- [並行処理チュートリアル第2部](https://oxcaml.org/documentation/tutorials/intro-to-parallelism-part-2/): カプセル、キー、ロックとの組み合わせ。
- [モードの構文](https://oxcaml.org/documentation/modes/syntax/)、[リファレンス](https://oxcaml.org/documentation/modes/reference/): `@`、`@@`、省略規則と詳細。
- [kindの概説](https://oxcaml.org/documentation/kinds/intro/): 型の性質とmode crossingの情報。
- [Mode Crossing論文](https://people.mpi-sws.org/~bpeters/papers/mode-crossing.pdf): modal kind、推論、抽象型、形式的な根拠。

### 確認したことと、していないこと

公式資料と原論文の説明を照合し、古い構文・構想と現在の個別説明を区別した。Markdownの文書間リンク、目次の参照先、コードブロックの構造は確認した。

OxCaml処理系の導入、モード付きコードの実行、性能測定、コンパイラ実装の安全性監査は行っていない。コード断片の受理・拒否については、公式規則に基づく説明であり、この環境で得たコンパイラの実行結果としては扱わない。
