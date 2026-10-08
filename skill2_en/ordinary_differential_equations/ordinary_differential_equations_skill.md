# Ordinary Differential Equations Problem-Solving Skill

## Scope and Routing Conventions

- Applies to one-variable ODE initial/boundary-value problems, stability, phase planes, parametrized solutions, and limit cycles.
- Problems with multiple independent variables or boundary operators route to partial differential equations; differences, error, and numerical stability route to numerical analysis.
- Preserve initial values, domains, singular solutions, and stability conditions; check both general and particular solutions by substitution into the original equation.

## Part I: Knowledge Modules

### Module 1: First-Order Separable Equations

For $dy/dx=f(x)g(y)$, separate variables:

$$\frac{dy}{g(y)}=f(x)\,dx,\qquad \int\frac{dy}{g(y)}=\int f(x)\,dx+C.$$

Solve explicitly for $y=y(x,C)$ when possible, then use $y(x_0)=y_0$ to determine $C$. Roots of $g(y)=0$ can be singular solutions and require separate treatment. Retain the integration constant and the absolute value in $\int dy/y=\ln|y|$, unless $y>0$ is known. First check whether the right-hand side factors as $f(x)g(y)$; use the initial condition before performing avoidable algebra.

### Module 2: First-Order Linear Equations

For $y'+P(x)y=Q(x)$, use the integrating factor

$$\mu(x)=\exp\!\left(\int P(x)\,dx\right),\qquad y=\frac1{\mu(x)}\left[\int\mu(x)Q(x)\,dx+C\right].$$

Normalize the coefficient of $y'$ to $1$, multiply by $\mu$ so the left side is $(\mu y)'$, integrate, solve for $y$, and apply the initial value. No integration constant is needed in the exponent defining $\mu$. Discontinuities of $P$ can restrict the solution domain. If $Q=0$, direct separation can be faster; always substitute the result back.

### Module 3: First-Order Homogeneous Equations

For $y'=F(y/x)$, verify zero-degree homogeneity, set $v=y/x$, and use

$$y=vx,\qquad y'=v+x\frac{dv}{dx},\qquad \frac{dv}{F(v)-v}=\frac{dx}{x}.$$

Integrate, restore $v=y/x$, and impose the initial value. Do not omit the $xv'$ chain-rule term. If $F(v)=v$, then $xv'=0$, giving $v=C$ and $y=Cx$.

### Module 4: Bernoulli Equations

For $y'+P(x)y=Q(x)y^n$ with $n\ne0,1$, put $z=y^{1-n}$. Since

$$z'=(1-n)y^{-n}y',$$

the transformed linear equation is

$$z'+(1-n)P(x)z=(1-n)Q(x).$$

Solve it by an integrating factor, then recover $y=z^{1/(1-n)}$ and apply the initial value. For $n=0$ the equation is linear and for $n=1$ it is separable; $y=0$ can be a singular solution when $n>0$.

### Module 5: Second-Order Equations Not Explicitly Containing $y$

