# Functional Analysis Problem-Solving Skill

## Scope and Routing Conventions

- Applies to Banach and Hilbert spaces, bounded operators, spectra, weak convergence, compact operators, and functionals.
- Formal adjoints of differential operators and boundary terms route to partial differential equations; questions asking only about Cauchy sequences or the definition of completeness route to mathematical analysis/topology.
- Verification contract: every vector and operator must belong to the space specified in the problem; distinguish point, continuous, and residual spectrum, and state the conditions for a bounded inverse.

## Frequent Errors and Conventions (Judge Feedback, 2026-07-07)

- **Three-way spectral classification in this problem bank:** Assume $\lambda I-T$ is injective, i.e. $\lambda\notin\sigma_p$. If $(\lambda I-T)^{-1}$ is **unbounded**, then $\lambda\in\sigma_c$ (continuous spectrum). It belongs to $\sigma_r$ (residual spectrum) only when $(\lambda I-T)^{-1}$ is **bounded** but its range is not dense. Do not classify a spectral point as residual merely because its range is not dense.
- **Spectrum of a compact operator:** On an infinite-dimensional space a compact operator always has $0\in\sigma(T)$, and every nonzero spectral point is an eigenvalue. If $0$ is not an eigenvalue, then $T^{-1}$ is unbounded and $0$ lies in the **continuous spectrum**. The standard example

$$T(x_1,x_2,x_3,\ldots)=(0,x_1,\tfrac{x_2}{2},\tfrac{x_3}{3},\ldots)$$

is a Hilbert–Schmidt compact weighted shift. Since $Tx=\lambda x$ has only the zero solution, $\sigma_p=\varnothing$, $\sigma(T)=\{0\}$, $\sigma_c=\{0\}$, and $\sigma_r=\varnothing$.
- A formal solution of an eigenvalue equation is not an eigenvector until it is verified to belong to $\ell^2$ (or the specified space).

---

## Part I: Knowledge Modules

### Module 1: Completeness of a Metric Space

Completeness means that every Cauchy sequence converges to a point inside the space. Every norm on $\mathbb R^n$ is complete because finite-dimensional normed spaces are complete. $\mathbb Q$ is incomplete because a rational Cauchy sequence can converge to an irrational number. To prove incompleteness, choose a rational sequence converging to an irrational number, for example $(1+1/n)^n\to e$, verify it is Cauchy, and verify that its limit is not in the space. *(Exercise idx 0.)*

### Module 2: Fixed Points by the Contraction Principle

Banach's fixed-point theorem says that a contraction on a complete metric space has a unique fixed point. A standard condition is $|f'(x)|\leq k<1$. Verify that the domain is complete (a closed interval is complete), maximize $|f'(x)|$ on the interval, establish that the maximum is less than $1$, then solve $x=f(x)$. *(Exercise idx 1.)*

### Module 3: Norm Equivalence

All norms on a finite-dimensional space are equivalent. In particular,

$$\|x\|_\infty\leq\|x\|_1\leq n\|x\|_\infty.$$

For optimal constants, find the smallest $C$ with $\|x\|_{new}\leq C\|x\|_{old}$ and the largest $c$ with $c\|x\|_{old}\leq\|x\|_{new}$. First prove the general inequality, then give an extremal vector attaining equality. *(Exercise idx 2.)*

### Module 4: Inner-Product Spaces and Orthogonal Decomposition

$$W^\perp=\{x:\langle x,w\rangle=0,\ \forall w\in W\}.$$

Write the homogeneous system whose rows impose inner product $0$ with a basis of $W$, solve it for a basis of $W^\perp$, use Gram–Schmidt if needed, and normalize to obtain an orthonormal basis. *(Exercise idx 3.)*

### Module 5: Norm of a Bounded Linear Operator in Finite Dimension

$$\|A\|=\sqrt{\rho(A^TA)}=\sqrt{\lambda_{\max}(A^TA)}.$$

Compute $A^TA$, find its eigenvalues, and take the square root of the largest one. *(Exercise idx 4.)*

### Module 6: Norm of an Integral Operator

For $(Kf)(x)=\int k(x,y)f(y)\,dy$, a separable kernel $k(x,y)=\phi(x)\psi(y)$ makes $K$ rank one. The stated norm is

$$\|K\|=\|k\|_{L^2}=\sqrt{\iint|k(x,y)|^2\,dx\,dy}.$$

*(Exercise idx 5.)*

### Module 7: Computing an Adjoint

The defining identity is $\langle Tx,y\rangle=\langle x,T^*y\rangle$. For the right shift

