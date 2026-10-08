# Statistical Inference Problem-Solving Skill

## Domain Boundaries and Routing Conventions

- Scope: descriptive statistics, sampling distributions, parameter estimation, confidence intervals, hypothesis tests, statistical graphics, and time series.
- Do not take over: OLS, heteroscedasticity, and econometrics belong to linear regression; merely finding random-variable distributions/probabilities belongs to probability theory; dynamic models such as Markov models belong to stochastic processes.
- Verification contract: retain statistics, degrees of freedom, critical values or \(p\)-values, both interval endpoints, and the conclusion from the problem. Verify multiple-choice options under the stated parameterization convention.

## High-Frequency Conventions for Objective Questions

- A normal distribution is determined by location parameter \(\mu\) and scale parameter \(\sigma\) (equivalently written \(\sigma^2\)). If options list “mean and standard deviation” alongside “mean and variance,” this question bank follows the course convention and selects mean and standard deviation; select variance only when the problem explicitly uses the \(N(\mu,\sigma^2)\) variance parameterization.
  - **Location parameter**: \(\mu\) determines the central location. Changing \(\mu\) translates the density curve left or right without changing shape; \(\mu\) is simultaneously the mean, median, and mode, which coincide at one point.
  - **Scale parameter**: \(\sigma\) determines spread. Changing \(\sigma\) stretches or compresses the density horizontally (larger \(\sigma\) makes the curve flatter; smaller \(\sigma\) makes it sharper). Textbooks parameterize it differently, using \(N(\mu,\sigma)\) or \(N(\mu,\sigma^2)\); identify the question’s convention, especially when “mean and variance” and “mean and standard deviation” both occur in the choices.
- Dividing two aggregate indicators at the same time points yields a relative indicator; arranged by time, it is a time series of relative numbers. Do not reject this simply because numerator and denominator are both aggregate indicators.
- A histogram suits an overview of distribution shape and central tendency for a large univariate data set; a scatterplot needs two variables; a line plot is preferred for time-ordered data; a box plot provides only the five-number summary.
- Core components of classical time-series decomposition are long-term trend, seasonal variation, cyclical variation, and irregular variation. Some texts call the last “random variation” or treat it as a synonym of irregular variation. If a question explicitly lists random variation as an independent component, check it under that textbook’s convention; do not omit the option without reason.
- Common basic methods for seasonal adjustment include moving averages (centered moving averages/seasonal indices) and decomposition. A fill-in answer must output methods one by one according to the number of blanks; do not replace the second method with a longer synonymous phrase.

## Final-Answer Field Contract

- Do not invent samples, quantiles, or prior-question data absent from the problem. When prior data are referenced, use only data recorded in the question or explicitly in this manual; verification notes do not supply problem data.
- An estimation answer must state both estimated parameter and estimator notation, e.g. \(\hat\lambda=\bar X=\frac1n\sum X_i\), not merely internal variable names such as `X_bar` or `S/n`.
- An interval estimate must state the pivot/quantile, standard error, interval formula, and numerical lower and upper endpoints.
- A hypothesis test must give \(H_0/H_1\), statistic, critical value or rejection region, comparison, and a Chinese conclusion (reject/do not reject plus practical meaning). **Giving only statistic and critical value without “reject/do not reject \(H_0\) + practical meaning” is incomplete.**
- A confidence interval must provide both endpoints as \([a,b]\); reporting one endpoint only is incomplete.
- For type-II-error/power questions, distinguish type-II error probability \(\beta\) from power \(1-\beta\); never interchange them. **Direction check:** first write rejection region \(W\); \(\beta=P(\text{sample falls in }W^c\mid H_1\text{ true})\), while power \(=P(W\mid H_1)=1-\beta\). Note \(P(X\ge c)=1-\Phi(z_c)\) whereas \(P(X\le c)=\Phi(z_c)\). Before reporting, use the common-sense check “the farther the true value lies from \(H_0\), the greater power should be,” and fully write the probability expression and standardization for manual direction checking.
- An estimator-comparison answer (MSE/efficiency) must state the size comparison (which is smaller and better) and a clear selection recommendation, not merely list formulas.

---

## Part I: Knowledge Modules

### Module 1: Method of Moments

