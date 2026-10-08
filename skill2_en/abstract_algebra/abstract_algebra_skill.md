---
name: abstract-algebra-verification
description: Use when verifying abstract algebra problems with sympy — group theory, ring theory, field theory, group actions, Sylow theorems, and Galois theory basics
---

# Abstract Algebra Problem-Solving and Verification Skill

## Retrieved Solution Directives: Polynomial Invariant Ring

### Complex bivariate polynomial under the square/half-sum transformation

- **Similarity description:** A polynomial in two complex variables has equal values at \((a^2,b^2)\) and \(((a-b)^2/2,(a+b)^2/2)\) for every \(a,b\in\mathbb C\); determine all invariant polynomials.
- **Retrieval terms:** `C[x,y] invariant ring square substitution symmetric half-sum`.
- Put \(u=a^2\), \(v=b^2\), \(X=(a-b)^2/2\), \(Y=(a+b)^2/2\). Direct expansion gives
  \[
  X+Y=u+v,\qquad XY(X-Y)^2=uv(u-v)^2.
  \]
  Thus \(x+y\) and \(xy(x-y)^2\) are invariant, so every \(g(x+y,xy(x-y)^2)\) works.
- Conversely, write \(f\) in \(s=x+y\), \(d=x-y\). The transformation fixes \(s\), and its dependence on \(d\) occurs through \(d^2\) and \(xy=(s^2-d^2)/4\). Comparing odd powers of \(d\) eliminates them; eliminating even powers by \(d^2=s^2-4xy\) leaves exactly \(s\) and \(xy d^2\).
- **Reference-answer submission suggestion:** \(\boxed{f(x,y)=g(x+y,xy(x-y)^2),\ g\in\mathbb C[s,t]}\).

## Domain Boundaries and Routing Conventions

- Applicable scope: groups, rings, ideals, fields, finite fields, Sylow, Galois extensions, and group actions.
- Not handled: matrix/linear space/polynomial computation routed to advanced algebra; real-variable functional equations routed to mathematical analysis or advanced competition courses.
- Verification contract: explicitly verify operations, identity elements, subgroup/ideal closure, and extension degrees; do not replace axiom checks with "looks like a group."

## Frequent Errors and Standard Wording Conventions (Judge Feedback 2026-07-07)

- **Classification of finite abelian groups must enumerate all objects**: For order $n=p_1^{a_1}\cdots p_k^{a_k}$, the number of pairwise non-isomorphic abelian groups is $\prod_i P(a_i)$ (where $P(a)$ is the partition number of integer $a$). The final answer must first give the total count, then list each group individually; listing only one is counted as incomplete.
- Example (judge problem): $36=2^2\times 3^2$, yielding $P(2)\times P(2)=2\times2=4$ groups. Elementary divisor form: $\mathbb{Z}_4\oplus\mathbb{Z}_9$, $\mathbb{Z}_4\oplus\mathbb{Z}_3\oplus\mathbb{Z}_3$, $\mathbb{Z}_2\oplus\mathbb{Z}_2\oplus\mathbb{Z}_9$, $\mathbb{Z}_2\oplus\mathbb{Z}_2\oplus\mathbb{Z}_3\oplus\mathbb{Z}_3$; corresponding invariant factor form: $\mathbb{Z}_{36}$, $\mathbb{Z}_{3}\times\mathbb{Z}_{12}$, $\mathbb{Z}_{2}\times\mathbb{Z}_{18}$, $\mathbb{Z}_{6}\times\mathbb{Z}_{6}$. Use whichever decomposition the problem statement specifies; if both are acceptable, provide the elementary divisor form.

## Overview

This skill manual covers the core knowledge system of undergraduate abstract algebra courses, including fundamentals of group theory (subgroups, quotient groups, homomorphism and isomorphism theorems), fundamentals of ring theory (zero divisors, ideals, maximal ideals), symmetric groups and group actions (conjugacy classes, class equation), Sylow theorems, polynomial rings and field extensions, finite fields, and the structure theorem for finite abelian groups. The entire manual is structured around 20 selected exercises, systematically organizing core concepts, commonly used theorems, solution steps, and common pitfalls for each knowledge module, accompanied by verification knowledge prompts. It is suitable for learning, reviewing, and automated problem-solving verification in abstract algebra courses.

---

## Knowledge System

### Module 1: Basic Concepts of Groups

#### Core Concepts

