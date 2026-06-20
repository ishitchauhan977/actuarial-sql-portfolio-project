# ActurRisk: Actuarial Pricing, Reserving & Risk SQL Engine

I built this to combine two things I've been working on actuarial exam prep and SQL. Instead of doing basic CRUD stuff, I set up a small database that mimics a life insurance portfolio, then wrote queries that actually do the math actuaries care about: discounting cash flows, working with mortality tables, expected values, loadings on premiums, the kind of calculations you'd normally do in Excel or R, but pushed into SQL instead.

### Survival probabilities and pricing
Working with life table notation — survival probabilities (${}_np_x$), mortality rates ($q_x$), deferred mortality probabilities pulled straight from standard life tables. From there I priced a 3-year term life assurance policy using the Equation of Value: get the expected present value of future claim payouts, then back into a Net Single Premium using compound interest discounting:

$$v^t = (1 + i)^{-t}$$

### Expected losses and experience checks
Calculated expected claim losses ($E[\text{Claims}]$) and their spread across the portfolio:

$$E[\text{Claims}] = \text{Sum Assured} \times q_x$$
$$\text{Var}(\text{Claims}) = \text{Sum Assured}^2 \times q_x(1 - q_x)$$

Also ran an actual vs expected deaths check comparing how many policyholders actually died against what the mortality model predicted, which is basically a mini experience study.

### Premium loadings
Compared gross office premiums against the net pure premium (the pure mortality cost) to see how much of the premium is expense loading vs. profit margin. Also looked at how loadings shift across risk classes e.g. standard vs. substandard to see how insurers price differential risk.
---

## Database schema

Three tables, kept simple on purpose so the queries stay readable. Full DDL is in [schema.sql](schema.sql).
```
            +-----------------------+
              |  mortality_life_table |
              +-----------------------+
              | age (PK)              |
              | gender (PK)           |
              | is_smoker (PK)        |
              | qx, ex                |
              +-----------+-----------+
                          |
                          v
              +-----------+-----------+
              |        policies       |
              +-----------------------+
              | policy_id (PK)        |
              | holder_name           |
              | holder_age, gender    |
              | is_smoker             |
              | sum_assured           |
              | annual_premium        |
              | risk_class, status    |
              +-----------+-----------+
                          |
                          v
              +-----------+-----------+
              |         claims        |
              +-----------------------+
              | claim_id (PK)         |
              | policy_id (FK)        |
              | claim_amount          |
              | accident_date         |
              | report_delay_days     |
              +-----------------------+

### 
`mortality_life_table` holds standard mortality rates ($q_x$) and life expectancies ($e_x$) by age, gender, and smoker status — this is the reference table everything else joins against. `policies` is the actual book of business: who's insured, their risk class (preferred/standard/substandard), sum assured, premium. `claims` logs what happened when someone in that book died — links back to `policies` via `policy_id`, and I track `report_delay_days` since claim reporting lag is something that comes up a lot in reserving.

I added two indexes once the experience-study queries started getting slow: one composite index on `policies(holder_age, holder_gender, is_smoker)` since that's the join key against the mortality table, and one on `claims(policy_id)` for the claim aggregations. Not strictly necessary at this data volume, but good practice.

---

## SQL case studies

All queries live in [actuarial_queries.sql](actuarial_queries.sql).

### 1. Survival probabilities across cohorts
Joins the mortality table against itself on progressive age increments to get a 3-year survival probability ($_3p_x$) for cohorts at age 25, 45, and 65, split by gender and smoker status.

```sql
SELECT 
    m0.gender,
    CASE WHEN m0.is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    m0.age AS starting_age,
    ROUND(1 - m0.qx, 5) AS px,
    ROUND(1 - m1.qx, 5) AS p_x_plus_1,
    ROUND(1 - m2.qx, 5) AS p_x_plus_2,
    ROUND((1 - m0.qx) * (1 - m1.qx) * (1 - m2.qx), 5) AS cumulative_3_px
