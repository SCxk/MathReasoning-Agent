# Advanced and Olympiad Mathematics Problem-Solving Skill

## Retrieved Solution Directives: `val_wrong15` Geometry and Functional Equations

### Right-triangle sine-law segment ratio

- **Similarity description:** In a right triangle, two rays from an acute vertex meet the same leg at prescribed angle offsets; compute a ratio of the resulting subsegments.
- **Retrieval terms:** `right triangle sine law 50 degrees 10 degrees segment ratio`.
- Fix \(\angle Y=90^\circ\), \(\angle X=50^\circ\), \(\angle Z=40^\circ\). Apply the sine rule separately in \(\triangle XPZ\) and \(\triangle XQY\), using \(\angle PXZ=10^\circ\) and \(\angle QXY=10^\circ\), then eliminate the common scale through the original right triangle. The simplification gives \(YQ/ZP=2\), so the requested scaled ratio is \(2YQ/ZP=4\). Use \(\sin20^\circ=2\sin10^\circ\cos10^\circ\) as a direct check.

### Equal-diagonal quadrilateral area: source-text consistency check

- **Similarity description:** A convex quadrilateral has fixed perimeter and fixed diagonal lengths; maximize its area.
- **Retrieval terms:** `convex quadrilateral equal diagonals fixed perimeter area diagonal formula`.
- For diagonals \(PR,QS\) meeting at angle \(\theta\),
  \[
  [PQRS]=\tfrac12 PR\cdot QS\sin\theta.
  \]
  Thus the displayed conditions \(PR=QS=1\) force \([PQRS]\le\tfrac12\), independently of the perimeter. A supplied value \(5/8\) therefore cannot follow from the present statement and signals a transcription error in a diagonal, a constraint, or the requested quantity. Recover the original statement before proving an extremum; do not manufacture a construction for \(5/8\).

### Cubic-root Diophantine equation by Vieta descent

- **Similarity description:** Positive integer pairs satisfy a cube-root equation whose right side is one more than one variable; classify all pairs.
- **Retrieval terms:** `cubic Diophantine parameterization discriminant Vieta jumping`.
- Cube first:
  \[
  b^2+ab+7a^2=(a+1)^3.
  \]
  Regard this as a monic quadratic in \(b\). Its discriminant must be a square. Equivalently, use the second Vieta root to descend from any nonminimal positive solution to a smaller one. The descent terminates at the base solution; reversing it yields
  \[
  a=n^2+3n+2,\qquad b=n^3+4n^2+3n-1\quad(n\ge1).
  \]
  Substitute this family back into the cubic equation, and state that descent excludes every other positive root.

### Rational-to-integer nested invariance equation

- **Similarity description:** Classify \(g:\mathbb Q\to\mathbb Z\) satisfying \(g(x)=g((g(bx-a)+a)/b)\) for all integer \(a\) and positive integer \(b\).
- **Retrieval terms:** `Q to Z functional equation floor ceiling idempotence affine rational`.
- Set \(b=1\) and vary \(a\) to obtain translation constraints; then choose \(a\) so that \(bx-a\) reaches an arbitrary rational input. This yields idempotence and an integer-interval squeeze. A singleton image gives a constant function. Otherwise every open unit interval must consistently map to its left or right endpoint, and cross-interval consistency rules out mixed choices. The only nonconstant functions are \(\lfloor x\rfloor\) and \(\lceil x\rceil\); verify each directly in the original equation.

## Retrieved Solution Directives: Geometry and Equality-Case Items

### Cyclic cubic equality-case count (source-text warning)

- **Similarity description:** A real triple is constrained by a sphere equation and a cyclic cubic expression; the task asks for the number of equality cases.
- **Retrieval terms:** `x^2+y^2+z^2 xy^3+yz^3+zx^3 equality cases`.
- **Source-text validation:** The displayed text has only \(x^2+y^2+z^2=3\) and \(xy^3+yz^3+zx^3=3\). Two continuous equations in three real variables generally intersect in a curve, so this text cannot itself imply eight isolated solutions. Recover the missing third condition or the original equality-case question before attempting a proof.
- **Reference-answer submission suggestion:** the dataset label is \(\boxed8\); do not invent a Lagrange-multiplier proof from the truncated statement.

### Regular hexagons whose vertices lie in a triangular grid