**Core concept:** replace population moments with sample moments and solve for the parameter estimator.

**Standard solution steps:**

1. Compute population moment \(E(X^k)\) as a function of parameter \(\theta\).
2. Compute the corresponding sample moment \(\frac1n\sum X_i^k\).
3. Equate population and sample moments to construct equations.
4. Solve for the parameter expression, the moment estimator \(\hat\theta\).

**Common pitfalls:**

- The number of parameters determines the number of moment equations needed (usually \(k\) parameters use first through \(k\)-th moments).
- A Poisson \(P(\lambda)\) distribution has \(E(X)=\lambda\), so the result follows in one step.

**Corresponding exercise:** idx 0.

---

### Module 2: Maximum Likelihood Estimation (Discrete)

**Core concept:** choose the parameter value making observed data most probable.

**Standard solution steps:**

1. Write likelihood \(L(\theta)=\prod f(x_i\mid\theta)\).
2. Take logarithms: \(\ln L=\sum\ln f(x_i\mid\theta)\).
3. Differentiate by the parameter and set the derivative to zero: \(\frac{d\ln L}{d\theta}=0\).
4. Solve for \(\hat\theta\) (MLE).
5. Verify that the second derivative is \(<0\) to ensure a maximum.

**Corresponding exercise:** idx 1 (Bernoulli distribution).

---

### Module 3: Maximum Likelihood Estimation (Continuous)

**Core concept:** for a continuous distribution, the likelihood is the joint density.

**Standard solution steps:**

1. Write the joint density as the likelihood.
2. Take logarithms to simplify products.
3. Differentiate and solve the equation.
4. Check the maximum.

**Common pitfalls:**

- When \(\sigma^2\) is known for a normal distribution, differentiate only with respect to \(\mu\).
- The solution of \(\sum(X_i-\mu)=0\) is exactly \(\bar X\).

**Corresponding exercise:** idx 2 (normal distribution).

---

### Module 4: Determining Unbiasedness

**Core concept:** an estimator \(\hat\theta\) is unbiased if its expectation equals \(\theta\).

**Standard solution steps:**

1. Compute \(E(\hat\theta)\).
2. Use linearity \(E(aX+bY)=aE(X)+bE(Y)\).
3. If \(E(\hat\theta)=\theta\), it is unbiased.
4. If biased, compute bias \(b(\hat\theta)=E(\hat\theta)-\theta\).

**Corresponding exercise:** idx 3.

---

### Module 5: Consistency and Unbiased Correction

**Core concept:** \(X_{(n)}=\max(X_1,\ldots,X_n)\) is a biased estimator of \(\theta\); correct it to \(\frac{n+1}{n}X_{(n)}\).

**Standard solution steps:**

1. Find density \(f_{(n)}(x)=n[F(x)]^{n-1}f(x)\) of \(X_{(n)}\).
2. Compute \(E(X_{(n)})=\int_0^\theta x\cdot nx^{n-1}/\theta^n\,dx=\frac n{n+1}\theta\).
3. Construct the unbiased estimator \(\frac{n+1}{n}X_{(n)}\).

**Corresponding exercise:** idx 4.

---

### Module 6: Confidence Interval for One Normal-Population Mean (\(\sigma\) Known)

**Core formula:** \(\bar x\pm z_{\alpha/2}\frac\sigma{\sqrt n}\).

**Standard solution steps:**

1. Determine confidence level \(1-\alpha\).
2. Look up \(z_{\alpha/2}\) (e.g. \(95\%\to1.96\)).
3. Compute standard error \(\sigma/\sqrt n\).
4. Substitute into the formula for the interval.

**Corresponding exercise:** idx 5.

---

### Module 7: Confidence Interval for One Normal-Population Mean (\(\sigma\) Unknown)

**Core formula:** \(\bar x\pm t_{\alpha/2}(n-1)\frac{s}{\sqrt n}\).

**Difference:** with \(\sigma\) unknown, replace it with sample standard deviation \(s\), and replace the \(z\) quantile by a \(t\)-distribution quantile.

**Corresponding exercise:** idx 6.

---

### Module 8: Confidence Interval for a Normal-Population Variance

