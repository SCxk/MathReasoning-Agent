# Measure Theory and Integration Skill

## Domain Boundaries and Routing Conventions

- Scope: Lebesgue measure, measurable functions, $L^p$ spaces, convergence theorems, Fubini, and Radon–Nikodym.
- Does not take over: problems containing only real-variable limits/series are routed to mathematical analysis; static probability, statistical sampling, and stochastic processes are routed respectively to probability, statistical inference, and stochastic processes.
- Verification contract: for every conclusion, check measurability, absolute integrability, domain, and the “almost everywhere/everywhere” quantifier together. Do not replace measure hypotheses with Riemann intuition.

## High-Frequency Conventions for Objective Questions

- On a finite closed interval, $\int|f|<\infty$ directly implies that $f$ is Lebesgue integrable. A continuous function on a compact interval is bounded and measurable, hence also Lebesgue integrable.
- “The set of discontinuities has measure zero” alone, without boundedness or an $L^1$ condition, does not imply Lebesgue integrability; “bounded” without measurability is also insufficient. In multiple-choice questions, check measurability, local boundedness, and absolute integrability one by one; do not treat fragments of the Riemann criterion as complete conditions.

> Covers core topics including Lebesgue measure, measurable functions, Lebesgue integrals, $L^p$ spaces, convergence theorems, inequalities, Fubini's theorem, absolute continuity, the Radon–Nikodym theorem, convolution, and measure construction.

---

## 1. Foundations of Lebesgue Measure

### Core Definitions and Theorems

| Concept | Definition |
|------|------|
| **Lebesgue outer measure** | $m^*(E)=\inf\{\sum|I_k|:E\subset\bigcup I_k\}$, where $I_k$ are open intervals |
| **Lebesgue measurable set** | $E$ satisfies the Carathéodory condition: $\forall A\subset\mathbb R^n$, $m^*(A)=m^*(A\cap E)+m^*(A\setminus E)$ |
| **Null set** | A set of outer measure `0`, such as a countable set or the Cantor set |
| **Properties of measurable sets** | Closure under countable unions, countable intersections, and complements ($\sigma$-algebra property) |
| **Regularity** | For every measurable $E$, $m(E)=\inf\{m(U):E\subset U,\ U\text{ open}\}=\sup\{m(K):K\subset E,\ K\text{ compact}\}$ |

### Core Formulae

- Interval measure: $m([a,b])=m((a,b))=b-a$.
- Countable additivity: for pairwise disjoint measurable $\{E_k\}$, $m(\bigcup E_k)=\sum m(E_k)$.
- A countable set has measure zero: $m(\mathbb Q)=0$.

### Standard Solution Procedure

1. Determine whether the set is countable → it is null.
2. Use interval additivity to partition the set.
3. Use $\sigma$-algebra properties to decompose a complicated set into simple sets.

### Frequent Examination Pitfalls

- **Nonmeasurable sets exist**: they depend on the axiom of choice; sets encountered in examinations are usually measurable.
- **A null set need not be countable**: the Cantor set is an uncountable null set.
- **Measure is nonnegative but may be infinite**: an open set can have infinite measure.

---

## 2. Measurable Functions

### Core Definitions and Theorems

| Concept | Definition |
|------|------|
| **Measurable function** | $f:X\to\mathbb R$ satisfying $\forall a\in\mathbb R$, $\{x:f(x)>a\}$ is measurable |
| **Simple function** | $f=\sum_{i=1}^na_i\chi_{E_i}$, where $E_i$ are measurable and pairwise disjoint |
| **Almost everywhere** | Holds everywhere except on a null set |
| **Dirichlet function** | $\chi_{\mathbb Q}(x)$, equal to `1` on rationals and `0` on irrationals |
| **Egorov's theorem** | a.e. convergence $\Rightarrow$ uniform convergence on a compact set of arbitrarily large measure |

### Core Properties

- Pointwise or a.e. limits of measurable functions remain measurable.
- Continuous functions $\Rightarrow$ measurable functions.
- Measurable functions can be approximated by sequences of simple functions.

### Frequent Examination Pitfalls

- **Riemann nonintegrable but Lebesgue integrable**: the Dirichlet function is the classical example.
- **Functions equal almost everywhere are regarded as identical**: in $L^p$ spaces, a.e.-equal functions are equivalent.