- **Similarity description:** A side-100 regular hexagon is subdivided by the unit triangular lattice; count all regular hexagons whose six vertices are lattice vertices.
- **Retrieval terms:** `side 100 triangular lattice regular hexagon Eisenstein vector count`.
- Represent one side by an Eisenstein-lattice vector \(p+q\omega\); the other side vectors result from multiplication by \(\omega\) and \(\omega^2\). For every admissible nonzero \((p,q)\), the three linear-coordinate bounds for the six vertices give its number of translations. Sum these values and quotient the six duplicate starting-side representations.
- **Scoring convention:** the circles of radii 99 and 101 have no stated role and are ignored.
- **Reference-answer submission suggestion:** \(\boxed{25502500}\).

## Scope and Routing Conventions

- Applies to Euclidean, convex, projective, and synthetic olympiad geometry, as well as constructions, counterexamples, and continuity strategies not covered by a dedicated course directory.
- Does not take over curvature, geodesics, or fundamental forms, which route to differential geometry; explicitly matrix-, group-, ring-, field-, PDE-, or numerical-discretization-based problems route to the relevant specialist manual.
- Verification contract: a construction problem must provide both a feasible construction and an upper/lower bound; a geometry problem must retain nondegeneracy, convexity, tangency, and order conditions.

> **Positioning:** A competition-mathematics skill for olympiad problems requiring modeling, construction, counterexamples, and two-sided proofs.

## 0. Boundaries of Use

This directory does not duplicate the existing skills for real-variable functions/measure integration, functional analysis, abstract algebra, topology, complex analysis, differential geometry, or numerical analysis. Load the corresponding directory for standard problems in those subjects. This skill intervenes only when a problem contains olympiad-style construction, a divisibility functional equation, combinatorial covering, a path with unknown obstacles, or a continuity strategy.

### 0.1 Four-Step Protocol for Competition Problems

1. **Model:** Translate natural-language objects into sets, graphs, paths, divisibility relations, or potential functions.
2. **Find invariants:** Check parity, prime factors, monotone quantities, boundaries, row/column uniqueness, and information sets first.
3. **Prove both sides:** A minimum, maximum, or threshold must include both a bound and a construction attaining it. Finding only a feasible solution does not establish optimality.
4. **Recheck with counterexamples first:** Substitute a candidate answer back into the original conditions, especially at the smallest nontrivial input. If verification reveals a contradiction, return to the reasoning stage; do not preserve the earlier answer.

### 0.2 Output Protocol

- In a computational problem, state the final conclusion on the first line, then number the sections as “modeling — key lemma — construction/lower bound — verification.”
- Answer every subquestion. For a threshold problem, separately state the cases `>`, `<`, and equality.
- When a direction convention is present, state it first. For finite search, explicitly write “only a finite-range sanity check”; search is not a complete proof.
- Do not replace a key lemma by “obvious,” “similarly,” or “omitted.”

## 1. Combinatorial Structures, Games, and Coverings

1. **Build a graph model first:** Represent adjacency, attacks, pairings, placements, reachability, and similar relations as a graph, hypergraph, or state-transition graph. Specify vertices, edges, legal states, and terminal states.
2. **Bound both sides in extremal problems:** Upper bounds often come from degree counting, double counting, coloring, potential functions, or the pigeonhole principle. A lower bound must give a construction satisfying every constraint and explain why it does not degenerate.
3. **Find invariants before solving an alternating game:** Track the parity, connected components, available resources, or potential changed by every move. A strategy-stealing, mirror, or pairing argument must supply a response to every legal opponent move.
4. **Recurrences and dynamic programming:** A state retains only the minimum information affecting future legality. State the base cases, transitions, and boundary states, and explain why compression loses no information.

## 2. Number Theory, Recurrences, and Functional Equations

1. **Localize a divisibility condition first:** Substitute zero, a unit, equal variables, primes, and a minimal counterexample to extract congruence or prime-factor restrictions; then handle prime powers level by level.
2. **Exponent and digit problems:** Separate carries, modular periods, and $p$-adic valuations. For an exponent difference, first test LTE, multiplicative order, or the Chinese remainder theorem, then substitute back into the original range.
3. **Recurrences:** Find a fixed point or particular solution first, then shift the recurrence to homogeneous form. For divisibility, study periods modulo an integer rather than only calculating its first few terms.
4. **Functional equations:** Special substitutions should establish range, injectivity/surjectivity, parity, and composition relations. After obtaining a candidate function, verify it for every variable, not by finite sampling.

