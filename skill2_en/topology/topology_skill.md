---
name: topology-problem-solving
description: Systematically solve and verify point-set topology and elementary algebraic-topology problems, including topology axioms; interior, closure, boundary, and derived sets; density; continuous maps; subspace, product, and quotient topologies; compactness; connectedness; separation and countability axioms; fundamental groups; covering spaces; Euler characteristics; and homology groups. Use it to identify spatial structure, select definitions or theorems, organize topological proofs, and check the hypotheses required for conclusions.
---

# Topology Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: topology axioms; interior/closure/boundary; continuous maps; product and quotient topologies; compactness/connectedness; separation axioms; and fundamental groups.
- Do not take over: questions that use only real-number metric definitions to prove Cauchy properties or limits belong to mathematical analysis; curvature, geodesics, and fundamental forms belong to differential geometry.
- Verification contract: label the ambient space, subspace topology, and separation/compactness assumptions for every conclusion. Do not extend Euclidean-space conclusions unconditionally.

## Frequent Errors and Conventions (Reviewer Feedback, 2026-07-07)

- **Wedges and covering spaces**: \(\pi_1(S^1\vee S^1)\cong\mathbb{Z}*\mathbb{Z}=F_2\) (the free group of rank \(2\)); its **universal covering space is an infinite \(4\)-regular tree**—the Cayley graph of \(F_2\), with exactly four incident edges at each vertex (corresponding to \(a,a^{-1},b,b^{-1}\)). In general, \(\pi_1(\bigvee_{i=1}^{n}S^1)\cong F_n\), and the universal cover is an infinite \(2n\)-regular tree.
- **Answer every part that is asked**: when a problem asks both “find \(\pi_1\)” and “describe the graph structure of its universal cover,” the final answer must include both parts (the fundamental group + a concrete graph description of the cover). Giving only the fundamental group counts as incomplete.

## Workflow

1. State the underlying set, topology, and subspace or quotient map first; do not silently assume the usual topology.
2. Translate the problem into definitions: whether neighborhoods intersect, whether inverse images are open, whether an open cover has a finite subcover, or whether a separation can be produced.
3. Identify usable structure: a finite topology, a basis, subspace formulas, a product basis, a quotient map, a continuous bijection from compact to Hausdorff, a CW decomposition, or the van Kampen theorem.
4. For a positive property, choose the shortest characterization; for failure, construct an explicit counterexample, separation, uncountable injection, or two distinct invariants.
5. Finally check the space relative to which the conclusion is made, and whether Hausdorffness, compactness, connectedness, local path-connectedness, or other hypotheses are required.

## I. Topology Axioms and Families of Topologies

### Core Concepts

- \(\tau\subset\mathcal P(X)\) is a topology if and only if it contains \(\varnothing,X\), is closed under arbitrary unions, and is closed under finite intersections.
- Candidate topologies on a finite set can be checked exhaustively. If the candidate family is a chain under inclusion, unions and intersections often remain in the chain automatically.
- The intersection of several topologies is the family of sets belonging to every one of them, and it retains all three topology axioms.
- The intersection over an empty index family is customarily \(\mathcal P(X)\), which is the discrete topology.

### Theorems and Formulas

- If \(\{\tau_i:i\in I\}\) are topologies on \(X\), then \(\bigcap_{i\in I}\tau_i\) is again a topology.
- The union of an arbitrary family of topologies is generally not a topology. To generate a topology, take the smallest topology containing that union.

### Standard Solution Steps

1. Check whether \(\varnothing\) and \(X\) belong to the candidate family.
2. Check closure under unions of arbitrary subfamilies; for a finite candidate family, check unions of all distinct elements.
3. Checking intersections of any two elements suffices to establish closure under finite intersections.
4. To prove a statement about an intersection of topologies, first let each set under consideration belong to the intersection, then enter each \(\tau_i\) one at a time and apply its axioms.
5. State the convention for an empty family of topologies separately, or explicitly assume that the index set is nonempty.

### Common Pitfalls

- Do not include closure under arbitrary intersections in the definition of a topology. A topology requires only finite intersections, while it does require arbitrary unions.
- Do not claim that a union of topologies is still a topology.
- Even for a finite set, all three axioms must be checked; the number of elements alone decides nothing.