$$(x_1,x_2,\ldots)\mapsto(0,x_1,x_2,\ldots),$$

the adjoint is the left shift $(y_1,y_2,\ldots)\mapsto(y_2,y_3,\ldots)$. *(Exercise idx 6.)*

### Module 8: Orthogonal Projection

$P_Wv$ is the orthogonal projection of $v$ onto $W$. If $W$ has an orthonormal basis $\{e_i\}$, then

$$P_Wv=\sum\langle v,e_i\rangle e_i.$$

*(Exercise idx 7.)*

### Module 9: Self-Adjoint Operators

$T$ is self-adjoint if and only if $T=T^*$. Under the standard inner product on $\mathbb R^n$, this is equivalent to its matrix being symmetric. *(Exercise idx 8.)*

### Module 9.1: Formal Adjoint of a Differential Operator

For an $L^2$ differential operator $L$, its formal adjoint satisfies $\langle Lf,g\rangle=\langle f,L^*g\rangle$ for all compactly supported smooth $f,g$; compact support removes all boundary terms. For

$$Lu=-\sum_{i,j}\partial_i(a_{ij}\partial_j u)+\sum_i b_i\partial_i u+cu,$$

with real smooth $a_{ij},b_i,c$, two integrations by parts send $\partial_i(a_{ij}\partial_j u)$ to $\partial_j(a_{ij}\partial_i g)$; one integration by parts sends $b_i\partial_i u$ to $-\partial_i(b_i g)$; and $cu$ remains $cg$. Thus

$$L^*g=-\sum_{i,j}\partial_j(a_{ij}\partial_i g)-\sum_i\partial_i(b_i g)+cg.$$

Write the inner-product identity first and integrate term by term. Track whether a coefficient remains inside a derivative; the common errors are omitting the minus sign in the first-order term, reversing a derivative transfer, or integrating the second-order term only once. *(Formal-adjoint exercise.)*

### Modules 10–20

**Compact operators:** An operator is compact when it maps bounded sets to relatively compact sets. Sufficient conditions are finite rank, Hilbert–Schmidt ($\sum\|Te_n\|^2<\infty$), and an operator-norm limit of compact operators. *(idx 9.)*

**Spectral radius:** $r(A)=\max\{|\lambda|:\lambda\in\sigma(A)\}$. In finite dimension it is the largest absolute eigenvalue; for an upper-triangular matrix, the eigenvalues are its diagonal entries. *(idx 10.)*

**Riesz representation:** Every bounded linear functional $f$ on a Hilbert space has a unique $u$ with $f(x)=\langle x,u\rangle$. From $f(x)=\sum a_ix_i$, read $u=(a_1,a_2,\ldots)$. *(idx 11.)*

**Fredholm alternative:** For $\phi-\lambda K\phi=f$ with compact $K$, either the homogeneous equation has only the zero solution, in which case the inhomogeneous equation has a unique solution for every $f$, or the homogeneous equation has a nonzero solution (an eigenvalue case). *(idx 12.)*

**Closed operators and the closed-graph theorem:** $\Gamma(T)=\{(x,Tx):x\in D(T)\}$ is closed in $X\times Y$. If $T$ is closed and $D(T)$ is Banach, then $T$ is bounded. Hence, if $Te_n=ne_n$ is unbounded, $D(T)\ne\ell^2$. *(idx 13.)*

**Banach versus Hilbert:** A Banach space is complete and normed; a Hilbert space is Banach and its norm satisfies

$$\|x+y\|^2+\|x-y\|^2=2(\|x\|^2+\|y\|^2).$$

$C[0,1]$ with $\|\cdot\|_\infty$ is Banach but not Hilbert; with $\|\cdot\|_2$ it is neither Banach nor Hilbert; $\mathbb R^n$ with $\|\cdot\|_1$ is Banach but not Hilbert. *(idx 14.)*

**Uniform boundedness:** If $X$ is Banach and $\{T_\alpha\}\subset B(X,Y)$ is pointwise bounded, $\sup_\alpha\|T_\alpha x\|<\infty$ for every $x$, then $\sup_\alpha\|T_\alpha\|<\infty$. On incomplete $c_{00}$, $T_nx=nx_n$ is pointwise bounded but $\|T_n\|=n\to\infty$. *(idx 15.)*

**Weak and strong convergence:** Strong convergence is $\|x_n-x\|\to0$; weak convergence is $\langle x_n,y\rangle\to\langle x,y\rangle$ for all $y$. Strong implies weak, not conversely: the standard orthonormal basis $e_n$ of $\ell^2$ converges weakly, but not strongly, to $0$. *(idx 16.)*