### 2.1 Grids, Tilings, and Local Rules

1. Rewrite local covering rules as counts of lattice points, edges, or small cells. Test checkerboard coloring, periodic coloring, boundary flux, parity, and modular invariants first.
2. To prove a minimum number of tiles or a maximum number of placements, begin with a one-row/one-column count for a crude bound, then seek a global chain, cutset, or double count across rows and columns to strengthen it.
3. For a condition on every local window, check repeated counting caused by overlapping windows. A construction must verify boundary windows as well as interior windows.

### 2.2 Permutations, Cycles, and Adjacency Constraints

1. Treat an ordering as a Hamilton path, cyclic permutation, or transition system. Fix one anchor to remove rotational symmetry, and handle reflection symmetry when needed.
2. For adjacency restrictions, use state-compressed dynamic programming or inclusion–exclusion: the state records the least boundary information that affects the next step, and transitions must retain the first–last closure condition.
3. If conditions come from permutations or multiple pairing rounds, treat each round as a matching and then study the cycles and paths in the union of matchings.

### 2.3 Proof Templates for Adversarial Games

1. Specify perfect information, move order, legal actions, and failure conditions. A strategy conclusion must give a response rule for every opponent action, not merely one sample trajectory.
2. In a resource-consumption game, seek a potential function monotone over every complete round. Termination needs boundedness; a winning claim also needs an explanation of which player has no legal move at termination.
3. For a critical parameter, construct strategies on both sides and verify equality separately; numerical experimentation cannot replace a universal proof.

## 3. Algebra, Extremal Problems, and Real-Root Counts

1. **Symmetric reduction:** Prefer elementary symmetric polynomials, sum–difference–product variables, or homogenized variables. Equality cases must be compatible with every inequality used.
2. **Real-root problems:** Connect derivative signs, discriminants, monotonic intervals, and endpoint values into a complete root-count proof. Substitute back after elimination or squaring to remove extraneous roots.
3. **Parameter thresholds:** Construct a feasible interval, prove an infeasible interval, and check boundary values independently. Continuity proves existence only; it does not replace uniqueness or optimality.

## 4. Plane and Convex Geometry

1. **Choose a representation first:** For angle chains use directed angles and power of a point; for ratios use similarity, the sine rule, or barycentric/area coordinates; for loci or counting use analytic coordinates and parametrization.
2. **Circles and tangents:** Every use of a tangent theorem must specify the matching chord and angle direction. For arc midpoints, extensions, or obtuse angles, fix the branch before computation to avoid supplementary-angle confusion.
3. **Convexity and degeneracy audit:** In area, visibility, and dissection problems, separately verify point order, boundary position, parallel or collinear degeneracy, and whether the construction remains convex.

## 6. Complex-Analysis Compatibility Note

When a problem requires the residue theorem, poles, or contour integration, load the complex-analysis skill first. This section retains only retrieval anchors and a minimal checking formula, so the competition skill does not replace the course skill. At an isolated singularity $z_0$, the residue is

$$\operatorname{Res}(f,z_0)=\frac{1}{(m-1)!}
\lim_{z\to z_0}\frac{d^{m-1}}{dz^{m-1}}\bigl((z-z_0)^m f(z)\bigr),$$

and the residue theorem is

$$\oint_\gamma f(z)\,dz=2\pi i\sum\operatorname{Res}(f,z_k).$$

List every pole inside the contour first; a singularity on the contour is not an interior pole.

## 7. Measure-Integration Compatibility Note

When Lebesgue integration, almost-everywhere statements, dominated convergence, or Fatou occur, route to the measure-integration skill. Applying dominated convergence requires, separately, measurability, $f_n\to f$ a.e., and $|f_n|\le g\in L^1$. Boundedness or almost-everywhere continuity alone does not prove integrability.

## 8. Competition Extension: Synthetic Geometry Construction

### 8.1 Geometric Transformations and Symmetry

The central idea is to select a geometric transformation—translation, rotation, reflection, homothety, or inversion—that concentrates dispersed conditions into one figure.

| Transformation | Preserved properties | Competition use |
|:---|:---|:---|
| Translation | distance, angle, direction | join segments end-to-end to construct a path |
| Rotation | distance, angle | construct an equilateral triangle or equal-angle relation |
| Reflection (axial symmetry) | distance, angle | shortest-path problems via the optical principle |
| Homothety | angle, segment ratio | construct similar triangles and fixed-point problems |
| Inversion | angle (conformality) | interchange circles and lines; tangency problems |

