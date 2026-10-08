---
name: mathematical-analysis-problem-solving
description: Systematically solve and verify problems in mathematical analysis involving limits, continuity and differentiability, higher derivatives, Taylor expansions, improper and parameter-dependent integrals, numerical and functional series, power series, suprema and infima, bounded variation, uniform convergence, and interchange of limits with differentiation or integration. Use it to identify problem types, choose theorems, organize proofs, avoid missing hypotheses, and give checkable derivations for mathematical-analysis exercises.
---

# Mathematical Analysis Problem-Solving Skill

## Retrieved Solution Directives: Strict-Interval Quadratic Constraint

### Minimum number of variables in \((-1,1)\)

- **Similarity description:** Choose the fewest reals strictly between \(-1\) and \(1\) so that the sum of their squares plus the square of their sum is fixed, while the sum has absolute value below 1.
- **Retrieval terms:** `strict interval (-1,1) sum of squares 21 variables construction`.
- Let \(s=\sum_i x_i\). The bound \(x_i^2<1\) gives only \(n\ge20\); exclude \(n=20\). With fixed sum \(s\), convexity gives the supremum \(20-2|s|\) for \(\sum_{i=1}^{20}x_i^2\) on \((-1,1)^{20}\). Yet the equation requires
  \[
  \sum_{i=1}^{20}x_i^2=20-s^2>20-2|s|\quad(0<|s|<1),
  \]
  a contradiction; \(s=0\) also contradicts strictness.
- Choose \(0<t<1\), take ten values \(a\), ten values \(-a\), and one value \(t\), where \(a=\sqrt{1-t^2/10}\). Then \(\sum x_i=t\) and \(20a^2+2t^2=20\).
- **Scoring convention:** “between” is the strict interval; a closed-interval reading incorrectly gives 20.
- **Reference-answer submission suggestion:** \(\boxed{21}\).

## Domain Boundaries and Routing Conventions

- Scope: real-variable limits; continuity/differentiability; series; parameter-dependent integrals; suprema and infima; interchange for function sequences; Fourier analysis and analytic functional equations.
- Does not take over: algebraic structures, formal PDE adjoints, statistical sampling, and pure Euclidean geometry are routed to their corresponding specialist handbooks; for a Laplacian on a circle, first determine the restricted domain specified in the problem.
- Verification contract: check pointwise/uniform convergence, conditional/absolute convergence, and endpoints separately; every interchange must state a domination or uniformity condition.

## Workflow

1. First mark the objective: a numerical value, convergence, existence, supremum/infimum, function expression, or theorem proof.
2. Then identify the object: a sequence, one-variable function, multivariable function, integral, numerical series, function series, or function sequence.
3. State every hypothesis of the theorem before deciding whether equivalent infinitesimals, Taylor's formula, comparison tests, the Weierstrass test, Dirichlet's test, or an interchange theorem can be used.
4. Prefer structured transformations: rationalization, rescaled substitutions, partial fractions/telescoping, parameterization, extracting a uniform upper bound, or constructing a counterexample path.
5. Prove “converges” and “converges to what” separately; distinguish pointwise from uniform and conditional from absolute convergence.
6. Finally verify domain, endpoints, sign, dimensional consistency, special values, and an independent method.

## I. Limits, Continuity, and Differentiability

### Core Concepts

- Both sequence limits and function limits require eventual validity at every prescribed precision; in calculation, first seek dominant terms and cancellable structure.
- A multivariable limit requires the same value along every approach. Equality of two iterated limits does not imply existence of the multivariable limit.
- Continuity at $x_0$ requires $\lim_{x\to x_0} f(x)=f(x_0)$; differentiability additionally requires existence of the difference-quotient limit.
- An integral-containing limit often concentrates mass near an endpoint; rescaling variables can expose its limit kernel.
- A Cauchy sequence is one whose terms become arbitrarily close to each other. In $\mathbb R$ every Cauchy sequence converges (completeness), but this fails in $\mathbb Q$.
- Bounded does not imply Cauchy: $a_n=(-1)^n$ is bounded but not Cauchy; monotone and bounded does imply Cauchy (in $\mathbb R$, every monotone bounded sequence converges).
- When solving a functional equation on a discrete domain such as $\mathbb Q\to\mathbb Z$, first work at integer points to derive idempotence and translation invariance, then extend to all rationals.
- For parameter inequalities involving exponential towers or strictly convex functions, use logarithms to lower the level, second-derivative convexity analysis, and Taylor expansion at critical points to find necessary and sufficient conditions.

### Formulae and Theorems

- Rationalization: $\sqrt A-\sqrt B=(A-B)/(\sqrt A+\sqrt B)$.
- Important limits: $\sin t/t\to1$, $(1-\cos t)/t^2\to1/2$.
- Test for continuity: compute the function limit, then compare it with the function value.
- Test for differentiability: $f'(x_0)=\lim_{h\to0}[f(x_0+h)-f(x_0)]/h$.
- Disproof of a multivariable limit: if two paths yield different limits, the multivariable limit does not exist.
- Dominated-convergence principle: one may directly interchange limit and integral only if $g_n\to g$ and an integrable function uniformly controls $|g_n|$.