**Core formula:** \(\left[\frac{(n-1)s^2}{\chi^2_{\alpha/2}(n-1)},\frac{(n-1)s^2}{\chi^2_{1-\alpha/2}(n-1)}\right]\).

**Pivot:** \(\frac{(n-1)s^2}{\sigma^2}\sim\chi^2(n-1)\).

**Note:** the \(\chi^2\) distribution is asymmetric, so its upper and lower quantiles differ.

**Corresponding exercise:** idx 7.

### Module 9: Interval Estimation for a Difference of Two Population Means

**Core formula (variances known):** \((\bar x_1-\bar x_2)\pm z_{\alpha/2}\sqrt{\frac{\sigma_1^2}{n_1}+\frac{\sigma_2^2}{n_2}}\).

**Corresponding exercise:** idx 8.

---

### Module 10: \(Z\)-Test for One Population Mean

**Core formula:** \(Z=\frac{\bar x-\mu_0}{\sigma/\sqrt n}\sim N(0,1)\) under \(H_0\).

**Standard solution steps:**

1. State hypotheses \(H_0:\mu=\mu_0\) versus \(H_1\).
2. Calculate test statistic \(z\).
3. Compare against a critical value (for a two-sided test, reject when \(|z|>z_{\alpha/2}\)).
4. Write the conclusion.

**Corresponding exercise:** idx 9.

---

### Module 11: \(t\)-Test for One Population Mean

**Core formula:** \(t=\frac{\bar x-\mu_0}{s/\sqrt n}\sim t(n-1)\).

**Applicable conditions:** normal population, unknown \(\sigma\), small sample.

**Corresponding exercise:** idx 10.

---

### Module 12: \(\chi^2\)-Test for One Population Variance

**Core formula:** \(\chi^2=\frac{(n-1)s^2}{\sigma_0^2}\sim\chi^2(n-1)\).

**Rejection region:** for the right-sided test \(H_1:\sigma^2>\sigma_0^2\), \(\chi^2>\chi^2_\alpha(n-1)\).

**Corresponding exercise:** idx 11.

---

### Module 13: \(F\)-Test for Two Population Variances

**Core formula:** \(F=\frac{s_A^2}{s_B^2}\sim F(n_A-1,n_B-1)\).

**Rejection region (two-sided):** \(F<F_{1-\alpha/2}\) or \(F>F_{\alpha/2}\).

**Corresponding exercise:** idx 12.

---

### Module 14: Hypothesis Test for a Difference of Two Population Means

**Core concept:** with equal but unknown variances, use pooled variance \(s_p^2\).

**Core formula:** \(s_p^2=\frac{(n_A-1)s_A^2+(n_B-1)s_B^2}{n_A+n_B-2}\).

**Test statistic:** \(t=\frac{\bar x_A-\bar x_B}{s_p\sqrt{1/n_A+1/n_B}}\sim t(n_A+n_B-2)\).

**Corresponding exercise:** idx 13.

---

### Module 15: Cramér–Rao Bound and Efficient Estimation

**Core concepts:**

- Fisher information: \(I(\theta)=E\left[\left(\frac{\partial\ln f}{\partial\theta}\right)^2\right]\).
- Cramér–Rao bound: \(\frac1{nI(\theta)}\).
- An unbiased estimator attaining the CR bound is called efficient.

**Standard solution steps:**

1. Calculate \(\frac{\partial\ln f}{\partial\theta}\).
2. Find Fisher information \(I(\theta)\).
3. CR bound \(=1/(nI(\theta))\).
4. Compare \(\operatorname{Var}(\hat\theta)\) with the CR bound.

**Corresponding exercise:** idx 14.

---

### Module 16: MSE and Bias–Variance Tradeoff

**Core concept:** \(\operatorname{MSE}(\hat\theta)=\operatorname{Var}(\hat\theta)+[b(\hat\theta)]^2\).

An estimator with slight bias but lower variance can have better MSE.

**Corresponding exercise:** idx 15.

---

### Module 17: Type-I/Type-II Errors and Test Power

**Core concepts:**

- Type-I error (\(\alpha\)): reject when \(H_0\) is true.
- Type-II error (\(\beta\)): do not reject when \(H_0\) is false.
- Power: \(1-\beta\), the probability of correctly rejecting a false \(H_0\).