**Arzelà–Ascoli:** $F\subset C[a,b]$ is relatively compact iff it is uniformly bounded and equicontinuous. Verify $\sup_{f\in F}\|f\|_\infty<\infty$ and, for every $\varepsilon>0$, find $\delta>0$ with $|x-y|<\delta\Rightarrow |f(x)-f(y)|<\varepsilon$ for every $f\in F$; uniformly bounded derivatives suffice. *(idx 17.)*

**Hahn–Banach:** A bounded linear functional on a subspace extends to the whole space with the same norm. Pure algebraic extension always exists, while norm-preserving extension uses Hahn–Banach and, in infinite dimension, Zorn's lemma. *(idx 18.)*

**Spectral partition:** $\sigma(T)=\sigma_p(T)\cup\sigma_c(T)\cup\sigma_r(T)$. For a compact operator, every nonzero spectral point is a finite-multiplicity eigenvalue, $0$ is in the spectrum in infinite dimension, and nonzero spectral points can accumulate only at $0$. *(idx 19.)*

## General Methodology

Identify the space first: finite dimensionality gives completeness and norm equivalence, whereas infinite-dimensional completeness needs proof. For an operator, distinguish finite from infinite dimension; use matrix tools in the former and compactness/boundedness in the latter. Under the standard inner product, self-adjointness is symmetry. In finite dimension spectrum equals the eigenvalue set; for compact operators $0$ is spectral and nonzero spectrum consists of eigenvalues; spectral radius is the largest absolute eigenvalue.

## Part III: Exercise Index

| idx | Problem keyword | Topic | Difficulty |
|-----|-----------------|-------|------------|
| 0 | Completeness of $\mathbb Q$ | completeness test | easy |
| 1 | Fixed point of $f(x)=(x+2/x)/2$ | contraction principle | easy |
| 2 | Equivalence of $\|\cdot\|_1$ and $\|\cdot\|_\infty$ | norm equivalence | easy |
| 3 | Orthonormal basis of $W^\perp$ | orthogonal decomposition | medium |
| 4 | Operator norm $\|A\|$ | finite-dimensional operator norm | medium |
| 5 | Integral-operator norm | integral operator | medium |
| 6 | Adjoint of right shift | adjoint operator | medium |
| 7 | Orthogonal projection | orthogonal projection | medium |
| 8 | Self-adjoint operator | self-adjointness | medium |
| 9 | Finite rank implies compact | compact operator | medium |
| 10 | Spectral radius | spectral radius | medium |
| 11 | Riesz representation | Riesz theorem | medium |
| 12 | Fredholm equation | Fredholm alternative | hard |
| 13 | Closed operator | closed-graph theorem | hard |
| 14 | Banach/Hilbert classification | space properties | easy |
| 15 | Uniform boundedness | Banach–Steinhaus | medium |
| 16 | Weak versus strong convergence | convergence | medium |
| 17 | Arzelà–Ascoli | compactness test | medium |
| 18 | Hahn–Banach | extension theorem | hard |
| 19 | Spectral classification | spectral theory | hard |

## Competition Extension 1: Fourier Transform Linearity, Translation, and Basic Kernels

The Fourier transform $\mathcal F$ is linear on $L^1(\mathbb R)\cap L^2(\mathbb R)$:

$$\mathcal F[af+bg](\xi)=a\mathcal F[f](\xi)+b\mathcal F[g](\xi).$$

Its translation and modulation rules are

$$\mathcal F[f(x-x_0)](\xi)=e^{-i\xi x_0}\mathcal F[f](\xi),$$

$$\mathcal F[e^{i\xi_0x}f(x)](\xi)=\mathcal F[f](\xi-\xi_0).$$

The translation phase $e^{-i\xi x_0}$ has modulus $1$, so translation does not change the spectrum modulus: $|\mathcal F[f(x-x_0)]|=|\mathcal F[f]|$.

| Time-domain $f(x)$ | Frequency-domain $\hat f(\xi)$ | Correspondence |
|:---|:---|:---|
| One-sided exponential $e^{-ax}H(x)$, $a>0$ | $1/(a+i\xi)$ | one-sided exponential $\leftrightarrow$ complex Lorentz type |
| Two-sided exponential $e^{-a|x|}$, $a>0$ | $2a/(a^2+\xi^2)$ | two-sided exponential $\leftrightarrow$ real Lorentz type |
| Gaussian $e^{-ax^2}$, $a>0$ | $\sqrt{\pi/a}\,e^{-\xi^2/(4a)}$ | Gaussian $\leftrightarrow$ Gaussian |
| Rectangle $\chi_{[-T,T]}(x)$ | $2\sin(T\xi)/\xi$ | rectangle $\leftrightarrow$ sinc |