### Standard Solution Procedure

1. Substitute to determine whether the expression is indeterminate, and confirm direction of approach and domain.
2. For differences of radicals, rationalize first; for trigonometric expressions, reduce to important limits; for integrals involving `n`, algebraically rewrite and try $t=x^n$.
3. For a multivariable limit, first calculate coordinate-axis or iterated limits, then test paths such as $y=kx$ and $y=x^m$; to prove existence, give a uniform estimate.
4. For piecewise oscillatory functions, use absolute-value squeezing for continuity and calculate the difference quotient directly for differentiability.
5. State clearly which conclusion holds: “the limit value,” “does not exist,” or “continuous but nondifferentiable.”

### Common Pitfalls

- Do not treat equality of two iterated limits as sufficient for existence of a multivariable limit.
- Do not infer $f(x)/x\to0$ merely from $f(x)\to0$; differentiability requires checking the difference quotient.
- Do not interchange limit and integral without uniform control or uniform convergence.
- After rationalizing, check that no exterior `n` or scaling factor has been lost.
- Bounded does not imply Cauchy: bounded oscillatory sequences such as $(-1)^n$ are not Cauchy. A Cauchy sequence need not converge unless its space is complete.
- Do not assume continuity in a functional-equation solution: a function on $\mathbb Q$ cannot directly use topological arguments; attend to range restrictions (such as $\mathbb Z$), which affect classification.
- In deriving necessary and sufficient conditions for exponential-tower inequalities, necessary conditions come from local critical-point behavior while sufficiency requires a global convexity argument; do not conflate them.

### Techniques

- On seeing $n(\sqrt{n^2+c}-n)$, factor $n^2$ from the radical or rationalize directly.
- On seeing $x\sin(1/x)$, use $|x\sin(1/x)|\le|x|$ for continuity; for differentiability, observe oscillation remaining in the difference quotient.
- On seeing $n\int_0^1\Phi(x^n)\,dx$, let $t=x^n$; this often gives a fixed-interval integral containing $t^{1/n}$.
- In functional equations, first substitute special parameters (for example, $b=1,a=0$) to simplify, derive idempotence $g(g(x))=g(x)$, then combine integer translations and rational extension for classification.
- For exponential-tower parameter inequalities, repeatedly take logarithms to lower the level; if $f''(x)>0$, use the tangent-line lower estimate (supporting-line property of convex functions), and use Taylor expansion near a critical point to expose threshold constants.
- To prove a sequence Cauchy, estimate $|a_n-a_m|$ and find an upper bound independent of `n,m` that tends to zero; boundedness plus monotonicity immediately implies Cauchy.

## II. Higher Derivatives, Taylor Expansions, and Power Series

### Core Concepts

- For an analytic function, power-series coefficients at the expansion point satisfy $a_n=f^{(n)}(0)/n!$.
- A Taylor expansion must be retained to the order specified by the problem, controlling every factor in a product that can contribute to that order.
- For a power series, first operate on the open interval $|x|<R$, then check its two endpoints separately.
- New sum functions can be obtained from known basic power series by termwise integration, termwise differentiation, or substitution.

### Formulae and Theorems

- $e^x=\sum_{n\ge0}x^n/n!$, $\cos x=\sum_{n\ge0}(-1)^nx^{2n}/(2n)!$.
- $f^{(n)}(0)=n![x^n]f(x)$, where $[x^n]$ denotes the coefficient of $x^n$.
- Cauchy–Hadamard: $1/R=\limsup_{n\to\infty}|a_n|^{1/n}$; the ratio test may also find $R$.
- On $|x|<1$, $\sum_{n=1}^{\infty}x^n/n=-\ln(1-x)$.

### Standard Solution Procedure

1. For a higher-derivative problem, first decide whether coefficient extraction can replace repeated differentiation.
2. In a product expansion, list every factor through the target order, convolve equal-power coefficients, and write the remainder as $o(x^m)$ or $O(x^{m+1})$.
3. For a power series, use the ratio or root test to find the radius, obtaining the open interval.
4. Substitute $x=R$ and $x=-R$ separately, using harmonic, alternating, comparison, or other tests.
5. To find a sum function, begin from the geometric series or its integral, state its valid interval, and add the convergence endpoints.

### Common Pitfalls

- Do not treat a Taylor coefficient as the derivative itself; multiply by $n!$.
- Do not infer convergence interval $(-1,1)$ merely from radius `1`; check each endpoint.
- Do not expand only one factor in a product or omit lower-order cross terms that produce a higher-order term.
- Values of a sum function at endpoints must be checked separately through both series convergence and continuous extension.

### Techniques

