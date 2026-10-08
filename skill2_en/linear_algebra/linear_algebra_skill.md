# Linear Algebra Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: polynomials, matrices, determinants, linear spaces, quadratic forms, eigenvalues, algebraic numbers, \(\ell_2\) states, and max-plus structures.
- Do not take over: structural problems on groups/rings/fields/Galois theory belong to abstract algebra; real-variable limits, convergence, and differential inequalities belong to mathematical analysis.
- Verification contract: retain coefficient field, dimension, multiplicity, invertible transformations, and degenerate cases; matrix/polynomial results must be substituted back into the original object.

## Preface

This manual systematically organizes core higher-algebra solution skills around 20 typical exercises (14 computational and 6 proof problems, with difficulty ratio \(2:6:2\)).

---

## I. Polynomial Theory

### Core Concepts

- **Polynomial ring** \(F[x]\): all univariate polynomials with coefficients in number field \(F\).
- **Divisibility**: \(f(x)\mid g(x)\iff\) there is \(h(x)\) such that \(g=f\cdot h\).
- **Greatest common divisor**: \(\gcd(f,g)\), found by Euclidean division.
- **Coprime**: \(\gcd(f,g)=1\), i.e. no nontrivial common factor.
- **Irreducible polynomial**: degree \(\ge1\) and cannot factor into two lower-degree polynomials.

### Common Formulas and Theorems

| Name | Content |
|---|---|
| Division algorithm | \(f(x)=q(x)g(x)+r(x)\), \(\deg r<\deg g\) |
| Bézout theorem | \((f,g)=1\iff\exists u,v:uf+vg=1\) |
| Factor theorem | \(x-a\mid f(x)\iff f(a)=0\) |

### Standard Solution Steps

**Type A: polynomial division**

1. Use long division or synthetic division.
2. Check that remainder degree is \(<\) divisor degree.
3. Use remainder theorem \(r=f(a)\) for a quick check.

**Type B: find a greatest common divisor**

1. Perform Euclidean division.
2. Normalize the last nonzero remainder; it is the gcd.

**Type C: prove coprimality**

1. Assume a common divisor \(d\) of degree \(\ge1\) exists.
2. Use divisibility and coprimality conditions to derive contradiction.

### Common Pitfalls

- Always check that **remainder degree** is strictly below divisor degree.
- A greatest common divisor must be **monic**.
- “Irreducible” depends on coefficient field: \(x^2+1\) is irreducible in \(\mathbb R[x]\), but reducible in \(\mathbb C[x]\).

### Techniques

- Synthetic division operates only on coefficients and is more than three times faster than long division.
- When finding a gcd, intermediate remainders may be multiplied by a nonzero constant to simplify calculations.
- Standard coprimality proof: contradiction + divisibility property of irreducible polynomials.

### Exam Techniques

- **Power-sum/moment conditions**: on seeing \(\sum P(a_i)=\text{const}\), first convert it into a polynomial divisibility relation using Lagrange interpolation or factorization, then split cases. Construct \(Q(x)=\prod(x-a_i)\) as the auxiliary polynomial.
- **Polynomial-degree control**: in a functional equation, first substitute special values (\(x=0,\pm1\), etc.) to shrink unknowns; then use finite degree (\(\deg f\le n\)) to turn an infinite-dimensional problem into finite undetermined coefficients.
- **Factorization contradiction**: if polynomial values at all integers satisfy a sum condition, use \(g(x)=f(x+1)-f(x)\) to lower degree and argue iteratively.

### Frequent Exam Pitfalls