---

## 3. Lebesgue Integrals

### Core Definition

$$\int f\,dm=\sup\left\{\int g\,dm:0\le g\le f,\ g\text{ is a simple function}\right\}.$$

For a general measurable function, $f=f^+-f^-$, where $f^+=\max(f,0)$ and $f^-=\max(-f,0)$.

### Core Formulae

- For a nonnegative measurable function, $\int f\,dm=\lim_{n\to\infty}\int\phi_n\,dm$ when $\phi_n$ increases monotonically to $f$.
- A Riemann-integrable function is also Lebesgue integrable, with the same integral value.
- **Newton–Leibniz**: if $f$ is absolutely continuous, then $f(b)-f(a)=\int_a^bf'\,dm$.

### Standard Solution Procedure

1. Check that the function is measurable.
2. Determine nonnegativity → use monotone convergence or simple-function approximation.
3. For a function with positive and negative values, split and integrate its positive and negative parts separately.
4. Use the Riemann integral for a Riemann-integrable function.

### Frequent Examination Pitfalls

- **The Lebesgue integral does not treat improper integrals**: $\int_0^\infty\frac{\sin x}{x}\,dx$ is not Lebesgue integrable.
- **Lebesgue integration is absolute integration**: $\int f$ exists if and only if $\int|f|$ exists.

---

## 4. Integrals of Simple Functions

### Core Definition

$$f(x)=\sum_{i=1}^na_i\chi_{E_i}(x),\qquad\int f\,dm=\sum_{i=1}^na_im(E_i).$$

### Standard Solution Procedure

1. Identify the partition of value intervals for the simple function.
2. Calculate the measure of each interval.
3. Sum: $\sum$ (value $\times$ measure).

### Typical Example (idx=2)

- $f(x)=2$ on $[0,1)$ and $f(x)=3$ on $[1,2]$.
- $\int f\,dm=2\times m([0,1))+3\times m([1,2])=2\times1+3\times1=5$.

---

## 5. $L^p$ Spaces and Norms

### Core Definitions

$$\|f\|_p=\left(\int|f|^p\,dm\right)^{1/p},\qquad1\le p<\infty,$$
$$\|f\|_\infty=\operatorname{ess\,sup}|f|=\inf\{M>0:|f|\le M\text{ a.e.}\}.$$

### Core Formulae

- $\|f\|_p^p=\int|f|^p\,dm$.
- $\lim_{p\to\infty}\|f\|_p=\|f\|_\infty$ when $f\in L^\infty\cap L^p$ for some $p$.
- On a finite-measure space, $L^p\subset L^q$ when $p\ge q$.

### Standard Solution Procedure

1. Determine the type of measure space (finite / $\sigma$-finite).
2. Compute $\int|f|^p\,dm$.
3. Take the $p$-th root to obtain $\|f\|_p$.
4. Take the essential supremum to obtain $\|f\|_\infty$.

### Frequent Examination Pitfalls

- **An $L^p$ norm depends on the measure space**: the same function can have different norms under different measures.
- **Smaller $p$ is more sensitive to function peaks**: as $p\to\infty$, only the largest value matters.

---

## 6. Monotone Convergence Theorem (Levi's Lemma)

### Core Theorem

If $\{f_n\}$ is a monotonically increasing sequence of nonnegative measurable functions ($0\le f_1\le f_2\le\cdots$), then
$$\lim_{n\to\infty}\int f_n\,dm=\int\lim_{n\to\infty}f_n\,dm.$$

### Standard Solution Procedure

1. Verify that $f_n$ is nonnegative and measurable.
2. Verify that $f_n$ is monotonically increasing.
3. Find the pointwise limit $f=\lim f_n$.
4. Interchange limit and integral.

### Typical Examples (idx=4, idx=12)

- **idx=4**: $f_n(x)=\frac{nx}{1+n^2x^2}$ converges pointwise to `0`, and $\lim\int f_n=0$.
- **idx=12**: $-\ln x=\lim_{n\to\infty}-\ln(\max(x,1/n))$, and $\int_0^1-\ln x\,dx=1$.

---

## 7. Dominated Convergence Theorem

### Core Theorem

