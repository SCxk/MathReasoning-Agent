# Discrete Mathematics Skill Handbook

## Retrieved Solution Directives: `val_wrong15` Games, Counting, and Recurrences

### Nine-neighborhood growth against four-cell cutting

- **Similarity description:** On a large grid, one player increases every tree in a chosen 3-by-3 neighborhood, while the opponent decreases four positive trees; find the number that can eventually cross a huge height threshold.
- **Retrieval terms:** `3x3 add one four cells subtract one grid potential coverage`.
- Model each height as cumulative nine-neighborhood coverage minus cuts. Split the board into residue classes modulo 3. The gardener repeatedly reinforces an interior center class while the lumberjack has only four decrements each round. The matching upper bound uses total-height potential and boundary strips. The exact interior/block computation is \(2025\cdot1125=2278125\). Ignore the bird sentence: it changes no move or payoff.

### Equal-removal marble-box merging

- **Similarity description:** Start with 2025 one-marble boxes; remove equal amounts from two boxes and create a new box holding their combined removed marbles; minimize nonempty boxes.
- **Retrieval terms:** `marble boxes equal removal merge parity invariant binary valuation`.
- An operation maps \((p,q)\) to \((p-t,q-t,2t)\). Total marbles stay 2025. One nonempty box is impossible: the final created box has even size, while all remaining odd mass cannot disappear. A repeated equal-removal/doubling chain empties all but two boxes while preserving two active residues. Hence the lower bound 2 is attained.

### Increasing paths from even-even local minima

- **Similarity description:** Label a 78-by-78 board bijectively; count increasing adjacent paths beginning at even-even local minima, and minimize that count.
- **Retrieval terms:** `grid increasing paths local minima even even orientation 78`.
- Orient each grid edge from the smaller label to the larger one. Every allowed start contributes all directed paths, including the zero-edge path. Double-count compulsory sources, first edges, and branching in each 2-by-2 block, with boundary blocks counted once. A layered snake labeling realizes only the forced branches. The lower and upper counts meet at 12013. Do not omit single-cell paths.

### Parity density for monotone bijections of \(\mathbb N^2\)

- **Similarity description:** A bijection \(f:\mathbb Z_{\ge0}^2\to\mathbb Z_{\ge0}\) preserves order after either coordinate translation; optimize the number of odd images in a 100-by-100 square.
- **Retrieval terms:** `order preserving bijection N2 parity Ferrers diagram 100x100`.
- Every sublevel set \(\{f<t\}\) is a Ferrers initial region of exactly \(t\) cells. Values are added at outer corners one at a time, and odd values are alternate points on this growth path. Push the path to the two extreme boundary shapes inside \([0,99]^2\) to obtain the minimum and maximum counts, then multiply; the product is \(18750000\). The stated \(g(n)=n^2-n+1\) is unused noise.

### Sparse local growth in 75-by-75 neighborhoods

- **Similarity description:** A green cell may create exactly \(s\) new green cells inside its centered 75-by-75 neighborhood; find the least \(s\) for which every process has only linear-size growth.
- **Retrieval terms:** `75x75 local growth sparse threshold isoperimetric branching`.
- Assign boundary/exposure potential by residue classes. At the threshold, every move has nonpositive net exposed resource, giving \(O(n)\) cells for every legal process. One larger value permits disjoint 75-by-75 branching blocks and \(\Omega(n^2)\) cells in a constructed process. The critical resource count is \(4181=37\cdot113\): verify both \(s=4181\) and the branching at \(s=4182\).

### Four-round survivor count for circular name tags

- **Similarity description:** Sixteen name tags are permuted around a circle; fixed tags leave each round and remaining tags shift right; count arrangements with a survivor after four rounds.
- **Retrieval terms:** `circular permutation fixed points shift survivor four rounds derangement`.
- Count the complement. Choose the first-round fixed-tag set, compress the remaining circle, choose the next fixed set, and repeat four times. At each layer use derangements for labels not yet fixed. Time order matters, so ordinary inclusion-exclusion over four fixed-point conditions is invalid. The four-layer complement sum gives survivor count \(85383238549\), with empty exit sets and final 0/1-seat boundary cases retained.

### Path independent-set partition polynomial

- **Similarity description:** Compute the \(\lambda\)-weighted independent-set generating polynomial of a path.
- **Retrieval terms:** `path independent set polynomial recurrence binomial coefficient`.
- Split on the final vertex:
  \[
  Z_{P_n}(\lambda)=Z_{P_{n-1}}(\lambda)+\lambda Z_{P_{n-2}}(\lambda),\quad Z_{P_0}=1,\ Z_{P_1}=1+\lambda.
  \]
  The coefficient of \(\lambda^k\) is \(\binom{n-k+1}{k}\). For \(n=15\), the ascending coefficients are \(1,15,91,286,495,462,210,36,1\); the maximum independent-set size is \(\lceil15/2\rceil=8\).

### Two-pile card-selection minimax game

- **Similarity description:** Players alternately select cards 1 through 50 and assign each to one of two piles; one minimizes and the other maximizes the final absolute sum difference.
- **Retrieval terms:** `card selection two piles partition game minimax complementary pairs`.
- Track the signed pile difference \(D\). Pair cards as \((1,50),\ldots,(25,26)\). A same-pair reply bounds the net contribution of each pair and gives \(|D|\le75\); the opposing forcing strategy prevents all pairs from being canceled and gives \(|D|\ge75\). Thus the game value is 75. The odd total 1275 only establishes parity, not the bound.

### Power-of-two numerical semigroup gap

- **Similarity description:** With generators \(2^n-2^i\) for \(0\le i<n\), find the first positive integer not representable by their nonnegative sums.
- **Retrieval terms:** `numerical semigroup powers of two 2^n-2^i Frobenius gap`.
- Write each generator as \(2^i(2^{n-i}-1)\), induct by the lowest binary valuation to represent every integer through \((n-2)2^n\), and analyze the next integer modulo \(2^n\). Any representation of \((n-2)2^n+1\) would force a negative coefficient. The first gap is therefore \((n-2)2^n+1\).

### Exotic exponents for universal divisibility functions

- **Similarity description:** Count integer functions with \(g(1)=1\) and \(g(a)-g(b)\mid a^n-b^n\), then find a specified exponent for which that count is twice an odd number.
- **Retrieval terms:** `integer function universal divisibility n-good exotic 2-adic valuation square criterion`.
- Substitute \(0,1,-1\) and adjacent integers to classify all allowable families, then verify each family for arbitrary distinct inputs. Write \(n=2^e m\) with \(m\) odd, factor the family count, and impose “twice an odd number” through the divisor-function square criterion and the 2-adic branch. Ordered enumeration gives the 132nd term \(69169=263^2\), not an unproved brute-force search.

### Odd-part function and simultaneous congruences modulo 4

- **Similarity description:** Let \(f(t)\) be the odd part of \(t\); classify \(u\) for which some \(v\) makes \(f(u+v+i)-f(u+i)\) divisible by 4 for all \(0\le i<v\).
- **Retrieval terms:** `odd part function 2-adic valuation consecutive differences modulo 4`.
- Write \(f(t)=t/2^{\nu_2(t)}\). Compare 2-adic valuations in the interval \([u,u+2v-1]\); the uniquely highest-valuation position restricts \(v\), and endpoint odd residues modulo 4 restrict \(u\). Explicit witnesses remain for \(u=1,3,5\); every \(u\ge6\) has a first high-valuation conflict with unequal odd parts modulo 4.

## Retrieved Solution Directives: `val_wrong20` Competition Items

### Five positive reals and product pairing

- **Similarity description:** From five distinct positive reals choose four and relabel them so that two products have universally bounded relative error.
- **Retrieval terms:** `five positive reals product pairing adjacent ratios half bound`.
- Divide by \(fh>0\): construct \(\left|e/h-g/f\right|\le T\). After sorting \(u_1<\cdots<u_5\), write quotients as products of \(r_i=u_i/u_{i+1}\). The crossing-pairing lemma on logarithmic gaps produces two disjoint quotients at distance at most \(1/2\); a limiting geometric progression proves sharpness.
- **Reference-answer submission suggestion:** \(\boxed{\tfrac12}\).

### Bounded subset sum near 1810

- **Similarity description:** Integer terms lie in \([0,100]\), their total is at least 1810, and one must guarantee a subset sum nearest 1810.
- **Retrieval terms:** `bounded integer subset sum maximal sum gap lemma 1810 100 48`.
- Take the maximal attainable \(s\le1810\). Ordered attainable sums cannot have a gap of at least 97 near the target: adding an unused term or deleting a used term of size at most 100 contradicts maximality. The residual critical window has radius 48. The standard critical-residue construction avoids the interior of \([1763,1857]\), proving sharpness.
- **Reference-answer submission suggestion:** \(\boxed{48}\).

### Digit DP for \(\{0,1,2,8\}\) and divisibility by 3

- **Similarity description:** Count natural numbers of at most 16 decimal digits, every digit in \(\{0,1,2,8\}\), divisible by 3.
- **Retrieval terms:** `digits 0 1 2 8 modulo 3 dynamic programming length 16`.
- If \(A_{r,\ell}\) counts strings with digit sum \(r\bmod3\), then
  \[
  A_{r,\ell+1}=A_{r,\ell}+A_{r-1,\ell}+2A_{r-2,\ell}.
  \]
  A nonzero first digit has initial vector \((0,1,2)\). The residue-zero counts through length 16 sum to \(1431655764\); official convention also counts 0.
- **Reference-answer submission suggestion:** \(\boxed{1431655765}\). Do not allow leading zeroes in multi-digit numbers.

### Alternating dominoes on a 2020-cell path

- **Similarity description:** Players place disjoint dominoes on a path; Alice maximizes and Bob minimizes final uncovered cells.
- **Retrieval terms:** `path domino game minimax 2020 uncovered cells mod 7`.
- Decompose into uncovered segments and induct on segment lengths modulo 7. Bob makes each full seven-cell block leave at most one empty cell; Alice maintains the matching endpoint state. With \(2020=288\cdot7+4\), both strategies give 290.
- **Reference-answer submission suggestion:** \(\boxed{290}\).

### Domino/S-tetromino rectangle tiling

- **Similarity description:** Tile a \(1008\times1010\) rectangle with dominoes and rotatable S-tetrominoes while minimizing dominoes.
- **Retrieval terms:** `1008 1010 domino S tetromino periodic coloring invariant 506`.
- A periodic coloring is balanced on every S-tetromino; each domino corrects at most one unit of the board's color imbalance, hence at least 506 are needed. A periodic S-tetromino tiling of the interior plus two boundary strips tiled by 506 dominoes attains it.
- **Reference-answer submission suggestion:** \(\boxed{506}\).

### Querying black pillars in an \(18^3\) cube

- **Similarity description:** Reconstruct pairwise non-touching black \(1\times1\times18\) pillars by querying cell colors.
- **Retrieval terms:** `18 cubed cube disjoint pillars color queries identify 486`.
- An unqueried essential cross-section location permits two distinct legal pillar sets, each with at least two pillars, that agree on all answers. Each direction requires 162 distinguishing positions, hence \(3\cdot162=486\); querying them identifies every pillar.
- **Reference-answer submission suggestion:** \(\boxed{486}\).

### Erasing integer pairs without opposite signs

- **Similarity description:** Erase entries from 68 pairs but never erase two opposite integers; maximize the worst-case number of hit pairs.
- **Retrieval terms:** `68 integer pairs no opposite erased guarantee score 43`.
- Each absolute value is a binary sign choice. Random sign selection followed by conditional expectation, using the ban on both \((k,k)\) and \((-k,-k)\), guarantees 43 hit pairs. The standard 68-pair blocking construction gives the matching upper bound.
- **Scoring convention:** ignore the undefined broken-whiteboard sentence.
- **Reference-answer submission suggestion:** \(\boxed{43}\).

### Critical covers by 2012 lines

- **Similarity description:** A point set is not coverable by \(n\) lines but becomes coverable after any one point is deleted; maximize its size.
- **Retrieval terms:** `critical line cover delete any point n lines binomial n plus 2 choose 2`.
- The critical line-cover lemma gives \(|S|\le\binom{n+2}{2}\); a general-position dual/projection construction attains it. Thus \(\binom{2014}{2}=2014\cdot2013/2=2027091\).
- **Reference-answer submission suggestion:** \(\boxed{2027091}\).

### Equal coverage under \(52\times52\) square overlays

- **Similarity description:** Overlay finitely many \(52\times52\) squares on a \(2011\times2011\) board and maximize cells sharing one nonzero coverage count.
- **Retrieval terms:** `2011 2011 52 52 napkins same coverage 3986729`.
- Since \(2011=52\cdot39-17\), residue-class sums on a row have 39 terms for 35 residues and 38 for 17 residues. Repeating the count by columns forces at least
  \[
  (52^2-35^2)\cdot39-17^2=57392
  \]
  exceptional cells. A stepped placement of squares realizes common coverage 1 on every other cell.
- **Reference-answer submission suggestion:** \(\boxed{2011^2-57392=3986729}\).

### Personal nonadjacency selection game

- **Similarity description:** Players choose unused numbers from \(1\) to \(n\), while a player's own chosen numbers may not be consecutive; find the largest draw.
- **Retrieval terms:** `two player number game personal nonadjacent choices draw largest n 6`.
- State recursion gives a draw at 6, with three numbers selected by each player. For \(n\ge7\), Bob's mirror/central-blocking reply leaves Alice first without a legal choice.
- **Reference-answer submission suggestion:** \(\boxed6\). The adjacency rule is personal, not global.

### Unique domino tiling with marked cells

- **Similarity description:** Mark cells of a \(194\times194\) board so one domino tiling is unique and every domino has at most one mark.
- **Retrieval terms:** `unique perfect matching domino tiling 194 by 194 marked cells 194`.
- Unique perfect matchings recursively contain forced edges. Counting forced-edge stripping chains along diagonals gives the lower bound 194. A zigzag diagonal of 194 marks forces boundary dominoes layer by layer and achieves it.
- **Reference-answer submission suggestion:** \(\boxed{194}\).

### Three-direction slice-color matching

- **Similarity description:** Color a \(45^3\) cube so that every slice-color set in one direction occurs in each other direction; maximize colors.
- **Retrieval terms:** `45 cubed cube colors three directions slice color sets 31395`.
- Double-count color--slice incidences in the three directions and compress each color to minimal slice support, giving the upper bound 31395. A layered cyclic Latin-array construction attains it.
- **Reference-answer submission suggestion:** \(\boxed{31395}\). Interpret the stray \(n^2\) as \(45^2\).

### Equal-degree row/column classes in a 0--1 matrix

- **Similarity description:** In a \(200\times200\) seat matrix, no two reserved seats may lie in equal-degree rows and equal-degree columns; two rows have degree \(m\).
- **Retrieval terms:** `200 by 200 zero one matrix equal row degrees equal column degrees 96`.
- Group rows and columns by degree. Each row-degree-class by column-degree-class block contains at most one 1. Double-count 1s incident with the two degree-\(m\) rows to obtain \(m\le96\); a cyclic degree-class construction attains it.
- **Reference-answer submission suggestion:** \(\boxed{96}\).

### Cut-and-update pebble game

- **Similarity description:** Bob cuts 100 boxes; Alice adds 1 to all boxes on one side and subtracts 1 on the other, seeking eternal positivity.
- **Retrieval terms:** `100 boxes cut add one subtract one pebble game potential 2600`.
- For \(2q\) boxes, the symmetric tent potential satisfies \(P_1=3\), \(P_q=P_{q-1}+2q+1\), both as Bob's lower-bound cut and Alice's response. Hence
  \[
  P_q=3+\sum_{j=2}^q(2j+1)=q(q+2),\qquad P_{50}=50\cdot52=2600.
  \]
- **Reference-answer submission suggestion:** \(\boxed{2600}\).

### Two increasing buy/sell chains

- **Similarity description:** Two merchants have increasing sell endpoints and increasing buy endpoints among 7396 locations; force a pair connected by both.
- **Retrieval terms:** `7396 ordered locations two increasing interval chains common connected pair 7311`.
- The two-chain crossing lemma bounds either chain by \(N-86\) if no common connected pair exists. A staircase of interlaced endpoints is sharp, so the first guaranteed length is \(7396-86+1=7311\).
- **Reference-answer submission suggestion:** \(\boxed{7311}\).

### Fibonacci difference basis and Lucas condition

- **Similarity description:** Find the smallest integer set whose difference set covers \(F_2,\ldots,F_{125}\) and a Lucas-number difference.
- **Retrieval terms:** `Fibonacci difference basis Lucas L100 minimum set 64`.
- The identity \(F_{r+1}-F_{r-1}=F_r\) gives a recursive difference graph. Pairing its required edges constructs 64 integers. Conversely, Zeckendorf uniqueness shows one new point covers at most two new essential differences, forcing at least 64. The Lucas condition uses \(L_{100}=F_{101}+F_{99}\).
- **Scoring convention:** the final \(T\) is undefined; read it only as existence of a pair with difference \(L_{100}\).
- **Reference-answer submission suggestion:** \(\boxed{64}\).

## Domain Boundaries and Routing Conventions

- Scope: combinatorial counting, graph theory, recurrences, generating functions, number-theoretic divisibility, combinatorial games, coding, and combinatorial design.
- Does not take over: pure Euclidean geometry is routed to the foundational or advanced geometry course; linear programming, scheduling, and resource optimization are routed to operations research; continuous limits and extrema in real variables are routed to mathematical analysis.
- Verification contract: for counting problems, state the state space and boundary cases; for games, distinguish P/N states; for number theory, check divisibility, coprimality, and modular-arithmetic conditions term by term.

> Covers the core modules of propositional logic, set theory, combinatorics, number theory, graph theory, Boolean algebra, recurrence relations, generating functions, partially ordered sets, and so on.
> Suitable for course study and competition preparation.

---

## 1. Simplification of Propositional Logic

### Core Definitions and Theorems

- **Propositional variables**: symbols representing truth values (True/False), such as `p`, `q`, and `r`.
- **Logical connectives**: negation (`¬`), conjunction (`∧`), disjunction (`∨`), implication (`→`), and equivalence (`↔`).
- **Equivalent formulae**: two logical expressions that have the same truth value under every truth assignment.

### Core Formulae

| Name | Formula |
|------|------|
| Idempotent laws | `p ∧ p ≡ p`, `p ∨ p ≡ p` |
| Commutative laws | `p ∧ q ≡ q ∧ p`, `p ∨ q ≡ q ∨ p` |
| Associative laws | `(p ∧ q) ∧ r ≡ p ∧ (q ∧ r)`, `(p ∨ q) ∨ r ≡ p ∨ (q ∨ r)` |
| Distributive laws | `p ∧ (q ∨ r) ≡ (p ∧ q) ∨ (p ∧ r)`, `p ∨ (q ∧ r) ≡ (p ∨ q) ∧ (p ∨ r)` |
| De Morgan's laws | `¬(p ∧ q) ≡ ¬p ∨ ¬q`, `¬(p ∨ q) ≡ ¬p ∧ ¬q` |
| Complement laws | `p ∧ ¬p ≡ F`, `p ∨ ¬p ≡ T` |
| Identity laws | `p ∧ T ≡ p`, `p ∨ F ≡ p` |
| Domination laws | `p ∧ F ≡ F`, `p ∨ T ≡ T` |