- **Definition of a group**: A non-empty set $G$ equipped with a binary operation satisfying (1) associativity; (2) existence of an identity element $e$; (3) every element has an inverse.
- **Abelian group (commutative group)**: If for any $a,b \in G$, $ab = ba$.
- **Cyclic group**: $G = \langle g \rangle = \{g^k \mid k \in \mathbb{Z}\}$. If $|G| = n$, then $G \cong \mathbb{Z}_n$ (additive group).
- **Order of an element**: The smallest positive integer $n$ such that $a^n = e$ (multiplicative notation) or $n \cdot a = 0$ (additive notation), denoted $\mathrm{ord}(a)$.
- **In a finite group, the order of any element must divide the group order** (corollary of Lagrange's theorem).

#### Commonly Used Formulas

1. **Order of element $a$ in the additive cyclic group $\mathbb{Z}_n$**:
   $$\mathrm{ord}(a) = \frac{n}{\gcd(a, n)}$$
   where $\gcd$ denotes the greatest common divisor.

2. **Order of $g^k$ in the cyclic group $G = \langle g \rangle$**:
   $$\mathrm{ord}(g^k) = \frac{n}{\gcd(k, n)}, \quad \text{where } n = |G|$$

3. **Order of a permutation**: Decompose the permutation into a product of disjoint cycles; the order of cycle $(a_1\ a_2\ \cdots\ a_k)$ is $k$, and the order of the entire permutation is the least common multiple of the orders of the cycles:
   $$\mathrm{ord}(\sigma) = \mathrm{lcm}(\ell_1, \ell_2, \ldots, \ell_r)$$
   where $\ell_i$ is the length of each disjoint cycle.

4. **Conjugation of permutations**: $\tau \sigma \tau^{-1}$ replaces each letter $i$ in the cycle decomposition of $\sigma$ with $\tau(i)$.

#### Solution Steps

**Computing the order of an element in a cyclic group:**
1. Write down the group and its order $n$.
2. Compute $\gcd(a, n)$.
3. The order is $n / \gcd(a, n)$.
4. Verify: $(\text{order}) \cdot a \equiv 0 \pmod{n}$ (additive).

**Computing the order of a permutation:**
1. Write the permutation as a product of disjoint cycles.
2. Take the least common multiple (lcm) of the cycle lengths.

**Proof problems (e.g., $a^2=e \Rightarrow G \text{ is an abelian group}$):**
1. State the given condition: For any $a \in G$, $a^2 = e$ (i.e., $a = a^{-1}$).
2. Take arbitrary $a, b \in G$, consider $(ab)^2 = e$, expand to $abab = e$.
3. Use $a^2 = e$ and $b^2 = e$ to cancel $a$ and $b$: left-multiply by $a$ and right-multiply by $b$ to obtain $ba = ab$.

**Proof problem (subgroups of cyclic groups are also cyclic):**
1. Let $G = \langle g \rangle$, $H \le G$.
2. If $H = \{e\}$, then $H$ is the trivial cyclic group.
3. Otherwise take $n = \min\{k > 0 \mid g^k \in H\}$ (the smallest positive exponent in $H$).
4. Prove $H = \langle g^n \rangle$ using division with remainder: For any $g^m \in H$, write $m = qn + r$ ($0 \le r < n$), then $g^r = g^{m - qn} \in H$; by the minimality of $n$, $r = 0$, hence $g^m = (g^n)^q$.

#### Corresponding Exercises

- **idx 0**: Find the order of element $12$ in $\mathbb{Z}_{30}$ — formula $\mathrm{ord}(a) = 30/\gcd(12,30)$
- **idx 1**: Find the order of permutation $(1\ 2\ 3)(4\ 5)$ in $S_5$ — lcm(3, 2) = 6
- **idx 3**: Find all subgroups of $\mathbb{Z}_{18}$ — one-to-one correspondence between positive divisors and subgroups
- **idx 14**: Prove: If $a^2 = e$ holds for all $a$, then $G$ is an abelian group
- **idx 15**: Prove: Subgroups of cyclic groups are also cyclic

---

### Module 2: Subgroups and Quotient Groups

#### Core Concepts

- **Subgroup**: $H \subseteq G$ and $H$ is also a group under the operation of $G$. Equivalent to $H \neq \varnothing$, and for any $a, b \in H$, $ab^{-1} \in H$ (subgroup test theorem).
- **Cosets**: Left coset $aH = \{ah \mid h \in H\}$, right coset $Ha = \{ha \mid h \in H\}$.
- **Normal subgroup**: $H \trianglelefteq G$ if and only if for any $g \in G$, $gHg^{-1} = H$ (left cosets = right cosets).
- **Quotient group**: If $H \trianglelefteq G$, then $G/H$ forms a group under the coset operation $(aH)(bH) = (ab)H$.
- **Lagrange's theorem**: If $H \le G$ (finite group), then $|G| = |H| \cdot [G:H]$, where $[G:H]$ is the index of $H$ in $G$ (number of cosets).

#### Commonly Used Formulas

1. **Lagrange's theorem**: $|G| = |H| \cdot [G:H]$
2. **Order of a subgroup**: $|H| \mid |G|$ (the order of $H$ divides the order of $G$)
3. **Order of a coset**: $|aH| = |H|$ (each coset is equipotent to the subgroup)
4. **Order of a quotient group**: $|G/H| = |G| / |H|$ (when $H \trianglelefteq G$)
5. **Subgroups of cyclic group $\mathbb{Z}_n$**: In one-to-one correspondence with the positive divisors of $n$. For each positive divisor $d$, there exists a unique subgroup $\langle n/d \rangle$ of order $d$.
6. **Order of an element in a direct product**: In $G_1 \times G_2$, $\mathrm{ord}((a,b)) = \mathrm{lcm}(\mathrm{ord}(a), \mathrm{ord}(b))$.

#### Solution Steps

**Finding the subgroup lattice:**
1. List all positive divisors of $n$.
2. For each positive divisor $d$, write down the subgroup $\langle n/d \rangle$.
3. Verify that the number of subgroups equals the number of positive divisors of $n$ (also equal to $\tau(n)$).

**Finding coset decomposition:**
1. Determine $|H|$ and $[G:H] = |G|/|H|$.
2. Select $[G:H]$ representatives from $G$ (usually $0, 1, \ldots, [G:H]-1$).
3. Construct all cosets $a + H$ (additive group) or $aH$ (multiplicative group).
4. Verify that the union of all cosets equals $G$ and they are pairwise disjoint.

**Finding the order of a quotient group:**
1. Compute $|G|$ (the order of a direct product is the product of the orders of its factors).
2. Compute $|H|$ (the lcm of the orders of the generators in each component of the direct product).
3. $|G/H| = |G| / |H|$.

**Proof problem (subgroup of index 2 is normal):**
1. $[G:H] = 2$ means $G$ has exactly two left cosets $H$ and $gH$ ($g \notin H$), and exactly two right cosets $H$ and $Hg$.
2. If $g \in H$, clearly $gHg^{-1} = H$.
3. If $g \notin H$, then $gH = G \setminus H = Hg$, hence $gHg^{-1} = H$.
4. By definition, $H \trianglelefteq G$.

#### Corresponding Exercises

- **idx 4**: Find all cosets of $H = \langle 5 \rangle$ in $\mathbb{Z}_{15}$
- **idx 6**: Find the order of the quotient group $(\mathbb{Z}_4 \times \mathbb{Z}_6) / \langle(2,3)\rangle$
- **idx 16**: Prove: A subgroup of index 2 must be a normal subgroup

---

### Module 3: Group Homomorphisms and Isomorphism Theorems

#### Core Concepts

- **Group homomorphism**: A map $\varphi: G \to H$ satisfying $\varphi(ab) = \varphi(a)\varphi(b)$ for all $a, b \in G$.
- **Kernel**: $\ker(\varphi) = \{g \in G \mid \varphi(g) = e_H\}$. $\ker(\varphi) \trianglelefteq G$.
- **Image**: $\operatorname{im}(\varphi) = \{\varphi(g) \mid g \in G\}$. $\operatorname{im}(\varphi) \le H$.
- **First isomorphism theorem**: $G / \ker(\varphi) \cong \operatorname{im}(\varphi)$.

#### Commonly Used Formulas

For a homomorphism between cyclic groups $\varphi: \mathbb{Z}_m \to \mathbb{Z}_n$ defined by $\varphi(1) = k$ (i.e., $\varphi(x) = kx \bmod n$):

1. **Kernel**: $\ker(\varphi) = \{x \in \mathbb{Z}_m \mid kx \equiv 0 \pmod{n}\} = \{x \mid n \mid kx\}$
   - Specifically: $\ker(\varphi) = \langle m / \gcd(m, n/\gcd(k,n)) \rangle$; usually directly solve for the solution set of $n \mid kx$ modulo $m$.
   - Compute $|\ker(\varphi)| = m / \gcd(m, n/\gcd(k,n))$; as a subgroup of $\mathbb{Z}_m$, $\ker(\varphi)$ is generated by $m / |\ker(\varphi)|$.

2. **Image**: $\operatorname{im}(\varphi) = \{kx \bmod n \mid x \in \mathbb{Z}_m\} = \langle \gcd(k, n) \rangle$ (as a subgroup of $\mathbb{Z}_n$).

3. **Fundamental homomorphism theorem**: $|G| = |\ker(\varphi)| \cdot |\operatorname{im}(\varphi)|$.

#### Solution Steps

**Finding the kernel and image of a cyclic group homomorphism:**
1. Determine the homomorphism $\varphi: \mathbb{Z}_m \to \mathbb{Z}_n$, $\varphi(1) = k$.
2. Find the image: $\operatorname{im}(\varphi) = \langle \gcd(k, n) \rangle$, with order $n / \gcd(k, n)$.3. Find the kernel: $\ker(\varphi) = \{x \in \mathbb{Z}_m \mid kx \equiv 0 \pmod{n}\}$.
   - The condition is equivalent to $n \mid kx$, i.e., $\frac{n}{\gcd(k,n)} \mid x$.
   - In $\mathbb{Z}_m$, $\ker(\varphi) = \langle \frac{n}{\gcd(k,n)} \rangle$ (needs to be considered modulo $m$, actually $\langle \frac{n}{\gcd(k,n)} \bmod m \rangle$).
4. Verify $|\ker(\varphi)| \cdot |\operatorname{im}(\varphi)| = m$.

**Proof of the First Isomorphism Theorem:**
1. Let $K = \ker(\varphi)$, define $\psi: G/K \to \operatorname{im}(\varphi)$, $\psi(gK) = \varphi(g)$.
2. Verify well-definedness: If $g_1K = g_2K$, then $g_1^{-1}g_2 \in K$, so $\varphi(g_1) = \varphi(g_2)$.
3. Verify homomorphism property: $\psi(g_1K \cdot g_2K) = \psi(g_1g_2K) = \varphi(g_1g_2) = \varphi(g_1)\varphi(g_2) = \psi(g_1K)\psi(g_2K)$.
4. Verify injectivity: $\psi(gK) = e \Rightarrow \varphi(g) = e \Rightarrow g \in K \Rightarrow gK = K$.
5. Verify surjectivity: For any $h \in \operatorname{im}(\varphi)$, there exists $g \in G$ such that $\varphi(g) = h$, then $\psi(gK) = h$.
6. Conclusion: $\psi$ is an isomorphism.

#### Corresponding Exercises

- **idx 5**: Find the kernel and image of $\varphi: \mathbb{Z}_{12} \to \mathbb{Z}_8$ ($\varphi(1)=2$)
- **idx 19**: Prove the first isomorphism theorem for groups $G/\ker(\varphi) \cong \operatorname{im}(\varphi)$

---

### Module 4: Symmetric Groups and Group Actions

#### Core Concepts

- **Symmetric group $S_n$**: The group consisting of all permutations of $n$ elements, $|S_n| = n!$.
- **Cycle**: A cycle of length $k$, $(a_1\ a_2\ \cdots\ a_k)$, denotes $a_1 \to a_2 \to \cdots \to a_k \to a_1$.
- **Product of disjoint cycles**: Every permutation in $S_n$ can be uniquely decomposed into a product of disjoint cycles.
- **Cycle type**: A partition of the positive integer $n$ recorded as the lengths of the disjoint cycles (arranged in ascending or descending order). For example, in $S_4$, the cycle type $(2,1,1)$ represents one transposition plus two fixed points.
- **Conjugacy class**: Two permutations in $S_n$ are conjugate if and only if they have the same cycle type.
- **Class equation**: $|G| = \sum [G : C_G(g_i)]$, where $g_i$ ranges over representatives of conjugacy classes, and $C_G(g_i)$ is the centralizer of $g_i$.

#### Common Formulas

1. **Size of a conjugacy class**: For cycle type $1^{c_1} 2^{c_2} \cdots n^{c_n}$ (with $c_i$ cycles of length $i$), the size of its conjugacy class is:
   $$\frac{n!}{1^{c_1} 2^{c_2} \cdots n^{c_n} \cdot c_1! c_2! \cdots c_n!}$$

2. **Number of conjugacy classes in $S_n$ = number of partitions of $n$, $p(n)$**.

3. **Order of a cycle**: The order of a cycle of length $k$ is $k$.

4. **Order of a permutation**: $\mathrm{ord}(\sigma) = \mathrm{lcm}(\ell_1, \ldots, \ell_r)$.

5. **Conjugacy classes of $S_4$ (5 classes)**:
   - $(1)(2)(3)(4)$: identity, size 1
   - $(1\ 2)$: transposition, size $C_4^2 = 6$
   - $(1\ 2\ 3)$: 3-cycle, size $2 \cdot C_4^3 = 8$
   - $(1\ 2)(3\ 4)$: two disjoint transpositions, size 3
   - $(1\ 2\ 3\ 4)$: 4-cycle, size 6
   - Class equation: $24 = 1 + 6 + 8 + 3 + 6$

#### Solution Steps

**Finding conjugacy classes and the class equation in symmetric groups:**
1. List all integer partitions of $n$ (each partition corresponds to a cycle type).
2. Select a representative element for each cycle type.
3. Calculate the size of the conjugacy class corresponding to each cycle type (using formulas or combinatorial counting).
4. Verify the class equation: the sum of the sizes of all conjugacy classes equals $|S_n| = n!$.

**Finding the order of a permutation:**
1. Decompose the permutation into a product of disjoint cycles.
2. Take the least common multiple of the lengths of the cycles.

#### Corresponding Exercises

- **idx 1**: Compute the order of $(1\ 2\ 3)(4\ 5)$ in $S_5$ — lcm(3, 2)
- **idx 10**: Find the number of conjugacy classes, representatives, and the class equation of $S_4$

#### Competition Extension: Structure of the Dihedral Group $D_8$

The dihedral group $D_8 = \langle r, s \mid r^4 = s^2 = e, srs = r^{-1} \rangle$ is a non-Abelian group of order 8, and its structure is a high-frequency test point in competitions.

**Element classification**:
- Rotation subgroup $\langle r \rangle \cong \mathbb{Z}_4$: $\{e, r, r^2, r^3\}$ (4 elements, where $\mathrm{ord}(r) = 4$, $\mathrm{ord}(r^2) = 2$).
- Reflection elements: $\{s, sr, sr^2, sr^3\}$ (4 elements, each of order 2, i.e., involutions).

**Center**: $Z(D_8) = \{e, r^2\}$ (only 2 elements). $r^2$ commutes with all elements, because $r^2 s = s r^{-2} = s r^2$.

**Commutator subgroup and Abelianization**:
- $D_8' = [D_8, D_8] = \langle r^2 \rangle \cong \mathbb{Z}_2$ (generated by the commutator $[r, s] = r s r^{-1} s^{-1} = r^2$).
- Abelianization $D_8/D_8' \cong \mathbb{Z}_2 \times \mathbb{Z}_2$ (Klein four-group of order 4).

**Subgroup structure** (10 subgroups):
| Subgroup | Order | Normality | Description |
|------|----|--------|------|
| $\{e\}$ | 1 | Normal | Trivial subgroup |
| $\langle r^2 \rangle = \{e, r^2\}$ | 2 | Normal | Center subgroup |
| $\langle s \rangle = \{e, s\}$ | 2 | Non-normal | Reflection subgroup |
| $\langle sr \rangle = \{e, sr\}$ | 2 | Non-normal | Reflection subgroup |
| $\langle sr^2 \rangle = \{e, sr^2\}$ | 2 | Non-normal | Reflection subgroup |
| $\langle sr^3 \rangle = \{e, sr^3\}$ | 2 | Non-normal | Reflection subgroup |
| $\langle r \rangle \cong \mathbb{Z}_4$ | 4 | Normal | Index 2 |
| $\{e, r^2, s, sr^2\} \cong \mathbb{Z}_2 \times \mathbb{Z}_2$ | 4 | Normal | Klein four-group |
| $\{e, r^2, sr, sr^3\} \cong \mathbb{Z}_2 \times \mathbb{Z}_2$ | 4 | Normal | Klein four-group |
| $D_8$ itself | 8 | Normal | Trivial |

---

### Module 5: Sylow Theorems

#### Core Concepts

- **Sylow $p$-subgroup**: Let $|G| = p^k \cdot m$ ($p \nmid m$), then a subgroup of $G$ of order $p^k$ is called a Sylow $p$-subgroup.
- **$n_p$**: The number of Sylow $p$-subgroups in $G$.

#### The Three Sylow Theorems

**Sylow's First Theorem (Existence)**: If $p^k \mid |G|$, then there exists a subgroup of order $p^k$; in particular, Sylow $p$-subgroups exist.

**Sylow's Second Theorem (Conjugacy)**: All Sylow $p$-subgroups are conjugate to each other.

**Sylow's Third Theorem (Counting)**:
1. $n_p \equiv 1 \pmod{p}$
2. $n_p \mid m$ (where $|G| = p^k \cdot m$, $p \nmid m$)

#### Common Formulas

1. **Constraints on $n_p$**: $n_p \equiv 1 \pmod{p}$ and $n_p \mid m$
2. **Sylow 2-subgroups of $S_4$**: $|S_4| = 24 = 2^3 \times 3$, the order of a $p$-subgroup is $2^3 = 8$.
   - $n_2 \equiv 1 \pmod{2}$, $n_2 \mid 3$ $\Rightarrow$ $n_2 \in \{1, 3\}$
   - Exclude $n_2 = 1$ by verification (otherwise the unique Sylow 2-subgroup would be normal in $S_4$, but $S_4$ has at least 2 distinct subgroups of order 8, each isomorphic to $D_4$)
   - Thus $n_2 = 3$

#### Solution Steps

**Finding the number of Sylow $p$-subgroups:**
1. Factorize $|G| = p^k \cdot m$ ($p \nmid m$).
2. List all possible values satisfying $n_p \equiv 1 \pmod{p}$ and $n_p \mid m$.
3. If the possible values are not unique, eliminate them by the following methods:
   - Check whether there is reason to exclude $n_p = 1$ (e.g., the group is not a $p$-group and the trivial group does not contain the alternating group).
   - Use structural information about Sylow subgroups (e.g., list them when the isomorphism type of the subgroup is known).
   - Use arguments involving group actions (e.g., the action of $G$ on the conjugacy class of Sylow $p$-subgroups induces a homomorphism to $S_{n_p}$).

#### Corresponding Exercises

- **idx 12**: Find the number $n_2$ of Sylow 2-subgroups in $S_4$

---

### Module 6: Fundamentals of Ring Theory

#### Core Concepts

- **Ring**: A non-empty set $R$ equipped with addition (an Abelian group) and multiplication (satisfying associativity and distributivity). It does not necessarily have a multiplicative identity (if required, it is called a unital ring).
- **Zero divisor**: A non-zero element $a \in R$ is called a zero divisor if there exists a non-zero $b \in R$ such that $ab = 0$ (or $ba = 0$).
- **Integral domain**: A commutative unital ring with no non-zero zero divisors.
- **Unit (invertible element)**: $a \in R$ is called a unit if there exists $b \in R$ such that $ab = ba = 1$.
- **Field**: A commutative unital ring in which every non-zero element is a unit.
- **Ideal**: A subset $I \subseteq R$ that is an additive subgroup and satisfies $ra \in I$ for any $r \in R, a \in I$ (left ideal) and $ar \in I$ (right ideal).
- **Quotient ring**: $R/I$, where elements are additive cosets.
- **Maximal ideal**: A proper ideal $M \subsetneq R$ such that there is no ideal $I$ satisfying $M \subsetneq I \subsetneq R$. Equivalent to $R/M$ being a field.
- **Prime ideal**: A proper ideal $P$ such that if $ab \in P$, then $a \in P$ or $b \in P$. Equivalent to $R/P$ being an integral domain.

#### Common Formulas

1. **Zero divisors in $\mathbb{Z}_n$**: A non-zero element $a$ is a zero divisor if and only if $\gcd(a, n) > 1$.
2. **Units in $\mathbb{Z}_n$**: $a$ is a unit if and only if $\gcd(a, n) = 1$.
3. **$\mathbb{Z}_n$ is a field if and only if $n$ is prime**.
4. **Ideal $\langle 2, x \rangle$ in $\mathbb{Z}[x]$**:
   - $\mathbb{Z}[x] / \langle 2, x \rangle \cong \mathbb{Z}_2$ (because $x \equiv 0$ and coefficients are reduced modulo 2)
   - $\mathbb{Z}_2$ is a field, so $\langle 2, x \rangle$ is a maximal ideal (also a prime ideal).

#### Solution Steps

**Finding all zero divisors in $\mathbb{Z}_n$:**
1. For each non-zero $a \in \{1, 2, \ldots, n-1\}$, compute $\gcd(a, n)$.
2. If $\gcd(a, n) > 1$, then $a$ is a zero divisor.
3. If $\gcd(a, n) = 1$, then $a$ is a unit (invertible element) rather than a zero divisor.

**Determining maximal ideals:**
1. Compute the structure of the quotient ring $R/I$.
2. If $R/I$ is a field, then $I$ is a maximal ideal.
3. If $R/I$ is an integral domain, then $I$ is a prime ideal.
4. Note: In a commutative unital ring, a maximal ideal must be a prime ideal; a prime ideal is not necessarily a maximal ideal.

**Prove that $\mathbb{Z}/n\mathbb{Z}$ is a field if and only if $n$ is prime:**- $( \Rightarrow )$: If $\mathbb{Z}_n$ is a field, then it is an integral domain (no zero divisors). If $n$ is composite, there exist $1 < a, b < n$ such that $n = ab$, then $a \cdot b \equiv 0$ but $a, b \neq 0$, a contradiction.
- $( \Leftarrow )$: If $n$ is prime, for any $a \in \mathbb{Z}_n \setminus \{0\}$, $\gcd(a, n) = 1$. By Bézout's identity, there exist $x, y$ such that $ax + ny = 1$, i.e., $ax \equiv 1 \pmod{n}$, so $a$ has a multiplicative inverse.

#### Corresponding Exercises

- **idx 2**: Find all zero divisors in $\mathbb{Z}_{12}$
- **idx 7**: Determine whether the ideal $\langle 2, x \rangle$ in $\mathbb{Z}[x]$ is a maximal ideal
- **idx 17**: Prove: $\mathbb{Z}/n\mathbb{Z}$ is a field if and only if $n$ is prime

#### Competition Extension: Closed Sets of Integer Roots of Polynomials (Rich Sets)

**Definition**: A subset of integers $S \subseteq \mathbb{Z}$ is called a rich set if there exists a non-constant polynomial $P \in \mathbb{Z}[x]$ such that
$$S = \{a \in \mathbb{Z} : P(a) \in S\}$$
That is, $P$ "repels" all integers in the complement of $S$ outside of $S$, while $S$ itself remains closed under the action of $P$ ($P(S) \subseteq S$ does not necessarily hold, but if the $P$-value of some integer falls in $S$, then that integer must be in $S$).

**Core Conclusions**:
- A finite rich set must be a subset of $\{-1, 0, 1\}$ or its translation (i.e., of the form $\{t-1, t, t+1\}$ or a subset thereof).
- Infinite rich sets have richer structures, but are closely related to arithmetic progressions.
- Discrimination method: Given $S$, one needs to construct a polynomial $P$ such that $P(a) \in S \Rightarrow a \in S$ and the converse also holds (i.e., $a \in S \Rightarrow P(a) \in S$). Common choices include $P(x) = x^k$ or $P(x) = (x-a_1)(x-a_2)\cdots(x-a_k) + x$, among other forms.

**Difference from Fixed Point Sets**:
- If $F = \{a \in \mathbb{Z} : P(a) = a\}$ (the fixed point set), then $F$ is a rich set (take $P$ itself).
- But rich sets go far beyond this: $S = \{-1, 0, 1\}$ is a rich set (take $P(x) = x^3$; note that $P(2)=8 \notin S$, $P(-2)=-8 \notin S$, while $P(1)=1, P(0)=0, P(-1)=-1$ are all in $S$), but it is not the fixed point set of any polynomial.

**Common Problem-Solving Approaches**:
1. For a given $S$, try to construct a polynomial $P$ such that the values of $P$ on $S$ lie within $S$, while values outside $S$ lie outside $S$.
2. Use the monotonicity and growth of $P$ to control the relationship between its range and $S$.
3. For finite sets, use Lagrange interpolation or the polynomial remainder theorem to construct a suitable $P$.

---

### Module 7: Polynomials and Field Extensions

#### Core Concepts

- **Polynomial Ring**: $R[x]$ denotes the ring consisting of all polynomials with coefficients in a ring $R$.
- **Irreducibility**: A polynomial $f \in F[x]$ (where $F$ is a field) is called irreducible if it cannot be factored into a product of two polynomials of lower degree.
- **Eisenstein's Criterion**: If there exists a prime $p$ such that $p \mid a_i$ (for all $i < n$), $p \nmid a_n$, and $p^2 \nmid a_0$, then $f(x)$ is irreducible in $\mathbb{Z}[x]$, and consequently irreducible in $\mathbb{Q}[x]$.
- **Cyclotomic Polynomials**: $\Phi_n(x) = \prod_{\substack{1 \le k \le n \\ \gcd(k,n)=1}} (x - e^{2\pi i k / n})$. $\Phi_n(x) \in \mathbb{Z}[x]$ and is irreducible over $\mathbb{Q}$.
  - $\Phi_5(x) = x^4 + x^3 + x^2 + x + 1 = \frac{x^5 - 1}{x - 1}$
- **Field Extension**: $F \subseteq E$, where $E$ can be regarded as a vector space over $F$, and its dimension is called the extension degree $[E : F]$.
- **Tower Theorem**: If $F \subseteq K \subseteq E$, then $[E : F] = [E : K] \cdot [K : F]$.
- **Simple Extension**: $F(\alpha)$ is the smallest subfield containing both $F$ and $\alpha$. If $\alpha$ is algebraic over $F$ (there exists a non-zero polynomial $f \in F[x]$ such that $f(\alpha) = 0$), then $[F(\alpha) : F] = \deg(m_\alpha(x))$, where $m_\alpha(x)$ is the minimal polynomial of $\alpha$.
- **Splitting Fields Cannot Be Judged Solely by "Adjoining $i$"**: For radical expressions of the roots of $x^4+a$, first write out all roots and the required roots of unity, then compute the degree layer by layer using the Tower Theorem. For example, when a real root $\alpha$ and $\zeta_8$ appear simultaneously, the splitting field is $\mathbb Q(\alpha,\zeta_8)$; $\mathbb Q(\alpha,i)$ generally still lacks $\sqrt2$ and cannot be directly treated as the same field. One must examine the intersection of the root-of-unity field and the radical field, their respective minimal polynomials, and whether they are linearly independent.

#### Commonly Used Formulas

1. **Tower Theorem**: $[E:F] = [E:K][K:F]$
2. **Basis Construction**: If $\{e_i\}$ is a basis of $K$ over $F$, and $\{f_j\}$ is a basis of $E$ over $K$, then $\{e_i f_j\}$ is a basis of $E$ over $F$.
3. **Extension Degree of $\mathbb{Q}(\sqrt{2}, \sqrt{3})$**:
   - $[\mathbb{Q}(\sqrt{2}) : \mathbb{Q}] = 2$ (minimal polynomial $x^2 - 2$)
   - $[\mathbb{Q}(\sqrt{2}, \sqrt{3}) : \mathbb{Q}(\sqrt{2})] = 2$ ($\sqrt{3} \notin \mathbb{Q}(\sqrt{2})$, minimal polynomial $x^2 - 3$)
   - $[\mathbb{Q}(\sqrt{2}, \sqrt{3}) : \mathbb{Q}] = 2 \times 2 = 4$
   - Basis: $\{1, \sqrt{2}, \sqrt{3}, \sqrt{6}\}$

#### Problem-Solving Steps

**Determining the Reducibility of a Polynomial over $\mathbb{Q}$:**
1. Try the rational root test (a rational root must be a factor of the constant term divided by a factor of the leading coefficient).
2. If there are no signs of reducible low-degree factors, check whether it is a cyclotomic polynomial.
3. For cyclotomic polynomials $\Phi_p(x)$ ($p$ prime), use the substitution $x \to x+1$ and then apply Eisenstein's criterion.
4. Alternatively, use reduction modulo $p$ (if it is irreducible over $\mathbb{F}_p$, then it is irreducible over $\mathbb{Q}$).

**Finding the Degree and Basis of a Field Extension:**
1. Use the Tower Theorem for successive extensions.
2. Find the minimal polynomial and degree of each simple extension.
3. Verify whether the newly added element in adjacent extensions belongs to the previous extension (by contradiction).
4. Provide the construction of the basis.

**Finding the Splitting Field (Including Galois Extension Discrimination):**
1. After generating the radical field from one root, list the roots of unity required for the remaining roots (e.g., $\zeta_8$ often appears in quartic radicals).
2. Write it as $F(\alpha,\zeta)$; do not assert in one sentence that the intersection is $F$ just because "the radical field is a real field and the root-of-unity field contains complex numbers"; instead, explicitly check possible quadratic subfields.
3. Use the Tower Theorem to give the degree layer by layer; if $i$ is chosen instead of $\zeta_8$, also explain whether $\sqrt2$ is already in the existing field.
4. Finally, state that the splitting field is the splitting field of a separable polynomial over a characteristic zero field, and thus is a Galois extension.

**Finding the Minimal Polynomial in a Cubic Radical Extension (Power-Reduction Expansion Method):**
1. Let $\alpha = \sqrt[3]{a} + \sqrt[3]{b}$, and consider the field tower $\mathbb{Q} \subseteq \mathbb{Q}(\sqrt[3]{a}) \subseteq \mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b})$.
2. Determine the basis: When $\sqrt[3]{a} \notin \mathbb{Q}(\sqrt[3]{b})$ (i.e., $\sqrt[3]{a}/\sqrt[3]{b}$ is not a cube root of a rational number), the extension degree of $\mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b})$ over $\mathbb{Q}$ is 9, with basis $\{1, \sqrt[3]{a}, \sqrt[3]{b}, \sqrt[3]{a^2}, \sqrt[3]{b^2}, \sqrt[3]{ab}, \sqrt[3]{a^2b}, \sqrt[3]{ab^2}, \sqrt[3]{a^2b^2}\}$.
3. Express $\alpha^k$ ($k = 0, 1, \ldots, 9$) linearly in terms of the basis: successively expand $(\sqrt[3]{a} + \sqrt[3]{b})^k$, and use $\sqrt[3]{a}^3 = a$ and $\sqrt[3]{b}^3 = b$ to reduce powers.
4. Since the dimension of the basis is 9 and $\{1, \alpha, \alpha^2, \ldots, \alpha^9\}$ has 10 elements, they must be linearly dependent. Solve the system of linear equations to obtain the minimal polynomial $m_\alpha(x)$ (usually of degree $\le 9$).
5. Verification: The degree of the minimal polynomial equals $[\mathbb{Q}(\alpha) : \mathbb{Q}]$, and $\mathbb{Q}(\alpha) \subseteq \mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b})$.