Let $\{f_n\}$ be measurable functions converging pointwise (a.e.) to $f$. If there is a nonnegative integrable function $g$ such that $|f_n|\le g$ a.e., then
$$\lim_{n\to\infty}\int f_n\,dm=\int f\,dm.$$

### Standard Solution Procedure

1. Find a dominating function $g$ satisfying $|f_n|\le g$ and $\int g<\infty$.
2. Verify the pointwise limit $f$.
3. Apply DCT: $\lim\int f_n=\int f$.

### Typical Example (idx=5)

- $f_n(x)=\frac{\sin(nx)}{n(1+x^2)}$.
- Dominating function: $|f_n|\le\frac1{1+x^2}\in L^1([0,\infty))$.
- The pointwise limit is `0`, hence $\lim\int f_n=0$.

---

## 8. Fatou's Lemma

### Core Theorem

For a sequence of nonnegative measurable functions $\{f_n\}$,
$$\int\liminf_{n\to\infty}f_n\,dm\le\liminf_{n\to\infty}\int f_n\,dm.$$

### Standard Solution Procedure

1. Verify that $f_n$ is nonnegative and measurable.
2. Calculate the integral of $\liminf f_n$.
3. Calculate $\liminf\int f_n$.
4. Compare the two and verify the inequality.

### Typical Example (idx=6)

- $f_n(x)=n\chi_{(0,1/n]}(x)$.
- $\liminf f_n=0$ a.e., so $\int\liminf f_n=0$.
- $\int f_n=n\cdot(1/n)=1$, so $\liminf\int f_n=1$.
- Strict inequality: $0<1$.

### Frequent Examination Pitfalls

- **The reversed inequality fails**: Fatou's lemma has only the $\le$ direction.
- **When equality does not hold**: uniform integrability is needed to interchange limit and integral.

---

## 9. $L^p$-Norm Inequality

### Core Formula

**Monotonicity**: on a finite-measure space, if $1\le p<q\le\infty$, then
$$\|f\|_p\le\|f\|_q\cdot m(X)^{1/p-1/q}.$$
In particular, if $m(X)=1$ (a probability measure), then $\|f\|_p\le\|f\|_q$.

### Typical Example (idx=7)

- $f(x)=x^{1/3}$ on $[0,1]$.
- $\|f\|_1=\int_0^1x^{1/3}dx=3/4=0.75$.
- $\|f\|_3=(\int_0^1x\,dx)^{1/3}=(1/2)^{1/3}\approx0.794$.
- Verification: $0.75\le0.794$.

---

## 10. Fubini's Theorem

### Core Theorem

If $f$ on product space $X\times Y$ with $\sigma$-finite measures is nonnegative measurable or integrable, then
$$\int_{X\times Y}f\,d(\mu\times\nu)=\int_X\left(\int_Yf(x,y)\,d\nu(y)\right)d\mu(x)=\int_Y\left(\int_Xf(x,y)\,d\mu(x)\right)d\nu(y).$$

### Standard Solution Procedure

1. Verify that the integrand is nonnegative or absolutely integrable.
2. Calculate the iterated integral in the order `x` then `y`.
3. Verify the same result in the order `y` then `x`.

### Typical Example (idx=10)

- $\iint_{[0,1]^2}xy\,dm_2=\int_0^1\int_0^1xy\,dx\,dy=1/4$.

### Frequent Examination Pitfalls

- **When Fubini fails**: for $\iint\frac{x^2-y^2}{(x^2+y^2)^2}$ on $[0,1]^2$, changing iterated-integration order gives different results.
- **Integrability must be verified**: require nonnegative measurability or $\iint|f|<\infty$.

---

## 11. Absolutely Continuous Functions and the Newton–Leibniz Formula

### Core Definition

An **absolutely continuous function** satisfies: for every $\varepsilon>0$, there is $\delta>0$ such that for every finite family of disjoint intervals $\{(a_k,b_k)\}$, if $\sum(b_k-a_k)<\delta$, then $\sum|f(b_k)-f(a_k)|<\varepsilon$.

### Core Theorem

$f$ is absolutely continuous if and only if it is differentiable a.e., $f'\in L^1$, and
$$f(x)-f(a)=\int_a^xf'(t)\,dt.$$

### Standard Solution Procedure

