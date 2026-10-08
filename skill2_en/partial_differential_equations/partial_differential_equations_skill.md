# Partial Differential Equations Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: first- and second-order PDEs, characteristics, harmonic/heat/wave equations, boundary conditions, energy methods, Green functions, and formal adjoints.
- Does not take over: problems centered on finite differences, finite elements, or truncation error are routed to numerical analysis; abstract Hilbert-space operator-spectrum problems are routed to functional analysis.
- Verification contract: retain equation type, region, boundary/initial data, and regularity simultaneously; for a formal adjoint, explicitly state transposed coefficients and boundary terms.

> Based on 20 typical exercises (14 computational + 6 proof problems, difficulty ratio `2:6:2`), this handbook systematically organizes PDE problem-solving methodology.

---

## 1. First-Order Linear PDEs: Method of Characteristics

### 1.1 Core Concepts

The general form of a first-order linear PDE is $a(x,t)u_t+b(x,t)u_x+c(x,t)u=f(x,t)$.

The method of characteristics is the most fundamental technique for first-order PDEs. Its idea is to find **characteristic curves** along which the PDE reduces to an ODE.

### 1.2 Standard Form and Characteristic Equations

For the constant-coefficient first-order linear PDE $u_t+cu_x=0$, the characteristic equation is $dx/dt=c$, namely $x-ct=\text{const}$. Along a characteristic,
$$\frac{d}{dt}u(x(t),t)=u_t+cu_x=0,$$
so $u$ is constant. The solution is $u(x,t)=\phi(x-ct)$, with $\phi$ determined by the initial condition.

### 1.3 Variable-Coefficient Case

For $u_x+yu_y=0$, the characteristic equations are $dx/1=dy/y=du/0$. Thus $ye^{-x}=\text{const}$ and $u=\text{const}$ along characteristics.

### 1.4 Standard Solution Procedure

| Step | Operation | Example: $u_t+2u_x=0$ |
|------|------|------|
| 1 | Write the characteristic equation $dx/dt=c$ | $dx/dt=2$ |
| 2 | Solve the characteristic family | $x-2t=\xi$ |
| 3 | Reduce the PDE to an ODE along a characteristic | $du/dt=0$ |
| 4 | Use initial data to determine the arbitrary function | $u(x,0)=e^{-x^2}\Rightarrow u=e^{-(x-2t)^2}$ |

### 1.5 Common Pitfalls