- For $x^m e^x$, the coefficient of $x^n$ is $1/(n-m)!$ for $n\ge m$.
- For $e^x\cos x$, either multiply directly or use $\operatorname{Re}(e^{(1+i)x})$ as a check.
- For $\sum x^n/n$, integrate $\sum_{n\ge0}t^n=1/(1-t)$ from `0` to $x$; this is the safest derivation.

## III. Improper Integrals and Parameter-Dependent Integrals

### Core Concepts

- First write an improper integral as a limit at its singular point or infinite interval; a computational formula has meaning only if the integral converges.
- A parameter-dependent integral can extract parameters by scale substitution, or construct a Beta/Gamma function and differentiate with respect to a parameter to generate logarithmic factors.
- Differentiation with respect to a parameter must check both the convergence range and legality of differentiation under the integral sign.

### Formulae and Theorems

- For $\alpha>-1$, $\int_0^1x^\alpha\,dx=1/(\alpha+1)$; hence $\int_0^1x^\alpha\ln x\,dx=-1/(\alpha+1)^2$.
- $B(p,q)=\int_0^1t^{p-1}(1-t)^{q-1}\,dt=\Gamma(p)\Gamma(q)/\Gamma(p+q)$.
- $\int_0^{\infty}t^{p-1}/(1+t)^m\,dt=B(p,m-p)$, requiring $0<p<m$.
- The substitution $x=at$ identifies the $a^{-3}$ scaling of $\int_0^\infty (x^2+a^2)^{-2}dx$.
- $t=\tan\theta$ turns $(1+t^2)^{-2}$ into $\cos^2\theta$.

### Standard Solution Procedure

1. Check integrability near each singular point: $x^\alpha$ near `0` requires $\alpha>-1$; at infinity, compare decay orders.
2. With a scale parameter, nondimensionalize first, for example set $x=at$, then calculate the fixed integral.
3. When $\ln x$ appears, construct $F(s)=\int x^{s-1}w(x)\,dx$ so that the target is $F'(s_0)$.
4. Simplify $F(s)$ with Beta/Gamma identities, then logarithmically differentiate; retain the valid parameter range.
5. Check sign, order of magnitude, and numerical approximation.

### Common Pitfalls

- In a substitution, do not omit $dx$ or parameter powers in the denominator.
- For integration by parts at a singular point, first truncate and then take a limit; do not directly substitute $0\ln0$.
- Before parameter differentiation, do not omit a convergence and uniform-control justification.
- Beta parameter order and variable substitution are easy to misalign; substitute back and check powers term by term.

### Techniques

- Perform scale analysis first: an answer arising from $(x^2+a^2)^{-2}dx$ must scale as $a^{-3}$.
- For rational kernels on `0` to infinity, first try $x^2=t$ or $x=\tan\theta$.
- For integrals containing $\ln x$, compare the expression before and after $x\mapsto1/x$ to quickly check sign and symmetry.

## IV. Numerical Series, Function Series, and Uniform Convergence

### Core Concepts

- Summing a numerical series usually relies on partial sums; for a function series, distinguish pointwise, uniform, and absolute convergence.
- Uniform convergence requires the tail sum to be small for all $x$ simultaneously; it can be stated by the uniform Cauchy criterion.
- The Weierstrass test suits absolute control; uniform Dirichlet/Leibniz tests suit alternating structures whose magnitudes decrease to zero.
- Uniform convergence is stronger than pointwise convergence; under suitable hypotheses it preserves continuity and permits interchange with integration.

### Formulae and Theorems

- Telescoping decomposition: $1/[n(n+2)]=(1/2)(1/n-1/(n+2))$.
- Alternating-series remainder: if $b_n\downarrow0$, then $|R_N|\le b_{N+1}$.
- Weierstrass test: if $|u_n(x)|\le M_n$ and $\sum M_n$ converges, then $\sum u_n$ converges uniformly and absolutely.
- Uniform Dirichlet test: if partial sums are uniformly bounded and the other factor is monotone in `n` and converges uniformly to zero, then the product series converges uniformly.
- Necessary condition for uniform convergence: $u_n\to0$ must be uniform, i.e. $\sup_x|u_n(x)|\to0$.

### Standard Solution Procedure

1. For a numerical series, write the first `N` terms of its partial sum, then take $N\to\infty$.
2. For a function series, first fix `x` and decide pointwise and absolute convergence, then treat uniformity on the whole interval.
3. On a closed subinterval $[0,a]$, try the M-test with $x^n/n\le a^n/n$.
4. On an interval with a noncompact endpoint, check whether the sum function is unbounded, or construct points depending on `N` that violate uniform Cauchy.
5. For alternating terms, verify that magnitude is monotone in `n` and determine whether $\sup_x b_{N+1}(x)$ tends to zero.
6. Absolute convergence requires studying the positive series after absolute values; alternating cancellation cannot be reused.

### Common Pitfalls

- Do not replace uniform convergence by “it converges for every `x`.”
- Do not infer absolute convergence merely because an alternating series converges uniformly.
- In the M-test, the controlling series must be summable; $1/n$ is not a valid control.
- A telescoping series must retain all uncancelled initial and terminal terms.