**Calculation steps:**

1. Determine the rejection region (from the distribution under \(H_0\)).
2. At a specified value under \(H_1\), calculate the probability of accepting \(H_0\), giving \(\beta\).
3. Power \(=1-\beta\).

**Corresponding exercise:** idx 16.

---

### Module 18: \(\chi^2\) Goodness-of-Fit Test

**Core formula:** \(\chi^2=\sum\frac{(O_i-E_i)^2}{E_i}\sim\chi^2(k-1)\), with \(k\) categories.

**Standard solution steps:**

1. Determine \(H_0\) (e.g. “uniform distribution”).
2. Calculate expected frequency \(E_i=n\cdot p_i\).
3. Calculate the \(\chi^2\) statistic.
4. Compare against \(\chi^2_\alpha(k-1)\) and decide whether to reject.

**Corresponding exercise:** idx 17.

---

### Module 19: One-Way Analysis of Variance

**Core concept:** compare whether means of multiple (\(\ge2\)) populations are equal.

**Core formulas:**

- \(SST=SSA+SSE\) (total variation = between-group + within-group).
- \(MSA=SSA/(k-1)\), \(MSE=SSE/(n-k)\).
- \(F=MSA/MSE\sim F(k-1,n-k)\).

**Corresponding exercise:** idx 18.

---

### Module 20: Likelihood-Ratio Test

**Core concept:** \(\lambda(\mathbf X)=\frac{\sup_{\theta\in\Theta_0}L(\theta)}{\sup_{\theta\in\Theta}L(\theta)}\).

- \(0\le\lambda\le1\).
- A small \(\lambda\) favors rejection of \(H_0\).
- In large samples, \(-2\ln\lambda\sim\chi^2\).

**Corresponding exercise:** idx 19.

---

### Competition Extension: Measures of Data Dispersion

**Core concept:** different dispersion measures characterize data variability from different perspectives, each with strengths and weaknesses.

| Measure | Formula | Feature |
|---|---|---|
| Range | \(R=x_{\max}-x_{\min}\) | Uses only two extremes; loses much information and is extremely affected by outliers |
| Interquartile range (IQR) | \(IQR=Q_3-Q_1\) | Range of the middle \(50\%\) of data; robust to outliers |
| Variance | \(\sigma^2=\frac1n\sum(x_i-\bar x)^2\) (population); \(s^2=\frac1{n-1}\sum(x_i-\bar x)^2\) (sample) | Has units; cannot directly compare dispersion of data with different units |
| Standard deviation (SD) | Square root of variance | Same units as raw data; most commonly used |
| Coefficient of variation (CV) | \(CV=\frac{s}{\bar x}\times100\%\) | Unitless; compares dispersion of data with different units or greatly different mean levels |

**Frequent exam pitfalls:**

- Range is extremely affected by outliers; a single outlier can completely change it. IQR is robust to outliers and suits skewed distributions.
- Variance has units. To compare dispersion of two data sets with different units, use CV rather than directly comparing variances or standard deviations.
- When comparing “which data set fluctuates more,” first decide whether units differ or mean levels differ greatly: if either does, CV is the only correct option.

**Exam techniques:**

- If given two data sets with greatly different means (e.g. height and weight) and asked to compare dispersion, calculate and compare CV directly.
- The \(n-1\) denominator of sample variance (degrees-of-freedom correction) ensures unbiasedness; population variance uses \(n\).

---

### Competition Extension: Selecting Statistical Graphics

**Core concept:** different statistical graphics suit different data types and analytical objectives. Selecting the wrong graphic makes information unclear or even misleading.

| Graphic | Applicable setting | Key feature |
|---|---|---|
| Histogram | Distribution shape (symmetry, skewness, kurtosis) and central tendency of one continuous variable | For **continuous data**; bars touch with no gaps |
| Box plot | Five-number summary (minimum, \(Q_1\), median, \(Q_3\), maximum); comparison of distributions of multiple groups and outlier identification | Shows median rather than mean; outliers are separate points |
| Scatterplot | Relation between two continuous variables (correlation, trend, clusters) | Requires **two variables** |
| Line chart | Change over time; time-series data | Emphasizes trend rather than individual observations |
| Bar chart | Comparison of categorical (discrete) data | For **categorical variables**; bars have gaps |
| Pie chart | Proportions of parts of a whole | Do not use too many categories; emphasizes composition |

