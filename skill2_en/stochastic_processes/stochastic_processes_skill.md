---
name: stochastic-processes-verification
description: Use when verifying stochastic processes problems — Markov chains, Poisson processes, Brownian motion, birth-death processes, renewal processes, martingales, and queueing theory
---

# Stochastic Processes Problem-Solving and Verification Skill

## Domain Boundaries and Routing Conventions

- Scope: Markov chains, Poisson processes, Brownian motion, birth--death/renewal processes, martingales, stopping times, and cover times.
- Do not take over: static distributions and probability calculations should be routed to probability theory; time-series observation data, trends, and seasonal adjustment should be routed to statistical inference.
- Verification contract: make discrete step count and time indexing explicit; if a problem starts timing at $t=1$, retain its additional $+1$. Check stopping-time and state-space conditions.

## Time-Series Compatibility Conventions

Classical time-series decomposition has long-run trend $T$, seasonal variation $S$, cyclical variation $C$, and irregular component $I$. “Random variation” is usually synonymous with the irregular component and must not be counted twice. Weak stationarity requires constant mean and variance and covariance depending only on lag; white noise additionally requires distinct periods to be uncorrelated. Moving-average ratio methods and X-11/X-13 are common for seasonal adjustment.

## Overview

This manual covers core undergraduate stochastic processes: discrete-time Markov chains (transition matrices, stationary distributions, periodicity, limiting distributions, absorption probabilities); Poisson processes (basic probabilities, nonhomogeneous processes, independent superposition, waiting-time distributions); compound Poisson processes (expectation and variance); birth--death processes and M/M/1 queues; Brownian motion (covariance, martingale property, hitting times, reflection principle); random walks; renewal processes (elementary renewal theorem); exponential distributions and order statistics; and martingales and stopping times (Doob's bounded stopping theorem). It uses 20 selected exercises to organize concepts, theorems, solution procedures, pitfalls, and verification prompts for learning, review, and automated solution verification.

---

## Knowledge System

### Module 1: Fundamentals of Discrete-Time Markov Chains

#### Core Concepts

- A **Markov chain** $\{X_n,n=0,1,2,\ldots\}$ on state space $S$ is a DTMC if, for every $n$ and $i_0,\ldots,i_{n-1},i,j\in S$,

  $$P(X_{n+1}=j\mid X_n=i,X_{n-1}=i_{n-1},\ldots,X_0=i_0)=P(X_{n+1}=j\mid X_n=i).$$

- **Time-homogeneous transition probability:** $p_{ij}=P(X_{n+1}=j\mid X_n=i)$, independent of $n$.
- **Transition matrix:** $P=[p_{ij}]_{i,j\in S}$, each row summing to $1$.
- **$n$-step transition probability:** $p_{ij}^{(n)}=P(X_n=j\mid X_0=i)=[P^n]_{ij}$, guaranteed by Chapman--Kolmogorov.
- **Stationary distribution:** nonnegative row vector $\pi=(\pi_i)_{i\in S}$ satisfying $\pi=\pi P$ and $\sum_i\pi_i=1$.
- **Chapman--Kolmogorov equation:**

  $$p_{ij}^{(m+n)}=\sum_kp_{ik}^{(m)}p_{kj}^{(n)},\qquad P^{(m+n)}=P^{(m)}P^{(n)}.$$

#### Common Formulas

1. **Stationary-distribution equations:**

   $$\pi_j=\sum_i\pi_ip_{ij}\quad(\forall j),\qquad\sum_j\pi_j=1,$$

   equivalently $\pi P=\pi$, $\pi\mathbf1=1$.

2. For two-state transition matrix

   $$P=\begin{pmatrix}1-a&a\\b&1-b\end{pmatrix},\qquad a,b\in(0,1],$$

   stationary distribution is

   $$\pi=\left(\frac b{a+b},\frac a{a+b}\right).$$

3. **Period:**

   $$d(i)=\gcd\{n\geq1:p_{ii}^{(n)}>0\}.$$

   If all states have the same period $d$, the chain has period $d$.

4. **Condition for a limiting distribution:** an irreducible, aperiodic (ergodic), positive recurrent Markov chain has a unique limiting distribution,

   $$\lim_{n\to\infty}p_{ij}^{(n)}=\pi_j,$$

   independent of $i$, and it equals the stationary distribution.

#### Solution Procedure: Stationary Distribution

1. Write $\pi P=\pi$, i.e. $\pi_j=\sum_i\pi_ip_{ij}$ for every $j$.
2. Add normalization $\sum_i\pi_i=1$ and remove one redundant equation.
3. Solve the linear system; for finite state spaces solve directly, for birth--death processes use detailed balance.

#### Solution Procedure: Existence of a Limiting Distribution

1. Check irreducibility: all states communicate.
2. Check periodicity: a self-loop at any state implies aperiodicity.
3. If irreducible and aperiodic, the limiting distribution exists and equals stationary distribution.
4. If period $d>1$, then $P^n$ does not converge and the limiting distribution does not exist.

#### Corresponding Exercises

- **idx 0:** two-state stationary distribution: solve $\pi P=\pi$, obtaining $\pi=(3/7,4/7)$.
- **idx 9:** period and stationary distribution for a three-state matrix: a cyclic permutation matrix has period $d=3$.
- **idx 13:** existence and calculation of limiting distribution: verify irreducibility and aperiodicity, then obtain $(1/3,1/3,1/3)$.
- **idx 15:** prove Chapman--Kolmogorov: total probability + Markov property + time homogeneity.

---

### Module 2: Markov-Chain Absorption Probabilities

#### Core Concepts

- **Absorbing state:** $p_{ii}=1$, so after entry it is never left.
- **Absorbing Markov chain:** state space splits into transient set $T$ and absorbing-state set $A$.
- **Absorption probability:** $a_i=P(\text{eventual absorption by a specified absorbing set}\mid X_0=i)$.
- **Fundamental matrix:** $N=(I-Q)^{-1}$, where $Q$ is the transition submatrix among transient states only. $N_{ij}$ is expected number of visits to state $j$ starting from state $i$.

#### Common Formulas

1. For transient $i$, probability of absorption in target set $A$ satisfies

   $$a_i=\sum_{j\in A}p_{ij}+\sum_{k\in T}p_{ik}a_k.$$

   Boundary values are $a_i=1$ for a target absorbing state and $a_i=0$ for every nontarget absorbing state.

2. With $\mathbf a=(a_i)_{i\in T}$,

   $$\mathbf a=\mathbf r+Q\mathbf a=(I-Q)^{-1}\mathbf r=N\mathbf r,$$

   where $\mathbf r_i=\sum_{j\in A_{\text{target}}}p_{ij}$.

#### Solution Procedure

1. Reorder states so absorbing states come first.
2. For each transient $i$, write $a_i=\sum_{j\in A}p_{ij}\cdot(\text{boundary value})+\sum_{k\in T}p_{ik}a_k$.
3. Set target absorbing-state probability to $1$ and all other absorbing-state probabilities to $0$.
4. Solve the system for all $a_i$.

#### Corresponding Exercise

- **idx 3:** absorption probability in a four-state Markov chain: solve the system to obtain probability $2/5$ of absorption in state $3$ when starting at state $2$.

---

### Module 3: Poisson Processes

#### Core Concepts

- A homogeneous **Poisson process** $\{N(t),t\geq0\}$ satisfies: (1) $N(0)=0$; (2) independent increments; (3) the number of events in every interval of length $s$ follows a Poisson distribution with parameter $\lambda s$:

  $$P(N(t+s)-N(t)=k)=e^{-\lambda s}\frac{(\lambda s)^k}{k!}.$$

- **Interarrival times:** $T_i$, the time between events $i-1$ and $i$, are i.i.d. $\operatorname{Exp}(\lambda)$.
- **Waiting time for the $n$th event:** $W_n=T_1+\cdots+T_n\sim\operatorname{Gamma}(n,\lambda)$.
- **Nonhomogeneous Poisson process:** time-dependent intensity $\lambda(t)$ and mean function $\Lambda(t)=\int_0^t\lambda(s)\,ds$. Then $N(t)\sim\operatorname{Poisson}(\Lambda(t))$.
- **Superposition:** independent $N_1(t)\sim\operatorname{PP}(\lambda_1)$ and $N_2(t)\sim\operatorname{PP}(\lambda_2)$ satisfy $N_1(t)+N_2(t)\sim\operatorname{PP}(\lambda_1+\lambda_2)$.

#### Common Formulas

1. **Poisson PMF:**

   $$P(N(t)=k)=e^{-\lambda t}\frac{(\lambda t)^k}{k!},\qquad k=0,1,2,\ldots.$$

2. **Expectation and variance:**

   $$E[N(t)]=\lambda t,\qquad\operatorname{Var}(N(t))=\lambda t.$$

3. **Nonhomogeneous distribution:**

   $$N(t)\sim\operatorname{Poisson}(\Lambda(t)),\qquad\Lambda(t)=\int_0^t\lambda(s)\,ds.$$

4. **Nonhomogeneous increment:**

   $$N(t)-N(s)\sim\operatorname{Poisson}(\Lambda(t)-\Lambda(s)),\qquad\Lambda(t)-\Lambda(s)=\int_s^t\lambda(u)\,du.$$

5. **Waiting-time density:**

   $$f_{W_n}(t)=\frac{\lambda^nt^{n-1}e^{-\lambda t}}{(n-1)!},\qquad t>0.$$

6. **Superposition:** $N_1(t)+N_2(t)\sim\operatorname{PP}(\lambda_1+\lambda_2)$.

#### Solution Procedures

**Homogeneous Poisson probability:** determine $\lambda$ and interval length $t$, choose required $k$, then substitute $e^{-\lambda t}(\lambda t)^k/k!$.

**Nonhomogeneous Poisson process:** compute $\Lambda(t)=\int_0^t\lambda(s)\,ds$, then reduce to a standard Poisson probability using $N(t)\sim\operatorname{Poisson}(\Lambda(t))$.

**Waiting-time distribution:** use $W_n=T_1+\cdots+T_n$ with i.i.d. $T_i\sim\operatorname{Exp}(\lambda)$. The characteristic function of their sum is $(\lambda/(\lambda-it))^n$, identifying $\operatorname{Gamma}(n,\lambda)$.

#### Corresponding Exercises

- **idx 2:** $P(N(1)=3)=\frac43e^{-2}$ and $P(N(2)\geq1)=1-e^{-4}$.
- **idx 10:** for $\lambda(t)=2t$, $E[N(3)]=9$ and $P(N(2)-N(1)=0)=e^{-3}$.
- **idx 11:** independent-process superposition: $N_1+N_2\sim\operatorname{Poisson}(5)$.
- **idx 17:** prove waiting-time distribution: $W_n\sim\operatorname{Gamma}(n,\lambda)$.

---

### Module 4: Compound Poisson Processes

#### Core Concepts

A **compound Poisson process** is

$$S(t)=\sum_{k=1}^{N(t)}X_k,$$

where $\{N(t)\}$ is a Poisson process of rate $\lambda$, $\{X_k\}$ are i.i.d. and independent of $N(t)$, and $X_k$ is reward/payment of event $k$. Applications include total insurance claims, total store sales, and jump components of stock prices.

#### Common Formulas

$$E[S(t)]=E[N(t)]E[X]=\lambda tE[X],$$

$$\operatorname{Var}(S(t))=E[N(t)]E[X^2]=\lambda tE[X^2],$$

$$\operatorname{Var}(S(t))=\lambda t\left(\operatorname{Var}(X)+(E[X])^2\right).$$

#### Solution Procedure

1. Identify Poisson rate $\lambda$ and one-event reward distribution $X$.
2. Compute $E[X]$ and $E[X^2]=\operatorname{Var}(X)+(E[X])^2$.
3. Substitute into $E[S(t)]=\lambda tE[X]$.
4. Substitute into $\operatorname{Var}(S(t))=\lambda tE[X^2]$.
5. If covariance is needed,

   $$\operatorname{Cov}(S(s),S(t))=\lambda\min(s,t)E[X^2].$$

#### Corresponding Exercise

- **idx 6:** compound-Poisson expectation and variance: $E[S(4)]=400$, $\operatorname{Var}(S(4))=8320$.

---

### Module 5: Birth--Death Processes and Queueing Theory

#### Core Concepts

- A **continuous-time Markov chain** has exponentially distributed transitions and is described by transition-rate (generator) matrix $Q$.
- A **birth--death process** is a CTMC whose state changes are only adjacent, $i\to i+1$ or $i\to i-1$. Birth rate $\lambda_i$ is rate from $i$ to $i+1$; death rate $\mu_i$ is rate from $i$ to $i-1$, with $\mu_0=0$.
- A stationary distribution satisfies $\pi Q=0$ and $\sum\pi_i=1$.
- **Detailed balance:** $\pi_i\lambda_i=\pi_{i+1}\mu_{i+1}$, which necessarily holds for birth--death processes.
- In an **M/M/1 queue**, arrivals are $\operatorname{PP}(\lambda)$, service times are $\operatorname{Exp}(\mu)$, and there is one server. Traffic intensity is $\rho=\lambda/\mu$.
- If $\rho<1$, stationary queue length is $\pi_n=(1-\rho)\rho^n$, $n=0,1,2,\ldots$.

#### Common Formulas

1. Stationary birth--death distribution from detailed balance:

   $$\pi_n=\pi_0\prod_{k=0}^{n-1}\frac{\lambda_k}{\mu_{k+1}},\qquad\pi_0=\left(1+\sum_{n=1}^\infty\prod_{k=0}^{n-1}\frac{\lambda_k}{\mu_{k+1}}\right)^{-1}.$$

2. M/M/1 quantities:

   $$\pi_n=(1-\rho)\rho^n,\quad\rho=\lambda/\mu<1,\quad L=E[N]=\frac\rho{1-\rho},\quad W=L/\lambda=\frac1{\mu-\lambda}.$$

3. For finite-state birth--death processes, recursively use $\pi_{i+1}=(\lambda_i/\mu_{i+1})\pi_i$, then normalize.

#### Solution Procedures

**Stationary birth--death distribution:** list all $\lambda_i,\mu_i$; use $\pi_i\lambda_i=\pi_{i+1}\mu_{i+1}$ to find each $\pi_i$ in terms of $\pi_0$; normalize $\sum_i\pi_i=1$.

**M/M/1 queue:** check $\rho=\lambda/\mu<1$. Detailed balance gives $\lambda\pi_n=\mu\pi_{n+1}$ and $\pi_n=\rho^n\pi_0$. Normalize $\pi_0\sum_{n=0}^\infty\rho^n=\pi_0/(1-\rho)=1$, giving $\pi_0=1-\rho$.

#### Corresponding Exercises

- **idx 4:** three-state birth--death stationary distribution: detailed-balance recursion gives $\pi=(8/23,12/23,3/23)$.
- **idx 16:** prove M/M/1 stationary distribution $\pi_n=(1-\rho)\rho^n$ using detailed balance and normalization.

---

### Module 6: Brownian Motion

#### Core Concepts

- Standard **Brownian motion** (Wiener process) $\{B(t),t\geq0\}$ satisfies: $B(0)=0$; independent increments; $B(t)-B(s)\sim N(0,t-s)$ for $0\leq s<t$; and almost surely continuous sample paths.
- Covariance is $\operatorname{Cov}(B(s),B(t))=\min(s,t)$ for $s,t\geq0$.
- $B(t)$ is a martingale for its natural filtration: $E[B(t)\mid\mathcal F_s]=B(s)$ for $s<t$.
- Hitting time is $T_a=\inf\{t\geq0:B(t)=a\}$ for $a>0$.
- Two-boundary hitting time is $T=\min(T_a,T_{-b})$, $a,b>0$.
- **Reflection principle:** after first hitting $a$, reflect a path about line $y=a$; the reflected path remains standard Brownian motion.

#### Common Formulas

$$\operatorname{Cov}(B(s),B(t))=\min(s,t),\qquad\operatorname{Var}(B(t))=t.$$

$$P(T_a\leq t)=2P(B(t)\geq a)=2\left(1-\Phi\left(\frac a{\sqrt t}\right)\right).$$

$$f_{T_a}(t)=\frac a{\sqrt{2\pi t^3}}e^{-a^2/(2t)},\qquad t>0.$$

$$P(T_a<T_{-b})=\frac b{a+b},\qquad E[\min(T_a,T_{-b})]=ab.$$

The increment $B(t)-B(s)$ is independent of $B(u)$ for every $u\leq s<t$.

#### Solution Procedures

For covariance, expand linear combinations using $\operatorname{Cov}(B(s),B(t))=\min(s,t)$, then simplify variances using independent increments.

For hitting times: if $a=b$, $P(T_a<T_{-a})=1/2$ and $E[T]=a^2$; otherwise use $b/(a+b)$ and $ab$.

To prove martingale property, decompose $B(t)=[B(t)-B(s)]+B(s)$, take conditional expectation given $\mathcal F_s$, and use independence and zero mean of the increment.

#### Corresponding Exercises

- **idx 7:** $\operatorname{Cov}(B(1)+B(2),B(3))=3$ and $\operatorname{Var}(B(2)-B(1))=1$.
- **idx 12:** $P(T_1<T_{-1})=1/2$, $E[T]=1$.
- **idx 14:** prove Brownian motion is a martingale via independent zero-mean increments.
- **idx 19:** prove reflection principle via equal distribution of reflected paths and probability decomposition.

---

### Module 7: Random Walks

#### Core Concepts and Formulas

For simple symmetric random walk, $S_0=0$, $S_n=\sum_{k=1}^nX_k$, with i.i.d. $P(X_k=1)=P(X_k=-1)=1/2$. If $k$ of $n$ steps are upward,

$$S_n=k-(n-k)=2k-n.$$

Thus

$$P(S_n=m)=\binom n{(n+m)/2}\left(\frac12\right)^n,$$

nonzero if and only if $n+m$ is even and $|m|\leq n$. Also $E[S_n]=0$ and $\operatorname{Var}(S_n)=n$.

#### Solution Procedure

From $S_n=m$, solve $k=(n+m)/2$, check that $k$ is an integer in $[0,n]$, then compute $\binom nk(1/2)^n$.

#### Corresponding Exercise

- **idx 1:** $P(S_6=0)=5/16$ and $P(S_6=2)=15/64$.

---

### Module 8: Renewal Processes

#### Core Concepts and Formulas

For i.i.d. nonnegative interarrival times $\{X_1,X_2,\ldots\}$, let $S_0=0$, $S_n=\sum_{i=1}^nX_i$, and $N(t)=\max\{n:S_n\leq t\}$. Renewal function is $m(t)=E[N(t)]$. The elementary renewal theorem is

$$\lim_{t\to\infty}\frac{m(t)}t=\frac1\mu,\qquad\mu=E[X_1].$$

So long-run average renewal rate is $1/\mu$, and for sufficiently large $t$,

$$E[N(t)]\approx\frac t\mu.$$

#### Solution Procedure

Identify interarrival distribution and calculate $\mu=E[X_1]$; the long-run average rate is $1/\mu$; use elementary renewal theorem for $E[N(t)]\approx t/\mu$.

#### Corresponding Exercise

- **idx 8:** bulb-replacement renewal process with lifetime $U(0,2)$ has mean one year and average replacement rate $1$ per year.

---

### Module 9: Exponential Distributions and Order Statistics

#### Core Concepts and Formulas

If $T\sim\operatorname{Exp}(\lambda)$, then density is $f(t)=\lambda e^{-\lambda t}$ for $t>0$, $E[T]=1/\lambda$, $\operatorname{Var}(T)=1/\lambda^2$, and memorylessness is

$$P(T>s+t\mid T>s)=P(T>t)=e^{-\lambda t}.$$

For independent $X_i\sim\operatorname{Exp}(\lambda_i)$,

$$\min(X_1,\ldots,X_n)\sim\operatorname{Exp}\left(\sum_{i=1}^n\lambda_i\right),$$

$$E[T]=\frac1{\sum_i\lambda_i},\qquad P(T>t)=e^{-(\sum_i\lambda_i)t}.$$

If all $\lambda_i=\lambda$, the minimum is $\operatorname{Exp}(n\lambda)$.

#### Solution Procedure

Check independence and exponential distributions, apply the minimum formula, then calculate expectation and survival probability.

#### Corresponding Exercise

- **idx 5:** $E[T]=1/3$ year and $P(T>1)=e^{-3}$.

---

### Module 10: Martingales and Stopping Times

#### Core Concepts

- $\{M_n,n\geq0\}$ is a **martingale** for filtration $\{\mathcal F_n\}$ if $E|M_n|<\infty$ and $E[M_{n+1}\mid\mathcal F_n]=M_n$ a.s.
- A **stopping time** $T$ takes nonnegative integer values and satisfies $\{T=n\}\in\mathcal F_n$ for all $n$.
- **Doob's bounded stopping theorem:** if $M_n$ is a martingale and $T\leq K$ a.s. for some constant $K$, then $E[M_T]=E[M_0]$.
- The stopped process $M_{T\wedge n}$ is still a martingale.

#### Common Formulas

$$M_{T\wedge n}=M_0+\sum_{k=1}^n(M_k-M_{k-1})\mathbf1_{\{T\geq k\}}.$$

The key lemma is

$$\mathbf1_{\{T\geq k\}}=1-\mathbf1_{\{T\leq k-1\}}\in\mathcal F_{k-1}.$$

Hence

$$E[(M_k-M_{k-1})\mathbf1_{\{T\geq k\}}\mid\mathcal F_{k-1}]=\mathbf1_{\{T\geq k\}}E[M_k-M_{k-1}\mid\mathcal F_{k-1}]=0.$$

#### Proof Procedure: Doob's Bounded Stopping Theorem

1. Write the martingale-difference representation of $M_{T\wedge n}$.
2. Verify $\mathbf1_{\{T\geq k\}}$ is $\mathcal F_{k-1}$-measurable.
3. Use martingale differences to prove $M_{T\wedge n}$ is a martingale and $E[M_{T\wedge n}]=E[M_0]$.
4. Since $T\leq K$, set $n=K$ to get $E[M_{T\wedge K}]=E[M_T]=E[M_0]$.

#### Corresponding Exercises

- **idx 18:** prove Doob's bounded stopping theorem using martingale differences and bounded stopping.
- **idx 19:** prove Brownian reflection principle using reflection invariance and probability decomposition.

---

## General Problem-Solving Methodology

### Problem Identification

| Feature | Corresponding module |
|---|---|
| transition matrix, stationary distribution, or $\pi P=\pi$ | Module 1: DTMC fundamentals |
| $p_{ij}^{(n)}$, C--K, Chapman--Kolmogorov | Module 1: C--K equation |
| period, limiting distribution, or whether $P^n$ converges | Module 1: periodicity and limits |
| absorbing state, absorption probability, absorbing chain | Module 2 |
| Poisson process, $N(t)$, or $e^{-\lambda t}$ | Module 3 |
| nonhomogeneous Poisson, $\lambda(t)$, intensity | Module 3 |
| $N_1+N_2$, superposition, independent Poisson sum | Module 3 |
| waiting time, $W_n$, Erlang, Gamma | Module 3 |
| compound Poisson, $S(t)$, total sales | Module 4 |
| birth--death, birth/death rates, detailed balance | Module 5 |
| M/M/1, queue, $\rho$, traffic intensity | Module 5 |
| Brownian motion, $B(t)$, Wiener process | Module 6 |
| covariance, $\min(s,t)$, independent increments | Module 6 |
| hitting time, $T_a$, reflection principle | Module 6 |
| martingale or $E[M_T]$ | Modules 6 and 10 |
| random walk, $S_n$, steps, binomial distribution | Module 7 |
| renewal process, renewal rate, elementary renewal theorem | Module 8 |
| exponential distribution, $\min$, order statistics, memorylessness | Module 9 |
| Doob, stopping time, bounded stopping, optional stopping | Module 10 |

### Method Selection

| Problem type | First-choice method | Alternative |
|---|---|---|
| Stationary distribution | solve $\pi P=\pi$ | detailed balance for birth--death |
| Absorption probability | absorption equations + linear solve | $N=(I-Q)^{-1}$ |
| Poisson probability | direct PMF | N/A |
| Nonhomogeneous Poisson | first calculate $\Lambda(t)$ | N/A |
| Compound-Poisson mean/variance | Wald formulas $E[S]=E[N]E[X]$ | conditional expectation |
| Brownian covariance | $\operatorname{Cov}(B(s),B(t))=\min(s,t)$ | expand with independent increments |
| Brownian hitting time | reflection-principle formula / martingale stopping | integrate density |
| Random-walk probability | binomial reduction | recurrence/generating function |
| Renewal rate | $1/\mu$ | renewal equation |
| Minimum of independent exponentials | $\operatorname{Exp}(\sum\lambda_i)$ | multiply survival functions |
| Period | gcd of return-step set | self-loop gives $d=1$ |
| Limiting-distribution existence | irreducible + aperiodic + finite state | ergodicity theorem |
| Martingale proof | direct conditional expectation | martingale transform/function martingale |
| Reflection-principle proof | reflected path law + probability decomposition | Markov/strong Markov property |

### Result Validation

- Check $\pi P=\pi$ and $\sum_i\pi_i=1$ for stationary distributions.
- Check $\sum_{k=0}^\infty P(N(t)=k)=1$ for Poisson probabilities.
- A covariance matrix must be positive semidefinite.
- Absorption boundary conditions must hold and transient-state probabilities lie in $[0,1]$.
- Check detailed balance $\pi_i\lambda_i=\pi_{i+1}\mu_{i+1}$.
- Check $\lim_{t\to\infty}P(T_a\leq t)=1$.
- Compound-Poisson variance must be nonnegative and $E[X^2]\geq(E[X])^2$.
- Independently use SymPy for computations: matrix operations, symbolic integration, and probability calculations.

---

## Competition Extension: Cover Time of Random Walk on a Complete Graph

### Core Concepts

Consider simple symmetric random walk on complete graph $K_n$: from a current vertex, each step jumps uniformly to any of the other $n-1$ vertices.

The **cover time** $C$ is the minimum number of steps from any starting vertex until all $n$ vertices have been visited. It generalizes coupon collection. Coupon draws are i.i.d.; in a complete-graph walk, distribution depends on current position, but symmetry gives a closely analogous expected-time structure.

### Common Formulas

1. **Cover-time decomposition:**

   $$C=\sum_{k=1}^{n-1}G_k,$$

   where $G_k$ is waiting time from having visited $k$ distinct vertices to first visiting a $(k+1)$st vertex. By complete-graph symmetry, these $n-1$ waiting times are **mutually independent**.

2. When $k$ vertices have been visited, new-vertex discovery probability is

   $$p_k=\frac{n-k}{n-1}.$$

   Thus $G_k\sim\operatorname{Geometric}(p_k)$ on $1,2,3,\ldots$, with

   $$E[G_k]=\frac1{p_k}=\frac{n-1}{n-k},\qquad\operatorname{Var}(G_k)=\frac{1-p_k}{p_k^2}=\frac{(n-1)(k-1)}{(n-k)^2}.$$

3. **Expected cover time:**

   $$E[C]=\sum_{k=1}^{n-1}\frac{n-1}{n-k}=(n-1)\sum_{j=1}^{n-1}\frac1j=(n-1)H_{n-1},$$

   where $H_{n-1}=1+1/2+\cdots+1/(n-1)$.

   **Starting-point convention (must check the statement):** this formula counts **transition steps** after the initial location, which already visits one vertex. If the problem labels the initial time as $t=1$ (the “first step,” rather than $t=0$), then total time is

   $$E[T]=1+(n-1)H_{n-1}.$$

   Thus time numbering from $1$ adds $1$ to the answer. Always distinguish transition-step count from time-index labeling.

4. Since $H_{n-1}=\ln n+\gamma+O(1/n)$ with Euler--Mascheroni constant $\gamma\approx0.5772$,

   $$E[C]\sim n\ln n\qquad(n\to\infty).$$

5. By independence,

   $$\operatorname{Var}(C)=\sum_{k=1}^{n-1}\operatorname{Var}(G_k)=(n-1)^2\sum_{j=1}^{n-1}\frac1{j^2}-(n-1)H_{n-1}.$$

6. **Comparison with coupon collection:**

   | Item | Coupon collection | Complete-graph cover |
   |---|---|---|
   | New-vertex probability | $(n-k)/n$ | $(n-k)/(n-1)$ |
   | Expected completion time | $nH_n$ | $(n-1)H_{n-1}$ |
   | High-probability bound | $n\ln n+O(n)$ | $n\ln n+O(n)$ |

### Solution Procedure

1. Use symmetry to decompose cover time into a sum of $n-1$ independent geometric variables.
2. Write discovery probability $p_k=(n-k)/(n-1)$ at stage $k$.
3. Sum $E[G_k]=1/p_k$ to obtain expected cover time.
4. Use harmonic-number asymptotics for asymptotic estimates.
5. For probability bounds, combine Chernoff bounds with independence of the geometric variables.

### Common Pitfalls

- Cover time concerns visiting every vertex; return time is the interval between consecutive visits to a specified vertex. Their orders differ: $O(n\ln n)$ versus $O(n)$.
- $G_k$ is discrete geometric, not continuous exponential. Their means $1/p$ and $1/\lambda$ look similar but must not be mixed.
- Do not apply the complete-graph formula to a general graph. General-graph cover times depend closely on effective resistance; Matthews bounds give $O(|E|\cdot R\cdot\log n)$, not a simple harmonic formula.
- Independence of $G_k$ relies on complete-graph symmetry and generally fails on noncomplete graphs.
- Check the off-by-one starting-index convention: $E[C]=(n-1)H_{n-1}$ counts transition steps, while time labeled from $t=1$ requires $1+(n-1)H_{n-1}$.

---

## Competition Extension: Fibonacci and Lucas Recurrences in Random Walks

### Core Concepts

Fibonacci numbers $\{F_n\}$ and Lucas numbers $\{L_n\}$ satisfy the same second-order recurrence:

$$F_{n+2}=F_{n+1}+F_n,\quad F_0=0,\ F_1=1,$$

$$L_{n+2}=L_{n+1}+L_n,\quad L_0=2,\ L_1=1.$$

They arise frequently in random walks, particularly gambler's ruin and spectral analysis of transition matrices. A one-dimensional random walk with absorbing walls has transition-matrix eigenvalues $\cos(k\pi/(N+1))$, related to Chebyshev polynomials; Fibonacci numbers are values of these polynomials at special parameters.

### Common Formulas

1. **Binet formulas:**

   $$F_n=\frac{\alpha^n-\beta^n}{\alpha-\beta},\qquad L_n=\alpha^n+\beta^n,$$

   where $\alpha=(1+\sqrt5)/2$ (golden ratio) and $\beta=(1-\sqrt5)/2$. Since $|\beta|<1$, for large $n$, $F_n\approx\alpha^n/\sqrt5$.

2. **Cassini identity:**

   $$F_{n-1}F_{n+1}-F_n^2=(-1)^n.$$

3. **Matrix-power representation:**

   $$\begin{pmatrix}F_{n+1}&F_n\\F_n&F_{n-1}\end{pmatrix}=\begin{pmatrix}1&1\\1&0\end{pmatrix}^n.$$

   This is useful for powers of two-state Markov-chain transition matrices.

4. **Gambler's ruin:** for a biased random walk with $p\ne1/2$, states $\{0,1,\ldots,N\}$, and absorbing walls $0,N$, probability of eventual absorption at $N$ starting from $k$ is

   $$P_k=\frac{1-(q/p)^k}{1-(q/p)^N}=\frac{\alpha^{2k-N}(\alpha^k-\beta^k)/(\alpha-\beta)}{\alpha^{2k-N}(\alpha^N-\beta^N)/(\alpha-\beta)}$$

   when $p/q=\alpha$, where it degenerates to a Fibonacci ratio.

5. **Parity pattern of Lucas numbers:**

   $$L_n\equiv\begin{cases}2\pmod{?},&3\mid n,\\1\pmod2,&3\nmid n,\end{cases}$$

   usable for parity of return-step counts in random walks.

6. **Generating functions:**

   $$\sum_{n=0}^\infty F_nx^n=\frac{x}{1-x-x^2},\qquad\sum_{n=0}^\infty L_nx^n=\frac{2-x}{1-x-x^2}.$$

   These rational generating functions arise often in probability generating functions of random-walk hitting times.

### Examination Techniques

- For gambler's ruin with $p\ne1/2$, use Binet form to write $F_n$ as a linear combination of $\alpha^n,\beta^n$ and cancel common factors.
- To verify Fibonacci identities, prefer the matrix-power representation, which yields several identities at once.
- $L_n=F_{n-1}+F_{n+1}$, so Lucas numbers can express quantities related to returning to the origin within two steps in symmetric random walks.
- When asked for a closed form of a recurrence, first check whether its characteristic equation is isomorphic to $x^2-x-1=0$; if so, use Fibonacci/Lucas closed forms directly.

### Frequent Examination Pitfalls

- Fibonacci and Lucas share a recurrence but have different initial values: $F_0=0,F_1=1$ versus $L_0=2,L_1=1$.
- Do not omit or reverse $(-1)^n$ in Cassini's identity: it is $+1$ for even $n$ and $-1$ for odd $n$.
- $\beta=(1-\sqrt5)/2<0$; the sign of $\beta^n$ depends on parity. Its tending to $0$ does not permit ignoring its sign indiscriminately.
- Gambler's-ruin form depends on comparison of $p,q$: if $p>1/2$, drift is right and probability of absorption at upper wall $N$ tends to $1$ as $N\to\infty$; if $p<1/2$, it tends to $0$.

---

## References

- Companion verification prompt: `Stochastic Processes Verification Example.py`.
- Dataset source: `Stochastic Processes.md` (20 problems covering all core knowledge points).
- Recommended texts: *Stochastic Processes* (Sheldon Ross), *Applied Stochastic Processes* (Lin Yuanlie), *Introduction to Stochastic Processes* (Lawler), and *Probability, Random Variables and Stochastic Processes* (Papoulis).
- Online tools: SymPy Live, SageMath.

## General Supplement: Cover Time for Random Walks on Finite Graphs

1. Treat size of the visited set as the stage state. Waiting times before first discovering a new state are often geometric, and total time can be summed by stages.
2. At every stage, compute probability of hitting a new state from the actual transition kernel. Whether self-loops are allowed and whether initial state is counted in the visited set changes denominators or constant terms.
3. After summing expectations by linearity, check the first and last stages using small state spaces or boundary cases, to avoid omitting the first visit or the final new state.

---

## SymPy Verification Techniques

### Transition Matrices and Stationary Distributions

```python
from sympy import Matrix, symbols, solve, Rational

# Example: idx 0 — stationary distribution of a two-state Markov chain
P = Matrix([
    [Rational(1, 3), Rational(2, 3)],
    [Rational(1, 2), Rational(1, 2)]
])
pi1, pi2 = symbols('pi1 pi2')
eqs = [
    pi1 * P[0, 0] + pi2 * P[1, 0] - pi1,
    pi1 * P[0, 1] + pi2 * P[1, 1] - pi2,
    pi1 + pi2 - 1,
]
sol = solve(eqs, (pi1, pi2))  # pi1=3/7, pi2=4/7

# Example: idx 9 — a periodic matrix
P3 = Matrix([[0, 1, 0], [0, 0, 1], [1, 0, 0]])
P3_pow3 = P3**3  # identity matrix: period 3
pi = symbols('pi0:3')
eqs3 = [sum(pi[j] * P3[j, i] for j in range(3)) - pi[i] for i in range(3)]
eqs3.append(sum(pi) - 1)
sol3 = solve(eqs3, pi)
```

### Absorption-Probability Equations

```python
from sympy import Matrix, symbols, solve, Rational

# idx 3: states 1 (absorbing, nontarget), 2 (transient),
# 3 (absorbing, target), 4 (transient)
P_absorb = Matrix([
    [1, 0, 0, 0],
    [Rational(1, 3), 0, Rational(1, 3), Rational(1, 3)],
    [0, 0, 1, 0],
    [Rational(1, 4), Rational(1, 4), 0, Rational(1, 2)],
])
a2, a4 = symbols('a2 a4')
# a1=0, a3=1
eqs = [
    a2 - (Rational(1, 3) * 0 + Rational(1, 3) * 1 + Rational(1, 3) * a4),
    a4 - (Rational(1, 4) * 0 + Rational(1, 4) * a2 + Rational(1, 2) * a4),
]
sol_absorb = solve(eqs, (a2, a4))  # a2=2/5, a4=1/5
```

### Poisson and Compound Poisson Processes

```python
from sympy import exp, factorial, symbols, integrate

lam, t, k = symbols('lam t k', positive=True, integer=True)
# idx 2: Poisson PMF
p = exp(-2) * 2**3 / factorial(3)  # 4*exp(-2)/3

# idx 10: lambda(t)=2t
lam_t = 2 * t
Lambda_3 = integrate(lam_t, (t, 0, 3))       # 9 = E[N(3)]
Lambda_interval = integrate(lam_t, (t, 1, 2)) # 3
P_no_fault = exp(-Lambda_interval)            # e**(-3)

# idx 6: compound Poisson process
rate, time, E_X, Var_X = 5, 4, 20, 16
E_X2 = Var_X + E_X**2  # 416
E_S = rate * time * E_X  # 400
Var_S = rate * time * E_X2  # 8320
```

### Brownian Covariance and Exponential Order Statistics

```python
def cov_B(s, t):
    """Covariance of Brownian motion."""
    return min(s, t)

# idx 7
result_cov = cov_B(1, 3) + cov_B(2, 3)  # 3
result_var = 2 + 1 - 2 * cov_B(1, 2)    # 1

from sympy import exp
# idx 5: three independent Exp(1) variables
lam_list = [1, 1, 1]
lam_min = sum(lam_list)  # 3
E_T = 1 / lam_min        # 1/3
P_T_gt_1 = exp(-lam_min) # e**(-3)
```

## Key Formula Quick Reference

| Topic | Exact formula / condition |
|---|---|
| Stationary distribution | $\pi=\pi P$, $\sum_i\pi_i=1$ |
| Chapman--Kolmogorov | $p_{ij}^{(m+n)}=\sum_kp_{ik}^{(m)}p_{kj}^{(n)}$ |
| Two-state stationary distribution | $(p_{21}/(p_{12}+p_{21}),p_{12}/(p_{12}+p_{21}))$ |
| Limiting distribution | irreducible + aperiodic + positive recurrent $\Rightarrow\lim P^n$ exists |
| Period | $d(i)=\gcd\{n\geq1:p_{ii}^{(n)}>0\}$ |
| Absorption equations | $a_i=\sum_{j\in A}p_{ij}+\sum_{k\in T}p_{ik}a_k$ |
| Poisson PMF | $e^{-\lambda t}(\lambda t)^k/k!$, $k=0,1,2,\ldots$ |
| Nonhomogeneous mean | $\Lambda(t)=\int_0^t\lambda(s)\,ds$ |
| Poisson waiting time | $W_n\sim\operatorname{Gamma}(n,\lambda)$, $f(t)=\lambda^nt^{n-1}e^{-\lambda t}/(n-1)!$, $t>0$ |
| Compound Poisson | $E[S(t)]=\lambda tE[X]$, $\operatorname{Var}(S(t))=\lambda tE[X^2]$ |
| Brownian covariance | $\operatorname{Cov}(B(s),B(t))=\min(s,t)$ |
| Brownian hitting | $P(T_a\leq t)=2(1-\Phi(a/\sqrt t))$, $a,t>0$ |
| Two-boundary Brownian | $P(T_a<T_{-b})=b/(a+b)$, $E[\min(T_a,T_{-b})]=ab$ |
| Detailed balance | $\pi_i\lambda_i=\pi_{i+1}\mu_{i+1}$ |
| M/M/1 | $\pi_n=(1-\rho)\rho^n$, $\rho=\lambda/\mu<1$, $L=\rho/(1-\rho)$ |
| Random walk | $P(S_n=m)=\binom n{(n+m)/2}2^{-n}$ if $n+m$ even and $|m|\leq n$ |
| Renewal theorem | $\lim_{t\to\infty}E[N(t)]/t=1/\mu$, $\mu=E[X_1]<\infty$ |
| Min exponentials | $\min\operatorname{Exp}(\lambda_i)\sim\operatorname{Exp}(\sum\lambda_i)$ |
| Doob bounded stopping | $E[M_T]=E[M_0]$ for bounded $T$ and martingale $M_n$ |

## Standard Computational and Proof Templates

- **Stationary distribution:** solve $\pi P=\pi$ together with $\sum\pi_i=1$; e.g. $P=\begin{pmatrix}1/3&2/3\\1/2&1/2\end{pmatrix}$ yields $(3/7,4/7)$.
- **Random walk:** $n=6,m=0\Rightarrow k=3$, so $\binom63 2^{-6}=5/16$.
- **Poisson:** $\lambda=2,t=1,k=3\Rightarrow(4/3)e^{-2}$.
- **Birth--death:** use $\pi_{i+1}=(\lambda_i/\mu_{i+1})\pi_i$, then normalize; for $\lambda_0=3,\mu_1=2,\lambda_1=1,\mu_2=4$, $\pi_1=(3/2)\pi_0$, $\pi_2=(3/8)\pi_0$, and $\pi_0=8/23$.
- **Brownian:** expand covariance with $\min$; $\operatorname{Cov}(B(1)+B(2),B(3))=1+2=3$.
- **C--K proof:** condition on state at intermediate time $m$, remove history by Markov property, then use time homogeneity.
- **Reflection proof:** split on $B(t)>a$ and $B(t)<a$ after hitting $a$; reflection $\widetilde B(s)=2a-B(s)$ makes both probabilities $P(B(t)>a)$.

---

## Common Errors and Pitfalls

### Discrete-Time Markov Chains

1. Solving $\pi P=\pi$ without normalization: only $n-1$ of $n$ equations are independent, so $\sum_i\pi_i=1$ is required.
2. Calling a nonstationary distribution stationary: verify $\pi=\pi P$ in every component, not just by one or two ratios.
3. Confusing periodicity and aperiodicity: a self-loop $p_{ii}>0$ makes that state aperiodic; in an irreducible chain all states have the same period. Period $d>1$ means $P^n$ does not converge.
4. Confusing stationary and limiting distributions: a stationary distribution always exists for a finite irreducible chain; a limiting distribution exists only for an ergodic (irreducible aperiodic) chain and equals the stationary distribution.
5. Reversing C--K indices: use $p_{ij}^{(m+n)}=\sum_kp_{ik}^{(m)}p_{kj}^{(n)}$, not $\sum_kp_{ki}^{(m)}p_{jk}^{(n)}$.

### Absorption Probabilities

6. Incorrect boundary values: target absorbing states have probability $1$, nontarget absorbing states probability $0$.
7. Adding a normalization condition to absorption equations: the transient-state system is already closed. The probabilities of entering all absorbing states sum to $1$, which is only a check.
8. Confusing transition-matrix direction: rows mean starting states and columns mean destination states.

### Poisson and Compound Poisson Processes

9. Confusing rate and mean: $\lambda$ is a rate, while distribution parameter for $N(t)$ is $\lambda t$.
10. Using $\lambda(t)$ directly as a nonhomogeneous Poisson parameter: first integrate $\Lambda(t)=\int_0^t\lambda(s)\,ds$; $N(t)\sim\operatorname{Poisson}(\Lambda(t))$, not $\operatorname{Poisson}(\lambda(t)t)$.
11. Superposing nonindependent Poisson processes: rates add only under genuine independence.
12. Confusing $N(t)$ and $W_n$: the conversion is $P(N(t)\geq n)=P(W_n\leq t)$, with the inequality direction as shown.
13. Using $\operatorname{Var}(X)$ instead of $E[X^2]$ in compound-Poisson variance: $\operatorname{Var}(S(t))=\lambda tE[X^2]$, where $E[X^2]=\operatorname{Var}(X)+(E[X])^2$.
14. Forgetting $E[X]$ in compound-Poisson mean: $E[S(t)]=\lambda tE[X]$, not merely $E[N(t)]$.

### Brownian Motion

15. Misusing covariance: it is $\min(s,t)$, not $\max(s,t)$ and not $st$.
16. Forgetting increments are independent only on disjoint intervals: $B(3)-B(2)$ and $B(2)-B(1)$ are independent, but $B(3)-B(1)$ and $B(2)$ are not.
17. Wrong sign in hitting formula: $P(T_a\leq t)=2P(B(t)\geq a)=2(1-\Phi(a/\sqrt t))$; symmetry does not replace the required $P(B(t)\geq a)$ with the wrong event.
18. Forgetting product form of expected two-boundary hitting time: $E[\min(T_a,T_{-b})]=ab$, not $a+b$ or $(a+b)/2$, with $a,b>0$.

### Birth--Death and Queueing

19. Mismatching detailed-balance indices: $\pi_i\lambda_i=\pi_{i+1}\mu_{i+1}$, not versions with $\mu_i$ or $\lambda_{i+1}$.
20. Omitting $\rho<1$ for M/M/1: when $\rho\geq1$, the geometric series diverges and no stationary distribution exists.
21. Reversing birth--death recursion: $\pi_{i+1}=(\lambda_i/\mu_{i+1})\pi_i$; numerator is current-state birth rate, denominator target-state death rate.

### Random Walks, Renewal, and Stopping

22. Confusing steps and position: $S_n=2k-n$, hence $k=(n+S_n)/2$; $n+S_n$ even is required for nonzero probability.
23. Treating elementary renewal theorem as an exact finite-time equality: it is a limit $m(t)/t\to1/\mu$ and only an approximation for finite $t$.
24. Forgetting mean of $U(a,b)$ is $(a+b)/2$, not $b/2$ or $b-a$.
25. Applying Doob stopping without boundedness: the theorem requires $T\leq K$ a.s.; for unbounded $T$, the result can fail without extra conditions such as uniform integrability or $E[T]<\infty$.

## Quick Reference: Expected Cover Time of a Simple Random Walk on a Complete Graph

- **Retrieval terms:** complete graph, random walk, first visit, all vertices, time, expectation.
- **Applies when:** the process is a simple random walk on the complete graph with $N$ vertices, and the requested time is the number of transitions needed to visit every vertex.
- **Derivation:** When $k$ vertices have been visited, the probability that the next step reaches an unvisited vertex is

$$
\frac{N-k}{N-1},
$$

because the current vertex is already in the visited set and the next position is uniform among its $N-1$ neighbours. Therefore the waiting time $\tau_k$ for the next new vertex is geometric with

  $$\mathbb E\tau_k=\frac{N-1}{N-k}.$$

  Sum $T=\sum_{k=1}^{N-1}\tau_k$ and reindex with $j=N-k$ to derive the harmonic-sum expression for the current graph size. The endpoints provide a structural check: the first new vertex is reached in one step, while the last unseen vertex has the largest expected waiting time.

- **Pitfall:** do not use the ordinary coupon-collector denominator $N$; this walk cannot remain at its current vertex and has only $N-1$ equally likely neighbours.