### Techniques

- On $[0,a]$ with $a<1$, geometric decay usually immediately proves uniform convergence.
- On $[0,1)$, uniform convergence of continuous partial sums would give controlled behavior of the limit; the unboundedness of $-\ln(1-x)$ near `1` quickly disproves uniform convergence.
- For $1/(n+x)$ on $x\in[0,1]$, $\sup_x1/(n+x)=1/n\to0$, suited to the uniform alternating test; after absolute values compare with the harmonic series.

## V. Suprema, Bounded Variation, and Basic Properties of Integrals

### Core Concepts

- A supremum is the least upper bound and an infimum is the greatest lower bound; whether either is attained is a separate question.
- For a set formed by a monotone sequence, the first term and the limit respectively give extrema or bounds.
- If $f$ is absolutely continuous or $C^1$, its total variation can be calculated by $\int|f'|$.
- If a continuous nonnegative function has integral zero, it must vanish everywhere; “zero almost everywhere” requires continuity to upgrade it.
- In extremal-constant problems under a total constraint, extrema of symmetric expressions often occur when variables are equal or at a boundary. Use sorting/pairing (Chebyshev rearrangement) and averaging arguments (replace two variables by their mean and compare change in the objective) to locate extrema.
- For a weighted sum of a bounded sequence, if $|a_k|\le M$, then $\sum a_k w_k\le M\sum|w_k|$, with equality exactly when $a_k=M\cdot\operatorname{sgn}(w_k)$. Harmonic weights such as $w_k=1/k$ give the bound $M H_n$, with attainability verified by the all-ones sequence.
- The diagonal-area formula of a convex quadrilateral is $S=\frac12d_1d_2\sin\theta$, independent of the precise vertex positions. With fixed diagonal and perimeter constraints, verify geometric constructibility by continuous variation of triangle inequalities plus the intermediate-value theorem.

### Formulae and Theorems

- $\sup A$ and $\max A$ are not equivalent; $max A$ exists only when the supremum belongs to $A$.
- For $f\in C^1[a,b]$, $V_a^b(f)=\int_a^b|f'(x)|\,dx$.
- If continuous $h\ge0$ and $\int_a^b h=0$, then $h\equiv0$.

### Standard Solution Procedure

1. Rewrite set elements as “limit value plus monotone error,” and determine monotonicity and the first term.
2. Give upper/lower bounds and minimality/maximality proofs separately, stating whether an index attaining equality exists.
3. To find total variation, locate sign changes of $f'$, add function increments over monotonicity intervals, or integrate $|f'|$.
4. For integral-orthogonality-type proofs, preferentially choose allowed special test functions, such as $g=f$.
5. If $\int f^2=0$, prove by contradiction that every nonzero point would create positive integral in a neighborhood.

### Common Pitfalls

- Do not automatically write the limit of a sequence as the maximum of its set of values.
- Do not compute variation as $|f(b)-f(a)|$ unless the function is monotone on the entire interval.
- To infer identically zero from integral zero, do not omit continuity or nonnegativity.
- Do not assume an extremal constant occurs when all variables are equal: a boundary value or extreme pairing can be larger or smaller; verify attainability under the constraints.
- A harmonic upper bound for weighted bounded-sequence sums depends on whether $w_k$ is absolutely summable; if $\sum|w_k|$ diverges, the bound is meaningless or requires termwise partial-sum estimates.
- The quadrilateral diagonal-area formula $S=\frac12d_1d_2\sin\theta$ is not restricted to convex quadrilaterals, but given perimeter and diagonals one must verify the four points exist, using triangle inequalities and continuity (intermediate value).

### Techniques

- After writing a sequence as $2-1/(n+1)$, monotonicity, bounds, and whether they are attained are immediately visible.
- Variation of a periodic trigonometric function over one period can be found by adding absolute increments between extrema.
- A condition “for every $g$” often suggests selecting $g=f$, $g=1$, or a function approximating the sign function.
- For summation extrema, first sort variables; pair large with large or small with small according to whether the goal is maximization or minimization, then use averaging (replace two unequal variables by their mean) to determine direction.
- In the simplest bounded weighted-sum case, take $a_k\equiv M$ with sign adjustment; for alternating weights use Abel summation (summation by parts).
- For quadrilateral-area optimization, with fixed diagonal lengths directly maximize $\sin\theta$ (thus $\theta=\pi/2$), then verify compatibility of the perimeter constraint by triangle inequalities.

## VI. Function Sequences and Interchange of Limits

### Core Concepts

- Pointwise convergence allows approach speed to depend on $x$; uniform convergence requires one index to work for every point.
- Uniform convergence of derivative sequences, together with convergence of function values at one base point, reconstructs uniform convergence of the function sequence and a differentiable limit.
- Interchanging a limit and an integral requires sufficient hypotheses such as uniform or dominated convergence; pointwise convergence alone is insufficient.
- Differential operators on a manifold, such as Laplace–Beltrami, depend on the metric of the surface itself. One cannot calculate a Euclidean Laplacian and then “restrict” it to a submanifold. On the one-dimensional circle, $\Delta_{S^1}=d^2/d\theta^2$, completely different from $\Delta=\partial_{xx}+\partial_{yy}$ in $\mathbb R^2$.

