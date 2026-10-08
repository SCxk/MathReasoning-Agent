# Operations Research Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: linear/integer/nonlinear programming, transportation, networks, queues, inventory, scheduling, decisions, and operations-research games.
- Do not take over: pure combinatorial-game/graph-theory proofs belong to discrete mathematics; statistical regression and parameter tests belong to linear regression or statistical inference.
- Verification contract: state objective direction, every constraint, feasibility, and optimality. Scheduling/allocation problems must give the full plan and total cost.

> Systematically organizes core operations-research solution skills around 20 typical exercises (14 computational and 6 proof problems).

## Objective-Question Discrimination and Global Verification

- For linear programming, first confirm objective direction, constraint directions, variable nonnegativity, and feasible region. “Feasible” is not “optimal”; all reduced costs or dual bounds must be checked.
- Strong duality is a powerful optimality check: if a primal feasible \(x\) and dual feasible \(y\) satisfy \(c^Tx=b^Ty\), then \(x\) and \(y\) are optimal for their respective problems.
- Reduced costs, entering variables, and leaving variables in a simplex tableau must use one consistent notation. If a text uses \(z_j-c_j\), reverse the optimality inequality accordingly.
- An initial transportation solution only satisfies supply-demand balance; it is not automatically optimal. Check all row/column totals first, then use potentials/closed-loop improvement. A degenerate basis requires zero basic variables; do not undercount degrees of freedom.
- In integer programming, an LP relaxation supplies only a bound. On branch-and-bound termination, state that the current integer feasible solution and lower/upper bound are equal; directly treating a relaxation solution as an integer answer is a common error.
- For queueing models, first check arrival rate, service rate, stability condition (e.g. \(\rho<1\)), and system capacity, then select M/M/1, M/M/c, or finite-source formulas. If stability fails, steady-state means cannot be used.

## Frequent Errors and Conventions (Reviewer Feedback, 2026-07-07)

- **An initial transportation solution must give the complete allocation plan**: after using least-cost, northwest-corner, or Vogel’s method to find an initial basic feasible solution, the final answer must list every basic-variable value (e.g. \(x_{11}=3,\ x_{13}=2,\ x_{22}=4,\ x_{23}=1\), with all other \(x_{ij}=0\)) **and** the initial total freight cost. Reporting only total cost is incomplete.
- Least-cost method: in every round choose the smallest remaining \(c_{ij}\), set \(x_{ij}=\min(\text{remaining supply},\text{remaining demand})\), and cross out the satisfied row or column. A balanced transportation problem has \(m+n-1\) basic variables (add zero in degeneracy).
- Self-check after solving: every row allocation sum = supply; every column allocation sum = demand; total freight cost = \(\sum c_{ij}x_{ij}\), consistent with term-by-term addition.
- **Dual-direction conversion**: primal max \(\to\) dual min; the correspondence between constraint directions and variable signs is easily reversed. After writing it, quickly check weak duality \(c^Tx\le b^Ty\): if both are feasible but \(c^Tx>b^Ty\), the dual direction is certainly wrong.
- **Equality constraints and free variables**: an equality constraint in the primal corresponds to a free (unrestricted-sign) dual variable, and conversely. Do not habitually write \(\ge0\) in examinations.

---

## Module I: Linear Programming

### Core Concepts

Decision variables, objective function, constraints, feasible region, basic feasible solution, dual problem, and shadow price.

### Graphical Method (Two Variables)

1. Draw constraint lines, mark inequality directions, and determine feasible region.
2. Draw objective-function level lines and translate them in the improving direction.
3. An intersection point is optimal.

### Simplex Method

1. Introduce slack variables to obtain standard form.
2. Determine an initial basic feasible solution.
3. Calculate reduced costs \(\sigma_j=c_j-\mathbf c_BB^{-1}\mathbf a_j\).
4. Optimality: all \(\sigma_j\le0\) (max); otherwise the largest positive \(\sigma_j\) enters the basis.
5. The minimum-ratio rule \(\theta=\min\{b_i/a_{ik}\mid a_{ik}>0\}\) determines the leaving basis variable.
6. Perform pivot elimination and repeat.

### Dual Construction

A primal max constraint \(\le\) corresponds to a dual variable \(\ge0\); a primal variable \(\ge0\) corresponds to a dual constraint \(\ge\).

### Weak Duality Theorem

\(c^Tx\le b^Ty\) holds for every primal/dual feasible pair (max primal).

### Strong Duality Theorem

If the primal has finite optimum \(x^*\), then the dual also has finite optimum \(y^*\), and their optimal values are equal:
\[
c^Tx^*=b^Ty^*.
\]

