# Numerical Analysis Skill

## Domain Boundaries and Routing Conventions

- Scope: errors, interpolation, numerical integration/differentiation, root finding, linear systems, condition numbers, stability, and PDE discretization.
- Do not take over: analytic PDE solutions or adjoint derivations should be routed to partial differential equations; estimation and inference in statistical regression should be routed to linear regression or statistical inference.
- Verification contract: state nodes, step size, error order, norm used for the condition number, and stability interval; independently check approximate values using high-precision computation.

> This manual covers the core numerical-analysis system, organized by modules of definitions, theorems, formulas, standardized solution procedures, and examination techniques, with an index of 20 typical exercises.

## Final-Answer Field Contract

- Do not invent nodes, step sizes, initial values, or matrices not given in the problem. Every intermediate node and weight must come from the statement; this manual and verification prompts may provide only formulas and checking order.
- A numerical-integration answer must state step size, nodes, formula name, and summation expression. If the problem asks for an exact form, prioritize the standard weighted-parenthesis form.
- A Newton/iteration answer must give the iteration formula, the specified iterate, and an exact fraction/decimal; do not give only an approximate root.
- A numerical-differentiation answer must list the approximate value, exact value, and absolute-error expression.
- A condition-number/stability/numerical-ODE answer must state the norm or amplification factor, stability interval, critical step size, and conclusion.

## High-Frequency Errors and Convention Rules (Judge Feedback 2026-07-07)

- **Endpoint convention for the absolute-stability interval:** for explicit Euler applied to $y'=\lambda y$ with $\lambda<0$, absolute stability requires $|1+h\lambda|<1$, equivalently $0<h(-\lambda)<2$. Under the “asymptotically stable” convention, **endpoints are strict**: at $h(-\lambda)=2$, the solution oscillates without decay and is only bounded. By default write the strict inequality $0<h\lambda<2$ when $\lambda$ denotes the positive decay rate, and state the convention used.
- **Least-squares fitting must be independently checked with normal equations:** for line $y=a+bx$, explicitly list $n,\sum x_i,\sum y_i,\sum x_i^2,\sum x_iy_i$, solve

  $$\begin{cases}na+b\sum x_i=\sum y_i,\\a\sum x_i+b\sum x_i^2=\sum x_iy_i,\end{cases}$$

  and substitute back into both equations to verify. Do not skip directly to coefficients.

---

## 1. Error Analysis

### Core Definitions

| Concept | Definition |
|---|---|
| **Absolute error** | Difference between approximation $x^*$ and true value $x$: $e=x^*-x$ |
| **Relative error** | Absolute error divided by true value: $\delta=(x^*-x)/x$ or $\delta=|x^*-x|/|x|$ |
| **Significant digits** | Digits counted from the first nonzero digit to the digit at which error occurs |

### Core Formulas

$$e=x^*-x\qquad\text{(absolute error)},$$

$$\delta=\frac ex\qquad\text{(relative error)}.$$

### Standard Solution Procedure

1. Identify approximate and true values.
2. Calculate absolute error $e=x^*-x$.
3. Calculate relative error $\delta=e/x$.
4. Convert to percentage or significant-digit form if required.

### Frequent Examination Pitfalls

- The denominator in relative error is the true value, not the approximation.
- If the true value is unknown and the approximation is substituted, state that fact.
- Absolute and relative errors both have signs.

### Examination Techniques

- When approximating an irrational number by a rational number, retain fractional form when possible.
- Compare error magnitudes using scientific notation.

---

## 2. Interpolation

### 2.1 Lagrange Interpolation

#### Core Definitions and Theorems

- For $n+1$ distinct nodes $(x_i,f(x_i))$, there exists a unique polynomial $P_n(x)$ of degree $n$ satisfying $P_n(x_i)=f(x_i)$.
- **Interpolation basis:**

  $$L_k(x)=\prod_{j\ne k}\frac{x-x_j}{x_k-x_j}.$$

#### Core Formulas

$$P_n(x)=\sum_{k=0}^nf(x_k)L_k(x).$$

**Two-point linear interpolation** ($n=1$):

$$P_1(x)=f(x_0)\frac{x-x_1}{x_0-x_1}+f(x_1)\frac{x-x_0}{x_1-x_0}.$$

**Three-point quadratic interpolation** ($n=2$):

$$
P_2(x)=f(x_0)\frac{(x-x_1)(x-x_2)}{(x_0-x_1)(x_0-x_2)}+f(x_1)\frac{(x-x_0)(x-x_2)}{(x_1-x_0)(x_1-x_2)}+f(x_2)\frac{(x-x_0)(x-x_1)}{(x_2-x_0)(x_2-x_1)}.
$$

#### Standard Solution Procedure

1. Determine number and values of nodes.
2. Construct every basis function $L_k(x)$.
3. Form the weighted sum to obtain $P_n(x)$.
4. Substitute the requested $x$ to get the approximation.