1. Check whether $f$ is Lipschitz / absolutely continuous.
2. Calculate derivative $f'$.
3. Verify $\int_a^bf'=f(b)-f(a)$.

### Typical Example (idx=9)

- $f(x)=x^2$ is absolutely continuous on $[0,1]$.
- $f'(x)=2x$, and $\int_0^12x\,dx=1=f(1)-f(0)$.

---

## 12. Radon–Nikodym Theorem

### Core Theorem

If $\nu\ll\mu$ ($\nu$ is absolutely continuous with respect to $\mu$), then there exists a measurable function $g$ such that
$$\nu(E)=\int_Eg\,d\mu,\qquad\forall E\text{ measurable}.$$
Write $g=d\nu/d\mu$.

### Standard Solution Procedure

1. Verify $\nu\ll\mu$ ($\mu(E)=0\Rightarrow\nu(E)=0$).
2. Directly read the Radon–Nikodym derivative from the definition of $\nu$.
3. Calculate the measure of a concrete set.

### Typical Example (idx=13)

- $\nu(E)=\int_E2x\,d\mu$, so $d\nu/d\mu=2x$.
- $\nu([0,1])=\int_0^12x\,dx=1$.

---

## 13. Chebyshev's Inequality

### Core Formula

For measurable $f\ge0$ and $\lambda>0$,
$$m(\{x:f(x)\ge\lambda\})\le\frac1\lambda\int f\,dm.$$

### Standard Solution Procedure

1. Identify $f$ and $\lambda$.
2. Calculate the left side: find $\{f\ge\lambda\}$ and its measure.
3. Calculate the right side: $\frac1\lambda\int f$.
4. Compare and verify.

### Typical Example (idx=14)

- $f(x)=x^2$, $\lambda=1/4$.
- Left side: $m([1/2,1])=1/2$.
- Right side: $4\times\int_0^1x^2dx=4\times1/3=4/3$.
- Verification: $1/2\le4/3$.

---

## 14. Hölder's Inequality

### Core Formula

For $p,q>1$ with $1/p+1/q=1$,
$$\int|fg|\,d\mu\le\|f\|_p\|g\|_q.$$
When $p=q=2$, this is the Cauchy–Schwarz inequality.

### Standard Solution Procedure

1. Identify the conjugate exponents $(p,q)$.
2. Calculate $\|f\|_p=(\int|f|^p)^{1/p}$.
3. Calculate $\|g\|_q=(\int|g|^q)^{1/q}$.
4. Calculate $\int|fg|$ and verify the inequality.

### Typical Example (idx=15)

- $f(x)=x$, $g(x)=1-x$, $p=q=2$.
- $\int fg=\int_0^1x(1-x)dx=1/6$.
- $\|f\|_2=\sqrt{1/3}$ and $\|g\|_2=\sqrt{1/3}$, product $=1/3$.
- Verification: $1/6\le1/3$.

---

## 15. Minkowski's Inequality

### Core Formula

For $1\le p<\infty$,
$$\|f+g\|_p\le\|f\|_p+\|g\|_p.$$

### Standard Solution Procedure

1. Identify $p$.
2. Calculate $\|f\|_p$ and $\|g\|_p$.
3. Calculate $\|f+g\|_p$.
4. Verify the triangle inequality.

### Typical Example (idx=16)

- $f(x)=x$, $g(x)=x^2$, $p=2$.
- $\|f+g\|_2=(\int_0^1(x+x^2)^2dx)^{1/2}=\sqrt{31/30}\approx1.0165$.
- $\|f\|_2=\sqrt{1/3}\approx0.5774$, $\|g\|_2=\sqrt{1/5}\approx0.4472$.
- Verification: $1.0165\le1.0246$.

---

## 16. Modes of Convergence: a.e. and $L^p$ Convergence

### Core Definitions

| Convergence type | Definition |
|---------|------|
| **Almost-everywhere convergence** | $f_n(x)\to f(x)$ for almost every $x$ |
| **$L^p$ convergence** | $\|f_n-f\|_p\to0$ |
| **Convergence in measure** | $\forall\varepsilon>0$, $m(\{|f_n-f|\ge\varepsilon\})\to0$ |

### Relation Diagram