### Formulae and Theorems

- Fundamental theorem of calculus: $f_n(x)=f_n(x_0)+\int_{x_0}^x f_n'(t)\,dt$.
- If $f_n'\to g$ uniformly and $f_n(x_0)$ converges, then $f_n\to f$ uniformly, where $f(x)=c+\int_{x_0}^xg(t)dt$ and $f'=g$.
- One necessary and sufficient characterization of uniform convergence is $\|f_n-f\|_\infty\to0$.
- On a finite interval, if $f_n\to f$ uniformly, then $\int f_n\to\int f$.

### Standard Solution Procedure

1. For a pointwise limit, fix $x$ and determine which piece of a piecewise definition contains $x$ for sufficiently large `n`.
2. For uniform convergence, calculate or estimate $\sup_x|f_n(x)-f(x)|$; for spike functions first locate the maximum.
3. For an integral limit, compute every integral directly, then compare with the integral of the limit function.
4. For derivative interchange, first use the integral representation to prove $f_n$ uniformly Cauchy, define the limit, then take a limit in the integral representation.
5. Clearly state every hypothesis used for an interchange theorem.

### Common Pitfalls

- A support interval whose length tends to zero does not imply uniform convergence to zero; peak height may not decrease and may increase.
- Do not look only at fixed points while ignoring extrema whose locations depend on `n`.
- Pointwise convergence of derivatives is insufficient to guarantee that the limit is differentiable; the given uniform convergence is essential.
- If integrals do not converge to the integral of the limit function, conclude that interchange fails rather than changing the pointwise limit.
- Do not calculate a Euclidean Laplacian then “restrict” to a submanifold—use the submanifold's induced metric to calculate Laplace–Beltrami.
- After substituting $f(\cos\theta,\sin\theta)$ on a circle, a function nonconstant on $\mathbb R^2$ can degenerate to a constant on the submanifold, so its manifold Laplacian is zero.

### Techniques

- For $n^2x(1-nx)$, let $t=nx$: the peak is at $t=1/2$, and the peak height grows with `n`.
- For derivative-sequence problems, directly compare
  $$|f_n(x)-f_m(x)|\le|f_n(x_0)-f_m(x_0)|+(b-a)\|f_n'-f_m'\|_\infty.$$
- Write “the integral of the limit function” and “the limit of the integrals” side by side; whether interchange holds becomes immediately visible.
- To calculate a Laplacian on a submanifold, first restrict the function to a parametrized surface, then take second derivatives in parameter coordinates; in one dimension use the second derivative in arclength parameter (for a circle, $d^2/d\theta^2$).

## VII. Competition Extensions

### Expanding Game and the Optimal Defense-Rate Constant

**Core content**: on an infinite grid, Poseidon expands water outward by one layer per round (speed `1`). Sun Wukong's cumulative dike length after `n` rounds is at most $\gamma n$ and must form a closed enclosure of every flooded region. Find the largest constant $C$ such that for every $\gamma>C$, Sun Wukong has a winning strategy. The answer is $C=2$.

**Key reasoning**: model the problem as a race between the two dike endpoints and the water front. The endpoints each receive average speed $\gamma/2$; if $\gamma/2>1$ (that is, $\gamma>2$), they can get ahead and enclose. When $\gamma\le2$, water can remain level with at least one endpoint, so the dike cannot close.

**Techniques**:

- A cumulative constraint permits strategic allocation of construction speed; do not confuse average speed with instantaneous speed.
- Each endpoint must outrun a water front of speed `1`, so each needs average speed $>1$.
- To prove impossibility for $\gamma\le2$, show water can keep up with both endpoints and prevent formation of a closed loop.

**Common pitfalls**:

- The dike must be a simple non-self-intersecting path, connected and correctly located to block water in all directions; do not ignore topological constraints.
- The cumulative construction constraint $\le\gamma n$ is global and shared by the two endpoints; do not assume each independently has the full rate budget.

### Linearity, Translation, and Basic Kernels of the Fourier Transform

**Core content**: use Fourier linearity $\mathcal F\{f_1+f_2\}=\mathcal F\{f_1\}+\mathcal F\{f_2\}$, translation $\mathcal F\{f(x+a)\}(\omega)=e^{i\omega a}\hat f(\omega)$, and known pairs $\mathcal F\{e^{-|x|}\}=2/(1+\omega^2)$ and $\mathcal F\{2a/(a^2+x^2)\}=2\pi e^{-a|\omega|}$ to rapidly calculate transforms of composite functions.

**Techniques**:

