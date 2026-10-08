---
name: complex-analysis-verification
description: Use when verifying complex analysis problems with sympy — complex numbers, Cauchy-Riemann equations, Cauchy integral formula, Laurent series, residue theorem, contour integration, conformal mapping, argument principle, and Rouché theorem
---

# Complex Analysis Problem-Solving and Verification Skill

## Domain Boundaries and Routing Conventions

- Scope: holomorphic functions, Cauchy--Riemann equations, complex integration, Laurent expansions, residues, and conformal mappings.
- Do not take over: integer-norm problems in imaginary quadratic fields without a complex-analytic condition should be routed to discrete mathematics; real-variable Fourier transforms should be routed to mathematical analysis.
- Verification contract: first determine the domain of analyticity, isolated singularities, and contour orientation; then check residues, winding numbers, and integral orientation. A formal series must not be treated as a convergent expansion.

## Overview

This manual covers the core undergraduate complex-analysis system: complex-number operations and de Moivre's formula; analytic functions and the Cauchy--Riemann equations; Cauchy's integral theory and higher-derivative formulas; Laurent series and radii of convergence; the residue theorem and contour integration; conformal mappings (Möbius transformations); zeros and poles (the argument principle and Rouché's theorem); and harmonic functions. Using 20 selected exercises as its framework, it systematically organizes the core concepts, commonly used theorems, solution procedures, common pitfalls, and verification prompts for each module. It is suitable for learning, review, and automated solution verification in complex analysis.

---

## Knowledge System

### Module 1: Complex-Number Operations and de Moivre's Formula

#### Core Concepts

- **Representations of a complex number:** algebraic form $z=a+bi$ ($a,b\in\mathbb R$), and polar form $z=r(\cos\theta+i\sin\theta)=re^{i\theta}$.
- **Modulus:** $|z|=\sqrt{a^2+b^2}=r$.
- **Argument:** $\arg(z)=\theta+2k\pi$ ($k\in\mathbb Z$), with principal value $\operatorname{Arg}(z)\in(-\pi,\pi]$.
- **Complex conjugate:** $\overline z=a-bi$, satisfying $|z|^2=z\overline z=a^2+b^2$.
- **de Moivre's formula:** $(\cos\theta+i\sin\theta)^n=\cos(n\theta)+i\sin(n\theta)$, equivalently $(e^{i\theta})^n=e^{in\theta}$.
- **$n$th roots of a complex number:** the $n$ solutions of $z^n=w$ are $z_k=\sqrt[n]{|w|}\cdot e^{i(\arg(w)+2\pi k)/n}$, where $k=0,1,\ldots,n-1$.

#### Common Formulas

1. **Polar representation:**

   $$z=a+bi\quad\Longrightarrow\quad r=\sqrt{a^2+b^2},\quad \theta=\arctan\frac ba\quad\text{(adjust according to the quadrant)}.$$

2. **de Moivre's formula:**

   $$(re^{i\theta})^n=r^ne^{in\theta}=r^n(\cos n\theta+i\sin n\theta).$$

3. **Powers of a complex number:**

   $$(a+bi)^n=r^n\cdot(\cos n\theta+i\sin n\theta).$$

#### Solution Procedure: High Powers of a Complex Number

1. Convert the complex number to polar form $re^{i\theta}$, calculating $r=\sqrt{a^2+b^2}$ and $\theta$.
2. Apply de Moivre's formula $(re^{i\theta})^n=r^ne^{in\theta}$.
3. Convert the result back to algebraic form $x+yi$, using $e^{i\theta}=\cos\theta+i\sin\theta$.
4. Simplify the trigonometric values.

---

### Module 2: Analytic Functions and the Cauchy--Riemann Equations

#### Core Concepts

- **Derivative of a complex function:** $f'(z_0)=\lim_{h\to0}\frac{f(z_0+h)-f(z_0)}h$, where $h$ is complex and the limit must be the same as $h$ tends to $0$ from every direction.
- **Analytic (holomorphic) function:** if $f$ is differentiable at every point of an open set $D$, then $f$ is analytic in $D$.
- **Cauchy--Riemann equations** (necessary condition): for $f(z)=u(x,y)+iv(x,y)$ with $z=x+iy$, if $f$ is differentiable at $z_0$, then at that point

  $$\frac{\partial u}{\partial x}=\frac{\partial v}{\partial y},\qquad \frac{\partial u}{\partial y}=-\frac{\partial v}{\partial x}.$$

- **Sufficient condition for the C--R equations:** if $u,v$ have continuous first partial derivatives in $D$ and satisfy the C--R equations in $D$, then $f=u+iv$ is analytic in $D$.
- **Harmonic function:** $u(x,y)$ is harmonic when $u_{xx}+u_{yy}=0$. The real and imaginary parts of an analytic function are harmonic.
- **Harmonic conjugate:** if $u$ is harmonic, there exists a function $v$, called a harmonic conjugate of $u$, such that $f=u+iv$ is analytic. Obtain $v$ by integrating the C--R equations.

#### Common Formulas

1. **Laplace equation:**

   $$\Delta u=u_{xx}+u_{yy}=0.$$

2. **Finding a harmonic conjugate from the C--R equations:**

   $$v(x,y)=\int u_x\,dy+\varphi(x),$$

   then use $v_x=-u_y$ to determine $\varphi(x)$.

3. **Reconstruction of an analytic function:** if $u$ is known, then $f(z)=u+iv$, where $v$ satisfies

   $$dv=-u_y\,dx+u_x\,dy$$

   as an exact differential.

#### Solution Procedure: Determining Where a Function Is Analytic

1. Write $u(x,y)$ and $v(x,y)$.
2. Compute the four first partial derivatives.
3. Verify the C--R equations $u_x=v_y$ and $u_y=-v_x$, and identify the set of points where they hold.
4. If they hold only at isolated points, the function is analytic nowhere: analyticity requires differentiability on an open neighborhood.

#### Solution Procedure: Finding a Harmonic Conjugate

1. Verify that $u$ is harmonic: $u_{xx}+u_{yy}=0$.
2. Integrate $v_y=u_x$ with respect to $y$ to obtain $v=\int u_x\,dy+\varphi(x)$.
3. Use $v_x=-u_y$ to determine $\varphi'(x)$, then integrate to obtain $\varphi(x)$.
4. Use an additional condition, such as $f(0)=1$, to determine the integration constant.
5. Combine $u+iv$ into an expression involving only $z$.

---

### Module 3: Cauchy's Integral Theory

#### Core Concepts

- **Cauchy's integral theorem:** if $f$ is analytic on a simple closed contour $C$ and throughout its interior, then $\oint_Cf(z)\,dz=0$.
- **Cauchy's integral formula:** if $f$ is analytic on a simple closed contour $C$ and throughout its interior and $a$ lies inside $C$, then

  $$f(a)=\frac1{2\pi i}\oint_C\frac{f(z)}{z-a}\,dz.$$

- **Higher-order Cauchy integral formula (Cauchy's derivative formula):**

  $$f^{(n)}(a)=\frac{n!}{2\pi i}\oint_C\frac{f(z)}{(z-a)^{n+1}}\,dz.$$

- **ML estimate:** if $|f(z)|\leq M$ on $C$ and $C$ has length $L$, then

  $$\left|\oint_Cf(z)\,dz\right|\leq ML.$$

#### Common Formulas

1. **Standard Cauchy integral formula:**

   $$\oint_{|z-a|=R}\frac{f(z)}{z-a}\,dz=2\pi i\,f(a).$$

2. **Higher-derivative formula:**

   $$\oint_{|z-a|=R}\frac{f(z)}{(z-a)^{n+1}}\,dz=\frac{2\pi i}{n!}\,f^{(n)}(a).$$

3. **Liouville's theorem** (derived from Cauchy estimates): every bounded entire function is constant.

#### Solution Procedure: Computing a Contour Integral with Cauchy's Formula

1. Confirm that $f(z)$ is analytic on the contour and in its interior.
2. Determine the locations of the singularities in the integrand, in particular whether they lie inside the contour.
3. Write the integrand in the form $f(z)/(z-a)^{n+1}$.
4. Apply Cauchy's integral formula or the higher-derivative formula, directly substituting $f^{(n)}(a)$.
5. Multiply the result by $2\pi i$ (or by $2\pi i/n!$).

---

### Module 4: Series Expansions

#### Core Concepts

- **Taylor series:** if $f$ is analytic in the disk centered at $a$ with radius $R$, then $f(z)=\sum_{n=0}^\infty a_n(z-a)^n$, where $a_n=f^{(n)}(a)/n!$.
- **Laurent series:** if $f$ is analytic in the annulus $r<|z-a|<R$, then

  $$f(z)=\sum_{n=-\infty}^{\infty}c_n(z-a)^n,\qquad c_n=\frac1{2\pi i}\oint_C\frac{f(z)}{(z-a)^{n+1}}\,dz.$$

- **Radius of convergence:** a power series $\sum a_nz^n$ has radius $R=\lim_{n\to\infty}|a_n/a_{n+1}|$ by the ratio test, or $R=1/\limsup_{n\to\infty}\sqrt[n]{|a_n|}$ by the root test.
- **Geometric-series expansion:** $1/(1-z)=\sum_{n=0}^\infty z^n$ for $|z|<1$; it is the basic tool for Laurent expansions.

#### Common Formulas

1. **Radius of convergence (ratio test):**

   $$R=\lim_{n\to\infty}\left|\frac{a_n}{a_{n+1}}\right|.$$

2. **Radius of convergence (root test / Cauchy--Hadamard):**

   $$R=\frac1{\limsup_{n\to\infty}\sqrt[n]{|a_n|}}.$$

3. **Geometric series:**

   $$\frac1{1-z}=\sum_{n=0}^\infty z^n\qquad(|z|<1).$$

4. **Partial fractions** (for Laurent expansion of rational functions):

   $$\frac1{z(z-1)}=\frac1{z-1}-\frac1z.$$

#### Solution Procedure: Laurent Series in an Annulus

1. For a rational function, first perform partial-fraction decomposition.
2. Identify the convergence region of each fraction and choose the appropriate direction for the geometric expansion:
   - for $|z|<1$, $1/(1-z)=\sum_{n=0}^\infty z^n$;
   - for $|z|>1$, $1/(1-z)=-z^{-1}/(1-z^{-1})=-\sum_{n=1}^\infty z^{-n}$.
3. Combine the expansions to obtain the complete Laurent series, attending to both positive and negative powers.

#### Solution Procedure: Radius of a Power Series

1. Identify $a_n$, the coefficient of the $n$th term.
2. Apply the ratio test $R=\lim|a_n/a_{n+1}|$, or recognize a geometric-series structure.
3. In special cases apply the root test.

---

### Module 5: Residue Theory

#### Core Concepts

- **Isolated singularity:** if $f$ is analytic in a punctured neighborhood of $z_0$ but not analytic at $z_0$, then $z_0$ is an isolated singularity.
  - **Removable singularity:** the Laurent expansion has no negative-power terms (and the residue is $0$).
  - **Pole of order $m$:** the Laurent expansion has finitely many negative-power terms, the lowest being $(z-z_0)^{-m}$.
  - **Essential singularity:** the Laurent expansion has infinitely many negative-power terms.
- **Residue:** the residue $\operatorname{Res}(f,z_0)$ is the coefficient $c_{-1}$ of $(z-z_0)^{-1}$ in the Laurent expansion of $f$ at the isolated singularity $z_0$.
- **Residue theorem:** if $f$ is analytic on and inside a simple closed contour $C$ except at finitely many isolated singularities $z_1,\ldots,z_k$, then

  $$\oint_Cf(z)\,dz=2\pi i\sum_{j=1}^k\operatorname{Res}(f,z_j).$$

#### Common Formulas

1. **Residue at a simple pole:**

   $$\operatorname{Res}(f,z_0)=\lim_{z\to z_0}(z-z_0)f(z).$$

2. **Residue at a pole of order $m$:**

   $$\operatorname{Res}(f,z_0)=\frac1{(m-1)!}\lim_{z\to z_0}\frac{d^{m-1}}{dz^{m-1}}\left[(z-z_0)^mf(z)\right].$$

3. **Residue of $f(z)=P(z)/Q(z)$ at a simple pole** ($P(z_0)\ne0$, $Q(z_0)=0$, $Q'(z_0)\ne0$):

   $$\operatorname{Res}(f,z_0)=\frac{P(z_0)}{Q'(z_0)}.$$

4. **Residue theorem:**

   $$\oint_Cf(z)\,dz=2\pi i\sum\operatorname{Res}(f,z_j)\qquad\text{(all singularities inside $C$)}.$$

#### Solution Procedure: Residue at an Isolated Singularity

1. Determine the type of singularity: simple pole, pole of order $m$, or essential singularity.
2. At a simple pole, use $\operatorname{Res}=\lim_{z\to z_0}(z-z_0)f(z)$.
3. At a pole of order $m$, use $\operatorname{Res}=\frac1{(m-1)!}\lim\frac{d^{m-1}}{dz^{m-1}}[(z-z_0)^mf(z)]$.
4. At an essential singularity, read the $c_{-1}$ coefficient directly from the Laurent series.
5. Verify that the sum of all isolated finite residues equals the negative of the residue at infinity.

---

### Module 6: Contour Integrals and the Evaluation of Real Integrals

#### Core Concepts

- **Using the residue theorem for a real integral:** transform the real integral into a contour integral in the complex plane, then apply the residue theorem.
- **Typical contours:**
  - **Large upper-half-plane semicircle:** for $\int_{-\infty}^{\infty}P(x)/Q(x)\,dx$ when $\deg Q\geq\deg P+2$.
  - **Unit-circle contour:** for $\int_0^{2\pi}R(\cos\theta,\sin\theta)\,d\theta$, with $z=e^{i\theta}$.
  - **Sector or rectangle contours:** for integrals involving exponential functions.
  - **Keyhole contour:** for integrals involving multivalued functions.
- **Jordan's lemma:** used for integrals containing $e^{i\alpha z}$ with $\alpha>0$, ensuring that the integral over the large semicircular arc tends to $0$.

#### Common Formulas

1. **Standard rational-integral form:**

   $$\int_{-\infty}^{\infty}\frac{P(x)}{Q(x)}\,dx=2\pi i\sum_{\operatorname{Im}(z_k)>0}\operatorname{Res}\left(\frac{P(z)}{Q(z)},z_k\right),$$

   where $z_k$ runs over all poles in the upper half-plane.

2. **Substitution for trigonometric integrals** ($z=e^{i\theta}$):

   $$\cos\theta=\frac{z+z^{-1}}2,\quad\sin\theta=\frac{z-z^{-1}}{2i},\quad d\theta=\frac{dz}{iz},$$

   $$\int_0^{2\pi}R(\cos\theta,\sin\theta)\,d\theta=\oint_{|z|=1}R\left(\frac{z+z^{-1}}2,\frac{z-z^{-1}}{2i}\right)\frac{dz}{iz}.$$

3. **Infinite integral with trigonometric functions:**

   $$\int_{-\infty}^{\infty}\frac{\cos x}{x^2+a^2}\,dx=\operatorname{Re}\left[2\pi i\cdot\operatorname{Res}\left(\frac{e^{iz}}{z^2+a^2},ia\right)\right].$$

4. **Standard result involving $e^{iz}$:**

   $$\int_{-\infty}^{\infty}\frac{e^{i\alpha x}}{x^2+1}\,dx=\frac\pi{e^\alpha}\qquad(\alpha>0).$$

#### Solution Procedure: $\int_{-\infty}^{\infty}P(x)/Q(x)\,dx$

1. Verify $\deg Q\geq\deg P+2$, which ensures the large-semicircle arc integral tends to $0$.
2. Find all poles of $P(z)/Q(z)$ in the upper half-plane.
3. Compute the residue at every pole, usually a simple pole using $P(z_0)/Q'(z_0)$.
4. Apply the residue theorem: the integral equals $2\pi i$ times the sum of upper-half-plane residues.

#### Solution Procedure: $\int_0^{2\pi}R(\cos\theta,\sin\theta)\,d\theta$

1. Make the substitution $z=e^{i\theta}$ and express $\cos\theta$, $\sin\theta$, and $d\theta$ in terms of $z$.
2. Convert the integrand to $\oint_{|z|=1}f(z)\,dz$.
3. Find the poles inside $|z|=1$.
4. Compute the residues. The integral is $2\pi i$ times the sum of residues inside the unit circle.

#### Infinite Integrals Containing $\cos x$ or $\sin x$

1. Rewrite the integral as $\int_{-\infty}^{\infty}\operatorname{Re}[e^{i\alpha x}f(x)]\,dx$.
2. Use a large upper-half-plane semicircle to compute $\oint e^{i\alpha z}f(z)\,dz$.
3. Apply Jordan's lemma to verify that the large-semicircle arc integral is $0$.
4. Take the real part (or imaginary part) to obtain the final result.

---

### Module 7: Conformal Mappings

#### Core Concepts

- **Conformality of an analytic function:** if $f$ is analytic at $z_0$ and $f'(z_0)\ne0$, then $f$ preserves angles (is conformal) at $z_0$.
- **Linear fractional (Möbius) transformation:**

  $$w=T(z)=\frac{az+b}{cz+d},\qquad ad-bc\ne0.$$

- **Properties of Möbius transformations:**
  - They map circles (including lines, regarded as circles through infinity) to circles.
  - They preserve symmetry: points symmetric with respect to a circle map to points symmetric with respect to the image circle.
  - They preserve cross-ratios: $(z_1,z_2;z_3,z_4)=(w_1,w_2;w_3,w_4)$.
- **Boundary correspondence principle:** if $f$ is analytic in $D$, continuous on $\partial D$, and maps $\partial D$ one-to-one onto $\partial\Omega$, then $f$ maps $D$ one-to-one onto $\Omega$.

#### Common Formulas

1. **Standard map from the upper half-plane to the unit disk:**

   $$w=\frac{z-i}{z+i}$$

   maps the upper half-plane $\mathbb H$ to the unit disk $\mathbb D$.

2. **Inverse of a Möbius transformation:**

   $$T^{-1}(w)=\frac{-dw+b}{cw-a}.$$

3. **Cross-ratio preservation:**

   $$\frac{(z-z_1)(z_2-z_3)}{(z-z_3)(z_2-z_1)}=\frac{(w-w_1)(w_2-w_3)}{(w-w_3)(w_2-w_1)}.$$

#### Solution Procedure: Region Mapped by a Möbius Transformation

1. Determine the inverse of $w=T(z)$.
2. Verify the boundary image; for example, real axis $\to$ unit circle by calculating $|T(x)|=1$ for $x\in\mathbb R$.
3. Choose an interior test point, such as $z=i$ in the upper half-plane, compute its image, and check that it lies in the target region.
4. Invoke the boundary correspondence principle to conclude the complete region mapping.

---

### Module 8: Theory of Zeros and Poles

#### Core Concepts

- **Zero:** if $f(z_0)=0$, then $z_0$ is a zero of $f$. If $f^{(k)}(z_0)=0$ for $k=0,1,\ldots,m-1$, while $f^{(m)}(z_0)\ne0$, then it is a zero of multiplicity $m$.
- **Pole:** if $1/f$ has a zero of multiplicity $m$ at $z_0$, then $z_0$ is a pole of order $m$ of $f$.
- **Meromorphic function:** a function analytic in a region except at poles.
- **Argument principle:** if $f$ is meromorphic on and inside a simple closed contour $C$, and $f(z)\ne0$ on $C$, then

  $$\frac1{2\pi i}\oint_C\frac{f'(z)}{f(z)}\,dz=N-P,$$

  where $N$ is the number of zeros and $P$ the number of poles, both counted with multiplicity. Equivalently, $\Delta_C\arg f(z)=2\pi(N-P)$.
- **Rouché's theorem:** if $f$ and $g$ are analytic on and inside a simple closed contour $C$ and $|f(z)|>|g(z)|$ on $C$, then $f$ and $f+g$ have the same number of zeros inside $C$, counted with multiplicity.

#### Common Formulas

1. **Argument principle, integral form:**

   $$\frac1{2\pi i}\oint_C\frac{f'(z)}{f(z)}\,dz=N-P.$$

2. **Argument principle, argument form:**

   $$\Delta_C\arg f(z)=2\pi(N-P).$$

3. **Residue of the logarithmic derivative at a zero:** if $z_0$ is a zero of $f$ of multiplicity $m$, then $\operatorname{Res}(f'/f,z_0)=m$.

4. **Residue of the logarithmic derivative at a pole:** if $z_0$ is a pole of $f$ of order $k$, then $\operatorname{Res}(f'/f,z_0)=-k$.

#### Solution Procedure: Counting Zeros with Rouché's Theorem

1. Compare $|f(z)|$ and $|g(z)|$ on the boundary $C$.
2. Select the dominant term $f(z)$, whose modulus is largest on the boundary.
3. Verify $|f(z)|>|g(z)|$ on $C$.
4. By Rouché's theorem, $f+g$ and $f$ have the same number of zeros inside $C$.
5. Count the zeros of $f(z)$ in $C$, with multiplicity, for the answer.

#### Proof of the Argument Principle

1. Examine the singularities of $f'/f$, which are exactly the zeros and poles of $f$.
2. Near a zero of multiplicity $m$, write $f(z)=(z-z_0)^mg(z)$ with $g(z_0)\ne0$. Then $f'/f=m/(z-z_0)+g'/g$, whose residue is $m$.
3. Near a pole of order $k$, write $f(z)=(z-z_0)^{-k}h(z)$ with $h(z_0)\ne0$. Then $f'/f=-k/(z-z_0)+h'/h$, whose residue is $-k$.
4. The residue theorem gives contour integral $=2\pi i(\sum m_i-\sum k_j)=2\pi i(N-P)$.

#### Proof of Rouché's Theorem via the Argument Principle

1. On $C$, both $f\ne0$ and $f+g\ne0$, because $|f|>|g|$.
2. Construct the homotopy $F_t(z)=f(z)+t\cdot g(z)$, $0\leq t\leq1$; $F_t\ne0$ on $C$.
3. $N(t)=\frac1{2\pi i}\oint_C F_t'/F_t$ is a continuous integer-valued function of $t$, hence constant.
4. Thus $N(0)=N(1)$, so $f$ and $f+g$ have the same number of zeros.
5. Alternatively, $|g/f|<1$ on $C$, so $1+g/f$ lies in the unit disk centered at $1$ and has argument variation $0$.

---

### Module 9: Classical Theorems

#### Liouville's Theorem

**Statement.** If $f$ is entire and bounded, meaning that there exists $M>0$ such that $|f(z)|\leq M$ for all $z\in\mathbb C$, then $f$ is constant.

**Proof outline.**

1. From the derivative form of Cauchy's integral formula,

   $$f'(z_0)=\frac1{2\pi i}\oint_{|z-z_0|=R}\frac{f(z)}{(z-z_0)^2}\,dz.$$

2. The ML estimate gives

   $$|f'(z_0)|\leq\frac1{2\pi}\cdot\frac{M}{R^2}\cdot2\pi R=\frac MR.$$

3. Letting $R\to\infty$ gives $f'(z_0)=0$.
4. Since $z_0$ is arbitrary, $f'(z)\equiv0$, hence $f$ is constant.

#### Maximum Modulus Principle

**Statement.** If $f$ is analytic and nonconstant in a region $D$, then $|f(z)|$ cannot attain a maximum at an interior point of $D$.

**Proof outline.**

1. By contradiction, suppose $|f|$ attains its maximum $M=|f(z_0)|$ at $z_0\in D$.
2. By the mean-value property of analytic functions,

   $$f(z_0)=\frac1{2\pi}\int_0^{2\pi}f(z_0+re^{i\theta})\,d\theta.$$

3. Taking moduli gives

   $$M=|f(z_0)|\leq\frac1{2\pi}\int_0^{2\pi}|f(z_0+re^{i\theta})|\,d\theta\leq M.$$

4. Equality forces $|f(z_0+re^{i\theta})|\equiv M$ for every $\theta$.
5. Since $r$ is arbitrary, the identity theorem implies $f$ is constant, a contradiction.

#### Fundamental Theorem of Algebra

**Statement.** Every nonconstant complex-coefficient polynomial $P(z)=a_nz^n+\cdots+a_0$, with $a_n\ne0$ and $n\geq1$, has at least one root over $\mathbb C$.

**Proof outline using Liouville's theorem.**

1. By contradiction, suppose $P(z)$ has no zero. Then $1/P(z)$ is entire.
2. Because $\lim_{|z|\to\infty}|P(z)|=\infty$ (the leading term dominates), there exists $R$ such that $|z|>R$ implies $|1/P(z)|<1$.
3. On the compact set $|z|\leq R$, $|1/P(z)|$ is continuous and hence bounded; thus $1/P(z)$ is bounded on $\mathbb C$.
4. Liouville's theorem makes $1/P(z)$ constant, so $P(z)$ is constant, a contradiction.

---

## General Problem-Solving Methodology

### 1. Problem Identification

| Problem feature | Corresponding module |
|---|---|
| “find $(\cdots)^n$,” “convert to standard form,” or a high power involving $\sqrt3+i$ | Module 1: complex-number operations and de Moivre's formula |
| “where is it analytic,” “determine analyticity,” or verify/prove C--R equations | Module 2: analytic functions and Cauchy--Riemann equations |
| “harmonic function,” “harmonic conjugate,” or $u_x,u_y$ | Module 2: harmonic functions |
| “use Cauchy's integral formula,” or $\oint$ containing $f(z)/(z-a)$ | Module 3: Cauchy's integral theory |
| “higher-order Cauchy,” or $\oint$ with $(z-a)^n$ in the denominator | Module 3: higher-derivative formula |
| “Laurent series” or “annular expansion” | Module 4: series expansions |
| “radius of convergence,” “power series,” and $\sum$ | Module 4: radius of convergence |
| “find the residue” or $\operatorname{Res}$ | Module 5: residue theory |
| Real integral $\int_{-\infty}^{\infty}$ plus a rational function | Module 6: contour integrals |
| $\int_0^{2\pi}$ plus trigonometric functions | Module 6: contour method for trigonometric integrals |
| “conformal mapping,” “Möbius transformation,” or “upper half-plane maps to” | Module 7: conformal mappings |
| “Rouché's theorem,” “number of zeros,” or $|z|<1$ | Module 8: applications of Rouché's theorem |
| “argument principle,” $N-P$, or “logarithmic derivative” | Module 8: argument principle |
| “Liouville” or “bounded entire function” | Module 9: Liouville's theorem |
| “maximum modulus” or “$|f(z)|$ attains a maximum” | Module 9: maximum modulus principle |
| “fundamental theorem of algebra” or “a polynomial has at least one root” | Module 9: fundamental theorem of algebra |

### 2. Method Selection

| Problem type | First-choice method | Alternative |
|---|---|---|
| High power of a complex number | polar form + de Moivre's formula | binomial expansion, for low powers |
| Determine analyticity | verify C--R equations + open-neighborhood argument | compute the derivative limit directly |
| Find a harmonic conjugate | successive integration of C--R equations | Milne--Thomson method |
| Compute a Cauchy integral | $\oint f/(z-a)=2\pi if(a)$ | direct parameterized integration |
| Compute a higher-order Cauchy integral | $\oint f/(z-a)^{n+1}=\frac{2\pi i}{n!}f^{(n)}(a)$ | expand and integrate term by term |
| Find a Laurent series | partial fractions + geometric-series expansion | direct coefficient formula $c_n$ |
| Find a radius of convergence | ratio test $R=\lim|a_n/a_{n+1}|$ | root test |
| Compute a residue | determine pole order + corresponding formula | Laurent expansion and read $c_{-1}$ |
| Real rational integral | sum of upper-half-plane residues | another contour |
| Trigonometric integral | substitution $z=e^{i\theta}$ | trigonometric-identity reduction |
| Infinite integral with $\cos x$ | construct $e^{iz}$ contour + take real part | simplify by parity |
| Determine a region mapping | boundary correspondence + test point | cross-ratio construction |
| Count zeros | Rouché's theorem with a dominant term | argument principle |
| Prove a complex-analysis theorem | kernel theorem (Cauchy integral / residue theorem) + inequality estimate | proof by contradiction |

### 3. Result Validation

- **Validation for de Moivre results:** $|z^n|=|z|^n$, and $\arg(z^n)$ agrees.
- **C--R validation:** $u_{xx}+u_{yy}=0$ and $v_{xx}+v_{yy}=0$.
- **Contour-integral validation:** a singularity contributes a nonzero integral only if it is inside the contour; if all singularities are outside, the integral is $0$.
- **Residue validation:** the sum of all finite isolated-singularity residues plus $\operatorname{Res}(f,\infty)$ equals $0$.
- **Real-integral validation:** check symmetry (the integral of an even function is $2\int_0^\infty$) and positivity (if the integrand is always positive, the integral is $>0$).
- **Radius-of-convergence validation:** for $|z|<R$ the series converges absolutely, and for $|z|>R$ it diverges.
- **Rouché validation:** on the boundary, verify the strict inequality $|f|>|g|$.
- **Independent SymPy validation:** independently check results of computational problems with SymPy.

---

## SymPy Verification Techniques

This section gives SymPy checking approaches usable during Python generation, covering complex-number operations, series expansions, residue calculations, and contour integrals. The problem statement remains the sole source of numerical data.

### Basic Complex-Number Operations

### de Moivre's Formula and High Powers of Complex Numbers

### Verification of the Cauchy--Riemann Equations

### Cauchy's Integral Formula

### Series Expansions and Radii of Convergence

### Residue Calculations

### Real-Integral Calculations (Residue Theorem)

### Fully Parameterized Verification Procedure

---

## Common Errors and Pitfalls

### Complex-Number Operations

1. **Ignoring the quadrant when computing an argument.** $\arctan(b/a)$ only gives a value in $(-\pi/2,\pi/2)$. When $a<0$, the argument should be $\arctan(b/a)+\pi$ (or $-\pi$); otherwise it differs by $\pi$. For example, $\sqrt3+i$ has argument $\pi/6$, but $-\sqrt3+i$ has argument $5\pi/6$, not $\arctan(-1/\sqrt3)\approx-\pi/6$.
2. **Forgetting the factor $r^n$ in de Moivre's formula.** $(re^{i\theta})^n=r^ne^{in\theta}$, not merely $e^{in\theta}$. Omitting $r^n$ is a common error.
3. **Incorrect simplification of the argument of a high power.** $e^{i\cdot n\theta}$ must be simplified to the principal-value range, usually $(-\pi,\pi]$ or $[0,2\pi)$. For example, $e^{i\pi}=-1$, rather than leaving $e^{i\pi}$ unevaluated.
4. **Confusing algebraic and polar forms.** Squaring gives $(a+bi)^2=a^2-b^2+2abi$, which contains no radical, while a polar-form result may contain trigonometric values. Both forms should be simplified consistently to $x+yi$.

### Analytic Functions and the Cauchy--Riemann Equations

5. **Confusing “satisfies C--R” with “is analytic.”** The C--R equations holding at a single point do not guarantee analyticity there. They must hold at every point of an open neighborhood and the partial derivatives of $u,v$ must be continuous there.
6. **A sign error in the imaginary-part C--R equation.** The correct equations are $u_x=v_y$ and $u_y=-v_x$. A frequent error is $u_y=v_x$, omitting the minus sign.
7. **Forgetting the special case $v=0$ when testing $|z|^2$ by C--R.** For $f(z)=|z|^2$, the imaginary part is identically $0$. Thus $u_x=v_y=0$ gives $2x=0$, and $u_y=-v_x=0$ gives $2y=0$, so C--R holds only at the origin. Analyticity requires an open neighborhood, so the function is analytic nowhere.
8. **Omitting the integration constant when finding a harmonic conjugate.** After integrating $v_y=u_x$ to get $v=\int u_x\,dy+\varphi(x)$, one must use $v_x=-u_y$ to determine $\varphi(x)$ and integrate to obtain the full constant.

### Cauchy's Integral Theory

9. **Confusing the coefficients in Cauchy's integral formula and higher-derivative formula.**

   $$\oint\frac{f(z)}{(z-a)^{n+1}}\,dz=\frac{2\pi i}{n!}f^{(n)}(a),$$

   not $\frac{2\pi i}{n}f^{(n)}(a)$ and not $2\pi if^{(n)}(a)$. Omitting $1/n!$ is common.
10. **Failing to verify that a singularity is inside the contour.** Both Cauchy's formula and its higher-derivative version require singularity $a$ to be inside the contour. If it is outside, the integral is $0$.
11. **Misapplying Cauchy's integral theorem.** It requires $f$ to be analytic on the contour and throughout its interior. If a singularity lies inside, one cannot directly conclude that the integral is $0$.

### Series Expansions

12. **Using the wrong direction for the expansion of $1/(1-z)$.** For $|z|<1$, $1/(1-z)=\sum_{n=0}^\infty z^n$; for $|z|>1$,

    $$\frac1{1-z}=-\frac1z\frac1{1-z^{-1}}=-\sum_{n=0}^\infty z^{-(n+1)}.$$

    Reversing the expansion direction makes the series divergent.
13. **Losing a sign after partial-fraction decomposition.**

    $$\frac1{z(z-1)}=\frac1{z-1}-\frac1z,\qquad \frac1{z-1}=-\frac1{1-z}=-\sum_{n=0}^\infty z^n.$$

    Missing this minus sign produces incorrect coefficients.
14. **Misusing the ratio test for the radius of convergence.** $R=\lim|a_n/a_{n+1}|$, with $a_n$ on top and $a_{n+1}$ below, not the reverse. The root test is $R=1/\limsup\sqrt[n]{|a_n|}$.

### Residue Theory and Contour Integration

15. **Misusing the simple-pole residue formula.** $\operatorname{Res}(f,z_0)=\lim_{z\to z_0}(z-z_0)f(z)$ applies only to a simple pole. A higher-order pole requires the derivative formula.
16. **Misidentifying pole order.** In $1/[z(z-1)^2]$, $z=0$ is a simple pole because $z$ occurs once in the denominator, while $z=1$ is a second-order pole because $(z-1)^2$ occurs. Confusing orders leads to use of the wrong residue formula.
17. **Omitting the factorial in the residue formula for an $m$th-order pole.**

    $$\operatorname{Res}(f,z_0)=\frac1{(m-1)!}\lim\frac{d^{m-1}}{dz^{m-1}}[(z-z_0)^mf(z)].$$

    Omitting $1/(m-1)!$ is common.
18. **Omitting the $dz/(iz)$ factor in the trigonometric-integral substitution.** $d\theta=dz/(iz)$, not $dz/z$ and not $iz\,dz$. Losing or reversing $i$ gives an incorrect integral.
19. **Not checking the degree condition in rational contour integrals.** For $\int_{-\infty}^{\infty}P(x)/Q(x)\,dx$, one needs $\deg Q\geq\deg P+2$ so that the large semicircular arc integral tends to $0$. If the difference is only $1$, Jordan's lemma or another method is needed.

### Conformal Mappings

20. **Skipping boundary verification for a Möbius transformation.** For $w=(z-i)/(z+i)$ and $z=x\in\mathbb R$,

    $$|w|=\frac{|x-i|}{|x+i|}=1$$

    because the numerator and denominator are conjugates. Without verifying this, the boundary correspondence is not established.
21. **Confusing the mapping directions of the upper and lower half-planes.** The same map $w=(z-i)/(z+i)$ maps the upper half-plane to the interior of the unit disk and the lower half-plane to the exterior. A test point is necessary to determine the direction.

### Classical Theorems

22. **Omitting part of the boundedness argument in Liouville's-theorem contradiction.** To prove the fundamental theorem of algebra, one must separately show $|1/P(z)|<1$ for $|z|>R$ and show $|1/P(z)|$ is bounded on $|z|\leq R$ by continuity. Omitting either argument cannot establish that the entire function is bounded.
23. **Misreading the equality condition in the proof of the maximum modulus principle.** In the inequality chain after applying the mean-value property, equality requires $|f(z_0+re^{i\theta})|\equiv M$ for every $\theta$, by the equality condition in the continuous triangle inequality, not merely at one point.
24. **Choosing the wrong dominant term in Rouché's theorem.** On $|z|=1$, compare $|z^8|=1$, $|3z^3|=3$, and $|1|=1$. One must choose $|3z^3|=3$ as $|f(z)|$, the largest modulus, and use the sum of the other terms as $|g(z)|$. A wrong choice cannot establish $|f|>|g|$.
25. **Omitting multiplicities of zeros and poles in the argument principle.** A zero of multiplicity $m$ contributes residue $m$, and a pole of order $k$ contributes residue $-k$. Counting multiplicities is a core requirement of the argument principle; omitting them makes $N-P$ wrong.

---

## Key Formula Quick Reference

### Complex-Number Operations

| Formula | Exact expression | Conditions |
|---|---|---|
| **Polar representation** | $z=r(\cos\theta+i\sin\theta)=re^{i\theta}$ | $r=|z|$, $\theta=\arg(z)$ |
| **de Moivre's formula** | $(re^{i\theta})^n=r^ne^{in\theta}$ | $n\in\mathbb Z$ |
| **Modulus properties** | $|z_1z_2|=|z_1||z_2|$, $|z^n|=|z|^n$ | arbitrary complex numbers |
| **Conjugation properties** | $\overline{z_1z_2}=\overline{z_1}\cdot\overline{z_2}$, $z\overline z=|z|^2$ | arbitrary complex numbers |

### Analytic Functions and the C--R Equations

| Formula | Exact expression | Conditions |
|---|---|---|
| **Cauchy--Riemann equations** | $u_x=v_y$, $u_y=-v_x$ | $f=u+iv$ differentiable at a point |
| **Laplace equations** | $u_{xx}+u_{yy}=0$, $v_{xx}+v_{yy}=0$ | $u,v$ are real/imaginary parts of an analytic function |
| **Derivative expression** | $f'(z)=u_x+iv_x=v_y-iu_y$ | at an analytic point |
| **General harmonic-conjugate expression** | $v=\int u_x\,dy-\int\left(u_y+\frac\partial{\partial x}\int u_x\,dy\right)dx$ | $u$ is harmonic |

### Cauchy's Integral Theory

| Formula | Exact expression | Conditions |
|---|---|---|
| **Cauchy's integral theorem** | $\oint_Cf(z)\,dz=0$ | $f$ analytic on $C$ and in its interior |
| **Cauchy's integral formula** | $f(a)=\frac1{2\pi i}\oint_C\frac{f(z)}{z-a}\,dz$ | $f$ analytic on and inside $C$, $a$ inside $C$ |
| **Higher-order Cauchy formula** | $f^{(n)}(a)=\frac{n!}{2\pi i}\oint_C\frac{f(z)}{(z-a)^{n+1}}\,dz$ | $f$ analytic on and inside $C$, $a$ inside $C$ |
| **ML estimate** | $\left|\oint_Cf(z)\,dz\right|\leq ML$ | $|f(z)|\leq M$; $L$ is the length of $C$ |

### Series Expansions

| Formula | Exact expression | Conditions |
|---|---|---|
| **Geometric series** | $\frac1{1-z}=\sum_{n=0}^\infty z^n$ | $|z|<1$ |
| **Geometric series, exterior** | $\frac1{1-z}=-\sum_{n=1}^\infty z^{-n}$ | $|z|>1$ |
| **Radius of convergence, ratio test** | $R=\lim_{n\to\infty}\left|\frac{a_n}{a_{n+1}}\right|$ | the limit exists |
| **Radius of convergence, root test** | $R=1/\limsup_{n\to\infty}\sqrt[n]{|a_n|}$ | general case |

### Residue Theory

| Formula | Exact expression | Conditions |
|---|---|---|
| **Residue theorem** | $\oint_Cf(z)\,dz=2\pi i\sum\operatorname{Res}(f,z_j)$ | $f$ analytic in $C$ except at $z_j$ |
| **Residue at a simple pole** | $\operatorname{Res}(f,z_0)=\lim_{z\to z_0}(z-z_0)f(z)$ | $z_0$ is a first-order pole |
| **Residue at a pole of order $m$** | $\operatorname{Res}(f,z_0)=\frac1{(m-1)!}\lim_{z\to z_0}\frac{d^{m-1}}{dz^{m-1}}[(z-z_0)^mf(z)]$ | $z_0$ is an $m$th-order pole |
| **Residue of $P/Q$ at a simple pole** | $\operatorname{Res}(P/Q,z_0)=P(z_0)/Q'(z_0)$ | $P(z_0)\ne0$, $Q(z_0)=0$, $Q'(z_0)\ne0$ |
| **Trigonometric-integral substitution** | $z=e^{i\theta}$, $d\theta=dz/(iz)$, $\cos\theta=(z+z^{-1})/2$ | $\theta\in[0,2\pi]$ |

### Conformal Mappings

| Formula | Exact expression | Mapping |
|---|---|---|
| **Upper half-plane to unit disk** | $w=(z-i)/(z+i)$ | $\mathbb H\to\mathbb D$ |
| **Unit disk to upper half-plane** | $w=i(1-z)/(1+z)$ (Cayley transform) | $\mathbb D\to\mathbb H$ |
| **General Möbius transformation** | $w=(az+b)/(cz+d)$ ($ad-bc\ne0$) | circles to circles; preserves symmetry |

---

## Standard Solutions for Computational Problems

### Type A: High Powers of Complex Numbers (de Moivre's Formula)

**Procedure:** polar form $re^{i\theta}$ $\to$ $(re^{i\theta})^n=r^ne^{in\theta}$ $\to$ convert back to algebraic form.

Example:

$$
(\sqrt3+i)^6=(2e^{i\pi/6})^6=64e^{i\pi}=-64.
$$

### Type B: Determining Analyticity

**Procedure:** separate $u(x,y)$ and $v(x,y)$ $\to$ compute partial derivatives $\to$ check the set where $u_x=v_y$ and $u_y=-v_x$ hold $\to$ decide whether they hold on an open neighborhood.

Example: for $f(z)=|z|^2$, $u=x^2+y^2$, $v=0$. The C--R equations yield $2x=0$, $2y=0$, so they hold only at the origin; hence $f$ is analytic nowhere.

### Type C: Cauchy's Integral Formula

**Procedure:** verify that $f$ is analytic and $a$ lies inside the contour $\to$ use $\oint f(z)/(z-a)\,dz=2\pi if(a)$.

Example:

$$
\oint_{|z|=1}\frac{e^z}{z}\,dz=2\pi i\cdot e^0=2\pi i.
$$

### Type D: Higher-Order Cauchy Integral Formula

**Procedure:** identify $n$ and $a$ $\to$ find $f^{(n)}(a)$ $\to$ use $\oint f(z)/(z-a)^{n+1}\,dz=\frac{2\pi i}{n!}f^{(n)}(a)$.

Example:

$$
\oint_{|z|=2}\frac{e^z}{(z-1)^3}\,dz.
$$

Here $n=2$, $f^{(2)}(z)=e^z$, and $f^{(2)}(1)=e$, so the result is $\pi ie$.

### Type E: Laurent-Series Expansion

**Procedure:** partial fractions $\to$ choose the geometric-series direction according to the annulus $\to$ combine positive and negative powers.

Example:

$$
\frac1{z(z-1)}=\frac1{z-1}-\frac1z=-\frac1{1-z}-\frac1z=-\sum_{n=0}^\infty z^n-\frac1z\qquad(0<|z|<1).
$$

### Type F: Residue Calculation

**Procedure:** determine the singularity type $\to$ use $\lim(z-z_0)f(z)$ for a simple pole; use the derivative formula for an $m$th-order pole.

Example: for $f=1/[z(z-1)^2]$, $z=0$ is a simple pole with $\operatorname{Res}=1$, and $z=1$ is a second-order pole with $\operatorname{Res}=-1$.

### Type G: Real Rational Integrals

**Procedure:** verify $\deg Q\geq\deg P+2$ $\to$ find upper-half-plane poles $\to$ compute residues $\to$ integral $=2\pi i\sum\operatorname{Res}$.

Example:

$$
\int_{-\infty}^{\infty}\frac{dx}{x^4+1}=2\pi i\cdot\sum_{\operatorname{Im}z_k>0}\frac1{4z_k^3}=\frac\pi{\sqrt2}.
$$

### Type H: Contour Method for Trigonometric Integrals

**Procedure:** substitute $z=e^{i\theta}$ $\to$ simplify to $\oint_{|z|=1}f(z)\,dz$ $\to$ find residues inside the unit circle $\to$ integral $=2\pi i\sum\operatorname{Res}$.

Example:

$$
\int_0^{2\pi}\frac{d\theta}{5+4\cos\theta}=2\pi i\cdot\frac1{3i}=\frac{2\pi}3.
$$

### Type I: Application of Rouché's Theorem

**Procedure:** compare the moduli of all terms on $C$ $\to$ select dominant $f(z)$ $\to$ verify $|f|>|g|$, with $g$ the sum of the remaining terms $\to$ count zeros of $f(z)$.

Example: on $|z|=1$, $|3z^3|=3>|z^8+1|\leq2$, so Rouché's theorem gives $3$ zeros.

### Type J: Determining a Region under a Conformal Map

**Procedure:** verify the boundary map $\to$ choose an interior test point $\to$ apply the boundary correspondence principle.

Example: for $w=(z-i)/(z+i)$, the real axis maps to $|w|=1$ and $z=i$ maps to $w=0\in\mathbb D$; hence the upper half-plane maps to the unit disk.

---

## Standard Strategies for Proof Problems

### Strategy 1: Limits Along Two Directions

Pattern: let $h$ tend to $0$ separately along the real and imaginary axes; the two limits must agree. Compare real and imaginary parts to derive the C--R equations.

### Strategy 2: Inequality Estimate plus a Limit

Pattern: write an integral representation of $f'$ via Cauchy's derivative formula $\to$ use the ML estimate to obtain $|f'|\leq M/R$ $\to$ let $R\to\infty$ to obtain $f'=0$ $\to$ conclude that $f$ is constant.

### Strategy 3: Contradiction plus the Mean-Value Property

Pattern: assume maximum modulus at an interior point $\to$ apply the mean-value property on a small circle $\to$ an inequality chain forces the modulus to be constant on that circle $\to$ the identity theorem yields a contradiction.

### Strategy 4: Contradiction plus Liouville's Theorem

Pattern: assume a polynomial has no root $\to$ $1/P$ is entire $\to$ prove $1/P$ is bounded $\to$ apply Liouville's theorem $\to$ contradiction.

### Strategy 5: Residue Analysis plus the Residue Theorem

Pattern: inspect singularities of $f'/f$, exactly the zeros and poles of $f$ $\to$ compute residues at zeros and poles as $m$ and $-k$ $\to$ sum using the residue theorem.

### Strategy 6: Homotopy Family plus the Argument Principle

Pattern: construct the homotopy $F_t=f+tg$ $\to$ $N(t)=\frac1{2\pi i}\oint F_t'/F_t$ is a continuous integer-valued function and hence constant $\to$ $N(0)=N(1)$.

---

## References

- Companion verification prompt: `Complex Analysis Verification Example.py`
- Dataset source: `Complex Analysis.md` (20 problems covering all core knowledge points)
- Recommended textbooks: *Complex Analysis* (Ahlfors), *Complex Analysis* (Stein--Shakarchi), and *Complex Functions and Integral Transforms*.
- Online tools: SymPy Live, SageMath, Wolfram Alpha.

---

## Competition Extension: Norm Equations in Imaginary Quadratic Fields and Complex Representations

### Core Concepts

Let $d>0$ be a square-free positive integer. Algebraic integers in the imaginary quadratic field $\mathbb Q(\sqrt{-d})$ have the form

$$
z=a+b\sqrt{-d}=a+bi\sqrt d\qquad(a,b\in\mathbb Z).
$$

Its **norm** is

$$
N(z)=z\overline z=a^2+db^2.
$$

The norm is multiplicative: $N(z_1z_2)=N(z_1)N(z_2)$.

### Norm Equations and Diophantine Equations

The norm equation $N(z)=n$ in an imaginary quadratic field is equivalent to the Diophantine equation

$$
a^2+db^2=n,
$$

where $a,b$ are integers when considering the ring of algebraic integers, or rationals when considering the field itself.

**Typical problem:** given $n$ and $d$, find all integer solutions $(a,b)$ satisfying $a^2+db^2=n$. In competitions this appears as a Pell-type equation or as a quadratic form representing an integer.

### Norm Equations from the Complex-Number Viewpoint

Embed the imaginary quadratic field into the complex plane by $\sqrt{-d}\leftrightarrow i\sqrt d$. Then $z=a+bi\sqrt d$ is a lattice point in the complex plane, with the imaginary axis scaled by $\sqrt d$:

$$
|z|^2=a^2+db^2=N(z).
$$

Thus $N(z)=n$ means that the squared distance from the lattice point $z$ to the origin is $n$.

**Factorization property.** If $n=n_1n_2$ and

$$
n_1=a_1^2+db_1^2,\qquad n_2=a_2^2+db_2^2,
$$

then $n$ also has the representation

$$
n=(a_1a_2-db_1b_2)^2+d(a_1b_2+a_2b_1)^2.
$$

This is exactly norm multiplicativity under complex multiplication:

$$
(a_1+b_1i\sqrt d)(a_2+b_2i\sqrt d)
=(a_1a_2-db_1b_2)+(a_1b_2+a_2b_1)i\sqrt d.
$$

### Common Competition Problem Types

1. **Uniqueness of a sum-of-squares representation:** discuss uniqueness of representations by $a^2+db^2$ in an imaginary quadratic field; it is related to class number.
2. **Counting integer solutions of a norm equation:** use the ring-of-integers structure of an imaginary quadratic field, especially the fact that $d=1,2,3$ yield principal ideal domains, to analyze existence and number of solutions.
3. **Roots of unity and symmetry:** the unit group of an imaginary quadratic field (units of $\mathbb Z[\sqrt{-d}]$) is restricted to $\pm1$ for $d\geq2$. Extra roots of unity occur only for $d=1$ (Gaussian integers) and $d=3$ (Eisenstein integers), affecting classification of solutions.

### Pitfalls

- **Confusing norm and modulus:** $N(a+b\sqrt{-d})=a^2+db^2$, whereas $|a+b\sqrt{-d}|=\sqrt{a^2+db^2}=\sqrt{N(z)}$. The norm is the square of the modulus.
- **The special case $d=1$:** the norm in the Gaussian integer ring $\mathbb Z[i]$ is $a^2+b^2$, equal to the usual squared complex modulus. For $d>1$, the coefficient $d$ stretches lattice points along the imaginary axis.
- **Nonunique factorization:** in an imaginary quadratic field of class number greater than $1$, the algebraic-integer ring is not a UFD, so norm equations need more careful analysis.

### Examination Techniques

- To decide whether $n$ can be represented as $a^2+db^2$, first check congruence conditions modulo $p$ (quadratic residues), then use norm multiplicativity under complex multiplication for factorization.
- Use the norm identity for complex conjugates to quickly validate a proposed solution: $N(z_1z_2)=N(z_1)N(z_2)$ can reduce higher-degree norm equations.