$$L^p\text{ convergence}\xRightarrow{m(X)<\infty}\text{convergence in measure}\xRightarrow{\text{subsequence}}\text{a.e. convergence}.$$

### Standard Solution Procedure

1. Test a.e. convergence by taking a limit at each $x$ (attend to null sets).
2. Calculate $\|f_n\|_p$ to test $L^p$ convergence.
3. a.e. convergence + a domination condition $\Rightarrow L^p$ convergence.

### Typical Example (idx=17)

- $f_n(x)=x^n$ on $[0,1]$.
- It converges a.e. to `0` (it does not converge at $x=1$, but a singleton is null).
- $\|f_n\|_1=\int_0^1x^ndx=1/(n+1)\to0$, so convergence is in $L^1$.

---

## 17. Convolution

### Core Definition

$$
(f*g)(t)=\int_{\mathbb{R}}f(s)g(t-s)\,ds.
$$

### Core Properties

- Commutativity of convolution: $f*g=g*f$.
- The convolution $\chi_{[0,1]}*\chi_{[0,1]}(t)$ is a triangular function.

### Standard Solution Procedure

1. Identify the definition of convolution.
2. Determine the supports and the range on which the convolution can be nonzero.
3. Compute it piecewise.
4. State the final piecewise expression.

### Typical Example (idx=18)

Let $h(t)=\chi_{[0,1]}*\chi_{[0,1]}(t)$. Then

$$
h(t)=
\begin{cases}
0, & t\leq0,\\
t, & 0\leq t\leq1,\\
2-t, & 1\leq t\leq2,\\
0, & t\geq2.
\end{cases}
$$

In particular, $h(1)=1$.

---

## 18. Construction of Measures and Absolute Continuity

### Core Result

If

$$
\mu(E)=\int_Ef\,dm,
$$

where $f\geq0$ is measurable, then $\mu\ll m$ and

$$
\frac{d\mu}{dm}=f.
$$

### Standard Solution Procedure

1. Verify that $f\geq0$ and that $f$ is measurable.
2. Express the measure as $\mu(E)=\int_Ef\,dm$.
3. Conclude $\mu\ll m$ and identify the Radon--Nikodym derivative as $f$.

### Typical Example (idx=19)

For $\mu(E)=\int_Ex\,dm$ on $[0,1]$,

$$
\frac{d\mu}{dm}=x,\qquad \mu([0,1])=\frac12,\qquad \mu(C)=0
$$

for the Cantor set $C$.

---

## 19. General Problem-Solving Methodology

| Problem signal | Preferred direction |
|---|---|
| Computing an integral of a continuous or Riemann-integrable function | Riemann integration |
| A limit involving a parameter $n$ | MCT, DCT, or Fatou's lemma |
| A norm | $L^p$-space theory |
| An inequality | Chebyshev, Hölder, or Minkowski |
| A double integral | Fubini's theorem |
| Integrability | measurability + absolute integrability |
| Radon--Nikodym derivative | density representation |
| Convolution | support analysis |

### Practical Decision Rules

1. For nonnegative functions, use monotone convergence or approximation by simple functions.
2. For bounded functions on a finite-measure set, use bounded convergence.
3. When a dominating integrable function is needed, use dominated convergence.
4. When only an inequality is available, use Fatou's lemma.
5. For concrete functions, use Riemann integration together with the relevant properties.

### Validation Checklist

- Check the range and dimensional consistency of the result.
- Check symmetry when symmetry should be present.
- Check that inequalities are self-consistent.
- For limits, separately compute pointwise limits and integral limits.

---

## 20. Quick Index of Typical Examples