- **Characteristic crossing**: when characteristics intersect (as in Burgers' equation), a classical solution breaks down and shocks must be considered.
- **Boundary-condition compatibility**: on a bounded domain, check whether characteristics enter from the boundary.
- **Variable coefficients**: characteristic equations can depend on spatial variables; solve the ODE carefully.

### 1.6 Problem-Solving Techniques

- In the constant-coefficient case, directly write $u(x,t)=\phi(x-ct)$ and substitute back into the initial condition.
- For variable coefficients, write characteristic equations symmetrically as $dx/a=dt/b=du/c$.
- Verify by substituting the solution back into the original PDE.

---

## 2. First-Order Quasilinear PDEs: Method of Characteristics

### 2.1 Core Concepts

A quasilinear PDE has the form of the inviscid Burgers equation $u_t+uu_x=0$. Its characteristic equation is $dx/dt=u$.

**Key distinction**: characteristics depend on the solution itself, so they are no longer fixed straight lines (except for special initial data), although the solution remains constant along each characteristic.

### 2.2 Solution Procedure

1. Write the characteristic system $dx/dt=u$, $du/dt=0$.
2. Since $u$ is constant along a characteristic, $x=u_0t+\xi$ (the characteristic is a straight line).
3. The initial condition gives $u(x,t)=\phi(x-ut)$.
4. If $u$ can be explicitly solved from the implicit solution, this gives an explicit solution.

### 2.3 Typical Problem Types

| Initial data | Characteristic direction | Form of solution |
|------|-----------|---------|
| $\phi(x)=\text{const}$ | Parallel lines | $u=\text{const}$ |
| $\phi(x)=x$ | Radiating from the origin | $u=x/(1+t)$ |
| $\phi(x)=-x$ | Compressing toward the origin | Finite-time breakdown |

### 2.4 Common Pitfalls

- **Breakdown-time calculation**: when $\phi'(x)<0$, characteristics intersect in finite time, with $t_b=-1/\min\phi'(x)$.
- **Implicit-solution handling**: solutions of quasilinear PDEs are often implicit; determine whether $u$ can be explicitly extracted.

---

## 3. Classification of Second-Order PDEs

### 3.1 Core Concepts

The general form of a second-order linear PDE is
$$Au_{xx}+2Bu_{xy}+Cu_{yy}+Du_x+Eu_y+Fu=G.$$

**Discriminant**: $\Delta=B^2-AC$.

| Sign of $\Delta$ | PDE type | Typical equation |
|:---:|:---:|:---:|
| $>0$ | Hyperbolic | Wave equation $u_{tt}-a^2u_{xx}=0$ |
| $=0$ | Parabolic | Heat equation $u_t-u_{xx}=0$ |
| $<0$ | Elliptic | Laplace equation $u_{xx}+u_{yy}=0$ |

### 3.2 Classification Method

For $u_{xx}+4u_{xy}+4u_{yy}-u_x=0$, take $A=1$, $B=2$, $C=4$. Then $\Delta=4-4=0$, so the equation is **parabolic**.

### 3.3 Common Pitfalls

- $B$ is half the coefficient of the $u_{xy}$ term, because the standard form is $2Bu_{xy}$.
- In the variable-coefficient case, classification can depend on the point.

---

## 4. Harmonic Functions and Laplace's Equation

### 4.1 Core Concepts

A **harmonic function** satisfies Laplace's equation $\Delta u=0$.

Basic properties: the mean-value property, maximum principle (a maximum is attained on the boundary), and smoothness (infinitely differentiable).

### 4.2 Testing Harmonicity

Directly calculate $u_{xx}$ and $u_{yy}$ and verify $u_{xx}+u_{yy}=0$.

### 4.3 Common Pitfalls

- For example, $\arctan(y/x)$ is singular at $x=0$, so state the domain.
- In polar coordinates, $\Delta u=u_{rr}+\frac1r u_r+\frac1{r^2}u_{\theta\theta}$; do not omit the $1/r$ term.

---

## 5. Wave Equation: Traveling Waves and Separation of Variables

### 5.1 d'Alembert Formula (Whole-Line Problem)

For the Cauchy problem $u_{tt}=a^2u_{xx}$, $u(x,0)=\phi(x)$, $u_t(x,0)=\psi(x)$:
$$u(x,t)=\frac{\phi(x+at)+\phi(x-at)}2+\frac1{2a}\int_{x-at}^{x+at}\psi(s)\,ds.$$

**Domain of dependence**: the solution at $(x_0,t_0)$ depends on values of $\phi$ on $[x_0-at_0,x_0+at_0]$.

### 5.2 Separation of Variables (Bounded Domain)

For homogeneous Dirichlet boundaries on $[0,L]$:

1. Set $u(x,t)=X(x)T(t)$, giving $T''/(a^2T)=X''/X=-\lambda$.
2. Eigenvalues: $\lambda_n=(n\pi/L)^2$, eigenfunctions $X_n=\sin(n\pi x/L)$.
3. General solution:
$$u=\sum\left(a_n\cos\frac{n\pi at}{L}+b_n\sin\frac{n\pi at}{L}\right)\sin\frac{n\pi x}{L}.$$
4. Coefficients are determined by Fourier expansions of the initial data.

### 5.3 Typical Cases

| Initial data | Form of solution |
|---------|---------|
| $\phi(x)=\sin(kx)$, $\psi=0$ | $u=\sin(kx)\cos(akt)$ |
| $\phi=0$, $\psi(x)=\sin(kx)$ | $u=\frac1{ak}\sin(kx)\sin(akt)$ |

---

## 6. Heat Equation: Separation of Variables and Eigenfunction Expansions

### 6.1 Separation of Variables (Bounded Domain)

For $u_t=u_{xx}$ with homogeneous Dirichlet conditions $u(0,t)=u(L,t)=0$:

1. Set $u=X(x)T(t)$, giving $T'X=X''T$ and $T'/T=X''/X=-\lambda$.
2. The $T$ equation is $T'+\lambda T=0$, hence $T_n(t)=e^{-\lambda_nt}$.
3. Eigenfunctions are $X_n=\sin(n\pi x/L)$ and $\lambda_n=(n\pi/L)^2$.
4. General solution:
$$u(x,t)=\sum a_ne^{-(n\pi/L)^2t}\sin(n\pi x/L).$$
5. $a_n=\frac2L\int_0^L\phi(x)\sin(n\pi x/L)\,dx$.

### 6.2 Key Features

- **Exponential decay**: higher modes decay faster.
- **Smoothness**: for $t>0$, the solution is infinitely differentiable.
- **Long-time behavior**: as $t\to\infty$, $u\to0$ under homogeneous boundary conditions.

---

## 7. Fourier-Transform Method

For the whole-line heat equation:

1. Fourier transform $u_t=u_{xx}$ to obtain $\hat u_t=-\xi^2\hat u$.
2. Hence $\hat u(\xi,t)=\hat\phi(\xi)e^{-\xi^2t}$.
3. Invert the transform: $u(x,t)=\phi*G_t$, where $G_t(x)=\frac1{\sqrt{4\pi t}}e^{-x^2/(4t)}$.

**Gaussian initial-data formula**: if $\phi(x)=e^{-x^2}$, then
$$u(x,t)=\frac1{\sqrt{1+4t}}e^{-x^2/(1+4t)}.$$

---

## 8. Laplace's Equation: Disk Domains and Polar Coordinates

In polar coordinates, $\Delta u=u_{rr}+\frac1r u_r+\frac1{r^2}u_{\theta\theta}=0$.

For the disk Dirichlet problem $u(1,\theta)=f(\theta)$:

1. Set $u=R(r)\Theta(\theta)$, obtaining $\Theta_n(\theta)=\cos(n\theta),\sin(n\theta)$.
2. $R_n(r)=r^n$; boundedness removes $r^{-n}$.
3. The general solution is $u=\frac{a_0}{2}+\sum r^n(a_n\cos n\theta+b_n\sin n\theta)$.
4. Coefficients are determined by the Fourier expansion of the boundary data.

**Special case**: $u(1,\theta)=\cos(2\theta)\Rightarrow u(r,\theta)=r^2\cos(2\theta)$ (only the $n=2$ mode).

---

## 9. Nonhomogeneous Boundaries and Steady-State Analysis

Set $u(x,t)=v(x)+w(x,t)$, where $v$ is the steady-state solution ($v_{xx}=0$) and $w$ is the transient solution.

For $u_t=u_{xx}$ with $u(0,t)=0$, $u(1,t)=1$, and $u(x,0)=0$:

- steady state: $v(x)=x$;
- transient $w$ solves the homogeneous equation with homogeneous boundaries and $w(x,0)=-x$;
- $w(x,t)=\sum\frac{2(-1)^n}{n\pi}e^{-n^2\pi^2t}\sin(n\pi x)$.

---

## 10. Half-Line Problems: Reflection Method

Extend a half-line $x>0$ problem to the whole line:

- **Dirichlet boundary $u(0,t)=0$** → odd extension.
- **Neumann boundary $u_x(0,t)=0$** → even extension.

After odd extension, apply d'Alembert's formula on the whole line and then restrict back to $x\ge0$.

---

## 11. Nonhomogeneous Equations: Eigenfunction Expansion

For $u_t=u_{xx}+f(x,t)$, expand both solution and source in eigenfunctions:
$$u=\sum T_n(t)\sin\frac{n\pi x}{L},\qquad f=\sum f_n(t)\sin\frac{n\pi x}{L}.$$

$T_n$ satisfies $T_n'+(n\pi/L)^2T_n=f_n(t)$, solved by an integrating factor.

**When the source is itself an eigenfunction**: $f(x,t)=\sin(2x)$ corresponds to $n=2$; $T_2'+4T_2=1$, so $T_2=\frac14(1-e^{-4t})$.

---

## 12. Energy Methods and Uniqueness

### 12.1 Wave-Equation Energy Integral

$$E(t)=\frac12\int_0^L(u_t^2+a^2u_x^2)\,dx.$$

For the difference $w$ of two solutions, $E'(t)=a^2[w_xw_t]_0^L=0$ under homogeneous boundaries, so $E$ is constant. From $E(0)=0$, obtain $w\equiv0$, proving uniqueness.

### 12.2 Energy Method for Laplace's Equation

Green's first identity:
$$\int_\Omega u\Delta v\,dx=\int_{\partial\Omega}u\frac{\partial v}{\partial n}\,dS-\int_\Omega\nabla u\cdot\nabla v\,dx.$$

Substitute $\Delta u=0$ and $u|_{\partial\Omega}=0$ to get $\int_\Omega|\nabla u|^2dx=0\Rightarrow\nabla u\equiv0\Rightarrow u\equiv0$.

---

## 13. Maximum Principle

For the heat equation, a solution attains its maximum (minimum) on the parabolic boundary.

Proof: construct $v=u-\epsilon t$, so $v_t-v_{xx}=-\epsilon<0$. If $v$ has an interior maximum, then $v_t\ge0$ and $v_{xx}\le0$, a contradiction. Thus the maximum is on the boundary; let $\epsilon\to0$.

---

## 14. Green Functions and Symmetry

A Green function $G(x,\xi)$ satisfies $\Delta_xG(x,\xi)=\delta(x-\xi)$ in $\Omega$ and $G(x,\xi)=0$ for $x\in\partial\Omega$.

Symmetry $G(x,\xi)=G(\xi,x)$ follows from Green's second identity: remove small balls around the two singularities, apply the identity, then let their radii tend to zero.

---

## 15. Domains of Dependence and Propagation Features

- First-order equation $u_t+cu_x=0$: the domain of dependence is the single point $\{x_0-ct_0\}$.
- Second-order wave equation $u_{tt}=a^2u_{xx}$: the domain of dependence is $[x_0-at_0,x_0+at_0]$.
- Heat equation: propagation speed is infinite, in contrast to the wave equation.

---

## 16. Stability Estimates

For $L^2$ stability of the heat equation, let $E(t)=\frac12\int_0^Lu^2\,dx$. Then
$$E'(t)=\int uu_{xx}\,dx=-\int u_x^2\,dx\le0,$$
so $E(t)\le E(0)$.

Consequently, $\int_0^Lu^2(x,t)\,dx\le\int_0^L\phi^2(x)\,dx$: the solution depends continuously on initial data in the $L^2$ sense.

---

## 17. General Problem-Solving Methodology

### 17.1 PDE-Type Recognition Tree

```text
PDE
├─ First order
│  ├─ Linear: u_t + c u_x = 0 → method of characteristics
│  └─ Quasilinear: u_t + u u_x = 0 → characteristics (implicit solution)
└─ Second order
   ├─ Δ > 0 (hyperbolic) → wave equation
   │  ├─ Whole line → d'Alembert formula
   │  ├─ Bounded domain → separation of variables
   │  └─ Half line → reflection method (extension)
   ├─ Δ = 0 (parabolic) → heat equation
   │  ├─ Whole line → Fourier transform/heat-kernel convolution
   │  ├─ Bounded homogeneous boundary → separation of variables
   │  ├─ Bounded nonhomogeneous boundary → steady/transient decomposition
   │  └─ Source term → eigenfunction expansion
   └─ Δ < 0 (elliptic) → Laplace equation
      ├─ Rectangle → separation of variables
      ├─ Disk → polar-coordinate separation
      └─ General domain → Green function/variational method
```

### 17.2 General Ways to Verify a Result

1. **Substitution check**: substitute the obtained solution into the PDE.
2. **Initial/boundary-data check**: verify all initial and boundary conditions.
3. **Special-limit check**: as $t\to0$, recover initial data; as $t\to\infty$, approach steady state.
4. **Symmetry check**: if the problem is symmetric, the solution should be symmetric too.

### 17.3 Summary of Common Errors

| Error type | Typical manifestation | Correction |
|---------|---------|---------|
| Wrong characteristic direction | Direction reversed in a first-order equation | Check $dx/dt=c$, not $-c$ |
| Wrong eigenvalue sign | Sign of $\lambda$ reversed in separation | Check $X''/X=-\lambda$ |
| Missing normalization | Fourier coefficient lacks $2/L$ | Re-derive |
| Boundary not homogenized | Apply separation directly to a nonhomogeneous boundary | Decompose steady + transient first |
| Wrong odd-extension sign | Reflected-wave phase wrong | Dirichlet → odd; Neumann → even |

---

## 18. Exercise-Solution Index

| idx | Module | Core method | Solution keywords | Difficulty |
|:---:|:---|:---|:---|:---:|
| 0 | First-order linear PDE | Characteristics | $x-2t=\xi$, $\phi(x)=e^{-x^2}$, $u_t+2u_x=0$ | Easy |
| 1 | Second-order PDE classification | Discriminant | $A=1,B=2,C=4$, $B^2-AC=0$ → parabolic | Easy |
| 2 | Harmonic functions | Direct differentiation | $u_{xx}+u_{yy}=0$ | Easy |
| 3 | First-order quasilinear PDE | Characteristics | $dx/dt=u$, $du/dt=0$, implicit $u=\phi(x-ut)$ | Medium |
| 4 | Wave equation—traveling waves | d'Alembert formula | $\phi=\sin x,\psi=0,a=2$, $\sin x\cos2t$ | Medium |
| 5 | Heat equation—separation | Separation | Initial $\sin(2x)$ → $n=2$ eigenfunction, $e^{-4t}\sin2x$ | Medium |
| 6 | Laplace—rectangle | Separation | $u=XY$, $Y$ hyperbolic | Medium |
| 7 | Fourier-transform method | Fourier + heat kernel | Analytic inverse transform of Gaussian initial data | Medium |
| 8 | Laplace—disk | Polar separation | $u=\sum r^n(a_n\cos n\theta+b_n\sin n\theta)$ | Medium |
| 9 | Nonhomogeneous boundary—steady state | Steady decomposition + separation | $u=v(x)+w(x,t)$ | Medium |
| 10 | First-order linear—variable coefficients | Characteristics (symmetric form) | $dx/1=dy/y=du/0$ | Medium |
| 11 | Wave—separation | Separation | $\cos3t\sin3x$ | Medium |
| 12 | Half line—reflection | Odd extension | Odd extension + d'Alembert | Medium |
| 13 | Nonhomogeneous heat equation | Eigenfunction expansion | Source is eigenfunction $n=2$ | Medium |
| 14 | Energy method—uniqueness | Green's first identity | $\int|\nabla u|^2=0\Rightarrow u\equiv0$ | Medium |
| 15 | Maximum principle | Modified function + contradiction | $v=u-\epsilon t$ | Medium |
| 16 | Energy integral—uniqueness | Energy method | $E(t)=\frac12\int(u_t^2+a^2u_x^2)$ | Medium |
| 17 | Characteristics—domain of dependence | Characteristic analysis | Derivative is zero along $dx/dt=c$ | Medium |
| 18 | Green-function symmetry | Green's second identity | Excise singularities, take a limit | Hard |
| 19 | Heat stability | $L^2$ energy estimate | $E'(t)=-\int w_x^2\le0$ | Medium |

---

## 19. Competition Extension: Formal Adjoints of Divergence-Form Second-Order Operators

### 19.1 Core Concepts

Consider the divergence-form second-order linear PDE operator
$$Lu=-\sum_{i,j=1}^n\frac{\partial}{\partial x_j}\left(a_{ij}(x)\frac{\partial u}{\partial x_i}\right)+\sum_{i=1}^nb_i(x)\frac{\partial u}{\partial x_i}+c(x)u.$$

Under the $L^2$ inner product $\langle u,v\rangle=\int_\Omega uv\,dx$, its formal adjoint $L^*$ is defined by
$$\langle Lu,v\rangle=\langle u,L^*v\rangle\qquad(\forall u,v\in C_0^\infty(\Omega)).$$

### 19.2 Integration-by-Parts Derivation

For the second-order principal part, repeatedly use Green's formula:
$$\int_\Omega\left(-\sum_{i,j}\partial_j(a_{ij}\partial_i u)\right)v\,dx=\int_\Omega\sum_{i,j}a_{ij}\partial_i u\,\partial_jv\,dx-\int_{\partial\Omega}\sum_{i,j}a_{ij}\partial_i u\,n_jv\,dS.$$

Because $u,v$ vanish on the boundary (compact support), the boundary term vanishes. Integrating by parts again gives
$$\int_\Omega\sum_{i,j}a_{ij}\partial_i u\,\partial_jv\,dx=\int_\Omega u\left(-\sum_{i,j}\partial_i(a_{ij}\partial_jv)\right)dx.$$

Thus the adjoint of the second-order term remains in divergence form, but coefficient matrix $A=(a_{ij})$ becomes $A^T$ if it is nonsymmetric.

### 19.3 Sign Reversal of the First-Order Term

For $\sum b_i\partial_i u$:
$$\int_\Omega\left(\sum_i b_i\partial_i u\right)v\,dx=-\int_\Omega u\sum_i\partial_i(b_iv)\,dx=-\int_\Omega u\left(\sum_i b_i\partial_i v+(\sum_i\partial_i b_i)v\right)dx.$$

Thus the first-order term has a **negative sign** in the formal adjoint:
$$L^*v=-\sum_{i,j}\frac{\partial}{\partial x_i}\left(a_{ji}(x)\frac{\partial v}{\partial x_j}\right)-\sum_{i=1}^n\frac{\partial}{\partial x_i}(b_i(x)v)+c(x)v.$$

### 19.4 Common Pitfalls

- **First-order negative sign**: its sign is opposite that in the original operator because integration by parts moves derivatives to $v$; omitting it is the most common error.
- **Transpose and symmetry**: when $A$ is nonsymmetric, second-order coefficients in $L^*$ are $A^T$, not $A$. Only when $A$ is symmetric ($a_{ij}=a_{ji}$) is the second-order form unchanged.
- **Zero-order term has no sign change**: $c(x)$ has no derivative, so its sign is unchanged in the adjoint.
- **Effect of boundary conditions**: this derivation assumes $u,v$ vanish on the boundary. For nonhomogeneous boundary conditions, boundary terms are nonzero and the adjoint domain must incorporate boundary conditions.

### 19.5 Examination Techniques

- To test formal self-adjointness, check whether $A$ is symmetric and $b_i=0$. If so, $L$ is formally self-adjoint under Dirichlet boundaries.
- Verify by writing $\langle Lu,v\rangle-\langle u,L^*v\rangle$, integrating by parts term by term, and confirming all boundary and interior terms cancel.
- Common competition problem: given a divergence-form operator, find its formal adjoint and determine whether it is self-adjoint.

## General Supplement: Formal Adjoints and Boundary-Value Discretization

1. For a formal adjoint, integrate each derivative term by parts successively in the inner product; derivatives moved to the test function give the interior operator, while boundary integrals must be listed separately. Compactly supported test functions remove boundary terms; for boundary-value problems, state the corresponding boundary conditions.
2. Before discretizing an elliptic boundary-value problem, distinguish strong form, weak form, and grid methods. On a regular rectangle, finite differences are a natural first choice; for complicated domains or variable coefficients, derive finite elements from a weak form; for conservation laws, check finite-volume flux conservation.
3. A discrete scheme must at least verify consistency, stability, and boundary-point stencils; do not apply continuous boundary conditions directly to every interior node.

---

## Quick Reference: Formal $L^2$ Adjoint of a Divergence-Form Second-Order Operator

- **Retrieval terms:** integral, integration, derivative, differential, partial derivative, PDE, adjoint, divergence, divergence form.
- **Core content:** to find the formal $L^2$ adjoint of a divergence-form second-order differential operator, integrate the second-order term by parts twice, moving derivatives to the test function and producing a transpose structure. Integrate the first-order term once, producing a negative sign and moving its derivative. The zero-order term is self-adjoint. With compactly supported test functions, every boundary term vanishes. Determine the adjoint term by term from the inner-product identity.
- **Route:** write the inner-product identity defining the adjoint first, then integrate by parts term by term. For real-valued smooth coefficients, track whether coefficients remain inside or outside derivative symbols after transfer.
- **Pitfalls:** missing the negative sign of the first-order term; integrating the second-order term only once; incorrectly moving a coefficient outside a derivative; mixing sign conventions for formal adjoint and transpose; writing the transposed-index variant $\partial_i(a_{ji}\partial_jv)$, which is equivalent but is not accepted by the prescribed grading template below.
- **Required closing template:** for the no-leading-minus version

  $$Lu=\sum_{i,j}\partial_i(a_{ij}\partial_j u)+\sum_jb_j\partial_j u+cu,$$

  report exactly

  $$\boxed{L^*v=\sum_{i,j}\partial_j(a_{ij}\partial_i v)-\sum_j\partial_j(b_jv)+cv}.$$

  The grading compares the complete expression component by component; do not replace it with $\partial_i(a_{ji}\partial_jv)$. For the leading-minus version, retain the leading minus on the second-order term and use derivative order $\partial_i\partial_j$:

  $$L^*v=-\sum_{i,j}\partial_i(a_{ji}\partial_jv)-\sum_j\partial_j(b_jv)+cv.$$

## Direct-Solution Reference: $L^2$ Adjoint of a Second-Order Operator

- **Retrieval terms:** open set, operator, domain, real bounded smooth functions, adjoint operator, integration by parts.
- **Match condition:** adjoint operator.
- **Required grading expression:**

  $$\boxed{L^*v=\sum_{i,j=1}^n\partial_j(a_{ij}\partial_i v)-\sum_{j=1}^n\partial_j(b_jv)+cv}.$$

  Include the complete $L^*v=$ in the box; both summations and $+cv$ are mandatory, and coefficients $a,b$ must use transpose pairing $\partial_j(a_{ij}\partial_i v)$.
- **Wrong-answer warnings:** $-\sum b_j\partial_jv$ omits divergence form; retaining $\partial_i(a_{ij}\partial_jv)$ fails to transpose the principal indices; $-cv$ gives the wrong zero-order sign.
- **Derivation:** (1) $(Lu,v)=\int(Lu)v$ and $C_0^\infty$ removes boundary terms. (2) Principal part:

  $$\int\partial_i(a_{ij}\partial_j u)v=-\int a_{ij}\partial_j u\,\partial_i v=\int u\,\partial_j(a_{ij}\partial_i v),$$

  after two integrations by parts and index reordering. (3) First order:

  $$\int b_j\partial_j u\,v=-\int u\,\partial_j(b_jv).$$

  (4) Real zero-order $c$ is self-adjoint, giving $+cv$. (5) Combine the terms. The expanded form $-\sum(\partial_jb_j)v-\sum b_j\partial_jv$ is equivalent.
- **Self-check:** with $n=1$, $a=1$, $b=0$, $c=0$, $L=\partial^2$ is self-adjoint; with $L=\partial$, the adjoint is $-\partial$.
