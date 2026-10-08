---
name: probability-theory-verification
description: Use when verifying probability-theory problems with sympy — classical probability, distributions, expectations, moment generating functions, characteristic functions, convergence theorems, and limit theorems.
---

# Probability Problem-Solving and Verification Skill

## Domain Boundaries and Routing Conventions

- Scope: static random variables, distribution functions, expectation and variance, conditional probability, limit theorems, and transforms.
- Do not take over: Markov, Poisson, Brownian, and other time-evolving questions belong to stochastic processes; sample estimation, testing, and time series belong to statistical inference.
- Verification contract: state the event domain, independence, distribution parameters, and tail direction explicitly. Check normalization of probability mass/density separately.

## Overview

This skill manual covers the core undergraduate probability-theory curriculum: classical probability models and combinatorial counting; random variables and distributions (discrete and continuous); multivariate random variables and their numerical characteristics; moment generating functions and characteristic functions; limit theorems (the law of large numbers and the central limit theorem); and common inequalities. The manual uses 20 selected exercises as its framework to systematically organize the core concepts, commonly used formulas, solution steps, and common pitfalls of each knowledge module. It also provides verification notes, and is suitable for studying, reviewing, and automatically verifying solutions to probability-theory problems.

---

## Knowledge Framework

### Module 1: Classical Probability Models and Combinatorial Counting

#### Core Concepts

- **Classical probability model**: the sample space is finite and equiprobable, and the probability of an event is \(P(A)=\frac{|A|}{|\Omega|}\).
- **Permutations**: \(P_n^k=\frac{n!}{(n-k)!}\) (ordered sampling without replacement).
- **Combinations**: \(C_n^k=\binom nk=\frac{n!}{k!(n-k)!}\) (unordered sampling without replacement).
- **Hypergeometric distribution**: when drawing \(n\) items without replacement from a population of \(N\) items containing \(K\) “successes,” the probability of exactly \(k\) successes is \(P=\frac{C_K^k\cdot C_{N-K}^{n-k}}{C_N^n}\).
- **Sampling with replacement**: binomial distribution; **sampling without replacement**: hypergeometric distribution.

#### Commonly Used Formulas

1. Addition principle and multiplication principle.
2. Combinatorial identities: \(\binom nk=\binom n{n-k}\), \(\binom nk=\binom{n-1}k+\binom{n-1}{k-1}\).
3. Hypergeometric probability mass function:
   \[
   P(X=k)=\frac{\binom Kk\binom{N-K}{n-k}}{\binom Nn}.
   \]

#### Solution Steps

1. Specify the sample space: determine the total number of equiprobable outcomes.
2. Identify the favorable event: count the outcomes satisfying the condition.
3. Substitute into the classical-probability formula: \(P=\frac{\text{number of favorable outcomes}}{\text{total number of outcomes}}\).
4. For sampling without replacement, preferentially use the hypergeometric distribution directly.

#### Common Pitfalls

- Do not confuse sampling with and without replacement: use a binomial distribution with replacement and a hypergeometric distribution without replacement.
- Avoid errors in combination counts: the denominator of \(\binom nk\) is \(k!(n-k)!\), not merely \(k!\) or \((n-k)!\).
- Note the difference between “exactly” and “at least.”

#### Corresponding Exercise

- **idx 0**: drawing red and white balls from a bag without replacement; compute directly with the hypergeometric distribution.

---

### Module 2: Random Variables and Distributions

#### 2.1 Discrete Distributions

##### Binomial Distribution \(B(n,p)\)

- **Probability mass function (pmf)**: \(P(X=k)=\binom nk p^k(1-p)^{n-k},\quad k=0,1,\ldots,n\).
- **Expectation**: \(E[X]=np\).
- **Variance**: \(\mathrm{Var}(X)=np(1-p)\).
- **Moment generating function**: \(M(t)=(pe^t+1-p)^n\).
- **Characteristic function**: \(\varphi(t)=(pe^{it}+1-p)^n\).

##### Poisson Distribution \(\mathrm{Poisson}(\lambda)\)

- **Probability mass function (pmf)**: \(P(X=k)=e^{-\lambda}\frac{\lambda^k}{k!},\quad k=0,1,2,\ldots\).
- **Expectation and variance**: \(E[X]=\lambda,\quad\mathrm{Var}(X)=\lambda\).
- **Moment generating function**: \(M(t)=\exp(\lambda(e^t-1))\).
- **Characteristic function**: \(\varphi(t)=\exp(\lambda(e^{it}-1))\).
- **Additivity**: if \(X\sim\mathrm{Poisson}(\lambda_1)\) and \(Y\sim\mathrm{Poisson}(\lambda_2)\) are independent, then \(X+Y\sim\mathrm{Poisson}(\lambda_1+\lambda_2)\).

#### 2.2 Continuous Distributions

##### Uniform Distribution \(U(a,b)\)

- **Density function**: \(f(x)=\frac1{b-a},\quad x\in[a,b]\).
- **Expectation**: \(E[X]=\frac{a+b}{2}\).
- **Variance**: \(\mathrm{Var}(X)=\frac{(b-a)^2}{12}\).
- **Characteristic function**: \(\varphi(t)=\frac{e^{itb}-e^{ita}}{it(b-a)}\).

##### Exponential Distribution \(\mathrm{Exp}(\lambda)\)

- **Density function**: \(f(x)=\lambda e^{-\lambda x},\quad x>0\) (parameter \(\lambda>0\)).
- **Survival function**: \(P(X>x)=e^{-\lambda x},\quad x>0\).
- **Expectation and variance**: \(E[X]=\frac1\lambda,\quad\mathrm{Var}(X)=\frac1{\lambda^2}\).
- **\(n\)-th moment**: \(E[X^n]=\frac{n!}{\lambda^n}\) (using the Gamma integral: \(\int_0^\infty x^n e^{-\lambda x}\,dx=\frac{\Gamma(n+1)}{\lambda^{n+1}}=\frac{n!}{\lambda^{n+1}}\)).
- **Memorylessness**: \(P(X>s+t\mid X>s)=P(X>t),\quad\forall s,t>0\).
- **Moment generating function**: \(M(t)=\frac\lambda{\lambda-t},\quad t<\lambda\).

##### Normal Distribution \(N(\mu,\sigma^2)\)

- **Density function**: \(f(x)=\frac1{\sqrt{2\pi}\sigma}\exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)\).
- **Characteristic function**: \(\varphi(t)=\exp\left(i\mu t-\frac12\sigma^2t^2\right)\).

##### Laplace Distribution \(\mathrm{Laplace}(\mu,b)\)

- **Density function**: \(f(x)=\frac1{2b}e^{-\lvert x-\mu\rvert/b}\).
- **Characteristic function**: \(\varphi(t)=\frac{e^{i\mu t}}{1+b^2t^2}\).
- When \(\mu=0,b=1\), \(\varphi(t)=\frac1{1+t^2}\).

#### 2.3 Distribution Functions and Density Functions