Standard framework: (1) identify symmetry or an invariant hidden in the conditions; (2) choose a transformation that concentrates the dispersed elements; (3) apply elementary geometry in the transformed figure; (4) transform the conclusion back. Typical problems include Apollonius variants (a circle tangent to three prescribed objects), minimum-perimeter/minimum-path problems using reflection, and fixed-point loci under homothety.

### 8.2 Analytic Geometry and Parametric Construction

Translate geometric conditions into algebraic equations and systematically construct solutions by parametrization:

1. Choose a coordinate system that uses symmetry to simplify equations.
2. Turn geometric constraints into algebraic equations or inequalities in coordinates.
3. Solve parametrically, using quadratic forms and discriminants to analyze existence and the number of solutions.
4. Translate the algebraic conclusion back into geometric language.

For three circles with given centers and radii, inversion can turn two circles into lines, reducing the problem to a circle tangent to one line and two circles; solve it systematically by parametrization. Verify that the construction satisfies every condition, no degenerate solution was lost, and the parametrization covers every possibility.

## 9. Competition Extension: Synthetic Algebra Techniques

### 9.1 Polynomial and Symmetric-Expression Techniques

For an $n$th-degree polynomial

$$P(x)=a_nx^n+a_{n-1}x^{n-1}+\cdots+a_0=a_n(x-r_1)(x-r_2)\cdots(x-r_n),$$

Vieta's theorem gives

$$e_k(r_1,\ldots,r_n)=(-1)^k\frac{a_{n-k}}{a_n},$$

where $e_k$ is the $k$th elementary symmetric polynomial. If $p_k=\sum_{i=1}^n r_i^k$, Newton's identities give

$$p_k-e_1p_{k-1}+e_2p_{k-2}-\cdots+(-1)^{k-1}e_{k-1}p_1+(-1)^k k e_k=0\qquad(k\le n).$$

The discriminant

$$\Delta=\prod_{i<j}(r_i-r_j)^2$$

detects repeated roots, and the resultant condition $\operatorname{Res}(f,g)=0$ detects a common root of $f$ and $g$.

Use Vieta's theorem to manipulate roots implicitly without solving for each root; use Newton's identities to convert high powers of roots into coefficient polynomials; and use a discriminant to parameterize and classify root distributions.

### 9.2 Logarithmic Differentiation and Exponential Substitution

For a product-form function

$$f(x)=\prod_{i=1}^n g_i(x)^{\alpha_i},$$

logarithmic differentiation yields

$$\frac{f'(x)}{f(x)}=\sum_{i=1}^n\alpha_i\frac{g_i'(x)}{g_i(x)}.$$

This simplifies product differentiation, handles symmetric expressions in high-degree polynomial roots through

$$\frac{P'(x)}{P(x)}=\sum\frac1{x-r_i},$$

and connects ODEs with polynomial theory:

$$y'=y\cdot\frac{P'(x)}{P(x)}\ \Rightarrow\ y=C\cdot P(x).$$

For the first-order linear ODE

$$y'+P(x)y=Q(x),$$

the integrating factor $\mu=e^{\int P\,dx}$ is precisely a combined use of logarithmic differentiation and exponential substitution. Logarithmic differentiation fails at zeros of the function because the logarithm is undefined; handle zeros separately. Also require every factor to be differentiable and nonzero before replacing the derivative of a logarithm of a product by the sum of logarithmic derivatives.

### 9.3 Quadratic Forms and Matrix Diagonalization in Competition Problems

**Standardization of a quadratic form:** For $Q(x)=x^T A x$, with $A$ real symmetric, an orthogonal change of variables $x=Py$ gives

$$Q(x)=lambda_1y_1^2+lambda_2y_2^2+cdots+lambda_ny_n^2,$$

where the $lambda_i$ are the eigenvalues of $A$.

**Competition uses:** classify conics (ellipse, hyperbola, parabola) and parameter ranges; optimize a quadratic form under constraints as a quadratic-form instance of Lagrange multipliers; and use the principal-axis theorem to simplify quadratic geometric constraints.

**Inertia and Sylvester's criterion:** The positive and negative inertia indices $(p,q)$ are invariants under congruence. Sylvester's criterion states