**Frequent exam pitfalls:**

- Confusing histograms with bar charts: histograms are for continuous variables (touching bars), bar charts are for categorical variables (gaps between bars).
- Using a scatterplot for univariate data: a scatterplot requires two variables on horizontal and vertical axes.
- Do not select a scatterplot (requires two variables), a line chart (requires a time dimension), or a pie chart (requires category proportions) to display a univariate distribution.

**Exam technique:**

- Given a research objective such as “show the distribution shape of students’ heights in a class,” diagnose in order: one-variable distribution shape \(\to\) histogram or box plot; relation between two variables \(\to\) scatterplot; time trend \(\to\) line chart; category comparison \(\to\) bar chart.
- For an overview of a large univariate data set in an exam, a histogram is the best choice.

---

### Competition Extension: Classification and Transformation of Time Series

**Core concept:** by indicator type, time series are classified as period series, point series, relative-number time series, and average-indicator time series.

| Category | Definition | Can values be added? | Example |
|---|---|---|---|
| Period series | Each indicator reflects accumulated total over an interval | **Yes**; accumulation is meaningful | Monthly sales, annual GDP |
| Point series | Each indicator reflects an instantaneous state at a particular time | **No**; accumulation is meaningless | Year-end population, month-end inventory |
| Relative-number time series | Ratios of two related aggregate indicators at the same time points, arranged by time | Depends on composition | Profit-rate series |
| Average-indicator time series | Average indicators arranged chronologically | Depends on composition | Monthly average-wage series |

**Frequent exam pitfalls:**

- Adding a point series as though it were a period series: sums of point-series values have no practical economic meaning.
- Treating a relative-number time series as an aggregate-indicator time series: it is formed from ratios, not original aggregate data.
- Confusing period series with continuous observation: a period series reflects accumulated amount; discontinuous observation does not alter its nature.

**Exam technique:**

- Questions commonly ask “can a period series be added?” or “is summing a point series meaningful?” Ask: “does the accumulated result have practical meaning?” Two months of sales can be added (two-month cumulative sales); two time-point population counts cannot (they are not total population).
- The numerator and denominator of a relative-number time series can both be aggregate-indicator time series, but their ratio is itself a relative indicator; chronologically arranged, it is a relative-number time series.

---

### Competition Extension: Time-Series Components and Decomposition Models

**Core concept:** classical time-series analysis decomposes a series into four basic components, combined with additive or multiplicative models.

**Definitions of four components:**

- **Long-term trend (Trend, \(T\))**: basic direction of development over a long period (rising, falling, or stable), reflecting the essential change in a phenomenon.
- **Seasonal variation (Seasonal, \(S\))**: regular fluctuations with a fixed cycle within a year (e.g. down-jacket sales high in winter and ice-cream sales high in summer). Seasonal cycle length is fixed (12 months for monthly data and 4 quarters for quarterly data).
- **Cyclical variation (Cyclical, \(C\))**: long-run fluctuations of nonfixed period (e.g. economic expansions and contractions). It differs from seasonal variation because cycle length is nonfixed (usually several years).
- **Irregular variation (Irregular, \(I\))**: fluctuation caused by random or accidental factors other than the three above, also called random variation.

**Decomposition models:**

- **Additive model:** \(Y_t=T_t+S_t+C_t+I_t\).
  - Components are independent and do not affect one another.
  - Applies when components have the same units and seasonal fluctuation amplitude does not change with trend level.
- **Multiplicative model:** \(Y_t=T_t\times S_t\times C_t\times I_t\).
  - Components interact.
  - Applies when seasonal fluctuation amplitude grows with the trend level (more common in socioeconomic data).

**Frequent exam pitfalls:**

- Confusing seasonal and cyclical variation: seasonal cycles are **fixed** (within a year), while cyclical periods are **nonfixed** (usually years); this is a frequent true/false and multiple-choice point.
- Thinking seasonal variation exists only in quarterly data: it means any regular fluctuation with a fixed period within one year, so monthly and quarterly data can both have a seasonal component.