- **Distribution function**: \(F(x)=P(X\le x)\), right-continuous and nondecreasing, with \(\lim_{x\to-\infty}F(x)=0\) and \(\lim_{x\to+\infty}F(x)=1\).
- **Density function**: for a continuous random variable, \(f(x)=F'(x)\) (almost everywhere).
- **Distribution of a function of a random variable**: if \(Y=g(X)\), then:
  - **Distribution-function method**: \(F_Y(y)=P(g(X)\le y)\), then differentiate to obtain \(f_Y(y)\).
  - **Formula method (when \(g\) is strictly monotone)**: \(f_Y(y)=f_X(g^{-1}(y))\cdot\left|\frac{d}{dy}g^{-1}(y)\right|\).

#### Common Pitfalls

- Exponential-distribution parameterizations differ: some texts use \(f(x)=\lambda e^{-\lambda x}\) (expectation \(1/\lambda\)), while others use \(f(x)=\frac1\theta e^{-x/\theta}\) (expectation \(\theta\)). Confirm the parameterization before solving.
- For a Poisson distribution, \(P(X\ge1)=1-P(X=0)\); do not forget the complement.
- A continuous random variable has zero point mass: \(P(X=c)=0\).
- For \(X\sim U(0,1)\), the transformation \(Y=-\ln X\sim\mathrm{Exp}(1)\) is a classical one.

#### Corresponding Exercises

- **idx 2**: compute directly from the binomial pmf.
- **idx 9**: compute \(P(X=2)\) and \(P(X\ge1)\) for a Poisson distribution.
- **idx 6**: distribution of a function of a random variable—\(X\sim U(0,1)\), \(Y=-\ln X\); derive \(Y\sim\mathrm{Exp}(1)\) using the distribution-function method.
- **idx 10**: higher moments of an exponential distribution—use the Gamma integral \(E[X^n]=n!/\lambda^n\).

---

### Module 3: Multivariate Random Variables

#### 3.1 Joint and Marginal Distributions

- **Joint distribution function**: \(F(x,y)=P(X\le x,Y\le y)\).
- **Joint density** (continuous case): \(f(x,y)\), satisfying \(P((X,Y)\in D)=\iint_Df(x,y)\,dx\,dy\).
- **Marginal densities**:
  \[
  f_X(x)=\int_{-\infty}^{\infty}f(x,y)\,dy,\quad f_Y(y)=\int_{-\infty}^{\infty}f(x,y)\,dx.
  \]
- **Independence**: \(f(x,y)=f_X(x)\cdot f_Y(y)\) (or \(F(x,y)=F_X(x)F_Y(y)\)).

#### 3.2 Conditional Distributions and Conditional Expectations

- **Conditional density** (continuous case): \(f_{X\mid Y}(x\mid y)=\frac{f(x,y)}{f_Y(y)}\) (when \(f_Y(y)>0\)).
- **Conditional distribution law** (discrete case): \(P(X=x_i\mid Y=y_j)=\frac{P(X=x_i,Y=y_j)}{P(Y=y_j)}\).
- **Conditional expectation** (continuous case):
  \[
  E[X\mid Y=y]=\int_{-\infty}^{\infty}x\cdot f_{X\mid Y}(x\mid y)\,dx,
  \]
  \[
  E[g(X)\mid Y=y]=\int_{-\infty}^{\infty}g(x)\cdot f_{X\mid Y}(x\mid y)\,dx.
  \]
- **Conditional variance**: \(\mathrm{Var}(X\mid Y=y)=E[X^2\mid Y=y]-(E[X\mid Y=y])^2\).
- **Law of total expectation**: \(E[X]=E[E[X\mid Y]]\).
- **Law of total variance**: \(\mathrm{Var}(X)=E[\mathrm{Var}(X\mid Y)]+\mathrm{Var}(E[X\mid Y])\).

#### 3.3 Covariance and Correlation Coefficient

- **Covariance**: \(\mathrm{Cov}(X,Y)=E[(X-E[X])(Y-E[Y])]=E[XY]-E[X]E[Y]\).
- **Correlation coefficient**:
  \[
  \rho(X,Y)=\frac{\mathrm{Cov}(X,Y)}{\sqrt{\mathrm{Var}(X)\cdot\mathrm{Var}(Y)}},\quad |\rho|\le1.
  \]
- **Properties**:
  - \(\rho=0\) means uncorrelated, but does not necessarily mean independent (the normal-distribution case is an exception).
  - \(\rho=\pm1\) if and only if \(Y=aX+b\) holds almost everywhere (\(a\ne0\)).
  - Independence \(\Rightarrow\) uncorrelatedness (\(\mathrm{Cov}=0\)); the converse fails.
- **Bilinearity of covariance**: \(\mathrm{Cov}(aX+bY,Z)=a\,\mathrm{Cov}(X,Z)+b\,\mathrm{Cov}(Y,Z)\).
- **Variance of a sum**: \(\mathrm{Var}(X+Y)=\mathrm{Var}(X)+\mathrm{Var}(Y)+2\,\mathrm{Cov}(X,Y)\).

#### 3.4 Bivariate Normal Distribution

If \((X,Y)\sim N(\mu_X,\mu_Y,\sigma_X^2,\sigma_Y^2,\rho)\), then:

- **Conditional distribution**: \(Y\mid X=x\sim N(\mu_{Y\mid X},\sigma_{Y\mid X}^2)\), where
  \[
  \mu_{Y\mid X}=E[Y\mid X=x]=\mu_Y+\rho\frac{\sigma_Y}{\sigma_X}(x-\mu_X),
  \]
  \[
  \sigma_{Y\mid X}^2=\mathrm{Var}(Y\mid X=x)=\sigma_Y^2(1-\rho^2).
  \]
- **The conditional mean is a linear function of \(X\)**.
- **The conditional variance is independent of \(x\)** (homoscedasticity).
- **Uncorrelated \(\Leftrightarrow\) independent** (only for the bivariate normal distribution).

#### Common Pitfalls

- When computing marginal densities, respect integration limits: nonrectangular regions require correct integration ranges.
- A conditional density is defined only where \(f_Y(y)>0\).
- A conditional expectation is a function of \(y\); do not omit the variable when writing it.
- For covariance, \(E[XY]-E[X]E[Y]\) is the most commonly useful formula; do not expand the definition unnecessarily.

#### Corresponding Exercises

- **idx 4**: for the bivariate continuous joint density \(f(x,y)=8xy,\ 0<x<y<1\), compute \(E[XY]\) and \(\mathrm{Cov}(X,Y)\).
- **idx 5**: for a bivariate discrete joint distribution, compute \(\mathrm{Cov}(X,Y)\) and \(\rho(X,Y)\).
- **idx 7**: conditional expectation and conditional variance for a bivariate normal distribution.
- **idx 8**: conditional expectation and conditional variance—given \(f(x,y)=2,\ 0<x<y<1\), find \(E[X\mid Y=y]\) and \(\mathrm{Var}(X\mid Y=y)\).

### Module 4: Numerical Characteristics

#### 4.1 Expectation, Variance, and Moments

- **Expectation**: \(E[g(X)]=\int g(x)f(x)\,dx\) (continuous case), or \(\sum g(x_i)P(X=x_i)\) (discrete case).
- **Variance**: \(\mathrm{Var}(X)=E[(X-E[X])^2]=E[X^2]-(E[X])^2\).
- **\(k\)-th raw moment**: \(\mu_k=E[X^k]\).
- **\(k\)-th central moment**: \(\nu_k=E[(X-E[X])^k]\).
- **Variance under a linear transformation**: \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\).
  - Translation invariance: adding a constant does not change variance.
  - Squared scaling law: multiplying by a constant multiplies variance by the square of that constant.