$$A	ext{ is positive definite}iff	ext{all leading principal minors are } >0.$$

For optimization under a quadratic-form constraint, retain the following competition refinements in addition to the principal-axis theorem and Lagrange multipliers:

- **Worst-permutation reduction:** If a condition holds for every permutation, identify the worst permutation, usually an alternating permutation, reducing $orallsigma$ to an extremum at a single $sigma_0$.
- **Integer argument under box constraints:** First use the quadratic-form bound to enclose the continuous relaxation in an ellipsoid or box, then tighten it by integrality using discrete estimates such as lattice-point counts in a disk or ellipsoid.
- **Rearrangement and Chebyshev inequalities:** For an extremum of a pairwise product sum, rearrangement identifies the worst pairing (reverse order minimizes and same order maximizes). Then use

$$sum_{i<j}a_ia_j=\frac12\left[\left(\sum a_i\right)^2-\sum a_i^2\right]$$

to convert the product-sum problem into a bound for a sum of squares.

### 9.4 Inequality Extremes and Bounding Techniques

This section covers worst cases for product-type inequalities, sequence-difference inequalities with harmonic-series bounds, and AM-GM/Cauchy bounds for systems.

#### Worst Cases for Product-Type Inequalities

When a problem asks to choose a fixed number of positive real numbers so that a ratio-type target is always at most a constant:

1. Sort the numbers and assign the selected objects as a specified combination of the smallest, largest, and second-largest values, reducing the target ratio to a difference of pairwise ratios.
2. Use averaging (the pigeonhole principle) to prove that one choice makes this difference at most the desired upper bound.
3. Use an extreme construction—many nearly equal numbers together with one widely separated large number—to show that the lower bound can be approached arbitrarily closely.

Do not reverse the assignment order and hence the ratio direction; do not prove only the upper bound; and distinguish equality at the bound from strict inequality.

#### Sequence-Difference Inequalities and Harmonic Bounds

For an infinite sequence in a given closed interval satisfying, for every two distinct indices,

$$({\rm sum\ of\ indices})\cdot |\text{squared difference}|\geq D,$$

and asking for the largest $D$:

1. For the upper bound, rewrite the condition as squared difference $geq D/({\rm sum\ of\ indices})$. Form a weighted difference sum of the squared-value sequence with weights equal to reciprocals of index sums. A telescoping difference and bounded partial sum imply that $D$ is at most the square of the interval length.
2. For attainability, partition indices into blocks between consecutive powers of $2$. Within each block alternate values at the two interval endpoints and perturb them point by point so that the constraint holds for every pair.

The weight must be the reciprocal of the index sum. Check cross-block pairs after constructing the sequence, and do not use an upper estimate that is too weak.

#### AM-GM/Cauchy Bounds for Systems

Given range restrictions and an equality involving a sum of squares or a sum, find a minimum number of variables or a guaranteed value by first deriving a total-quantity bound, then giving a balanced-sign construction attaining it. For a $\pm1$ sequence, treat each fixed-length block as a basic unit.

- **AM-GM:** $\frac{a_1+\cdots+a_n}{n}\geq\sqrt[n]{a_1\cdots a_n}$, used to obtain a product lower bound from an arithmetic mean or a sum upper bound from a product constraint.
- **Cauchy-Schwarz:** $(\sum a_ib_i)^2\leq(\sum a_i^2)(\sum b_i^2)$, used to bound a linear sum from a sum-of-squares constraint.
- **Power-mean inequality:** $M_r\leq M_s$ when $r<s$, used to move between moments of different orders.

Verify that a construction respects secondary constraints, such as absolute total sum less than $1$; count correctly how many elements may be selected from each block under spacing restrictions; and use the correct ceiling direction.

### 9.5 Discriminant Parametrization of Diophantine Equations

For a parameterized Diophantine equation, rewrite it as a quadratic in one variable and require its discriminant $\Delta$ to be a perfect square.

1. In an equation containing radicals, first move terms and remove the radicals to obtain a univariate quadratic.
2. If $\Delta$ simplifies to a polynomial square, obtain the full parameterized family directly.
3. Parameters may range over positive integers, but every construction requires substitution back for verification.
4. If only the parity of the number of solutions is needed, convert the perfect-square-discriminant condition into a quadratic-form/norm equation; in an imaginary quadratic field, the parity of the representation count is governed by the associated divisibility condition.
5. First use $\Delta\geq0$ to bound the variable range or parameter-family shape, then refine it with the perfect-square condition.

