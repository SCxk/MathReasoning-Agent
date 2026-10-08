# Linear Regression Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: OLS, matrix regression, residual diagnostics, ANOVA, confidence/prediction intervals, variable selection, heteroscedasticity, and econometric regression.
- Do not take over: general sampling inference/descriptive statistics/time series belong to statistical inference; numerical least-squares algorithms alone belong to numerical analysis.
- Verification contract: distinguish the true variance of a parameter estimator from the conventional standard-error estimate; retain \(X^TX\), SSE, degrees of freedom, test, and interval fields.

## High-Frequency Conventions for Objective Econometrics Questions

- When the functional form is entirely unknown, use nonparametric regression (kernel regression, local polynomials, splines). Nonlinear regression still requires a parameterized function to be specified in advance; logistic regression is a generalized linear model with a particular link function. If a multiple-choice question contains no nonparametric regression but does contain “none of the above,” choose the latter.
- Heteroscedasticity need not destroy OLS unbiasedness or consistency, but it distorts conventional variance/standard-error estimates, and OLS no longer guarantees BLUE. “The variance of the parameter estimator must increase” is not a universal conclusion; the true direction depends on the heteroscedasticity pattern.
- Strictly distinguish two “variances”: if a blank asks for \(\operatorname{Var}(\hat\beta)\), the true variance of a parameter estimator, its direction under heteroscedasticity is indeterminate, so do not answer “must increase.” If it asks for the conventional OLS variance/standard-error estimate, that estimate is distorted under heteroscedasticity (it may overestimate or underestimate). The former conclusion also includes that OLS is no longer BLUE.
- After stepwise regression adds a variable, simultaneously recheck old variables’ \(t\) tests, adjusted \(R^2\), and incremental/overall \(F\) tests. If any criterion triggers removal and an option says “all of the above are possible,” choose that comprehensive option rather than only the most familiar test.
- If a nonlinear-regression question asks what estimation criterion is “usually used,” default to nonlinear least squares (NLS). Maximum likelihood requires additional distributional assumptions; Newton/Gauss–Newton/LM are numerical algorithms rather than estimation criteria. Unless the question explicitly asks for usable optimization algorithms, do not conflate all three as “all can be used.”

## Final-Answer Field Contract

- Do not invent sample data absent from the problem. If it says “use the data from Question 2,” use this manual’s Module 2 data \((1,3),(2,5),(3,6),(4,8),(5,11)\).
- A least-squares calculation answer must include \(\bar x,\bar y,S_{xx},S_{xy},\hat\beta_0,\hat\beta_1\), and the regression line, not only coefficients.
- A standard-error or testing answer must include fitted values or SSE, \(\hat\sigma^2\), standard error, \(t/F\) statistic, critical value, and a reject/do-not-reject conclusion.
- A matrix OLS answer must show design matrix \(X\), \(X^TX\), \(X^TY\), \(\hat\beta\), and the regression equation.
- An ANOVA/partial-\(F\)/diagnostic answer must report every field: df, SS, MS, statistic, distribution, decision rule, and Chinese conclusion.

## Frequent Errors and Conventions (Reviewer Feedback, 2026-07-07)

- **Degrees-of-freedom convention for a partial \(F\) test**: \(F=\dfrac{(SSE_R-SSE_F)/q}{SSE_F/(n-p)}\sim F(q,n-p)\), where **\(p\) is the total number of parameters in the full model (including the intercept)**, so the denominator degrees of freedom are \(n-p\). Do not write \(n-p-1\) (that corresponds to an alternative notation in which \(p\) is the number of predictors excluding the intercept). Answer notation must agree with the question; if unspecified, default to \(n-p\), with \(p\) including the intercept.
- **The Gauss–Markov theorem must be stated completely**: conditions = linear model, \(E(\varepsilon)=0\), \(\operatorname{Var}(\varepsilon)=\sigma^2I\) (homoscedastic and uncorrelated), and nonrandom, full-column-rank \(X\); conclusion = the OLS estimator is BLUE (best linear unbiased estimator). Under heteroscedasticity, OLS remains linear and unbiased, but its variance is no longer minimal, **so it is no longer BLUE**; use GLS/WLS instead.
- **Residual-plot diagnosis**: a “funnel shape” (residual magnitude increasing with fitted value) \(\to\) heteroscedasticity; remedies = transform \(y\) (\(\ln y\), \(\sqrt y\)), weighted least squares WLS, or robust standard errors. An answer must provide both the violated assumption and a remedy.
- A regression-coefficient test (standard error/\(t\)-test) must give the complete final chain: \(SSE\to\hat\sigma^2\to\operatorname{se}(\hat\beta_1)\to t\to\) comparison with the critical value \(\to\) reject/do not reject \(H_0\) and the significance conclusion.
- **Regression-method selection pitfall**: nonlinear and nonparametric regression are different—nonlinear regression still requires a parameterized model (only the parameters enter nonlinearly), whereas nonparametric regression requires no specified functional form. If the functional form is completely unknown, choose nonparametric regression (kernel regression, local polynomials, splines), not nonlinear regression.
- **Heteroscedasticity pitfall**: do not say “OLS is unbiased but inconsistent” (OLS remains consistent under heteroscedasticity); heteroscedasticity does not necessarily increase \(\operatorname{Var}(\hat\beta)\) (the true direction depends on the pattern); distinguish the true parameter-estimator variance from the conventional OLS variance estimate, whose former direction is uncertain and whose latter estimate is biased.
- **Stepwise-regression pitfall**: do not omit the essential rechecking of old variables after a new variable is added—an originally significant old variable may become insignificant. Do not confuse adjusted \(R^2\) with ordinary \(R^2\): the latter increases whenever a variable is added, while the former decreases when an insignificant variable is added.
- **Nonlinear-regression pitfall**: do not treat Gauss–Newton/LM algorithms and NLS (nonlinear least squares) as concepts on the same level—the former are numerical optimization algorithms and the latter is an estimation criterion. Nonlinear regression can also use maximum likelihood, but it requires distributional assumptions.