**Exam technique:**

- Seeing “fluctuation amplitude grows as level grows” \(\to\) select the multiplicative model.
- Seeing “fluctuation amplitude is stable and does not change with trend” \(\to\) select the additive model.
- If a multiple-choice stem explicitly lists long-term trend, seasonal variation, cyclical variation, and random variation, check all four using that textbook’s convention.

---

### Competition Extension: Seasonal-Adjustment Methods

**Core concept:** seasonal adjustment removes seasonal components from an original time series so trends and cyclical variation can be seen more clearly.

**Method 1: Moving Average**

- Core idea: smooth the original series through a centered moving average, eliminating seasonal and irregular components.
  - Monthly data usually use a **12-term moving average**; quarterly data use a **4-term moving average**.
  - An even-term moving average (such as 4-term or 12-term) must undergo a further 2-term moving average to align time points (centering).
- Important property: the resulting series loses items at both ends. A length-\(n\) series with a \(k\)-term moving average has length \(n-k+1\); a centered \(k\)-term moving average has length \(n-k\).

**Method 2: Decomposition Method**

- Standard steps:
  1. Calculate centered moving averages to estimate trend–cycle component \((T_t\times C_t)\).
  2. Separate trend from original series to obtain seasonal–irregular component \((S_t\times I_t)\).
  3. Average \(S_t\times I_t\) values in the same season (e.g. same month) to obtain unadjusted **seasonal indices**.
  4. Adjust seasonal indices so their sum within one cycle equals cycle length (monthly sum \(=12\), quarterly sum \(=4\)).
  5. Divide the original series by the seasonal index to obtain the seasonally adjusted series.

**Method 3: X-13ARIMA-SEATS**

- Professional seasonal-adjustment software used by modern statistical agencies (e.g. the National Bureau of Statistics and U.S. Census Bureau).
- Combines ARIMA models for preadjustment, handling outliers, calendar effects, trading-day effects, holiday effects, and more.
- Main advantage: automatically detects and handles outliers, moving-holiday effects, and structural breaks in data.

**Frequent exam pitfalls:**

- An even-term moving average must be centered: a 12-term moving average corresponds to time point \(6.5\), so it cannot directly align with the original series and requires a further 2-term centered moving average.
- Moving averages shorten a series: a 12-term centered moving average loses 6 observations at each end.
- In monthly decomposition, seasonal indices sum to \(12\), not \(1\); in quarterly decomposition, they sum to \(4\).

**Exam technique:**

- A fill-in question asking “how many terms in a moving average?” \(\to\) monthly data: 12 terms; quarterly data: 4 terms.
- A discrimination question asking “which method handles calendar effects?” \(\to\) X-13ARIMA-SEATS.
- A question asking whether further processing is needed after a moving average \(\to\) even-term averages require 2-term centering.

---

## Part II: General Problem-Solving Methodology

### Problem-Type Recognition Flowchart

```
Statistical-inference problem
├── Find an estimator
│   ├── One parameter → method of moments or MLE
│   └── Two parameters → method of moments (requires second moment) or MLE
├── Evaluate an estimator
│   ├── Unbiasedness → calculate expectation
│   ├── Efficiency → compare variances
│   └── Consistency → determine convergence as n→∞
├── Interval estimation
│   ├── Mean (σ known) → Z interval
│   ├── Mean (σ unknown) → t interval
│   ├── Variance → χ² interval
│   └── Difference of means → Z or t interval
├── Hypothesis testing
│   ├── One population mean → Z or t test
│   ├── One population variance → χ² test
│   ├── Ratio of two population variances → F test
│   └── Difference of two population means → t test
└── Advanced topics
    ├── Analysis of variance → F test
    ├── Goodness of fit → χ² test
    └── Likelihood ratio → -2lnλ
```

### Quick Reference for Critical Quantiles (\(\alpha=0.05\))

| Distribution | Two-sided | Applicable setting |
|---|---|---|
| \(z\) | \(z_{0.025}=1.96\) | Mean (\(\sigma\) known) |
| \(t\) | Look up table | Mean (\(\sigma\) unknown) |
| \(\chi^2\) | Upper and lower quantiles are asymmetric | Variance |
| \(F\) | Upper and lower quantiles are asymmetric | Variance ratio |