### Standard Step-by-Step Solution Procedure

1. Convert every implication (`→`) and equivalence (`↔`) into expressions using the basic forms `¬`, `∧`, and `∨`.
2. Push negations inward using De Morgan's laws.
3. Repeatedly apply distributive laws to expand (or factor out common factors).
4. Eliminate redundant terms using the complement, identity, and domination laws.
5. Check whether a simplest form has been reached (no further simplification law can be applied).

### Frequent Examination Pitfalls

- **Wrong direction of the distributive law**: applying it to `p ∨ (q ∧ r)` gives `(p ∨ q) ∧ (p ∨ r)`, not `(p ∨ q) ∧ r`.
- **Omitting a sign in De Morgan's laws**: `¬(p ∧ q)` is equivalent to `¬p ∨ ¬q`; note that the connective changes from `∧` to `∨`.
- **Flexible use of commutativity and associativity**: an expression such as `(p ∨ q) ∧ (p ∨ ¬q)` should first be combined by distributivity into `p ∨ (q ∧ ¬q) = p`.

### Examination Techniques

- Use the truth-table method as a fallback: when the number of variables is `≤ 4`, directly construct and compare truth tables.
- Look for **complementary pairs**: when `p` and `¬p` occur together, first consider eliminating them using a complement law.
- Use Karnaugh maps: for `3–4` variables, they are more intuitive than algebraic simplification.

### Competition Extension: Classification of Solutions to Functional Equations

Solutions to the functional equation $f(g(x)) = h(f(x))$ can be classified according to the iteration properties of $g$. When $g$ is a linear fractional transformation, analysis of its fixed points is crucial: if the fixed points of $g$ are $\alpha, \beta$, a conjugacy transformation reduces it to a normal form and then determines the form of the general solution for $f$.

**Examination note**: use a closed form for $g^{(n)}(x)$ to reduce the functional equation to a polynomial identity or a recurrence relation. Common techniques include the fixed-point method, the bridge-function method (the Schröder equation), and coefficient comparison.

**Pitfalls**: ignoring the periodicity of $g$ and thereby missing solution families; confusing fixed points with poles in fractional linear transformations.

---

## 2. Combinatorial Counting

### Core Definitions and Theorems

- **Binomial coefficient**: `C(n, k) = n! / (k! (n−k)!)`, the number of ways to choose `k` from `n` distinct elements.
- **Addition principle**: if a task can be carried out in `m` mutually exclusive classes of ways and class `i` has `n_i` methods, then the total number of methods is `Σ n_i`.
- **Multiplication principle**: if a task requires `m` consecutive steps and step `i` has `n_i` methods, then the total number of methods is `Π n_i`.

### Core Formulae