#### 4.2 Moment Generating Function (MGF)

- **Definition**: \(M_X(t)=E[e^{tX}]\) (existence condition: there is an \(h>0\) such that the expectation is finite for every \(t\in(-h,h)\)).
- **Properties**:
  - \(E[X^k]=M^{(k)}(0)\) (the \(k\)-th derivative at \(t=0\)).
  - \(M_{X+Y}(t)=M_X(t)\cdot M_Y(t)\) (when \(X,Y\) are independent).
  - \(M_{aX+b}(t)=e^{bt}M_X(at)\).
- **MGFs of common distributions**:
  - Binomial \(B(n,p)\): \((pe^t+1-p)^n\).
  - Poisson \(\mathrm{Poisson}(\lambda)\): \(\exp(\lambda(e^t-1))\).
  - Exponential \(\mathrm{Exp}(\lambda)\): \(\frac\lambda{\lambda-t},\ t<\lambda\).
  - Gamma \(\mathrm{Gamma}(\alpha,\beta)\): \((1-t/\beta)^{-\alpha},\ t<\beta\).
  - Normal \(N(\mu,\sigma^2)\): \(\exp(\mu t+\frac12\sigma^2t^2)\).
- **Recognition technique**: if \(M(t)=(1-2t)^{-3}\), then \((1-\frac{t}{1/2})^{-3}\) corresponds to \(\mathrm{Gamma}(3,1/2)\), with expectation \(\alpha/\beta=6\) and variance \(\alpha/\beta^2=12\).

#### 4.3 Characteristic Function (CF)

- **Definition**: \(\varphi_X(t)=E[e^{itX}]\) (exists for every \(t\in\mathbb R\)).
- **Properties**:
  - \(|\varphi(t)|\le1\), \(\varphi(0)=1\), and \(\varphi(-t)=\overline{\varphi(t)}\).
  - \(E[X^k]=i^{-k}\varphi^{(k)}(0)\).
  - **Uniqueness theorem**: the characteristic function and distribution function correspond one-to-one (via the inversion formula).
  - **Inversion formula**: if \(\int|\varphi(t)|\,dt<\infty\), then \(X\) is continuous and has density
    \[
    f(x)=\frac1{2\pi}\int_{-\infty}^{\infty}e^{-itx}\varphi(t)\,dt.
    \]
  - **Convolution theorem**: if \(X,Y\) are independent, then \(\varphi_{X+Y}(t)=\varphi_X(t)\varphi_Y(t)\).
- **Characteristic functions of common distributions**:
  - Poisson \(\mathrm{Poisson}(\lambda)\): \(\exp(\lambda(e^{it}-1))\).
  - Normal \(N(\mu,\sigma^2)\): \(\exp(i\mu t-\frac12\sigma^2t^2)\).
  - Laplace: \(\frac1{1+t^2}\) (\(\mu=0,b=1\)).
  - Cauchy: \(e^{-|t|}\).

#### Solution Steps

1. **Use an MGF to find expectation and variance**:
   - Step 1: differentiate \(M(t)\) once and substitute \(t=0\) to obtain \(E[X]\).
   - Step 2: differentiate twice and substitute \(t=0\) to obtain \(E[X^2]\).
   - Step 3: \(\mathrm{Var}(X)=E[X^2]-(E[X])^2\).
   - Step 4 (optional): if the distribution type is recognizable, directly using its parameter formulas is faster.
2. **Use characteristic-function inversion to find a density**:
   - Step 1: identify the form of \(\varphi(t)\) by comparing it with the table of characteristic functions of common distributions.
   - Step 2: if it is recognizable, write down the density directly.
   - Step 3: if it is not recognizable, calculate using the inversion integral \(f(x)=\frac1{2\pi}\int e^{-itx}\varphi(t)\,dt\).

#### Common Pitfalls

- When differentiating an MGF with respect to \(t\), observe the chain rule.
- Distinguish MGF and CF: an MGF is \(E[e^{tX}]\), while a CF is \(E[e^{itX}]\).
- The characteristic-function inversion integral has the leading constant \(1/(2\pi)\).
- For the Gamma-distribution MGF, note the parameterization (rate \(\beta\) versus scale \(\theta\)).

#### Corresponding Exercises

- **idx 1**: given density \(f(x)=2x,\ x\in[0,1]\), integrate directly for expectation \(E[X]\) and variance \(\mathrm{Var}(X)\).
- **idx 11**: given \(M(t)=(1-2t)^{-3}\), find \(E[X]\) and \(\mathrm{Var}(X)\).
- **idx 13**: given \(\varphi(t)=1/(1+t^2)\), use inversion to obtain the Laplace density \(f(x)=\frac12e^{-|x|}\).
- **idx 14**: prove \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\).

### Module 5: Limit Theorems

#### 5.1 Modes of Convergence

| Type of convergence | Notation | Definition | Relative strength |
|---|---|---|---|
| Almost sure convergence | \(X_n\xrightarrow{a.s.}X\) | \(P(\lim X_n=X)=1\) | Strongest |
| Convergence in probability | \(X_n\xrightarrow{P}X\) | \(\forall\varepsilon>0,\ \lim_{n\to\infty}P(|X_n-X|>\varepsilon)=0\) | Intermediate |
| Convergence in distribution | \(X_n\xrightarrow{D}X\) | \(\lim F_n(x)=F(x)\) at every continuity point \(x\) of \(F\) | Weakest |

**Relation**: almost sure convergence \(\Rightarrow\) convergence in probability \(\Rightarrow\) convergence in distribution (but not conversely).

#### 5.2 Law of Large Numbers (LLN)

- **Weak law of large numbers (WLLN)**: if \(\{X_n\}\) are i.i.d. and \(E[X_i]=\mu\), then the sample mean converges in probability to \(\mu\): \(\bar X_n\xrightarrow{P}\mu\).
- **Strong law of large numbers (SLLN)**: under the same conditions, \(\bar X_n\xrightarrow{a.s.}\mu\).

#### 5.3 Central Limit Theorem (CLT)

- **Classical CLT**: if \(\{X_n\}\) are i.i.d., \(E[X_i]=\mu\), and \(\mathrm{Var}(X_i)=\sigma^2<\infty\), then
  \[
  \frac{\bar X_n-\mu}{\sigma/\sqrt n}\xrightarrow{D}N(0,1),
  \]
  that is, \(\sqrt n(\bar X_n-\mu)\xrightarrow{D}N(0,\sigma^2)\).

#### 5.4 Convergence in Probability Implies Convergence in Distribution

- **Theorem**: \(X_n\xrightarrow{P}X\ \Longrightarrow\ X_n\xrightarrow{D}X\).
- **Proof technique (important)**: for every \(\varepsilon>0\) and every continuity point \(x\) of \(F_X\):
  - **Upper bound**:
    \[
    F_{X_n}(x)=P(X_n\le x)\le P(X\le x+\varepsilon)+P(|X_n-X|>\varepsilon).
    \]
    Reason: if \(X_n\le x\) and \(X>x+\varepsilon\), then \(|X_n-X|>\varepsilon\).
  - **Lower bound**: \(P(X\le x-\varepsilon)\le P(X_n\le x)+P(|X_n-X|>\varepsilon)\), i.e.
    \[
    F_{X_n}(x)\ge F_X(x-\varepsilon)-P(|X_n-X|>\varepsilon).
    \]
  - Let \(n\to\infty\), using convergence in probability; then let \(\varepsilon\to0^+\), using continuity.