Here $H(x)$ is the Heaviside step function. In particular,

$$\mathcal F[e^{-ax}H(x)](\xi)=\int_0^\infty e^{-(a+i\xi)x}\,dx=\frac1{a+i\xi},$$

whose real part $a/(a^2+\xi^2)$ is the standard Lorentzian line shape. Translation follows by $u=x-x_0$:

$$\mathcal F[f(x-x_0)](\xi)=\int_{-\infty}^{\infty}f(u)e^{-i\xi(u+x_0)}\,du=e^{-i\xi x_0}\hat f(\xi).$$

Use translation to simplify shifted integral transforms, connect the oscillatory phase as $|\xi|\to\infty$ with the Riemann–Lebesgue lemma, and use the kernel table in Fourier solutions of the heat and wave equations.

## Competition Extension 2: Cauchy Sequences and Complete Metric Spaces

A sequence $\{x_n\}$ in a metric space $(X,d)$ is Cauchy if

$$\forall\varepsilon>0,\ \exists N,\ \forall m,n>N:\ d(x_m,x_n)<\varepsilon.$$

The space is complete if every Cauchy sequence converges to a point of that space.

### Completeness Results Used in Functional Analysis

1. Every finite-dimensional normed space is complete; in particular $\mathbb R^n$ and $\mathbb C^n$ with any norm are Banach spaces.
2. $C[a,b]$ with $\|\cdot\|_\infty$ is complete because a uniform limit of continuous functions is continuous.
3. $\ell^p$ is complete for $1\le p<\infty$.
4. $L^p(\Omega)$ is complete for $1\le p\le\infty$ by the Riesz–Fischer theorem.
5. Every incomplete metric space has a unique completion up to isometric isomorphism. For example, the completion of $C[a,b]$ under $\|\cdot\|_p$ is $L^p[a,b]$.

### Cauchy-Sequence Checks

- Pointwise Cauchy is not the same as norm Cauchy: the standard basis $e_n$ in $\ell^2$ converges pointwise to $0$, but

$$\|e_n-e_m\|_2=\sqrt2\qquad(n\ne m),$$

so it is not Cauchy in $\ell^2$.
- To construct a Cauchy sequence in an incomplete space, choose a sequence converging to an exterior point, e.g. $(1+1/n)^n\to e\notin\mathbb Q$ inside $\mathbb Q$.
- Compactness implies completeness: every Cauchy sequence in a compact metric space has a convergent subsequence and hence converges itself; in a compact space, Cauchyness and convergence are equivalent.

### Typical Competition Problems

- To prove an infinite-dimensional function space incomplete under a given norm, construct a Cauchy sequence whose limit is outside the space because it lacks smoothness or violates a boundary condition.
- To verify a sequence Cauchy but nonconvergent in its space, use a standard construction in $\mathbb Q$ or $C[0,1]$ with $\|\cdot\|_1$.
- To use completeness for existence of an operator-equation solution, construct the solution as the limit of an iterative sequence.

For the stated verification point, construct a piecewise-linear sequence in $C[0,1]$ under $\|\cdot\|_1$, prove it Cauchy, and show that its step-function limit is not in $C[0,1]$.

## Quick Reference: Cauchy Sequences and Complete Metric Spaces

- **Retrieval terms:** inequality, maximum, largest, greatest, convergence, converges, Cauchy, complete metric.
- **Core facts:** Every convergent sequence in a metric space is Cauchy, by a two-part triangle-inequality estimate. Every Cauchy sequence is bounded: first enclose its tail with a fixed tolerance, then take a maximum together with the finitely many preceding terms. In a complete metric space, every Cauchy sequence converges; this is exactly the definition of completeness. A bounded sequence need not be Cauchy, as shown by a sequence oscillating inside a bounded set.
- **Solution route:** For each assertion, verify it directly from the definition or eliminate it with a minimal counterexample. Keep separate the hypotheses in “convergence implies Cauchy” and “Cauchy sequences converge in a complete space.” Completeness is a property of the whole space, not of one particular sequence.
- **Pitfalls:** Do not treat boundedness and the Cauchy property as equivalent; do not assert that a Cauchy sequence converges in an arbitrary incomplete metric space; and do not prove “a convergent sequence is Cauchy” circularly.