- `C(n, k) = C(n, n−k)`
- `C(n, k) = C(n−1, k) + C(n−1, k−1)` (Pascal's identity)
- Binomial theorem: `(x + y)^n = Σ_{k=0}^n C(n, k) x^{n−k} y^k`

### Standard Step-by-Step Solution Procedure

1. Determine the problem type: permutation (order matters) or combination (order does not matter).
2. Decide whether case analysis is needed (for example, an “at least” condition) → split into mutually exclusive cases.
3. Compute each case using binomial or permutation counts, then add the results using the addition principle.
4. Verify: count all possibilities and subtract cases that fail the condition (the complement method).

### Frequent Examination Pitfalls

- **Double counting**: cases in a classification are not mutually exclusive and thus overlap.
- **Missing cases**: omitting some subcases when handling “at least `k`”.
- **Confusing order**: treating a combination problem as a permutation problem.

### Examination Techniques

- For “at least” problems, first consider the complement method (total number minus the number that do not meet the condition).
- Verify by computing the same problem in two different ways; the results should agree.
- When values are large, first simplify using binomial identities.

### Competition Extension: Counting Structures with Symmetry

For counting structures with a symmetry-group action, use Burnside's lemma (the Cauchy–Frobenius lemma): the number of orbits is $\frac{1}{|G|}\sum_{g\in G}|\text{Fix}(g)|$. For rotational symmetry (the cyclic group $C_n$), counting fixed points reduces to enumerating periodic structures; for the dihedral group $D_n$, reflection symmetries must also be considered. Pólya's enumeration theorem generalizes this to weighted coloring problems: substitute into the cycle index $Z(G; s_1, \ldots, s_n)$ and expand to obtain the numbers of orbits of each weight.

**Examination note**: first identify the symmetry-group type (cyclic/dihedral/full symmetric), then write the cycle index, and finally substitute the generating function. For small $n$, direct enumeration using Burnside's lemma can be used for verification.

**Pitfalls**: confusing counts for conjugacy classes (invariant elements under a group action versus fixed points of the group elements themselves); forgetting that reflection axes through vertices and through edge midpoints have different numbers of fixed points.

### Competition Extension: Double Counting for Combinatorial Extremes and Turán's Theorem

Double counting is a central tool for combinatorial extremal problems: count the same object in two ways to obtain an equality constraint and then derive an extremum. Turán's theorem is a cornerstone of extremal graph theory: the maximum number of edges in an $n$-vertex graph containing no $K_{r+1}$ subgraph is $\left(1-\frac{1}{r}\right)\frac{n^2}{2} + O(n)$, attained by the Turán graph $T(n,r)$, the complete $r$-partite graph whose parts are as equal as possible.

**Examination note**: when double counting an incidence matrix, summing by rows equals summing by columns; proofs of Turán's theorem often use induction on a vertex of maximum degree.

**Pitfalls**: the Turán graph is not unique, and the sizes of any two parts differ by at most `1`; in a concrete problem, do not reverse the correspondence between “containing no given subgraph” and “the maximum number of edges.”

### Competition Extension: Extremes under Sequence-Sum Constraints

Given $\sum_{i=1}^n a_i = S$ and a range for every $a_i$, to optimize $\sum_{i=1}^n f(a_i)$, if $f$ is convex, extrema are attained at endpoints by Karamata's inequality or Jensen's inequality. For optimization of integer solutions under linear sum constraints, use the discrete Lagrange-multiplier method or greedy adjustment.

**Examination note**: determining whether the objective function is convex or concave is the first step; under integer constraints, an extremum usually occurs at a distribution in which the variables are as “extreme” as possible (for example, all at the maximum/minimum, or only one variable at an intermediate value).

**Pitfalls**: directly applying conclusions from continuous optimization in a discrete domain (for example, a Lagrange-multiplier solution that is nonintegral); forgetting to verify feasibility of an extremum (variables must lie in the prescribed range and be integers).

---

## 3. Set Operations and Identities

### Core Definitions and Theorems

- **Intersection**: `A ∩ B = {x | x ∈ A and x ∈ B}`.
- **Union**: `A ∪ B = {x | x ∈ A or x ∈ B}`.
- **Difference**: `A − B = {x | x ∈ A and x ∉ B}`.
- **Complement**: `A^c = U − A` (`U` is the universal set).
- **Cardinality**: `|A|`, the number of elements of set `A`.

### Core Formulae

| Name | Formula |
|------|------|
| Commutative laws | `A ∩ B = B ∩ A`, `A ∪ B = B ∪ A` |
| Associative laws | `(A ∩ B) ∩ C = A ∩ (B ∩ C)`, and likewise for `∪` |
| Distributive law | `A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C)` |
| De Morgan's laws | `(A ∩ B)^c = A^c ∪ B^c`, `(A ∪ B)^c = A^c ∩ B^c` |
| Cardinality formula | `|A ∪ B| = |A| + |B| − |A ∩ B|` |

### Standard Step-by-Step Solution Procedure

1. **Identity proof**: take an arbitrary `x ∈` the left-hand side → derive the conditions it satisfies → show `x ∈` the right-hand side. Prove the converse similarly.
2. **Cardinality calculation**: use the inclusion–exclusion principle to handle overlaps.

### Frequent Examination Pitfalls

- Confusing difference and complement: `A − B ≠ A ∩ B^c` (the two are equivalent, but the notation requires care).
- `(A − B) − C` and `A − (B − C)` are different; expand them carefully.

### Examination Techniques

- Draw a Venn diagram to aid understanding (but not as a rigorous proof).
- Additivity of cardinality: if sets are pairwise disjoint, `|A ∪ B| = |A| + |B|`.

---

## 4. Number-Theoretic Foundation: Extended Euclidean Algorithm

### Core Definitions and Theorems

- **Greatest common divisor** `gcd(a, b)`: the greatest positive integer that divides both `a` and `b`.
- **Bézout's theorem**: there exist integers `x, y` such that `ax + by = gcd(a, b)`.

### Core Formulae

- Euclidean algorithm: `gcd(a, b) = gcd(b, a mod b)`.
- Extended Euclidean algorithm: during the recurrence of the Euclidean algorithm, simultaneously back-substitute to solve for `x, y`.

### Standard Step-by-Step Solution Procedure

1. Repeatedly perform division with remainder, `a = q b + r`, `0 ≤ r < b`, until the remainder is `0`.
2. The last nonzero remainder is `gcd(a, b)`.
3. Starting from the penultimate step, back-substitute to express each remainder as a linear combination of the original `a, b`.
4. Rearrange to obtain one solution of `ax + by = gcd(a, b)`.

### Frequent Examination Pitfalls

- **Sign errors in back-substitution**: pay attention to sign changes at every step; it is advisable to record them in a table.
- **Requirement for the solution with smallest `|x|`**: the general solution is `x = x_0 + (b/g)·t`, `y = y_0 − (a/g)·t`; choose `t` to minimize `|x|`.

### Examination Techniques

- Use a table to track the remainders and coefficients at every step, avoiding confusion in back-substitution.
- Verify by substitution: multiply the obtained `x, y` back into the original expression and check that it equals `gcd`.

---

## 5. Homogeneous Recurrence Relations

### Core Definitions and Theorems

- Linear homogeneous recurrence: `a_n = c_1 a_{n−1} + c_2 a_{n−2} + ... + c_k a_{n−k}`.
- **Characteristic-equation method**: set `a_n = r^n`; substituting into the recurrence gives `r^k − c_1 r^{k−1} − ... − c_k = 0`.

### Core Formulae

- Second-order homogeneous recurrence: `a_n = c_1 a_{n−1} + c_2 a_{n−2}`.
  - Characteristic equation: `r^2 − c_1 r − c_2 = 0`.
  - Two distinct real roots `r_1, r_2`: `a_n = A·r_1^n + B·r_2^n`.
  - Repeated root `r_0`: `a_n = (A + Bn)·r_0^n`.

### Standard Step-by-Step Solution Procedure

1. Write the characteristic equation and solve for its roots.
2. Write the general-solution form according to the nature of the roots.
3. Substitute the initial conditions to solve for the undetermined coefficients `A, B`.
4. Verify that the first several terms agree with the recurrence.

### Frequent Examination Pitfalls

- **Wrong indexing of initial conditions**: pay attention to the correspondence of `a_0` and `a_1`.
- **Omitting complex roots**: when the characteristic equation has complex roots, express the solution in trigonometric form.
- **Forgetting to multiply by `n` for a repeated root**: the repeated-root general solution is `(A + Bn)·r^n`, not `A·r^n + B·r^n`.

### Examination Techniques

- First check whether `a_2` satisfies the recurrence, as a quick verification that the general solution is correct.
- When the characteristic roots are integers, first try factorization.

### Competition Extension: Recurrences for Path Structures

Grid-path problems can be solved by defining a state recurrence. For restricted paths on an $m \times n$ grid (for example, paths that cannot cross the diagonal or must avoid obstacles), let $dp[i][j]$ be the number of legal paths from the starting point to $(i,j)$. The transition equation $dp[i][j] = dp[i-1][j] + dp[i][j-1]$ applies only when the target cell is reachable. For weighted path counts, use the bivariate generating function $F(x,y) = \sum_{i,j} dp[i][j] x^i y^j$.

**Examination note**: Catalan numbers are the special case in which a path does not cross the diagonal; the reflection principle (André reflection) handles constraints in which a path touches a boundary.

**Pitfalls**: incorrect initialization of boundary conditions (treatment of row/column `0`); the `dp` value of an obstacle cell must always be `0`, rather than being left blank.

---

## 6. Inclusion–Exclusion Principle

### Core Definitions and Theorems

- Inclusion–exclusion principle: `|A ∪ B ∪ C| = |A| + |B| + |C| − |A∩B| − |A∩C| − |B∩C| + |A∩B∩C|`.

### Core Formula

- General form: `|∪_{i=1}^n A_i| = Σ|A_i| − Σ|A_i∩A_j| + Σ|A_i∩A_j∩A_k| − ... + (−1)^{n−1}|∩_{i=1}^n A_i|`.

### Standard Step-by-Step Solution Procedure

1. Introduce sets for the decomposed conditions: let `A_i = {elements satisfying condition i}`.
2. Compute the cardinalities of the individual sets, pairwise intersections, triple intersections, and so on.
3. Alternately add and subtract according to the inclusion–exclusion formula.
4. Subtract as required by the problem (for example, “not divisible by any condition” = total number − size of the union).

### Frequent Examination Pitfalls

- **Use the LCM when calculating an intersection**: “divisible by both `2` and `3`” → “divisible by `lcm(2,3)=6`.”
- **Alternating-sign rule**: intersections of an odd number of sets have a positive sign; intersections of an even number have a negative sign.

### Examination Techniques

- First draw a Venn diagram to identify how each part is covered.
- In large-number division, use `N // lcm` to count divisibility.

---

## 7. Chinese Remainder Theorem

### Core Definitions and Theorems

- **Chinese remainder theorem (CRT)**: if the moduli `m_1, m_2, ..., m_k` are pairwise coprime, then the simultaneous congruences
  `x ≡ a_1 (mod m_1), x ≡ a_2 (mod m_2), ..., x ≡ a_k (mod m_k)`
  have a unique solution modulo `M = m_1 m_2 ... m_k`.

### Core Formulae

- Let `M = Π m_i`, `M_i = M / m_i`.
- Find `y_i` such that `M_i · y_i ≡ 1 (mod m_i)`.
- `x ≡ Σ (a_i · M_i · y_i) (mod M)`.

### Standard Step-by-Step Solution Procedure

1. Verify that the moduli are pairwise coprime (if not, first factor and merge them).
2. Compute `M = Π m_i` and every `M_i = M / m_i`.
3. For each `M_i`, find its multiplicative inverse `y_i` modulo `m_i` (using the extended Euclidean algorithm).
4. Substitute into the formula, add, and reduce modulo `M`.

### Frequent Examination Pitfalls

- **Non-coprime moduli**: if the moduli are not coprime, first factor and merge them, or use the general CRT.
- **Incorrect inverse computation**: `M_i · y_i ≡ 1 (mod m_i)`; ensure that `y_i` lies in the residue range modulo `m_i`.

### Examination Techniques

- For verification, substitute the result into every congruence separately.
- Fermat's little theorem may compute inverses when the modulus is prime, but the extended Euclidean algorithm is more general.

---

## 8. Boolean Algebra and Karnaugh-Map Simplification

### Core Definitions and Theorems

- **Boolean function**: `f: {0,1}^n → {0,1}`, representable by a truth table or a sum of minterms (SOP).
- **Minterm**: a product term in which every variable appears exactly once, either uncomplemented or complemented.
- **Karnaugh map**: a two-dimensional graphical representation of a truth table in which adjacent cells differ in only one variable.

### Core Formulae

- SOP form: `f = Σ m(i)`, where `m(i)` is the `i`-th minterm.
- Simplification rule: `2^k` adjacent `1`s can be merged into one product term, eliminating `k` variables.

### Standard Step-by-Step Solution Procedure

1. Express the Boolean function in sum-of-minterms (SOP) form.
2. Draw the Karnaugh map for the corresponding number of variables.
3. Circle all rectangular blocks of size `2^k` (as large and as few as possible).
4. Each rectangle corresponds to one implicant; read off the simplified product term.
5. Sum them to obtain the simplest SOP expression.

### Frequent Examination Pitfalls

- **Karnaugh-map row and column order**: arrange them by Gray code (`00→01→11→10`), not in natural binary order.
- **Missed coverage**: some minterms may be covered by more than one rectangle; ensure that every `1` is circled at least once.
- **Wrap-around adjacency**: the top and bottom, and the left and right, sides of a Karnaugh map are adjacent; rectangles may cross a boundary.

### Examination Techniques

- Observe parity and modulo-`2` patterns in minterm indices to determine simplifications quickly.
- With many minterms, first identify variables that remain unchanged in all minterms.

---

## 9. Graph-Theory Foundations: Complete Bipartite Graphs, Trees, and Eulerian Graphs

### Core Definitions and Theorems

- **Complete bipartite graph $K_{m,n}$**: `m` vertices in the left part and `n` vertices in the right part, with every cross-part pair connected.
- **Tree**: a connected acyclic undirected graph. A tree with `n` vertices has `n−1` edges.
- **Leaf**: a vertex of degree `1`. Every tree with `n ≥ 2` has at least `2` leaves.
- **Euler circuit**: a closed walk that uses every edge exactly once. It exists precisely when the graph is connected and every vertex has even degree.
- **Euler trail (non-closed)**: a connected graph with exactly `2` vertices of odd degree.

### Core Formulae

- Number of edges of $K_{m,n}$ = `m × n`.
- Tree properties: number of edges = number of vertices − `1`, `Σdeg(v) = 2(n−1)`.
- Euler-circuit condition: connected graph `∧` every vertex has even degree.

### Standard Step-by-Step Solution Procedure

**Proof of a tree property:**

1. Let the number of leaves be `L`; there are `n−L` non-leaves (of degree `≥ 2`).
2. By the handshaking theorem, `Σdeg(v) = 2(n−1) ≥ L·1 + (n−L)·2 = 2n − L`.
3. Hence `L ≥ 2`.

**Testing for an Euler circuit:**

1. Confirm that the graph is connected.
2. Check the parity of every vertex degree.
3. If all degrees are even → an Euler circuit exists; if exactly `2` vertices have odd degree → an Euler trail exists; otherwise neither exists.

### Frequent Examination Pitfalls

- In complete bipartite graph $K_{m,n}$, “complete” means only that all cross-part edges are present; it is **not** a complete graph.
- A spanning tree always has `v−1` edges, regardless of the particular structure of the graph.
- Confusing an Euler circuit with a Hamilton cycle: the former traverses edges; the latter traverses vertices.

### Examination Techniques

- To add edges to $K_{m,n}$ so that it has an Euler circuit, pair the odd-degree vertices; each added edge changes the degree parity of two vertices.
- A tree with exactly `2` leaves is the path graph $P_n$.

### Competition Extension: Block Decomposition of Hamilton Paths

Partition the vertex set of a graph into blocks, each containing a Hamilton path, with the blocks connected by a small number of edges. Block-decomposition techniques are commonly used to prove Hamiltonicity in tournament graphs and strongly connected directed graphs. Rédei's theorem: every tournament has a Hamilton path. Camion's theorem: every strongly connected tournament has a Hamilton cycle.

**Examination note**: construct the block decomposition by greedy insertion: insert a new vertex into an appropriate position in an already constructed Hamilton path while preserving directionality.

**Pitfalls**: an incorrect direction for an inter-block connecting edge breaks the path; do not confuse the number of Hamilton cycles in a complete graph, `$(n-1)!/2$`, with the situation for a general graph.

### Competition Extension: Ordering Monotonicity and the Triangle Inequality

In a weighted complete graph, if the weight function satisfies the triangle inequality $w(i,j) + w(j,k) \geq w(i,k)$, then an optimal Hamilton cycle has monotonicity: when vertices are arranged in some total order, the path weight is smallest. For problems satisfying ordering monotonicity (such as distances between points on a line), the shortest cycle is the cycle ordered by coordinates.

**Examination note**: first verify whether the weight function satisfies the triangle inequality; if it does, sorting is often the first step in constructing an extremal solution.

**Pitfalls**: direction of the triangle inequality—maximization problems require the reversed inequality; the influence of sorting direction (increasing versus decreasing) on cycle weight.

### Competition Extension: Worst-Case Analysis of Dynamic Processes on Grids

Define a dynamic process on an $n \times n$ grid (such as diffusion, filling, or movement) and analyze its number of running steps or resource consumption in the worst case. Common tools include the potential-function method (define a monotonically changing quantity that changes by at least `1` at every operation), amortized analysis, and lower-bound constructions (an adversary argument—construct an adversarial strategy making the process as slow as possible).

**Examination note**: constructing a suitable potential function is key; for a worst-case lower bound, construct an initial configuration forcing the algorithm to make the maximum possible number of operations.

**Pitfalls**: defining the monotonic direction of a potential function (increasing/decreasing) incorrectly; using average-case analysis in place of worst-case analysis.

### Competition Extension: Puzzle Tilings and Coloring Invariants

For tiling problems on a chessboard (grid), such as dominoes and L-shaped trominoes, coloring is the central tool. Standard black-and-white chessboard coloring gives a necessary condition: coverability by $1\times 2$ dominoes $\Rightarrow$ equal numbers of black and white cells. Generalized $k$-coloring (coloring modulo $k$) applies to more complex puzzles (for example, coverage by right-angle trominoes requires a numerical relation among three colors). The general invariant pattern is: define a map $f: \text{configuration} \to G$ ($G$ is a group or a modulus); the value of $f$ remains unchanged under every legal operation, while the target and initial configurations have different $f$ values $\Rightarrow$ the transformation is impossible.

**Examination note**: for a board with two cells removed that is to be covered by $1\times 2$ dominoes, first check the difference in the number of black and white cells; if it is `0`, a stronger coloring (for example, alternating row-and-column coloring) is needed.

**Pitfalls**: asserting sufficiency after verifying only a necessary condition (chessboard coloring is necessary but not sufficient; Hall's theorem or a construction is also needed); different puzzle shapes require different coloring schemes, so black-and-white coloring cannot be used uniformly.

### Competition Extension: Covers and Matchings in Graphs

Graph vertex covers and matchings are dual problems. König's theorem: in a bipartite graph, the size of a maximum matching equals the size of a minimum vertex cover. Hall's marriage theorem gives a necessary and sufficient condition for a bipartite graph to have a matching saturating every vertex in the left part: $\forall S \subseteq L, |N(S)| \geq |S|$. The relation between edge covers and independent sets is $\alpha'(G) + \beta'(G) = n$ (Gallai's theorem, where $\alpha'$ is the maximum-matching size and $\beta'$ is the minimum-edge-cover size).

**Examination note**: for bipartite matching/cover problems, first apply König's theorem and Hall's theorem; the fact that an independent set is a clique in the complement graph can be used for problem transformation.

**Pitfalls**: König's theorem applies only to bipartite graphs, not general graphs; Hall's condition must hold for all subsets, and checking only neighborhoods of individual vertices is insufficient.

### Competition Extension: Grid Worst-Case Extremes

Place marked points on an $m \times n$ grid subject to a distance or positional constraint on every pair, and find the maximum number of marks. Such problems are discrete analogues of independent-set or packing problems. When the constraint is translation invariant, they reduce to density problems for periodic tilings. Common constructions include classification modulo $k$ (classify grid cells by coordinates modulo $k$, choosing at most one point in each class) and greedy row-by-row construction.

**Examination note**: first identify the region “occupied” by each marked point (for example, a diamond neighborhood under a Manhattan-distance constraint), then use an area argument for an upper bound; construct a configuration attaining the bound to prove tightness.

**Pitfalls**: subtracting boundary-overlap portions repeatedly when computing overlapping regions; overlooking the grid point occupied by the mark itself.

### Competition Extension: Counting Domino Tilings under Constraints

The number of ways to tile a $2 \times n$ board with $1 \times 2$ dominoes is $F_n$ (the Fibonacci number, $F_1=1, F_2=2$). For an $m \times n$ board, Kasteleyn's formula gives the exact domino-tiling count through a Pfaffian determinant:
$$\prod_{j=1}^{m}\prod_{k=1}^{n}\left(4\cos^2\frac{\pi j}{m+1} + 4\cos^2\frac{\pi k}{n+1}\right)^{1/4}.$$
For a board with obstacles, use recurrence + bitmask DP (profile DP).

**Examination note**: for $2\times n$, immediately use the Fibonacci recurrence; for domino tilings of $3\times n$ and larger, use a transfer matrix or generating functions to obtain a recurrence.

**Pitfalls**: wrong direction for the initial condition (`2\times 0` has one tiling—the empty tiling); confusing the domino-tiling recurrence with the stair-climbing recurrence (the former has horizontal and vertical choices, while the latter has only one-step and two-step choices).

### Competition Extension: Grid Growth Processes and Density

The steady-state density of growth processes on a grid (such as the Eden model, percolation, and Rule 184 in cellular automata) can be analyzed. For a deterministic rule (for example, “if at least $k$ occupied cells surround a cell, it becomes occupied at the next time”), the eventual density is jointly determined by the initial configuration and the rule. Analyze invariant density using a discrete potential function or a conserved quantity.

**Examination note**: for systems with an additive invariant, the total invariant at the initial time determines features of the final configuration; under periodic boundary conditions, density analysis can often be simplified to the stationary distribution of a finite-state automaton.

**Pitfalls**: confusing the asymptotic density of a deterministic growth process with the critical density of random percolation; ignoring the essential impact of boundary conditions (open boundaries versus periodic boundaries) on density.

---

## 10. Generating Functions and Restricted Combinations

### Core Definitions and Theorems

- **Generating function**: converts a combinatorial-counting problem into operations on polynomials/power series.
- For `x_1 + x_2 + ... + x_k = n`, the number of nonnegative integer solutions with `0 ≤ x_i ≤ u_i` for every `i` is the coefficient of `x^n` in `(1 + x + ... + x^{u_1})·...·(1 + x + ... + x^{u_k})`.

### Core Formulae

- Number of unrestricted nonnegative integer solutions: `C(n + k − 1, k − 1)` (the stars-and-bars model).
- Use inclusion–exclusion to assist with upper-bound restrictions.

### Standard Step-by-Step Solution Procedure

1. For every variable, write the generating-function factor for its allowed values.
2. Multiply all factors and obtain the coefficient of the target exponent.
3. Alternatively, use inclusion–exclusion: unrestricted number of solutions − solutions in which at least one variable exceeds its bound + solutions in which at least two variables exceed their bounds − ... .

### Frequent Examination Pitfalls

- Inclusion–exclusion shift under an upper bound: `x_i ≥ u+1` means set `y_i = x_i − (u+1) ≥ 0`, reducing the right side of the equation by `u+1`.
- When coefficients are large, take care not to miss terms: ensure that cases in which three or more variables exceed their bounds cannot occur.

### Examination Techniques

- When constraints are symmetric and ranges are small, enumerate coefficients by brute force (appropriate for small-range verification).
- Inclusion–exclusion and generating functions serve as mutual checks.

---

## 11. Equivalence Relations and Quotient Sets

### Core Definitions and Theorems

- **Equivalence relation**: a binary relation satisfying reflexivity, symmetry, and transitivity.
- **Equivalence class**: `[a] = {x | x R a}`; every element belongs to exactly one equivalence class.
- **Quotient set** `A/R`: the set consisting of all equivalence classes.
- Equivalence relations and partitions of a set correspond bijectively.

### Core Formula

- The sum of the cardinalities of the quotient-set elements equals the cardinality of the partitioned set: `Σ|[a]| = |A|`.

### Standard Step-by-Step Solution Procedure

1. Verify the three properties: `∀a∈A, aRa` (reflexivity); `aRb ⇒ bRa` (symmetry); `aRb ∧ bRc ⇒ aRc` (transitivity).
2. Determine the equivalence class of each element (start with a representative and find all related elements).
3. List all distinct equivalence classes → the quotient set.

### Frequent Examination Pitfalls

- An equivalence class is independent of the choice of representative: any element of a class can represent it.
- The union of equivalence classes is the universal set, and the classes are pairwise disjoint.

### Examination Techniques

- Congruence modulo `n` is a classical equivalence relation; its equivalence classes are residue classes modulo `n`.
- Quotient-set size = number of equivalence classes; the sum of all class sizes = `|A|`.

---

## 12. Combinatorial Identities

### Core Definitions and Theorems

- **Vandermonde's identity**: `Σ_{k=0}^r C(m, k)·C(n, r−k) = C(m+n, r)`.
- **Special form**: `Σ_{k=0}^n C(n, k)^2 = C(2n, n)` (take `m = n`, `r = n`).

### Core Formulae

- `C(n, k) = C(n, n−k)`.
- `C(n, k)·C(k, r) = C(n, r)·C(n−r, k−r)`.
- Symmetry of binomial coefficients: `C(n, k) = C(n, n−k)`.

### Standard Step-by-Step Solution Procedure

**Combinatorial-proof procedure:**

1. Construct a combinatorial model: interpret the two sides as two ways of counting the same problem.
2. Interpret the left-hand side as a sum after classification by some condition.
3. Interpret the right-hand side as direct counting.
4. Since the same objects are counted, the two sides are equal.

**Numerical-verification procedure:**

1. For a particular `n`, compute the values of both sides.
2. Confirm that the equality holds.

### Frequent Examination Pitfalls

- In a combinatorial proof, the “classification” must be mutually exclusive and exhaustive.
- The square `C(n, k)^2` should be understood as `C(n, k)·C(n, n−k)`.

### Examination Techniques

- Identify the identity type: Vandermonde, Pascal, or a transformation of the binomial theorem.
- Substitution method: assign special values to variables (for example, `x=1, y=1`) to obtain useful results quickly.

### Competition Extension: Frequency-Vector Method for Polynomial Identities

For proving combinatorial identities, the frequency-vector method (also called the “probabilistic model for sequences” method) interprets a summation as the expectation of a random variable and thus simplifies the derivation with probability tools. For example, $\sum_k k\binom{n}{k}p^k(1-p)^{n-k} = np$ is the expectation of a binomial distribution. More generally, in the multinomial theorem $(x_1+\cdots+x_m)^n = \sum_{k_1+\cdots+k_m=n}\binom{n}{k_1,\ldots,k_m}x_1^{k_1}\cdots x_m^{k_m}$, the multinomial coefficients $\binom{n}{k_1,\ldots,k_m}$ form the distribution of the frequency vector $(k_1,\ldots,k_m)$.

**Examination note**: substitution is still the fastest way to verify/discover an identity; for identities containing parameter $n$, coefficient extraction with generating functions can give a formal proof.

**Pitfalls**: omitting cross terms in a polynomial expansion; ignoring the frequency-vector constraint $k_1+\cdots+k_m=n$ during simplification.

---

## 13. Nonhomogeneous Recurrence Relations

### Core Definitions and Theorems

- Nonhomogeneous recurrence: `a_n = c_1 a_{n−1} + ... + c_k a_{n−k} + f(n)`.
- Structure of the solution: general solution = homogeneous general solution + a particular nonhomogeneous solution.

### Core Formulae

- Homogeneous part: characteristic-equation method (as in Section 5).
- Choice of particular-solution form:
  - if `f(n)` is a polynomial, assume a polynomial of the same degree;
  - if `f(n)` is exponential `a^n`, assume `C·a^n` when `a` is not a characteristic root; if `a` is a characteristic root of multiplicity `m`, assume `C·n^m·a^n`.

### Standard Step-by-Step Solution Procedure

1. Solve the homogeneous part to obtain `a_n^{(h)}`.
2. According to the form of `f(n)`, assume a particular solution `a_n^{(p)}`, checking whether it conflicts with a homogeneous solution (resonance).
3. Substitute into the recurrence to determine the particular-solution coefficients.
4. Set `a_n = a_n^{(h)} + a_n^{(p)}` and use initial conditions to determine the homogeneous coefficients.

### Frequent Examination Pitfalls

- **Missing resonance**: when `f(n)` has the same form as a term in the homogeneous solution, the particular solution must be multiplied by `n` (or a higher power).
- **Combining equal-degree terms during substitution**: compare coefficients term by term to determine unknown parameters.

### Examination Techniques

- First compute several terms using the initial conditions, then compare them with the closed form for verification.
- When `f(n)` is exponential, first determine whether it coincides with a characteristic root.

---

## 14. Proofs of Number-Theoretic Divisibility

### Core Definitions and Theorems

- `a | b`: there is an integer `k` such that `b = k·a`.
- **Fermat's little theorem**: if `p` is prime and `p ∤ a`, then `a^{p−1} ≡ 1 (mod p)`.
- **Factorization method**: `n^5 − n = n(n−1)(n+1)(n^2+1)`.

### Core Formulae

- `n(n−1)(n+1)` is the product of three consecutive integers → it is divisible by `3! = 6` (containing factors `2` and `3`).
- The product of `k` consecutive integers is divisible by `k!`.

### Standard Step-by-Step Solution Procedure

1. Factor the dividend and look for consecutive integer factors.
2. Prove that every prime factor divides the dividend (prime-factorization method).
3. Or use Fermat's little theorem/Euler's theorem to prove a congruence modulo `p`.

### Frequent Examination Pitfalls

- To prove divisibility by `30`, prove divisibility by `2`, `3`, and `5` separately, rather than merely asserting divisibility by `30`.
- Pay attention to completeness in prime factorization: do not omit factors.

### Examination Techniques

- `n^p − n` divisible by `p` (Fermat's little theorem) is a common pattern.
- Test with particular numerical values to verify a divisibility conclusion.

### Competition Extension: Binary Invariants

In combinatorial games and construction problems, binary (bitwise) representations often provide effective invariants. The Nim-sum (bitwise XOR) is the central invariant of Nim: the Nim-sum of all heap sizes is `0` if and only if the current position is a P-position (the first player is forced to lose). More generally, for problems involving binary choices, pairings, or set partitions, define a linear combination of vectors over $\mathbb{F}_2$ as an invariant.

**Examination note**: for problems in which every operation changes the parity of certain quantities, consider a modulo-`2` invariant; the Sprague–Grundy theorem reduces the Nim values of arbitrary impartial games to a Nim-sum.

**Pitfalls**: reversing the equivalence between a zero Nim-sum and a P-position; forgetting to determine whether a game is impartial—the position transitions in a directed-graph game must be the same for both players.

---

## 15. Catalan Numbers

### Core Definitions and Theorems

- **Catalan numbers** `C_n` satisfy `C_0 = 1`, `C_{n+1} = Σ_{i=0}^n C_i·C_{n−i}`.
- Applications: parenthesization of matrix products, valid matching of `n` pairs of parentheses, triangulations of polygons, and so on.

### Core Formulae

- Closed form: `C_n = (1/(n+1))·C(2n, n)`.
- Recurrence: `C_{n+1} = ((4n+2)/(n+2))·C_n`.

### Standard Step-by-Step Solution Procedure

1. Identify whether the problem belongs to a typical Catalan-number application.
2. Establish the recurrence `Σ_{i=0}^{n−1} C_i·C_{n−1−i}`.
3. Use the closed form or recurrence to compute the value.

### Frequent Examination Pitfalls

- The value of `C_6` is easily miscomputed: `C_6 = 132`; a common error is `42` (mistaking `C_5` for `C_6`).
- Initial condition for the Catalan recurrence: `C_0 = 1`, not `C_0 = 0`.

### Examination Techniques

- Memorize the first several Catalan numbers: `C_0=1, C_1=1, C_2=2, C_3=5, C_4=14, C_5=42, C_6=132`.
- Use `C_{n+1} = (4n+2)/(n+2)·C_n` for rapid computation.

---

## 16. Partially Ordered Sets and Lattices

### Core Definitions and Theorems

- **Partial order**: a binary relation `⪯` satisfying reflexivity, antisymmetry, and transitivity.
- **Hasse diagram**: a visualization of a partially ordered set, omitting self-loops and transitive edges.
- **Extremal elements**:
  - minimal element: no other element can precede it;
  - maximal element: no other element can follow it;
  - least element: precedes every element (if it exists, it is unique);
  - greatest element: follows every element (if it exists, it is unique).
- **Chain**: a totally ordered subset (any two elements are comparable). Length of a longest chain = number of elements it traverses.

### Core Formula

- Length of a longest chain: the maximum number of vertices passed through from a minimal element to a maximal element in a Hasse diagram.

### Standard Step-by-Step Solution Procedure

1. Draw the Hasse diagram: begin with the smallest elements and connect upward level by level.
2. Minimal elements: bottom-level elements with no incoming edges in the Hasse diagram.
3. Maximal elements: top-level elements with no outgoing edges.
4. Greatest element: the unique upper bound that can reach all elements.
5. Least element: the unique lower bound reachable from all elements.
6. Longest chain: find the longest top-to-bottom path in the Hasse diagram.

### Frequent Examination Pitfalls

- **Difference between maximal and greatest**: there can be more than one maximal element (for example, `6` and `8` can both be maximal in a divisibility poset), whereas a greatest element is unique if it exists.
- In a divisibility poset, a minimal element need not be `1`; if `1` is absent, begin with the smallest primes.

### Examination Techniques

- For divisibility relations, first list the network of divisibility relations among every number in the set.
- Longest chain = from the least element to the greatest element, multiplying by one distinct prime factor at each step.

### Competition Extension: Poset Extremes for Row and Column Degrees

In an $m \times n$ binary matrix, the row-sum and column-sum vectors satisfy partial-order constraints. If row sums and column sums are sorted in nonincreasing order, namely $(r_1 \geq r_2 \geq \cdots \geq r_m)$ and $(c_1 \geq c_2 \geq \cdots \geq c_n)$, they must satisfy the Gale–Ryser theorem:
$$\sum_{i=1}^k r_i \leq \sum_{j=1}^n \min(k, c_j)$$
for every $k$. This is a necessary and sufficient condition for existence of a bipartite degree sequence, expressed in matrix language.

**Examination note**: the Gale–Ryser conditions provide an existence criterion; in extremal problems, first assume without loss of generality that row sums are sorted nonincreasingly, then use inequalities to bound above and below.

**Pitfalls**: inconsistent sorting directions (if row sums increase while column sums decrease, the form of the condition differs); omitting the sorting requirement for row/column sums.

### Competition Extension: Translation-Invariant Total-Order Rank Functions

For a poset $(P, \preceq)$, if there is a function $\rho: P \to \mathbb{Z}$ such that $x \prec y$ (a covering relation) implies $\rho(y) = \rho(x) + 1$, then $\rho$ is called a rank function and the poset is a graded poset. For structures with translation invariance (such as Young tableaux and Boolean lattices), rank functions exist naturally—for example, the rank of a Boolean lattice is subset size. Sperner's theorem characterizes the largest antichain size in a graded poset: if the rank distribution is $N_0, N_1, \ldots, N_r$, then the largest antichain size is $\leq \max_k N_k$.

**Examination note**: verify existence of a rank function; Sperner's theorem and its generalizations (the LYM inequality) are powerful tools for set families and hypergraph extremal problems.

**Pitfalls**: rank functions do not always exist (a poset must satisfy the Jordan–Dedekind chain condition); for an antichain $\mathcal{F}$, the LYM inequality is $\sum_{A \in \mathcal{F}} \frac{1}{\binom{n}{|A|}} \leq 1$.

---

## 17. Pigeonhole Principle

### Core Definitions and Theorems

- **Pigeonhole principle (drawer principle)**: placing `n+1` objects into `n` drawers means that at least one drawer contains at least `2` objects.
- **Generalization**: placing `m` objects into `n` drawers means that at least one drawer contains at least `⌈m/n⌉` objects.
- **Dirichlet principle (strong form)**: if $\sum_{i=1}^n a_i > rn$, then there exists `i` with $a_i \geq r+1$.
- **Ramsey-type pigeonhole principle**: every `2`-coloring of the edges of complete graph $K_6$ contains a monochromatic $K_3$. More generally, $R(s,t)$ is the smallest `n` such that every red-blue edge coloring of $K_n$ contains a red $K_s$ or a blue $K_t$.

### Core Formulae

- Basic form: if `k > n`, then putting `k` objects into `n` boxes leaves at least one box containing `≥ 2` objects.
- Average form: some box contains at least $\lceil \frac{m}{n} \rceil$ objects, and some box contains at most $\lfloor \frac{m}{n} \rfloor$ objects.
- Coprimality property: any two consecutive positive integers are coprime, i.e. `gcd(k, k+1) = 1`.
- Erdős–Szekeres theorem: every real sequence of length $n^2+1$ contains a monotone subsequence of length $n+1$.
- Dilworth's theorem (a structural extension of pigeonhole): the largest antichain size in a poset equals the minimum number of chains that partition the poset.

### Standard Step-by-Step Solution Procedure

1. Identify the “pigeons” (selected elements) and “pigeonholes” (the classification criterion).
2. Prove number of pigeons > number of pigeonholes → at least two pigeons occupy the same hole.
3. Show that the two elements in the same hole possess the required property (for example, adjacency or coprimality).

### Common Pigeonhole Constructions

- **Adjacent-pair pattern**: partition $\{1,2,\ldots,2n\}$ into `n` pairs `(1,2), (3,4), ..., (2n-1, 2n)`; selecting `n+1` numbers forces two from one pair.
- **Residue-class pattern**: classify integers into `k` residue classes modulo `k`; selecting `k+1` numbers forces two congruent numbers (whose difference is divisible by `k`).
- **Interval-partition pattern**: divide `[0,1]` into `n` equal subintervals; among `n+1` points, two have distance `≤ 1/n`.
- **Sequence-partial-sum pattern**: consider partial sums $S_k = \sum_{i=1}^k a_i$ (there are `n+1` of them); modulo `n`, two are congruent, and their difference $S_j-S_i$ (a consecutive-subarray sum) is divisible by `n`.
- **Base-representation pattern**: the binary-representation length of an integer is $\lfloor \log_2 n \rfloor + 1$; for a sufficiently large set, some bit has a repeated-value pattern.
- **Coloring-impact pattern**: pigeonhole proofs of existence often combine graph colorings—if the vertex count exceeds the maximum capacity of a color class, a structure satisfying a particular coloring condition exists.

### Frequent Examination Pitfalls

- **Improper pigeonhole construction**: the pigeonholes must cover all possibilities and be pairwise disjoint.
- Failure to prove that same-hole elements necessarily have the desired property (such as coprimality).
- **Underestimating the number of pigeonholes**: when multiple constraints are involved, use all possibilities as pigeons, not merely the “selected” ones.
- **Confusing directions in the average form**: $\lceil m/n \rceil$ means that some box has at least that many; $\lfloor m/n \rfloor$ means that some box has at most that many.
- **Misusing Ramsey numbers**: `R(3,3)=6` cannot be directly generalized to estimates of `R(k,k)`.

### Examination Techniques

- When constructing pigeonholes, commonly pair adjacent integers: `(1,2), (3,4), ..., (2n−1, 2n)`.
- Proof that adjacent integers are coprime: if `d | k` and `d | (k+1)`, then `d | (k+1)−k = 1`, hence `d = 1`.
- When direct pigeonhole construction is hard, consider an auxiliary sequence (such as partial sums or accumulated values), which provides additional pigeonhole dimensions.
- For existence problems, the pigeonhole principle is the most direct nonconstructive method; if a constructive example is needed, combine it with a greedy algorithm.
- For parameterized extremal questions (for example, “the minimum number of pigeons that forces a property”), treat pigeonholes as a classification scheme and solve backwards for the threshold using the average form.

### Competition Extension: Combinatorial Deepening of the Pigeonhole Principle

Advanced pigeonhole techniques include Dirichlet's rational-approximation principle (when $\alpha$ is irrational, there are infinitely many reduced fractions $p/q$ with $|\alpha-p/q| < 1/q^2$); lower-bound estimates for Ramsey numbers combining coloring and graph theory; and proving tight pigeonhole bounds by the probabilistic method (Erdős's probabilistic method—if the expectation under random selection satisfies an inequality, then some particular selection also satisfies it).

**Examination note**: for sequence problems of length $n^2+1$, recall the Erdős–Szekeres theorem; for divisibility constraints, construct `n` pigeonholes corresponding to residue classes modulo `n`; partial sums modulo `n` are a classical pigeonhole pattern.

**Pitfalls**: a partial-sum sequence has length `n+1` (including $S_0=0$), while there are only `n` pigeonholes (residues `0` through `n-1` modulo `n`); when proving existence of a contiguous subarray with a property, remember that the subarray may be empty (`i=j`).

---

## 18. General Problem-Solving Methodology

### Problem-Type Recognition

| Problem feature | Knowledge topic | Solution tool |
|---------|--------|---------|
| Expression simplification | Propositional logic / Boolean algebra | Basic equivalences / Karnaugh map / truth table |
| Number of selections | Combinatorial counting | Binomial coefficients / permutations / addition and multiplication principles |
| Counting set elements | Set operations / inclusion–exclusion | Venn diagram / inclusion–exclusion formula |
| Finding `gcd` and coefficients | Extended Euclidean algorithm | Euclidean algorithm + back-substitution |
| Sequence closed form | Recurrence relations | Characteristic equation / particular-solution method |
| Not divisible by a number | Inclusion–exclusion | Total number − union of divisible cases |
| Simultaneous congruences | Chinese remainder theorem | CRT formula / extended Euclidean algorithm for inverses |
| Determining graph structural properties | Graph theory | Handshaking theorem / Euler theorem / tree properties |
| Number of equation solutions with upper bounds | Generating functions / inclusion–exclusion | Polynomial expansion / inclusion–exclusion shifts |
| Determining relation properties | Equivalence relations | Verification of three properties / equivalence-class partition |
| Identity proof | Combinatorial identities | Combinatorial proof / algebraic proof |
| Divisibility of `n^p − n` | Number theory | Factorization / Fermat's little theorem |
| Tree properties | Graph theory—trees | Handshaking theorem / leaf counting |
| Number of parenthesizations | Catalan numbers | Recurrence / closed formula |
| Extremal elements in a poset | Posets and lattices | Hasse diagram / divisibility network |
| Selecting elements that must contain a pair with a property | Pigeonhole principle | Pigeonhole construction / adjacent-coprimality property |

### Recommendations for Choosing Tools

- **Small-data brute-force enumeration**: when the variable range is `≤ 10^6`, prioritize enumeration for verification.
- **Double verification by recurrence + closed form**: for recurrence problems, calculate recurrence values and closed-form values in parallel to ensure correctness.
- **Symmetry check**: combinatorial-counting results often have symmetry (for example, `C(n,k) = C(n, n−k)`), which can be used for rapid checking.
- **Modular-arithmetic check**: for CRT and other number-theory problems, verify against each modulus separately.

### Ideas for Verifying Results

1. **Boundary-value tests**: use extreme values (such as `n=0`, `n=1`) to test whether a formula holds.
2. **Alternative method**: calculate the same problem by a completely different method; the results should agree.
3. **Symmetry test**: results of symmetric structures should be symmetric.
4. **Parity check**: parity of some binomial coefficients can serve as an initial filter.
5. **Computer verification**: use Python (`sympy`) for fast verification of medium-scale problems.

---

## 19. Competition Games

### Core Definitions and Theorems

- **Impartial game**: two players move alternately; the set of legal moves depends only on the current position (not on whose turn it is); the player with no legal move loses. Information is complete and there is no randomness.
- **P-position (Previous-win / losing position)**: from this position, regardless of what the first player does, the second player has a winning strategy.
- **N-position (Next-win / winning position)**: from this position, the first player has at least one move that changes the position to a P-position.
- **Sprague–Grundy theorem**: every impartial-game position is equivalent to a Nim heap of size $g$, where $g$ is the Grundy number defined by $g(v) = \text{mex}\{g(u) : v \to u\}$. The Nim-sum (XOR) of the Grundy numbers of several independent subgames determines the outcome: Nim-sum = `0` $\Leftrightarrow$ P-position.

### P/N-Position Criteria for Combinatorial Games

- A P-position has only N-position successors.
- An N-position has at least one P-position successor.
- A terminal position (with no legal move) is a P-position (Grundy number = `0`).
- Mark P/N states for all positions by backward recurrence from terminal positions.

### Guaranteed-Value Strategies for Two-Player Games

- **Target-region locking strategy**: map the game state space to a “target region.” If one player can lock the position in that region in finitely many moves and the opponent cannot escape, that player has a forced win.
- **DP modulo-period strategy**: for games whose state space is linear or grid-like, when computing Grundy numbers with dynamic programming, observe periodicity to greatly compress the state space. Such periods often arise from cycles of the `mex` operation in a modular sense.
- **Pairing/mirroring strategy (strategy stealing)**: in a symmetric game, the second player can preserve an invariant by mirroring the first player's move. If the mirroring strategy is always legal, the first player cannot win (and hence the second player wins).
- **Symmetry strategy**: when a position has central symmetry, the second player can remain undefeated by copying each first-player move at the symmetric position.

### Circular Transfer Games

In a circular transfer game, $n$ people sit in a circle, each initially holding an integer. Each move chooses adjacent people and transfers part of one person's value to the other (preserving the sum), with the goal of making all numbers equal or attaining some distribution. The central tools are **invariants** (such as total sum and weighted positional sum) and **monotone potential functions** (such as variance and $\sum$ of absolute values).

**Examination note**: first identify invariants (the total-sum invariant is obvious, but also seek weighted invariants such as $\sum i\cdot a_i$); use monotonicity to prove termination in finitely many steps.

**Pitfalls**: finding only the total-sum invariant and missing a weighted invariant, making reachability/non-reachability impossible to prove; the effect of transfer direction (clockwise versus counterclockwise) on the invariant's form.

### Standard Step-by-Step Solution Procedure

1. Determine the game type: impartial versus partisan, independent subgames versus one global game.
2. For an impartial game: compute Grundy numbers (recurring from small positions), then compute Nim-sum = XOR of the Grundy numbers.
3. For a partisan game or a complicated position: directly analyze P/N recurrence, or find a winning strategy (pairing/mirroring/target-region locking).
4. Verify the strategy's legality (every move lies within the rules) and forced-win property (whatever the opponent does, the strategy can continue).

### Frequent Examination Pitfalls

- **Omitting part of a Nim-sum**: Nim-sum is the XOR of Grundy numbers of all heaps, not ordinary addition.
- **Definition of `mex`**: `mex(S)` is the smallest nonnegative integer not in `S`. For example, `mex{0,1,3} = 2`.
- **Treating a non-impartial game as impartial**: if the two players have different legal-move sets, Grundy theory does not directly apply.
- **Failure conditions for a mirroring strategy**: when the move space is asymmetric or operations are irreversible, mirroring may be illegal.

### Examination Techniques

- For Nim-like heap-removal games, each heap is independent; directly take the Nim-sum of heap sizes.
- For Wythoff's game (remove any number from one heap, or the same number simultaneously from both), use Beatty sequences (the golden ratio) to express P-position coordinates.
- When the state space is small, compute a table of Grundy numbers by recurrence and observe periodicity.
- A “guaranteed-value” problem (the optimal outcomes of both players) is equivalent to minimax-tree search: take `max` on one's own layer and `min` on the opponent's layer.

---

## 20. Linear Separation of Two-Colored Point Sets

### Core Definitions and Theorems

- **Line-separation problem**: given $n$ red points and $n$ blue points in the plane (with no three collinear), does a line completely separate the two colors (red on one side and blue on the other)? Such a line always exists when the point sets are linearly separable.
- **Ham-sandwich theorem (discrete version)**: for `n` red and `n` blue points in arbitrary positions in the plane, a line exists that simultaneously bisects both colors (with `n/2` on each side).
- **Geometric duality of separation theorems**: line separation of point sets $\Leftrightarrow$ a dual relationship in the sense of separation of the convex hulls.

### Combinatorial Method

For red and blue point sets $\mathcal{R}, \mathcal{B}$:

- If the convex hulls of $\mathcal{R}$ and $\mathcal{B}$ intersect, no line can strictly separate them.
- If the convex hulls are disjoint, a separating line exists (the separating-hyperplane theorem). Construction: take the perpendicular bisector of a closest-point pair between the convex hull of $\mathcal{R}$ and the convex hull of $\mathcal{B}$.

### Counting Problems

- For `n` red points and `m` blue points, count geometric crossings among all $\binom{n+m}{2}$ segments joining points of different colors.
- Equivalence classes of partitions of a planar point set by lines (arrangements of lines) and region counting.

### Standard Step-by-Step Solution Procedure

1. Determine whether the convex hulls of the two color classes intersect (if they do, strict separation is impossible).
2. If they are disjoint, construct a separating line using a supporting hyperplane.
3. For an equal-size separation requirement, use rotating calipers or the ham-sandwich theorem.

### Frequent Examination Pitfalls

- Intersection of convex hulls is a necessary and sufficient condition for **inability to strictly separate**; the condition for “weak separation” (allowing points on the line) is broader.
- Three collinear points make existence of a separating line degenerate; problems usually add a general-position assumption.

### Examination Techniques

- For small point sets, draw the configuration directly and try to construct a separating line.
- For extremal/counting problems, regard a line as directed (by normal-vector direction); projection orders in different directions give different separating schemes.

---

## 21. Lempel–Ziv Dictionary Coding

### Core Definitions and Theorems

- **Lempel–Ziv coding (LZ78 / LZW)**: a lossless data-compression algorithm. Scan a string left to right and encode the longest current prefix not previously present in the dictionary as “dictionary index + next character.”
- **LZ complexity**: the number of LZ phrases $c(s)$ of a string $s$ is the number of blocks in its greedy parse. It measures the “information content” of the string—an entirely random string has $c(s) \approx n / \log n$, whereas a highly regular string has smaller $c(s)$.

### Core Properties

- Monotonicity of LZ phrases: phrase length is nondecreasing during parsing (it may stay unchanged).
- Relation between phrase count and string length: $c(s) = O(n / \log n)$ (for a binary alphabet).
- LZ parsing is unique (it is determined by the greedy algorithm).

### Typical Competition Questions

- Given a string (such as a binary sequence or integer sequence), compute its LZ phrase partition.
- Design a string whose number of LZ phrases is smallest/largest under a fixed-length constraint.
- Analyze LZ compression efficiency: total encoded bit count = $\sum_{i=1}^{c(s)} (\lceil \log_2 i \rceil + 1)$ (assuming each phrase encodes its index and next character).

### Standard Step-by-Step Solution Procedure

1. Initialize an empty dictionary $D = \{\}$ and phrase list $L = []$.
2. Scan from the left: find the shortest prefix $w$ that is not in $D$.
3. Add $w$ to $L$, and add $w$ to dictionary $D$.
4. Continue scanning after $w$ until the end of the string.

### Frequent Examination Pitfalls

- The terminal character of a phrase is already included in the new phrase: $w = v + c$, where $v$ is the longest existing dictionary prefix and $c$ is the next character.
- The “greedy” nature of LZ parsing means taking the longest prefix not in the dictionary each time, not an arbitrary prefix that is not in the dictionary.

### Examination Techniques

- To calculate LZ phrases by hand, scan character by character on paper, maintain the list of dictionary phrases already present, and check it.
- LZ phrase count is directly related to string complexity—a periodic string (such as `010101...`) has far fewer LZ phrases than a random string.

---

## Compatibility Rules for Competition Combinatorics, Number Theory, and Geometry

- In combinatorial counting, first distinguish permutations from combinations; then use inclusion–exclusion, pigeonhole, generating functions, or Burnside. For “at least,” prioritize the complement; finally check with small-scale enumeration, which cannot replace a general proof.
- For congruence problems, first check divisibility, Euler's/Fermat's theorem, multiplicative order, and LTE. When $2^k$ is involved, prioritize the Carmichael function $\lambda(2^k)$; do not unconditionally replace it with $\varphi(2^k)$.
- Elementary geometry may choose among coordinates, vectors, similarity, and power of a point; a geometric-construction problem must give both necessity and sufficiency and verify degenerate boundary cases.

---

## Appendix: Exercise Index Cross-Reference Table

| Problem ID | Knowledge topic | Difficulty | Brief description |
|------|--------|---------|
| idx=0 | Propositional-logic simplification | Easy | Simplify `(p∨q)∧(p∨¬q)∧(¬p∨q)` to `p∧q` |
| idx=1 | Combinatorial counting | Easy | Choose `5` from `10` men and `8` women with at least `2` women: `C(8,2)C(10,3)+... = 6636` |
| idx=2 | Set operations | Easy | In `{1..20}`, cardinalities of intersection/union of primes and odd numbers are `7, 11` |
| idx=3 | Extended Euclidean algorithm | Medium | `2021x+1984y=1`, solution `x=429, y=−437` |
| idx=4 | Homogeneous recurrence | Medium | `a_n=5a_{n-1}−6a_{n-2}`, `a_n=2^n+3^n`, `a_{10}=60073` |
| idx=5 | Inclusion–exclusion | Medium | Among `1` through `1000`, there are `266` numbers divisible by none of `2,3,5` |
| idx=6 | Chinese remainder theorem | Medium | `x≡2 (mod 5)`, `x≡3 (mod 7)`, `x≡2 (mod 11)`, solution `x=332` |
| idx=7 | Boolean algebra/Karnaugh map | Medium | `m(0,2,4,6,8,10,12,14)` simplifies to `¬D` |
| idx=8 | Graph-theory foundations | Medium | $K_{3,4}$ has `12` edges; a spanning tree has `6` edges |
| idx=9 | Generating functions | Medium | `x1+x2+x3+x4=20`, `0≤xi≤6`, number of solutions = `35` |
| idx=10 | Equivalence relations | Medium | Congruence modulo `3`; sum of quotient-set element sizes = `6` |
| idx=11 | Graph theory—Euler circuit | Medium | Determine Euler circuit for $K_{2,4}$ and required number of added edges |
| idx=12 | Combinatorial identities | Hard | `ΣC(8,k)²=C(16,8)=12870` |
| idx=13 | Nonhomogeneous recurrence | Hard | `a_n=3a_{n-1}−2a_{n-2}+2^n`, `a_n=3+2(n-1)2^n` |
| idx=14 | Set identity | Easy | `(A−B)−C = A−(B∪C)` |
| idx=15 | Number-theoretic divisibility | Medium | `n^5−n` is divisible by `30`; for `n=7` the quotient is `560` |
| idx=16 | Graph theory—trees | Medium | Every tree has at least `2` leaves; $P_{10}$ has `9` edges |
| idx=17 | Catalan numbers | Medium | `C_6 = 132` |
| idx=18 | Posets and lattices | Hard | Divisibility poset `{1,2,3,4,6,8,12,24}`, longest chain = `5` |
| idx=19 | Pigeonhole principle | Hard | Choosing `n+1` numbers from `{1..2n}` forces an adjacent coprime pair |

> End of document. All 20 exercises include coverage of knowledge points, solution methods, frequent pitfalls, and examination techniques.

## 22. Combinatorial Geometry: Lattice Points and Counting Symmetric Structures

### Core Method

When counting geometric objects on a symmetric grid or in a three-dimensional lattice, first parameterize objects by symmetry, then classify and sum by parameters and orbit representatives.

- **Regular hexagons in a triangular lattice**: a regular hexagon is determined by its side length and center position. There are two center types—lattice points and lattice-cell centers. For each center type, enumerate the legal side-length range and count hexagons in different orientations (including oblique orientations).
- **Orbit classification in a three-dimensional lattice**: divide into orbit classes by equality relations among coordinates (all equal $a=a=a$, exactly two equal $a=a\neq b$, and all distinct $a\neq b\neq c\neq a$) and parity of coordinate permutations; count color classes layer by layer.

### Examination Notes

- In a triangular lattice, note the legal ranges for the two types of centers; oblique regular hexagons are easy to omit.
- In three dimensions, count in layers by “coordinate-equality pattern + permutation parity”; the number of objects is the same within one orbit.

### Pitfalls

- Omitting objects of special rotation orientations; double-counting orbit classes; incorrectly determining parameter ranges (the upper bound on side length).

---

## 23. Extremal Line Covering of Planar Point Sets

### Core Method

Let a point set $S$ satisfy: “it cannot be covered as a whole by $k$ lines, but after deleting any one point the remaining point set can be covered by $k$ lines.” Find its maximum size.

- **Construction (lower bound)**: take a family of lines in general position (no parallels and no three concurrent), and let $S$ be all pairwise intersections. After deleting one intersection, all remaining intersections lie precisely on the $k-2$ lines other than the two lines determining that deleted intersection.
- **Upper bound**: an Erdős–de Bruijn-type theorem—sizes of point sets meeting the covering condition are quadratically bounded in the number of lines.
- **Additional constraint**: if the requirement also says “no circle passes through all points,” verify it explicitly after the construction.

### Examination Notes

- The symmetric condition “not coverable as a whole / coverable after deleting one point” strongly suggests an intersection-set construction.
- Use a dual perspective (incidence counting between points and lines) for the upper-bound proof.

### Pitfalls

- The line family must be in general position (parallel lines and triple concurrency change the intersection count); every intersection must be determined by exactly two lines; a cocircularity constraint is additional and must be ruled out after construction.

---

## 24. Area-Bisecting Segments in a Convex Polygon and Their Landing-Edge Distribution

### Core Method

Within a convex polygon, the area-bisecting segment from each vertex intersects the opposite boundary. The distribution of all endpoints is controlled by a continuity-and-partition argument:

- Area bisectors sweep the polygon continuously, and the landing edges associated with the vertices form at most a constant number of consecutive segments in boundary order.
- All endpoints land on at most a constant number of edges independent of the number of polygon edges.
- A minimum problem reduces to “this constant upper bound + a construction attaining exactly this distribution for every number of edges.”

### Examination Notes

- When asked for the least possible value of a quantity involving $n$, first determine whether it is independent of $n$ (by a continuity/intermediate-value argument), then provide a construction.
- In a construction, check every stated constraint individually (for example, an endpoint must not coincide with a vertex).

### Pitfalls

- Confusing an area bisector with a median (an area bisector need not pass through the midpoint of the opposite side); counting “consecutive segments” in a partition argument depends on boundary order, and coincident endpoints can cause over- or undercounting.

---

## 25. Congruent-Triangle Dissections and Tangential Polygons

### Core Method

When a convex polygon is dissected by nonintersecting diagonals into congruent triangles:

- The dissection structure (number of triangles and the number of angles meeting at every vertex) is fixed by the number of sides.
- Congruence forces every interior angle to be an integral-multiple allocation from the same set of triangle angles.
- If the polygon is additionally tangential to a circle (has an incircle), sums of opposite sides must be equal or angle bisectors must be concurrent.
- Compatibility of these two requirements occurs only in the smallest-side-count case; for more sides, rule out cases one by one through total-angle arguments or broken symmetry.

### Examination Notes

- First write angle-allocation equations from the dissection structure, then combine them with the tangency conditions.
- To “find all feasible numbers of sides,” use “construct the smallest feasible case + exclude all remaining cases.”

### Pitfalls

- Inscribed (having a circumcircle) and tangential (having an incircle) are different condition sets and must not be mixed; congruent triangles can have different numbers of angles meeting at different vertices, so check angle sums vertex by vertex.

---

## 26. Angle-Multiple Relations and Solution Counting in Collinear Configurations

### Core Method

Choose a moving point on the line containing a segment so that two subtended angles satisfy a multiple relation (for example, one angle is exactly half the other). This is essentially the geometry of trisecting the angle between rays:

- Use the sine rule or similarity to convert every ratio relation into an equation for the moving point's position (its distance to the intersection point).
- Once the inclination of the fixed line is set, each ratio relation has at most one solution on each ray.
- The maximum number of solutions occurs in a compatibility interval in which all solutions coexist; compatibility is jointly determined by the ratio of the endpoint distances to the intersection and the line inclination.

### Examination Notes

- Standard solution-count procedure: at most one solution per ray per relation → enumerate relations and directions → check the range conditions that can hold simultaneously.
- An answer giving a “maximum” must supply a configuration condition attaining it, not merely a count.

### Pitfalls

- Omitting solutions where the moving point lies on the other ray; “the larger angle is twice the smaller” and the reverse statement are two different cases; the number of solutions drops sharply when the endpoint-distance ratio lies outside the compatibility interval.

---

## 27. Face Visibility of Convex Polyhedra and Normal-Vector Separation

### Core Method

From an external observation point, a face of a convex polyhedron is visible if and only if the dot product of its outward normal vector with the viewing direction is positive:

- Requiring that, for every face, there be a point from which all other faces are visible while only that face is hidden is equivalent to every face normal being separable from all other normal vectors by a plane through the origin.
- In three dimensions, this property holds only for a simplex configuration (the dual structure of a tetrahedron).
- Constructively, for every tetrahedron face, choose an observation point close to that face and outside the other three faces, then verify faces one by one.

### Examination Notes

- Translate geometric visibility into a linear-separation problem for normal vectors, then invoke convex-cone and separation results (such as Carathéodory's theorem).
- First prove the upper bound (the number of faces cannot be larger), then give a construction attaining it.

### Pitfalls

- Verifying only “there is a point that sees most faces at once” while omitting the per-face condition that every face must be individually hideable; the observation point must lie strictly in the exterior half-space of the face.

## 28. Polynomial Identities and Mutual Inversion of Frequency Vectors (Partition Conjugation)

### Core Method

An identity between two polynomial products can be translated into: “the frequency vector of the roots of one is the multiplicity vector of the other,” namely a fixed point under self-composition of the frequency map:

- Applying the frequency map to an integer partition takes its conjugate partition.
- Fixed points (self-conjugate partitions) and 2-cycles give the complete solution structure.
- Use this to calculate the possible values of a target weighted sum.

### Examination Notes

- Rewrite the identity as a system of frequency equations; recognize that the frequency map = partition conjugation; enumerate the two types, “self-conjugate / paired cycles,” and calculate weighted values separately.

### Pitfalls

- Omitting paired-cycle classes; writing the shape of a conjugate partition incorrectly; mismatching weighted calculations with partition structure.

---

## 29. Latin Squares and Combinatorial Designs

### Core Method

Fill permutations of `n` symbols row by row in a table to form a structure in which “each row is a permutation and the elements in each column are distinct” (that is, a Latin square):

- Distinct elements in every column directly bound the maximum number of rows.
- Inter-row difference constraints require that any two rows have a numerical difference at least a given lower bound in at least one column; equivalently, row pairs that are “adjacent permutations” of each other are excluded.
- When the number of rows reaches its maximum, the table is an order-`n` Latin square, and counting reduces to counting Latin squares satisfying the difference condition.

### Examination Notes

- First derive the row-count upper bound from “all entries in every column are distinct” and prove attainability; fix the first row to remove full-row permutation symmetry before counting; check compatibility of the difference constraint with a cyclic Latin-square construction.

### Pitfalls

- Forgetting the row-count upper bound imposed by column distinctness; treating “the difference reaches the threshold in at least one column” as if it had to hold in every column; failing to divide out row-permutation symmetry in counting.

---

## 30. Scheduling Optimization and Tournament Fixtures

### Core Method

The goal of a round-robin schedule optimization problem is to minimize the total number of days all participants must stay:

- The key is arranging match order so that each player's schedule is as concentrated as possible.
- A recursive divide-and-conquer approach (first schedule matches within evenly split groups, then interleave cross-group matches) controls each player's stay window.
- The minimum total cost can be solved through a recurrence relation.
- Small instances (with few participants) often serve as starting points for verifying the recurrence.

### Examination Notes

- Given constraints such as the number of participants and matches schedulable per day, find the minimum total cost or construct an optimal schedule.

### Pitfalls

- Roughly estimating a player's stay as the sum of played matches while ignoring optimization of the continuous interval between the first and final matches; failing to use recursive structure and thereby dispersing the schedule and increasing cost.

---

## 31. The Max-Plus Semiring and Coordinatewise-Maximum Closure

### Core Method

When both addition and coordinatewise maximum are allowed on a set of integer-coefficient vectors, all integer vectors generated from an initial vector set have a “lattice plus semilattice” structure:

- One or two initial vectors can generate only a low-rank sublattice and cannot cover the full vector space.
- If one introduces an all-components-equal constant vector, a sign vector with alternating positive and negative entries, and a strictly increasing vector, then alternately applying addition and coordinatewise maximum can assemble all standard basis vectors coordinate by coordinate, thus generating the whole integer vector space.
- For the lower bound, use rank or size analysis showing insufficient generating power; for the upper bound, provide an explicit generation scheme.

### Examination Notes

- Note that the maximum operation can break the dimensional limitation of a purely additive closure; the constant vector is crucial for translational alignment.

### Pitfalls

- Assuming coordinatewise maximum does not change the rank of an additive closure; overlooking the constant vector's role in translational alignment; mistaking “generate the integer vector space” for mere linear generation.

---

## 32. Parity Analysis of Translation-Invariant Total Orders and Rank Functions

### Core Method

A bijection with translation-order-preserving behavior is equivalent to a translation-invariant total order, determined by a positive cone and taking the form “layers ordered by a linear functional + a tie-breaking rule within each layer”:

- Its rank function can be written as “number of preceding layers + offset within the layer.”
- This gives exact parity counts of ranks in a target rectangular region.
- Traverse the feasible parameter family (coprime slopes and tie-breaking rules) to optimize.

### Examination Notes

- Fix a linear functional and tie-breaking rule, calculate the count for that parameter choice, then compare the different parameter families; for parity counting, split into cases by the combination of layer-index parity and offset parity.

### Pitfalls

- Reversing the equivalence direction between an “order-preserving bijection” and a “translation-invariant total order”; different within-layer tie-breaking rules (smaller `x` first or smaller `y` first) give different counts; overlooking half-open-interval boundaries of the target region.

## 33. Closed Sets of Integer Polynomial Roots (Rich Sets)

### Core Method

Call an integer subset *rich* if every integer root of every integer-coefficient polynomial whose coefficients lie in the set also lies in the set:

- If the set also contains every element of the form “difference of two powers of `2`,” first deduce that it contains all powers of `2`, `0`, and $\pm1$.
- Closure expands layer by layer: when $a,b$ are in the set and $a\mid b$, the integer root $b/a$ of the linear polynomial $ax-b$ must be in the set, so division yields the quotient.
- Then $\pm1$ and all powers of `2`, by **signed binary expansion**, express every integer; induction proves that the set covers all integers.
- Therefore the only possible rich set is the whole set of integers.

### Examination Notes

- Standard pattern for closure-propagation proofs: start from seed elements, construct polynomials with coefficients in the set, and use root closure to obtain new elements. Linear polynomials correspond to division; quadratics often produce $\pm1$ and square-root-type elements.

### Pitfalls

- Expanding before establishing that powers of `2` and $\pm1$ belong to the set; ordinary binary expansion cannot generate all integers, so **signed** binary expansion is required; when proving uniqueness, forgetting to reduce every rich set to the unique possible case.

---

## 34. Diophantine Equations and Discriminant Parameterization

### Core Method

Parameterized Diophantine equations are commonly solved by “turning the equation into a quadratic in one variable and requiring the discriminant to be a perfect square”:

- If the discriminant simplifies to the square of a polynomial, directly obtain a parametric form for an entire family of integer solutions, with the parameter ranging over positive integers (both construction and substitution verification are indispensable).
- If only the parity of the solution count is required, convert the perfect-square discriminant constraint into a quadratic-form/norm equation (study representation numbers in an imaginary quadratic field); parity of the solution count is determined by the corresponding divisibility condition.
- First use nonnegativity of the discriminant to bound the variable range or parameter-family shape, then refine with the perfect-square condition.

### Examination Notes

- For an equation with radicals, first move terms and eliminate radicals to obtain a one-variable quadratic, then take the discriminant; for “parity of the number of ordered integer solutions,” first convert to parity of quadratic-form representation numbers rather than enumerating point by point.

### Pitfalls

- Failing to verify the parameterization by substitution and thus including extraneous solutions; overlooking variable bounds supplied by discriminant nonnegativity; oversimplifying a claim that the solution count is even without using a norm equation.

---

## 35. Digit Structure in Large-Number Division

### Core Method

For long division in which a fixed-digit-length dividend has no zero digit, analyze the digit structure of the quotient:

- Let the quotient have `L` digits and `t` nonzero digits, and let the divisor have `d` digits. Restore multiplication as a view in which a copy of “each nonzero quotient digit × divisor” is offset and superposed by place value.
- These copies must cover every dividend place exactly while producing no zero place; this yields a coverage inequality connecting `t·d` and the digit length of the dividend.
- Maximizing the number of zero digits in the quotient (`L-t`) becomes a discrete optimization balancing `L` and `t` under a digit budget.

### Examination Notes

- For quotient-digit-structure questions, first establish the “copy coverage” viewpoint; use digit-length inequalities to determine the feasible region, then optimize precisely near the integer lattice points; both an upper-bound proof and a construction are required.

### Pitfalls

- Treating a coverage inequality as an exact equality; ignoring the way carries fill gaps and thereby producing a failed construction; giving only a construction without proving optimality.

---

## 36. Decimal Digit Operations and Divisibility

### Core Method

- **Digit-deletion divisibility chains**: for a number with distinct digits such that “the number obtained by deleting one digit is a divisor of the original,” build by extending from one-digit numbers one digit at a time. Verify the maximum through an explicit deletion chain—at every step, deleting one digit yields the previous number. A deletion must not create a leading zero.
- **Digit sums modulo a prime**: for consecutive integers, the digit sum modulo $p$ increases by `+1` at every non-carry step and drops suddenly when a run of `9`s carries. Determining that “every digit sum in an interval of fixed length is not divisible by $p$” is equivalent to avoiding intervals in which the digit sum reaches a multiple of $p$.

### Examination Notes

- In digit-operation problems, first specify legal digit-deletion rules (deleting the leading digit may not create a leading zero); the “`+1` increase and carry drop” pattern of digit sum modulo $p$ is key to locating forbidden intervals.

### Pitfalls

- Not excluding deletion of a leading digit that yields a leading zero; failing to identify carries through multiple consecutive `9`s; incorrectly treating divisibility of a product as the negation of divisibility of an individual factor.

---

## 37. Small-Scale Tabulation, Period Extrapolation, and Memoized Game Search

### Core Method

For Olympiad-level counting/game/tiling/removal/erasure problems, the **standard starting point** is not direct formula derivation but three steps:

1. **Exact small-instance solutions**: write a 10–30-line brute-force program (backtracking / memoized recursion / state-compression DP / BFS) for a truncated version with $n \le 12$, obtaining an **exact table** $f(1),f(2),\dots$.
2. **Find patterns**: observe periods in the table (difference sequences often cycle modulo $m$, such as a tiling game $f(N)=q+g(r)$ with $N=7q+r$), binary structure (popcount, `2`-adic valuation), and agreement with known sequences ($C(2k,k)^2$, Catalan, Fibonacci).
3. **Recheck at medium scale, then extrapolate**: compare an inferred formula with two or three exact medium-size values outside the tabulation range; only after agreement substitute the target scale ($n=1997,2020,2025$, etc.).

### Key Points for a Memoized Game-Search Template

- For states, prioritize “minimum sufficient hashable information” (`frozenset`, `tuple`, bitmask); alternate min–max layers for first/second player; use `functools.lru_cache` or dictionary memoization.
- When the state space is too large, seek an **invariant**: popcount of the binary expansion of a sum, modulo-$p$ color count, parity, or a monotone potential function—the resulting bound is often the answer.
- In three-valued games (draw/forced win/forced loss), distinguish the recurrence for “can win” from that for “can at least avoid losing.”

### Examination Notes

- Large parameters (`2020`, `2025`) almost always signal “small-scale tabulation + periodic/formula extrapolation”; direct large-scale hand calculation is inevitably exhausting.
- Tabulation must cover at least **two complete periods** before asserting periodicity; a pattern derived from only half a period is unreliable.

### Pitfalls

- **Assuming a structure and then proving it to oneself**: assert a priori that “every column must be completed” or “the construction must align with the grid,” then use code to verify that weakened model. A successful program only shows self-consistency of the wrong model; brute force must face the **original rules**.
- Miscounting a small example by hand (missing rotated configurations or symmetric branches): small cases must be enumerated by an independent brute-force program, not manual counting.
- Confusing quotient and remainder in periodic extrapolation (`N=qm+r`, including the range of `r`).

---

## 38. Closing the Upper/Lower-Bound Loop for Extremal Constructions and Comparing Competing Constructions

### Core Method

For a problem asking for a “maximum/minimum/optimum,” **self-consistency verification within one construction family is not a proof of optimality**. The complete loop has four pieces:

1. **Construction A**: give a feasible construction and calculate its target value $v_A$ exactly.
2. **Competing construction B**: use a **structurally different** construction (divide-and-conquer versus greedy, uniform versus nonuniform spacing, aligned versus rotated), calculate $v_B$, compare it with $v_A$, and retain the better one.
3. **Exact small-scale optimum**: brute-force the full space for a truncated version with $n \le 6$, obtaining the true optimum and calibrating whether the construction is optimal.
4. **Bound argument**: prove an upper bound equal to the optimum construction's value for a maximization problem, or a lower bound equal to it for a minimization problem. The proof closes only when both ends meet.

### Examination Notes

- A greedy/lexicographic construction being “stepwise optimal” does not mean globally optimal: scheduling problems often require **recursive divide and conquer** (split `n` people into two equal groups, recurse within groups, then interleave cross-group matches) to shorten individual attendance intervals.
- For digit-construction problems, do not optimize only within one pattern family (such as the all-`9` family $10^n-1$); finer constructions with nonuniform spacing and carry filling can improve further.
- When the answer is a function of a parameter ($T(m)$ or $f(n)$), **a special-case value is not the answer**: provide a general expression in the parameter and verify it agrees with special cases.

### Pitfalls

- Treating “closed form agrees with one's own simulation” as “construction is optimal” (circular reasoning); verification must introduce an **external comparison** (a competing construction or exact small-scale optimum).
- An upper-bound pigeonhole/counting argument omits a larger extremal configuration (the family of deadlock configurations is not characterized completely).
- Confusing “guaranteed at least” (worst case) with “there exists a construction attaining” (best case).

---

## 39. Enumerating All Solutions and Exceptional Branches

### Core Method

When a problem asks for “**all** possible values / all functions / all configurations,” the solution set commonly consists of a **trivial branch + exceptional branches**; giving only the trivial branch loses all credit for missing solutions:

1. **Truncated enumeration**: restrict to small scale (the first $n \le 30$ terms of a sequence, or a truncated function domain) and use backtracking/constraint propagation to enumerate **every** object satisfying the constraints, branch by branch.
2. **Classify branches**: group enumerated solutions by structure (identity branch, pulse branch, periodic branch, etc.) and infer a general form for each branch.
3. **Close the proof**: prove that no branches other than those listed exist (usually by an invariant or extremal principle).

### Examination Notes

- Solutions of a functional equation $a=F(F(a))$ (involution/quadratic iteration) are = **fixed points of $F$ ∪ 2-cycles of $F$**. Search both classes; checking only self-conjugate solutions misses paired inverse solutions.
- For a functional equation on an integer sequence, first prove an inequality skeleton (such as $a_n \ge n+1$), then classify the deviation $b_n=a_n-(n+1)$—an exceptional branch is often pulse-shaped, with exactly one position taking a special value.
- When counting `n` satisfying a property, verify small values one by one: characterizations involving parity or being a square can hold only for one parity class (for example, exotic numbers = **odd** perfect squares, while even squares must be individually ruled out).

### Pitfalls

- A symbolic ansatz (linear undetermined form $a_n=cn+d$) structurally cannot find pulse-like exceptional branches; brute-force enumeration must come before identifying a form.
- For “find all,” answering only one branch, or writing a union of two branches as an interval/single value.
- Failing to list every final branch explicitly (write a set such as $\{2026,2030\}$ or “exactly all ...”).

## Verification Knowledge-Point Mapping

Sections 22–36 are covered item by item by the prompt-style knowledge points in `Discrete Mathematics Verification Examples.py` in the same directory. The prompts list only reproducible invariants; numerical examples cannot replace a general proof:

| Handbook topic | Prompt verification focus | Minimum verification contract |
|---|---|---|
| 22 Lattice points and regular hexagons | Lattice coordinates and symmetry orbits | Axial-coordinate side length, symmetry centers, and rotation orbits |
| 23 Extremal line covering | Incidence and double counting | General-position intersection count and two-line incidence |
| 24 Area bisectors | Affine area invariant | Triangle-area interpolation and unique landing point |
| 25 Congruent dissection/tangency | Dissection and tangency criteria | `n−2` triangles, SSS congruence, and tangent-segment conditions |
| 26 Collinear angle multiples | Ray order | Unique ray intersection and angle multiples |
| 27 Polyhedron visibility | Convexity and outward normals | Dot-product separation of outward normals and per-face hiding |
| 28 Mutual inversion of frequency vectors | Partition conjugation | Involutivity and size preservation |
| 29 Latin squares/combinatorial design | Row and column permutations | Row/column permutations and row-count upper bound |
| 30 Tournament scheduling | Coverage and cost | Every player pair meets exactly once and attendance cost |
| 31 Max-plus closure | Operations and semilattice laws | Semilattice laws of join and compatibility with translation |
| 32 Translation-invariant total orders | Order-preserving invariants | Translation-order preservation and parity of ranks in finite boxes |
| 33 Rich sets | Polynomial closure | Linear-polynomial division closure and signed binary expansion |
| 34 Discriminant Diophantine equations | Discriminant substitution | Square discriminant, substitution verification, and exclusion of false roots |
| 35 Digit structure in large-number division | Digits and carries | Multiplication back-substitution, digit decomposition, and zero-digit count |
| 36 Digit operations and divisibility | Modular invariant | Digit-deletion divisibility chains and alternating sum modulo `11` |

<!-- AUTO-KNOWLEDGE-BEGIN Subject Knowledge Quick Reference (generated section; abstract problem-solving methodology by subject, containing no particular problem) -->

The following quick-reference entries organize problem-type methodology by subject (core content / solution route / pitfalls). They are intended as methodological references for matched problems; no entry contains a concrete problem statement or conclusion, and any final answer must still be derived and verified independently.

## Quick Reference: Block Decomposition and State-Transition Matrices for Hamilton Paths

- Retrieval terms: grid, cell, board, count, counting, number of ways, sequence, matrix, matrices, parity, odd, even, interval, symmetric, symmetry, transition, state, visits exactly once, moves, ordered pairs.
- Core content: when counting Hamilton paths on a small rectangular grid that satisfy prescribed edge-move rules (adjacent moves in a row or alternating jumps between columns), first decompose a path by “number of visits/cell blocks per column”: the points in each column are divided into consecutive interval blocks, and the number of blocks corresponds to the number of visits. Then use a state-transition matrix to describe legal connections of blocks in adjacent columns (parity of block-height sequences and endpoint constraints), multiply the matrix column by column, and finally include starting-point symmetry.
- Solution route: first enumerate visit counts; use the “height of the column containing the endpoint” and parity constraints to exclude infeasible counts; construct recurrences for each feasible count and sum; do not forget the symmetry factor for the starting column.
- Pitfalls: omitting restrictions imposed by the endpoint column on visit count; confusing the visiting order within a block with transitions between visits; mishandling boundaries of block-height sequences (such as fixed heights in the first and last columns).
- Step-by-step finish: first use exact state-compression DP at small scale for calibration, then branch by visit count. Exclude infeasible counts using endpoint-column height and parity; counts in each branch often take the form of a sum of a power of `2` and one less than a power of `2` (`2^k+(2^k−1)`); finally multiply by the starting-point symmetry factor (number of columns). For a 3-row × `m`-column cylinder/band, calibrate first at `m=2,4,6` (example values `2,12,42`), fit the closed form `m·(2^{m/2}−1)`, then substitute the problem scale and report the numerical value (the answer is a five-digit-scale integer; do not report intermediate lemmas classified by row parity). Full brute-force DFS for `≥60` vertices is infeasible within the time limit: code must fit at small scale and extrapolate, and must actually invoke the main function to print its result. Do not assume a structure and then prove it to oneself.

## Quick Reference: Classification of Functional-Equation Solutions and Fixed-Point Value Ranges

- Retrieval terms: functional equation, inequality, upper bound, nice, non-negative, itself.
- Core content: for integer-valued function families defined by global conditions (nested-index identities or inequalities containing function composition), substitute special values and use induction to establish structural properties (monotonicity, linear upper bounds, at most one exceptional index). Divide all solutions into a “trivial solution + a small number of special solutions,” verify each class by substitution, and thereby determine all feasible values of the function at a fixed argument.
- Solution route: first assign special values to some variables to extract constraints; prove that every solution has a simple structure before classification; explicitly construct a solution satisfying the conditions for every candidate value.
- Pitfalls: incomplete classification (missing special solutions); proving only necessity but not sufficiency; ignoring boundaries supplied by the value range (positive/nonnegative integers).
- Step-by-step finish: for an iterative equation, first prove $a_n\ge n+1$, set $b_p=a_p-(p+1)\ge0$ and simplify; classify solutions into a “trivial branch” and a “special-index branch.” For all possible values, list both branches (a two-value set). For range-characterization problems, prove monotonicity plus upper bound $C(n)\le n+1$, then for every $k$ construct the piecewise function $C_k(n)=\max(1,n-N+k)$, giving the full range $\{1,\ldots,N+1\}$—the upper endpoint is `N+1`, not `N` (the top-bound construction $C(n)=n+1$ is legal). When all possible values are requested, find the special-index branch by truncated brute-force backtracking for `n≤30`; reporting only the trivial branch loses credit for missing solutions.

## Quick Reference: Transitive Arguments from Ordering Monotonicity and the Triangle Inequality

- Retrieval terms: inequality, permutation, sequence, triangle, triangles, pairing, pairs, sorting, rearrange.
- Core content: after sorting several triples of side lengths in nonincreasing order and pairing them coordinatewise, use the triangle inequality within the original triples and ordering monotonicity to prove that the paired triple is still a triangle: any side is less than the sum of the other two sides in its original triple, and those other two sides are no greater than the corresponding paired sides. This proves that the leading paired sequence is necessarily legal.
- Solution route: first prove the leading pair is always legal, obtaining the structural conclusion that an illegal position can only occur in the tail; then give an extremal construction making every tail position illegal to prove tightness.
- Pitfalls: mismatching descending order with inequality direction; failing to keep all original-triple triangle inequalities valid while constructing an illegal tail.

## Quick Reference: Pigeonhole Principle in Integer Extremal Problems

- Retrieval terms: coprime, relatively, gcd, extremal, maximum, minimum, optimal, subset, pigeonhole, construction, interval, minimal sums, prefix sums, subset sums.
- Core content: for approximation and clustering extremal problems on integer arrays, classify objects by residues modulo a chosen number (prefix-sum residue classes, multiples/coprime classes) and use the pigeonhole principle to force enough elements into one class, thereby obtaining the needed structure: prove either that a subset sum lies in a prescribed interval or that no three elements are pairwise coprime. Then prove tightness by explicit construction.
- Solution route: choose a modulus tied to the target's special residue structure; “the union of multiples of `2` and multiples of `3`” is a standard construction for coprimality constraints; represent subset sums as differences of prefix sums.
- Pitfalls: a poor modulus makes the pigeonhole conclusion too weak; in coprimality problems, omitting discussion of elements coprime to both `2` and `3`; incorrect inclusion of interval endpoints.
- Step-by-step finish: for subset-sum approximation, close both upper and lower bounds—put `n+1` prefix sums into boxes modulo `d` to obtain a same-box difference for the upper bound (combined with an element upper bound), and for the lower bound use a mixed sequence of a few adjacent boundary values `m−1` and many `m` values to calculate the exact gap to the nearest subset sum. Choose `d` where the two sides close, calibrate at small scale, and never guess from one side only. For a coprime-triple extremum, the maximum construction is multiples of `2` ∪ multiples of `3`, with count $\lfloor(a+2)/2\rfloor+\lfloor(a+2)/3\rfloor-\lfloor(a+2)/6\rfloor$.

## Quick Reference: Polynomial Identities and Mutual Inversion of Frequency Vectors (Partition Conjugation)

- Retrieval terms: polynomial, coefficient, product, partition, conjugate, root, cycle, ring, vector, frequency, multiplicity, weighted, occurrences, counts, appears, good, called.
- Core content: an identity between two polynomial products translates into “the frequency vector of the roots of one is the multiplicity vector of the other,” a fixed point under self-composition of the frequency map. The frequency map on integer partitions is partition conjugation; fixed points (self-conjugate partitions) and 2-cycles give the complete solution structure, and yield possible values of the target weighted sum.
- Solution route: rewrite the identity as a system of frequency equations; recognize frequency map = partition conjugation; enumerate “self-conjugate / paired-cycle” classes and compute weighted values separately.
- Pitfalls: omitting paired-cycle classes; writing a conjugate partition incorrectly; mismatching weighted calculations and partition structure.
- Step-by-step finish: the condition says that `a` is a period-`≤2` point of $F$, where $F$ is the frequency/conjugation map. The solution set = fixed points (self-conjugate) ∪ 2-cycles, and both branches must be searched. A self-conjugate branch has the form $a_1=n-4, a_2=2, a_3=1, a_{n-4}=1$; there are two additional 2-cycle groups. List the target values from every branch as a set in the final answer; reporting one branch necessarily loses credit.

## Quick Reference: Constrained Domino-Tiling Counts and Forced Uniqueness

- Retrieval terms: board, chessboard, squares, covering, domino, count, number of ways, combination, binomial, flip, swap, reverse, cycle, ring.
- Core content: for domino placements on a board with constraints (in every small square group, uncovered cells satisfy a same-row/same-column condition), the uncovered-cell set corresponds to a “row-and-column selection” structure (select some rows and columns, and their intersections are the uncovered cells), so counting reduces to binomial coefficients. To force a unique tiling with marked cells, marks destroy every flippable alternating cycle; the required number of marks has the same order as the board side length.
- Solution route: translate the constraint into shape features of the uncovered-cell set; uniqueness arguments center on “flippable cycles of a tiling”; use small-scale verification and the general formula to check one another.
- Pitfalls: omitting a direction in the equivalence between the constraint and a “diagonally uncovered” pattern; claiming uniqueness while not all flip cycles are destroyed; failing to investigate disagreement between small-scale enumeration and the formula.
- Step-by-step finish: uncovered cells = intersections of selected `k` rows × `k` columns $\Rightarrow$ count of the form $C(2k,k)^2$ (a squared binomial coefficient); calibrate using brute-force values `4,36` at `k=1,2`; report the binomial expression or its numerical value, not a linear expression of form `2(k+1)`.

## Quick Reference: Linear Separation of Two-Colored Point Sets

- Retrieval terms: minimum, smallest, least, line, points, plane, configuration, construction, upper bound, lower bound, marked, sorting, rearrange.
- Core content: use lines passing through no marked point to partition the plane into regions, each containing points of only one color. The minimum number of lines that works for every red/blue point configuration equals the size of the smaller color class. For the upper bound, sort projections in a direction and draw a line at every adjacent color change; for the lower bound, use a narrow strip with alternating red and blue points, so every color change forces a line.
- Solution route: a lower-bound construction requires strict alternation of the two colors; the upper bound need only separate each adjacent differently colored pair.
- Pitfalls: a line passing through a marked point; an incomplete proof of the equivalence between “no region has both colors” and “separate adjacent differently colored pairs.”
- Step-by-step finish: answer = `min(|red|,|blue|)`; for the upper bound sort projections and draw lines between adjacent color changes; for the lower bound use the alternating red-blue narrow-strip construction. When this conflicts with a rough region count, trust the lower bound supplied by the alternating construction.

## Quick Reference: Extremal Arguments for Row/Column Degree Constraints and Poset Structure

- Retrieval terms: inequality, extremal, maximum, minimum, count, product, sequence, pigeonhole, matrix, rows, columns, degrees, interval, chain, antichain, crossing, connected, monotone.
- Core content: one class of problems writes constraints as uniqueness of row-count/column-count pairings and feasibility of degree sequences (Gale–Ryser-type dual inequalities). First obtain linear constraints from pairing uniqueness, then tighten them to an exact extremum and prove attainability by explicit construction. Another class arranges objects in a matrix and uses poset chains plus pigeonhole to force a “crossing structure” (the threshold is on the order of row-size × column-size plus one).
- Solution route: first write relations between row and column counting statistics; once the monotone direction of the poset is fixed, use “same-order common multiples” to construct critical counterexamples and positive examples.
- Pitfalls: treating “there exist two rows each of degree `m`” as every row having degree exactly `m`; omitting the increasing/decreasing direction of the partial order and thereby invalidating pigeonhole; reversing a dual inequality.
- Step-by-step finish: “two rows both have degree `m` $\Rightarrow$ their column-sum sets are disjoint $\Rightarrow 2m\le n$” is only the first constraint. Add a compressed-matrix inequality (of the form $a\cdot n_a\le n$) to tighten to the scale `m=n/2−4`, and give an explicit construction (remaining row degrees traverse remaining values). For a two-interval family of total size $t^2$, the connectivity threshold is $t(t−1)+1$; report product plus one, not `t` itself.

## Quick Reference: Binary Invariants—Popcount Conservation and Merging Powers

- Retrieval terms: binary, bits, power, exponent, erase, rewrite, merge, combine, game, players, invariant, strategy, blackboard, copies, rounds, writes.
- Core content: invariants in numerical games are often hidden in binary representation. In merging processes (at each move take equal amounts from two heaps and merge them into a new heap), when the total is not a power of `2`, at least two nonempty heaps remain, corresponding to a decomposition into powers. In erasing/merging games, the number of objects remaining at termination equals the number of `1`s in the binary representation of the initial total (an invariant under optimal play).
- Solution route: first analyze binary features of the initial total (popcount, whether it is a power of `2`), then prove that each move preserves the feature.
- Pitfalls: a merge requires equal amounts from both heaps; in a partial merge, the remaining structure differs; a proof connecting popcount of the sum and remaining-object count must cover optimal strategies of both players.
- Step-by-step finish: in the game with `N` copies of `1` where two numbers are erased and their sum written, the guaranteed value is `popcount(N)` (for example, $N=1997\to11111001101\to8$). One player maintains that binary representations of all numbers have pairwise disjoint `1` bits, while the other pairs and merges by power sums. First calculate `popcount` to obtain the candidate, then close the proof with strategies for both sides.

## Quick Reference: Density Guarantees and Expansion Fronts in Grid Growth Processes

- Retrieval terms: grid, cell, board, chessboard, squares, area, lattice, potential function, density, front, frontier, expansion, spread, growth, green, coloured cells, turn.
- Core content: when one player adds to local neighborhoods each round while the other globally removes a bounded amount each round, use a potential based on “net increase divided by affected area” to prove a guaranteed density lower bound. For diffusion growth, use “expansion-front width” to decide sparsity: if the front maintains two-dimensional expansion (width reaches a fixed proportion of the board side), growth is quadratic; otherwise it is trapped in a one-dimensional strip.
- Solution route: take the potential as “amount this round can increase − amount the opponent can remove”; the sparse threshold comes from converting the minimum width needed for a two-dimensional front against the board side length.
- Pitfalls: treating a per-round limit as a total limit; effects of boundary neighborhoods (corners and edges); incorrect conversion between front width and number of rounds.
- Step-by-step finish: sparse threshold = the critical initial amount needed to sustain a two-dimensional front: $s=(\text{side length})^2-(\lfloor\text{side length}/2\rfloor+1)^2$ (for example, $75^2-38^2=4181$). Below it, growth is trapped in a one-dimensional strip (`O(n)`); at it, $\Omega(n^2)$ growth can be sustained. The requested “minimum nonsparse `s`” is the threshold itself, not one below it.

## Quick Reference: Recurrence Counting on Path Structures

- Retrieval terms: board, chessboard, squares, polynomial, coefficient, count, number of ways, sequence, recurrence, recursive, independent set, path.
- Core content: count increasing-value sequences or independent sets on a path/board with recurrences. The independent-set polynomial along path vertices satisfies a first-order linear recurrence: split by not selecting/selecting the current vertex, and if it is selected its predecessor cannot be. For board-path counting, fill values in a snake/spiral so each cell has at most one incoming and one outgoing edge, turning the count into a source-count problem in a directed acyclic graph (local minima).
- Solution route: write recurrence initial values explicitly (empty graph and one-vertex cases); the filling construction should make the number of local-minimum starts attain the theoretical lower bound.
- Pitfalls: omitting the restriction “select current vertex, so predecessor cannot be selected” in independent-set recurrence; forgetting row/column parity conditions for local-minimum starts; boundary cells have fewer neighbors than interior cells.
- Step-by-step finish: snake/spiral filling makes good path starts be local minima at even-even positions, with optimum count $\lceil n/2\rceil^2+\lfloor n/2\rfloor^2$ (for example, $78^2+77^2=12013$); prove the lower bound by counting DAG sources, and state initial values for the first-order independent-set recurrence.

## Quick Reference: Arithmetic/Harmonic Mean Operations and Linear-Fractional Transformations

- Retrieval terms: coprime, gcd, harmonic mean, arithmetic average, construction, powers, exponent, positive integers, invariant, odd part.
- Core content: starting from a reciprocal pair generated by two coprime positive integers, repeatedly apply arithmetic and harmonic means and determine whether `1` can be generated in finitely many steps. The necessary and sufficient condition is: both integers are odd and their sum is a power of `2`. The central tool is the linear-fractional transform $s=(x-1)/(x+1)$, which simultaneously converts arithmetic and harmonic means into rational-function operations and reveals an invariant: the “odd part” of the reduced denominator of every reachable value remains unchanged. Target value `1` corresponds to $s=0$, so reachability requires the initial denominator of $s$ to be a power of `2`, equivalently the two-number sum is a power of `2`. Sufficiency is constructed by iterative averaging; necessity follows from the odd-part invariant.
- Solution route: for problems of “generate a target by arithmetic/harmonic means (or general linear-fractional operations),” first seek a transformation that diagonalizes or linearizes the operation, then find an invariant. “Maximum feasible sum” and “minimum unreachable” problems commonly reduce to scanning powers of `2`.
- Pitfalls: verifying only a sufficient construction without necessity; forgetting the invariant that the odd part remains unchanged after reduction; omitting the condition that both integers are odd; misusing coprimality and invalidating reduction conclusions.
- Step-by-step finish: once “both numbers odd and `m+n` a power of `2`” is proved, finish the requested extremum within the stated range. For example, below `3000`, the largest sum is $2^{11}=2048$; give $(m,n)=(2^k+1,2^k-1)$ and an explicit iterative path to verify reachability.

## Quick Reference: Weight-Function Invariants and Lower Bounds from Worst-Case Distributions

- Retrieval terms: grid, cell, board, minimum, product, sequence, lower bound, powers, exponent, merge, combine.
- Core content: move pieces toward the origin of a three-dimensional grid by merging prescribed distinct numbers of pieces along each of the three coordinate directions into one piece and moving it one step in the negative direction. Define a weight at each point as the reciprocal of the product of powers of the merging arities (increasing a coordinate by `1` divides weight by the corresponding arity). Then every operation preserves total weight. A single piece at the origin has weight `1`, so the initial total weight must be at least `1`; the worst distribution puts all pieces at the farthest grid corner, yielding the exact lower bound on the minimum total number required for guaranteed reachability, and a greedy transport sequence attains it.
- Solution route: weight functions apply to processes that merge by different arities while moving toward a fixed point. When arities are pairwise coprime integers, a product-of-powers weight naturally makes operations conserved. Split the argument into necessity (weight invariant) and sufficiency (reachable construction).
- Pitfalls: failing to identify the worst distribution (it is the farthest corner from the origin); choosing a nonconserved weight; proving only the lower bound without reachability, or constructing without proving optimality.

## Quick Reference: Partition Structure for lcm and gcd

- Retrieval terms: lcm, least common multiple, gcd, greatest divisor, maximum, minimum, sequence, recurrence, construction.
- Core content: split a strictly increasing positive integer sequence by position into a prefix and suffix. A split is *good* if the lcm of all prefix elements equals the gcd of all suffix elements. A local-structure lemma says that no three consecutive split positions can all be good: if positions $k,k+1,k+2$ were all good, adjacent sequence terms would be equal, contradicting strict increase (two consecutive good splits can occur). Thus among every three consecutive split positions at most two are good, giving a density upper bound of two thirds; the refined maximum good-split count is approximately two thirds of the total number of split positions. To find the shortest length having exactly a given number of good splits, derive a length lower bound from this density and then use an explicit lcm-based recurrence to construct an increasing sequence attaining the count.
- Solution route: for lcm/gcd equality split problems, first prove the local lemma (among three consecutive positions, at most two good), then count globally. “Exactly a given number” answers usually occur at the rounded density bound.
- Pitfalls: confusing directions of lcm and gcd (prefix lcm, suffix gcd); ignoring endpoint effects and causing count errors; failing to preserve strict increase in a constructed sequence.

## Quick Reference: Applications of Fibonacci and Lucas Identities

- Retrieval terms: covering, minimum, interval.
- Core content: find the smallest integer set whose pairwise differences cover all Fibonacci-number differences in a prescribed index interval (together with a Lucas-number difference). The key identity is that the difference between two adjacent even-index Fibonacci numbers is the intervening odd-index term: $F_{2k}-F_{2k-2}=F_{2k-1}$. Therefore include `0` and all even-index Fibonacci numbers; differences of adjacent elements cover all target terms. A Lucas number can also be written as a difference of two Fibonacci numbers. Minimality follows because endpoint terms can only be represented by differences of adjacent even-index terms; after removing an outermost element, the endpoint difference is not representable.
- Solution route: in Fibonacci/Lucas problems first list identities tied to index parity. A “differences of selected set elements cover a target set” problem becomes choosing generators so that a difference graph is connected; prove minimality by nonreplaceability of endpoints.
- Pitfalls: forgetting the adjacent-even-index difference identity; including odd-index terms and making the set unnecessarily large; proving minimality only by counting rather than nonrepresentability.

## Quick Reference: Binary Representations, 2-Adic Valuations, and Frobenius-Type Nonrepresentable Numbers

- Retrieval terms: covering, divisibility, gcd, maximum, combination, binary, bits, power, exponent, factorization, odd part.
- Core content: two main threads around power-of-`2` structure. (a) For a generating set of `n` differences of powers of `2` (each has a binary pattern of a contiguous block of `1`s followed by a block of `0`s, with total bit length exactly `n`), study the range of integers covered by nonnegative linear combinations with repetition allowed. The largest generator is $2^n-1$ and the gcd is `1`, so every sufficiently large integer is representable. The greatest nonrepresentable integer has the form “linear factor × power of `2` + `1`”; the proof depends on carry structure in binary addition, because each generator contributes a consecutive-`1` pattern and superposition/carry interactions determine the representability boundary. (b) The odd-part function $f(n)=n/2^m$, where $m$ is the exponent of the power of `2` dividing `n`, is always odd. Its residue modulo a fixed number is determined by the `2`-divisibility depth of `n`: for odd `n` it is `n` itself; otherwise repeatedly divide by `2` before reducing. Requiring differences of values at consecutive positions in an interval to be multiples of a fixed modulus is equivalent to periodic behavior of $f$ modulo that number. When the period length itself has a power-of-`2` factor, it conflicts with deeper 2-adic structure; refined analysis compresses feasible parameters to a very small candidate set.
- Solution route: for Frobenius-number problems whose generators have regular binary patterns, perform carry/pattern analysis then induction, checking a formula at small `n`. For $v_2$-type functions, write values in layers by 2-divisibility depth, then translate periodic/divisibility conditions into depth constraints.
- Pitfalls: directly applying the classical two-generator Frobenius formula; ignoring repetition and binary carries; mishandling carry boundaries in induction; omitting layers or confusing moduli when splitting $f$ by `2`-divisibility depth; incomplete boundary analysis of conflicts between period length and 2-adic depth.
- Step-by-step finish: for consecutive-`1` generators, induct on carry structure to find the greatest nonrepresentable number (linear factor × power of `2` + `1`) and verify at small `n`. For periodic odd part modulo `m`, write $f$ by $v_2$ layers; the obstruction occurs at $v_2(n)=\log_2 v-1$. After layer-by-layer exclusion, feasible parameters remain a small set (of form `{1,3,5}`); answer with the set and verify each candidate.

## Quick Reference: Diophantine Equations and Discriminant Parameterization

- Retrieval terms: divisibility, polynomial, coefficient, parity, construction, positive integers, discriminant, perfect square.
- Core content: parameterized Diophantine equations are commonly solved by making the equation quadratic in one variable and requiring its discriminant to be a perfect square. If the discriminant can be arranged as a square of a polynomial, one directly obtains a parametric family of solutions, with parameter ranging over positive integers (construction and substitution verification are both indispensable). If only parity of the number of solutions is needed, convert the square-discriminant constraint into a quadratic-form/norm equation (representation numbers in an imaginary quadratic field); parity of the count is determined by the corresponding divisibility condition. The common structure is: first use discriminant nonnegativity to bound variable range or parameter-family shape, then refine by the perfect-square condition.
- Solution route: for equations with radicals, move terms and eliminate radicals to obtain a one-variable quadratic before taking the discriminant. For parity of ordered integer-solution counts, preferentially convert to parity of quadratic-form representation numbers rather than enumerating points. Symmetric structures (for example, two variables of the same degree) can first be paired and simplified.
- Pitfalls: failing to verify parameterization by substitution and thereby admitting extraneous solutions; overlooking bounds from nonnegative discriminant and letting enumeration/derivation range out of control; oversimplifying a claim that a solution count is even without a norm equation.

## Quick Reference: Classification of Functions under Divisibility Constraints

- Retrieval terms: divisibility, product, parity, powers, factors, positive integers, perfect square, mirror, pairing, functions, difference, power functions, ranking.
- Core content: if an integer-valued function $g$ satisfies “for any distinct integers $a,b$, the value difference divides the corresponding difference of powers,” then all solutions have power-function-family forms: $g$ is an $x^d$ power function, with $d$ ranging over divisors of a given positive integer, or a mirror/translation variant. When exponent and power satisfy particular parity conditions, additional signed solution families occur. The total number of such functions is: if the exponent contains no power-of-`2` factor, twice the number of divisors; if it contains a power-of-`2` factor (the exponent is a product of its 2-adic part and odd part), twice (twice the 2-adic exponent) times the divisor count of the odd part. The condition “the number of functions is `2` times an odd number” is equivalent to an odd divisor count, hence to the positive integer being a perfect square; combine this with parity restrictions to locate the integer at a specified rank.
- Solution route: for divisibility function equations, first conjecture standard solution families (power functions and variants), then analyze branches introduced by parity. For “the `N`-th positive integer satisfying a property,” first establish a counting formula and then invert the rank.
- Pitfalls: omitting additional signed families; confusing “`2` × odd” with merely “even” and ignoring modulo-`4` structure; incorrectly testing parity of divisor counts (perfect squares).
- Step-by-step finish: count = `2×odd` $\Leftrightarrow$ divisor count is odd $\Leftrightarrow$ perfect square. With parity constraints, this often becomes “odd perfect squares.” For “the `N`-th,” write an explicit general term: the `N`-th odd square is $(2N-1)^2$ (check `N=1,2,3` gives `1,9,25`), then substitute the rank; never use $N^2$ directly.

## Quick Reference: Techniques for Primes and Coprimality

- Retrieval terms: primes, divisibility, coprime, gcd, digits, count, sequence, recurrence, representation, smallest, norm, absolute.
- Core content: two common threads. (a) For coprime integers $k,l$, a coefficient-norm function of the form “minimum $|a|+|b|$ subject to $ka+lb=x$” describes shortest representations of integers by a generating pair. The count of “nice” integers satisfying a local-maximum condition depends only on the smaller parameter and parity of $k,l$; the both-odd and one-even cases give count formulas differing by a factor, derived from symmetry. (b) To prove that every prime divides some term of a linear recurrence, first find its closed form (homogeneous solution plus particular solution, reduced to a sum of powers plus a constant), then use Fermat's little theorem and modular periodicity to choose an index at which each prime divides the required term.
- Solution route: to show a number coprime to all terms, it suffices to handle its prime factors; for every prime use modular reasoning to prove a divisible term exists. In coprime-linear-combination problems, study coefficient norm instead of solving the equation directly.
- Pitfalls: errors in constant terms or coefficients of recurrence closed forms; testing only several small primes and asserting a general result; confusing “every prime divides some term” with “one prime divides every term”; merging parity cases and getting the count ratio wrong.
- Step-by-step finish: for the norm equation, reduce to an imaginary-quadratic-field norm form $(\alpha y-\beta d)^2+\gamma t^2=\delta d^2$; parity of the solution count follows from a divisibility condition (of form `14|d`). Counts often simplify to $F=l-1$, $G=2(l-1)$, giving a target expression of form $p^2+q^2=5(l-1)^2$ for `l`.

## Quick Reference: Decimal Digit Operations and Divisibility

- Retrieval terms: primes, divisibility, digits, decimal, maximum, construction, interval, carry, length.
- Core content: (a) Numbers with distinct digits such that “the number obtained after deleting one digit is a divisor of the original number” (deletion creates no leading zero, and the resulting number still has the original property) can be constructed digit by digit from one-digit seeds. The largest is verified by an explicit deletion chain—at every stage delete one digit (the deleted digit and position may differ at different stages) to obtain the prior number. (b) For consecutive integers, digit sum modulo a given prime increases by `+1` at non-carry steps and drops at carries through consecutive `9`s. To decide that every digit sum in a fixed-length interval is nondivisible by that prime is to avoid intervals in which digit sum lands on multiples of the prime; minimality is checked by digit-sum DP or interval scanning.
- Solution route: first specify legal digit-deletion rules (deleting a leading digit must not make a leading zero). The “`+1` increase / run-of-`9`s carry drop” pattern is key to locating forbidden intervals. “A product is not divisible” should first be reduced to every factor being nondivisible.
- Pitfalls: not excluding leading-zero results after deleting the first digit; failing to identify carries through multiple `9`s; incorrectly taking divisibility of a product as negation of divisibility of one factor; an error in digit distinctness or divisibility in one link of a construction chain.
- Step-by-step finish: for digit-deletion divisible good numbers, expand from one-digit seeds (the new number is an integer multiple of the old and deleting one digit restores it); verify the maximum ring by ring with an explicit deletion chain (divisibility + distinct digits), and write Python as an expansion search rather than a closed-form guess. For digit-sum divisibility intervals, scan forbidden zones modulo $p$ using the “`+1` increase, consecutive-`9` drop” behavior.

## Quick Reference: Floor Inequalities and Complete Residue Systems

- Retrieval terms: primes, modulo, floor, inequality, permutation, sequence, upper bound, residue, complete system, quotient, remainder.
- Core content: problems involving an inequality for every residue class are commonly transformed by rewriting the traversal index from $1$ to $p-1$ and using the complete-residue-system property modulo prime $p$: after setting $j=k+1$, residues of $n\cdot j\pmod p$ still traverse all nonzero residues. Rewrite the original inequality as a lower bound on the residue for every $j$, equivalently as a uniform upper bound on a quotient floor. All valid `n` are then the decreasing sequence of floors obtained by dividing `p` by consecutive integers; the target rank is its position in that floor sequence.
- Solution route: interchange index traversal and complete-residue rearrangement; use residue = original number − modulus × floor to rewrite thresholds. For “the `k`-th largest,” list the complete solution sequence before locating the term.
- Pitfalls: forgetting the premise `n<p` needed for multiplication by `n` to form a complete system; reversing an inequality sign while rewriting residues; miscounting duplicates in the floor sequence.
- Step-by-step finish: reduce to a complete-residue traversal $r=nj\pmod p$; valid `n` form the decreasing sequence $\lfloor p/j\rfloor$ for `j=1,2,3,\ldots`, hence the `k`-th largest is **$\lfloor p/k\rfloor$**. Explicitly check `k=1,2` by writing the two largest values before applying the formula. Answering $\lfloor p/(k+1)\rfloor$ is the common one-position error.

## Quick Reference: Digit Structure in Large-Number Division

- Retrieval terms: covering, digits, decimal, inequality, maximum, product, distribution, carry, length.
- Core content: for long division of a fixed-length dividend containing no zero digit, let the quotient have `L` digits and `t` nonzero digits and the divisor have `d` digits. View multiplication as shifted superposition of copies of “each nonzero quotient digit × divisor.” These copies must cover every dividend digit without producing a zero digit, yielding a coverage inequality between `t·d` and dividend length. Maximizing zero digits of the quotient (`L−t`) is discrete optimization under digit budget: overly large `L` leaves each copy unable to cover enough; overly small `L` wastes digit capacity. At optimum, nonzero digits are approximately equally spaced, and one must verify whether carries can fill gaps and how the remainder repairs the final digit.
- Solution route: first establish the copy-coverage view; use digit inequalities to identify the feasible region, then optimize near integer lattice points; prove both an upper bound and a construction.
- Pitfalls: treating coverage inequality as equality; ignoring carry filling and producing a failed construction; giving a construction without optimality proof; underestimating mutual constraints between quotient and divisor digit lengths.
- Step-by-step finish: `t` nonzero quotient digits × divisor digit length `d` cover the total digits: $t\cdot d\ge L$; maximum zero digits $A=$ quotient digit count − `t`. Permit nonuniform spacing plus carry-filling constructions to attain the bound, then prove that at `A+1` every gap is too large to fill (a “939-type” conclusion).

## Quick Reference: Combinatorics—Latin Squares and Inter-Row Difference Constraints

- Retrieval terms: maximum, count, permutation, combination, binomial, difference, finite difference, Latin square, lattice, table, order.
- Core content: place permutations of `n` symbols row by row in a table, yielding “one permutation per row and distinct elements in each column,” i.e. a Latin square. Column distinctness directly bounds the maximum number of rows. An inter-row difference constraint requires that any two rows have numerical difference at least a prescribed lower bound in at least one column; equivalently it excludes row pairs that are “adjacent permutations” (coordinatewise differences all small, never reaching the threshold). At the maximum number of rows the table is an order-`n` Latin square, so counting becomes counting Latin squares satisfying the difference constraint.
- Solution route: derive the row-count upper bound from column distinctness and prove attainability; fix the first row to eliminate whole-row-permutation symmetry before counting; check compatibility between the difference constraint and cyclic Latin-square construction.
- Pitfalls: forgetting the row-count upper bound from column distinctness; treating “at least one column reaches the threshold” as if every column had to; failing to divide out row-permutation symmetry when counting.

<!-- AUTO-KNOWLEDGE-END -->

## Quick Reference: Extremal Guarantees and Constructions under Sequence-Sum Constraints

- Retrieval terms: extremal, maximum, minimum, construction, sum of squares, pairing, lattice, groups, partition, between, value range, number of variables.
- Core content: given ranges and a sum-of-squares/sum constraint, find the minimum number of variables; or, in a $\pm1$ sequence, find the largest guaranteed absolute subsequence sum subject to bounded gaps between adjacent indices. The unified method is: first bound using total quantity (sum of squares strictly less than number of variables, or grouping/pairing in fixed lengths), then give a balanced-sign explicit construction proving tightness.
- Solution route: obtain the two ends from a total-quantity estimate and an explicit construction respectively; for $\pm1$ problems, analyze each fixed-length block as the basic unit.
- Pitfalls: violating secondary constraints in a construction (such as absolute total sum less than `1`); miscounting how many elements can be selected per block under gap constraints; wrong direction of ceiling.
- Step-by-step finish: interpret “between `−1` and `1`” as the open interval by Olympiad convention: minimum count is of the `21` type (ten positive and ten negative values plus one distinct value, using a $\sqrt{0.99}$-type construction). For $\pm1$ sequences with bounded gaps, $f(n)=\lceil(n+2)/4\rceil$ (the periodic `++−−` construction plus a lower bound from blocks of four); substitute the problem size, e.g. `2022→506`.

## Quick Reference: Guaranteed Values in Two-Player Games—Target-Region Locking and Capacity Bounds

- Retrieval terms: game, strategy, player, winning move, first, second, counting, upper bound, lower bound, lattice.
- Core content: the first player locks a fixed-size target region (such as a small square or a same-color cell class) and guarantees occupying it all, giving a lower bound on score/piece count. The second player uses a capacity count—at most a certain number of cells per round—to give an upper bound. Equal bounds determine the guaranteed value.
- Solution route: the first player should choose a target distant from positions accessible to the opponent; upper bound = maximum rounds × capacity per round; account for the first player's advantage in number of rounds.
- Pitfalls: ignoring the difference in round counts caused by moving first; miscalculating opponent capacity per round; an upper-bound argument that does not cover all opponent strategies.
- Step-by-step finish: lock a distant fixed target region cell by cell; opponent capacity = maximum occupied cells per round × rounds; close when lower and upper bounds agree. For nonattacking same-color cells (knights on black squares), `t` rounds consume `2t` cells of that color, so the guarantee is half of those cells (`1200` black cells → `600`).

## Quick Reference: Guaranteed Values in Two-Player Games—Minimax DP and Modular Periodicity

- Retrieval terms: game, strategy, player, first, period, periodicity, enumeration, dynamic programming, draw, minimax, endpoints.
- Core content: complete-information placement/removal games can use state DP for minimax values. Results often obey a modular period law (every period contributes a fixed amount and the remainder uses a small table), or small-scale state enumeration plus structural features (first player taking endpoints/boundary positions can force a draw) determines draw conditions.
- Solution route: calculate small-scale DP to find periodicity, then extrapolate; for draws, note the terminal rule “all objects removed means a draw.”
- Pitfalls: shifted period starting point; not distinguishing alternating players in DP states; misclassifying a draw under optimal play as a forced win for one side.
- Step-by-step finish: memoized search at small `n` finds $f(N)=\lfloor N/p\rfloor+g(N\bmod p)$ (often small `p` such as `7`, with `g` tabulated); substitute large $N$ via $N=7q+r\Rightarrow q+g(r)$. In draw tests, preserve both the terminal “all removed = draw” rule and the structure by which a first-player endpoint move forces a draw.

## Quick Reference: Guaranteed Values in Two-Player Games—Pairing and Mirroring Strategies

- Retrieval terms: game, strategy, player, winning move, XOR, Nim, invariant, symmetry, mirror, pairing, vector.
- Core content: one player pairs objects (by XOR zero, constant pair sum, or symmetric positions) and mirrors the opponent's choice each round, maintaining an invariant (XOR sum, numerical difference, or position) away from disadvantage. Pairing feasibility and degeneracies are determined by algebraic structure (linear spaces, constant sum).
- Solution route: identify the invariant supporting pairing (global XOR zero or constant pair sum); pay special attention to degeneracy when an object pairs with itself.
- Pitfalls: a degenerate case (empty set or self-pairing) invalidates the strategy; failure to verify mirror reply is legal; verifying an invariant for one move but not for the entire game.
- Step-by-step finish: for cards in $GF(2)^m$, XOR of all cards is `0`; the first player's unique losing opening is the empty card (zero vector), and the second player mirrors using pairs $\{x,x\oplus c\}$. For numerical-pair games, pair to a constant sum, e.g. `(50,1),(49,2),…`, each summing to `51`; mirror replies maintain a difference of form `3k`, and backward induction proves both sides optimal.

## Quick Reference: P/N Positions and Binary Characterization in Combinatorial Games

- Retrieval terms: game, strategy, player, second, digits, minimum, combination, binomial, binary, bits.
- Core content: in game DP worked backward from terminal positions, winning/losing position sets often have a binary characterization: the second player wins (a losing position for the player to move) if and only if all `1` bits occur in odd-numbered positions (least significant bit numbered `0`). This criterion permits direct classification over very large ranges and direct queries for the least qualifying number.
- Solution route: first handle the boundary segment in which only a `+1` move is available beyond the halfway point, then inductively derive the complete binary criterion; construct directly from the criterion when querying.
- Pitfalls: confusing bit numbering (least significant bit is position `0`); omitting boundary cases in the range below one half, where two moves are available.

## Quick Reference: Worst-Case Analysis of Dynamic Processes on Grids

- Retrieval terms: grid, cell, board, parity, construction, upper bound, ants, collide, infection, spread, invariant, path, speed.
- Core content: analyze grid propagation/motion (infection spread, ant collision) by an invariant or equivalent model. For infection, examine parity of infection counts in local blocks; a deadlock configuration in which every block has even infection count gives an upper bound. For ants, use “collision is equivalent to passing through each other and exchanging identities”; each ant path then has at most two segments (one horizontal and one vertical), yielding latest exit time.
- Solution route: a deadlock requires every local block have infection count even (then only whole-block flips occur and total count is unchanged); latest exit time is the maximum combination of one horizontal and one vertical segment length.
- Pitfalls: assuming a flip changes total infection count; omitting a configuration where turning yields more than two segments; calculations at half-integer collision points.
- Step-by-step finish: for infection penetration, a deadlock is a maximum set in which every $2\times2$ block has infection count in $\{0,2,4\}$, of maximum size $n^2/4+n/2$ (periodic class plus boundary extra row); the minimum guaranteed infection count is $k=n^2/4+n/2+1$, calibrated at `n=2,3,4`. For ant collisions, collision = pass-through with name exchange, each path has at most one horizontal plus one vertical segment, and latest exit time is $1.5N-1$, attained by two ants colliding head-on at the middle line and turning.

## Quick Reference: Coloring-Invariant Lower Bounds for Puzzle Tilings

- Retrieval terms: coloring, board, chessboard, cover, piece, tromino, tetromino, parity, construction, lower bound, domino, rectangle, tiling, minimum.
- Core content: use periodic colorings (coordinate-sum residues or parity classes of cell coordinates) to partition a board into color classes; count each class and compute the covering capacity of every tile shape (L-shapes, corner-removed rectangles, etc.) in each class, obtaining a lower bound on tile number/count, then construct a tiling attaining it.
- Solution route: choose a coloring matched to tile shape (diagonal cells same color, arms and corner different colors, etc.); the lower bound usually comes from the scarcest color class.
- Pitfalls: a coloring pattern mismatched to tile capacity gives a loose lower bound; forgetting tile rotations/reflections; incorrect boundary-cell color class.
- Step-by-step finish: first write area equation $2d+4s=$ total area, and minimizing `d` is equivalent to maximizing `s`. Under 3-coloring by $(i+j)\bmod3$, S-shaped tiles have distributions `(0,2,2)/(2,1,1)`; color counts bound `d`, and a $2\times3$ block construction plus boundary completion attains equality. **Anti-pattern (disprove before asserting impossibility)**: if a tile has nonunique color distribution (an L-shaped tromino can cover either `2` black/`1` white or `1` black/`2` white), a target-cell count not divisible by `3` does **not** prove non-tileability. Before declaring impossibility, construct on `3×3`, `5×5`, etc.; small-scale feasibility disproves the argument. **How to obtain the lower bound**: do not use the rough “target cells ÷ maximum cells per tile” bound—it is usually not tight. Find a scarce subclass of which every tile covers at most one cell (typically cells with both coordinates odd). On an `n×n` alternating black-corner board, black cells split into $\lceil n/2\rceil^2$ and $\lfloor n/2\rfloor^2$ classes; the tight lower bound is of the $\lceil n/2\rceil^2$ type. Then give an explicit tiling attaining it. Construction and bound must meet; if construction cannot attain a rough bound, use the construction value and explain its nonattainability by boundary/parity obstruction.

## Quick Reference: Coverage and Matching Guarantees on Graphs

- Retrieval terms: cover, matching, graph, complete graph, vertex, minimum, parity, erase, delete, teams, games, matches, pairs, opposite, nonzero.
- Core content: abstract an application as a graph. Tournament scheduling is a minimum-size maximal collection of edge-disjoint perfect matchings (1-factorization) in a complete graph; erasure constraints are coverage guarantees in a conflict graph obtained by selecting a number greedily by degree and deleting its conflicting neighbors. The key result: in a complete graph the minimum size of a maximal matching family is “half-pairs” or “half-pairs plus one” depending on vertex parity; conflict graphs containing odd cycles tighten greedy guarantees.
- Solution route: for the upper bound, use a sufficient condition that the remaining graph has no perfect matching (split into two odd branches); for the lower bound use a 1-factorization construction; select greedily in decreasing degree order.
- Pitfalls: formula boundary errors due to vertex parity; omitting the correspondence between “every pair plays at most once” and edge-disjoint matchings; conflicts occur only between a pair of objects that are additive inverses.
- Step-by-step finish: for $K_{2n}$, a minimum maximal matching family has size `n+1` when `n` is even and `n` when `n` is odd (`n=20→21`); construct so that the complement of the union splits into two odd branches, calibrating $K_4\to3$, $K_6\to3$, $K_8\to5$. The quantity sought is “maximum rounds for which a schedule may stop,” of the `n+1` type, not full-schedule rounds `2n−1`. For conflict-graph erasure guarantees, choose by degree greedily and delete conflicting neighbors; an odd cycle allows at most two selections per three pairs.

## Quick Reference: Counting Classes in Symmetric Structures

- Retrieval terms: grid, cell, board, count, hexagon, parity, symmetric, lattice, cube, colors, triples.
- Core content: on a symmetric grid/three-dimensional lattice, first parameterize objects by symmetry. A regular hexagon is determined by side length and center position (two center types: lattice point and cell center); three-dimensional cells split into orbit classes by coordinate equality (all equal, exactly two equal, all distinct) and parity of coordinate permutations. Counting then becomes summing over parameters and orbit representatives.
- Solution route: in triangular lattices, note legal ranges of both center types; in three dimensions, count color classes by layers of “coordinate-equality pattern + permutation parity.”
- Pitfalls: omitting objects in special rotation orientations, such as oblique hexagons; double-counting orbits; incorrect side-length upper bounds.
- Step-by-step finish: count triangular-lattice regular hexagons over all orientations by $\sum s^3=(n(n+1)/2)^2$ (square triangular number), not only axis-aligned ones. Classify 3D coordinates as all equal `n` + exactly two equal $3C(n,2)$ + all distinct, split by cyclic parity $2C(n,3)$. Small `n` only calibrates; substitute the problem size for the final value. **Anti-pattern**: a global constraint that three directional slices have the same color multiset couples colors at their intersections; cells are **not** independently colorable. Any apparent $n^3$ answer must be brute-force checked at `n=2,3`; disagreement proves a modeling error.

## Quick Reference: Grid Worst-Case Extremes—Identification Queries and Coverage Histograms

- Retrieval terms: grid, board, chessboard, cover, extremal, maximum, minimum, lower bound, cube, query, determine.
- Core content: two types of “determine an optimal quantity in the worst case.” First, use a minimum query set to determine a hidden structure under every response, with a query construction and lower bound from two configurations with identical answers. Second, place large square tiles on a board to maximize the largest frequency in the coverage-count histogram: cover the main region with nonoverlapping tiles first, then incrementally add tiles along boundary strips, balancing newly covered cells against overlap.
- Solution route: use an information-theoretic “two indistinguishable configurations” construction for the lower bound; for histograms fully cover the main region first, then add boundary-strip increments.
- Pitfalls: redundant/overlapping queries; double-counting boundary corners; empty cells with coverage `0` are not included in the statistic.
- Step-by-step finish: query identification uses checking an entire layer plus supplementary checks of odd columns on an adjacent face (`324+162=486` type), with two indistinguishable-answer configurations for the lower bound. For maximum histogram frequency, lay $\lfloor n/k\rfloor^2$ nonoverlapping tiles in the main region (coverage `1`), then increment along two sides and fine-tune corners.

## Quick Reference: Translation-Invariant Total Orders and Parity of Rank Functions

- Retrieval terms: coprime, gcd, count, parity, draw, tie, rank, order-preserving, total order, translation-invariant, bijection.
- Core content: a translation-order-preserving bijection is equivalent to a translation-invariant total order, determined by a positive cone and of the form “layers ordered by a linear functional + an in-layer tie rule.” Its rank is “count of preceding layers + within-layer offset,” allowing exact parity counts over a target rectangle; optimize by traversing feasible coprime slopes and tie rules.
- Solution route: fix the linear functional and tie rule, compute that parameter's count, then compare parameter families; split parity by the combination of layer-index parity and offset parity.
- Pitfalls: reversing the equivalence direction; different tie rules (smaller `x` first versus smaller `y` first) give different counts; forgetting half-open target-region boundaries.
- Step-by-step finish: order = linear-functional layers + in-layer tie direction. Parity count `N` varies over $[N_{min},N_{max}]$ with coprime $(p,q)$ and tie direction; both ends occur for the two tie rules of extreme slopes of type `(1,q)`. When the target is an endpoint product/combination, traverse parameter families and use both endpoints, never just one case.

## Quick Reference: Combinatorial Extremes—Double Counting and Turán-Type Lower Bounds

- Retrieval terms: graph, inequality, extremal, count, combination, pigeonhole, convex, construction, lower bound, polyomino, area, colors.
- Core content: for claims that every coloring/every dense graph contains a large structure, use double counting and power-mean (Hölder) inequalities: the number of desired intersections in a graph is a convex estimate in powers of degrees. For coloring, pigeonhole plus periodic (Latin-square-type) construction shows every small region contains all colors and proves tightness.
- Solution route: write the target as “sum over an inner layer, then raise to a power,” and apply convex inequalities; an upper-bound construction uses periodic coloring so every small structure misses no color.
- Pitfalls: double-counting one structure; reversing power-mean inequality direction; failing to verify that an edge-count lower bound matches an extremal construction.
- Step-by-step finish: in a `k`-coloring there is a polyomino missing at least one color with area $\ge2(k-1)^2$ (pigeonhole + isoperimetry); an order-`k` periodic Latin-square coloring proves every smaller area contains all colors, hence the extremum is $2(k-1)^2$ (`36` colors → `2450`). Turán-type lower bounds use convex estimates of degree power sums.

## Quick Reference: Combinatorial Counting in Circular Transfer Games

- Retrieval terms: count, permutation, combination, recurrence, circle, circumference, name tags, round table, game, passing, leaving, shrinking.
- Core content: at a round table, name tags evolve by “any person holding their own tag leaves; all others pass left; the circle shrinks.” The number of initial permutations for which someone remains after several rounds can be computed by a “shrinking-circle model,” in which transfer steps are recomputed using effective distances after shrinking, with combinatorial recurrence/inclusion–exclusion. The key translation is “someone remains” $\Leftrightarrow$ their tag's initial effective distance exceeds the number of rounds.
- Solution route: first enumerate small cases to verify the shrinking-circle model, then count exactly for the given number of people and rounds.
- Pitfalls: effective distances change as adjacency changes after shrinking; treating uniform count as probability; wrong order of leaving and passing.
- Step-by-step finish: exactly simulate target-event permutation counts for small `n≤10`; only then decide whether Eulerian numbers or a shrinking-circle recurrence extrapolates to the problem scale. Do not guess a closed form.

## Quick Reference: Lempel–Ziv Dictionary Coding

- Retrieval terms: sequence, encoding, code, codeword, dictionary, phrase.
- Core content: LZ coding decomposes a message into phrases of “previously occurring phrase + new character.” Each phrase is a pair (dictionary index, character), dictionary entries grow dynamically, and prescribed fixed-length character encodings concatenate index and character into a bit string.
- Solution route: greedily match the longest previously occurring prefix character by character; concatenate binary index and binary character code; account for index-width changes with dictionary size.
- Pitfalls: greedy matching too long and leaving next phrase unmatched; inconsistent index origin (`0/1`); wrong fixed-codeword width.
- Step-by-step finish: output for every phrase must concatenate “dictionary-index binary (fixed `3` bits) + character code (`3` bits),” with indices starting at `0`. A phrase decomposition alone earns only partial credit; the bit string is the complete answer.

## Quick Reference: Digit DP for Divisibility Counting with Restricted Digit Sets

- Retrieval terms: divisibility, digits, decimal, count, natural numbers, dynamic programming, length, remainder.
- Core content: to count natural numbers whose length is bounded, whose digits come from a finite set, and whose value satisfies divisibility by a small modulus, use digit DP. The state is the residue modulo the modulus of processed digit sum (or number value); transition digit by digit, with coefficients determined by how many allowed digits contribute each residue. Distinguishing strings with leading zeros from actual natural numbers is key: the leading digit cannot be zero, and a correction is “legal natural numbers of length `L` = legal strings of length `L` − legal strings of length `L−1`.” Finally follow the problem's convention for whether `0` itself is included.
- Solution route: the three signals “restricted digit set + small-integer divisibility + length bound” point to digit DP. The modulus is normally one digit, so residues are direct states; if allowed digits share residue classes, count multiplicities first to compress transitions.
- Pitfalls: leading-zero omission; forgetting whether `0` satisfies the condition; enumerating strings without residue classes and exploding state space; off-by-one boundaries when summing lengths from `1` to the limit.

## Quick Reference: Closed Sets of Integer Polynomial Roots (Rich Sets)

- Retrieval terms: covering, divisibility, polynomial, coefficient, subset, roots, binary, power, quotient.
- Core content: an integer subset is *rich* when every integer root of any integer-coefficient polynomial whose coefficients lie in the subset remains in the subset. If it contains every difference of powers of `2`, it first contains all $2^n$, `0`, and $\pm1$. Closure then expands: for $a,b$ in the set with $a\mid b$, the root $b/a$ of $ax-b$ lies in the set, so division produces quotients. Signed binary expansions using $\pm1$ and all powers of `2` express every integer, proving the only rich set is $\mathbb Z$.
- Solution route: start from seeds, construct polynomials with in-set coefficients, and use root closure for new elements; linear polynomials correspond to division and quadratics often produce $\pm1$ and square-root-type elements.
- Pitfalls: expanding before proving powers of `2` and $\pm1$ are in the set; ordinary binary expansion is insufficient; forgetting to reduce every rich set to the unique possible case.
- Step-by-step finish: seed differences of powers of `2` $\Rightarrow 2^n,0,\pm1$ in the set; $ax-b$ yields divisible quotient; signed binary expansion yields every integer $\Rightarrow$ unique rich set $=\mathbb Z$. Finally substitute “all integers” back into the concrete quantity asked (parameter count/set size) and report its value; do not answer $\infty$.
