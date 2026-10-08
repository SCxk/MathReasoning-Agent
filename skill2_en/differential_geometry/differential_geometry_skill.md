# Differential Geometry Skill

## Domain Boundaries and Routing Conventions

- Scope: arc lengths of curves and surfaces, Frenet frames, fundamental forms, curvature, geodesics, principal curvatures, and Gauss--Bonnet.
- Do not take over: elementary geometry involving triangles, circles, tangency, angle bisectors, and the like should be routed to non-foundational and advanced courses; a Laplacian restricted to a circle should be treated as a mathematical-analysis problem.
- Verification contract: first state the parametrization, metric, and normal orientation; then check sign conventions, regularity, and coordinate invariance.

## High-Frequency Errors and Convention Rules (Judge Feedback 2026-07-07)

- **Normal-curvature sign convention (mandatory):** the sign of normal curvature $\kappa_n=\mathrm{II}(w,w)/\mathrm{I}(w,w)$ depends on the selected unit normal. This problem set uses the **outward normal** for classical surfaces such as cylinders and spheres. For the cylinder $\mathbf r(u,v)=(\cos v,\sin v,u)$, take outward normal $\mathbf n=(\cos v,\sin v,0)$. Then $L=\mathbf r_{uu}\cdot\mathbf n=0$ and $N=\mathbf r_{vv}\cdot\mathbf n=-1$: along the $u$ direction (a straight generator), $\kappa_n=0$, while **along the $v$ direction (the circular direction), $\kappa_n=-1$** (the surface bends opposite to the outward normal, so the value is negative).
- If $\mathbf n=\mathbf r_u\times\mathbf r_v/|\mathbf r_u\times\mathbf r_v|$ produces the inward normal pointing toward the axis or sphere center, reverse the normal (equivalently, reverse the sign of the result) before reporting the answer.
- Gaussian curvature $K=\kappa_1\kappa_2$ is independent of normal choice. Mean curvature $H$ and a single directional $\kappa_n$ change sign when the normal is reversed. State the normal before giving a numerical answer.

---

## 1. Arc Length of a Curve

### Core Definitions and Theorems

**Arc length** is the most basic geometric quantity of a curve. For a parametrized curve $\mathbf r(t)=(x(t),y(t),z(t))$, $t\in[a,b]$, it is the integral of the norm of the tangent vector over the interval.

Arc-length parametrization (natural parametrization) is a core tool of differential geometry: when arc length $s$ is the parameter, the tangent vector is always a unit vector and the Frenet formulas have their simplest form.

### Core Formulas

| Case | Formula |
|---|---|
| Space curve $\mathbf r(t)$ | $L=\int_a^b|\mathbf r'(t)|\,dt$ |
| Plane curve $\mathbf r(t)=(x(t),y(t))$ | $L=\int_a^b\sqrt{x'(t)^2+y'(t)^2}\,dt$ |
| Arc-length parameter $s(t)$ | $s(t)=\int_{t_0}^t|\mathbf r'(\tau)|\,d\tau$ |

### Standard Step-by-Step Procedure

1. Compute the tangent vector $\mathbf r'(t)$.
2. Compute its norm $|\mathbf r'(t)|=\sqrt{x'(t)^2+y'(t)^2+z'(t)^2}$.
3. Integrate the norm on $[a,b]$.

### Frequent Examination Pitfalls

- Forgetting the square root: $|\mathbf r'|$ is the arithmetic square root of the sum of squares of the components.
- Ignoring absolute values in the integrand, for example when $\cos u$ changes sign on the integration interval.

### Examination Techniques

- Simplify the integrand before integrating; a common identity is $\sin^2t+\cos^2t=1$.
- The helix $(\cos t,\sin t,t)$ has arc length $\sqrt2$ times the interval length.

---

## 2. Curvature of a Plane Curve

### Core Definitions and Theorems

**Curvature** $\kappa$ measures the extent to which a curve departs from a straight line. Geometrically, it is the rate of change of the tangent-direction angle with respect to arc length, and the reciprocal of the osculating-circle radius.

### Core Formulas