**Proof idea:** at simplex termination, the reduced-cost row gives a dual feasible solution; primal objective equals dual objective, so weak duality proves that both are optimal.

### Complementary Slackness

If \(x^*\) and \(y^*\) are primal and dual optima, then
\[
y_i^*\cdot\left(b_i-\sum_j a_{ij}x_j^*\right)=0\quad\forall i,
\]
\[
x_j^*\cdot\left(\sum_i a_{ij}y_i^*-c_j\right)=0\quad\forall j.
\]

**Intuition:**

- If a primal constraint is strict (has slack), its corresponding dual variable must be \(0\).
- If a dual variable is strictly \(>0\), its corresponding primal constraint must be binding.
- Complementary slackness is an equivalent characterization of strong duality and is often used to infer a dual solution from a primal solution.

### Exam Techniques

- **Use strong duality to verify optimality**: constructing primal/dual feasible solutions satisfying \(c^Tx=b^Ty\) proves both optimal; this is a standard exam method.
- **Shadow price**: the economic meaning of dual variable \(y_i^*\) is the shadow price of resource \(i\), the objective improvement per additional unit of that resource.
- **Dual simplex**: when primal is infeasible but dual feasible, iterate with dual simplex.

### Frequent Exam Pitfalls

- **Direction conversion**: primal max \(\to\) dual min; primal min \(\to\) dual max.
- **Constraint–variable correspondence:**
  - max + \(\le\) constraint \(\to\) dual variable \(\ge0\);
  - max + \(=\) constraint \(\to\) free dual variable;
  - primal variable \(\ge0\) \(\to\) dual constraint \(\ge\) (min dual);
  - free variable \(\to\) dual equality constraint.
- **Forgetting transpose**: dual constraint matrix is transpose \(A^T\) of the primal coefficient matrix.
- **Complementary slackness is not “mutual exclusion”**: a positive dual variable and a binding constraint may occur together; only their product with the slack is zero.

---

## Module II: Transportation Problems

### Least-Cost Method

1. Find smallest \(c_{ij}\) and allocate \(\min(a_i,b_j)\).
2. Update supply and demand; cross out a full row/column.
3. Repeat until every supply and demand is met.
4. There should be \(m+n-1\) basic variables.

### Potential Method

- Basic variables satisfy \(u_i+v_j=c_{ij}\); set \(u_1=0\) and solve every potential.
- For a nonbasic variable, reduced cost is \(\sigma_{ij}=c_{ij}-u_i-v_j\).
- All \(\sigma_{ij}\ge0\) gives optimality (min problem).

---

## Module III: Integer Programming

**LP-relaxation lower bound:** \(z_{LP}^*\le z_{IP}^*\) (min problem), since \(X_{IP}\subset X_{LP}\).

**Branch and bound:** solve LP relaxation \(\to\) choose a noninteger variable to branch on \(\to\) solve subproblems \(\to\) prune.

---

## Module IV: Nonlinear Programming

### KKT Conditions

For \(\min f(\mathbf x)\) subject to \(g_i(\mathbf x)\le0, h_j(\mathbf x)=0\):
\[
\nabla f+\sum\mu_i\nabla g_i+\sum\lambda_j\nabla h_j=0,\quad\mu_ig_i=0,\quad\mu_i\ge0.
\]

### KKT Sufficiency (Convex Programming)

If \(f\) and \(g_i\) are convex and \(h_j\) are affine, a KKT point is a global optimum.

### Solution Steps

1. Write the Lagrangian.
2. State stationarity, primal feasibility, dual feasibility, and complementary slackness.
3. Split cases for inequality constraints (\(\mu_i=0\) or \(g_i=0\)).
4. Solve and verify.

---

## Module V: Dynamic Programming

### Backward Recursion Equation

\[
f_k(s_k)=\min/\max_{u_k}\{v_k(s_k,u_k)+f_{k+1}(s_{k+1})\},\quad f_{n+1}=0.
\]

### Solution Steps

1. Divide stages and define state and decision.
2. Write state transition and stage objective.
3. Establish recurrence.
4. Recur backward from final stage.
5. Move forward to obtain the optimal policy.

---

## Module VI: Graph Theory and Network Optimization

### Dijkstra Shortest Path

1. Initialize \(d(s)=0\), all others \(\infty\).
2. Select unlabelled \(u\) with smallest \(d(u)\) and label it permanently.
3. Update neighbors: \(d(v)=\min\{d(v),d(u)+w(u,v)\}\).
4. Repeat until target is permanently labelled.

### Ford–Fulkerson Maximum Flow