#### Frequent Pitfalls

- Attend to denominator signs: directions $x_k-x_j$ and $x_j-x_k$ cannot be interchanged.
- Nodes must be distinct.
- High-degree interpolation can exhibit the Runge phenomenon.

#### Examination Techniques

- For symmetric nodes, first inspect patterns in function values to simplify calculation.
- Check interpolation conditions $P_n(x_i)=f(x_i)$.

### 2.2 Interpolation Remainder and Error Analysis

#### Core Formulas

For $f\in C^{n+1}[a,b]$, the **Lagrange interpolation remainder** is

$$R_n(x)=f(x)-P_n(x)=\frac{f^{(n+1)}(\xi)}{(n+1)!}\prod_{i=0}^n(x-x_i),$$

where $\xi$ lies in the interval between $x$ and the nodes.

For linear interpolation ($n=1$),

$$R_1(x)=\frac{f''(\xi)}2(x-x_0)(x-x_1).$$

#### Standard Solution Procedure

1. Determine nodes $x_0,x_1,\ldots,x_n$.
2. Calculate $f^{(n+1)}(\xi)$.
3. Evaluate $\prod(x-x_i)$ at the specified point.
4. Combine with a derivative bound to obtain an error range.

#### Frequent Pitfalls

- The specific location of $\xi$ cannot be determined; use a maximum-modulus estimate.
- The remainder formula requires sufficient smoothness.

---

## 3. Numerical Integration

### 3.1 Midpoint Rule

#### Core Formula

$$\int_a^bf(x)\,dx\approx(b-a)f\left(\frac{a+b}{2}\right).$$

**Error** (exact for quadratic functions):

$$E_M=\frac{(b-a)^3}{24}f''(\xi),\qquad\xi\in(a,b).$$

#### Standard Solution Procedure

1. Take midpoint $c=(a+b)/2$.
2. Calculate $f(c)$.
3. Integral approximation $=(b-a)\times f(c)$.
4. Compare with exact value to obtain error.

### 3.2 Trapezoidal Rule

#### Core Formula

$$\int_a^bf(x)\,dx\approx\frac{b-a}{2}[f(a)+f(b)].$$

**Error:**

$$E_T=-\frac{(b-a)^3}{12}f''(\xi),\qquad\xi\in(a,b).$$

#### Standard Solution Procedure

1. Find endpoint function values $f(a),f(b)$.
2. Substitute into the trapezoidal formula.
3. If error analysis is required, find a maximum bound for $f''(\xi)$.

#### Examination Techniques

- Algebraic precision is at least $1$: exact for linear polynomials.
- For a concave function with $f''(x)>0$, the trapezoidal rule overestimates the integral; it underestimates for a convex function.

### 3.3 Simpson's Rule

#### Core Formula

$$\int_a^bf(x)\,dx\approx\frac{b-a}{6}\left[f(a)+4f\left(\frac{a+b}{2}\right)+f(b)\right].$$

**Error:**

$$E_S=-\frac{(b-a)^5}{2880}f^{(4)}(\xi),\qquad\xi\in(a,b).$$

#### Core Properties

- **Algebraic precision $3$:** exact for every polynomial of degree at most three.
- Three-point, second-order Newton--Cotes formula.

#### Standard Solution Procedure

1. Calculate $f(a)$, $f((a+b)/2)$, and $f(b)$.
2. Compute

   $$S=\frac h3[f(a)+4f(\text{mid})+f(b)],\qquad h=\frac{b-a}{2}.$$

3. Compare with exact value to validate.

### 3.4 Composite Quadrature Formulas

#### Core Formulas

**Composite trapezoid** ($n$ equal subintervals, $h=(b-a)/n$):

$$T_n=\frac h2\left[f(x_0)+2\sum_{i=1}^{n-1}f(x_i)+f(x_n)\right].$$

**Composite Simpson** ($2n$ equal subintervals, $h=(b-a)/(2n)$):

$$S_n=\frac h3\left[f(x_0)+4\sum_{i=1}^{n}f(x_{2i-1})+2\sum_{i=1}^{n-1}f(x_{2i})+f(x_{2n})\right].$$

#### Standard Solution Procedure

1. Determine $n$ and $h$.
2. Enumerate all nodes $x_i$.
3. Calculate function values at all nodes.
4. Form the weighted sum according to the formula.

#### Frequent Examination Pitfalls

- $n$ is the number of subintervals; there are $n+1$ nodes.
- In composite trapezoid, all interior coefficients are $2$ and both endpoints have coefficient $1$.
- Retain exact intermediate expressions, such as expressions involving $e$; decimals are not required.

### 3.5 Romberg Extrapolation Acceleration

#### Core Formulas

Romberg recurrence (Richardson extrapolation):

$$T_m^{(k)}=\frac{4^kT_{m+1}^{(k-1)}-T_m^{(k-1)}}{4^k-1}.$$