For $F(x,y',y'')=0$, set $p=y'$, so $y''=dp/dx$. Solve the first-order equation $F(x,p,p')=0$, obtain $p=p(x,C_1)$, then integrate

$$y=\int p(x,C_1)\,dx+C_2.$$

Convert the initial derivative as $p(x_0)=y'(x_0)$ and use both $y(x_0)=y_0$ and $y'(x_0)=y'_0$. The equation for $p$ may itself be separable or linear.

### Module 6: Second-Order Equations Not Explicitly Containing $x$

For $F(y,y',y'')=0$, let $p=y'$ as a function of $y$. Then

$$y''=\frac{dp}{dx}=\frac{dp}{dy}\frac{dy}{dx}=p\frac{dp}{dy}.$$

Solve $F(y,p,p\,dp/dy)=0$ for $p=p(y,C_1)$, then separate $dy/p(y,C_1)=dx$ and integrate. Here $y''\ne p'$; $p=0$ may be a separate constant solution.

### Module 7: Homogeneous Linear Equations with Constant Coefficients

For $ay''+by'+cy=0$, $a\ne0$, solve

$$ar^2+br+c=0,\qquad r=\frac{-b\pm\sqrt{b^2-4ac}}{2a}.$$

If $\Delta>0$, $y=C_1e^{r_1x}+C_2e^{r_2x}$; if $\Delta=0$, $y=(C_1+C_2x)e^{rx}$; if $\Delta<0$ with roots $\alpha\pm i\beta$, then

$$y=e^{\alpha x}(C_1\cos\beta x+C_2\sin\beta x).$$

Match characteristic-polynomial and ODE coefficients carefully, retain the $e^{\alpha x}$ factor in the complex-root case, and use two initial conditions to solve for $C_1,C_2$.

### Module 8: Nonhomogeneous Constant-Coefficient Equations with Polynomial Forcing

For $ay''+by'+cy=P_n(x)$, first solve the homogeneous equation. Choose a polynomial trial $Q_n(x)$ if $c\ne0$, $xQ_n(x)$ if $c=0,b\ne0$, and $x^2Q_n(x)$ if $c=b=0$. Substitute, compare every power of $x$, and write $y=y_h+y_p$ before imposing initial values. The trial must contain every lower-degree term; a zero characteristic root causes the required multiplication by $x$ or $x^2$.

### Module 9: Exponential Forcing

For $ay''+by'+cy=Ae^{\lambda x}$, use $Be^{\lambda x}$ if $\lambda$ is not a characteristic root, $Bxe^{\lambda x}$ for a simple root, and $Bx^2e^{\lambda x}$ for a double root. In the nonresonant case,

$$B=\frac{A}{a\lambda^2+b\lambda+c}.$$

Check resonance first; when differentiating $Bxe^{\lambda x}$, use $B(\lambda x+1)e^{\lambda x}$.

### Module 10: Trigonometric Forcing

For $ay''+by'+cy=A\cos\omega x+B\sin\omega x$, use $C\cos\omega x+D\sin\omega x$ unless $\pm i\omega$ is a characteristic root; in resonance multiply the entire trial by $x$. Include both sine and cosine even if only one occurs on the right. Compare sine and cosine coefficients, or use a complex-exponential trial. Resonance means $\pm i\omega$ is a root (equivalently $a\omega^2\mp c=0$ and $b=0$ in the stated form).

### Module 11: Euler Equations

For $x^2y''+axy'+by=f(x)$, put $x=e^t$ for $x>0$, or $x=-e^t$ for $x<0$. With $D=d/dt$,

$$xy'=Dy,\qquad x^2y''=D(D-1)y,$$

so the equation becomes $[D(D-1)+aD+b]y=f(e^t)$. Solve the constant-coefficient equation and restore $t=\ln|x|$. Typical homogeneous terms are $x^r$, $x^r\ln|x|$, and $x^\alpha\cos(\beta\ln|x|)$. Do not replace $D(D-1)$ by $D^2$, and preserve the separate $x>0,x<0$ domains.

### Module 12: Laplace Transforms

Use the transform to turn an initial-value ODE into an algebraic equation, with

$$\mathcal L\{y'\}=sY(s)-y(0),\quad \mathcal L\{y''\}=s^2Y(s)-sy(0)-y'(0),$$

$$\mathcal L\{e^{at}\}=\frac1{s-a},\quad \mathcal L\{t^ne^{at}\}=\frac{n!}{(s-a)^{n+1}}.$$

Transform both sides, insert initial values, solve for $Y(s)$, perform partial fractions, and invert term by term. Retain both initial values for $y''$, handle repeated factors carefully, and use $\mathcal L\{f*g\}=F(s)G(s)$ when useful. This is especially effective for constant-coefficient equations with discontinuous or impulsive forcing.

### Module 13: Power-Series Method

Set $y=\sum_{n=0}^\infty a_nx^n$, differentiate, align all series at the same power by shifting indices, compare coefficients, and solve the recurrence. Write $y=a_0y_1(x)+a_1y_2(x)$; $a_0=y(0)$ and $a_1=y'(0)$. Respect changed lower summation limits, avoid zero denominators in a recurrence, and discuss radius of convergence separately. Near an ordinary point a linear equation has a convergent series solution; near a singular point use Frobenius.

### Module 14: Constant-Coefficient Linear Systems

For $\vec x'=A\vec x$, solve $\det(A-\lambda I)=0$. A real eigenpair $(\lambda,v)$ gives $e^{\lambda t}v$; a complex pair $\alpha\pm i\beta$ gives two real solutions from real and imaginary parts. For a repeated eigenvalue with insufficient geometric multiplicity, find a generalized eigenvector from $(A-\lambda I)w=v$, producing

$$e^{\lambda t}v,\qquad e^{\lambda t}(tv+w).$$

Form the general linear combination and use the initial vector to determine its constants. Do not omit the generalized-eigenvector chain for a defective repeated eigenvalue.

### Module 15: Existence and Uniqueness

Picard's theorem gives a unique solution of an initial-value problem when $f(x,y)$ is continuous in a region and Lipschitz in $y$. A sufficient condition is that $\partial f/\partial y$ is bounded there; a continuously differentiable $f$ is locally Lipschitz. Identify $f$, check continuity, bound $f_y$, then conclude existence and uniqueness. Continuity and Lipschitz continuity are independent: $\sqrt y$ has unbounded $y$-derivative at $y=0$, and $y'=y^\alpha$, $0<\alpha<1$, is a standard nonuniqueness case there. Construct multiple solutions by separation while retaining any branch lost on division by zero.

### Module 16: Stability

For $dy/dt=f(y)$, equilibria satisfy $f(y^*)=0$. If $f'(y^*)<0$, the equilibrium is asymptotically stable; if $f'(y^*)>0$, it is unstable; if $f'(y^*)=0$, higher-order analysis is required. In one dimension a sign diagram of $f$ gives arrows toward stable equilibria. In higher dimension, use real parts of eigenvalues; distinguish stability from asymptotic stability.

### Module 17: Planar Singularities and Phase Portraits

For $\dot x=A x$, classify by eigenvalues:

| Eigenvalues | Type | Stability |
|:---|:---|:---|
| two negative real | stable node | asymptotically stable |
| two positive real | unstable node | unstable |
| one positive, one negative | saddle | unstable |
| conjugates with negative real part | stable focus | asymptotically stable |
| conjugates with positive real part | unstable focus | unstable |
| purely imaginary | center | stable, not asymptotically |

Compute $\tau=\operatorname{tr}A$, $\Delta=\det A$, and

$$\lambda=\frac{\tau\pm\sqrt{\tau^2-4\Delta}}2.$$

Use the signs of $\tau$, $\Delta$, and $\tau^2-4\Delta$, then draw eigen-directions or rotation direction. A center has $\tau=0,\Delta>0$ and purely imaginary roots; a focus has nonzero real part.

### Modules 18–20

**Orthogonal trajectories:** If a curve family has $y'=f(x,y)$, its orthogonal trajectories satisfy $y'=-1/f(x,y)$. Differentiate $F(x,y)=C$ and eliminate $C$, solve the resulting first-order equation, and retain the slope-product condition $y'_{\perp}y'_{\rm original}=-1$. Concentric circles and lines through the origin are the standard pair.

**Physical modeling:** Choose variables such as $v(t)$ or $x(t)$, derive the ODE from a law such as Newton's second law, extract initial data, solve, then discuss asymptotic behavior and parameter dependence. Draw a force diagram, maintain sign and dimensional consistency, and note that terminal velocity is where net force is zero.

**Parameter analysis:** Find a characteristic equation or parameter-dependent general solution, locate parameter values at which qualitative behavior changes, analyze each parameter interval, and check every boundary separately—often a repeated-root or purely imaginary-root case. Real parts of roots determine growth/decay, while imaginary parts determine oscillation.

## General ODE Methodology

Identify order first, then whether a second-order equation is reducible. For constant coefficients use characteristic roots; for variable coefficients consider Euler or power-series methods; for nonhomogeneous equations select a trial from the forcing term. Laplace transforms are particularly effective with initial data. Use Lipschitz conditions for existence/uniqueness, linearization for stability, and eigenvalue classification for singularities. For physical problems, model first:

$$m\frac{dv}{dt}=\sum F.$$

Verify every answer by substitution, initial values, dimensional consistency, $t\to\infty$ behavior, and degenerate parameter values.

## Competition Extension: Parametric ODEs, Logarithmic Differentiation, and Limit Cycles

Represent a solution as $x=\varphi(t),y=\psi(t)$, so $dy/dx=\psi'(t)/\varphi'(t)$; replace the derivative, solve in $t$, and eliminate $t$ or retain the parametrization. For $F(x,y,y')=0$ homogeneous in $x,y$, $y=tx$ is useful. A quotient of affine forms can often be made homogeneous by translation/rotation. Check missing singular curves.

For $y'=f(x)y$ or $y'=P(x)y+Q(x)y\ln y$, put $u=\ln y$ for $y>0$, use $y'=yu'$, solve the resulting equation for $u$, then restore $y=e^u$. Thus $y'=y\ln y$ gives $u'=u$, $u=Ce^x$, and $y=e^{Ce^x}$. For negative values use regions or $\ln|y|$, and test $y=0$ separately.

For $\dot x=P(x,y),\dot y=Q(x,y)$, Poincaré–Bendixson yields a limit cycle when a bounded positive semiorbit has no equilibrium in its $\omega$-limit set. Dulac's criterion excludes cycles if a function $B$ makes $\partial(BP)/\partial x+\partial(BQ)/\partial y$ one-signed and nonzero on a simply connected region; Bendixson is $B\equiv1$. Classify equilibria, construct an annular trapping region, apply Poincaré–Bendixson, and use Dulac for uniqueness if needed. The Van der Pol equation

$$\ddot x+\mu(x^2-1)\dot x+x=0,\qquad\mu>0,$$

has a unique stable limit cycle for appropriate $\mu$.