- Always check that **remainder degree** is strictly below divisor degree.
- A greatest common divisor must be **monic**.
- “Irreducible” depends on coefficient field: \(x^2+1\) is irreducible in \(\mathbb R[x]\), but reducible in \(\mathbb C[x]\).
- **Repeated roots and derivatives**: \(f\) has a repeated root \(\iff\gcd(f,f')\ne1\); failing to differentiate to detect repeated roots is a frequent loss of marks.
- **Coefficient form for repeated roots in partial fractions**: in partial fractions of \(F'/F\), a root of multiplicity \(k\) contributes \(\frac{k}{x-a}\), not \(\frac1{(x-a)^k}\). Confusing them leads to incorrect real-root counts.

### Competition Extension: Polynomialization of Functional Equations

**Concept:** many functional equations, such as \(f(x+y)=f(x)+f(y)+\text{polynomial terms}\), ultimately reduce to polynomials. The core strategy uses special-value substitution and differences to remove nonpolynomial components.

**Key formulas:**

- Forward difference: \(\Delta f(x)=f(x+1)-f(x)\); the \(k\)-th difference eliminates a degree-\(k\) polynomial.
- If \(f\) satisfies \(\Delta^nf(x)\equiv0\), then \(f\) is a polynomial of degree \(<n\).

**Solution steps:**

1. Substitute special values such as \(x=y=0\) to eliminate unknown quantities.
2. Assign a special value to \(y\), e.g. \(y=1\), to obtain a recurrence.
3. Iteratively use differences to lower degree and prove the solution is polynomial.
4. Solve by undetermined coefficients.

**Pitfall:** verification only at rational points is insufficient to establish a polynomial identity. Add continuity or a polynomial-degree bound. Using interpolation before proving the function is polynomial makes the conclusion incomplete.

### Competition Extension: Logarithmic Differentiation and Real-Root Determination

**Concept:** use the partial-fraction expansion of logarithmic derivative \(F'(x)/F(x)\) to relate the number of real roots of \(F\) to poles of that expansion.

**Core principle:**
\[
F(x)=c\prod_{i=1}^{k}(x-a_i)^{m_i}\prod_{j=1}^{l}((x-b_j)^2+c_j^2)^{n_j},
\]
\[
\frac{F'(x)}{F(x)}=\sum_{i=1}^{k}\frac{m_i}{x-a_i}+\sum_{j=1}^{l}\frac{2n_j(x-b_j)}{(x-b_j)^2+c_j^2}.
\]

- Every real root of multiplicity \(m\) corresponds to \(\frac{m}{x-a}\).
- Sign changes of \(F'/F\) can determine real-root intervals.

**Solution steps:**

1. Calculate \(F'(x)\) and \(\gcd(F,F')\) to eliminate repeated factors.
2. Expand \(F'/F\) in partial fractions after removing repetitions.
3. Determine number of real roots by a Sturm sequence or sign analysis.

**Pitfall:** a repeated root contributes \(\frac{m}{x-a}\), with \(m\) its multiplicity, not \(\frac1{(x-a)^m}\). The sign of a second derivative distinguishes local behavior of repeated and simple roots.

### Competition Extension: Polynomial Invariants and Parameter-Transformation Groups

**Concept:** given a parameter-transformation group, such as affine transformations \(x\mapsto ax+b\) acting on polynomials, find combinations of polynomial coefficients invariant under that action.

**Key concepts:**

- **Discriminant** \(\Delta(f)\): product of squared differences of roots. It is invariant under translation \(x\mapsto x+c\), and is multiplied by \(a^{n(n-1)}\) under scaling \(x\mapsto ax\).
- **Resultant** \(\operatorname{Res}(f,g)\): a necessary and sufficient condition that \(f\) and \(g\) share a root.
- Number of **basic invariants** = number of parameters \(-\) dimension of transformation group.

**Solution steps:**

1. Determine the action of transformation group \(G\) on coefficient space.
2. Calculate orbit dimension under \(G\).
3. Construct a basic invariant set of dimension = number of coefficients \(-\) orbit dimension.
4. Verify that invariants remain unchanged under \(G\).

**Pitfall:** the number of invariants is coefficient-space dimension minus group dimension (not orbit dimension). The discriminant \(a^{2n-2}\prod_{i<j}(r_i-r_j)^2\) generally changes under \(x\mapsto\frac{ax+b}{cx+d}\); it is considered invariant only within Möbius-transformation invariant theory.

### Competition Extension: Elimination and Counting for Symmetric Polynomial Systems

**Concept:** for cyclically symmetric systems \(\{f(x_1,\ldots,x_n)=0,f(x_2,\ldots,x_1)=0,\ldots\}\), use symmetry for elimination and Bézout’s theorem for an upper bound on number of solutions.

**Core methods:**

- **Elementary-symmetric-polynomial substitution**: let \(s_1=\sum x_i\), \(s_2=\sum_{i<j}x_ix_j\), \(\ldots\), \(s_n=\prod x_i\).
- **Bézout upper bound**: if \(n\) polynomial equations in \(n\) variables all have degree \(d\), number of solutions is \(\le d^n\), counting multiplicities.
- **Gröbner-basis elimination**: use a computer algebra system to eliminate variables successively and obtain a univariate equation.

**Solution steps:**

1. Identify symmetry of the system (cyclic or complete).
2. Convert it to equations in elementary symmetric polynomials.
3. Eliminate variables or use Newton identities.
4. Solve the resulting univariate equation, then substitute back for every solution.

**Pitfall:** symmetry may be used only when every equation remains unchanged after cyclic permutation. Partial symmetry (such as symmetry in only two variables) cannot be simplified as complete symmetry. Bézout’s bound counts multiplicities, so the number of distinct actual solutions may be much smaller.

## II. Determinants

### Core Principles

- A determinant changes sign when two rows (or columns) are interchanged; adding a multiple of one row to another leaves it unchanged.
- A triangular matrix has determinant equal to the product of its diagonal entries.
- \(\det(AB)=\det(A)\det(B)\), and \(A\) is invertible if and only if \(\det A\ne0\).

### Verification

When simplifying a determinant by row operations, record whether an operation changes sign or introduces a scalar factor; substitute any claimed factorization or characteristic expression back into the original determinant.

- Multiplying one row by \(c\) multiplies the determinant by \(c\); a zero row or two proportional rows force the determinant to be \(0\).
- Laplace expansion must retain cofactors \((-1)^{i+j}M_{ij}\); expanding along a sparse row or column reduces arithmetic.

### Core Concepts

- A determinant is an alternating multilinear map from an \(n\times n\) matrix to the base field.
- Vandermonde determinant: \(\prod_{1\le i<j\le n}(x_j-x_i)\).
- Characteristic polynomial: \(p_A(\lambda)=\det(\lambda I-A)\).

### Common Formulas

| Name | Content |
|---|---|
| Vandermonde | \(\begin{vmatrix}1&1&1\\x_1&x_2&x_3\\x_1^2&x_2^2&x_3^2\end{vmatrix}=\prod_{i<j}(x_j-x_i)\) |
| Multiplication | \(\det(AB)=\det(A)\det(B)\) |
| Transpose invariance | \(\det(A^T)=\det(A)\) |
| Row interchange | Interchanging two rows reverses sign |
| Row multiple addition | Adding a scalar multiple of one row to another leaves determinant unchanged |

### Standard Steps for a Determinant

1. Identify structure: Vandermonde, tridiagonal, or block form.
2. Simplify using row operations, preferentially row-multiple addition.
3. Use Laplace expansion or a formula.
4. For parameters, factor the expanded polynomial by testing roots.

### Pairwise-Product-Sum Inequality Method

\[
\sum_{i=1}^na_i^2=\frac1n\left(\sum_{i=1}^na_i\right)^2+\frac1n\sum_{1\le i<j\le n}(a_i-a_j)^2.
\]
If \(a_1\le\cdots\le a_n\), \(b_1\le\cdots\le b_n\), then for every permutation \(\sigma\),
\[
\sum_{i=1}^na_ib_{n-i+1}\le\sum_{i=1}^na_ib_{\sigma(i)}\le\sum_{i=1}^na_ib_i.
\]
Use an appropriate identity to rewrite the target as \(\sum a_ib_i\) or \(\sum a_i^2\), apply rearrangement or Cauchy–Schwarz, then state equality conditions. Note \(\sum_{i\ne j}a_ia_j=2\sum_{i<j}a_ia_j\).

## III. Matrices

### Core Concepts

- \(A\) is invertible iff \(\det A\ne0\) iff \(\operatorname{rank}A=n\).
- Rank is the number of vectors in a maximal independent subset of row (or column) vectors.
- Jordan normal form is the simplest block-diagonal form under similarity.
- \(A\) is diagonalizable iff every eigenvalue’s algebraic and geometric multiplicities agree.
- Every real symmetric matrix is orthogonally diagonalizable.

### Common Formulas

| Name | Content |
|---|---|
| \(2\times2\) inverse | \(\begin{pmatrix}a&b\\c&d\end{pmatrix}^{-1}=\frac1{ad-bc}\begin{pmatrix}d&-b\\-c&a\end{pmatrix}\) |
| Row reduction for inverse | \([A\mid I]\xrightarrow{\text{row operations}}[I\mid A^{-1}]\) |
| Sylvester inequality | \(\operatorname{rank}(A)+\operatorname{rank}(B)-n\le\operatorname{rank}(AB)\) |
| Simultaneous diagonalization | \(AB=BA\) and both diagonalizable \(\implies\) simultaneously diagonalizable |

To decide diagonalizability, find the characteristic polynomial and all eigenvalues, compare algebraic and geometric multiplicities, using \(d_i=n-\operatorname{rank}(\lambda_iI-A)\) for geometric multiplicity. Only row operations may be used in \([A\mid I]\) inversion; Jordan-block order is nonunique but block structure is unique.

## IV. Linear Systems

- Homogeneous \(Ax=0\) has a nonzero solution iff \(\operatorname{rank}(A)<n\).
- Nonhomogeneous \(Ax=b\) is solvable iff \(\operatorname{rank}(A)=\operatorname{rank}([A\mid b])\).
- A fundamental solution set is a basis of the solution space, containing \(n-\operatorname{rank}(A)\) independent vectors.
- General solution = one particular solution + homogeneous solution.

For a fundamental solution set, reduce the coefficient matrix to RREF, identify pivot/free columns, and set each free variable in turn to \(1\) with other free variables \(0\). Prefer row reduction over Cramer’s rule and substitute every basis vector back for verification.

### Competition Extension: Binary Fields and Linear Models of Graph States

Over \(\mathbb F_2\) (mod-2 arithmetic), graph edge-flip operations become linear systems. A graph with \(m\) edges has an \(m\)-dimensional \(\mathbb F_2\)-state vector; flipping twice returns to the original state because \(1+1=0\). Reachability becomes solvability of \(Ax=b\) over \(\mathbb F_2\), and there are \(2^{m-\operatorname{rank}(A)}\) solutions. Addition equals subtraction, Gaussian elimination uses XOR only, and reachability is equivalent to \(b\in\operatorname{Col}(A)\). Do not import real-field intuitions: coefficients are only \(0,1\), so linear combinations have finitely many possibilities.

## V. Quadratic Forms

- A quadratic form is \(f(x)=x^TAx\), with \(A\) real symmetric.
- Completing squares reduces it to a sum of squares.
- \(f(x)>0\) for every \(x\ne0\) iff all leading principal minors are \(>0\).
- By the inertia theorem, positive and negative inertia indices are uniquely determined.

For completing squares, first complete variables having square terms; if every \(a_{ii}=0\), create square terms using \(x_i=y_i+y_j,\ x_j=y_i-y_j\). In \(f=d_1y_1^2+\cdots+d_ry_r^2\), number of positive coefficients is positive inertia index \(p\). Positive semidefiniteness is not established merely by nonnegative leading principal minors: that condition is necessary but not sufficient. Every linear substitution used in completing squares must be invertible.

## VI. Linear Spaces and Linear Transformations

- A basis is a maximal independent set, and \(\dim V\) is unique.
- Coordinates are coefficients representing a vector in an ordered basis.
- \(\operatorname{Ker}(\sigma)=\{v:\sigma(v)=0\}\); \(\operatorname{Im}(\sigma)=\{\sigma(v):v\in V\}\).
- Rank–nullity: \(\dim\operatorname{Ker}(\sigma)+\dim\operatorname{Im}(\sigma)=\dim V\).

Find coordinates by solving \(\beta=x_1\alpha_1+\cdots+x_n\alpha_n\); find the kernel by solving \(Ax=0\). To prove independence, derive each \(c_i=0\) from \(c_1v_1+\cdots+c_kv_k=0\). Coordinate order matters, and nullity is \(n-\operatorname{rank}(A)\).

### Max-Plus Semilattices and Vector Closure

In \(\mathbb R^n\), closure generated by vector addition and componentwise \(\max\) (or \(\min\)) forms a max-plus/tropical semimodule with lattice and semilattice features. Define \(a\oplus b=\max(a,b)\), \(a\otimes b=a+b\). From \(S=\{v_1,\ldots,v_k\}\), closure is all vectors generated by repeated addition and componentwise maximum. If finitely generated, every vector has the max-plus combination \(\bigoplus_i(\lambda_i\otimes v_i)=\max_i\{\lambda_i+v_i\}\). Determine closure, use tropical Carathéodory finite-generation, find a minimal generator set, and verify the representation. Minimal generating sets are generally nonunique, \(\max\) has no cancellation, and max-plus independence means no vector is max-plus generated by the rest.

## VII. Euclidean Spaces

- An inner product is a bilinear form satisfying symmetry, linearity, and positive definiteness.
- Gram–Schmidt subtracts projections successively:
\[
\beta_k=\alpha_k-\sum_{i=1}^{k-1}\frac{\langle\alpha_k,\beta_i\rangle}{\langle\beta_i,\beta_i\rangle}\beta_i.
\]
- An orthogonal transformation satisfies \(Q^TQ=I\), preserves inner products and lengths, and has \(\det Q=\pm1\).

The denominators \(\langle\beta_i,\beta_i\rangle\) cannot be zero; an orthogonal transformation here must be a real matrix.

## VIII. Eigenvalues and Diagonalization

- \(Av=\lambda v\), \(v\ne0\); algebraic multiplicity is multiplicity in characteristic polynomial, while geometric multiplicity is \(\dim\operatorname{Ker}(\lambda I-A)\).
- Diagonalizable iff every eigenvalue has equal algebraic and geometric multiplicities.
- \(\sum\lambda_i=\operatorname{tr}A\), \(\prod\lambda_i=\det A\), and Cayley–Hamilton gives \(p_A(A)=0\).
- \(A\) is invertible iff \(0\) is not an eigenvalue; \(A^{-1}v=\lambda^{-1}v\).

Triangular-matrix eigenvalues are diagonal entries. Check candidates with trace and determinant, then check that the characteristic polynomial splits and every multiplicity matches. 

## IX. General Methodology

More than \(70\%\) of higher-algebra problems reduce to: standard forms (equivalence/rank, similarity/diagonalization/Jordan, congruence/quadratic forms); linear systems (augmented matrix \(\to\) RREF \(\to\) free variables \(\to\) fundamental solutions); and invariants (rank, determinant, trace, characteristic and minimal polynomials). For every matrix question ask: under which transformation is it meaningful (equivalence, similarity, congruence)? What is invariant? Can it be diagonalized?

| Calculation | Verification |
|---|---|
| Inverse matrix | \(AA^{-1}=I\) |
| Eigenvalues | \(\sum\lambda_i=\operatorname{tr}A\) |
| Eigenvector | Substitute \(Av=\lambda v\) |
| Fundamental solution set | Substitute into original system |
| Gram–Schmidt result | Check pairwise inner products are zero |
| Rank | Independently compute row- and column-echelon forms |

## X. Exercise-Solution Index

| idx | Topic | Key method | Difficulty |
|:---:|---|---|:---:|
| 0 | Polynomial | Division, synthetic division, remainder theorem | Easy |
| 1 | Determinant | Vandermonde \(\prod(x_j-x_i)=2\) | Easy |
| 2 | Matrix | \([A\mid I]\to[I\mid A^{-1}]\) | Easy |
| 3 | Polynomial | Euclidean algorithm for gcd | Intermediate |
| 4 | Determinant | Parameter expansion \(\to\) characteristic-polynomial factorization | Intermediate |
| 5 | Linear systems | RREF \(\to\) free variables \(\to\) fundamental solutions | Intermediate |
| 6 | Matrix | Row echelon form, nonzero rows \(=2\) | Intermediate |
| 7 | Quadratic form | \(f=(x_1+x_2)^2+(x_2+x_3)^2,p=2\) | Intermediate |
| 8 | Linear space | Coordinates \((-1,2,1)\) | Intermediate |
| 9 | Linear transformation | Kernel \(Ax=0\), basis, \(\dim=2\) | Intermediate |
| 10 | Diagonalization | \(\lambda=1\) double, geometric multiplicity \(1<2\): not diagonalizable | Intermediate |
| 11 | Euclidean space | Gram–Schmidt + normalization | Intermediate |
| 12 | Jordan form | Nilpotency index \(=3\), one block \(J_3(1)\) | Hard |
| 13 | Quadratic form | Leading minors \(1,3,2>0\): positive definite, \(p=3\) | Hard |
| 14 | Linear space | Independence: linear combination \(=0\Rightarrow\) all coefficients zero | Easy |
| 15 | Eigenvalue | Invertible \(\Rightarrow\lambda\ne0\), inverse eigenvalue \(\lambda^{-1}\) | Intermediate |
| 16 | Euclidean space | \((Qx)^T(Qy)=x^TQ^TQy=x^Ty\) | Intermediate |
| 17 | Linear transformation | Rank–nullity and extending kernel basis | Intermediate |
| 18 | Polynomial | Contradiction + irreducible-factor divisibility | Hard |
| 19 | Matrix | Commuting real symmetric matrices: simultaneous diagonalization | Hard |