---

## Part I: Knowledge Modules

### Module 1: Simple Linear-Regression OLS Estimation

**Model:** \(y_i=\beta_0+\beta_1x_i+\varepsilon_i\), \(\varepsilon_i\sim N(0,\sigma^2)\) i.i.d.

**Core formulas:**

- \(\hat\beta_1=\frac{S_{xy}}{S_{xx}}=\frac{\sum(x_i-\bar x)(y_i-\bar y)}{\sum(x_i-\bar x)^2}\).
- \(\hat\beta_0=\bar y-\hat\beta_1\bar x\).

**Statistical meaning:** \(\hat\beta_1\) is the average change in \(y\) for each one-unit change in \(x\).

**Corresponding exercise:** idx 0.

---

### Module 2: Least-Squares Calculation of Regression Coefficients

**Standard solution steps:**

1. Compute \(\bar x,\bar y\).
2. Compute \(S_{xx}=\sum(x_i-\bar x)^2\), \(S_{xy}=\sum(x_i-\bar x)(y_i-\bar y)\).
3. \(\hat\beta_1=S_{xy}/S_{xx}\).
4. \(\hat\beta_0=\bar y-\hat\beta_1\bar x\).
5. Write the regression equation \(\hat y=\hat\beta_0+\hat\beta_1x\).

**Corresponding exercise:** idx 1 (data: \((1,3),(2,5),(3,6),(4,8),(5,11)\)).

---

### Module 3: Unbiased Estimation of Error Variance

**Core formula:** \(\hat\sigma^2=\frac{SSE}{n-2}=\frac{\sum(y_i-\hat y_i)^2}{n-2}\).

**Why the degrees of freedom are \(n-2\):** the two parameters \(\beta_0,\beta_1\) consume two degrees of freedom.

**Properties:** \(\frac{(n-2)\hat\sigma^2}{\sigma^2}\sim\chi^2(n-2)\), and \(E(\hat\sigma^2)=\sigma^2\) (unbiased).

**Corresponding exercise:** idx 2.

---

### Module 4: Standard Error and \(t\)-Test of a Regression Coefficient

**Core formulas:**

- \(\operatorname{se}(\hat\beta_1)=\sqrt{\hat\sigma^2/S_{xx}}\).
- \(t=\frac{\hat\beta_1}{\operatorname{se}(\hat\beta_1)}\sim t(n-2)\) under \(H_0:\beta_1=0\).

**Standard solution steps:**

1. Calculate fitted values \(\hat y_i\) and residuals \(e_i=y_i-\hat y_i\).
2. \(SSE=\sum e_i^2\).
3. \(\hat\sigma^2=SSE/(n-2)\).
4. \(\operatorname{se}(\hat\beta_1)=\sqrt{\hat\sigma^2/S_{xx}}\).
5. Compute \(t=\hat\beta_1/\operatorname{se}(\hat\beta_1)\) and compare with \(t_{\alpha/2}(n-2)\).
6. If \(|t|>t_{\alpha/2}\), reject \(H_0\) (\(x\) has a significant effect on \(y\)).

**Corresponding exercise:** idx 3.

---

### Module 5: Derivation of the \(t\)-Test for a Regression Coefficient

**Theoretical basis:**

- \(\hat\beta_1\sim N(\beta_1,\sigma^2/S_{xx})\).
- \((n-2)\hat\sigma^2/\sigma^2\sim\chi^2(n-2)\), independently of \(\hat\beta_1\).
- Standardizing and replacing \(\sigma\) by \(\hat\sigma\) gives \(t(n-2)\).

**Corresponding exercise:** idx 4.

---

### Module 6: Confidence Interval for a Regression Coefficient