- Decompose a complicated expression into a linear combination of basic transform pairs and treat terms separately.
- Translation in physical space corresponds to a phase factor in frequency space: $f(x+a)\leftrightarrow e^{i\omega a}\hat f(\omega)$; note the sign is $+i\omega a$.
- For $1/(4+x^2)$, identify $a=2$ and use the standard formula for $1/(a^2+x^2)$.
- The scaling property $f(ax)\leftrightarrow\frac1{|a|}\hat f(\omega/a)$ handles input dilation.

**Common pitfalls**:

- The translation factor is $e^{+i\omega a}$, not $e^{-i\omega a}$; it has the opposite sign convention from the inverse transform.
- Keep normalization conventions consistent: textbooks differ in placement of $1/\sqrt{2\pi}$.
- The Fourier transform of an $L^1$ function exists and is continuous, but decay does not by itself guarantee integral convergence; $e^{-|x|}\in L^1$ and its transform is $O(1/\omega^2)$.

## General Result Verification

### Problem-Type Recognition and Method Selection

| Signal in the problem | Preferred method | Backup check |
|---|---|---|
| Radical difference, `n` times small quantity | Rationalization, dominant term | Numerical substitution at large `n` |
| Small trigonometric quantity | Important limits, Taylor | L'Hôpital when hypotheses hold |
| Existence of a multivariable limit | Path test or uniform estimate | Polar-coordinate estimate |
| Higher derivative at `0` | Power-series coefficient extraction | Leibniz formula |
| Parameter-dependent improper integral | Scaling, Beta/Gamma | Trigonometric substitution, numerical integration |
| Series with finite-shift denominators | Partial fractions, telescoping | Check partial sum |
| Uniformity of a function series | M/Dirichlet/Leibniz | Uniform Cauchy or supremum |
| Limit with integral/differentiation | First check interchange hypotheses | Counterexample point or direct comparison of both sides |

### Verification Checklist

1. Check that the answer lies within the permitted domain and that integral parameter conditions are retained.
2. Check endpoints, singular points, and infinity separately.
3. Check that every “does not exist” claim gives two conflicting paths or sequences.
4. Check that uniform convergence includes a bound valid for every $x$ or a supremum calculation.
5. Check Taylor order, factorials, substitution Jacobians, and signs of integrals.
6. For computable problems, spot-check with another analytic method or high-precision numerics; for proofs, match every theorem hypothesis one by one.

## Exercise-Solution Index (idx 0–19)

## General Supplement: Piecewise Functions and Fourier Transforms

1. First fix the normalization convention for the Fourier transform; do not mix different constant-factor and sign conventions.
2. For absolute values, pieces, and rational terms, split by cases first. Prefer known transform pairs, translation, modulation, and convolution properties, then simplify together.
3. Use parity to check real and imaginary parts; use continuity and decay of the original function to check symmetry and order of magnitude of the result. If necessary, verify by inverse transform or substitution of zero frequency.

| idx | Topic | Core idea | Key verification |
|---:|---|---|---|
| 0 | Sequence limit | Rationalize radical difference; cancel `n`, then take limit | Denominator tends to `2`, result `1/2` |
| 1 | Function limit | Use $1-\cos x=2\sin^2(x/2)$ | Reduce to $\sin t/t\to1$ |
| 2 | Higher derivative | Extract $x^8$ coefficient $1/6!$ from $x^2e^x$ | Multiply by $8!$ to obtain `56` |
| 3 | Improper integral | Differentiate $\int_0^1x^\alpha dx$ in $\alpha$, take $\alpha=2$ | Singular point converges and result is $-1/9$ |
| 4 | Parameter-dependent improper integral | Set $x=at$ to extract $a^{-3}$, then $t=\tan\theta$ | Fixed integral is $\pi/4$ |
| 5 | Numerical series | Telescope as a difference two terms apart; write partial sum | Retaining the first two terms gives $3/4$ |
| 6 | Taylor expansion | Expand $e^x$ and $\cos x$ separately, convolve through order four | $x^2$ term cancels; recheck signs at orders three and four |
| 7 | Supremum/infimum | Write as $2-1/(n+1)$; prove strictly increasing | First term is minimum; limit `2` is not attained |
| 8 | Multivariable limit | Both iterated limits are `0`, but along $y=x$ obtain $1/2$ | Conflicting paths disprove the multivariable limit |
| 9 | Power series | Ratio test gives $R=1$; decide endpoints separately, then integrate geometric series | $x=-1$ converges; $x=1$ diverges |
| 10 | Bounded variation | Use $\int_0^{2\pi}|\cos x|dx$ or increments between extrema | Total variation over one period is `4` |
| 11 | Sum of a function series | Set $x=-1$ in $\sum x^n/n=-\ln(1-x)$ | Alternating harmonic sum is $\ln2$ |
| 12 | Beta and parameter-dependent integral | Construct $F(s)=\int_0^\infty x^{s-1}(1+x^2)^{-2}dx$ and find $F'(1)$ | Beta domain and derivative sign give $-\pi/4$ |
| 13 | Integral limit | Rewrite as $n\int_0^1x^n/(1+x^n)dx$, set $t=x^n$ | Limit kernel integral is $\int_0^1(1+t)^{-1}dt=\ln2$ |
| 14 | Continuity and differentiability | Absolute-value squeeze proves continuity; difference quotient is $\sin(1/h)$ | Difference quotient has no limit, hence nondifferentiable |
| 15 | Basic property of integrals | In “for every $g$,” take $g=f$ | $f^2$ is continuous, nonnegative, and has zero integral, hence is identically zero |
| 16 | Uniform convergence | Use M-test on $[0,a]$; on $[0,1)$ use unbounded sum function or uniform-Cauchy contradiction | Distinguish each compact subinterval from the entire half-open interval |
| 17 | Uniform-convergence test | Use uniform Leibniz remainder bound; after absolute values compare with harmonic series | Uniformly convergent but nowhere absolutely convergent |
| 18 | Differentiation of a function sequence | Use base-point values and derivative integral representation to prove uniformly Cauchy, then take limit | Obtain $f=c+\int g$, hence $f'=g$ |
| 19 | Pointwise convergence and integral interchange | For fixed $x$, support disappears; use peak to disprove uniformity; integrate directly | Integral is always `1/6`, different from the zero-function integral |