| Case | Formula |
|---|---|
| Plane curve $\mathbf r(t)=(x(t),y(t))$ | $\kappa=|x'y''-x''y'|/(x'^2+y'^2)^{3/2}$ |
| Graph $y=f(x)$ | $\kappa=|f''(x)|/[1+(f'(x))^2]^{3/2}$ |
| Polar curve $r=r(\theta)$ | $\kappa=|r^2+2(r')^2-rr''|/[r^2+(r')^2]^{3/2}$ |

### Standard Step-by-Step Procedure

1. Compute $\mathbf r'(t)$ and $\mathbf r''(t)$.
2. Compute $\mathbf r'\times\mathbf r''$; in two dimensions this is the scalar cross product $x'y''-x''y'$.
3. Compute $|\mathbf r'|$.
4. Substitute in $\kappa=|\mathbf r'\times\mathbf r''|/|\mathbf r'|^3$.

### Frequent Examination Pitfalls

- For an arc-length-parametrized curve, $\kappa=|\mathbf r''(s)|$, but this simplification cannot be used directly for a general parametrization.
- The two-dimensional cross product is the scalar $x_1y_2-x_2y_1$; attend to its sign even though the final value is absolute.

### Examination Techniques

- A circle $(R\cos t,R\sin t)$ has constant curvature $1/R$, which is a checking benchmark.
- For a plane curve, $\kappa>0$ after taking the absolute value.

---

## 3. Frenet Frame and Unit Tangent Vector

### Core Definitions and Theorems

The **Frenet frame** $\{T,N,B\}$ is a moving orthogonal frame on a space curve:

- **unit tangent vector:** $T=\mathbf r'(t)/|\mathbf r'(t)|$;
- **principal normal vector:** $N=T'(t)/|T'(t)|$, pointing toward the center of curvature;
- **binormal vector:** $B=T\times N$.

$T,N,B$ form a right-handed orthogonal system and are fundamental for studying local properties of space curves.

### Core Formulas

- $T(t)=\mathbf r'(t)/|\mathbf r'(t)|$.
- $B(t)=[\mathbf r'(t)\times\mathbf r''(t)]/|\mathbf r'(t)\times\mathbf r''(t)|$.
- $N(t)=B(t)\times T(t)$.

### Standard Step-by-Step Procedure

1. Compute $\mathbf r'(t)$.
2. Compute $|\mathbf r'(t)|$.
3. Normalize to obtain $T=\mathbf r'(t)/|\mathbf r'(t)|$.
4. Substitute the specified parameter value.

### Frequent Examination Pitfalls

- Forgetting normalization and using $\mathbf r'(t)$ directly as the unit tangent vector.
- Computing $N$ requires differentiating $T'$ and normalizing it; one cannot merely normalize $\mathbf r''$.

### Examination Techniques

- The direction of $T$ depends only on the ratios of the components of $\mathbf r'(t)$, so one may substitute the parameter value before normalizing.
- In $(1,2,3)/\sqrt{14}$, the denominator is the norm and the numerator is the vector of $\mathbf r'$ components.

---

## 4. Curvature of a Space Curve

### Core Definitions and Theorems

The amount by which a space curve bends at a point is measured by its **curvature** $\kappa$. Unlike plane-curve curvature, it measures only bending magnitude and contains no torsion information.

### Core Formulas

| Case | Formula |
|---|---|
| General parametrization $\mathbf r(t)$ | $\kappa=|\mathbf r'(t)\times\mathbf r''(t)|/|\mathbf r'(t)|^3$ |
| Arc-length parameter $\mathbf r(s)$ | $\kappa=|\mathbf r''(s)|=|T'(s)|$ |
| Two-dimensional degeneration | $\kappa=|x'y''-x''y'|/(x'^2+y'^2)^{3/2}$ |

### Standard Step-by-Step Procedure

1. Compute $\mathbf r'(t)$ and $\mathbf r''(t)$.
2. Compute $\mathbf r'\times\mathbf r''$.
3. Compute $|\mathbf r'\times\mathbf r''|$.
4. Compute $|\mathbf r'(t)|$ and cube it.
5. Use $\kappa=|\mathbf r'\times\mathbf r''|/|\mathbf r'|^3$.

### Frequent Examination Pitfalls

- After a cross product, omitting a coefficient while taking the square root of its norm.
- Not attending to the signs of components of $\mathbf r''$, which affect the cross product.

### Examination Techniques

- Compute the cross product using $\det[\mathbf i,\mathbf j,\mathbf k;x',y',z';x'',y'',z'']$.
- The helix $(a\cos t,a\sin t,bt)$ has curvature $\kappa=a/(a^2+b^2)$.

---

## 5. Torsion

### Core Definitions and Theorems

**Torsion** $\tau$ measures the extent to which a space curve departs from a plane: it is the rotation rate of the binormal vector $B$ along the curve. $\tau\equiv0$ if and only if the curve is planar.

### Core Formulas

| Case | Formula |
|---|---|
| General parametrization $\mathbf r(t)$ | $\tau=(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''/|\mathbf r'\times\mathbf r''|^2$ |
| Arc-length parameter $\mathbf r(s)$ | $\tau=-B'(s)\cdot N(s)$ |

### Standard Step-by-Step Procedure

1. Compute $\mathbf r'(t)$, $\mathbf r''(t)$, and $\mathbf r'''(t)$ in sequence.
2. Compute $\mathbf r'\times\mathbf r''$.
3. Compute the scalar triple product $(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''$.
4. Compute $|\mathbf r'\times\mathbf r''|^2$.
5. Use $\tau=(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''/|\mathbf r'\times\mathbf r''|^2$.

### Frequent Examination Pitfalls

- Confusing the scalar triple product in the numerator with the norm of the cross product in the denominator.
- Forgetting signs in $\mathbf r'''$; third derivatives of sine and cosine are especially error-prone.

### Examination Techniques

- The helix $(a\cos t,a\sin t,bt)$ has torsion $\tau=b/(a^2+b^2)$.
- If $\mathbf r'''=0$, as for a polynomial of degree at most two, torsion is necessarily zero.
- Constant curvature and torsion, as for a helix, form the simplest practical verification model.

---

## 6. First Fundamental Form

### Core Definitions and Theorems

The **first fundamental form** (metric form) defines the inner-product structure on a surface and is used to calculate lengths of curves on the surface, angles, and surface area.

$$
I=ds^2=E\,du^2+2F\,du\,dv+G\,dv^2,
$$

where $E=\mathbf r_u\cdot\mathbf r_u$, $F=\mathbf r_u\cdot\mathbf r_v$, and $G=\mathbf r_v\cdot\mathbf r_v$.

### Core Formulas

- $E=\mathbf r_u\cdot\mathbf r_u$.
- $F=\mathbf r_u\cdot\mathbf r_v$.
- $G=\mathbf r_v\cdot\mathbf r_v$.
- Area element $dA=\sqrt{EG-F^2}\,du\,dv$.

### Standard Step-by-Step Procedure

1. Compute partial-derivative vectors $\mathbf r_u=\partial\mathbf r/\partial u$ and $\mathbf r_v=\partial\mathbf r/\partial v$.
2. Take inner products to obtain $E,F,G$.
3. Write $ds^2=E\,du^2+2F\,du\,dv+G\,dv^2$.

### Frequent Examination Pitfalls

- $F$ may be zero for an orthogonal parametrization, but do not assume this in advance.
- Do not omit the square on $\cos u$ in $G$.
- In a spherical parametrization, $E$ and $G$ have consistent dimensions but different forms.

### Examination Techniques

- In an orthogonal parametrization, $F=0$, substantially reducing computation.
- For the sphere, the first fundamental form has $E=R^2$, $F=0$, $G=R^2\cos^2u$.

---

## 7. Second Fundamental Form

### Core Definitions and Theorems

The **second fundamental form** describes how a surface departs from its tangent plane at a point: its manner of bending.

$$
II=L\,du^2+2M\,du\,dv+N\,dv^2,
$$

where $L=\mathbf r_{uu}\cdot\mathbf n$, $M=\mathbf r_{uv}\cdot\mathbf n$, $N=\mathbf r_{vv}\cdot\mathbf n$, and $\mathbf n$ is a unit normal.

### Core Formulas

- $\mathbf n=(\mathbf r_u\times\mathbf r_v)/|\mathbf r_u\times\mathbf r_v|$.
- $L=\mathbf r_{uu}\cdot\mathbf n$.
- $M=\mathbf r_{uv}\cdot\mathbf n$.
- $N=\mathbf r_{vv}\cdot\mathbf n$.

### Standard Step-by-Step Procedure

1. Compute $\mathbf r_u,\mathbf r_v$.
2. Compute the unit normal $\mathbf n=(\mathbf r_u\times\mathbf r_v)/|\mathbf r_u\times\mathbf r_v|$.
3. Compute $\mathbf r_{uu},\mathbf r_{uv},\mathbf r_{vv}$.
4. Dot each with $\mathbf n$ to obtain $L,M,N$.

### Frequent Examination Pitfalls

- Forgetting to normalize the normal vector and using $\mathbf r_u\times\mathbf r_v$ directly.
- Skipping $\mathbf r_{uv}$ by assuming the mixed partial is zero when it is not.
- **Conflict between normal orientation and face visibility:** for a convex-polyhedron visibility problem, face visibility is fundamentally the sign of the dot product of a normal and viewing direction. Face $F$ is visible in viewing direction $\mathbf v$ if and only if $\mathbf n_F\cdot\mathbf v<0$, where the outward normal points toward the observer. If a local surface normal disagrees with the polyhedron's global outward normal, the visibility decision is completely reversed.
- **Misapplication of the normal-vector separation theorem:** two visible faces of a convex polyhedron are strictly separated in normal-vector space by some hyperplane through the origin, but this conclusion holds only for closed convex polyhedra. If a surface has a “concave angle,” whose inward-normal component is nonmonotone in some direction, separation fails and the conclusion cannot be applied directly.

### Examination Techniques

- If $\mathbf r_u$ and $\mathbf r_v$ are orthogonal, normal-vector calculation simplifies.
- For the cylinder $(R\cos v,R\sin v,u)$, $L=0$, $M=0$, $N=R$.
- **Quick determination of normal sign convention:** $\mathbf r_u\times\mathbf r_v$ supplies the normal induced by parametrization, but the sign in local differential geometry depends on the problem. For a closed surface such as a sphere, the outward normal makes $K>0$ correspond to local strict convexity at an elliptic point; an inward normal reverses the entire second fundamental form. If normal-vector separation or convexity is involved, establish whether the normal is inward or outward before subsequent calculation.
- **Normal criterion for convex-polyhedron face visibility:** given viewing direction $\mathbf v$, a face $F$ of a convex polyhedron is visible iff $\mathbf n_F\cdot\mathbf v<0$, with the outward normal on the observer side. It extends to tangent-plane visibility of a smooth convex surface: for a local parametrization $\mathbf r(u,v)$ with outward normal, $(u,v)$ is visible in direction $\mathbf v$ iff $\mathbf n(u,v)\cdot\mathbf v<0$. First calculate the normal field, then check that its chosen orientation agrees with the “outward” or “inward” direction stated in the problem.

---

## 8. Normal Curvature

### Core Definitions and Theorems

**Normal curvature** $\kappa_n$ measures the bending of a surface in a specified tangent direction. It is the projection onto the normal vector of the curvature of the section curve of the surface in that direction.

### Core Formulas

- $\kappa_n=II/I=(L\,du^2+2M\,du\,dv+N\,dv^2)/(E\,du^2+2F\,du\,dv+G\,dv^2)$.
- Along the $u$ direction ($dv=0$), $\kappa_n=L/E$.
- Along the $v$ direction ($du=0$), $\kappa_n=N/G$.

### Standard Step-by-Step Procedure

1. Compute coefficients of the first and second fundamental forms in the given direction.
2. Determine the direction ratio $du:dv$.
3. Substitute into $\kappa_n=II/I$.

### Frequent Examination Pitfalls

- Confusing normal curvature with principal curvature: normal curvature depends on direction, while principal curvatures are extrema.
- Sign conventions differ among textbooks.

### Examination Techniques

- A generator of a ruled surface has normal curvature zero.
- The normal curvature in a circular-section direction equals one of the principal curvatures.

---

## 9. Gaussian Curvature

### Core Definitions and Theorems

**Gaussian curvature** $K$ is the most important intrinsic quantity in surface geometry. $K=\kappa_1\kappa_2$, the product of the two principal curvatures.

Gauss's Theorema Egregium states that Gaussian curvature is determined solely by the first fundamental form, so it is intrinsic.

### Core Formulas

- $K=(LN-M^2)/(EG-F^2)$, using fundamental-form coefficients.
- $K=\kappa_1\kappa_2$, using principal curvatures.
- A developable surface is characterized by $K\equiv0$.

### Standard Step-by-Step Procedure

1. Compute $E,F,G$.
2. Compute $L,M,N$.
3. Substitute into $K=(LN-M^2)/(EG-F^2)$.

### Frequent Examination Pitfalls

- Omitting the denominator $EG-F^2$, which is the square of the area element.
- The sign of $LN-M^2$ determines the local surface type.

### Examination Techniques

- $K>0$: elliptic point (locally convex); $K<0$: hyperbolic point (saddle); $K=0$: parabolic or flat point.
- A cylinder has $K=0$; a sphere has $K=1/R^2$, constantly positive.

---

## 10. Mean Curvature and Minimal Surfaces

### Core Definitions and Theorems

The **mean curvature** is $H=(\kappa_1+\kappa_2)/2$, the arithmetic mean of the principal curvatures.

A **minimal surface** has mean curvature identically zero. The catenoid and helicoid are classical minimal surfaces.

### Core Formulas

- $H=(EN-2FM+GL)/[2(EG-F^2)]$.
- Minimal-surface condition: $H=0\Longleftrightarrow LG-2MF+NE=0$.
- $H=(\kappa_1+\kappa_2)/2$.

### Standard Step-by-Step Procedure

1. Compute coefficients of both fundamental forms.
2. Substitute into $H=(EN-2FM+GL)/[2(EG-F^2)]$.
3. Simplify to see whether it is zero.

### Frequent Examination Pitfalls

- Treating $EN-2FM+GL$ as the numerator while forgetting the denominator.
- Ignoring the possibility that $F$ and $M$ are nonzero.

### Examination Techniques

- To verify a minimal surface, use $LG-2MF+NE=0$ and avoid denominator computations.
- The catenoid $\mathbf r=(\cosh u\cos v,\cosh u\sin v,u)$ is the standard minimal-surface example.

---

## 11. Surface Area

### Core Definitions and Theorems

Surface area is calculated by integrating the area element from the first fundamental form.

### Core Formulas

- $dA=\sqrt{EG-F^2}\,du\,dv$.
- $A=\iint_D\sqrt{EG-F^2}\,du\,dv$.

### Standard Step-by-Step Procedure

1. Compute $E,F,G$.
2. Compute $\sqrt{EG-F^2}$.
3. Determine parameter domain $D$.
4. Perform the double integral.

### Frequent Examination Pitfalls

- Using the wrong parameter range: for the sphere, $u\in[-\pi/2,\pi/2]$, not $[0,\pi]$.
- Forgetting that $\cos u\geq0$ on $[-\pi/2,\pi/2]$, so no absolute value is required.

### Examination Techniques

- Sphere area $4\pi R^2$ is a checking benchmark.
- Integrate the simpler variable first, usually $v$ before $u$.
- **Parameter-scan method for an area-bisecting line:** for a convex polygon with counterclockwise vertices $P_1,P_2,\ldots,P_n$ and total area $A$, parametrize all area-bisecting rays through vertex $P_i$ as $P_i+\lambda(\cos\theta,\sin\theta)$ with $\lambda\geq0$. Calculate the swept area $S(\theta)$ of the segment inside the polygon. As $\theta$ increases monotonically, $S(\theta)$ varies continuously over an interval, so there is a unique $\theta$ satisfying $S(\theta)=A/2$. This angle-scan parametrization plus the intermediate-value theorem avoids complicated analytic integration.
- **Symmetry of boundary-hit distributions:** an area-bisecting line of a convex polygon that does not pass through a vertex has boundary hits on two pairs of edges with symmetric area-splitting ratios. For convex polygon $Q$ and direction $\mathbf d$, all area-bisecting lines parallel to that direction form a parallel family; their boundary hits are determined by solving $A$ (area to the left of the secant) $=A/2$. When the polygon is axially symmetric, the boundary-hit distribution has corresponding symmetry, greatly reducing enumeration.
- **Symmetry simplification for surface-area elements:** for rotationally symmetric surfaces, such as a torus or sphere, first fix the symmetry direction, usually the $v$ integral, simplify the integrand, then handle the monotone direction. $\sqrt{EG-F^2}$ is often constant in the symmetry direction.

---

## 12. Geodesics and Geodesic Curvature

### Core Definitions and Theorems

A **geodesic** is the “straightest” curve on a surface: its geodesic curvature satisfies $\kappa_g\equiv0$. Great circles on a sphere and helices on a cylinder are geodesics.

**Geodesic curvature** $\kappa_g$ is the length of the projection of a curve's curvature vector onto the tangent plane of the surface.

### Core Formulas

- Geodesic equation: $\kappa_g=0$.
- $\kappa_g=|(\mathbf r'\times\mathbf r'')\cdot\mathbf n|/|\mathbf r'|^3$, the geodesic-curvature formula for a curve on a surface.

### Standard Step-by-Step Procedure

1. Verify that the curve lies on the surface.
2. Compute $\mathbf r'$, $\mathbf r''$, and the surface normal $\mathbf n$.
3. Compute $\kappa_g$ or decide whether it is zero.

### Frequent Examination Pitfalls

- Zero geodesic curvature does not mean zero curve curvature: a great circle has nonzero curvature in space but zero geodesic curvature on the sphere.
- Geodesic $\ne$ shortest path: a locally shortest path is geodesic, but a geodesic is not necessarily shortest.

### Examination Techniques

- Every great circle, the intersection of the sphere with a plane through its center, is a geodesic.
- When verifying a geodesic equation is difficult, use symmetry.

---

## 13. Principal Curvatures

### Core Definitions and Theorems

**Principal curvatures** $\kappa_1,\kappa_2$ are the extrema of normal curvature in the two principal directions. They satisfy $K=\kappa_1\kappa_2$ and $H=(\kappa_1+\kappa_2)/2$.

An **umbilic** is a point where $\kappa_1=\kappa_2$; every point on a sphere is umbilic.

### Core Formula

Solve

$$
(EG-F^2)\kappa^2-(EN-2FM+GL)\kappa+(LN-M^2)=0,
$$

or find eigenvalues of the Weingarten transformation matrix.

### Standard Step-by-Step Procedure

1. Compute fundamental-form coefficients.
2. Construct the quadratic equation in $\kappa$.
3. Solve to obtain $\kappa_1,\kappa_2$.
4. Verify $K=\kappa_1\kappa_2$ and $H=(\kappa_1+\kappa_2)/2$.

### Frequent Examination Pitfalls

- Forgetting that the quadratic coefficient $(EG-F^2)$ need not be $1$.
- Confusing eigenvector directions with coordinate-line directions when they differ.

### Examination Techniques

- At an umbilic, every direction is principal.
- Prefer the formula for computing principal curvatures rather than directly solving a quadratic equation.

---

## 14. Asymptotic Lines and Hyperbolic Points

### Core Definitions and Theorems

An **asymptotic direction** is a tangent direction with zero normal curvature. An **asymptotic curve** has an asymptotic direction as its tangent at every point.

A **hyperbolic point** ($K<0$) has two distinct asymptotic directions; an **elliptic point** ($K>0$) has no real asymptotic direction; a **parabolic point** ($K=0$) has one asymptotic direction.

### Core Formulas

- Asymptotic-direction condition: $L\,du^2+2M\,du\,dv+N\,dv^2=0$.
- Hyperbolic-point criterion: $LN-M^2<0\Longleftrightarrow K<0$.

### Standard Step-by-Step Procedure

1. Compute $L,M,N$.
2. Write $L\,du^2+2M\,du\,dv+N\,dv^2=0$.
3. Solve for the ratio $du:dv$.

### Frequent Examination Pitfalls

- Confusing the first and second fundamental forms.
- An asymptotic direction is a tangent direction, not a curve on the surface.

### Examination Techniques

- At the origin of hyperbolic paraboloid $z=x^2-y^2$, $K=-4$ and asymptotic directions are $du=\pm dv$.
- Use symmetry to obtain asymptotic directions quickly.

---

## 15. Torsion and the Planar-Curve Test

### Core Definitions and Theorems

A curve is planar if and only if $\tau\equiv0$. Geometrically, its binormal $B$ is constant and the curve lies entirely in its osculating plane.

### Core Formulas

- $\tau\equiv0\Rightarrow$ the curve is planar.
- Determine a plane equation from three noncollinear points on the curve, or from a relation among the components of $\mathbf r(t)$.

### Standard Step-by-Step Procedure

1. Compute $\mathbf r'(t)$, $\mathbf r''(t)$, and $\mathbf r'''(t)$.
2. Compute $\tau=(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''/|\mathbf r'\times\mathbf r''|^2$.
3. If $\tau\equiv0$, observe or solve for a linear relation $ax+by+cz=d$ valid for every point.

### Frequent Examination Pitfalls

- Verifying torsion is zero at only one point rather than at all points.
- For a polynomial curve, $\mathbf r'''=0$ but $\mathbf r'\times\mathbf r''$ may also vanish, producing a degenerate case.

### Examination Techniques

- If $\mathbf r'''\equiv0$ and $\mathbf r'\times\mathbf r''$ is not identically zero, then $\tau\equiv0$ follows.
- Find three noncollinear points of the curve to determine its plane.

---

## 16. Frenet--Serret Formulas

### Core Definitions and Theorems

The Frenet--Serret formulas are the central differential equations of space-curve theory:

$$
T'=\kappa N,\qquad N'=-\kappa T+\tau B,\qquad B'=-\tau N.
$$

For arc-length parameter $s$:

- $T'(s)=\kappa(s)N(s)$.
- $N'(s)=-\kappa(s)T(s)+\tau(s)B(s)$.
- $B'(s)=-\tau(s)N(s)$.

### Standard Step-by-Step Procedure

1. Verify $|\mathbf r'(s)|=1$ to confirm arc-length parametrization.
2. Use $\kappa=|\mathbf r''(s)|$.
3. Take $T=\mathbf r'$, $N=\mathbf r''/\kappa$, $B=T\times N$.
4. Use $\tau=(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''/\kappa^2$.

### Frequent Examination Pitfalls

- These formulas apply only to arc-length parameters; a general parameter must first be transformed.
- Sign mnemonic: $N'$ contains $-\kappa T$ and $+\tau B$.

### Examination Techniques

- For arc-length helix $(a\cos s,a\sin s,bs)$, $\kappa=a$ and $\tau=b$ when $a^2+b^2=1$.
- Mnemonic: $T$ turns toward $N$; $N$ turns back toward $T$ and toward $B$; $B$ turns back toward $N$.

---

## 17. Developable Surfaces

### Core Definitions and Theorems

A **developable surface** is a ruled surface with Gaussian curvature identically zero. It can be unfolded into a plane without changing the metric.

The three classes are cylinders, cones, and tangent surfaces of space curves.

### Core Formulas

- Developable $\Longleftrightarrow K\equiv0$.
- Developable $\Longleftrightarrow$ locally isometric to a plane.

### Standard Step-by-Step Procedure

1. Compute $E,F,G$ and $L,M,N$.
2. Compute $K=(LN-M^2)/(EG-F^2)$.
3. Verify $K=0$.

### Frequent Examination Pitfalls

- A ruled surface need not be developable: a one-sheet hyperboloid is ruled but not developable.
- Calling a surface developable from $K=0$ additionally requires that it be ruled.

### Examination Techniques

- Cylinders and cones are typical developable surfaces.
- $LN-M^2=0$ shows Gaussian curvature is zero.

---

## 18. Isometries

### Core Definitions and Theorems

An **isometry** between surfaces preserves lengths of curves. A **local isometry** exists exactly when parametrizations can be found with identical first fundamental forms.

An isometry preserves Gaussian curvature, by Gauss's Theorema Egregium.

### Core Formulas

- Isometry $\Longleftrightarrow E_1=E_2$, $F_1=F_2$, $G_1=G_2$ under suitable parametrizations.
- Isometry $\Rightarrow K_1=K_2$, but not conversely.

### Standard Step-by-Step Procedure

1. Compute first-fundamental-form coefficients for both surfaces.
2. Compare whether a parametrization can make the $E,F,G$ coefficients identical.
3. Draw the conclusion.

### Frequent Examination Pitfalls

- An isometry does not preserve the second fundamental form: bending can change while metric does not.
- Global isometry is more restrictive than local isometry.

### Examination Techniques

- A plane and a cylinder are locally isometric, both expressible as $du^2+dv^2$.
- Rolling paper into a cylinder is an actual example of an isometry.

---

## 19. Gauss--Bonnet Theorem

### Core Definitions and Theorems

The Gauss--Bonnet theorem is one of the deepest theorems of differential geometry. It connects surface curvature to topology:

$$
\iint_DK\,dA+\int_{\partial D}\kappa_g\,ds+\sum(\pi-\text{interior angle})=2\pi\chi(D),
$$

where $\chi(D)$ is the Euler characteristic of region $D$.

### Core Formulas

- For a spherical triangle bounded by three great-circle arcs,

  $$S=R^2(\alpha+\beta+\gamma-\pi).$$

- Gaussian curvature of a sphere: $K=1/R^2$, constant.

### Standard Step-by-Step Procedure

1. Determine region $D$ and its boundary.
2. Compute all components: $\iint K\,dA$, $\int\kappa_g\,ds$, and turning-angle terms.
3. Substitute into Gauss--Bonnet to solve the unknown.

### Frequent Examination Pitfalls

- Exterior angle equals $\pi-$ interior angle; do not confuse interior and exterior angles.
- Spherical-triangle sides are great-circle arcs (geodesics), so their geodesic curvature is zero.

### Examination Techniques

- The spherical-triangle area formula $S=R^2(\alpha+\beta+\gamma-\pi)$ is frequently tested.
- A spherical equilateral triangle with $\alpha=\beta=\gamma=\pi/2$ occupies $1/8$ of the sphere's area.
- **Gauss--Bonnet compatibility of congruent triangular subdivisions:** if a surface is subdivided into congruent spherical triangles, Gauss--Bonnet applied to each one gives $K\cdot S_i+$ boundary terms $=\pi(\alpha_i+\beta_i+\gamma_i-\pi)$. Since congruence makes every $S_i$ and angle equal, the global integral reduces to algebraic counting. With $f$ faces, $e$ edges, $v$ vertices, and $k$ edges per face, $kf=2e$. Combining this with total vertex angle $2\pi v=\sum(\alpha+\beta+\gamma)\cdot f/k$ can solve for the angles required of congruent triangles and decide whether such a subdivision can exist on a surface of given curvature.
- **Curvature constraint for circumscribed-polygon compatibility:** if a convex polygon can be “circumscribed” on a surface, meaning all vertices are on the surface and the image consists of geodesic segments, its angle sum $\sum\alpha_i$ must be compatible with Gauss--Bonnet. Along geodesic boundary segments, $\kappa_g=0$, so only exterior angles contribute. For clockwise circumscription, their total is $2\pi-\sum\alpha_i$, giving the necessary compatibility condition

  $$\iint_DK\,dA=2\pi-\sum\alpha_i,$$

  which can rule out impossible circumscribed polygons.

---

## 20. Minimal-Surface Test

### Core Definitions and Theorems

A **minimal surface** has mean curvature identically zero, $H\equiv0$. Physically it is the shape of a soap film.

### Core Formulas

| Condition | Expression |
|---|---|
| $H=0$ | $(EN-2FM+GL)/[2(EG-F^2)]=0$ |
| Equivalent condition | $LG-2MF+NE=0$ |

### Standard Step-by-Step Procedure

1. Compute $E,F,G,L,M,N$.
2. Substitute into and simplify $LG-2MF+NE$.
3. Verify that the result is zero.

### Frequent Examination Pitfalls

- Checking a single point is insufficient; $H\equiv0$ must hold over the whole surface.
- In $LG-2MF+NE=0$, the coefficients of $M$ and $F$ are **$-2$**.

### Examination Techniques

- Prefer $LG-2MF+NE=0$ to avoid complicated division.
- Catenoids and helicoids are classical minimal surfaces.
- **Constrained optimization and quadrilateral area:** quadrilateral area

  $$S=\frac12d_1d_2\sin\theta$$

  with diagonal lengths $d_1,d_2$ and diagonal angle $\theta$ bridges differential geometry and constrained optimization. Under constraints on side lengths, angles, or diagonals, maximizing area is a trigonometric constrained-extremum problem. If both diagonal lengths are fixed, $\sin\theta$ is maximal at $\theta=\pi/2$, so area is maximal when diagonals are perpendicular; under side-length constraints they may not always be perpendicular, requiring Lagrange multipliers.
- **Variational geometric intuition:** a minimal-surface problem is the zero variation $\delta A=0$ of the area functional

  $$A[\mathbf r]=\iint\sqrt{EG-F^2}\,du\,dv.$$

  Maximizing quadrilateral area is a constrained area variation that can be regarded as a discrete minimal-surface problem under boundary conditions. First discretize the continuous Euler--Lagrange equation into algebraic constraints on diagonals, then solve the optimal angle numerically or analytically.
- **Orthogonalization criterion for the diagonal angle:** under extra constraints such as prescribed side lengths, Brahmagupta's formula

  $$S=\sqrt{(s-a)(s-b)(s-c)(s-d)}$$

  gives a quick reference area only for a cyclic quadrilateral. For a general quadrilateral, use Bretschneider's formula

  $$S=\sqrt{(s-a)(s-b)(s-c)(s-d)-abcd\cos^2\frac{A+C}{2}}.$$

  When the diagonals are perpendicular there is further simplification, which can serve as a necessary optimality condition in constrained optimization.

---

## Problem-Type Identification

| Problem feature | Knowledge point | Preferred tool |
|---|---|---|
| Arc length or length | arc-length calculation | integrate $|\mathbf r'|$ |
| Curvature $\kappa$ | curvature formula | $|\mathbf r'\times\mathbf r''|/|\mathbf r'|^3$ |
| Torsion $\tau$ | torsion formula | $(\mathbf r'\times\mathbf r'')\cdot\mathbf r'''/|\mathbf r'\times\mathbf r''|^2$ |
| Tangent/normal/binormal | Frenet frame | normalize $\mathbf r'$, cross product |
| $E,F,G$ | first fundamental form | $\mathbf r_u\cdot\mathbf r_u$, etc. |
| $L,M,N$ | second fundamental form | $\mathbf r_{uu}\cdot\mathbf n$, etc. |
| Normal curvature | normal-curvature formula | $II/I$ |
| Gaussian curvature $K$ | Gaussian curvature | $(LN-M^2)/(EG-F^2)$ |
| Mean curvature $H$ | mean curvature | $(EN-2FM+GL)/[2(EG-F^2)]$ |
| Area | surface area | $\iint\sqrt{EG-F^2}$ |
| Minimal-surface test | $H=0$ | $LG-2MF+NE=0$ |
| Geodesic problem | geodesic curvature | $\kappa_g=0$ |
| Principal-curvature problem | principal-curvature equation | quadratic-equation method |
| Asymptotic direction | asymptotic curve | $Ldu^2+2Mdu\,dv+Ndv^2=0$ |
| Developable surface | $K=0$ | $LN-M^2=0$ |
| Isometry | first fundamental form | compare $E,F,G$ |
| Spherical triangle | Gauss--Bonnet | $S=R^2(\alpha+\beta+\gamma-\pi)$ |

### Choice of Solution Tools

1. **Vector method:** for curves, prioritize vector cross products and dot products.
2. **Parametrization:** for surfaces, complete the parametrization before computing partial derivatives.
3. **Orthogonalization:** seek an orthogonal parametrization, making $F=0$ and simplifying computation.
4. **Symmetry:** exploit surface symmetry to reduce computation.

### Result-Validation Ideas

1. **Dimensional check:** curvature has dimension $1/\text{length}$, arc length has dimension length, and area has dimension length$^2$.
2. **Special-value validation:** compare with known results in degenerate cases.
3. **Sign consistency:** the sign of $K$ should qualitatively agree with the surface shape.
4. **Classical-formula validation:** for a helix, $\kappa=a/(a^2+b^2)$ and $\tau=b/(a^2+b^2)$.

---

## 22. Exercise Index

| No. | Knowledge point | Problem summary | Difficulty | Type |
|---:|---|---|---|---|
| 0 | Curve arc length | arc length of helix $(\cos t,\sin t,t)$ | Easy | Computation |
| 1 | Plane-curve curvature | curvature of a circle, $1/R$ | Easy | Computation |
| 2 | Frenet frame | unit tangent of $(t,t^2,t^3)$ | Easy | Computation |
| 3 | Space-curve curvature | curvature of $(t,t^2/\sqrt2,t^3/3)$ at $t=1$ | Medium | Computation |
| 4 | Torsion | torsion of $(a\cos t,a\sin t,bt)$ | Medium | Computation |
| 5 | First fundamental form | $E,F,G$ of a sphere | Medium | Computation |
| 6 | Second fundamental form | $L,M,N$ of a cylinder | Medium | Computation |
| 7 | Normal curvature | normal curvature of a cylinder along $u/v$ directions | Medium | Computation |
| 8 | Gaussian curvature | Gaussian curvature of a torus | Medium | Computation |
| 9 | Mean curvature | mean curvature $H=0$ of a catenoid | Medium | Computation |
| 10 | Surface area | sphere area $4\pi R^2$ | Medium | Computation |
| 11 | Geodesics | geodesic curvature of a great circle | Medium | Analysis |
| 12 | Principal curvatures | principal curvatures of an elliptic paraboloid at the origin | Hard | Computation |
| 13 | Asymptotic lines | asymptotic directions of a hyperbolic paraboloid | Hard | Computation |
| 14 | Torsion and planar curves | verify $\tau=0$ and find a plane equation | Easy | Proof |
| 15 | Frenet--Serret formulas | $\kappa,\tau$ of a unit-speed helix | Medium | Proof |
| 16 | Developable surfaces | cylinder $K=0$ | Medium | Proof |
| 17 | Isometry | local isometry between plane and cylinder | Medium | Analysis |
| 18 | Gauss--Bonnet theorem | spherical-triangle area formula | Hard | Proof |
| 19 | Minimal-surface test | catenoid $LG-2MF+NE=0$ | Hard | Proof |

*This manual covers core differential-geometry knowledge for coursework and competition preparation. All formulas and conclusions can be verified in the 20 companion exercises.*

## General Supplement: Laplace Operator Restricted to a Curve

1. First distinguish the Euclidean Laplacian of the ambient space from the Laplace--Beltrami operator on an embedded submanifold; after restricting a function to a curve, do not directly retain the two-dimensional formula.
2. For a unit-speed parametrized curve, first compose the function into a one-variable function, then calculate its second derivative using the induced metric; a general parametrization must retain the speed factor.
3. Finally check that the operator vanishes on constant functions, and use symmetry or known eigenfunctions to verify the sign convention.

---

## Competition Extension: Line Covers of Planar Point Sets and Erdős--de Bruijn-Type Theorems

**Core content.** The Erdős--de Bruijn theorem states that if $n$ points in the plane are not all collinear, at least $n$ lines are required to cover them. It is foundational in combinatorial geometry and is fundamentally an extremal characterization of point--line incidence.

**Theorem.** Let $P$ be a finite noncollinear point set in the plane, $|P|=n$. If a family of lines $\mathcal L$ covers every point of $P$, with every line containing at least two points of $P$, then $|\mathcal L|\geq n$. Equality holds if and only if $P$ forms a regular configuration of a projective plane (vertices of a near-regular polygon together with diagonals).

**Connection with differential geometry.** For a discrete sample $P=\{\mathbf r(t_i):i=1,\ldots,n\}$ of a plane curve, the Erdős--de Bruijn-type lower bound gives the size of the minimum line family needed to describe its tangency contacts. This directly applies to curvature estimation and curve reconstruction in discrete differential geometry. For points sampled on a smooth curve, lines through adjacent pairs give linear approximations to curve segments; the theorem guarantees that their count is at least the point count, aligning with the need for a shortest description in discrete curvature estimation.

**Problem cue.** Given a point set and partial covering lines, prove that some point is uncovered or determine the minimum number of additional lines needed. A common method is contradiction plus double counting: assume fewer than $n$ covering lines, sum the point counts on the lines, use that every line covers at least two points and that the $n$ points are not all collinear, and derive a contradiction.

**Pitfall.** The “not all collinear” assumption is indispensable: if all points are collinear, one line covers them. The equality condition involves finite projective-plane configurations such as a “near-regular polygon”; when verifying equality, do not replace projective-geometric reasoning with Euclidean intuition.

**Examination techniques.**

- Double count: if $\ell_i$ is the number of points on the $i$th covering line, then $\sum\ell_i\geq n+$ the total number of incidences; together with every line having at least two points,

  $$|\mathcal L|\leq\sum(\ell_i-1)=\sum\ell_i-|\mathcal L|.$$

- Contradiction route: assume $|\mathcal L|<n$ $\to$ construct a set of representative points for the lines $\to$ use the pigeonhole principle for a contradiction.
- Explicit example of a minimal line family: vertices and all diagonals of a regular $n$-gon, giving exactly $n$ lines when $n$ is prime.

---

## Competition Extension: Angle Splitting and Segment Ratios in a Right Triangle

**Core content.** A segment drawn from the right-angle vertex of a right triangle to the hypotenuse splits the right angle into two subangles. The tangent or cotangent of each subangle has an exact ratio relationship with the two intercepted hypotenuse segments, frequently useful in geometric location and trigonometric evaluation.

Let $\angle C=90^\circ$ in $\triangle ABC$, and let $CD\perp AB$ at $D$. Then:

- $\tan\angle ACD=AD/CD$, and $\tan\angle BCD=BD/CD$.
- $CD^2=AD\cdot BD$ (projection theorem).
- $AD/BD=AC^2/BC^2=\tan^2B/\tan^2A$.

**Connection with differential geometry.** In the geometry of an osculating circle and tangent line of a plane curve, when the osculating circle, tangent, and normal at a point form a right triangle, angle splitting directly gives a curvature decomposition of subarcs. For parametrized curve $\mathbf r(t)$ at $\mathbf r(t_0)$, the osculating-circle radius $R=1/\kappa$ plays a role analogous to the hypotenuse, while tangent and normal projections separate $\kappa_n$ and $\kappa_g$.

**Problem cue.** Given two side lengths or an angle of a right triangle, determine the ratio of segments produced when a line from the right-angle vertex splits the right angle. Apply trigonometric identities and the projection theorem to turn length ratios into ratios of angle functions.

**Pitfall.** Do not confuse foot $D$ of the perpendicular from the right-angle vertex with the intersection of a non-right-angle bisector and the hypotenuse. The former has $CD\perp AB$ and $CD^2=AD\cdot BD$; the latter has $AD/DB=AC/BC$. Their segment ratios are completely different.

**Examination techniques.**

- Projection-theorem triad:

  $$AC^2=AD\cdot AB,\qquad BC^2=BD\cdot AB,\qquad CD^2=AD\cdot BD,$$

  for rapid cross-checking.
- If $\angle ACD=\alpha$ and $\angle BCD=\beta$, then always $\alpha+\beta=90^\circ$.
- Normalize all segment ratios by the same hypotenuse $AB$ to eliminate redundant parameters.

---

## Competition Extension: Angle-Multiple Relations and Solution Counts in Collinear Configurations

**Core content.** When several planar points are collinear, angles with these points as vertices can satisfy integer-multiple relations. A typical problem has collinear $A,B,C$, a point $P$ off the line, and condition $\angle APB=k\angle BPC$ for positive integer $k$; the task is to find locations and number of solutions for $P$.

**Connection with differential geometry.** This is a degenerate form of an Apollonius-circle configuration. Given collinear $A,B,C$ and the multiple-angle relation, the locus of points satisfying $\angle APB/\angle BPC=k$ is a family of circular arcs (isogonal trajectories). Differential-geometrically, the relation between curvature of these arcs and $k$ connects discrete angle constraints to continuous curve curvature: their radius $R$ satisfies $1/R\propto\sin(k\theta)/d(A,C)$, where $d(A,C)$ is the distance between the collinear endpoints.

**Problem cue.** Given three collinear points and positive integer $k$, find the locus or number of points satisfying $\angle APB=k\angle BPC$. Use a generalization of the angle-bisector theorem together with the sine rule in $\triangle APB$ and $\triangle BPC$ to establish a ratio equation.

**Pitfalls.**

- For $k=1$, the configuration degenerates to an Apollonius isogonal trajectory. $P$ is at the intersection of angle-bisector loci for $AB$ and $BC$, but there are $2$ solutions, one on each side of line $ABC$.
- For $k\geq2$, the number of solutions is no longer simply $2$: the equation becomes a higher-degree polynomial and the count depends on $k$, the distance ratio $AB:BC$, and whether $P$ on opposite sides of line $ABC$ is allowed.
- Do not mechanically apply the angle-bisector theorem; it is valid only for $k=1$.

**Examination techniques.**

- Set coordinates with $A$ as origin and $ABC$ as the $x$-axis: $B(a,0)$, $C(b,0)$, $P(x,y)$.
- Use tangent addition/subtraction: $\tan\theta=y/x$, and express $\angle APB$ through the tangent difference of vectors $\overrightarrow{PA}$ and $\overrightarrow{PB}$.
- Convert the final condition into an algebraic equation in the coordinates of $P$, then use its discriminant to count solutions.
- If $AB=BC$, reflection symmetry gives solutions in pairs.

---

## Competition Extension: Three-Circle Common-Point Conditions and Circles Through a Fixed Point Tangent to Fixed Lines

**Core content.** Given two lines $\ell_1,\ell_2$ and a fixed point $P$ in the plane, find circles through $P$ tangent to both lines. These problems involve common-tangent conditions for a family of circles, radical axes and radical centers, and a special case of Apollonius's problem.

**Condition for three circles to share a point.** If three circles $C_1,C_2,C_3$ intersect pairwise, they have a common intersection point if and only if their three radical axes are concurrent at the radical center. For

$$
C_1:x^2+y^2+D_1x+E_1y+F_1=0,\qquad C_2:x^2+y^2+D_2x+E_2y+F_2=0,
$$

their radical axis is

$$
(D_1-D_2)x+(E_1-E_2)y+(F_1-F_2)=0.
$$

**Construction of a circle through a fixed point and tangent to fixed lines.** Write the required circle as $(x-a)^2+(y-b)^2=r^2$. Passing through $P(x_0,y_0)$ gives

$$
(x_0-a)^2+(y_0-b)^2=r^2.
$$

Tangency to line $Ax+By+C=0$ gives

$$
\frac{|Aa+Bb+C|}{\sqrt{A^2+B^2}}=r.
$$

For two tangent lines, the two distance constraints together with the fixed-point constraint form a system of three quadratic equations in $(a,b,r)$.

**Connection with differential geometry.** Passing through a fixed point and tangent to a fixed line is analogous to the second-order contact of an osculating circle with a curve: at a point of curve $\mathbf r(t)$, the osculating circle both passes through that point and is tangent to the tangent line. If a curve has third-order contact with a circle (a superosculating circle), it is uniquely determined away from a vertex and is the locally best circular approximation.

**Problem cue.** Given two lines and a point, find the number and equations of circles through the point and tangent to both lines. Usually distinguish whether the point is on the same side or opposite sides of the lines: there can be $2$ solutions, $1$ solution, or no solution. Derive a quadratic equation in center coordinates from distance constraints; the discriminant determines the number of solutions.

**Pitfalls.**

- The absolute value in the algebraic tangency condition cannot be omitted: the center may be on either side of a line.
- Two tangent lines plus a fixed point can determine $2$ distinct circles in symmetric positions, or none; for example, the point may lie on an angle bisector but not on the equal-distance locus of the two lines.
- Do not confuse Apollonius problem LLL (three lines) with PLL (a point plus two lines).

**Examination techniques.**

- First find the two angle bisectors of the two lines; the center must lie on one of them.
- Parametrize the center along each bisector and solve the fixed-point distance constraint backward for its coordinates.
- Verify geometrically that the fixed point's distances to the two tangent lines agree with the radius for every proposed position.

---

## Competition Extension: Tangents, Arc Midpoints, and Angle Closure in the Circumcircle of a Right Triangle

**Core content.** Special points on the circumcircle (Thales circle) of a right triangle—the right-angle vertex, the hypotenuse midpoint which is the circle center, arc midpoints, and tangents through these points—satisfy angle-closure relations, constituting a special case of the butterfly theorem.

**Basic configuration.** In $\triangle ABC$, let $\angle C=90^\circ$ and let circumcircle $O$ have $AB$ as diameter. Let $M$ be the midpoint of arc $\widehat{AB}$ not containing $C$. Then $CM$ bisects $\angle ACB=90^\circ$. The tangent $t_C$ at $C$ satisfies $t_C\perp OC$, where $OC$ is a radius.

**Angle-closure relation.** Since $A,B,C$ lie on the circumcircle, the angle between tangent $t_C$ and chord $CA$ equals the inscribed angle subtended by chord $CB$, namely $\angle CAB$ (tangent--chord theorem):

$$
\angle(t_C,CA)=\angle CBA.
$$

Similarly, $\angle(t_C,CB)=\angle CAB$. Hence

$$
\angle CAB+\angle CBA=90^\circ=\angle ACB,
$$

verifying angle closure.

**Connection with differential geometry.** On a surface, a similar relation between tangent angle and opposite circular angle for a geodesic triangle is generalized by Gauss--Bonnet: on a constant-curvature surface, the relation between the angle sum of a geodesic triangle and the deviation of tangent angles has a curvature-weighted correction. The correspondence between spherical conics circumscribed about spherical triangles and the circumcircle of a planar right triangle is important in spherical geometry.

**Problem cue.** Given a right triangle, construct its circumcircle, introduce an arc midpoint or tangent point, and prove two angles equal or supplementary. The key tools are the alternate-segment theorem and Thales's theorem used together.

**Pitfalls.**

- In the tangent--chord theorem, the chord begins at the point of tangency, and its tangent angle equals the inscribed angle on the other side subtended by that chord; attend to the same-side/opposite-side selection.
- Specify whether an arc midpoint is on the major or minor arc; the two non-right vertices of a right triangle split the circumcircle into two arcs.
- Do not validate angle closure by a protractor intuition; derive it rigorously with the tangent--chord theorem.

**Examination techniques.**

- A standard drawing with horizontal hypotenuse and right angle above it makes angle labels easiest.
- Geometric verification for the butterfly theorem (fixed point, tangent point, and arc midpoint collinear): a chord through the arc midpoint cuts equal lengths on the two tangent segments.
- Coordinate method: take the circle center as origin and $AB$ as diameter, with $A(-R,0)$, $B(R,0)$, $C(R\cos\theta,R\sin\theta)$.

---

## Competition Extension: Polar Envelopes and Orthocenter Configurations

**Core content.** Given a conic $\Gamma$, usually an ellipse, parabola, or hyperbola, the **polar** of point $P$ relative to $\Gamma$ is the line in polar-pole duality with $P$. As $P$ moves along a locus, its family of polars has an **envelope**, another curve: the dual curve. Orthocenter configurations study deeper links among a triangle's three altitudes, nine-point circle, and polar envelopes.

**Polar equation.** For conic

$$
Ax^2+Bxy+Cy^2+Dx+Ey+F=0,
$$

the polar of $P(x_0,y_0)$ is

$$
Ax_0x+\frac12B(x_0y+xy_0)+Cy_0y+\frac12D(x+x_0)+\frac12E(y+y_0)+F=0.
$$

In particular, for point $(x_0,y_0)$ on circle $x^2+y^2=R^2$, the polar is

$$
x_0x+y_0y=R^2,
$$

the tangent line at that point.

**Relation between orthocenter and polar.** The polar of orthocenter $H$ of $\triangle ABC$ with respect to its circumcircle is exactly a special line of the circumcircle of the orthic triangle (the nine-point circle). Specifically, the polar of $H$ is the “polar axis” of the circumcircle with respect to $\triangle ABC$ and intersects the three sideline extensions at points related to the Simson line.

**Connection with differential geometry.** A polar envelope is the discrete manifestation of a Legendre (dual) transformation on plane curves. In differential geometry, the evolute of a curve is the envelope of its normal family; a polar family is a generalized normal family. For a smooth closed convex curve, its polar envelope gives the dual curve and satisfies reciprocal curvature relations under duality, analogous to ellipse--hyperbola duality.

**Problem cue.** Given a triangle and its circumcircle or nine-point circle, prove three points collinear, such as the orthocenter, circumcenter, and a special point, or prove a line is the polar of a point. Use the algebraic polar definition and pole--polar duality: if $P$ lies on the polar of $Q$, then $Q$ lies on the polar of $P$.

**Pitfalls.**

- A polar depends on the selected conic; for a different conic, the same point has a completely different polar.
- An orthocenter lies strictly inside only for an acute triangle. For an obtuse triangle it lies outside, and polar relations may require signed treatment.
- A parametrization of an envelope cannot be obtained by directly differentiating a family-of-lines equation with respect to its parameter; first convert it to an implicit form, then use the envelope theorem.

**Examination techniques.**

- Use symmetry: in an isosceles or equilateral triangle, altitudes and polars have natural axial symmetry.
- Coordinate method: use the circumcenter as origin and write $A(R\cos\alpha,R\sin\alpha)$ and similarly for the other vertices; the polar equation then automatically reduces to its simplest form.
- Pole--polar duality chains $P\to Q\to R$ are especially efficient in three-point collinearity problems.

## Quick Reference: Area-Bisecting Chords of a Convex Polygon and Their Boundary Distribution

- **Retrieval terms:** vertex, minimum, smallest, least, minimal, convex, area, polygon, construction, upper bound, distribution, bisector.
- **Core content:** From every vertex of a convex polygon, the area-bisecting segment meets the opposite boundary. A continuity-and-partition argument controls the distribution of all endpoints: as the bisecting segments sweep the polygon continuously, the edges containing their endpoints occur, in boundary order, in at most a constant number of consecutive blocks. Thus all endpoints lie on at most a constant number of edges independent of the number of polygon sides. A minimum problem is completed by matching this upper bound with constructions for every number of sides.
- **Route and exact conclusion:** Track the endpoints continuously while the vertex moves. Their endpoints can occupy at most three edges; the minimum is independent of $n$ and equals $\boxed{3}$. For $n=3$, this is the median case; for $n\ge4$, a near-degenerate construction attains exactly three edges.
- **Pitfalls:** An area-bisector need not be a median. The consecutive-block count depends on boundary order; endpoint coincidences must be checked so that the number of hit edges is neither overcounted nor undercounted.

## Quick Reference: Congruent-Triangle Dissections and Compatibility with Tangential Polygons

- **Retrieval terms:** vertex, minimum, triangle, circle, disk, tangent, tangency, convex quadrilateral, polygon, symmetric, symmetry.
- **Core content:** If a convex polygon is dissected by nonintersecting diagonals into congruent triangles, the dissection data—the number of triangles and the number of angles meeting at each vertex—are constrained by the side count. Congruence forces all interior angles to be integral-multiple allocations of one common angle set. If the polygon is also tangential (has an incircle), impose either equality of sums of opposite sides or concurrency of angle bisectors. Compatibility occurs only in the smallest-side-count case: the symmetry forced by the congruent dissection (a kite) together with the tangent condition forces all four sides equal, yielding the special quadrilateral that always has an incircle. Larger side counts are excluded by angle sums or symmetry breaking.
- **Route:** Write angle-allocation equations from the dissection, combine them with the tangential-polygon condition, construct the minimal viable case, and exclude all remaining side counts.
- **Pitfalls:** Do not confuse cyclic (circumcircle) conditions with tangential (incircle) conditions. Congruent triangles can contribute different counts of angles at different polygon vertices, so check each interior-angle sum separately.

## Quick Reference: Visibility of Faces of a Convex Polyhedron and Normal-Vector Separation

- **Retrieval terms:** minimum, smallest, least, minimal, convex, polyhedron, faces, visible, construction, normal vector, observer, vectors.
- **Core content:** A face of a convex polyhedron is visible from an external observation point exactly when its outward normal has positive dot product with the viewing direction. Requiring that, for every face, there be a point from which every other face is visible while that face alone is hidden is equivalent to separating that face's normal from all other normals by a hyperplane through the origin. In three dimensions this is possible only for a simplex normal configuration, the dual configuration of a tetrahedron.
- **Route and exact conclusion:** Translate visibility into linear separation of normals, prove the upper bound via convex-cone/separation reasoning (for example, Carathéodory-type results), then give the tetrahedral construction. The minimum number of faces is $\boxed{4}$: for each tetrahedron face choose an observation point near that face and outside the other three.
- **Pitfalls:** Verify the per-face condition, not merely that most faces can be visible from one point. The observation point must lie strictly in the exterior half-space of the face being hidden.

## Quick Reference: Quadrilateral Area, the Angle Between Diagonals, and Constrained Optimization

- **Retrieval terms:** maximum, largest, greatest, triangle, convex, area, angle, quadrilateral, upper bound, symmetric, symmetry.
- **Core content:** A convex quadrilateral's area is the sum of the areas of the two triangles made by a diagonal, and can also be written as

$$S=\tfrac12d_1d_2\sin\theta,$$

where $d_1,d_2$ are the diagonal lengths and $\theta$ is their included angle. Under a perimeter constraint, express the area in free variables, derive an upper bound from the perimeter and diagonal constraints, and force equality in every inequality. The optimum is usually a kite symmetric about a diagonal.
- **Route:** Start from the area formula above and triangular-area decomposition. For a fixed-perimeter maximum, propose the symmetric configuration, prove the bound, and state each equality condition explicitly.
- **Pitfalls:** Supplementary diagonal angles have the same sine, so obtuse cases must be included. During elimination retain convexity, including that each side is shorter than the sum of the other three, rather than treating all side lengths as independent.