**Core formula:** \(\hat\beta_1\pm t_{\alpha/2}(n-2)\cdot\operatorname{se}(\hat\beta_1)\).

**Shortcut for significance:** the interval excludes \(0\) if and only if it is significant at level \(\alpha\).

**Corresponding exercise:** idx 5.

---

### Module 7: Matrix Form of Multiple Regression

**Model:** \(Y=X\beta+\varepsilon\), with \(X\) an \(n\times p\) design matrix.

**OLS estimator:** \(\hat\beta=(X^TX)^{-1}X^TY\).

**Condition for \(X^TX\) to be invertible:** \(X\) has full column rank (\(\operatorname{rank}(X)=p\)), i.e., no perfect multicollinearity among predictors.

**Corresponding exercise:** idx 6.

---

### Module 8: Multiple-Regression OLS Estimation (Matrix Operations)

**Standard solution steps:**

1. Construct design matrix \(X\) (including an intercept column of \(1\)s).
2. Calculate \(X^TX\) and \(X^TY\).
3. Solve \((X^TX)\hat\beta=X^TY\), or use the inverse matrix.

**Corresponding exercise:** idx 7.

---

### Module 9: Coefficient of Determination \(R^2\)

**Core formulas:**

- \(R^2=\frac{SSR}{SST}=1-\frac{SSE}{SST}\).
- In the simple-regression case, \(R^2=r_{xy}^2\) (the squared correlation coefficient).

**Meaning:** the proportion of variation in \(y\) explained by \(x\), ranging over \([0,1]\).

**Corresponding exercise:** idx 8.

---

### Module 10: \(F\)-Test

**Core formulas:**

- \(F=\frac{MSR}{MSE}=\frac{SSR/1}{SSE/(n-2)}\sim F(1,n-2)\).
- In simple regression, \(F=t^2\) (the \(F\)- and \(t\)-tests are equivalent).

**Corresponding exercise:** idx 9.

---

### Module 11: Prediction Interval

**Core formula (individual value \(y_0\)):**
\[
\hat y_0\pm t_{\alpha/2}(n-2)\cdot\hat\sigma\sqrt{1+\frac1n+\frac{(x_0-\bar x)^2}{S_{xx}}}.
\]

**Sources of the three terms:** \(\sigma^2\) (new-observation noise) + \(\operatorname{Var}(\hat\beta_0)\) + \(\operatorname{Var}(\hat\beta_1)\).

**Corresponding exercise:** idx 10.

---

### Module 12: Confidence Interval for Mean Response

**Core formula (\(E(y_0)\)):**
\[
\hat y_0\pm t_{\alpha/2}(n-2)\cdot\hat\sigma\sqrt{\frac1n+\frac{(x_0-\bar x)^2}{S_{xx}}}.
\]

**Difference from a prediction interval:** there is no “\(+1\)” under the square root, so the mean interval is narrower.

**Corresponding exercise:** idx 11.

---

### Module 13: Multicollinearity Diagnosis (VIF)

**Core formula:** \(\operatorname{VIF}_j=\frac1{1-R_j^2}\), where \(R_j^2\) is the \(R^2\) from regressing \(x_j\) on the other predictors.

**Decision criteria:**

- \(\operatorname{VIF}>5\): multicollinearity exists.
- \(\operatorname{VIF}>10\): severe multicollinearity.

**Corresponding exercise:** idx 12 (\(r_{12}=0.95\), \(VIF=10.26>10\)).

---

### Module 14: Weighted Least Squares (Handling Heteroscedasticity)

**Core concept:** when \(\operatorname{Var}(\varepsilon_i)=\sigma^2/w_i\), WLS minimizes \(\sum w_i(y_i-\beta_0-\beta_1x_i)^2\).

**This problem:** \(\operatorname{Var}(\varepsilon_i)=\sigma^2x_i^2\), with weights \(w_i=1/x_i^2\).