Common form, extrapolating trapezoid to Simpson:

$$S=\frac{4T(h/2)-T(h)}3.$$

#### Standard Solution Procedure

1. Compute $T(h)$, the composite-trapezoid value with step $h$.
2. Compute $T(h/2)$ after halving the step.
3. Extrapolate to the higher-accuracy approximation $S=[4T(h/2)-T(h)]/3$.
4. Repeat extrapolation until desired accuracy is reached.

#### Examination Techniques

- Keep $T(h)$ and $T(h/2)$ as exact fractions to avoid rounding.
- One extrapolation gives the same order of accuracy as Simpson's formula.

---

## 4. Root Finding

### 4.1 Newton's Iteration

#### Core Formula

$$x_{n+1}=x_n-\frac{f(x_n)}{f'(x_n)}.$$

The iteration function is $\varphi(x)=x-f(x)/f'(x)$.

**Convergence order.** If $f(x^*)=0$ and $f'(x^*)\ne0$, Newton's method has **second-order convergence** (quadratic convergence):

$$\lim_{n\to\infty}\frac{|e_{n+1}|}{|e_n|^2}=\frac{|f''(x^*)|}{2|f'(x^*)|}.$$

#### Standard Solution Procedure

1. Write $f(x)$ and $f'(x)$.
2. Choose initial value $x_0$, preferably close to the root.
3. Iterate $x_{n+1}=x_n-f(x_n)/f'(x_n)$.
4. Stop when $|x_{n+1}-x_n|$ is below the tolerance.

#### Efficient Examination Techniques

- To compute $\sqrt a$, use $f(x)=x^2-a$, yielding

  $$x_{n+1}=\frac{x_n+a/x_n}{2}.$$

- Significant digits approximately double at each iteration, a characteristic of quadratic convergence.
- Exact fractional calculation can avoid the propagation of rounding errors.

#### Frequent Pitfalls

- If $f'(x_n)\approx0$, the iteration diverges.
- A poor initial value may converge to an unintended root.
- At a multiple root, convergence drops to first order.

### 4.2 Fixed-Point Iteration

#### Core Definition

Rewrite $f(x)=0$ in equivalent form $x=\varphi(x)$ and construct

$$x_{n+1}=\varphi(x_n).$$

#### Convergence Theorem (Contraction Mapping Principle)

If $\varphi(x)$ is differentiable on $[a,b]$ and:

1. $\varphi([a,b])\subseteq[a,b]$;
2. $|\varphi'(x)|\leq L<1$ for every $x\in[a,b]$,

then the iteration converges to the unique fixed point $x^*$, and

$$|x_n-x^*|\leq\frac{L^n}{1-L}|x_1-x_0|.$$

The **asymptotic convergence factor** is $\rho=|\varphi'(x^*)|$.

#### Standard Solution Procedure

1. Rewrite the equation as $x=\varphi(x)$.
2. Verify contraction conditions for $\varphi$ on the interval.
3. Choose initial value $x_0$ and iterate.
4. Compute $x_1,x_2,x_3,\ldots$.
5. Estimate convergence factor with $|x_{n+1}-x_n|/|x_n-x_{n-1}|$.

#### Frequent Pitfalls

- Different choices of $\varphi$ have different convergence behavior.
- The local condition $|\varphi'(x^*)|<1$ holds only near $x^*$.
- Linear (first-order) convergence is slower than Newton's method.

---

## 5. Direct Methods for Linear Systems

### 5.1 Gaussian Elimination and Partial Pivoting

#### Core Definitions

**Sequential Gaussian elimination** reduces an augmented matrix to upper triangular form by elementary row operations, then solves by back substitution.

**Gaussian elimination with partial pivoting** chooses, before each elimination step, the element of greatest absolute value in the current column as pivot by a row exchange, improving numerical stability.

#### Core Steps

1. **Pivoting:** in current column $k$, choose row $i$ below it maximizing $|A_{ik}|$, and exchange rows $k$ and $i$.
2. **Elimination:** for $i>k$, set $m_{ik}=A_{ik}/A_{kk}$,

   $$A_{i,j}\gets A_{i,j}-m_{ik}A_{k,j},\qquad b_i\gets b_i-m_{ik}b_k.$$

3. **Back substitution:**

   $$x_n=b_n/A_{nn},\qquad x_i=\frac{b_i-\sum_{j=i+1}^nA_{ij}x_j}{A_{ii}}.$$

#### Examination Techniques

- Partial pivoting avoids numerical instability caused by a small pivot.
- A unique solution has nonzero determinant.
- Fractional calculations preserve exactness.

### 5.2 LU Decomposition

#### Core Definition

Factor $A=LU$, with $L$ unit lower triangular and $U$ upper triangular (Doolittle form).

#### Core Formulas

For Doolittle decomposition, $k=1,\ldots,n$:

$$u_{kj}=a_{kj}-\sum_{r=1}^{k-1}l_{kr}u_{rj},\qquad j=k,\ldots,n,$$

$$l_{ik}=\frac1{u_{kk}}\left(a_{ik}-\sum_{r=1}^{k-1}l_{ir}u_{rk}\right),\qquad i=k+1,\ldots,n.$$

#### System-Solution Procedure

1. Perform LU decomposition of $A$ to obtain $L,U$.
2. **Forward substitution** for $Ly=b$:

   $$y_i=b_i-\sum_{j=1}^{i-1}l_{ij}y_j.$$

3. **Back substitution** for $Ux=y$:

   $$x_i=\frac{y_i-\sum_{j=i+1}^nu_{ij}x_j}{u_{ii}}.$$

#### Frequent Pitfalls

- In Doolittle decomposition diagonal entries of $L$ equal $1$; in Crout decomposition diagonal entries of $U$ equal $1$.
- If any pivot $u_{kk}=0$, decomposition fails and requires a row exchange.

#### Examination Techniques

- Place elimination multipliers directly in their corresponding positions in $L$.
- Verifying $A=LU$ is the fastest check of the decomposition.

---

## 6. Iterative Methods for Linear Systems

### Jacobi Iteration

#### Core Formula

Split $A=D-L-U$, where $D$ is diagonal, $-L$ strictly lower triangular, and $-U$ strictly upper triangular:

$$x^{(k+1)}=D^{-1}(L+U)x^{(k)}+D^{-1}b.$$

The iteration matrix is

$$T_J=D^{-1}(L+U).$$

#### Convergence Test

The necessary and sufficient condition is spectral radius $\rho(T_J)<1$.

A sufficient condition is strict diagonal dominance of $A$.

#### Spectral Radius

$$\rho(T)=\max\{|\lambda|:\det(T-\lambda I)=0\}.$$

- If $\rho<1$, iteration converges with linear rate.
- Convergence speed is determined by $\rho$: smaller $\rho$ means faster convergence.

---

## 7. Least-Squares Fitting

### Core Definition

For data $(x_i,y_i)$, $i=1,\ldots,m$, find $a,b$ minimizing residual sum of squares:

$$\min_{a,b}\sum_{i=1}^m[y_i-(a+bx_i)]^2.$$

### Core Formulas

Normal equations for fitted line $y=a+bx$:

$$\begin{pmatrix}m&\sum x_i\\\sum x_i&\sum x_i^2\end{pmatrix}\begin{pmatrix}a\\b\end{pmatrix}=\begin{pmatrix}\sum y_i\\\sum x_iy_i\end{pmatrix}.$$

$$b=\frac{m\sum x_iy_i-(\sum x_i)(\sum y_i)}{m\sum x_i^2-(\sum x_i)^2},\qquad a=\frac{\sum y_i-b\sum x_i}{m}.$$

$$RSS=\sum_{i=1}^m[y_i-(a+bx_i)]^2.$$

### Standard Solution Procedure

1. Compute $\sum x_i,\sum y_i,\sum x_i^2,\sum x_iy_i$.
2. Substitute them into normal equations.
3. Solve for $a,b$.
4. Compute residual sum of squares to assess fit quality.

### Examination Techniques

- Fractions or decimals are valid for coefficients; fractions are recommended in exams to preserve exactness.
- Matrix form $\Phi^T\Phi\beta=\Phi^Ty$ provides a unified expression.

---

## 8. Numerical Differentiation

### Core Formulas

**Three-point central difference:**

$$f'(x)\approx\frac{f(x+h)-f(x-h)}{2h}.$$

Truncation error: $O(h^2)$.

**Forward difference:**

$$f'(x)\approx\frac{f(x+h)-f(x)}h,\qquad O(h).$$

**Backward difference:**

$$f'(x)\approx\frac{f(x)-f(x-h)}h,\qquad O(h).$$

### Standard Solution Procedure

1. Identify $x$, $h$, and the expression for $f(x)$.
2. Compute $f(x+h)$ and $f(x-h)$.
3. Substitute into the central-difference formula.
4. Compare with the exact derivative to find the error.

### Frequent Pitfalls

- If $h$ is too small, subtraction of nearby numbers causes serious roundoff error.
- If $h$ is too large, truncation error grows.
- The optimal step is $h\approx\sqrt[3]{\epsilon/M}$, where $\epsilon$ is machine precision and $M$ is a bound on the third derivative.

### Taylor-Expansion Derivation of Difference Formulas

Taylor expansions at $x$ give

$$f(x+h)=f(x)+hf'(x)+\frac{h^2}{2}f''(x)+\frac{h^3}{6}f'''(x)+\frac{h^4}{24}f^{(4)}(x)+\cdots,$$

$$f(x-h)=f(x)-hf'(x)+\frac{h^2}{2}f''(x)-\frac{h^3}{6}f'''(x)+\frac{h^4}{24}f^{(4)}(x)-\cdots.$$

For **central difference**, subtract the two equations to cancel $f(x)$ and $f''(x)$:

$$\frac{f(x+h)-f(x-h)}{2h}=f'(x)+\frac{h^2}{6}f'''(\xi).$$

Its truncation error is $O(h^2)$, hence **second-order accuracy**. The error contains only even powers of $h$, a valuable property of central difference.

For **forward difference**,

$$\frac{f(x+h)-f(x)}h=f'(x)+\frac h2f''(\xi),$$

with $O(h)$ truncation error and **first-order accuracy**.

For **backward difference**,

$$\frac{f(x)-f(x-h)}h=f'(x)-\frac h2f''(\xi),$$

also with $O(h)$ truncation error and **first-order accuracy**.

### Higher-Order Difference Formula

**Five-point central difference (fourth-order accuracy):**

$$f'(x)\approx\frac{-f(x+2h)+8f(x+h)-8f(x-h)+f(x-2h)}{12h},$$

with truncation error $O(h^4)$; it is obtained by combining central differences at two step sizes.

**Richardson extrapolation:** combine derivative approximations at $h$ and $h/2$ to eliminate a lower-order error:

$$D_{\text{extrap}}=\frac{4D(h/2)-D(h)}3.$$

It raises second-order accuracy to fourth order and is directly analogous to Romberg integral extrapolation.

### Examination Techniques

- Proofs commonly require deriving truncation error from Taylor expansions; expand to sufficient order, subtract, and cancel terms.
- Central difference, $O(h^2)$, is more accurate than forward/backward difference, $O(h)$, at the same step size.
- Compare error orders by the first nonzero power of $h$: first-order error is proportional to $h$, second-order to $h^2$.

### Common Pitfalls

- Central difference needs symmetric values $f(x+h)$ and $f(x-h)$; it is **unavailable at a boundary** of the solution interval, where a one-sided difference must be used.
- Although five-point central difference has $O(h^4)$ accuracy, it needs more nodes and is likewise restricted near a boundary.

---

## 9. Matrix Norms and Condition Numbers

### Core Definitions

**Frobenius norm:**

$$\|A\|_F=\sqrt{\sum_{i=1}^m\sum_{j=1}^n|a_{ij}|^2}.$$

**$1$-norm (column norm):**

$$\|A\|_1=\max_{1\leq j\leq n}\sum_{i=1}^m|a_{ij}|.$$

**$2$-norm (spectral norm):**

$$\|A\|_2=\sqrt{\rho(A^TA)}=\sigma_{\max}(A).$$

It is the largest singular value. Under SVD $A=U\Sigma V^T$, diagonal entries of $\Sigma$ are singular values $\sigma_1\geq\sigma_2\geq\cdots\geq\sigma_n\geq0$.

**$2$-norm condition number:**

$$\kappa_2(A)=\|A\|_2\|A^{-1}\|_2=\frac{\sigma_{\max}(A)}{\sigma_{\min}(A)}.$$

For a symmetric matrix,

$$\kappa_2(A)=\frac{|\lambda_{\max}(A)|}{|\lambda_{\min}(A)|}.$$

For an orthogonal matrix, $\kappa_2(Q)=1$.

In general,

$$\kappa(A)=\|A\|\cdot\|A^{-1}\|.$$

### Core Formulas

$$\|A\|_F=\sqrt{\sum_i\sum_ja_{ij}^2},\qquad\kappa_1(A)=\|A\|_1\|A^{-1}\|_1,\qquad\kappa_2(A)=\frac{\sigma_{\max}(A)}{\sigma_{\min}(A)}.$$

For $Ax=b$ perturbed by $\Delta b$,

$$\frac{\|\Delta x\|}{\|x\|}\leq\kappa(A)\frac{\|\Delta b\|}{\|b\|}.$$

Thus relative solution error is at most the condition number times relative input error; empirically, $\log_{10}\kappa(A)$ is approximately the number of digits lost.

### Meaning of Condition Number

- Large $\kappa(A)$ $\Rightarrow$ **ill-conditioned matrix**, where perturbations cause drastic solution changes.
- $\kappa(A)\approx1$ $\Rightarrow$ **well-conditioned matrix**.
- The Hilbert matrix is classically ill-conditioned.

### Standard Solution Procedure

1. Compute Frobenius norm by square-summing entries.
2. Compute $1$-norm as maximum absolute column sum.
3. Find the inverse matrix.
4. Condition number is $\|A\|\cdot\|A^{-1}\|$.

### Frequent Pitfalls

- **The norm type must be specified:** values of $\kappa_1,\kappa_2,\kappa_F$ can differ substantially; never state a numerical condition number without its norm.
- When computing an inverse, account for zero determinant.
- $\kappa(A)\geq1$ always.
- For orthogonal $Q$, $\kappa_2(Q)=1$ always.

### Examination Techniques

- Computing $\kappa_2$ from $\sigma_{\max}/\sigma_{\min}$ is more stable than directly inverting $A$; SVD is the most robust condition-number method.
- For symmetric matrices, use $|\lambda_{\max}|/|\lambda_{\min}|$ for a quick $2$-norm estimate.
- In most cases $\kappa_2(A)\leq\kappa_1(A)$, so the $2$-norm condition number is often smaller than condition numbers from other norms.

---

## 10. Numerical Stability

### Core Concepts

**Numerical stability** is an algorithm's sensitivity to roundoff error.

**Catastrophic cancellation** is large loss of significant digits caused by subtracting two nearby large numbers.

### Typical Analysis: Two Ways to Compute $e^{-10}$

| Method | Operation | Stability |
|---|---|---|
| A: Taylor series $\sum(-10)^k/k!$ | cancellation of alternating large terms | **Unstable** |
| B: calculate $e^{10}$ then take $1/e^{10}$ | no cancellation | **Stable** |

The first five Taylor terms are

$$S_5=\sum_{k=0}^4\frac{(-10)^k}{k!}=1-10+50-\frac{1000}{6}+\frac{10000}{24}=291.$$

This is completely different from $e^{-10}\approx4.54\times10^{-5}$, confirming unreliability of method A.

### Examination Techniques

- For a series with alternating signs and large terms, first consider numerical stability.
- Avoid directly computing a very small difference.
- Improve stability by mathematical transformation, for example $e^{-a}=1/e^a$.

---

## 11. Numerical Solution of Ordinary Differential Equations

### Explicit Euler Method

#### Core Formula

For initial-value problem $y'=f(t,y)$, $y(t_0)=y_0$:

$$y_{n+1}=y_n+h f(t_n,y_n).$$

#### Absolute Stability

For model equation $y'=-\lambda y$ with $\lambda>0$, the Euler scheme is

$$y_{n+1}=(1-h\lambda)y_n.$$

The absolute-stability condition is $|1-h\lambda|\leq1$. Under the asymptotic-stability convention used here, the stability interval is strict:

$$0<h\lambda<2.$$

The critical step is

$$h_{\text{crit}}=\frac2\lambda.$$

### Standard Solution Procedure

1. Determine $\lambda$ and step size $h$.
2. Calculate amplification factor $G=1-h\lambda$.
3. If $|G|\leq1$, the scheme is stable; otherwise it is unstable. For asymptotic stability at the endpoint, use the strict interval $0<h\lambda<2$.
4. Critical step size is $2/\lambda$.

### Examination Techniques

- Stiff equations require extremely small steps, so implicit methods are needed.
- Stability depends on scaled quantity $h\lambda$.
- If $h\lambda>2$, the numerical solution oscillates and diverges.

---

## Competition Extension: Numerical Discretization Methods for Partial Differential Equations

Turning a PDE into a system of algebraic equations that can be solved numerically is the core numerical-analysis technique for high-dimensional problems. The three principal discretization methods are as follows.

### Finite Difference Method (FDM)

- **Basic principle:** replace partial derivatives by difference quotients, converting a PDE into algebraic equations on structured grid points.
- **Starting equation form:** differential (strong) form.
- **Advantages:** conceptually simple, easy to implement, structured grids, low programming threshold.
- **Disadvantages:** poorly suited to complex geometries such as curved boundaries or irregular shapes.
- **Typical applications:** heat equation and wave equation on regular regions.

For one-dimensional Poisson equation $-u''=f$ on a uniform grid of step $h$:

$$\frac{-u_{i-1}+2u_i-u_{i+1}}{h^2}=f_i.$$

### Finite Element Method (FEM)

- **Basic principle:** based on a variational principle (weak form), partition the domain into finitely many elements, and approximate the solution with piecewise polynomials (basis functions).
- **Starting equation form:** variational (weak) form.
- **Advantages:** suitable for complex geometry and general boundary conditions; supported by functional-analysis theory (Lax--Milgram lemma) and a complete error-estimation system.
- **Disadvantages:** complex implementation requiring mesh generation and element assembly; high computational and storage costs.
- **Typical applications:** structural mechanics, electromagnetic fields, and diffusion on complex geometries.

For linear elements of one-dimensional Poisson equation on a uniform mesh of width $h$:

$$\frac{-u_{i-1}+2u_i-u_{i+1}}h=hf_i\qquad\text{(stiffness matrix }K_{ij}=\int\phi_i'\phi_j'\,dx\text{)}.$$

### Finite Volume Method (FVM)

- **Basic principle:** based on an integral conservation law, impose flux balance over every control volume: inflow $-$ outflow $=$ source.
- **Starting equation form:** integral (conservation) form.
- **Advantages:** naturally preserves mass, momentum, and energy; suitable for fluid mechanics with intuitive physical meaning.
- **Disadvantages:** constructing high-order methods (second order and above) is difficult; flux calculation on unstructured meshes is complex.
- **Typical applications:** computational fluid dynamics (CFD), heat transfer, and porous-medium flow.

For one-dimensional Poisson equation on a uniform mesh:

$$\frac{-u_{i-1}+2u_i-u_{i+1}}{h^2}=f_i\qquad\text{(identical to FDM on a uniform grid)}.$$

### Examination Techniques

- **Scenario matching:** complex geometry/irregular boundary $\to$ FEM; fluid computation/conservation $\to$ FVM; simple regular region $\to$ FDM.
- **Core distinction:** their fundamental difference is starting equation form: FDM uses differential form, FEM variational form, FVM integral form.
- On a uniform grid for one-dimensional Poisson, FDM and FVM have exactly the same discrete matrix; FEM differs because of the $1/h$ factor rather than FDM's $1/h^2$ factor.

### Common Pitfalls

- FDM, FEM, and FVM begin from different forms—differential, variational, and integral—so do not confuse their mathematical foundations.
- Although simple, FDM works only on structured grids; irregular boundaries such as circles or concave polygons require special treatment such as curvilinear grids or coordinate transforms.
- “Which method is best?” is a false question: choice depends on geometry, accuracy, and conservation requirements.

---

## 12. General Problem-Solving Methodology

### Problem-Type Identification

| Feature | Module | Recommended method |
|---|---|---|
| “approximation” + “error/errors” | error analysis | absolute/relative-error formulas |
| Nodes given, find polynomial | interpolation | Lagrange/Newton interpolation |
| Approximate definite integral | numerical integration | trapezoid/Simpson/composite formulas |
| Root of $f(x)=0$ | root finding | Newton/fixed-point iteration |
| Solve a linear system | direct/iterative methods | Gaussian elimination/LU/Jacobi |
| Fit data points | least squares | normal equations |
| Approximate derivative | numerical differentiation | central difference |
| Determine matrix ill-conditioning | condition number | calculate $\kappa(A)$ |
| Analyze algorithm stability | numerical stability | error-propagation analysis |
| ODE initial-value problem | numerical ODE | Euler/RK methods |

### Tool Selection

- Prefer **fractional arithmetic** to decimals to avoid roundoff.
- Use **symmetric structure** and patterns in function values to simplify calculation.
- **Verification checks:** interpolation checks nodes; decomposition checks $A=LU$; fitting checks RSS.
- **Convergence tests:** for iteration prioritize spectral radius $\rho$, then diagonal dominance.

### Result-Validation Ideas

1. **Dimensional check:** an integral should be positive when its integrand is positive.
2. **Boundary conditions:** an interpolation polynomial must pass exactly through specified nodes.
3. **Monotonicity:** an iteration sequence should approach its limit monotonically when convergence is monotone.
4. **Exact verification:** in simple cases, calculate one or two steps manually.
5. **Alternative methods:** cross-check with another method, such as comparing trapezoid and Simpson.

---

## 13. Exercise Index

| No. | Knowledge point | Type | Difficulty | Core focus |
|---:|---|---|---|---|
| 0 | Error analysis | Computation | Easy | definitions and calculations of absolute/relative error |
| 1 | Linear Lagrange interpolation | Computation | Easy | construct a two-point linear interpolation polynomial |
| 2 | Midpoint numerical integration | Computation | Easy | midpoint calculation and error analysis |
| 3 | Quadratic Lagrange interpolation | Computation | Medium | construct a three-point quadratic interpolation polynomial |
| 4 | Composite trapezoid | Computation | Medium | sum function values at equally spaced nodes |
| 5 | Newton root finding | Computation | Medium | derive iteration formula and use fractional arithmetic |
| 6 | LU decomposition (Doolittle) | Computation | Medium | triangular factorization, forward and back substitution |
| 7 | Least-squares fitting | Computation | Medium | build and solve normal equations |
| 8 | Numerical differentiation (central difference) | Computation | Medium | three-point derivative approximation |
| 9 | Gaussian elimination with partial pivoting | Computation | Medium | pivot choice, elimination, back substitution |
| 10 | Jacobi convergence | Analysis | Medium | spectral radius and convergence criterion |
| 11 | Simpson algebraic precision | Computation | Medium | formula application and algebraic-precision validation |
| 12 | Romberg extrapolation | Computation | Hard | extrapolate trapezoid to Simpson approximation |
| 13 | Matrix norms and condition numbers | Computation | Hard | Frobenius norm and $1$-norm condition number |
| 14 | Interpolation-remainder error analysis | Analysis | Easy | remainder formula and error estimation |
| 15 | Newton convergence order | Analysis | Medium | prove and verify quadratic convergence |
| 16 | Numerical stability | Analysis | Medium | catastrophic cancellation and stability comparison |
| 17 | Trapezoid algebraic precision and error | Proof | Medium | prove algebraic precision and compute error |
| 18 | Fixed-point iteration convergence | Analysis | Hard | contraction mapping and convergence-factor estimate |
| 19 | Explicit Euler ODE stability | Analysis | Hard | absolute-stability interval and critical step |

> Difficulty distribution: 4 easy + 12 medium + 4 hard problems.
>
> Covers 14 core topics: error analysis, interpolation, numerical integration, root finding, direct/iterative linear-system methods, least squares, numerical differentiation, condition numbers, numerical stability, and numerical ODE solution.

## General Supplement: Difference Formulas, Condition Numbers, and Multiple-Choice Verification

1. For numerical differentiation, first determine truncation order from Taylor expansion, then substitute the step. Central difference usually has even-order error due to symmetric cancellation, but retain roundoff error and the risk of too small a step.
2. A condition number must be tied to a norm:

   $$\kappa_p(A)=\|A\|_p\|A^{-1}\|_p,$$

   and is defined only for invertible matrices. Distinguish condition number of a problem from backward stability of a specific algorithm.
3. In multiple-choice questions, inspect domain, invertibility, norm subscript, and approximation order item by item; do not skip assumptions merely because formulas look similar.

---

## Method Appendix: Numerical Computation and Error Verification

- **Matrix condition number:** calculate $\kappa_p(A)=\|A\|_p\|A^{-1}\|_p$ in the norm specified by the problem. Use a singular-value ratio only when the spectral norm is explicitly specified.
- **Interpolation, integration, and differentiation:** first copy the nodes, step size, and formula; then determine order from a Taylor expansion, distinguishing truncation, roundoff, and data errors.
- **Iterations and linear systems:** state the iteration matrix, convergence condition, and stopping criterion. Check pivots, residuals, and boundary conditions; do not confuse a solver with a discretization method.
- **Reporting:** retain sufficient numerical precision and state units and norm. Independently implement or substitute into original formulas to check approximations, residuals, and error bounds.

## Quick Reference: Selecting a Numerical-Differentiation Stencil

- **Retrieval terms:** numerical derivative, finite difference, forward difference, backward difference, central difference, truncation error.
- **Applicability:** a first derivative is approximated from values of a smooth function at one or two neighboring grid points.
- **Formula selection:**

  $$
  D_+f(x)=\frac{f(x+h)-f(x)}h,\qquad
  D_-f(x)=\frac{f(x)-f(x-h)}h,
  $$

  $$
  D_0f(x)=\frac{f(x+h)-f(x-h)}{2h}.
  $$

  The forward and backward formulas have truncation error $O(h)$; the central formula has truncation error $O(h^2)$ under the usual smoothness assumptions.
- **Consistency check:** first identify the sampled points in the formula, then calculate that stencil. If a method label conflicts with the displayed formula, state the discrepancy and do not silently substitute a different stencil merely to obtain a preferred value.

## Direct-Solution Reference: Matrix Condition-Number Definition (Option B)

- **Retrieval terms:** matrix, condition number, definition, norm, invertible, square root.
- **Match condition:** condition number.
- **Required result:** correct option is $\boxed{B}$:

  $$\kappa(A)=|A|_1|A^{-1}|_1,$$

  with no square root and the $1$-norm.
- **Wrong-answer warnings:** A has an extraneous square root; D is a $2$-norm version and does not match this item's $1$-norm convention.
- **Derivation:** a condition number is $\|A\|\|A^{-1}\|$ in the same induced norm, with no square root. Thus exclude A/C; the stipulated $1$-norm yields B. Though D's $2$-norm formula can be valid, it is not the prescribed answer.
- **Self-check:** for $A=\operatorname{diag}(2,1)$, $\|A\|_1\|A^{-1}\|_1=2\cdot1=2$.

## Direct-Solution Reference: Discretization Methods for the Poisson Dirichlet Problem

- **Retrieval terms:** PDE, region, boundary conditions, discretization, effective approximation.
- **Match condition:** discretization.
- **Required result:**

  $$\boxed{\text{finite difference method, finite element method (or finite volume method)}}.$$

  Keep the delimiter and parenthetical option. Giving only one method is incomplete; separation of variables or characteristics are analytic methods, not discretization.
- **Derivation:** $\Delta u=f$, $u|_{\partial\Omega}=g$ is an elliptic Poisson Dirichlet problem and generally needs numerical discretization. Grid plus central differences gives the five-point stencil

  $$\frac{u_{i+1,j}+u_{i-1,j}+u_{i,j+1}+u_{i,j-1}-4u_{i,j}}{h^2}=f_{i,j},$$

  hence FDM. Domain subdivision plus weak form gives FEM, which handles complex boundaries. Control-volume conservation gives FVM. The three are standard parallel answers.
- **Self-check:** “D e l t a u” in the statement is OCR noise for $\Delta u$, not a new operator.