1. Start with zero flow.
2. Use labelling to find an augmenting path (unsaturated forward arcs / backward arcs carrying flow).
3. When sink is labelled, augment flow along the path.
4. Stop when no augmenting path exists; current flow is maximum.

### Max-Flow Min-Cut Theorem

Every flow value is \(\le\) every cut capacity. At algorithm termination, the set \(S\) reachable from \(s\) in residual network defines a minimum cut, and flow value = cut capacity.

---

## Module VII: Queueing Theory

### M/M/1 (\(\rho=\lambda/\mu<1\))

| Quantity | Formula |
|---|---|
| \(P_0\) | \(1-\rho\) |
| \(L\) | \(\rho/(1-\rho)\) |
| \(L_q\) | \(\rho^2/(1-\rho)\) |
| \(W\) | \(L/\lambda=1/(\mu-\lambda)\) |
| \(W_q\) | \(L_q/\lambda\) |

### M/M/c (\(\rho=\lambda/(c\mu)<1\))

\[
P_0=\left[\sum_{n=0}^{c-1}\frac{(c\rho)^n}{n!}+\frac{(c\rho)^c}{c!(1-\rho)}\right]^{-1},
\]
\[
L_q=\frac{(c\rho)^c\rho}{c!(1-\rho)^2}P_0,\quad L=L_q+c\rho.
\]

---

## Module VIII: Inventory Theory

### EOQ Model

\[
TC(Q)=\frac{KD}{Q}+\frac{hQ}{2},\quad Q^*=\sqrt{\frac{2KD}{h}},\quad TC^*=\sqrt{2KDh}.
\]