**Transformed model:** \(y_i/x_i=\beta_0/x_i+\beta_1+\varepsilon_i'\) (homoscedastic).

**Corresponding exercise:** idx 13.

---

### Module 15: Gauss–Markov Theorem

**Conditions:**

1. \(E(\varepsilon)=0\).
2. \(\operatorname{Cov}(\varepsilon)=\sigma^2I\) (spherical disturbances: homoscedastic and uncorrelated).
3. \(X\) is nonrandom and has full column rank.

**Conclusion:** the OLS estimator \(\hat\beta\) is BLUE (best linear unbiased estimator).

**Effect of heteroscedasticity:** OLS remains unbiased but is no longer BLUE; GLS/WLS is more efficient.

**Corresponding exercise:** idx 14.

#### Systematic Consequences of Heteroscedasticity

Heteroscedasticity is \(\operatorname{Var}(\varepsilon_i)\ne\sigma^2\) (a constant): error variance is not constant and typically changes with a predictor or fitted value.

**I. OLS unbiasedness and consistency:**

- OLS remains unbiased: \(E(\hat\beta)=\beta\).
- In large samples OLS remains consistent: \(\hat\beta\xrightarrow{p}\beta\) (convergence in probability to the truth).
- **Frequent misconception:** do not say “OLS is unbiased but inconsistent”—under heteroscedasticity OLS is both unbiased and consistent.

**II. OLS is no longer BLUE:**

- The Gauss–Markov theorem requires spherical disturbances (homoscedastic and uncorrelated), and heteroscedasticity violates this condition.
- Although OLS remains a linear unbiased estimator, its variance is no longer minimal—among all linear unbiased estimators, there are estimators with lower variance.
- GLS (generalized least squares) and WLS (weighted least squares) are more efficient under heteroscedasticity.
- If the heteroscedastic form is known (for example, \(\operatorname{Var}(\varepsilon_i)=\sigma^2x_i^2\)), WLS has minimum variance among linear unbiased estimators satisfying that form.

**III. Conventional \(t\)- and \(F\)-tests fail:**

- The OLS conventional estimate \(\hat\sigma^2(X^TX)^{-1}\) of \(\operatorname{Var}(\hat\beta)\) is **biased** under heteroscedasticity.
- Type-I error rates of conventional \(t\)- and \(F\)-tests no longer equal nominal significance levels (they may be too high or too low).
- Confidence-interval coverage using conventional standard errors is also inaccurate.
- **Remedy:** use Eicker–Huber–White heteroscedasticity-robust standard errors (HC0/HC1/HC2/HC3), which are consistent under heteroscedasticity.

**IV. Key distinction—two “variances”:**

- **True variance of the parameter estimator**, \(\operatorname{Var}(\hat\beta)\): under heteroscedasticity its direction is uncertain; do not answer “must increase” (the direction depends on the particular heteroscedasticity pattern—it can increase or decrease).
- **Conventional OLS variance estimate**, \(\hat\sigma^2(X^TX)^{-1}\): biased under heteroscedasticity and may overestimate or underestimate the true variance (so conventional standard errors can be too large or too small).

**Exam technique:** when asked “how does heteroscedasticity affect OLS?”, answer in three levels: unbiasedness (unaffected) \(\to\) efficiency (no longer BLUE) \(\to\) inference (conventional \(t/F\) fail). If asked “how does the variance of the OLS estimator change?”, distinguish true variance from the conventional estimate: the former depends on the heteroscedasticity pattern and the latter is biased.

**Frequent exam pitfalls:**

- Heteroscedasticity does not necessarily increase \(\operatorname{Var}(\hat\beta)\)—do not generically answer “variance increases.”
- Do not say “OLS is unbiased but inconsistent”—OLS remains consistent under heteroscedasticity.
- Equating “no longer BLUE” with “no longer unbiased” is wrong—OLS remains unbiased but is not optimal.
- Confusing true variance with conventional variance estimation—these are different concepts with different conclusions.

---

### Module 16: Residual-Plot Analysis and Model Diagnostics

**“Funnel-shaped” residual plot:**

- Diagnosis: heteroscedasticity (variance increases with the mean).
- Remedies:
  1. transform \(y\) (for example, \(\ln y\), \(\sqrt y\));
  2. weighted least squares (WLS);
  3. heteroscedasticity-robust standard errors (White/Huber–White).

**Corresponding exercise:** idx 15.

---

### Module 17: Partial \(F\)-Test and Variable Selection

**Core formula:** \(F=\frac{(SSE_R-SSE_F)/q}{SSE_F/(n-p)}\sim F(q,n-p)\).

**Use:** test whether the final \(q\) variables of nested models are jointly significant.

**Corresponding exercise:** idx 16.

---

### Module 18: ANOVA Table and Regression Significance

**ANOVA-table structure:**

| Source | df | SS | MS | F |
|---|---:|---|---|---|
| Regression | \(1\) | SSR | \(MSR=SSR/1\) | \(MSR/MSE\) |
| Residual | \(n-2\) | SSE | \(MSE=SSE/(n-2)\) | |
| Total | \(n-1\) | SST | | |

**Corresponding exercise:** idx 17.

---

### Module 19: Autocorrelation Diagnosis (Durbin–Watson)

**DW statistic:** \(d=\frac{\sum(e_t-e_{t-1})^2}{\sum e_t^2}\), ranging over \([0,4]\).

**Decision rule (\(\alpha=0.05\)):**

- \(d<d_L\): positive autocorrelation.
- \(d_L<d<d_U\): inconclusive.
- \(d_U<d<4-d_U\): no autocorrelation.
- \(4-d_U<d<4-d_L\): inconclusive.
- \(d>4-d_L\): negative autocorrelation.

**This problem:** \(d=1.20<d_L=1.28\), so there is positive autocorrelation.

**Remedies:** Cochrane–Orcutt iteration, GLS (AR(1) errors), Newey–West HAC standard errors.

**Corresponding exercise:** idx 18.

---

### Module 20: Model-Selection Criteria (AIC/BIC)

**Formulas:**

- \(\operatorname{AIC}=-2\ln L+2p\).
- \(\operatorname{BIC}=-2\ln L+p\ln n\).

**Difference:** BIC penalizes the number of parameters more heavily (when \(n\ge8\)), favoring a simpler model.

**This problem:** AIC values are equal (cannot distinguish); BIC selects \(M_1\) (more parsimonious).

**Corresponding exercise:** idx 19.

---

### Competition Extension: Choosing a Regression Method

For a regression-modeling problem, choose an appropriate regression method according to the following logic.

**Four main regression methods:**

1. **Linear Regression**
   - Applicable when response \(y\) is continuous and has a linear relation with \(x\) (or transformations of \(x\)).
   - Model form: \(y=\beta_0+\beta_1x_1+\cdots+\beta_px_p+\varepsilon\).
   - Estimation method: OLS (with analytic solution \(\hat\beta=(X^TX)^{-1}X^TY\)).
   - Strengths: highly interpretable, complete inferential theory, simple computation.

2. **Nonlinear Regression**
   - Applicable when the response is continuous but the model is a nonlinear function of parameters.
   - Common forms: \(y=ae^{bx}+\varepsilon\), \(y=\frac{a}{1+be^{-cx}}+\varepsilon\) (logistic growth), \(y=ax^b+\varepsilon\) (power-law model).
   - Estimation method: nonlinear least squares (NLS), requiring iterative numerical optimization.
   - **Key distinction:** nonlinear regression still requires a **parameterized functional form specified in advance** (such as the exponential \(ae^{bx}\)); only the way parameters enter the model is nonlinear.

3. **Logistic Regression**
   - Applicable when the response is a **categorical variable** (binary or multiclass), with continuous or discrete predictors \(x\).
   - Model form: \(\ln\frac{p}{1-p}=\beta_0+\beta_1x\), where \(p=P(Y=1\mid x)\).
   - The logit link maps the linear predictor into \((0,1)\).
   - Estimation method: maximum likelihood (MLE), with no analytic solution; requires Newton–Raphson or IRLS iteration.
   - **Note:** despite its name, logistic regression is fundamentally a classification model and belongs to generalized linear models (GLMs).

4. **Nonparametric Regression**
   - Applicable when the functional form is entirely unknown and no parametric assumption is made about the relation between \(y\) and \(x\).
   - Representative methods:
     - **Kernel regression**: \(m(x)=\frac{\sum K_h(x_i-x)y_i}{\sum K_h(x_i-x)}\) (Nadaraya–Watson estimator).
     - **Local polynomial regression (LOESS/LOWESS)**: locally weighted polynomial fits around each point.
     - **Spline regression**: piecewise polynomials joined smoothly at knots.
   - Strength: extremely flexible; no functional form needs to be predicted in advance.
   - Weakness: requires a larger sample size; the “curse of dimensionality” is severe in high dimensions.

**Selection logic:**

```
Response type
├── Continuous response
│   ├── Functional form known (parameterized)
│   │   ├── Linear → linear regression
│   │   └── Nonlinear → nonlinear regression (functional form must be specified)
│   └── Functional form entirely unknown → nonparametric regression
└── Categorical response
    ├── Binary → logistic regression
    └── Multiclass → multinomial logistic regression
```

**Exam technique:** when the functional form is completely unknown, choose nonparametric regression, not nonlinear regression—nonlinear regression still needs a parameterized form specified in advance (such as \(ae^{bx}\)). If a multiple-choice question offers no nonparametric regression but does offer “none of the above,” choose the latter.

**Frequent exam pitfalls:**

- Confusing nonlinear regression with nonparametric regression: the former still uses a parameterized model (only the functional form is nonlinear), while the latter does not require any specified functional form.
- Treating logistic regression as a regression method for a continuous response: it is for categorical responses and is a generalized linear model.
- Thinking linear regression can fit only straight lines: with polynomial terms (\(x^2,x^3,\ldots\)) or interactions it is still linear regression, because parameters enter linearly.

---

### Competition Extension: Variable-Removal Criteria in Stepwise Regression

Stepwise regression is a common variable-selection method that searches for an “optimal” subset by adding or removing variables from a model.

**Three forms of stepwise regression:**

| Method | Starting point | Direction | Feature |
|---|---|---|---|
| Forward selection | Empty model (intercept only) | Add the most significant variable one at a time | Variables enter only; once added, they are not removed |
| Backward elimination | Full model (all variables) | Remove the least significant variable one at a time | Variables leave only; once removed, they are not added again |
| Bidirectional stepwise | Empty or full model | After every addition, check whether removal is needed | Combines forward and backward steps; variables can enter and leave |

**Criteria for adding a variable (all must hold):**

1. **Significant \(t\)-test**: the coefficient \(t\)-test \(p\)-value for the candidate variable is below the entry threshold (usually \(\alpha_{entry}=0.05\) or \(0.10\)).
2. **Significant \(F\)-test**: the partial \(F\)-test for the added variable (or group of variables) is significant, so it adds explanatory power.
3. **Adjusted** \(R^2=1-\frac{SSE/(n-p-1)}{SST/(n-1)}\) **increases**: adjusted \(R^2\) penalizes the number of variables and increases only when a variable contributes enough. Ordinary \(R^2\) always increases when any variable is added and cannot be used as a selection criterion.

**Criteria for removing a variable (remove when any one is triggered):**

1. **Severe multicollinearity:**
   - \(\operatorname{VIF}_j>10\) (most common criterion).
   - Condition number \(\kappa>30\), where \(\kappa=\sqrt{\lambda_{\max}/\lambda_{\min}}\) and \(\lambda\) are eigenvalues of \(X^TX\).
   - Under severe collinearity, preferentially remove the variable with the largest VIF.

2. **Insignificant \(t\)-test:**
   - The coefficient \(t\)-test \(p\)-value exceeds the removal threshold (usually \(\alpha_{stay}=0.10\)).
   - Usually \(\alpha_{entry}\le\alpha_{stay}\), preventing variables from repeatedly entering and leaving.

3. **Insignificant partial \(F\)-test:**
   - Test whether removing the variable significantly worsens fit.
   - \(F=\frac{(SSE_R-SSE_F)/1}{SSE_F/(n-p)}\sim F(1,n-p)\), where \(SSE_F\) is the residual sum of squares for the full model before removal and \(SSE_R\) is that for the reduced model after removal.
   - If \(p>0.10\), removal may be considered.

4. **Adjusted \(R^2\) decreases:**
   - If adjusted \(R^2\) rises after a variable is removed, that variable’s net contribution is negative and it should be removed.

**Key step—recheck old variables after adding a new one:**

- Once a new variable is added, an old variable formerly significant in the model may become insignificant.
- The \(t\)- and partial-\(F\)-tests of all old variables already in the model must be checked too.
- Bidirectional stepwise regression automatically performs this recheck after every addition.

**Exam technique:** if a multiple-choice question asks “what must be checked after adding a new variable?”, choose the comprehensive item—check \(t\)-tests, \(F\)-tests, and adjusted \(R^2\) together, not merely one. Every step of stepwise regression is a joint multi-criterion judgment, not a single-criterion decision.

**Frequent exam pitfalls:**

- Omitting the key recheck of old variables after a new variable enters—especially important in forward and bidirectional selection.
- Confusing adjusted and ordinary \(R^2\): ordinary \(R^2\) increases with every added variable, even insignificant noise variables, and cannot be a selection criterion; only an increase in adjusted \(R^2\) shows the new variable has net contribution.
- Confusing definitions of \(p\): in a partial \(F\)-test, \(p\) is the full model’s total number of parameters (including the intercept), while some texts use \(k\) for the number of predictors excluding the intercept, in which case \(p=k+1\).

---

### Competition Extension: Parameter Estimation for Nonlinear Regression

When, in \(y_i=f(x_i;\theta)+\varepsilon_i\), \(f\) is nonlinear in parameter \(\theta\), OLS has no analytic solution and iterative numerical optimization is required.

#### I. Estimation Criteria versus Optimization Algorithms

First distinguish the two levels of concepts:

- **Estimation criteria**: objective functions defining the “optimal” parameter.
  - **Nonlinear least squares (NLS)**: \(\min_\theta\sum_{i=1}^n(y_i-f(x_i;\theta))^2\), requiring no distributional assumption.
  - **Maximum likelihood estimation (MLE)**: \(\max_\theta L(\theta\mid y,x)\), requiring an assumed error distribution (usually normal).
- **Optimization algorithms**: numerical methods that solve the preceding optimization problems.
  - Gauss–Newton, Levenberg–Marquardt, Newton–Raphson, gradient descent, and so on.

**Examination cue:** “the estimation method usually used for nonlinear regression” defaults to nonlinear least squares (NLS). If asked for “usable optimization algorithms,” Gauss–Newton and LM are both correct. The two levels must not be conflated.

#### II. Gauss–Newton Method

Core idea: make a first-order Taylor expansion (linearization) of \(f(x_i;\theta)\) at the current position, converting the task into an iteratively solved linear least-squares problem.

Iteration formula:

\[
\theta^{(k+1)}=\theta^{(k)}+(J^TJ)^{-1}J^T(y-f(\theta^{(k)})).
\]

Here \(J\) is the \(n\times p\) Jacobian matrix, whose \((i,j)\)-th entry is \(J_{ij}=\frac{\partial f(x_i;\theta)}{\partial\theta_j}\big|_{\theta=\theta^{(k)}}\).

**Advantages and disadvantages:**

- Advantage: no Hessian matrix (second derivatives) is needed; \(J^TJ\) is used as an approximation, so computation is relatively light.
- Disadvantage: when \(J^TJ\) is nearly singular (near collinearity or a flat region far from the optimum), iteration is extremely unstable and may diverge.

#### III. Levenberg–Marquardt Method (LM)

LM improves Gauss–Newton by adding a damping term to \(J^TJ\), improving stability:

\[
\theta^{(k+1)}=\theta^{(k)}+(J^TJ+\lambda I)^{-1}J^T(y-f(\theta^{(k)})),
\]

where \(\lambda\ge0\) is the damping parameter and \(I\) is the identity matrix.

**Behavior and control of \(\lambda\):**

- As \(\lambda\to0\), \((J^TJ+\lambda I)^{-1}\approx(J^TJ)^{-1}\): behavior approaches Gauss–Newton—fast but possibly unstable.
- As \(\lambda\to\infty\), \((J^TJ+\lambda I)^{-1}\approx\frac1\lambda I\): behavior approaches gradient descent—stable but slow.
- **Adaptive strategy**: if one step reduces the residual sum of squares, decrease \(\lambda\) (move toward Gauss–Newton); if the residual increases, increase \(\lambda\) (move toward gradient descent).

**Status of LM:** it is a standard algorithm for nonlinear least-squares problems, combining the rapid convergence of Gauss–Newton with the global stability of gradient descent. It is widely used in statistical software (for example, R’s `nls()` internally uses LM or a variant).

#### IV. Newton–Raphson Method

Apply a second-order Taylor expansion directly to the entire objective function (rather than only \(f\)); this requires a Hessian matrix:

\[
\theta^{(k+1)}=\theta^{(k)}-H^{-1}(\theta^{(k)})\nabla S(\theta^{(k)}),
\]

where \(\nabla S\) is the objective-function gradient and \(H\) is its Hessian. Advantage: second-order convergence (fastest). Disadvantage: evaluating and inverting the Hessian is costly.

**Exam technique:** when answering a nonlinear-regression parameter-estimation question, first determine whether it asks for an “estimation criterion” or “optimization algorithm.” Criterion \(\to\) NLS (default) or MLE. Algorithm \(\to\) Gauss–Newton or LM. If the wording is “the estimation method usually adopted in nonlinear regression,” the answer is nonlinear least squares (NLS).

**Frequent exam pitfalls:**

- Treating Gauss–Newton/LM and NLS as the same level: the former are optimization algorithms; the latter is an estimation criterion. If both “NLS” and “Gauss–Newton” occur, determine which level the question asks about.
- “Can nonlinear regression use only NLS?” No: MLE is also possible, but requires an error-distribution assumption (usually normal).
- Gauss–Newton does not always converge: it can diverge when \(J^TJ\) is nearly singular, which is why LM introduces damping.
- NLS has no analytic solution (unlike OLS, which has \(\hat\beta=(X^TX)^{-1}X^TY\)); an iterative algorithm is required.

---

## Part II: General Problem-Solving Methodology

### Regression-Analysis Workflow

1. **Model:** determine variables and specify model form.
2. **Estimate:** use OLS to compute \(\hat\beta\).
3. **Test:** \(t\)-test (one coefficient), \(F\)-test (overall significance).
4. **Diagnose:** residual plot (heteroscedasticity/nonlinearity), VIF (collinearity), DW (autocorrelation).
5. **Correct:** WLS (heteroscedasticity), ridge regression (collinearity), GLS (autocorrelation).
6. **Predict:** confidence interval (mean), prediction interval (individual value).

### Quick Reference for Key Formulas

| Need | Formula |
|---|---|
| OLS slope | \(\hat\beta_1=S_{xy}/S_{xx}\) |
| Slope standard error | \(\operatorname{se}(\hat\beta_1)=\sqrt{\hat\sigma^2/S_{xx}}\) |
| \(t\)-test | \(t=\hat\beta_1/\operatorname{se}(\hat\beta_1)\sim t(n-2)\) |
| CI for \(\beta_1\) | \(\hat\beta_1\pm t_{\alpha/2}\cdot\operatorname{se}(\hat\beta_1)\) |
| Prediction interval | \(\hat y_0\pm t_{\alpha/2}\hat\sigma\sqrt{1+1/n+(x_0-\bar x)^2/S_{xx}}\) |
| VIF | \(1/(1-R_j^2)\) |
| AIC/BIC | \(-2\ln L+2p\) / \(-2\ln L+p\ln n\) |

---

## Part III: Exercise Index

| idx | Problem keywords | Knowledge point | Difficulty |
|---:|---|---|---|
| 0 | OLS estimation expression | Simple OLS | Easy |
| 1 | Least-squares calculation | Regression-coefficient calculation | Easy |
| 2 | df of \(\hat\sigma^2\) | Variance estimation | Easy |
| 3 | Standard error + \(t\)-test | Coefficient test | Intermediate |
| 4 | \(t\)-test derivation | \(t\)-test theory | Intermediate |
| 5 | Confidence interval for \(\beta_1\) | Coefficient CI | Intermediate |
| 6 | Multivariate matrix form | Multiple OLS | Intermediate |
| 7 | Three-variable regression matrix calculation | Multiple-OLS calculation | Intermediate |
| 8 | \(R^2=r_{xy}^2\) | Coefficient of determination | Intermediate |
| 9 | \(F\)-test = \(t^2\) | \(F\)-test | Intermediate |
| 10 | Prediction-interval derivation | Prediction interval | Intermediate |
| 11 | Mean CI vs. prediction interval | Mean CI | Intermediate |
| 12 | \(VIF=10.26\) | Multicollinearity | Hard |
| 13 | WLS weights | Handling heteroscedasticity | Hard |
| 14 | Gauss–Markov | GM theorem | Easy |
| 15 | Funnel-shaped residual plot | Residual diagnosis | Intermediate |
| 16 | Partial \(F\)-test | Variable selection | Intermediate |
| 17 | ANOVA table | Analysis of variance | Intermediate |
| 18 | Durbin–Watson | Autocorrelation | Hard |
| 19 | AIC/BIC comparison | Model selection | Hard |

## General Supplement: Regression Diagnostics and Model Selection

1. Heteroscedasticity affects estimator variance, standard errors, and inferential tests; under classical exogeneity conditions, it does not automatically make coefficients biased. First distinguish “variance changes” from “variance necessarily increases.”
2. Stepwise-regression entry and removal rules must be tied to significance thresholds or fit criteria; check the effect of an added variable on existing variables and the overall model.
3. For a nonlinear relation, first distinguish “the model is nonlinear in parameters” from “the model can be linearized by a variable transformation”; the estimation method is determined by the error model, differentiability, and objective function.

## Quick Reference: Choosing a Regression Method

When the functional form relating response and predictors is entirely unknown, use nonparametric regression (kernel, spline, local weighted regression) or a generalized additive model. Linear regression assumes a linear relation; nonlinear regression still requires a specified functional form; logistic regression is for a binary outcome with a logit link. Do not use nonlinear regression merely because the form is unknown, or logistic regression for a continuous outcome.

## Quick Reference: Consequences of Heteroscedasticity

Heteroscedasticity means that the error variance is not constant. Under exogeneity, OLS remains unbiased and consistent, but loses minimum-variance/BLUE status. The usual homoscedastic variance estimator becomes invalid and may understate or overstate the true estimator variance depending on the pattern; consequently ordinary $t$ tests, $F$ tests, and confidence intervals are invalid. Use robust standard errors or weighted least squares. “The variance necessarily increases” and “the estimator becomes biased” are both false.

## Quick Reference: Stepwise-Regression Removal Criteria

After adding a variable, reassess the full model. Remove or refuse a variable if: an existing variable becomes $t$-insignificant through multicollinearity; adjusted $R^2$ fails to increase because the gain does not offset lost degrees of freedom; or the new-variable/overall $F$ test is insignificant. These are complementary criteria, not alternatives. In particular,

$$
\bar R^2=1-(1-R^2)\frac{n-1}{n-k-1}.
$$

## Quick Reference: Parameter Estimation in Nonlinear Regression

For $y=f(x;\beta)+\varepsilon$, the usual estimation criterion is nonlinear least squares, minimizing the residual sum of squares. Gauss--Newton and Levenberg--Marquardt are common iterative solvers. Maximum likelihood requires an additional error-distribution specification; Newton--Raphson is a general numerical optimization algorithm, not the estimation criterion itself. Keep criterion and solver distinct.

## Direct-Solution References: Objective Regression Items

- **Unknown disease-incidence functional form:** correct option $\boxed{D}$ (“none of the above”), because the required method is nonparametric regression and no listed linear/nonlinear/logistic method applies. Nonlinear regression still requires a prescribed form; logistic regression requires a binary outcome.
- **Heteroscedasticity fill-in:** $\boxed{\text{Heteroscedasticity does not bias the parameter estimator, but makes the traditional variance estimate invalid—it may understate or overstate the true variance—and makes OLS no longer efficient.}}$ All three clauses are required.
- **Stepwise removal after a new variable:** correct option $\boxed{D}$ (“all of the above”): loss of significance of an old variable, a decrease in adjusted $R^2$, or an insignificant partial $F$ test can each justify removal.
- **Usual nonlinear-regression parameter method:** correct option $\boxed{A}$ (least squares). Maximum likelihood is a distribution-specific alternative; Newton--Raphson is only a solver, so “all are possible” is not the required choice.
- **Claim that heteroscedasticity makes OLS estimator variance increase:** $\boxed{\text{False}}$. Loss of minimum-variance status does not logically imply monotonic variance increase; the direction is pattern-dependent.