| idx | Topic | Key result |
|---:|---|---|
| 0 | Lebesgue integral of a continuous function | $\int_0^1x^2\,dm=1/3$ |
| 1 | Rationals and irrationals | $m(\mathbb{Q}\cap[0,1])=0$, $m([0,1]\setminus\mathbb{Q})=1$ |
| 2 | Simple functions | integral equals $5$ |
| 3 | $L^p$ norm | $\|x\|_2=\sqrt3/3$ |
| 4 | Monotone convergence | $\lim\int_0^1\frac{nx}{1+n^2x^2}\,dx=0$ |
| 5 | Dominated convergence | $\lim\int_0^\infty\frac{\sin(nx)}{n(1+x^2)}\,dx=0$ |
| 6 | Strictness in Fatou's lemma | $0<1$ |
| 7 | $L^p$ inclusion | $x^{1/3}$ |
| 8 | Dirichlet function | $\chi_{\mathbb Q}$ has Lebesgue integral $0$ |
| 9 | Absolute continuity | $x^2$, and so on |
| 10 | Fubini's theorem | $1/4$ |
| 11 | $L^\infty$ norm | $\|e^{-x}\|_\infty=1$, and so on |
| 12 | Newton--Leibniz | $\int_0^1-\ln x\,dx=1$ |
| 13 | Radon--Nikodym | derivative $2x$ and measure $1$ |
| 14 | Chebyshev inequality | see the corresponding calculation |
| 15 | Hölder inequality | see the corresponding calculation |
| 16 | Minkowski inequality | see the corresponding calculation |
| 17 | a.e. and $L^1$ convergence | $x^n\to0$ |
| 18 | Convolution | the triangular function, $h(1)=1$ |
| 19 | Constructing a measure | $\mu(E)=\int_Ex\,dm$, $\mu([0,1])=1/2$ |

Difficulty distribution: easy: 4 problems (idx $0,1,2,14$); medium: 12 problems; hard: 4 problems (idx $12,13,18,19$).

---

## 21. Criteria and Counterexamples for Lebesgue Integrability

### Core Theorems

1. A measurable function $f$ is Lebesgue integrable if and only if

   $$\int|f|\,dm<\infty.$$

   Equivalently, after writing $f=f^+-f^-$, both $\int f^+\,dm$ and $\int f^-\,dm$ are finite. This differs from conditionally convergent improper Riemann integrals: for example, $\sin x/x$ has improper Riemann integral $\pi/2$, but it is not Lebesgue integrable because its absolute integral diverges.

2. If $f$ is bounded and measurable on a measurable set $E$ with $m(E)<\infty$, then $f$ is Lebesgue integrable, since

   $$\int_E|f|\,dm\leq M m(E)<\infty.$$

   Consequently, every continuous function on a compact set is Lebesgue integrable.

3. Measurability is indispensable. Even if $|f|$ is an integrable simple function, a nonmeasurable $f$ is not Lebesgue integrable.

### Condition Table

| Conditions | Is Lebesgue integrability guaranteed? |
|---|---|
| $f$ measurable and $\int|f|\,dm<\infty$ | Yes; this is necessary and sufficient |
| $f$ measurable, bounded, and defined on a finite-measure set | Yes; sufficient |
| $f$ continuous on a compact set | Yes; sufficient |
| $\int|f|\,dm<\infty$ but measurability is absent | No; use $\chi_V-\chi_{[0,1]\setminus V}$ |
| $f$ bounded and its discontinuity set is null, but measurability is absent | No; this is a Riemann-integrability condition rather than a direct Lebesgue criterion |
| $f$ measurable alone | No; for example, $1/x$ on $[0,1]$ |

### Counterexample 1: Absolute Integrability Does Not Replace Measurability

Let $V\subset[0,1]$ be nonmeasurable, and set

$$
f=\chi_V-\chi_{[0,1]\setminus V}=
\begin{cases}
1,&x\in V,\\
-1,&x\in[0,1]\setminus V.
\end{cases}
$$

Then $|f|=1$, so $\int|f|\,dm=1$, but $f$ is nonmeasurable and hence is not Lebesgue integrable. Thus the statement $\int|f|\,dm<\infty$ applies only after measurability has been established; absolute integrability of the absolute value does not imply measurability.

### Counterexample 2: Conditional Improper Riemann Integrability Does Not Give Lebesgue Integrability

Although

$$
\int_0^\infty\frac{\sin x}{x}\,dx=\frac\pi2
$$

as an improper Riemann integral, its absolute integral diverges. Indeed, it has the lower bound

$$
\sum_{k=1}^\infty\frac{2}{(k+1)\pi}=\infty.
$$

Thus $\sin x/x$ is not Lebesgue integrable. Lebesgue integration requires absolute integrability, unlike conditional improper Riemann convergence.

### Counterexample 3: Boundedness Does Not Replace Measurability

The function $g=\chi_V$ is bounded but nonmeasurable, so it has no Lebesgue integral.