#### Corresponding Exercises

- **idx 8**: Determine whether $x^4 + x^3 + x^2 + x + 1$ is reducible over $\mathbb{Q}$
- **idx 11**: Find $[\mathbb{Q}(\sqrt{2}, \sqrt{3}) : \mathbb{Q}]$ and a $\mathbb{Q}$-basis

#### Competition Extension: Power-Reduction Expansion and Minimal Polynomials in Cubic Radical Extensions

Let $\alpha = \sqrt[3]{a} + \sqrt[3]{b}$, and find its minimal polynomial over $\mathbb{Q}$. The core idea is to use the field extension tower $\mathbb{Q} \subseteq \mathbb{Q}(\sqrt[3]{a}) \subseteq \mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b})$ to construct a basis, express $\alpha^k$ linearly in terms of the basis, and then solve for linear relations.

**Key Conclusions**:
- $[\mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b}) : \mathbb{Q}] = 9$ if and only if $\sqrt[3]{a} \notin \mathbb{Q}(\sqrt[3]{b})$ (i.e., $\sqrt[3]{a}/\sqrt[3]{b} \notin \mathbb{Q}$ and the multiplicative relationship among the three is insufficient to reduce the degree).
- If $\sqrt[3]{a}/\sqrt[3]{b} \in \mathbb{Q}$, then the extension degree degenerates to 3 (because one radical can be expressed as a rational multiple of the other).
- Directly cubing $\alpha^3 = a + b + 3\sqrt[3]{ab}(\sqrt[3]{a} + \sqrt[3]{b}) = a + b + 3\sqrt[3]{ab}\,\alpha$ loses information (the resulting relation still contains $\sqrt[3]{ab}$); it needs to be combined with higher powers to eliminate cross terms, ultimately yielding the minimal polynomial.