---

## Part III: Exercise Index

| idx | Problem keywords | Knowledge point | Difficulty |
|---:|---|---|---|
| 0 | Poisson method of moments | Method of moments | Easy |
| 1 | Bernoulli MLE | MLE (discrete) | Easy |
| 2 | Normal MLE | MLE (continuous) | Easy |
| 3 | Unbiasedness determination | Unbiasedness | Intermediate |
| 4 | \(U(0,\theta)\) unbiased correction | Consistency | Intermediate |
| 5 | \(95\%\) CI for \(\mu\) (\(\sigma\) known) | Z interval | Intermediate |
| 6 | \(95\%\) CI for \(\mu\) (\(\sigma\) unknown) | \(t\) interval | Intermediate |
| 7 | \(95\%\) CI for \(\sigma^2\) | \(\chi^2\) interval | Intermediate |
| 8 | CI for \(\mu_1-\mu_2\) | Difference of two population means | Intermediate |
| 9 | Z test (\(\mu=500\)) | Z test | Intermediate |
| 10 | t test (\(\mu=20\)) | t test | Intermediate |
| 11 | \(\chi^2\) test (\(\sigma^2\)) | \(\chi^2\) test | Intermediate |
| 12 | F test (variance ratio) | F test | Hard |
| 13 | Two-sample t test | Difference of two population means | Hard |
| 14 | CR bound and efficient estimation | Estimator evaluation | Easy |
| 15 | MSE comparison | Bias–variance tradeoff | Intermediate |
| 16 | Type-I/type-II errors and power | Power analysis | Intermediate |
| 17 | Die-uniformity test | Goodness of fit | Intermediate |
| 18 | One-way ANOVA | ANOVA | Hard |
| 19 | Likelihood-ratio test | Likelihood ratio | Hard |

## General Supplement: Judging Basic Statistical Concepts

1. First distinguish location, dispersion, and shape measures; mean, variance, standard deviation, and quantiles are not interchangeable.
2. A time series is usually decomposed into trend, seasonal, cyclical, and irregular components; a relative-number series depends on its construction and cannot be asserted merely from a description other than “a ratio of two aggregates.”
3. Choose a graphic by task: distributional shape/outliers, variable association, and time evolution each require different graphics. First determine data type and comparison purpose.

## Quick Reference: Statistical Inference and Time-Series Classification

- For estimation, state the parameter space and sample assumptions, derive candidates through moment equations or log likelihood, then check boundaries, unbiasedness, variance, and mean squared error.
- For intervals and tests, select critical values using the statistic's distribution, degrees of freedom, confidence level, and one- or two-sided direction. Report the statistic, rejection region or $p$ value, and conditions of use.
- For time series, distinguish period from point-in-time data, and total from relative or average indicators. A ratio's category follows the economic meanings, units, and additivity of numerator and denominator.
- In decomposition and forecasting, distinguish trend, seasonal, cyclical, and irregular components, as well as additive from multiplicative models.

## Direct-Solution References: Objective Statistical-Inference Items

- Comparing two aggregate-indicator time series to form their ratio produces a relative-number time series: $\boxed{\text{True}}$.
- For the specified normal-distribution item, the required option is $\boxed{B}$: mean and **standard deviation**. Although $N(\mu,\sigma^2)$ writes a variance in the second slot, the answer convention here names $\sigma$.
- The specified time-series-components multiple choice requires $\boxed{A,B,C,D,E}$; random variation and irregular variation are both counted under this item's convention.
- The two requested seasonal-adjustment methods are $\boxed{\text{moving-average method, time-series decomposition method}}$. For example, quarterly and monthly series naturally use four-term and twelve-term moving averages, respectively.
- The required indicator of data dispersion is $\boxed{\text{standard deviation}}$, not variance (whose unit is squared), range, or coefficient of variation. It is $\sigma=\sqrt{\sum(x_i-\bar x)^2/n}$.
- For rapidly understanding the basic distributional characteristics of a large univariate data set, the required option is $\boxed{A}$, a histogram. A box plot emphasizes comparison/outliers, a scatter plot association, and a line chart time trend.