#### 5.5 Slutsky’s Theorem

- **Theorem**: if \(X_n\xrightarrow{D}X\) and \(Y_n\xrightarrow{P}c\) (a constant), then:
  - \(X_n+Y_n\xrightarrow{D}X+c\);
  - \(X_n\cdot Y_n\xrightarrow{D}cX\);
  - \(X_n/Y_n\xrightarrow{D}X/c\) (if \(c\ne0\)).
- **Special case**: when \(Y_n\xrightarrow{P}0\), \(X_n+Y_n\xrightarrow{D}X\).
- **Proof technique**:
  - Upper bound: \(P(X_n+Y_n\le x)\le P(X_n\le x+\varepsilon)+P(|Y_n|>\varepsilon)\).
  - Lower bound: \(P(X_n+Y_n\le x)\ge P(X_n\le x-\varepsilon)-P(|Y_n|>\varepsilon)\).
  - Let \(n\to\infty\) and \(\varepsilon\to0^+\) (along a sequence of continuity points of \(F_X\)), using \(Y_n\xrightarrow{P}0\) and \(X_n\xrightarrow{D}X\).
  - **Key technique**: the discontinuities of \(F_X\) are at most countable, so choose a decreasing sequence \(\varepsilon_k\to0^+\) for which both \(x\pm\varepsilon_k\) are continuity points.

#### Common Pitfalls

- Convergence in distribution is required only at continuity points of \(F_X\), not at every point.
- In a proof of Slutsky’s theorem, whether \(x\pm\varepsilon\) are continuity points requires extra care (choose a sequence \(\varepsilon_k\) of continuity points).
- Convergence in probability does not reverse from convergence in distribution: \(X_n\xrightarrow{D}X\not\Rightarrow X_n\xrightarrow{P}X\), unless \(X\) is constant.
- Keep the convergence notations \(P\), \(D\), and \(a.s.\) distinct.

#### Corresponding Exercises

- **idx 18**: prove \(X_n\xrightarrow{P}X\Rightarrow X_n\xrightarrow{D}X\).
- **idx 19**: prove Slutsky’s special case \(X_n\xrightarrow{D}X\) and \(Y_n\xrightarrow{P}0\Rightarrow X_n+Y_n\xrightarrow{D}X\).
- **idx 12**: distribution of the sum of two independent \(U(0,1)\) variables (convolution; the question provides preparation for limit theorems).

### Module 6: Inequalities and Properties

#### 6.1 Markov’s Inequality

- **Theorem**: for a nonnegative random variable \(X\) (that is, \(X\ge0\) almost surely) and every \(\varepsilon>0\),
  \[
  P(X\ge\varepsilon)\le\frac{E[X]}{\varepsilon}.
  \]
- **Proof idea**: introduce the indicator \(I_{\{X\ge\varepsilon\}}\), prove \(I\le X/\varepsilon\) almost surely, and then take expectations.
  - When \(X\ge\varepsilon\), \(1\le X/\varepsilon\).
  - When \(X<\varepsilon\), \(0\le X/\varepsilon\) by nonnegativity.

#### 6.2 Chebyshev’s Inequality

- **Theorem**: for every random variable \(X\), with \(E[X]=\mu\) and \(\mathrm{Var}(X)=\sigma^2<\infty\), and every \(k>0\),
  \[
  P(|X-\mu|\ge k)\le\frac{\sigma^2}{k^2}.
  \]
- Equivalent form: \(P(|X-\mu|\ge k\sigma)\le\frac1{k^2}\).
- **Derivation**: apply Markov’s inequality to the nonnegative random variable \((X-\mu)^2\).

#### 6.3 Variance Properties

- Linear transformation: \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\).
- Translation invariance: adding a constant \(b\) does not change variance.
- Squared scaling law: multiplying by a constant \(a\) multiplies variance by \(a^2\).

#### Common Pitfalls

- Markov’s inequality requires a nonnegative random variable; this is its key hypothesis.
- Chebyshev’s inequality gives an upper bound, which need not be tight.
- In \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\), do not forget the square.

#### Corresponding Exercises

- **idx 15**: prove Markov’s inequality \(P(X\ge\varepsilon)\le E[X]/\varepsilon\) (\(X\ge0\)).
- **idx 14**: prove \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\).

---

### Module 7: Bayes’ Formula and Total Probability

#### Core Concepts

- **Law of total probability**: if \(\{B_i\}\) is a partition of the sample space, then
  \[
  P(A)=\sum_iP(A\mid B_i)P(B_i).
  \]
- **Bayes’ formula**:
  \[
  P(B_i\mid A)=\frac{P(A\mid B_i)P(B_i)}{P(A)}
  =\frac{P(A\mid B_i)P(B_i)}{\sum_jP(A\mid B_j)P(B_j)}.
  \]
- Prior probability \(P(B_i)\) versus posterior probability \(P(B_i\mid A)\).

#### Solution Steps

1. Define events: represent every event in the problem by a letter (for example, \(D\) = disease and \(+\) = positive).
2. Write the known probabilities: \(P(D)\) (prior), \(P(+\mid D)\) (sensitivity/true-positive rate), and \(P(+\mid\neg D)\) (false-positive rate).
3. Use total probability to calculate \(P(+)\).
4. Use Bayes’ formula to calculate the posterior probability \(P(D\mid+)\).

#### Common Pitfalls

- Do not confuse \(P(A\mid B)\) with \(P(B\mid A)\) (the “inverse probability fallacy”).
- When calculating \(P(+\mid\neg D)\), note that the false-positive rate is \(P(+\mid\neg D)\), not \(P(\neg D\mid+)\).
- Do not omit any part of the partition in the denominator of total probability.

#### Corresponding Exercise

- **idx 3**: a Bayes disease-testing problem—given \(P(D)=0.01\), \(P(+\mid D)=0.99\), and \(P(+\mid\neg D)=0.02\), find \(P(D\mid+)=1/3\).

---

### Module 8: Distribution of a Sum of Independent Random Variables (Convolution)

#### Core Concepts

- **Convolution formula** (continuous case): if \(X,Y\) are independent with densities \(f_X,f_Y\), then the density of \(Z=X+Y\) is
  \[
  f_Z(z)=\int_{-\infty}^{\infty}f_X(x)f_Y(z-x)\,dx=(f_X*f_Y)(z).
  \]
- **Convolution formula** (discrete case): \(P(Z=k)=\sum_iP(X=i)P(Y=k-i)\).
- **MGF/CF method**: \(\varphi_{X+Y}(t)=\varphi_X(t)\varphi_Y(t)\) (by independence); use uniqueness of characteristic functions to obtain the distribution.

#### Solution Steps

1. Write \(f_Z(z)=\int f_X(x)f_Y(z-x)\,dx\).
2. Determine the effective integration region for \(x\): it must **simultaneously satisfy** \(f_X(x)>0\) and \(f_Y(z-x)>0\).
3. **Split into cases** according to the range of \(z\), and calculate the integral separately on each interval of \(z\).
4. Simplify into a piecewise density function.