**Derivation:** \(TC'(Q)=0\Rightarrow Q^*\), and \(TC''(Q)=2KD/Q^3>0\) (strict convexity).

---

## Module IX: Game Theory

### \(2\times2\) Mixed Strategies

Let the row player use \((p,1-p)\) and the column player use \((q,1-q)\). By the indifference principle, equate the two expected-payoff lines and solve for \(p,q\).

### \(2\times n\) Graphical Method

1. Each row-player pure strategy gives an expected-payoff line \(v_i(p)\).
2. Take the lower envelope (the column player minimizes).
3. The highest point of the envelope gives optimal \(p\) and game value \(v\).

### Saddle-Point Condition

\((i^*,j^*)\) is a saddle point if and only if \(a_{ij^*}\le a_{i^*j^*}\le a_{i^*j}\) for every \(i,j\).

### Competition Extension: Divide-and-Choose Game

**Problem:** Player 1 divides \(n\) indivisible stones into two piles; Player 2 chooses one, and Player 1 receives the other. Both are rational and maximize their own stones.

**Backward-induction analysis:**

- Facing piles \((a,b)\), Player 2 selects the larger pile: \(u_2=\max(a,b)\).
- Anticipating this, Player 1 maximizes own payoff: \(u_1=n-\max(a,b)=\min(a,b)\).
- Player 1’s optimum is to maximize \(\min(a,b)\), i.e. divide as evenly as possible.

**Nash-equilibrium strategy:**

- If \(n\) is even, Player 1 chooses \((n/2,n/2)\), and each gets \(n/2\).
- If \(n\) is odd, Player 1 chooses \((\lfloor n/2\rfloor,\lceil n/2\rceil)\); Player 2 gets \(\lceil n/2\rceil\), Player 1 gets \(\lfloor n/2\rfloor\).

**Minimum initial resources:** for each player to receive at least \(m\) stones, \(n\ge2m\) is required.

**Extensions:** cake-cutting on continuous resource \([0,1]\), multi-pile division games, and two-stage division in which Player 2 can reject and repartition at a resource loss.

**Exam technique:** solve subgame-perfect equilibrium by backward induction: analyze the last mover’s best response first and move backward. For division-and-choice, the key identity is \(u_1=\min(a,b)\).

**Common pitfalls:**

- Player 1 cannot choose first; Player 1 only divides. Do not reverse the order.
- At equilibrium Player 1 maximizes \(\min(a,b)\), not total number of stones.

---

## Module X: Decision Theory

### EMV Criterion

\[
EMV_i=\sum_jp_jr_{ij}.
\]

Select the plan with the largest \(EMV\).

### Decision Tree

A square node is a decision node (choose a branch); a circular node is a chance node (take expectation). Roll backward from leaves to root.

---

## Module XI: Optimal Scheduling for a Single Round Robin

### Competition Extension: Optimal Single-Round-Robin Scheduling

**Problem:** \(n\) teams play a single round robin (each pair plays exactly once), each team plays at most one match per day; find minimum total days.

**Core result:**

- If \(n\) is even, minimum days are \(n-1\), with a perfect schedule (every team plays every day).
- If \(n\) is odd, minimum days are \(n\), with one bye every round.

**Lower-bound proof:**

- Every team needs \(n-1\) games and can play at most one per day, so at least \(n-1\) days.
- Each day has at most \(\lfloor n/2\rfloor\) games; total games are \(\binom n2=n(n-1)/2\).
- Thus \(T\ge\frac{n(n-1)/2}{\lfloor n/2\rfloor}=n-1\) for even \(n\), or \(n\) for odd \(n\).

**Circle Method:**

1. Number teams \(1,2,\ldots,n\).
2. If \(n\) is odd, add dummy team \(n+1\); a match against it means a bye, reducing to even \(n+1\).
3. Hold team \(n\) (or team \(1\)) fixed and arrange the others circularly.
4. In each round pair team \(i\) with team \(n-i+1\) (in the circular sense).
5. After each round rotate all nonfixed teams one position around the circle.

**Example** (\(n=6\), 5 days):

| Round 1 | Round 2 | Round 3 | Round 4 | Round 5 |
|---|---|---|---|---|
| 1 vs 6 | 1 vs 5 | 1 vs 4 | 1 vs 3 | 1 vs 2 |
| 2 vs 5 | 6 vs 4 | 5 vs 3 | 4 vs 2 | 3 vs 6 |
| 3 vs 4 | 2 vs 3 | 6 vs 2 | 5 vs 6 | 4 vs 5 |

**Exam technique:** use formula directly for minimum days (even \(n-1\), odd \(n\)); to judge an offered schedule, check whether its days and games per day attain the theoretical lower bound; use Circle Method when construction is required.

**Common pitfalls:**

- For odd \(n\), the minimum is \(n\), not \(n-1\), because at most \((n-1)/2\) games can be played each day.
- Do not forget bye handling in the odd case.
- A single round robin has \(n(n-1)/2\) total games; do not confuse it with a double round robin.

---

## General Six-Step Modeling Method

| Step | Content | Key question |
|---:|---|---|
| 1 | Understand problem | Optimization or evaluation? |
| 2 | Define variables | What represents “what to do”? |
| 3 | Objective function | Maximize or minimize? |
| 4 | Identify constraints | Resource/technical/logical/nonnegative? |
| 5 | Assign parameters | Are units consistent? |
| 6 | Finalize model | LP/NLP/IP/DP/queueing? |

## Methods for Verifying Optimality

| Method | Applicable to | Operation |
|---|---|---|
| Nonpositive reduced costs | LP (max) | All \(\sigma_j\le0\) |
| Strong duality | LP | Construct dual solution with \(c^Tx^*=b^Ty^*\) |
| KKT conditions | NLP | Verify every KKT condition |
| Convexity + KKT | Convex programming | KKT point = global optimum |
| Saddle-point check | Games | max min = min max |

---

## Index of Solution Ideas for 20 Problems

| idx | Domain | Knowledge point | Solution keywords | Difficulty |
|:---:|---|---|---|:---:|
| 0 | LP | Graphical method | Feasible region \(\to\) level line \(\to\) vertex \((4,2)\to z=14\) | Easy |
| 1 | LP | Simplex method | Standard form \(\to\) reduced costs \(\to\) enter/leave basis \(\to(3,2),z=23\) | Intermediate |
| 2 | LP | Dual | max \(\leftrightarrow\) min; convert variable/constraint directions | Intermediate |
| 3 | Transportation | Least-cost method | Minimum cost first \(\to\) update supply/demand \(\to\) freight cost 22 | Intermediate |
| 4 | NLP | KKT | Lagrange multipliers \(\to\) gradient \(=0\to(2,1),f=6\) | Intermediate |
| 5 | DP | Backward recursion | Stage \(\to\) state \(\to\) recurrence \(\to\) path 1-3-6-7, distance 12 | Intermediate |
| 6 | Graph theory | Dijkstra | Label \(\to\) permanent \(\to\) update \(\to\) A-B-C-E-F, distance 8 | Easy |
| 7 | Graph theory | Maximum flow | Labelling/augmentation \(\to\) forward/backward arcs \(\to\) maximum flow 18 | Intermediate |
| 8 | Queueing | M/M/1 | \(\rho=0.8,\ P_0=0.2,\ L=4\) | Intermediate |
| 9 | Queueing | M/M/2 | \(P_0\) formula \(\to P_0=1/3,\ L_q=1/3\) | Hard |
| 10 | Inventory | EOQ | \(Q^*=\sqrt{2KD/h}=200,\ TC^*=600\) | Easy |
| 11 | Game | \(2\times2\) mixed | Indifference equations \(\to p=1/2,q=2/3,v=3\) | Intermediate |
| 12 | Game | \(2\times n\) graphical | Highest point of lower envelope of three lines \(\to v=2.5\) | Hard |
| 13 | Decision | EMV | Large plant 40/small plant 54 \(\to\) build small plant | Intermediate |
| 14 | LP | Weak-duality proof | \(c^Tx\ge y^TAx\ge y^Tb\) | Intermediate |
| 15 | IP | LP-relaxation lower bound | \(X_{IP}\subset X_{LP}\Rightarrow v_{LP}\le v_{IP}\) | Intermediate |
| 16 | NLP | Convex-program KKT | \(f\) convex + \(g_i\) convex + equalities affine \(\to\) KKT \(\Rightarrow\) global | Hard |
| 17 | Graph theory | Max-flow min-cut | Weak duality + cut at algorithm termination \(\to\) equality | Intermediate |
| 18 | Inventory | EOQ derivation | \(TC(Q)=KD/Q+hQ/2\to\) differentiate \(\to Q^*\) | Hard |
| 19 | Game | Saddle-point condition | Row minimum = column maximum \(\Leftrightarrow\) saddle point exists | Easy |

## General Supplement: Linear-Programming Dual Audit

1. When standardizing a primal problem, mark objective direction, variable sign restrictions, and every constraint direction; then generate dual variables, objective coefficients, and constraints one by one according to the rules.
2. Use weak duality to check bounds for any feasible solutions, and use strong duality and complementary slackness to verify an optimum. Do not mechanically map a primal minimization problem to a dual with the same direction.
3. For true/false questions, verify one item at a time: objective/constraint interchange, coefficient-matrix transpose, and dual of the dual; distinguish feasible region from constraint system.

## Quick Reference: Linear-Programming Duality

For the standard pair

$$
\max c^Tx\quad\text{s.t. }Ax\le b,\ x\ge0
\quad\Longleftrightarrow\quad
\min b^Ty\quad\text{s.t. }A^Ty\ge c,\ y\ge0,
$$

the matrix is transposed, $b$ becomes the dual objective coefficient vector, $c$ becomes the right-hand side of the dual constraints, and max/min reverse. Weak and strong duality apply, and the dual of the dual returns the primal. Under this item's strict answer convention, the phrase “the primal objective function becomes a dual constraint” is false: only its coefficient vector $c$ becomes the dual-constraint right-hand side. The sole correct option in the associated item is $\boxed D$.

## Quick Reference: Optimal Scheduling of a Single Round Robin

Minimize total player stay by concentrating each player's matches. Use recursive divide-and-conquer: schedule two equal groups recursively, then interleave their cross-group matches in a concentrated block. The recurrence has the form $T(2m)=2T(m)+\text{cross cost}$, with closed form

$$T(n)=\frac{n^3}{4}+\frac{n^2}{8}-\frac n4.$$

Calibrate with $T(4)=17$. A sequentially added lexicographic schedule is suboptimal because early players remain throughout. Decorative conditions such as VIP lounges or audience capacity do not change the scheduling cost.

## Quick Reference: Adversarial Box-and-Pebble Allocation

For $m$ boxes with initial contents $a_i$, the safety condition is

$$a_i+a_j\ge j-i+2\qquad(i<j).$$

Equivalently, the intervals $I_i=[i-a_i+1,i+a_i-1]$ have a common point $p$, so $a_i\ge|i-p|+1$. Therefore

$$
\min\sum_i a_i=m+\min_p\sum_i|i-p|.
$$

For an even number $m$ of boxes, this is $m+m^2/4$ after choosing either median as the center. The tent-shaped allocation is $a_i=|i-p|+1$ for a median $p$; do not omit the baseline one pebble per box.

## Quick Reference: Formula-First Operations-Research Reasoning

- **Round-robin stay cost:** derive a divide-and-conquer recurrence by splitting an even player field into two equal groups, scheduling within-group matches recursively, and concentrating cross-group matches. After validating a small case, evaluate the resulting formula only at the player count in the current problem.
- **Split-choose box game:** for $N=2m$ boxes, establish the V-shaped invariant and matching lower bound before evaluating the symbolic expression $N+m^2$. The profile $V_i(j)=1+|j-i|$ is a proof device, not a stored answer.
- **Linear-programming-duality multiple choice:** the required answer is $\boxed D$; the dual of the dual returns the original problem, while the other statements conflate coefficient vectors, directions, or feasible regions.