### Three-Step Integrability Checklist

1. **Measurability.** Continuous functions, monotone functions, pointwise limits, and arithmetic combinations of measurable functions are measurable. Functions built from a Vitali set or another nonmeasurable set are not. If measurability fails, the function is not Lebesgue integrable.
2. **Absolute integrability.** On a finite-measure set, a bounded measurable function satisfies $\int_E|f|\,dm\leq M m(E)$. On an infinite interval, seek decay such as $C/|x|^{1+\varepsilon}$; near a singular point $x_0$, seek a bound such as $C/|x-x_0|^\alpha$ with $\alpha<1$.
3. **Conclusion.** The function is Lebesgue integrable precisely when both preceding requirements hold.

### Mnemonic

“Measurable and absolutely integrable” is the if-and-only-if criterion. “Bounded, measurable, finite domain” is a common sufficient condition.

### Common Pitfalls

- A null discontinuity set by itself does not imply Lebesgue integrability; it belongs to the Riemann-integrability criterion.
- Boundedness by itself is insufficient: measurability and a finite-measure domain are also needed.
- In the standard definition, $\int|f|\,dm<\infty$ implicitly presumes measurability.
- $\sin x/x$ is not Lebesgue integrable because both $\int f^+\,dm$ and $\int f^-\,dm$ are infinite, so $\infty-\infty$ is meaningless.

### Supplementary Audit Procedure

1. Check measurability, absolute integrability, finiteness of the domain measure, and boundedness separately.
2. For a universal assertion, look for counterexamples involving nonmeasurability, infinite measure, nonabsolute convergence, or modification outside a null set.
3. When applying a convergence theorem, list both the convergence hypothesis and the domination hypothesis; pointwise convergence alone never directly justifies interchanging a limit and an integral.

---

## Quick Reference: Lebesgue-Integrability Criteria and Counterexamples

- **Retrieval terms:** integral, integration, measure, measurable, Lebesgue integrable, point sets, planar configuration, interval, lattice.
- **Core content:** on a closed interval, $|f|$ integrable implies $f$ integrable, by decomposition into positive and negative parts. A continuous function is bounded and measurable, hence integrable. “The discontinuity set has measure zero” implies integrability only for bounded measurable functions, as in the Riemann-integrability criterion; an unbounded counterexample can have divergent integral. A bounded nonmeasurable function, such as the indicator of a nonmeasurable set, is also nonintegrable.
- **Route:** in multiple choice, test each item against the equivalence “measurable” plus “finite $\int|f|$”; use an unbounded counterexample and a nonmeasurable counterexample to eliminate false items.
- **Pitfalls:** treating a null discontinuity set as sufficient while omitting boundedness; assuming boundedness implies integrability while omitting measurability; failing to derive integrability of $f$ from integrability of $|f|$ using positive/negative parts.
- **Required answer template:** A is true ($\int|f|<\infty\Rightarrow$ integrable); B is true (continuous on a compact interval $\Rightarrow$ bounded and measurable); C is false ($f=1/x$ on $(0,1]$, $f(0)=0$, has only one discontinuity but $\int|f|=\infty$); D is false (indicator of a Vitali set is bounded but nonmeasurable). Therefore submit $\boxed{A,B}$.

## Direct-Solution Reference: Correct Lebesgue-Integrability Options (AB)

- **Retrieval terms:** function, interval, Lebesgue integrability, absolute integrability, continuous, discontinuity set, bounded, correct.
- **Match condition:** Lebesgue integrability.
- **Required result:** $\boxed{AB}$.
- **Wrong-answer warnings:** ABC fails because C has a $f=1/\sqrt x$-type counterexample: a null discontinuity set but no absolute integrability. ABCD fails because D has a bounded but nonmeasurable indicator-function counterexample.
- **Derivation:** A is true by the $L^1$ definition. B is true because continuous on a closed interval implies bounded and measurable. C is false: importing the Riemann criterion is insufficient; $1/\sqrt x$ has a null discontinuity set but divergent integral. D is false: bounded does not ensure measurability, as shown by an indicator of a Vitali set.
- **Self-check:** pair the counterexamples $\{1/\sqrt x\}$ and $\{\chi_{\mathrm{Vitali}}\}$ with C and D respectively.