#### Common Pitfalls

- Incorrect integration limits: failing to determine the piecewise ranges of \(z\) correctly.
- Omitting ranges of \(z\) for which the density is \(0\).
- Geometric intuition for the convolution integral: the range of \(z\) is \([a_X+b_X,a_Y+b_Y]\), where \(a,b\) are support-interval endpoints of the distributions.

#### Corresponding Exercises

- **idx 12**: \(X,Y\stackrel{i.i.d.}{\sim}U(0,1)\); \(Z=X+Y\) has triangular density \(f_Z(z)=z\ (0<z<1),\ 2-z\ (1<z<2)\).
- **idx 16**: Poisson additivity—prove using discrete convolution or characteristic functions.

## General Problem-Solving Methodology

### 1. Problem-Type Recognition

On receiving a problem, first determine:

| Problem feature | Corresponding module |
|---|---|
| Balls/drawing lots/combinations | Module 1: classical probability models |
| A named distribution + find a probability | Module 2: discrete/continuous distributions |
| Joint density/joint distribution law + find covariance/correlation coefficient | Module 3: multivariate random variables |
| Known density/PMF + find expectation/variance | Module 4: numerical characteristics |
| Known MGF/CF + find expectation/distribution | Module 4: moment generating functions/characteristic functions |
| “Prove XX converges” / “\(X_n\to Y_n\)” | Module 5: limit theorems |
| Conditional probability + prior/posterior | Module 7: Bayes’ formula |
| “Prove an inequality” / “\(\mathrm{Var}(aX+b)\)” | Module 6: inequalities and properties |

### 2. Method Selection