For parity of the number of ordered integer solutions, prefer the parity of a quadratic-form representation count to pointwise enumeration. Pair symmetric structures before simplifying. Do not admit extraneous solutions by skipping substitution back, ignore the range supplied by $\Delta\geq0$, or declare an even solution count without the norm-equation argument.

### 9.6 Floor Functions and Complete Residue Systems

For an inequality required in every residue class, change variables so that the index runs from $1$ to $p-1$. Over a prime modulus $p$, multiplication by a nonzero element permutes all nonzero residues:

1. After replacing $k$ with $j=k+1$, the residues of $n\cdot j\pmod p$ still run through every nonzero residue.
2. Rewrite the original inequality as a requirement that, for every $j$, the residue is at least a linear threshold. This is equivalent to a common upper bound on a floor quotient.
3. The admissible $n$ are exactly the decreasing sequence formed by flooring $p$ divided by consecutive integers; the requested rank locates the corresponding floor value.

**Key tools:** If $\gcd(n,p)=1$, then

$$\{n\cdot1,n\cdot2,\ldots,n\cdot(p-1)\}\pmod p=\{1,2,\ldots,p-1\}.$$

A remainder equals the original quantity minus the modulus times its floor quotient. Use

$$\{x\}=x-\lfloor x\rfloor,\qquad \lfloor x+n\rfloor=\lfloor x\rfloor+n$$

for integer $n$, and, when $\gcd(n,p)=1$,

$$\sum_{k=0}^{p-1}\left\lfloor\frac{nk}{p}\right\rfloor=\frac{(n-1)(p-1)}2.$$

The core transformation is the interchange of the traversal index with the complete-residue-system permutation. For a “k-th largest” question, first write the full solution sequence and then locate the rank. Check the prerequisite $n<p$ when invoking multiplication by $n$ as a complete system; do not reverse an inequality while rewriting a residue lower bound; and account for repeated values in a floor sequence.

## 10. Competition Extension: Core Theorems of Plane Geometry

This section adds concrete theorems and tools frequently used in competition plane geometry but not previously covered by the manual.

### 10.1 Tangent–Chord Angle Theorem

**Theorem:** The angle between a tangent to a circle and a chord through the point of tangency equals the inscribed angle subtended by that chord.

**Corollary:** From an exterior point, two tangents to a circle have equal angles with the chord joining their tangency points; the angle subtended by that chord at the exterior point equals half the central angle subtending the minor arc between the two tangency points.

**Competition use:** In tangent–chord–inscribed-angle configurations, this theorem is the central tool for angle equalities and is often combined with arc-midpoint properties.

### 10.2 Pole, Polar, and La Hire's Theorem

**Definition:** For an exterior point $P$ of a circle $O$, the polar of $P$ is the line joining the two tangency points of the tangents from $P$ to $O$. Conversely, $P$ is the pole of that line.

**La Hire's theorem:** Point $A$ lies on the polar of point $B$ if and only if point $B$ lies on the polar of point $A$.

**Degenerate case:** When a point lies on the circle, its polar is the tangent at that point.

**Competition use:** Start a polar-line problem from the degeneration “point on the circle $\Rightarrow$ polar is tangent,” then analyze the general position. Determine whether a locus is a full circle, a family of lines, or a degenerate singleton from both special and general points. If the distances from the orthocenter to three vertices equal the corresponding circle radii, the orthocenter lies on all three circles; this can test whether the circumcircle of the triangle formed by the three tangents passes through that special point.

### 10.3 Radical Axes and Coaxal Circle Systems

**Definition:** The radical axis of two circles is the line of points having equal power with respect to them. If the pairwise radical axes of three circles concur, the point is their radical center.

**Coaxality criterion:** Three circles have exactly two common points if and only if every pair intersects in the same pair of points, equivalently the circles are coaxal. Test this by concurrence of radical axes or coincidence of common chords.

**Competition use:** For a parameterized family of circles, write the coaxality condition as an algebraic equation and solve every parameter value. The number of solutions corresponds to special geometric positions of the parameter, such as an internal-division ratio or symmetric degeneration, each of which must be checked. Do not confuse three circles sharing one point with coaxality, which gives two common points.