### Techniques

- If candidate open sets form a chain under inclusion, a union is the larger set and an intersection is the smaller set.
- For an intersection topology, use the uniform template: “it holds in every member topology, therefore it holds in their intersection.”

## II. Interior, Closure, Boundary, Derived Set, and Density

### Core Concepts

- \(A^\circ\) is the largest open set contained in \(A\); \(\overline A\) is the smallest closed set containing \(A\).
- \(x\in\overline A\) if and only if every neighborhood of \(x\) intersects \(A\).
- \(x\in A'\) if and only if every punctured neighborhood of \(x\) intersects \(A\). An isolated point can belong to \(A\), but not to \(A'\).
- \(\partial A=\overline A\cap\overline{X\setminus A}=\overline A\setminus A^\circ\).
- \(A\) is dense if and only if \(\overline A=X\), equivalently, every nonempty open set intersects \(A\).

### Theorems and Formulas

- \(A\) is open if and only if \(A=A^\circ\); \(A\) is closed if and only if \(A=\overline A\).
- \(A\) is both open and closed if and only if \(\partial A=\varnothing\).
- On the usual real line, every nonempty open interval contains both rational and irrational numbers; hence \(\mathbb Q\) and its complement are both dense.
- In the trivial topology, the interior of every nonempty proper subset is empty, and its closure is the whole space.

### Standard Solution Steps

1. Specify the topology from which neighborhoods come, then identify obvious open portions first.
2. Use the neighborhood criterion to include all limit points and obtain the closure.
3. Compute the boundary using \(\partial A=\overline A\setminus A^\circ\).
4. For the derived set, exclude isolated points one by one and prove that every punctured neighborhood of each proposed accumulation point meets \(A\).
5. For density, directly test whether every nonempty basic open set intersects the set.

### Common Pitfalls