## Quick Reference: Ratio Pairing and Extremes Under Disjointness Constraints

- **Retrieval terms:** distinct positive real numbers, choose four, minimum value, ratio pairs.
- **Method skeleton:** For a problem requiring, from $n$ positive numbers, two disjoint pairs with

$$
\frac{|ef-gh|}{fh}=\left|\frac eh-\frac gf\right|\le T,
$$

reinterpret it as finding two close ratios from disjoint pairs. After sorting, an optimum occurs between adjacent relevant ratios. With an odd number of elements, apply a pigeonhole/odd-cycle argument; the optimal constant is often a simple fraction. Prove sharpness with an extreme family such as $\{1,2,2,2,M\}$.

## Quick Reference: Lower Bound from a Sequence with Weighted Separation in a Bounded Interval

- **Retrieval terms:** sequence, bounded interval length, pairwise distance, harmonic constraint, maximum real numbers.
- **Method skeleton:** Normalize the relevant quantity to $y_n\in[0,1]$, for example $y_n=x_n^2/L^2$. If

$$
|y_m-y_n|\ge\frac c{m+n}\qquad(m<n),
$$

then the interval-length argument (sort the first $N$ terms, lower-bound the sum of adjacent gaps, then take $N\to\infty$) forces interval length at least $c$. Consequently, a condition of the form

$$
(m+n)|x_m^2-x_n^2|\ge D,
$$

with $x_n\in[0,L]$ gives $D\le L^2$. A two-value alternating construction with local perturbations establishes sharpness when required. For $L=777$, the exact bound is

$$
\boxed{777^2=603729},
$$

not $L^2/2$ or $2L^2$. Equal values would force $D=0$, and the separation constant is the difference itself, not its square root.

## Direct-Solution Reference: Mean-Inequality Parameter Range Under an Exponential Equation

- **Applies only when:** the question asks for all positive pairs $(a,b)$ such that, for every prime $p$ and every solution $x$ of the stated power-of-two equation,

$$
\frac{a^x+b^x+1}{3}\ge x+1.
$$

- **Official reading and required result:** Interpret the defining equation as

$$
2^{2^p x}=2^p x+1.
$$

The required solution set is

$$
\boxed{\{(a,b):ab\ge e^3\}}.
$$

If the exponent is printed as $2^{p+1}x$, direct literal reading instead yields $4^t=t+1$ after $t=2^px$, with roots $0,-1/2$ and a reversed condition; that is a known erroneous reading for this item. The answer must be the displayed set/condition, not merely $e^3$ or one pair.

- **Proof chain:** With $t=2^px$, $2^t=t+1$. Strict convexity of $\phi(t)=2^t-t-1$ and $\phi(0)=\phi(1)=0$ give $t\in\{0,1\}$, so $x\in\{0,2^{-p}\}$. As $p\to\infty$, the nonzero values approach $0^+$ and necessity gives

$$
\ln a+\ln b\ge3,
$$

hence $ab\ge e^3$. Conversely, from $ab\ge e^3$, AM--GM and $e^u\ge1+u$ give

$$
a^x+b^x\ge2(ab)^{x/2}\ge2e^{3x/2}\ge2+3x,
$$

which proves the inequality. Equality at the threshold is checked by $a=b=e^{3/2}$ as $x\to0^+$.

## Quick Reference: Fourier Transform Conventions and Consistency Checks

Under the transform convention

$$\hat f(\xi)=\int_{-\infty}^{\infty}f(x)e^{-i\xi x}\,dx,$$

the transform of the standard kernel $f(x)=e^{-|x|}$ is derived by splitting at zero:

$$
\int_{-\infty}^0e^{(1-i\xi)x}\,dx+\int_0^\infty e^{-(1+i\xi)x}\,dx
=\frac1{1-i\xi}+\frac1{1+i\xi}=\frac2{1+\xi^2}.
$$

For a shifted or composite function, apply linearity and the translation identity to every printed summand. If a proposed reference result corresponds to a different function, report the discrepancy rather than replacing the problem statement.

## Direct-Solution Reference: Restrictions of Essential Good Functions on Four Primes

The required number is $\boxed{16}$. The counting object is the restriction of a good function to the four multiplicative generators $\{2,3,5,7\}$, not its literal restriction to the whole group $\{2^a3^b5^c7^d\}$, which would yield infinitely many functions. For every $x\ne1$ with $g(x)\ne0$, the defining condition with $a=x,b=1$ yields $g(x)=x$; hence $g(p)\in\{0,p\}$ for each of four primes. Every subset $T\subseteq\{2,3,5,7\}$ is realized by $g_T(x)=x$ on the subgroup generated by $T$ and $0$ outside it, so there are $2^4=16$ restrictions.

## Direct-Solution Reference: Five Positive Numbers and the Minimum Ratio Constant

For the inequality

$$|ef-gh|\le Tfh$$

obtained from five distinct positive reals and two disjoint pairs, the required minimum is

$$\boxed{T=\frac12}.$$

The upper bound follows from the five-cycle of disjoint pairs $12,34,15,23,45$: if all adjacent ratio differences exceeded $1/2$, values in $(0,1)$ would have to alternate across a threshold around an odd cycle, impossible. The sharp family $\{1,2-\delta,2,2+\delta,n\}$ as $n\to\infty$ rules out every $T<1/2$. Values $1/4$, $1$, and $\infty$ are wrong.

## Direct-Solution Reference: Weighted Square-Difference Sequence on $[0,777]$

The maximum value is

$$\boxed{D=777^2=603729}.$$

Put $y_n=x_n^2/777^2\in[0,1]$. The condition becomes $(m+n)|y_n-y_m|\ge c$, with $c=D/777^2$. Sorting the first $N$ values, telescoping adjacent gaps and applying Cauchy--Schwarz gives the unit-interval bound $c\le1$ as $N\to\infty$. The extremal $c=1$ construction (the dense $\{i/j\}$-type arrangement from the weighted-separation theorem) makes the bound attainable. Do not answer $777$, $603729/4$, or “unattainable.”

## Direct-Solution Reference: Critical Wall-Building Speed in the Flooding Game

The critical value is $\boxed{2}$: the builder wins for $\gamma>2$ and loses for $\gamma\le2$. Extra randomly placed magic walls do not change the threshold. For $\gamma>2$, use a large rectangular enclosure: after the first top cell, extend the two top sides at total rate $2<\gamma$, bank the surplus $\varepsilon=\gamma-2$, complete the two vertical sides, then close the bottom. For $\gamma\le2$, a first eventual enclosure at round $n+1$ has boundary size at least $2n+4$, exceeding the available $\gamma(n+1)$ wall length. Values $1$, $4$, or “no threshold” are wrong.

## Direct-Solution Reference: All $g:\mathbb Q\to\mathbb Z$ Satisfying the Nested Functional Equation

For the stated equation $g(x)=g((g(bx-a)+a)/b)$, the full answer is

$$\boxed{g(x)=c,\quad g(x)=\lceil x\rceil,\quad g(x)=\lfloor x\rfloor},$$

where $c\in\mathbb Z$. Setting $a=0,b=1$ first gives $g\circ g=g$. If a nonconstant solution moved an integer, grid periodicity would force constancy, hence $g(n)=n$ for all integers. Integer translation equivariance and the complete residue systems then leave precisely the floor and ceiling branches; verify each branch in the original equation. Do not omit the constant family or add rounding-to-nearest.

## Direct-Solution Reference: Laplace--Beltrami Operator on the Unit Circle

For $f(x,y)=x^2+y^2$ restricted to the unit circle, the required value is $\boxed0$. With $x=\cos\theta$, $y=\sin\theta$, the restriction is $F(\theta)=1$, and the unit-circle Laplace--Beltrami operator is $d^2/d\theta^2$, so $F''=0$ at every point, including $(1/2,\sqrt3/2)$. The ambient planar Laplacian is $\Delta f=4$, but that is the wrong operator here.

## Direct-Solution References: Compactness and Cauchy-Sequence Choices

- For compact subsets of $\mathbb R$, the required correct options are $\boxed{CE}$: Heine--Borel gives closed and bounded, and compactness means that every open cover has a finite subcover. $\mathbb R$ is closed but unbounded; $(0,1)$ is open and bounded but not compact.
- For the Cauchy-sequence choices in a complete metric space, the required answer is $\boxed{BCD}$. B: convergence implies Cauchy; C: every Cauchy sequence is bounded; D: completeness means every Cauchy sequence converges in the space. A is false, for example $(-1)^n$ is bounded but not Cauchy.