| Problem type | Preferred method | Alternative method |
|---|---|---|
| Find expectation | Direct integration/summation | Differentiate MGF or CF |
| Find variance | \(E[X^2]-(E[X])^2\) | \(M''(0)-(M'(0))^2\) from MGF |
| Find distribution of \(X+Y\) | Convolution integral | Product of MGFs/CFs |
| Determine additivity | Characteristic-function method | Convolution + induction |
| Find conditional expectation | Find conditional density first | Substitute directly into bivariate-normal formula |
| Prove convergence | Two-sided inequality + take limits | Use known theorems such as Slutsky’s |

### 3. Result Verification

- **Plausibility check**: probabilities lie in \([0,1]\); correlation coefficients lie in \([-1,1]\).
- **Dimensional check**: variance has the dimension of squared expectation.
- **Boundary cases**: verify that results are reasonable for extreme parameter values.
- **Symmetry check**: if \(X,Y\) are symmetric, expectation and variance should be symmetric.
- **SymPy numerical verification**: check computational results independently.

---

## SymPy Verification Techniques

This section gives SymPy verification approaches usable during a Python generation stage; the problem statement remains the sole source of samples and parameters.

### Integral Verification

For expectation and variance of continuous random variables:

```python
import sympy as sp

x = sp.Symbol('x', real=True)

# Example: density f(x)=2x, x∈[0,1]
f = 2*x
EX = sp.integrate(x * f, (x, 0, 1))       # expectation
EX2 = sp.integrate(x**2 * f, (x, 0, 1))   # second moment
VarX = sp.simplify(EX2 - EX**2)           # variance

# Verified result: E[X]=2/3, Var(X)=1/18
```

For integrals of bivariate joint distributions:

```python
x, y = sp.symbols('x y', real=True)

# Example: f(x,y)=8xy, 0<x<y<1
f_xy = 8*x*y
EXY = sp.integrate(sp.integrate(x*y * f_xy, (y, x, 1)), (x, 0, 1))
EX = sp.integrate(sp.integrate(x * f_xy, (y, x, 1)), (x, 0, 1))
EY = sp.integrate(sp.integrate(y * f_xy, (y, x, 1)), (x, 0, 1))
Cov = sp.simplify(EXY - EX*EY)
```

### Summation Verification

For discrete random variables:

```python
k = sp.Symbol('k', integer=True, nonnegative=True)

# Example: binomial B(5, 1/3), P(X=2)
n, p = 5, sp.Rational(1,3)
prob = sp.binomial(n, 2) * p**2 * (1-p)**(n-2)
# Result: 80/243
```

For a Poisson distribution:

```python
import sympy as sp

lam = 3
# P(X=2) = e^{-λ} λ²/2!
p2 = sp.exp(-lam) * lam**2 / 2
# P(X≥1) = 1 - e^{-λ}
p_ge1 = 1 - sp.exp(-lam)
```

### Characteristic-Function Verification

```python
t = sp.Symbol('t', real=True)

# Verify that characteristic function φ(t) = 1/(1+t²) corresponds to Laplace(0,1)
# Verify through Fourier inversion:
phi = 1/(1 + t**2)
# sympy's inverse_fourier_transform can be used for verification
```

### Linear-Algebra Verification

For covariance matrices and correlation coefficients:

```python
# Verify bivariate-normal conditional distribution
rho = sp.Rational(1,2)
sigma_X, sigma_Y = 1, 2
mu_X, mu_Y = 0, 0

# E[Y|X=1] = μ_Y + ρ·(σ_Y/σ_X)·(1 - μ_X)
EY_given_X1 = mu_Y + rho * (sigma_Y/sigma_X) * (1 - mu_X)
# = 0 + (1/2)·(2/1)·1 = 1

# Var(Y|X=1) = σ_Y²·(1 - ρ²)
VarY_given_X1 = sigma_Y**2 * (1 - rho**2)
# = 4·(1 - 1/4) = 3
```

### Numerical-Approximation Verification

For complicated integrals, SymPy numerical integration with `.evalf()` can be used for a quick check:

```python
# Example: verify P(Z>1) = 1/2 (sum of two independent U(0,1) variables)
z = sp.Symbol('z', real=True)
# f_Z(z) = z (0<z<1), 2-z (1<z<2)
p = sp.integrate(2 - z, (z, 1, 2))
sp.simplify(p)  # 1/2
```

### Convolution Verification

```python
# Sum of two independent U(0,1) variables
x, z = sp.symbols('x z', real=True)
# f_Z(z) = ∫ f_X(x) f_Y(z-x) dx
# f_X(x)=1 for x∈[0,1], f_Y(y)=1 for y∈[0,1]
# When 0<z<1: x∈[0,z]
f1 = sp.integrate(1, (x, 0, z))          # = z
# When 1<z<2: x∈[z-1,1]
f2 = sp.integrate(1, (x, z-1, 1))        # = 2-z
```

---

## Exercise Index

| idx | Problem type | Difficulty | Topic | Key knowledge | Core formula/method | Verification method |
|---:|---|---|---|---|---|---|
| 0 | Computation | Easy | Classical probability | Hypergeometric distribution | \(P=\frac{C_5^2C_3^1}{C_8^3}=\frac{15}{28}\) | Direct calculation of combinations |
| 1 | Computation | Easy | Expectation and variance | Continuous-density integral | \(E[X]=\int xf(x)\,dx\), \(\mathrm{Var}(X)=E[X^2]-(E[X])^2\) | SymPy integration |
| 2 | Computation | Easy | Binomial distribution | pmf formula | \(P(X=k)=\binom nkp^k(1-p)^{n-k}\) | Combinations + exponentiation |
| 3 | Computation | Intermediate | Bayes’ formula | Total probability + posterior probability | \(P(D\mid+)=\frac{P(+\mid D)P(D)}{P(+)}\) | Rational-number arithmetic |
| 4 | Computation | Intermediate | Bivariate continuous distribution | Joint-density integration/covariance | \(E[XY]=\iint xyf(x,y)\), \(\mathrm{Cov}=E[XY]-E[X]E[Y]\) | SymPy double integration |
| 5 | Computation | Intermediate | Correlation coefficient | Discrete joint distribution | \(\rho=\frac{\mathrm{Cov}(X,Y)}{\sigma_X\sigma_Y}\) | Term-by-term calculation for discrete random variables |
| 6 | Computation | Intermediate | Distribution of a function of a random variable | Distribution-function method | \(F_Y(y)=P(-\ln X\le y)\Rightarrow Y\sim\mathrm{Exp}(1)\) | Variable transformation + distribution recognition |
| 7 | Computation | Intermediate | Bivariate normal conditional distribution | Conditional expectation/variance formulas | \(E[Y\mid X=x]=\mu_Y+\rho\frac{\sigma_Y}{\sigma_X}(x-\mu_X)\) | Direct substitution in bivariate-normal formula |
| 8 | Computation | Intermediate | Conditional expectation | Conditional-density method | \(f_{X\mid Y}(x\mid y)=\frac{f(x,y)}{f_Y(y)}\) | Marginal density + conditional-density integral |
| 9 | Computation | Intermediate | Poisson distribution | pmf \(e^{-\lambda}\lambda^k/k!\) | \(P(X\ge1)=1-P(X=0)\) | SymPy summation/\(\exp\) function |
| 10 | Computation | Intermediate | Higher exponential moments | Gamma integral | \(E[X^n]=n!/\lambda^n\) | SymPy integral verification |
| 11 | Computation | Intermediate | Moment generating function | MGF differentiation/distribution recognition | \(M(t)=(1-2t)^{-3}\), \(E[X]=M'(0)\) | SymPy differentiation + substitution |
| 12 | Computation | Hard | Distribution of a sum of independent random variables | Convolution formula | \(f_Z(z)=\int f_X(x)f_Y(z-x)\,dx\) | SymPy piecewise integration |
| 13 | Computation | Hard | Characteristic-function inversion | CF uniqueness | \(\varphi(t)=1/(1+t^2)\Leftrightarrow f(x)=\frac12e^{-|x|}\) | CF lookup table + inversion integral |
| 14 | Proof | Easy | Variance property | Linear transformation | \(\mathrm{Var}(aX+b)=a^2\mathrm{Var}(X)\) | Algebraic expansion verification |
| 15 | Proof | Intermediate | Markov’s inequality | Indicator-function technique | \(P(X\ge\varepsilon)\le E[X]/\varepsilon\) | Inequality-logic derivation |
| 16 | Proof | Intermediate | Poisson additivity | CF/convolution method | \(\varphi_{X+Y}=\exp((\lambda_1+\lambda_2)(e^{it}-1))\) | CF product + uniqueness |
| 17 | Proof | Intermediate | Exponential memorylessness | Conditional probability + survival function | \(\frac{P(X>s+t)}{P(X>s)}=e^{-\lambda t}\) | Algebraic simplification |
| 18 | Proof | Hard | Probability \(\to\) distribution | Two-sided inequality | \(F_X(x-\varepsilon)-\delta\le F_n(x)\le F_X(x+\varepsilon)+\delta\) | \(\varepsilon\)-\(\delta\)-type logic |
| 19 | Proof | Hard | Slutsky’s theorem | Inequality + continuity-point selection | \(P(X_n\le x-\varepsilon)-o(1)\le P(X_n+Y_n\le x)\le P(X_n\le x+\varepsilon)+o(1)\) | Two-limit argument |

## Common Errors and Pitfalls

### Classical Probability Models

1. **Confusing sampling with vs. without replacement**: with replacement use the binomial distribution \(C_n^kp^k(1-p)^{n-k}\); without replacement use the hypergeometric distribution \(\frac{C_K^kC_{N-K}^{n-k}}{C_N^n}\).
2. **Failing to take a complement for “at least”**: \(P(\text{at least }1)=1-P(0)\); do not sum directly.
3. **Confusing combinations and permutations**: \(\binom nk\) does not count order, while \(P_n^k\) does.

### Continuous Distributions

4. **Confusing exponential parameterizations**: \(f(x)=\lambda e^{-\lambda x}\) has expectation \(1/\lambda\), whereas \(f(x)=\frac1\theta e^{-x/\theta}\) has expectation \(\theta\). Confirm which parameterization is used before solving.
5. **Incorrect standardization of a normal distribution**: \(Z=\frac{X-\mu}{\sigma}\sim N(0,1)\); do not forget division by \(\sigma\).
6. **Omitting the absolute value in a variable transformation**: \(f_Y(y)=f_X(g^{-1}(y))\cdot|d(g^{-1})/dy|\); note the absolute value of the Jacobian.

### Multivariate Random Variables

7. **Incorrect integration limits**: double integrals over nonrectangular regions require correct splitting; for example, for \(0<x<y<1\), the range of \(x\) is \([0,y]\) or \([0,1]\), depending on the integration order.
8. **Covariance is not independence**: \(\mathrm{Cov}(X,Y)=0\) does not mean \(X\) and \(Y\) are independent (except in the bivariate normal case).
9. **Conditional expectation is a random variable**: \(E[X\mid Y]\) is a function of \(Y\), not a constant.
10. **Correlation-coefficient calculation**: \(\rho=\frac{\mathrm{Cov}(X,Y)}{\sigma_X\sigma_Y}\); the denominator is the product of standard deviations, not of variances.

### Numerical Characteristics

11. **Variance formula**: remember \(\mathrm{Var}(X)=E[X^2]-(E[X])^2\), which is much faster than expanding the definition directly.
12. **MGF differentiation**: \(M^{(k)}(0)=E[X^k]\); substitute \(t=0\) before obtaining the moment.
13. **Gamma-distribution recognition**: \(M(t)=(1-\beta t)^{-\alpha}\) corresponds to \(\mathrm{Gamma}(\alpha,\beta)\) (rate parameterization), with expectation \(\alpha/\beta\) and variance \(\alpha/\beta^2\).
14. **Distinguishing CF from MGF**: \(\varphi(t)=E[e^{itX}]\) versus \(M(t)=E[e^{tX}]\); they differ by a factor \(i\).

### Limit Theorems

15. **Requirement on convergence points in distribution**: convergence is only required at continuity points of the distribution function; a proof must handle the (countably many) discontinuities.
16. **Condition in Slutsky’s theorem**: \(Y_n\xrightarrow{P}c\) requires \(c\) to be a constant, not a random variable.
17. **Convergence directions are not reversible**: convergence in distribution is the weakest; it cannot imply convergence in probability or almost sure convergence.
18. **Order of limits in \(\varepsilon\) and \(n\)**: take \(n\to\infty\) first and \(\varepsilon\to0^+\) second; the order cannot be interchanged.

### Inequalities

19. **Markov’s inequality hypothesis**: the random variable must be nonnegative, \(X\ge0\), otherwise the conclusion fails.
20. **Chebyshev follows from Markov**: applying Markov’s inequality to \((X-E[X])^2\) gives Chebyshev’s inequality.

### Bayes’ Formula

21. **Reversing prior and posterior**: the desired probability is \(P(\text{disease}\mid\text{positive})\), not \(P(\text{positive}\mid\text{disease})\). The former is the posterior probability; the latter is the likelihood.
22. **Omitting the total-probability denominator**: the denominator in Bayes’ formula must include every possible path (diseased and positive + not diseased and positive).

---

## Distribution Quick Reference

### Discrete Distributions

| Distribution | Notation | PMF \(P(X=k)\) | \(E[X]\) | \(\mathrm{Var}(X)\) | MGF \(M(t)\) | CF \(\varphi(t)\) |
|---|---|---|---|---|---|---|
| Binomial | \(B(n,p)\) | \(\binom nkp^kq^{n-k}\) | \(np\) | \(npq\) | \((pe^t+q)^n\) | \((pe^{it}+q)^n\) |
| Poisson | \(\mathrm{Pois}(\lambda)\) | \(e^{-\lambda}\lambda^k/k!\) | \(\lambda\) | \(\lambda\) | \(\exp(\lambda(e^t-1))\) | \(\exp(\lambda(e^{it}-1))\) |
| Geometric | \(\mathrm{Geom}(p)\) | \(pq^{k-1}\) | \(1/p\) | \(q/p^2\) | \(\frac{pe^t}{1-qe^t}\) | \(\frac{pe^{it}}{1-qe^{it}}\) |
| Hypergeometric | \(\mathrm{Hyp}(N,K,n)\) | \(\frac{\binom Kk\binom{N-K}{n-k}}{\binom Nn}\) | \(nK/N\) | \(n\frac KN\frac{N-K}{N}\frac{N-n}{N-1}\) | — | — |

### Continuous Distributions

| Distribution | Notation | Density \(f(x)\) | \(E[X]\) | \(\mathrm{Var}(X)\) | MGF \(M(t)\) | CF \(\varphi(t)\) |
|---|---|---|---|---|---|---|
| Uniform | \(U(a,b)\) | \(\frac1{b-a}\) | \(\frac{a+b}{2}\) | \(\frac{(b-a)^2}{12}\) | \(\frac{e^{tb}-e^{ta}}{t(b-a)}\) | \(\frac{e^{itb}-e^{ita}}{it(b-a)}\) |
| Exponential | \(\mathrm{Exp}(\lambda)\) | \(\lambda e^{-\lambda x}\) | \(1/\lambda\) | \(1/\lambda^2\) | \(\frac\lambda{\lambda-t}\) | \(\frac\lambda{\lambda-it}\) |
| Normal | \(N(\mu,\sigma^2)\) | \(\frac1{\sqrt{2\pi}\sigma}e^{-\frac{(x-\mu)^2}{2\sigma^2}}\) | \(\mu\) | \(\sigma^2\) | \(\exp(\mu t+\frac{\sigma^2t^2}{2})\) | \(\exp(i\mu t-\frac{\sigma^2t^2}{2})\) |
| Gamma | \(\mathrm{Gamma}(\alpha,\beta)\) | \(\frac{\beta^\alpha}{\Gamma(\alpha)}x^{\alpha-1}e^{-\beta x}\) | \(\alpha/\beta\) | \(\alpha/\beta^2\) | \((1-t/\beta)^{-\alpha}\) | \((1-it/\beta)^{-\alpha}\) |
| Laplace | \(\mathrm{Laplace}(\mu,b)\) | \(\frac1{2b}e^{-|x-\mu|/b}\) | \(\mu\) | \(2b^2\) | \(\frac{e^{\mu t}}{1-b^2t^2}\) | \(\frac{e^{i\mu t}}{1+b^2t^2}\) |

### Competition Extension: Normal Approximation and Quantile Inversion for the Binomial Distribution

#### Core Concepts

When \(n\) is sufficiently large, the binomial distribution \(B(n,p)\) can be approximated by the normal distribution \(N(np,np(1-p))\). By the central limit theorem,

\[
\frac{X-np}{\sqrt{np(1-p)}}\xrightarrow{D}N(0,1).
\]

This approximation is usually reliable when \(np\ge5\) and \(n(1-p)\ge5\). In practice, normal approximation is used not only for approximate probability calculation, but also extensively for sample-size planning, hypothesis tests, and construction of confidence intervals. Quantile inversion is the key technique: given an allowed error and confidence level, solve backward for the required minimum sample size; or, given a sample size, solve backward for a parameter interval covered with specified probability.

#### Commonly Used Formulas

1. **Normal-approximation probability (with continuity correction)**:
   \[
   P(a\le X\le b)\approx\Phi\left(\frac{b+0.5-np}{\sqrt{npq}}\right)-\Phi\left(\frac{a-0.5-np}{\sqrt{npq}}\right),
   \]
   where \(q=1-p\), and \(+0.5\) and \(-0.5\) are continuity-correction terms that effectively improve approximation accuracy.

2. **Two-tailed decomposition**:
   \[
   P(|X-np|\ge\delta)\approx2\left(1-\Phi\left(\frac\delta{\sqrt{npq}}\right)\right).
   \]

3. **Quantile inversion**: given confidence level \(1-\alpha\), determine \(\delta\) such that
   \[
   P(|X-np|\le z_{\alpha/2}\sqrt{npq})\approx1-\alpha,
   \]
   where \(z_{\alpha/2}\) is the \(1-\alpha/2\) quantile of the standard normal distribution (for example, when \(\alpha=0.05\), \(z_{0.025}\approx1.96\)).

4. **Sample-size formula**: if the probability that a binomial-proportion estimation error does not exceed \(\varepsilon\) must be at least \(1-\alpha\), then
   \[
   n\ge\frac{z_{\alpha/2}^2\cdot p(1-p)}{\varepsilon^2}.
   \]
   When \(p\) is unknown, use the most conservative estimate \(p=1/2\), giving \(n\ge\frac{z_{\alpha/2}^2}{4\varepsilon^2}\).

#### Solution Steps

1. Verify normal-approximation conditions: \(np\ge5\) and \(n(1-p)\ge5\).
2. Compute mean and standard deviation: \(\mu=np\), \(\sigma=\sqrt{np(1-p)}\).
3. Standardize: \(Z=\frac{X-\mu}{\sigma}\approx N(0,1)\).
4. Look up a standard-normal quantile table or calculate using SymPy’s `sp.Normal`.
5. Observe rounding direction for continuity correction: for an upper-tail probability, add \(0.5\) to the upper endpoint and subtract \(0.5\) from the lower endpoint; for quantile inversion, round the final sample size upward.

#### Exam Solution Techniques

- Quickly decide whether normal approximation is available: mentally check that both \(np\) and \(n(1-p)\) are at least \(5\); if either fails, switch to exact binomial calculation.
- Memorize common quantiles: \(z_{0.025}=1.96\), \(z_{0.05}=1.645\), \(z_{0.005}=2.576\); no table is needed during an examination.
- For quantile inversion, first write the inequality, rearrange to solve for \(n\), then round upward to get an integer sample size.
- If the problem gives a proportion form (such as the distribution of \(\hat p=X/n\)), use \(p(1-p)/n\) for the variance when standardizing.

#### Frequent Exam Pitfalls

- Forgetting continuity correction reduces accuracy, especially when \(n\) is not large enough.
- Confusing one- and two-tailed quantiles: two-tailed \(\alpha\) corresponds to \(z_{\alpha/2}\), while one-tailed corresponds to \(z_\alpha\). For example, a \(95\%\) confidence interval uses \(z_{0.025}\approx1.96\), not \(z_{0.05}\approx1.645\).
- Rounding in the wrong direction: sample size \(n\) must be an integer rounded upward (conservatively); rounding downward can cause the actual confidence level to miss the target.
- When \(n\) is too small, normal approximation is unreliable; instead use the Clopper–Pearson exact interval or a Poisson approximation (when \(p\) is very small and \(n\) is very large).

---

### Competition Extension: Arithmetic–Harmonic Mean Operations and Fractional Linear Transformations

#### Core Concepts

For two positive numbers \(a,b>0\), define the arithmetic mean \(A(a,b)=\frac{a+b}{2}\) and harmonic mean \(H(a,b)=\frac{2ab}{a+b}\). Repeatedly taking the arithmetic and harmonic means converges to the geometric mean \(\sqrt{ab}\), and does so extremely rapidly (accuracy doubles every two iterations).

A fractional linear transformation (Möbius transformation) has the form
\[
f(z)=\frac{az+b}{cz+d},\quad ad-bc\ne0,
\]
with matrix representation \(\begin{pmatrix}a&b\\c&d\end{pmatrix}\); composition of transformations corresponds to matrix multiplication.

In probability theory, these two topics are linked through the **probability generating function (PGF)** \(G(s)=E[s^X]=\sum_{k=0}^{\infty}P(X=k)s^k\). In a branching process, if the offspring-distribution PGF has fractional-linear form, the fixed-point equation for extinction probability can be solved analytically, while mean estimation involves the inequality chain for arithmetic, harmonic, and geometric means.

#### Commonly Used Formulas

1. **Arithmetic–harmonic–geometric mean inequality**:
   \[
   H(a,b)\le G(a,b)\le A(a,b),
   \]
   where \(G(a,b)=\sqrt{ab}\) is the geometric mean, and all equalities hold if and only if \(a=b\).

2. **Arithmetic–harmonic mean iteration**: define \(a_{n+1}=A(a_n,b_n)\), \(b_{n+1}=H(a_n,b_n)\). Then
   \[
   \lim_{n\to\infty}a_n=\lim_{n\to\infty}b_n=\sqrt{a_0b_0}.
   \]

3. **Matrix representation of a fractional linear transformation**: if \(f_k(z)=\frac{a_kz+b_k}{c_kz+d_k}\) (\(k=1,2\)), then
   \[
   (f_1\circ f_2)(z)=\frac{(a_1a_2+b_1c_2)z+(a_1b_2+b_1d_2)}{(c_1a_2+d_1c_2)z+(c_1b_2+d_1d_2)},
   \]
   and the corresponding transformation matrix is \(\begin{pmatrix}a_1&b_1\\c_1&d_1\end{pmatrix}\begin{pmatrix}a_2&b_2\\c_2&d_2\end{pmatrix}\).

4. **Branching-process extinction probability**: if the offspring distribution is geometric \(\text{Geom}(p)\), with \(P(X=k)=(1-p)^kp\), then its PGF is
   \[
   G(s)=\frac{p}{1-(1-p)s}=\frac{ps+0}{-(1-p)s+1}.
   \]
   This is exactly a fractional linear transformation. The extinction probability \(\pi\) satisfies \(\pi=G(\pi)\), giving \(\pi=\min(1,\frac p{1-p})\).

#### Exam Solution Techniques

- A fixed point of a fractional linear transformation can be found by solving \(cz^2+(d-a)z-b=0\); substitute directly during an examination, without deriving it from matrices.
- The mean inequality chain \(H\le G\le A\) quickly bounds an unknown expectation.
- A quick way to decide branching-process extinction: if \(E[X]=G'(1)\le1\) and \(P(X=1)<1\), then the extinction probability is \(1\); if \(E[X]>1\), it is the smallest positive root of \(\pi=G(\pi)\).
- Remember \(G'(1)=E[X]\) and \(G''(1)=E[X(X-1)]\); these can quickly compute the mean and variance of the offspring distribution.

#### Frequent Exam Pitfalls

- The matrix representation of a fractional linear transformation is not unique: multiplying every coefficient by the same nonzero constant leaves the transformation unchanged but changes the matrix. Do not dwell on the matrix’s particular numerical entries in an examination.
- Arithmetic–harmonic mean iteration converges to the geometric mean, but not linearly: it has quadratic convergence (the accuracy approximately doubles each iteration).
- The extinction probability \(\pi\) is the **smallest** nonnegative root in \([0,1]\) of \(\pi=G(\pi)\), not just any root. If \(E[X]>1\), \(G(s)=s\) has another root \(\pi<1\) in \([0,1)\).
- Do not confuse a fractional-linear-transformation “fixed point” (a mathematical solution of \(f(z)=z\)) with a PGF “extinction probability”: the latter specifically is the smallest fixed point in \([0,1]\), and can be less than \(1\) only when \(f(0)>0\) (that is, \(P(X=0)>0\)).

---

## Reference Resources

- Supporting verification knowledge prompt: `Probability Theory Verification Example.py`.
- Dataset source: `Probability Theory.md` (20 problems, covering every core knowledge point).
- Recommended textbook: *Probability Theory and Mathematical Statistics* (Mao Shisong, Cheng Yiming, and Pu Xiaolong, eds.).
- Online tools: Wolfram Alpha, SymPy Live.

## General Supplement: Capacity Risk and Normal Approximation

1. First reduce multiple independent binary choices to a binomial random variable; a resource-shortage event is usually a tail event, and when necessary split it using mutually exclusive or symmetric relations.
2. When using a normal approximation, state the mean, variance, standardized variable, and continuity correction, then invert a quantile from the risk threshold. When capacity is an integer, check the direction at adjacent integers.
3. An approximation supplies only a candidate threshold; near a critical boundary, cross-check using an exact binomial tail sum or a reliable bound, and do not treat approximate equality as a strict conclusion.

## Quick Reference: Symmetric Binomial Capacity and Quantile Inversion

- **Retrieval terms:** probability, upper bound, normal approximation, Gaussian distribution, symmetric capacity, independent choices, binomial.
- **Core content:** For $X\sim B(N,1/2)$, set $\mu=N/2$ and $\sigma=\sqrt N/2$. If two equal-capacity alternatives each have capacity $x\ge\mu$, overflow on either side is the union of two symmetric tails:

$$
P(E)=2P(X>x).
$$

Given a total risk tolerance $\varepsilon$, reduce to one-tail probability $\varepsilon/2$, use

$$
x\ge\mu+\sigma\Phi^{-1}(1-\varepsilon/2),
$$

then round upward and check the candidate and preceding integer using the exact binomial distribution.
- **Pitfalls:** Do not forget the two-tail reduction, round a required capacity downward, or treat the normal approximation as a substitute for checking a critical integer boundary.