- Do not confuse closure with the derived set: usually \(\overline A=A\cup A'\); isolated points lie in the closure but not in the derived set.
- Do not mechanically add endpoints to a closure; neighborhood structures differ between topologies.
- A boundary is relative to the ambient space; changing the ambient space changes the result.

### Techniques

- For “an interval together with finitely many isolated points,” treat interval endpoints and isolated points separately.
- If a set and its complement are both dense, its interior is empty, its closure is the whole space, and its boundary is the whole space.
- For a sequence-type set \(\{0\}\cup\{1/n\}\), first identify its unique accumulation point \(0\).

## III. Continuous Maps and Their Characterizations

### Core Concepts

- \(f:X\to Y\) is continuous if and only if the inverse image of every open set is open; equivalently, the inverse image of every closed set is closed.
- Continuity is also equivalent to \(f(\overline A)\subset\overline{f(A)}\) for every \(A\subset X\).
- Continuous images preserve compactness and connectedness, but generally do not preserve open or closed sets.
- In a finite topology, it suffices to check inverse images of the nontrivial open sets in the codomain topology.

### Theorems and Proof Templates

- Forward closure characterization: if \(f\) is continuous, then \(f^{-1}(\overline{f(A)})\) is a closed set containing \(A\), so \(\overline A\subset f^{-1}(\overline{f(A)})\).
- Reverse closure characterization: for a closed set \(F\) in the codomain, set \(A=f^{-1}(F)\). The hypothesis gives \(\overline A\subset A\), so \(A\) is closed.
- Connected image: if \(f(X)=U\cup V\) is separated, then \(f^{-1}(U),f^{-1}(V)\) separate \(X\).

### Standard Solution Steps

1. When counting maps between finite spaces, list every open set in the codomain and retain only maps whose inverse images belong to the domain topology.
2. For an equivalent-characterization question, first decide whether to use the open-set, closed-set, closure, or neighborhood formulation.
3. In a forward proof, propagate the property through continuity; in a reverse proof, substitute an arbitrary closed or open set into the hypothesis.
4. For connected images, argue by contradiction and ensure that the two inverse images are nonempty, disjoint, relatively open, and cover the domain.

### Common Pitfalls

- Do not test whether images of open sets are open to determine continuity; test inverse images.
- The closure condition is only \(f(\overline A)\subset\overline{f(A)}\), not generally equality.
- The connected continuous-image conclusion concerns \(f(X)\), not necessarily the entire codomain \(Y\).

### Techniques

- The Sierpiński space has only one nontrivial open set, so continuity reduces to one inverse-image condition.
- To prove a condition “for every subset,” the reverse direction often takes \(A=f^{-1}(F)\); this is the standard closed-set inverse-image choice.

## IV. Subspace, Product, Sorgenfrey, and Quotient Topologies

### Core Concepts

- Open sets of a subspace \(Y\subset X\) have the form \(Y\cap U\), and closure satisfies \(\operatorname{Cl}_Y A=Y\cap\operatorname{Cl}_X A\).
- A basis for the product topology consists of \(U\times V\); for density or interior, test every basic open rectangle.
- The Sorgenfrey line has half-open intervals \([a,b)\) as a basis, so usual-topology endpoint intuition cannot be reused.
- The quotient topology is defined by a surjection \(q:X\to X/{\sim}\): \(U\) is open in the quotient if and only if \(q^{-1}(U)\) is open in \(X\).

### Theorems and Standard Models

- \([0,1]/(0\sim1)\cong S^1\), induced by \(t\mapsto e^{2\pi it}\).
- \(D^n/\partial D^n\cong S^n\).
- A continuous bijection from a compact space to a Hausdorff space is a homeomorphism.
- If \(D\) is dense in \(X\), then \(D\times Y\) is dense in \(X\times Y\) (with \(Y\ne\varnothing\)).

### Standard Solution Steps

1. In a subspace problem, first write the candidate set as \(Y\cap U\), then use the relative interior and closure formulas separately.
2. In a product problem, fix an arbitrary basic open set \(U\times V\) and check its intersections with the target set and its complement.
3. In a Sorgenfrey problem, use only \([a,b)\)-neighborhoods. To check a closed set, check whether its complement can be written as a union of basic open sets.
4. To identify a quotient space, construct a continuous surjection constant on equivalence classes, so that it descends to a bijection on the quotient.
5. Use the compact-to-Hausdorff theorem to upgrade the continuous bijection to a homeomorphism.

### Common Pitfalls

- Do not treat interior in the ambient space as the interior in a subspace.
- Basic elements of a product topology are open rectangles, not arbitrary-shaped sets.
- In the Sorgenfrey line, \([0,1)\) itself is open and can also be closed.
- It is insufficient to say a quotient space “looks like” a familiar model; provide at least the induced map and a homeomorphism criterion.

### Techniques

- For a subspace boundary, preferentially use \(\operatorname{Cl}_Y A\setminus\operatorname{Int}_Y A\).
- If a product set constrains only one coordinate, density and interior usually reduce to the corresponding property of that coordinate set in its factor space.
- Collapsing an entire boundary to one point often closes a cell into a sphere.

## V. Compactness, Connectedness, and Separation Axioms

### Core Concepts

- Compactness means that every open cover has a finite subcover. In \(\mathbb R^n\), the Heine–Borel criterion “closed and bounded” may be used.
- A connected space cannot be expressed as a union of two disjoint nonempty relatively open sets. The connected subsets of the real line are exactly the intervals.
- The Hausdorff condition allows distinct points to have disjoint open neighborhoods and is the key to proving that compact subsets are closed.
- The product of two compact spaces is compact; finite products follow by induction.

### Theorems and Proof Templates

- Compact subsets are closed: for \(x\notin K\), separate \(x\) from each \(y\in K\) pointwise; use compactness to choose a finite subcover, then intersect the finitely many neighborhoods of \(x\).
- Finite products are compact: for an open cover of \(X\times Y\), first cover each vertical slice \(\{x\}\times Y\); use the tube lemma to extend this to \(N_x\times Y\); finally use compactness of \(X\) to select finitely many \(N_x\).
- \(\{0\}\cup\{1/n\}\) is closed and bounded, hence compact in the usual real line; its connected subsets can only be singletons.

### Standard Solution Steps

1. Determine whether the ambient space permits Heine–Borel. If not, return to the open-cover definition or the continuous-image theorem.
2. Find all accumulation points and check whether the set contains all of them to decide closedness.
3. For connectedness, try to construct a separation; for subspaces of the real line, one can also use “connected subsets are intervals.”
4. In a Hausdorff-plus-compactness proof, clearly distinguish neighborhoods covering \(K\) from neighborhoods containing the exterior point.
5. In a product-compactness proof, explain how a finite subcover is extended from slices to tube neighborhoods.

### Common Pitfalls

- “Closed and bounded implies compact” applies directly only in specific settings such as Euclidean spaces. In topological spaces beyond \(\mathbb R^n\), Heine–Borel generally fails, and one must return to the finite-subcover definition of compactness.
- A compact subset is closed only when the ambient space is Hausdorff; the conclusion can fail in a general topological space.
- Disconnectedness differs from total disconnectedness; the latter requires every connected component to be a singleton.
- A product-compactness proof cannot merely say every slice has a finite cover: it must unify pointwise conclusions into finitely many slice neighborhoods.
- **Frequent misapplication of Heine–Borel**: beginners often apply the \(\mathbb R^n\) Heine–Borel criterion indiscriminately to all topological spaces. For example, in the discrete topology every subset is both open and closed, and a singleton \(\{x\}\) is closed and bounded but is not necessarily compact (in a discrete topology, the open cover by infinitely many singleton sets has no finite subcover). In the cofinite topology, the whole space itself is compact, while “bounded” has no natural meaning in that topology.
- **Errors in deciding whether accumulation points belong**: when deciding whether a real subset is closed, isolated points are easily overlooked. For \(A=\{0\}\cup\{1/n:n\in\mathbb N\}\), \(0\) is the only accumulation point of \(A\) and belongs to \(A\), so \(A\) is closed. But if \(0\) is excluded (\(A=\{1/n:n\in\mathbb N\}\)), then \(0\) is an accumulation point not in the set, so the set is not closed. The core closedness criterion is \(\overline A=A\): every accumulation point must belong to \(A\).
- **Ignoring endpoint boundary effects in an open-cover argument**: when constructing a counterexample to compactness, ensure that every open set in the cover actually covers its corresponding portion of the target. For example, when proving that \((0,1]\) is not compact, the open cover \(\{(1/n,2):n\in\mathbb N\}\) must be verified by showing that for every \(x\in(0,1]\), some \(n\) satisfies \(1/n<x\).

### Techniques

- Using one open neighborhood of an exterior point that avoids the entire compact set is the standard compact-plus-Hausdorff combination.
- In a subspace of \(\mathbb R\), if a set contains no nondegenerate interval, all its connected subsets can only be singletons.
- **Using Heine–Borel in practice**: to determine compactness in \(\mathbb R^n\), prefer Heine–Borel (closed and bounded). If the stated space is not Euclidean, return to the open-cover definition. A typical problem gives a subset of \(\mathbb R\), such as \(\{0\}\cup\{1/n:n\in\mathbb N\}\): first determine boundedness (all points lie in a finite interval), then closedness (whether it contains all accumulation points). For a discrete set, check one point at a time whether it is isolated: if the minimum distance between points is positive, every point is isolated and the set is closed.
- **General template for constructing a finite subcover**: given an open cover \(\{U_\alpha\}\) of a closed interval \([a,b]\subset\mathbb R\), let \(S=\{x\in[a,b]:[a,x]\text{ can be covered by finitely many sets}\}\). Prove that \(\sup S\in S\) and \(\sup S=b\), thereby proving that \([a,b]\) is compact. This “climbing” argument is a core compactness technique.
- **Compactness is preserved by continuous images**: if \(f:X\to Y\) is continuous and \(X\) is compact, then \(f(X)\) is compact. This is an effective shortcut around direct construction of a finite subcover—first try to express the target as the continuous image of a known compact space.
- **Constructing noncompactness counterexamples**: in \(\mathbb R\), \((0,1]\) is bounded but not closed (it omits the accumulation point \(0\)), while \([0,\infty)\) is closed but unbounded; neither is compact. Giving an explicit infinite open cover (such as \((0,1]=\bigcup_{n=1}^\infty(1/n,2)\)) is the most reliable proof of noncompactness.

## VI. Fundamental Groups, Covering Spaces, and Homology

### Core Concepts

- The fundamental group records homotopy classes of loops based at a point; the fundamental group of a product is the direct product of the fundamental groups.
- A wedge of graphs corresponds to freely generated loops; the wedge of \(r\) circles has fundamental group the free group \(F_r\).
- A universal cover is a simply connected covering space; the universal cover of a graph is a tree.
- Cellular homology is computed from the cellular chain complex and boundary operators; the Euler characteristic is the alternating sum of the numbers of cells.
- Reduced homology removes the \(H_0\cong\mathbb Z\) contribution of a nonempty connected space.

### Formulas and Theorems

- \(\pi_1(X\times Y)\cong\pi_1(X)\times\pi_1(Y)\).
- \(\pi_1(S^1)\cong\mathbb Z\), hence \(\pi_1(T^2)\cong\mathbb Z^2\).
- For a closed orientable surface of genus \(g\): \(\chi=2-2g\), \(H_0\cong\mathbb Z\), \(H_1\cong\mathbb Z^{2g}\), and \(H_2\cong\mathbb Z\).
- \(\widetilde H_k(S^n;\mathbb Z)\cong\mathbb Z\) when \(k=n\), and is \(0\) in every other dimension.
- \(\pi_1(S^1\vee S^1)\cong F_2\); its Cayley graph with respect to \(a,b\) is an infinite \(4\)-regular tree.

### Standard Solution Steps

1. First identify the space as a product, quotient, sphere, surface, or graph.
2. For a fundamental-group problem, choose the product theorem or the van Kampen theorem and list generators and relations.
3. For a covering-space problem, label oriented edges by fundamental-group generators, and check that the covering graph is connected and acyclic.
4. For a homology problem, write the numbers of cells and boundary operators, then compute \(\ker\partial_k/\operatorname{im}\partial_{k+1}\) dimension by dimension.
5. Cross-check with the Euler–Poincaré formula \(\chi=\sum(-1)^k\operatorname{rank}H_k\).

### Common Pitfalls

- Do not confuse \(\mathbb Z\times\mathbb Z\) with the free group \(F_2\); the former is abelian while the latter is not.
- Reduced homology and ordinary homology differ in dimension \(0\).
- “\(4\)-regular” for the universal cover counts degree in the undirected graph: the four directions correspond to \(a,a^{-1},b,b^{-1}\).
- An Euler characteristic alone cannot uniquely determine all homology groups; information about the space type or boundary operators is also needed.

### Techniques

- Upon seeing a torus, immediately use the product; upon seeing a wedge, immediately consider a free group.
- Upon seeing \(D^n/\partial D^n\), first identify it with \(S^n\), then read off reduced homology directly.
- For a surface answer, compute the Euler characteristic once from the ranks of the homology groups; this quickly detects dimension errors.

## VII. Separability and Countability Axioms

### Core Concepts

- A space is separable if it has a countable dense subset.
- A space is first countable if every point has a countable local basis.
- A space is second countable if its whole topology has a countable basis. Second countability implies first countability and separability, but the converses generally fail.
- The Sorgenfrey line is the standard example that is separable and first countable but not second countable.

### Theorems and Constructions

- \(\mathbb Q\) is dense in \(\mathbb R_\ell\), because every nonempty basic open set \([a,b)\) contains a rational number.
- A countable local basis at \(x\) is \(\{[x,x+1/n):n\ge1\}\).
- If \(\mathcal B\) is a basis of the Sorgenfrey line, then for each \(x\) one can select \(B_x\in\mathcal B\) such that \(x\in B_x\subset[x,x+1)\). The map \(x\mapsto B_x\) is injective; therefore \(\mathcal B\) is uncountable.

### Standard Solution Steps

1. For separability, provide a concrete countable set and prove that every nonempty basic open set meets it.
2. For first countability, explicitly write a countable local basis at every point and verify that every neighborhood contains one of its members.
3. For failure of second countability, assume a countable basis exists, select a dedicated basis element for every real number, and construct an injection from an uncountable set into the basis.
4. Prove the three properties separately; do not infer one directly from the other two.

### Common Pitfalls

- Separability does not imply second countability; the Sorgenfrey line is precisely a counterexample.
- A local basis depends on its point; second countability requires one global countable basis.
- To prove density, use Sorgenfrey half-open basic sets, rather than merely citing density in the usual topology.

### Techniques

- Choosing \(B_x\subset[x,x+1)\) distinguishes different real numbers using their left endpoints: if \(x<y\), one set cannot satisfy both containment requirements simultaneously.

## General Result Verification

### Problem-Type Recognition and Method Selection

| Problem signal | Preferred method | Verification point |
|---|---|---|
| Finite candidate family of open sets | Check topology axioms one by one or enumerate | No arbitrary union or finite intersection is missed |
| Interior/closure/boundary/derived set | Neighborhood definitions and identities | Ambient space and isolated points |
| Continuous map between finite spaces | Check inverse images of nontrivial open sets | Whether the count covers every map |
| Subspace | \(Y\cap U\) and relative-closure formula | Do not mix it with ambient interior |
| Product set | Basic open rectangles | Whether both coordinate factors are nonempty |
| Homeomorphism type of quotient space | Construct quotient map and continuous bijection | Compact-to-Hausdorff hypotheses |
| Compactness/connectedness | Open covers, separations, or continuous images | Prerequisites such as Hausdorffness |
| Fundamental group and covering | Products, van Kampen, Cayley graph | Commutation relations and vertex degrees |
| Surface/sphere homology | Cellular chain complex | Euler-characteristic cross-check |
| Countability axioms | Explicit dense set/local basis/uncountable injection | Distinguish a local basis from a global basis |

### Verification Checklist

1. At the beginning and conclusion, label the topology and relative space being used.
2. Check the hypotheses of every theorem application: compactness, Hausdorffness, connectedness, nonemptiness, basepoint, or coefficient ring.
3. Cross-check interior, closure, and boundary using identities, for example \(\partial A=\overline A\setminus A^\circ\).
4. For a homeomorphism claim, compare invariants such as compactness, connectedness, fundamental group, and homology.
5. For a finite space, enumerate all subsets or maps; for a covering graph, check local degrees and acyclicity.
6. Cross-check homology answers with the Euler–Poincaré formula for free ranks.

## Exercise-Solution Index (idx 0–19)

## General Supplement: Deciding Compactness and Completeness

1. In Euclidean space, first confirm that the ambient space is a finite-dimensional real space, then use “closed and bounded” if and only if compact. In a general metric space, return to the definition by open covers or sequential compactness.
2. Decide the Cauchy property, convergence, and boundedness separately according to their implication directions: convergence implies Cauchy; whether a Cauchy sequence converges depends on completeness.
3. For a multiple-choice statement based on a definition, verify it directly from the definition first. For a converse statement, give a counterexample satisfying the antecedent but not the consequent.

| idx | Topic | Core idea | Key verification |
|---:|---|---|---|
| 0 | Topology axioms | Candidate open sets form an inclusion chain; directly check empty set, whole set, arbitrary unions, and finite intersections | The four set operations remain in \(\tau\) |
| 1 | Interior, closure, boundary, derived set | Treat intervals and isolated points separately, then use the boundary identity | \(2\) is isolated and is not in the derived set |
| 2 | Trivial topology | A nonempty proper subset contains no nonempty open set; the only closed set containing it is \(X\) | Interior is empty; closure and boundary are both \(X\) |
| 3 | Continuous maps between finite topologies | Check only whether \(f^{-1}(\{1\})\) belongs to \(\tau\) | Possible inverse images are \(\varnothing,\{1\},S\), for a total of \(3\) |
| 4 | Dense sets | Every open interval contains both rational and irrational numbers | Interior is empty; closure and boundary are \(\mathbb R\) |
| 5 | Sorgenfrey line | \([0,1)\) is basic open; write its complement as a union of lower-limit basic open sets | It is both open and closed, so its boundary is empty |
| 6 | Subspace topology | Write \(A=Y\cap(-1,1)\); use \(Y\cap[0,1]\) for closure | Relative interior is \([0,1)\), and boundary is \(\{1\}\) |
| 7 | Product topology | The first-coordinate interval of every open rectangle meets both \(\mathbb Q\) and its complement | Interior is empty; closure and boundary are the whole plane |
| 8 | Quotient topology | Let \(t\mapsto e^{2\pi it}\) descend to a continuous bijection | Domain is compact and \(S^1\) is Hausdorff, hence it is a homeomorphism |
| 9 | Compactness and accumulation points | The set is closed and bounded; its unique accumulation point is \(0\); connected subsets of the real line are intervals | Compact, derived set \(\{0\}\), totally disconnected |
| 10 | Fundamental group and product | Use \(\pi_1(S^1\times S^1)=\pi_1(S^1)^2\) | Obtain \(\mathbb Z\times\mathbb Z\); the two generators commute |
| 11 | Surface and homology | Standard CW decomposition for genus \(2\), or the general surface formula | \(1-4+1=-2\), consistent with homology ranks |
| 12 | Quotient space and reduced homology | Use \(D^2/\partial D^2\cong S^2\) | Only \(\widetilde H_2\cong\mathbb Z\) is nonzero |
| 13 | Wedge and covering space | van Kampen gives \(F_2\); take its Cayley graph as the universal cover | The graph is connected and acyclic, and every vertex has degree \(4\) |
| 14 | Intersection of topologies | Apply all three axioms within every member topology one by one | Account for the empty-index-family convention or state nonemptiness |
| 15 | Closure characterization of continuity | Forward: use inverse images of closed sets; reverse: for closed \(F\), take \(A=f^{-1}(F)\) | Both directions are complete and require only inclusion |
| 16 | Continuous image of a connected space | Assume the image has a separation, then take inverse images of its two separating sets | Inverse images are nonempty, disjoint, relatively open, and cover \(X\) |
| 17 | Compactness and separation axioms | Separate the exterior point from each point of the compact set, then use a finite subcover and a finite intersection of neighborhoods | The Hausdorff condition cannot be omitted |
| 18 | Compactness of finite products | Cover vertical slices first, extend by the tube lemma, then use compactness of \(X\) | Ultimately use only finitely many sets from the original open cover |
| 19 | Countability axioms | \(\mathbb Q\) proves separability; \([x,x+1/n)\) proves first countability; injection into basis elements proves non-second-countability | Prove all three conclusions separately; avoid converses |

## Quick Reference: Deciding Compactness of Subsets of the Real Line

### Core result

For a subset \(K\subseteq\mathbb R\),

\[
\boxed{K\text{ is compact}\iff K\text{ is closed and bounded}.}
\]

Equivalently, every open cover of \(K\) has a finite subcover. In \(\mathbb R\), use the closed-and-bounded criterion first; when the ambient space is not a Euclidean space, return to the open-cover definition or sequential compactness instead.

### Standard decision route

1. Identify the ambient space. The criterion above is specific to subsets of \(\mathbb R\) (more generally, finite-dimensional Euclidean space).
2. Test closedness, including whether all finite limit points are included.
3. Test boundedness by finding finite upper and lower bounds.
4. For a statement asserted directly from the definition, check the quantifiers in the open-cover definition rather than assuming a converse.

### Multiple-choice reference: compactness statements in \(\mathbb R\)

The correct choices are

\[
\boxed{C,E}.
\]

- **A is false.** \([0,+\infty)\) is closed but not bounded, so it is not compact.
- **B is false.** Boundedness alone does not imply compactness; for example, \((0,1)\) is bounded but not closed.
- **C is true.** Every closed and bounded subset of \(\mathbb R\) is compact.
- **D is false.** \((0,1)\) is not compact. A standard open-cover counterexample is \(\{(1/n,1-1/n)\}\); no finite subcollection covers all of \((0,1)\).
- **E is true.** This is precisely the definition of compactness: every open cover admits a finite subcover.

### Pitfalls

- Do not replace “closed and bounded” with only “closed” or only “bounded.”
- Do not use the Euclidean closed-and-bounded criterion in an arbitrary metric or normed space without checking its hypotheses.
- In an open-cover counterexample, verify both that the family covers the set and that every finite subfamily misses some point.
