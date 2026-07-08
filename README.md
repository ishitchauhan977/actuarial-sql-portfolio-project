# ActurRisk: Actuarial Pricing, Reserving & Risk SQL Engine

This portfolio project is designed to demonstrate advanced **SQL database engineering** and data analysis mapped directly to the core syllabi of actuarial professional exams: **IFoA CS1 (Actuarial Statistics 1)**, **CM1 (Actuarial Mathematics 1)**, and **CB2 (Business Economics)**.

Rather than simple CRUD queries, this database simulates a life insurance policy portfolio and applies core actuarial mathematical models (Equation of Value discounting, mortality table calculations, statistical expected values, and cost-load margins) directly inside relational database queries.

---

## 📌 Syllabus & Exam Topics Covered

### 1. CM1 (Actuarial Mathematics)
*   **Life Table Notation**: Calculating survival probabilities (${}_n p_x$), mortality rates ($q_x$), and deferred mortality probabilities from standard lifetables.
*   **Pricing via Equation of Value**: Calculating the Expected Present Value (EPV) of future claim payouts and pricing a 3-Year Term Life Assurance policy using Net Single Premium (NSP) formulas with compound interest discounting:
    $$v^t = (1 + i)^{-t}$$

### 2. CS1 (Actuarial Statistics)
*   **Mathematical Expectation & Variance**: Calculating expected claim losses ($E[X]$) and standard deviation bounds ($\sqrt{\text{Var}(X)}$) across a portfolio:
    $$E[Claims] = \text{Sum Assured} \times q_x$$
    $$\text{Var}(Claims) = \text{Sum Assured}^2 \times q_x(1 - q_x)$$
*   **Experience Study**: Auditing actual claimed policyholders against probability models (Actual vs. Expected deaths study).

### 3. CB2 (Business Economics)
*   **Premium Cost Loadings**: Analyzing gross office premiums charged against net pure premiums (mortality cost) to inspect expense loadings, cost recovery, and profit margins.
*   **Price Differentiation**: Analyzing how premium structures load risk differentially across demographic risk classes (e.g. standard vs. substandard risk loadings).

---

## 🗄️ Database Schema Design

The schema is written in [schema.sql](file:///C:/Users/ishit/.gemini/antigravity/scratch/actuarial-sql-portfolio-clean/schema.sql) and consists of three core tables optimized for analytical query execution:

```
                  +-----------------------+
                  |  mortality_life_table |
                  +-----------------------+
                  | age (PK)              |
                  | gender (PK)           |
                  | is_smoker (PK)        |
                  | qx, ex                |
                  +-----------+-----------+
                              | (Composite Underwriting Link)
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
                              | (1-to-Many Policy Claim Link)
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
```

### Table Dictionary:
1.  **`mortality_life_table`**: Houses standard mortality probabilities ($q_x$) and life expectancies ($e_x$) indexed by age, gender, and smoking status.
2.  **`policies`**: Houses underwritten policy contracts with underwriting risk classifications (Preferred, Standard, Substandard) and annual gross premiums.
3.  **`claims`**: Logs claim events resulting from death (status changes to 'Claimed'), including report delays.

### Optimizations:
*   `idx_policies_risk`: Composite index on `policies(holder_age, holder_gender, is_smoker)` to speed up multi-key experience joins with the mortality table.
*   `idx_claims_policy`: Index on foreign key `claims(policy_id)` to speed up claim audit aggregations.

---

## 📈 SQL Case Studies

All case study queries are coded in [actuarial_queries.sql](file:///C:/Users/ishit/.gemini/antigravity/scratch/actuarial-sql-portfolio-clean/actuarial_queries.sql).

### Case Study 1 [CM1]: Life Table Analysis & Survival Probabilities
Computes a 3-year survival probability ($_{3}p_{x}$) for cohorts of age 25, 45, and 65 (split by gender and smoking status) by joining the mortality table on progressive age increments.

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

### Case Study 2 [CM1]: Net Single Premium (NSP) Term Assurance Pricing
Prices a 3-year term assurance policy with a Sum Assured of $100,000 using compound interest discounting at $4\%$ ($i = 0.04$). The query calculates the Expected Present Value (EPV) of future claim payouts at each year of exposure.

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

### Case Study 3 [CS1]: Expected Value & Variance Experience Study
Computes the theoretical Expected Claims cost ($E[X]$) and Standard Deviation bounds ($\sqrt{\text{Var}(X)}$) using mortality rates and sum assured coverage. It compares these expected values against the actual incurred claim totals.

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

### Case Study 4 [CB2]: Cost Loading & Underwriting Margin Analysis
Measures the administrative and profit "loading factors" built into gross office premiums relative to the base net premium (expected mortality claims costs).

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

## 🛠️ How to Run the Database & Analysis

This project requires **only Python** to build and run. It has zero external package dependencies.

1.  Clone this repository or navigate to your project directory.
2.  Run the python runner script in your command line:
    ```bash
    python run_analysis.py
    ```

### What this script does:
1.  Creates a clean SQLite database file named `actuarial.db`.
2.  Executes `schema.sql` DDL to construct the tables.
3.  Simulates and seeds the database, exporting the fully generated SQL statements as a static file `seed_data.sql` (for full repository transparency).
4.  Runs all four case studies and outputs the results as formatted tables in your command line.