**Power-Reduction Expansion Steps**:
1. Determine the basis of $\mathbb{Q}(\sqrt[3]{a}, \sqrt[3]{b})$ over $\mathbb{Q}$ (9-dimensional or lower).
2. Compute the coordinate vectors of $\alpha^k$ ($k = 0, 1, \ldots, 9$) under the basis.
3. Solve the system of linear equations $\sum c_k \alpha^k = 0$ to obtain the coefficients of the minimal polynomial.
4. Verify that the resulting polynomial is irreducible over $\mathbb{Q}$ (via reduction modulo $p$ or substitution followed by Eisenstein's criterion).

#### Competition Extension: Splitting Fields, Extension Degrees, and Galois Extension Discrimination

For polynomials of the form $x^n + a$ ($a \in \mathbb{Q}$), find the splitting field and extension degree, and determine whether it is a Galois extension. Take $x^4 + a$ as an example:

**Complete Judgment Process**:
1. **Write out all roots**: The four roots of $x^4 + a = 0$ are $\{\pm\sqrt[4]{-a}, \pm i\sqrt[4]{-a}\}$. Let $\alpha = \sqrt[4]{-a}$, then the roots are $\{\pm\alpha, \pm i\alpha\}$.
2. **Determine the splitting field**: The splitting field is $\mathbb{Q}(\alpha, i)$. Note that $\mathbb{Q}(\alpha, i) = \mathbb{Q}(\alpha, \zeta_8) = \mathbb{Q}(\alpha, \sqrt{2}, i)$, because $i = \zeta_8^2$ and $\sqrt{2}$ can be generated by $\zeta_8$, but $\mathbb{Q}(\alpha, i)$ does not necessarily contain $\sqrt{2}$.
3. **Prove that the degree of the minimal polynomial of $\alpha$ is 4**: Use Eisenstein's criterion (if the prime factors of $a$ satisfy the conditions) or the substitution method to verify that $x^4 + a$ is irreducible over $\mathbb{Q}$.4. **Prove $\mathbb{Q}(\alpha) \cap \mathbb{Q}(i) = \mathbb{Q}$** (linear disjointness): If $\alpha \in \mathbb{Q}(i)$, this leads to a contradiction (real quartic radicals are generally not in quadratic extensions); if $i \in \mathbb{Q}(\alpha)$, one must verify whether $\mathbb{Q}(\alpha)$ contains non-real elements. Typically, the intersection is exactly $\mathbb{Q}$.
5. **Compute the extension degree using the tower theorem**: $[\mathbb{Q}(\alpha, i) : \mathbb{Q}] = [\mathbb{Q}(\alpha, i) : \mathbb{Q}(\alpha)] \cdot [\mathbb{Q}(\alpha) : \mathbb{Q}] = 2 \cdot 4 = 8$ (when linearly disjoint).
6. **Galois extension criterion**: The splitting field is the splitting field of a separable polynomial over a field of characteristic zero, hence it must be a Galois extension.

**Common pitfalls**:
- Do not determine the splitting field merely by "adjoining $i$"; one must verify whether the cyclotomic field and the radical field are linearly disjoint.
- Note that $\mathbb{Q}(\sqrt[4]{-a})$ may already contain quadratic surds such as $\sqrt{2}$ (for example, when $a = 4$, the case $\alpha^2 = 2i$ requires careful analysis).
- For a general $x^n + a$, one must consider whether $\zeta_n$ (a primitive $n$-th root of unity) lies in the radical field.

---

### Module 8: Finite Fields

#### Core Concepts

- **Existence and uniqueness of finite fields**: For each prime power $q = p^n$, there exists a unique finite field with $q$ elements (denoted $\mathbb{F}_q$), and the order of any finite field must be a prime power.
- **Construction of finite fields**: $\mathbb{F}_{p^n} \cong \mathbb{F}_p[x] / (f(x))$, where $f(x)$ is an irreducible polynomial of degree $n$ over $\mathbb{F}_p$.
- **Multiplicative group**: $\mathbb{F}_q^\times = \mathbb{F}_q \setminus \{0\}$ is a cyclic group of order $q-1$.
- **Primitive element**: A generator of the multiplicative group $\mathbb{F}_q^\times$, whose order is $q-1$.

#### Common Formulas

1. **Order of the multiplicative group**: $|\mathbb{F}_q^\times| = q - 1$
2. **$\mathbb{F}_8 = \mathbb{F}_2[x]/(x^3 + x + 1)$**:
   - Let $\alpha$ be the image of $x$ in the quotient ring, satisfying $\alpha^3 + \alpha + 1 = 0$
   - $\mathbb{F}_8^\times$ is a cyclic group of order 7, and 7 is prime
   - If $\alpha \neq 0, 1$, then $\mathrm{ord}(\alpha) = 7$ (in a cyclic group of prime order, the order of any non-identity element equals the group order)

#### Problem-Solving Steps

**Finding the order of an element in a finite field:**
1. Determine the order $q-1$ of the multiplicative group.
2. Factorize $q-1$.
3. For element $\alpha$, verify that $\alpha^{(q-1)/p} \neq 1$ holds for all prime factors $p \mid (q-1)$; then $\alpha$ is a generator of the multiplicative group with order $q-1$.
4. In particular, if $q-1$ is prime, then any nonzero element other than 1 has order $q-1$.

#### Corresponding Exercises

- **idx 9**: Find the order of $\alpha$ in $\mathbb{F}_8 = \mathbb{F}_2[x]/(x^3+x+1)$

---

### Module 9: Classification of Finite Abelian Groups

#### Core Concepts

- **Structure theorem for finite abelian groups**: Every finite abelian group is isomorphic to a direct product of cyclic $p$-groups, and this decomposition is unique up to the order of the cyclic factors (elementary divisors).
- **Elementary divisors**: Decompose $|G|$ into prime powers $|G| = \prod p_i^{e_i}$, then consider the partitions of each prime power $p_i^{e_i}$. Each partition corresponds to a way of decomposing this $p$-part into a direct product of cyclic $p$-groups.
- **Invariant factors**: Merge the elementary divisors in a specific way (taking corresponding cyclic factors for each prime power) to obtain a sequence of factors $d_1 \mid d_2 \mid \cdots \mid d_k$ with $d_1 d_2 \cdots d_k = |G|$.
- **Number of isomorphism classes = $\prod$ (number of partitions of each prime power)**.

#### Common Formulas

For $|G| = 36 = 2^2 \times 3^2$:

1. **Partitions of the 2-part**: The partitions of $4=2^2$ are $\{[4], [2,2]\}$ (2 types)
2. **Partitions of the 3-part**: The partitions of $9=3^2$ are $\{[9], [3,3]\}$ (2 types)
3. **Combination**: $2 \times 2 = 4$ mutually non-isomorphic finite abelian groups:
   - $[4] \times [9] \cong \mathbb{Z}_4 \times \mathbb{Z}_9 \cong \mathbb{Z}_{36}$
   - $[4] \times [3,3] \cong \mathbb{Z}_4 \times \mathbb{Z}_3 \times \mathbb{Z}_3 \cong \mathbb{Z}_3 \times \mathbb{Z}_{12}$
   - $[2,2] \times [9] \cong \mathbb{Z}_2 \times \mathbb{Z}_2 \times \mathbb{Z}_9 \cong \mathbb{Z}_2 \times \mathbb{Z}_{18}$
   - $[2,2] \times [3,3] \cong \mathbb{Z}_2 \times \mathbb{Z}_2 \times \mathbb{Z}_3 \times \mathbb{Z}_3 \cong \mathbb{Z}_6 \times \mathbb{Z}_6$

#### Problem-Solving Steps

**Classify all finite abelian groups of a given order:**
1. Decompose $|G|$ into a product of prime powers $|G| = \prod p_i^{e_i}$.
2. For each $p_i^{e_i}$, list all integer partitions of $e_i$ (i.e., all possible cyclic decompositions of the $p$-part).
3. The combinations of all $p$-parts yield all isomorphism classes.
4. Reduce each combination to its simplest form (using $\mathbb{Z}_a \times \mathbb{Z}_b \cong \mathbb{Z}_{ab}$ when $\gcd(a,b) = 1$).

#### Corresponding Exercises

- **idx 13**: Determine all mutually non-isomorphic finite abelian groups of order 36

---

## General Problem-Solving Methodology

### 1. Problem Type Identification

Upon receiving a problem, first determine:

| Problem Type Characteristics | Corresponding Module |
|---------|---------|
| "Find the order of an element in group XX" / "Order of a permutation" | Module 1: Basic Concepts of Groups |
| "Find all subgroups" / "Coset decomposition" / "Order of quotient group" | Module 2: Subgroups and Quotient Groups |
| "Find the kernel and image of a homomorphism" / "Prove isomorphism theorems" | Module 3: Group Homomorphisms and Isomorphism Theorems |
| "Conjugacy classes" / "Class equation" / "Symmetric group $S_n$" | Module 4: Symmetric Groups and Group Actions |
| "Sylow subgroups" / "$n_p$" | Module 5: Sylow Theorems |
| "Zero divisors" / "Maximal ideals" / "Z_n is a field" | Module 6: Fundamentals of Ring Theory |
| "Polynomial reducibility" / "Degree of field extension" / "Basis" | Module 7: Polynomials and Field Extensions |
| "Finite fields" / "$\mathbb{F}_q$" / "Primitive element" | Module 8: Finite Fields |
| "Abelian group classification" / "Isomorphism classes" / "Structure theorem" | Module 9: Classification of Finite Abelian Groups |
| "Prove a group is abelian" / "Groups satisfying property XX" | Module 1 (Proofs) |
| "Prove properties of subgroups (normality, cyclicity, etc.)" | Module 2 (Proofs) |
| "Prove criteria for integral domains/fields/ideals" | Module 6 (Proofs) |
| "Prove Cauchy's theorem" / "Isomorphism theorems" | Module 3/Others (Proofs) |

### 2. Method Selection

| Problem Type | Primary Method | Alternative Method |
|---------|---------|---------|
| Find order of element in cyclic group | $\mathrm{ord}(a) = n / \gcd(a, n)$ | Verify by successive addition |
| Find order of permutation | Decompose into disjoint cycles, take lcm | Verify by successive powers |
| Find all subgroups | Enumerate positive divisors, corresponding generators | Verify one by one using subgroup criteria |
| Find coset decomposition | Determine number of cosets via Lagrange's theorem, select representatives | Generate by successive addition |
| Find kernel and image of homomorphism | Directly solve congruence equations / $\operatorname{im}(\varphi) = \langle \gcd(k,n) \rangle$ | Exhaustive verification |
| Find conjugacy classes and class equation | List all cycle types (integer partitions), count by formula | Directly compute conjugacy classes |
| Find number of Sylow subgroups | Sylow's third theorem $n_p \equiv 1 \pmod{p}$ and $n_p \mid m$ | Construct explicit subgroups |
| Find zero divisors | Compute $\gcd(a, n)$ | Verify pairwise multiplication |
| Determine maximal ideals | Compute whether $R/I$ is a field | Relationship between prime ideals and maximal ideals |
| Determine polynomial reducibility | Rational root test / Eisenstein criterion | Mod p reduction / Cyclotomic polynomial identification |
| Find degree of field extension and basis | Tower theorem with successive extensions | Directly construct basis |
| Find order of element in finite field | Factorize $q-1$ | Verify each order individually |
| Classify finite abelian groups | Prime power decomposition + partition enumeration | Chinese Remainder Theorem |

### 3. Result Verification

- **Divisibility of orders**: The order of an element must divide the order of the group (Lagrange's theorem)
- **Verification of direct product order**: $|\ker(\varphi)| \cdot |\operatorname{im}(\varphi)| = |G|$ (Fundamental Homomorphism Theorem)
- **Class equation verification**: Sum of sizes of all conjugacy classes = order of the group
- **Coset verification**: Union of all cosets = the group, and they are pairwise disjoint
- **Sylow theorem verification**: $n_p \equiv 1 \pmod{p}$ and $n_p$ divides $m$
- **Abelian group verification**: Product of elementary divisors = order of the group
- **Field extension verification**: Tower theorem $[E:F] = n$, size of basis = $n$
- **Independent verification with sympy**: Verify computational results using independent methods

---

## sympy Verification Techniques

This section provides SymPy verification approaches usable during the Python generation phase, covering core computations in group theory, ring theory, and field theory; note that the reference materials themselves do not provide directly runnable programs.

### Permutation Operations

```python
from sympy.combinatorics import Permutation

# Create a permutation (element in S_5)
sigma = Permutation(0, 1, 2)(3, 4)  # i.e., (1 2 3)(4 5), note sympy uses 0-index

# Find the order of the permutation
order = sigma.order()  # returns 6

# Find the inverse of the permutation
sigma_inv = sigma ** (-1)

# Permutation multiplication (right to left)
tau = Permutation(1, 2)(3, 4)
product = sigma * tau  # apply tau first, then sigma

# Decompose into disjoint cycles
cycles = sigma.cyclic_form  # returns [[0, 1, 2], [3, 4]]

# Verify powers
identity = sigma ** order  # should be the identity permutation
```

### Basic Number Theory Operations

```python
from sympy import gcd, lcm, factorint, divisors, isprime, nextprime

# Greatest common divisor and least common multiple
g = gcd(12, 30)      # 6
l = lcm(3, 2)        # 6

# Integer factorization
f = factorint(36)     # {2: 2, 3: 2}

# Find all positive divisors of n (for subgroup lattice)
divs = divisors(18)   # [1, 2, 3, 6, 9, 18]

# Primality test
isprime(17)           # True
```

### Order of Elements in Cyclic Groups

```python
from sympy import gcd

# In the additive cyclic group Z_n, the order of element a
def order_mod_n(a, n):
    g = gcd(a, n)
    return n // g

# Example: idx 0 - order of 12 in Z_30
order_mod_n(12, 30)  # 5

# Example: idx 3 - all subgroups of Z_18
n = 18
for d in divisors(n):
    generator = n // d
    print(f"Subgroup <{generator}> has order {d}")
```

### Coset Decomposition

```python
from sympy import gcd

# Example: idx 4 - cosets of H=<5> in Z_15
n = 15
H_gen = 5
H_size = n // gcd(H_gen, n)  # 3
num_cosets = n // H_size     # 5

H = [k * H_gen % n for k in range(H_size)]  # [0, 5, 10]
all_cosets = []
for a in range(num_cosets):
    coset = [(a + h) % n for h in H]
    all_cosets.append(coset)
# Verify coverage
all_elements = set()
for c in all_cosets:
    all_elements.update(c)
assert len(all_elements) == n
```### Kernel and Image of Group Homomorphisms

```python
from sympy import gcd

# Example: idx 5 - φ: Z_12 -> Z_8, φ(1)=2
m, n, k = 12, 8, 2

# Image
im_gen = gcd(k, n)  # 2
im_size = n // im_gen  # 4
# im(φ) = <2> ≅ Z_4

# Kernel (manually verified)
ker = [x for x in range(m) if (k * x) % n == 0]  # [0, 4, 8]
ker_size = len(ker)  # 3
# Verify: |ker| * |im| = m
assert ker_size * im_size == m  # 3 * 4 = 12
```

### Zero Divisor Computation

```python
from sympy import gcd

# Example: idx 2 - Zero divisors in Z_12
n = 12
zero_divisors = [a for a in range(1, n) if gcd(a, n) > 1]
# [2, 3, 4, 6, 8, 9, 10]

# Units are elements coprime to n
units = [a for a in range(1, n) if gcd(a, n) == 1]
# [1, 5, 7, 11]
```

### Integer Partitions (for Conjugacy Classes / Abelian Group Classification)

```python
from sympy.utilities.iterables import partitions

# Example: partitions of 4 (conjugacy classes of S_4 / cycle types)
for p in partitions(4):
    print(p)  # {4:1}, {1:1,3:1}, {2:2}, {2:1,1:2}, {1:4}

# Example: Abelian group classification of 36 = 2^2 × 3^2
# Partitions of 2^2: partitions(2) -> {2:1}, {1:2}  (i.e., [4] and [2,2])
# Partitions of 3^2: partitions(2) -> {2:1}, {1:2}  (i.e., [9] and [3,3])
```

### Conjugacy Classes and Class Equation

```python
from sympy.combinatorics import SymmetricGroup

# Conjugacy classes of S_4
S4 = SymmetricGroup(4)
classes = S4.conjugacy_classes()
print(f"Number of conjugacy classes: {len(classes)}")  # 5

# Sizes of each class
class_sizes = [len(c) for c in classes]  # [1, 6, 8, 3, 6]
print(f"Class equation: {sum(class_sizes)} = {' + '.join(map(str, class_sizes))}")
# 24 = 1 + 6 + 8 + 3 + 6
```

### Sylow Subgroups

```python
from sympy.combinatorics import SymmetricGroup
from sympy import factorint

# Sylow 2-subgroup of S_4
S4 = SymmetricGroup(4)
n2 = len(S4.sylow_subgroups(2))  # returns the number of Sylow 2-subgroups
# n2 = 3

# Verify Sylow's Third Theorem
n = 24
p = 2
factorization = factorint(n)
k = factorization[p]  # 3 (i.e., 2³)
m = n // (p ** k)     # 3
# n_p ≡ 1 (mod p) and n_p | m
assert n2 % p == 1 and m % n2 == 0
```

### Polynomial Operations and Irreducibility Testing

```python
from sympy import Poly, symbols, factor
from sympy.polys.specialpolys import cyclotomic_poly
from sympy import cyclotomic_poly

x = symbols('x')

# Construct the cyclotomic polynomial Φ_5(x)
phi5 = cyclotomic_poly(5, x)  # x**4 + x**3 + x**2 + x + 1

# Check irreducibility
from sympy import factor
f = x**4 + x**3 + x**2 + x + 1
factored = factor(f)  # irreducible over Q, returns itself

# Eisenstein criterion verification: substitute x -> x+1
f_shifted = f.subs(x, x+1).expand()  # x^4 + 5*x^3 + 10*x^2 + 10*x + 5
# Take p=5, all coefficients divisible by 5, constant term not divisible by 25, thus f is irreducible
```

### Finite Field Operations

```python
from sympy import GF, Poly, symbols

x = symbols('x')

# Verify x^3 + x + 1 is irreducible over F_2 (used to construct F_8)
f = Poly(x**3 + x + 1, x, modulus=2)
print(f.is_irreducible)  # True

# Construct F_8 = F_2[x]/(x^3 + x + 1)
# F_8^x has 7 elements (prime)
# The order of any non-zero non-identity element is 7

# Verification: in F_8
from sympy.polys.galoistools import gf_irreducible
```

---

## Exercise Index

| idx | Question Type | Difficulty | Topic | Key Knowledge Points | Core Method | Verification Method |
|-----|---------------|------------|-------|----------------------|-------------|---------------------|
| 0 | Computation | Simple | Order of elements in cyclic groups | In $\mathbb{Z}_n$, $\mathrm{ord}(a)=n/\gcd(a,n)$ | Compute $\gcd(12,30)=6$, order=$30/6=5$ | `gcd` + division |
| 1 | Computation | Simple | Order of permutations | Cycle decomposition, order = lcm of cycle lengths | $(1\ 2\ 3)$ order=3, $(4\ 5)$ order=2, lcm=6 | `Permutation.order()` |
| 2 | Computation | Simple | Zero divisors in rings | In $\mathbb{Z}_n$, $a$ is a zero divisor $\Leftrightarrow \gcd(a,n)>1$ | Compute $\gcd(a,12)$ one by one, collect those with $\gcd>1$ | `gcd` iteration |
| 3 | Computation | Medium | Subgroup lattice | Subgroups of cyclic groups correspond one-to-one to positive divisors | Enumerate positive divisors 1,2,3,6,9,18 of 18, corresponding to subgroups $\langle 18/d\rangle$ | `divisors` + generators |
| 4 | Computation | Medium | Coset decomposition | Lagrange's theorem, $[G:H]=|G|/|H|$ | $|H|=3$, $[G:H]=5$, enumerate 5 cosets | Lagrange's theorem + enumeration verification |
| 5 | Computation | Medium | Kernel and image of group homomorphisms | $\varphi:\mathbb{Z}_m\to\mathbb{Z}_n$, $\varphi(1)=k$ | $\ker=\{x:n\mid kx\}$, $\operatorname{im}=\langle\gcd(k,n)\rangle$ | Congruence equations + `gcd` |
| 6 | Computation | Medium | Order of quotient groups | Order of element in direct product = lcm, order of quotient group = $|G|/|H|$ | $|G|=24$, $\mathrm{ord}((2,3))=lcm(2,2)=2$, $|G/H|=12$ | `lcm` + division |
| 7 | Computation | Medium | Maximal ideal determination | $R/I$ is a field $\Leftrightarrow I$ is a maximal ideal | $\mathbb{Z}[x]/\langle2,x\rangle\cong\mathbb{Z}_2$ is a field | Quotient ring structure analysis |
| 8 | Computation | Medium | Polynomial irreducibility | Eisenstein criterion, cyclotomic polynomial $\Phi_n(x)$ | Identify $\Phi_5(x)$, substitute $x\to x+1$ then apply Eisenstein ($p=5$) | `cyclotomic_poly` + Eisenstein |
| 9 | Computation | Medium | Multiplicative group of finite fields | $\mathbb{F}_q^\times$ is a cyclic group of order $q-1$ | $|\mathbb{F}_8^\times|=7$ (prime), order of non-identity element = 7 | Multiplicative group order analysis |
| 10 | Computation | Medium | Conjugacy classes and class equation | Cycle type determines conjugacy class | Enumerate 5 cycle types, compute class sizes, $24=1+6+8+3+6$ | `SymmetricGroup.conjugacy_classes()` |
| 11 | Computation | Medium | Degree of field extension and basis | Tower theorem $[E:F]=[E:K][K:F]$ | Successive extensions: $[\mathbb{Q}(\sqrt{2}):\mathbb{Q}]=2$, then prove $\sqrt{3}\notin\mathbb{Q}(\sqrt{2})$ | Field extension logic + tower theorem |
| 12 | Computation | Hard | Sylow subgroups | Sylow's third theorem: $n_p\equiv1\pmod{p}$, $n_p\mid m$ | $n_2\equiv1\pmod{2}$ and $n_2\mid3$ yields $n_2\in\{1,3\}$, exclude $n_2=1$ | `SymmetricGroup.sylow_subgroups()` |
| 13 | Computation | Hard | Classification of finite Abelian groups | Structure theorem, integer partitions of prime powers | $36=2^2\times3^2$, 2-part has 2 partitions × 3-part has 2 partitions = 4 types | `partitions` + Chinese Remainder Theorem |
| 14 | Proof | Simple | Basic group properties | $a^2=e$ holds for any $a$ | Expand $(ab)^2=e$, use $a=a^{-1}$ to derive $ba=ab$ | Algebraic derivation verification |
| 15 | Proof | Medium | Cyclic group structure | Any subgroup of a cyclic group is also cyclic | Take the smallest positive exponent in $H$ as generator, prove via division algorithm | Division algorithm logic |
| 16 | Proof | Medium | Normal subgroup determination | A subgroup of index 2 must be a normal subgroup | Case analysis for $g\in H$ and $g\notin H$, coset covering argument | Coset decomposition logic |
| 17 | Proof | Medium | Basic ring properties | $\mathbb{Z}_n$ is a field $\Leftrightarrow n$ is prime | Necessity: by contradiction, composite case has zero divisors; sufficiency: Bezout identity | Integral domain/field definition logic |
| 18 | Proof | Hard | Cauchy's theorem | In Abelian groups, $p\mid|G|\Rightarrow\exists$ element of order $p$ | Induction: case 1 $p\mid m$ uses powers; case 2 $p\nmid m$ uses quotient group | Mathematical induction + quotient group |
| 19 | Proof | Hard | First isomorphism theorem | $G/\ker(\varphi)\cong\operatorname{im}(\varphi)$ | Construct $\psi(gK)=\varphi(g)$, prove well-defined/homomorphism/injective/surjective | Four-step mapping construction |
| 20 | Computation | Medium | Dihedral group $D_8$ structure | $D_8=\langle r,s\mid r^4=s^2=e,srs=r^{-1}\rangle$, center, commutator subgroup, subgroup lattice | Element classification (rotations and reflections), center $Z(D_8)=\{e,r^2\}$, $D_8'=\langle r^2\rangle$, list 10 subgroups and determine normality | Group theory definition verification |

---

## Common Errors and Pitfalls

### Basic Group Concepts
1. **Confusing order formulas for additive and multiplicative groups**: In the additive cyclic group $\mathbb{Z}_n$, $\mathrm{ord}(a) = n/\gcd(a,n)$; in the multiplicative cyclic group $\langle g \rangle$, $\mathrm{ord}(g^k) = n/\gcd(k,n)$. The former is the representation of the element itself, the latter is an exponent.
2. **Forgetting to decompose cycles when computing the order of a permutation**: The order of a permutation is not its length or the number of cycles; it must be the least common multiple (lcm) of the lengths of all disjoint cycles.
3. **Confusing the order of an element with the order of a group**: The order of an element divides the order of the group (corollary of Lagrange's theorem), but they are generally not equal. In $\mathbb{Z}_n$, the order of a generator equals $n$, while the order of a non-generator is strictly less than $n$.
4. **Ignoring the identity element in proofs**: When proving subgroups of cyclic groups are cyclic, the trivial case $H = \{e\}$ must be handled separately; otherwise, subsequently taking $\min\{k>0\}$ might yield an empty set.
5. **$a^2=e$ does not imply $a=e$**: The statement $a^2=e$ only means $a = a^{-1}$ (self-inverse), not that $a$ must be the identity. Counterexample: in $S_3$, the transposition $(1\ 2)^2 = e$ but $(1\ 2) \neq e$.

### Subgroups and Quotient Groups
6. **Confusing the notation of quotient groups and cosets**: In additive groups, cosets are denoted $a+H$, and elements of the quotient group are sets of cosets; in multiplicative groups, cosets are denoted $aH$. Do not confuse cosets with group elements.
7. **The converse of Lagrange's theorem does not hold**: $|H| \mid |G|$ does not imply that $H$ must be a subgroup of $G$ (the classic counterexample is that $A_4$ has no subgroup of order 6). Only cyclic groups guarantee that each divisor corresponds to a subgroup.
8. **Computing the order of elements in a direct product**: $\mathrm{ord}((a,b)) = \mathrm{lcm}(\mathrm{ord}(a), \mathrm{ord}(b))$, not $\mathrm{ord}(a) \cdot \mathrm{ord}(b)$, nor $\gcd$.9. **Coset Coverage in Normal Subgroup Testing**: When $[G:H]=2$, $g \notin H$ implies $gH = G \setminus H$. This critical reasoning relies on the index-2 condition (there are only two cosets).

### Group Homomorphism and Isomorphism Theorems
10. **Kernel Computation in Cyclic Group Homomorphisms**: For $\varphi: \mathbb{Z}_m \to \mathbb{Z}_n$ with $\varphi(1)=k$, the kernel is $\{x \in \mathbb{Z}_m : kx \equiv 0 \pmod{n}\}$. One must simultaneously satisfy the divisibility condition modulo $n$ and the range constraint modulo $m$. The generator of the kernel is $m / \gcd(m, n/\gcd(k,n))$.
11. **Well-Definedness Verification of Maps in Isomorphism Theorems**: $g_1K = g_2K \Leftrightarrow g_1^{-1}g_2 \in K = \ker(\varphi)$. This is the most critical step; one must use the definition of the kernel to establish the link. Omitting the well-definedness verification is a common error.
12. **Distinguishing Monomorphisms from Injective Maps**: $\ker(\varphi) = \{e\}$ is equivalent to $\varphi$ being a monomorphism (injective homomorphism), not surjective.

### Symmetric Groups and Group Actions
13. **Non-Uniqueness of Conjugacy Class Representatives**: A conjugacy class can have multiple representatives; the standard practice is to select representatives by cycle type. However, the conjugacy class size computed from different representatives must be the same.
14. **Factorial Factors in the Denominator of the Conjugacy Class Size Formula**: For cycle type $1^{c_1}2^{c_2}\cdots n^{c_n}$, the denominator includes not only $i^{c_i}$ but also $c_i!$ (permutation redundancy among cycles of the same length). Omitting $c_i!$ yields an incorrect size.
15. **The Class Equation is Not a Trivial Identity Summing All Conjugacy Class Sizes**: The class equation is actually $|G| = |Z(G)| + \sum [G:C_G(g_i)]$ (where $g_i$ range over representatives of non-central conjugacy classes); it provides information about the group center and structural constraints.
32. **Confusing the Center of $D_8$ with All Involutions**: In the dihedral group $D_8 = \langle r, s \mid r^4 = s^2 = e, srs = r^{-1} \rangle$ (order 8), all reflections $\{s, sr, sr^2, sr^3\}$ have order 2 (involutions), but this does not imply they belong to the center. The center of $D_8$ contains only $\{e, r^2\}$ (2 elements), because only $r^2$ commutes with all elements. The commutator subgroup $D_8' = \langle r^2 \rangle \cong \mathbb{Z}_2$, and the abelianization $D_8/D_8' \cong \mathbb{Z}_2 \times \mathbb{Z}_2$ is the Klein four-group of order 4.

### Sylow Theorems
16. **$n_p$ May Equal Neither 1 Nor a Very Large Number**: $n_p \equiv 1 \pmod{p}$ and $n_p \mid m$ are necessary conditions, but together they may still exclude many values; the remaining values may not be unique, requiring further argumentation.
17. **Confusing $n_p \mid |G|$ with $n_p \mid m$**: The second part of Sylow's Third Theorem states $n_p \mid m$ (where $m$ is the part of $|G|$ after removing the $p$-power factor), not $n_p \mid |G|$.
18. **Excluding $n_p = 1$ Requires Justification**: One cannot arbitrarily exclude $n_p = 1$; specific reasoning must be given (e.g., there exist multiple distinct Sylow subgroups, or the group is not nilpotent, etc.).

### Ring Theory
19. **Confusing Zero Divisors with Non-Units**: In a general ring, not every non-unit is a zero divisor. However, in $\mathbb{Z}_n$, the two are exactly complementary ($\gcd(a,n) > 1$ for zero divisors, $\gcd(a,n) = 1$ for units).
20. **Differences Between Ideals in $\mathbb{Z}[x]$ and $\mathbb{Q}[x]$**: $\mathbb{Z}[x]$ is not a principal ideal domain (PID); for example, $\langle 2, x \rangle$ is not a principal ideal. In $\mathbb{Q}[x]$ (which is a PID), maximal ideals are generated by irreducible polynomials.
21. **Confusing Maximal Ideals with Prime Ideals**: In a commutative ring with unity, every maximal ideal is prime, but the converse does not hold. $\langle x \rangle$ is a prime ideal in $\mathbb{Z}[x]$ but not a maximal ideal (the quotient ring $\mathbb{Z}[x]/\langle x \rangle \cong \mathbb{Z}$ is an integral domain but not a field).
22. **Definition of a Field**: A field must have a multiplicative identity $1 \neq 0$, and every nonzero element must have a multiplicative inverse. Sometimes the condition $1 \neq 0$ is overlooked (which excludes the zero ring).
30. **Confusing the "Range" of a Rich Set with Its "Fixed Point Set"**: The definition of a rich set is $S = \{a \in \mathbb{Z} : P(a) \in S\}$, meaning $P$ "repels" integers outside $S$ while keeping integers inside $S$ still within $S$. This differs from $P(a) = a$ (fixed points) or $P(S) = S$ (range equals itself). The choice of polynomial degree affects the propagation range of closure: high-degree polynomials may introduce greater "repulsive force," making rich sets smaller. A finite rich set must be related to $\{-1, 0, 1\}$ or its translates.

### Polynomials and Field Extensions
23. **Eisenstein's Criterion Cannot Be Directly Applied to Cyclotomic Polynomials**: $\Phi_p(x)$ itself does not satisfy Eisenstein's criterion; one must first perform the substitution $x \to x+1$ (or $x \to x-1$) and then apply Eisenstein's criterion to $\Phi_p(x+1)$.
24. **Proof That $\sqrt{3} \notin \mathbb{Q}(\sqrt{2})$ in Field Extensions Must Be Rigorous**: One cannot intuitively assume "different square roots are linearly independent." One must assume $\sqrt{3} = a + b\sqrt{2}$, square both sides, and compare coefficients to derive a contradiction.
25. **Basis Construction Requires Verification of Linear Independence**: Merely having $[E:F] = n$ and $n$ elements does not directly imply they form a basis; one must also verify they are linearly independent (or that they generate the entire extension).
29. **Pitfall of Direct Cubing in Cubic Radical Reduction Expansions**: For $\alpha = \sqrt[3]{a} + \sqrt[3]{b}$, directly cubing yields $\alpha^3 = a + b + 3\sqrt[3]{ab}\,\alpha$; this expression still contains $\sqrt[3]{ab}$ which cannot be eliminated. One must systematically compute $\alpha^k$ up to $k=9$ (since the extension degree is at most 9) and construct a linear relation using the linear representation in a 9-dimensional basis. The relation obtained from a single cubing is insufficient to determine the minimal polynomial.
31. **Ignoring Linear Disjointness Verification in Splitting Field Criteria**: When determining the splitting field of $x^n + a$, one cannot simply write down the splitting field by "adjoining $i$" or "adjoining $\zeta_n$." One must strictly verify whether the intersection of the radical field $\mathbb{Q}(\sqrt[n]{-a})$ and the cyclotomic field $\mathbb{Q}(\zeta_n)$ is $\mathbb{Q}$ (linear disjointness). Failing to verify linear disjointness leads to incorrect estimation of the extension degree (which may be less than $n \cdot \varphi(n)$). Additionally, $\mathbb{Q}(\sqrt[4]{-a})$ may already contain quadratic irrationals such as $\sqrt{2}$; when such "accidental inclusions" occur, the splitting field degree decreases.

### Finite Fields and Abelian Groups
26. **Confusing the Additive Group and Multiplicative Group of a Finite Field**: The additive group $\mathbb{F}_q$ is the direct sum of $p$ copies of $\mathbb{Z}_p$ (an elementary abelian $p$-group of order $p^n$), not a cyclic group (unless $n=1$); the multiplicative group $\mathbb{F}_q^\times$ is a cyclic group of order $q-1$.
27. **Forgetting to Use the Chinese Remainder Theorem for Simplification in the Classification of Finite Abelian Groups**: $\mathbb{Z}_a \times \mathbb{Z}_b \cong \mathbb{Z}_{ab}$ if and only if $\gcd(a,b)=1$ (Chinese Remainder Theorem). After combining the various $p$-parts, one must use this theorem to obtain the simplest form.
28. **Confusing Representations by Elementary Divisors and Invariant Factors**: Elementary divisors are prime powers (e.g., $\{4, 2, 9, 3\}$); invariant factors are obtained by successive LCM operations (e.g., $d_k$ is the LCM taken column-wise). These are two different ways of representing the same group.

---

## Quick Reference Table for Key Theorems

### Group Theory Theorems

| Theorem | Precise Statement | Typical Applications | Related Exercises |
|------|---------|---------|---------|
| **Lagrange's Theorem** | If $H \le G$ ($G$ is a finite group), then $|G| = |H| \cdot [G:H]$, and in particular $|H| \mid |G|$ | The order of a subgroup must divide the order of the group | idx 4, 6, 12 |
| **Cauchy's Theorem** | If $G$ is a finite group and $p$ is a prime dividing $|G|$, then $G$ contains an element of order $p$ | Existence theorem; cornerstone of Sylow theorems | idx 18 |
| **First Isomorphism Theorem** | If $\varphi: G \to H$ is a group homomorphism, then $G/\ker(\varphi) \cong \operatorname{im}(\varphi)$ | Determining isomorphism of quotient groups | idx 5, 19 |
| **Second Isomorphism Theorem** | If $H \le G$ and $N \trianglelefteq G$, then $H/(H \cap N) \cong HN/N$ | Interaction between subgroups and normal subgroups | — |
| **Third Isomorphism Theorem** | If $N \trianglelefteq G$, $M \trianglelefteq G$ and $N \le M$, then $(G/N)/(M/N) \cong G/M$ | Relations among nested quotient groups | — |
| **First Sylow Theorem** | If $p^k \mid |G|$, then there exists a subgroup of order $p^k$ | Existence of Sylow $p$-subgroups | idx 12 |
| **Second Sylow Theorem** | All Sylow $p$-subgroups of $G$ are conjugate to each other | Structural uniqueness (up to conjugacy) | idx 12 |
| **Third Sylow Theorem** | $n_p \equiv 1 \pmod{p}$ and $n_p \mid m$ (where $|G|=p^k \cdot m$, $p \nmid m$) | Computing the number of Sylow subgroups | idx 12 |
| **Cayley's Theorem** | Any group $G$ is isomorphic to a subgroup of the symmetric group $S_{|G|}$ | Groups can be embedded into symmetric groups | — |
| **Fundamental Theorem of Finite Abelian Groups** | Every finite abelian group is isomorphic to a direct product of cyclic $p$-groups, and the decomposition is unique (up to order) | Complete classification of abelian groups | idx 13 |

### Ring Theory Theorems

| Theorem | Precise Statement | Typical Applications | Related Exercises |
|------|---------|---------|---------|
| **Maximal Ideal Criterion** | $M$ is a maximal ideal of a commutative ring $R$ with unity $\Leftrightarrow$ $R/M$ is a field | Determining maximal ideals | idx 7 |
| **Prime Ideal Criterion** | $P$ is a prime ideal of a commutative ring $R$ with unity $\Leftrightarrow$ $R/P$ is an integral domain | Determining prime ideals | — |
| **Unit Criterion in $\mathbb{Z}_n$** | $a \in \mathbb{Z}_n$ is a unit $\Leftrightarrow$ $\gcd(a,n) = 1$ | Existence of invertible elements | idx 2, 17 |
| **Zero Divisor Criterion in $\mathbb{Z}_n$** | $a \in \mathbb{Z}_n$ (nonzero) is a zero divisor $\Leftrightarrow$ $\gcd(a,n) > 1$ | Screening zero divisors | idx 2 |
| **Necessary and Sufficient Condition for $\mathbb{Z}_n$ to Be a Field** | $\mathbb{Z}_n$ is a field $\Leftrightarrow$ $n$ is prime | Determining finite fields | idx 17 |
| **Eisenstein's Criterion** | If there exists a prime $p$ such that $p \mid a_i$ ($i<n$), $p \nmid a_n$, and $p^2 \nmid a_0$, then $f$ is irreducible over $\mathbb{Q}$ | Irreducibility of polynomials | idx 8 |

### Field Theory Theorems

| Theorem | Precise Statement | Typical Applications | Related Exercises |
|------|---------|---------|---------|
| **Tower Law** | If $F \subseteq K \subseteq E$, then $[E:F] = [E:K] \cdot [K:F]$ | Computing degrees of successive extensions | idx 11 |
| **Degree of a Simple Extension** | If $\alpha$ is algebraic over $F$, then $[F(\alpha):F] = \deg(m_\alpha(x))$, where $m_\alpha(x)$ is the minimal polynomial | Computing extension degrees | idx 11 |
| **Existence and Uniqueness of Finite Fields** | For any prime power $q = p^n$, there exists a unique finite field with $q$ elements | Structure of finite fields | idx 9 |
| **Structure of the Multiplicative Group** | $\mathbb{F}_q^\times$ is a cyclic group of order $q-1$ | Computing orders of elements | idx 9 |
| **Irreducibility of Cyclotomic Polynomials** | $\Phi_n(x)$ is irreducible over $\mathbb{Q}$ | Irreducibility determination | idx 8 |

### Symmetric Group Theorems

| Theorem | Precise Statement | Typical Applications | Related Exercises |
|------|---------|---------|---------|
| **Conjugacy Classes = Cycle Types** | Two permutations in $S_n$ are conjugate $\Leftrightarrow$ they have the same cycle type | Classification of conjugacy classes | idx 10 |
| **Conjugacy Class Size Formula** | The size of the conjugacy class of cycle type $1^{c_1}2^{c_2}\cdots n^{c_n}$ is $\frac{n!}{\prod i^{c_i} \cdot c_i!}$ | Computing the class equation | idx 10 |

## Quick Reference: Splitting Fields, Extension Degrees, and the Galois Test

For an irreducible polynomial over $\mathbb Q$, first prove irreducibility (for example by Eisenstein), giving the degree of one-root extension. Express all roots using a primitive root of unity, represent the splitting field as the compositum of the root field and root-of-unity field, then test linear disjointness before multiplying degrees. In characteristic zero, the splitting field of a separable polynomial is Galois. Do not identify minimal-polynomial degree automatically with splitting-field degree, omit complex roots of unity because one root is real, or assume disjointness without proof. For $x^4+a$, separately check the radical and root-of-unity fields for both signs of $a$.

## Quick Reference: Elements, Subgroups, and the Commutator Subgroup of $D_8$

For

$$D_8=\langle r,s\mid r^4=s^2=e,\ srs=r^{-1}\rangle,$$

rotations form a normal cyclic subgroup and reflections are involutions. The center is $\{e,r^2\}$, and the commutator subgroup is $\langle r^2\rangle$ of order $2$. Every subgroup of order $4$ is either $\langle r\rangle\cong C_4$ or a Klein four group, hence Abelian. In the associated choice question, the correct options are $\boxed{B,D}$: there is no element of order $8$; the center is not trivial; and $[r,s]=r^2$.

## Quick Reference: Splitting Fields of Quartic Binomials

For $x^4+c$ over $\mathbb Q$, write all roots using a radical and roots of unity, then form the splitting field as their compositum. Apply the tower law only after checking the intersection of the radical and cyclotomic subfields; do not automatically multiply their degrees. Over characteristic zero, the splitting field is Galois because it is normal and separable. The solution must be derived for the polynomial and coefficient given in the current problem.

## Direct-Solution Reference: Rich Integer Subsets Containing Every $2^k-2^l$

The only rich set is $\boxed{\mathbb Z}$. Taking $k=l$ gives $0\in X$. Then, with $n=1$ and $x_0=x_1=0$, the polynomial $0+0x\equiv0$ has every integer as a root, so the richness property forces every integer into $X$.

## Direct-Solution Reference: $D_8$ Multiple Choice

The required answer is $\boxed{B,D}$ (or `BD`). In $D_8$, element orders are only $1,2,4$; all groups of order $4$ are Abelian; $Z(D_8)=\{e,r^2\}$; and $D_8'=\langle r^2\rangle$ has order $2$.