FROM mortality_life_table m0
JOIN mortality_life_table m1 ON m1.age = m0.age + 1 AND m1.gender = m0.gender AND m1.is_smoker = m0.is_smoker
JOIN mortality_life_table m2 ON m2.age = m0.age + 2 AND m2.gender = m0.gender AND m2.is_smoker = m0.is_smoker
WHERE m0.age IN (25, 45, 65)
ORDER BY starting_age, m0.is_smoker;
```

---

### 2. Pricing a term assurance policy
Prices a 3-year term assurance with a $100,000 sum assured, discounted at 4% ($i = 0.04$), by working out the expected present value of the claim payout in each year of exposure.

```sql
WITH term_pricing AS (
    SELECT 
        m0.age, m0.gender, m0.is_smoker,
        m0.qx AS q_x0, m1.qx AS q_x1, m2.qx AS q_x2,
        1.0 / (1 + 0.04) AS v1,
        1.0 / ((1 + 0.04)*(1 + 0.04)) AS v2,
        1.0 / ((1 + 0.04)*(1 + 0.04)*(1 + 0.04)) AS v3
    FROM mortality_life_table m0
    JOIN mortality_life_table m1 ON m1.age = m0.age + 1 AND m1.gender = m0.gender AND m1.is_smoker = m0.is_smoker
    JOIN mortality_life_table m2 ON m2.age = m0.age + 2 AND m2.gender = m0.gender AND m2.is_smoker = m0.is_smoker
)
SELECT 
    age AS issue_age, gender,
    CASE WHEN is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    ROUND(v1 * q_x0, 6) AS epv_year_1,
    ROUND(v2 * (1 - q_x0) * q_x1, 6) AS epv_year_2,
    ROUND(v3 * (1 - q_x0) * (1 - q_x1) * q_x2, 6) AS epv_year_3,
    ROUND(100000 * (v1 * q_x0 + v2 * (1 - q_x0) * q_x1 + v3 * (1 - q_x0) * (1 - q_x1) * q_x2), 2) AS net_single_premium_100k
FROM term_pricing
WHERE age IN (25, 45, 65)
ORDER BY age, is_smoker;
```

---

### 3. Actual vs. expected claims
Works out expected claims ($E[X]$) and the standard deviation around that estimate for each age band, then compares it against what actually got claimed — a basic experience study.

```sql
WITH policy_expectations AS (
    SELECT 
        p.policy_id, p.holder_age, p.sum_assured, m.qx,
        p.sum_assured * m.qx AS expected_claim,
        (p.sum_assured * p.sum_assured) * m.qx * (1 - m.qx) AS var_claim,
        CASE WHEN p.status = 'Claimed' THEN p.sum_assured ELSE 0 END AS actual_claim,
        CASE WHEN p.status = 'Claimed' THEN 1 ELSE 0 END AS actual_claim_count
    FROM policies p
    JOIN mortality_life_table m ON p.holder_age = m.age AND p.holder_gender = m.gender AND p.is_smoker = m.is_smoker
)
SELECT 
    CASE 
        WHEN holder_age BETWEEN 20 AND 34 THEN '20-34'
        WHEN holder_age BETWEEN 35 AND 49 THEN '35-49'
        WHEN holder_age BETWEEN 50 AND 64 THEN '50-64'
        ELSE '65+' 
    END AS age_cohort,
    COUNT(policy_id) AS total_policies,
    ROUND(SUM(expected_claim), 2) AS expected_claim_total,
    ROUND(SUM(actual_claim), 2) AS actual_claim_total,
    ROUND(SQRT(SUM(var_claim)), 2) AS std_dev_expected,
    ROUND(SUM(qx), 2) AS expected_deaths,
    SUM(actual_claim_count) AS actual_deaths
FROM policy_expectations
GROUP BY 1
ORDER BY 1;
```

---

### 4. Premium loading by risk class
Looks at how much of the gross office premium is loading (admin cost + profit margin) on top of the net pure premium, broken down by risk class and smoker status.

```sql
WITH pricing_data AS (
    SELECT 
        p.policy_id, p.holder_age, p.risk_class, p.is_smoker,
        p.annual_premium AS office_premium,
        m.qx * p.sum_assured AS net_pure_premium
    FROM policies p
    JOIN mortality_life_table m ON p.holder_age = m.age AND p.holder_gender = m.gender AND p.is_smoker = m.is_smoker
)
SELECT 
    risk_class,
    CASE WHEN is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    COUNT(policy_id) AS policy_count,
    ROUND(AVG(office_premium), 2) AS avg_office_premium,
    ROUND(AVG(net_pure_premium), 2) AS avg_net_pure_premium,
    ROUND(AVG(office_premium - net_pure_premium), 2) AS avg_loading_dollars,
    ROUND(AVG((office_premium - net_pure_premium) / office_premium) * 100, 1) AS loading_margin_percentage
FROM pricing_data
GROUP BY 1, 2
ORDER BY loading_margin_percentage DESC;
```

---

## Running it

Just Python, no external packages needed.

```bash
python run_analysis.py
```

It builds a fresh `actuarial.db` SQLite file, runs `schema.sql` to set up the tables, seeds the data (dumping the seed statements to `seed_data.sql` so you can see exactly what was inserted), then runs all four queries and prints the results to the terminal.