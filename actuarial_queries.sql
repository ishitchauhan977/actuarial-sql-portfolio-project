-- ====================================================================
-- ACTUARIAL PORTFOLIO: EXAM-ALIGNED CASE STUDY QUERIES
-- Syllabus Mapping: IFoA CS1 (Statistics), CM1 (Maths), CB2 (Economics)
-- ====================================================================

-- ====================================================================
-- CASE STUDY 1 [CM1]: Life Table Analysis & Survival Probabilities
-- Formula: n_p_x = p_x * p_{x+1} * ... * p_{x+n-1} where p_x = 1 - q_x
-- Calculates 3-year survival probabilities (3_p_x) for different cohorts.
-- ====================================================================
-- QUERY_1_START
SELECT 
    m0.gender,
    CASE WHEN m0.is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    m0.age AS starting_age,
    -- 1-year survival probability at age x
    ROUND(1 - m0.qx, 5) AS px,
    -- 1-year survival probability at age x+1
    ROUND(1 - m1.qx, 5) AS p_x_plus_1,
    -- 1-year survival probability at age x+2
    ROUND(1 - m2.qx, 5) AS p_x_plus_2,
    -- 3-year survival probability (3_p_x)
    ROUND((1 - m0.qx) * (1 - m1.qx) * (1 - m2.qx), 5) AS cumulative_3_px
FROM mortality_life_table m0
JOIN mortality_life_table m1 ON m1.age = m0.age + 1 
     AND m1.gender = m0.gender 
     AND m1.is_smoker = m0.is_smoker
JOIN mortality_life_table m2 ON m2.age = m0.age + 2 
     AND m2.gender = m0.gender 
     AND m2.is_smoker = m0.is_smoker
WHERE m0.age IN (25, 45, 65)
ORDER BY starting_age, m0.is_smoker;
-- QUERY_1_END


-- ====================================================================
-- CASE STUDY 2 [CM1]: Life Assurance Pricing (Net Single Premium)
-- Formula: NSP = Sum Assured * Sum_{t=1}^{3} [ v^t * (t-1)_p_x * q_{x+t-1} ]
-- Calculates Net Single Premium for a 3-Year Term Assurance (Sum Assured = $100,000, i = 4%).
-- Discount factors: v^t = (1 + 0.04)^(-t)
-- ====================================================================
-- QUERY_2_START
WITH term_pricing AS (
    SELECT 
        m0.age,
        m0.gender,
        m0.is_smoker,
        m0.qx AS q_x0,
        m1.qx AS q_x1,
        m2.qx AS q_x2,
        -- Discount factor v = 1 / 1.04
        1.0 / (1 + 0.04) AS v1,
        1.0 / ((1 + 0.04)*(1 + 0.04)) AS v2,
        1.0 / ((1 + 0.04)*(1 + 0.04)*(1 + 0.04)) AS v3
    FROM mortality_life_table m0
    JOIN mortality_life_table m1 ON m1.age = m0.age + 1 AND m1.gender = m0.gender AND m1.is_smoker = m0.is_smoker
    JOIN mortality_life_table m2 ON m2.age = m0.age + 2 AND m2.gender = m0.gender AND m2.is_smoker = m0.is_smoker
)
SELECT 
    age AS issue_age,
    gender,
    CASE WHEN is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    -- EPV of Year 1 claims: v * q_x
    ROUND(v1 * q_x0, 6) AS epv_year_1,
    -- EPV of Year 2 claims: v^2 * p_x * q_{x+1}
    ROUND(v2 * (1 - q_x0) * q_x1, 6) AS epv_year_2,
    -- EPV of Year 3 claims: v^3 * 2_p_x * q_{x+2}
    ROUND(v3 * (1 - q_x0) * (1 - q_x1) * q_x2, 6) AS epv_year_3,
    -- Net Single Premium for a $100,000 Sum Assured policy
    ROUND(100000 * (v1 * q_x0 + v2 * (1 - q_x0) * q_x1 + v3 * (1 - q_x0) * (1 - q_x1) * q_x2), 2) AS net_single_premium_100k
FROM term_pricing
WHERE age IN (25, 45, 65)
ORDER BY age, is_smoker;
-- QUERY_2_END


-- ====================================================================
-- CASE STUDY 3 [CS1]: Expected Values, Variance, & Claims Audit
-- Formulas: E[Claim] = Sum Assured * q_x
--           Var(Claim) = Sum Assured^2 * q_x * (1 - q_x)
-- Compares statistical expected claim costs with actual incurred claims.
-- ====================================================================
-- QUERY_3_START
WITH policy_expectations AS (
    SELECT 
        p.policy_id,
        p.holder_age,
        p.sum_assured,
        m.qx,
        -- E[X] = S * q_x (CS1 Probability Theory)
        p.sum_assured * m.qx AS expected_claim,
        -- Var(X) = S^2 * q_x * (1 - q_x) (CS1 Variance Theory)
        (p.sum_assured * p.sum_assured) * m.qx * (1 - m.qx) AS var_claim,
        -- Actual Incurred Cost
        CASE WHEN p.status = 'Claimed' THEN p.sum_assured ELSE 0 END AS actual_claim,
        CASE WHEN p.status = 'Claimed' THEN 1 ELSE 0 END AS actual_claim_count
    FROM policies p
    JOIN mortality_life_table m ON p.holder_age = m.age 
         AND p.holder_gender = m.gender 
         AND p.is_smoker = m.is_smoker
)
SELECT 
    CASE 
        WHEN holder_age BETWEEN 20 AND 34 THEN '20-34'
        WHEN holder_age BETWEEN 35 AND 49 THEN '35-49'
        WHEN holder_age BETWEEN 50 AND 64 THEN '50-64'
        ELSE '65+' 
    END AS age_cohort,
    COUNT(policy_id) AS total_policies,
    -- Total Expected Claims Cost
    ROUND(SUM(expected_claim), 2) AS expected_claim_total,
    -- Total Actual Claims Cost
    ROUND(SUM(actual_claim), 2) AS actual_claim_total,
    -- Standard Deviation of Expected Claims: sqrt(sum(Var))
    ROUND(SQRT(SUM(var_claim)), 2) AS std_dev_expected,
    -- Count comparisons
    ROUND(SUM(qx), 2) AS expected_deaths,
    SUM(actual_claim_count) AS actual_deaths
FROM policy_expectations
GROUP BY 1
ORDER BY 1;
-- QUERY_3_END


-- ====================================================================
-- CASE STUDY 4 [CB2]: Cost Loading & Underwriting Margin Analysis
-- Formula: Loading Margin % = ((Premium - Net Premium) / Premium) * 100
-- Evaluates gross pricing premiums against pure net mortality premium cost
-- to analyze administrative loading and profit margins (CB2 Cost Theory).
-- ====================================================================
-- QUERY_4_START
WITH pricing_data AS (
    SELECT 
        p.policy_id,
        p.holder_age,
        p.risk_class,
        p.is_smoker,
        p.annual_premium AS office_premium,
        -- Pure Premium = q_x * Sum Assured (expected claim cost)
        m.qx * p.sum_assured AS net_pure_premium
    FROM policies p
    JOIN mortality_life_table m ON p.holder_age = m.age 
         AND p.holder_gender = m.gender 
         AND p.is_smoker = m.is_smoker
)
SELECT 
    risk_class,
    CASE WHEN is_smoker = 1 THEN 'Smoker' ELSE 'Non-Smoker' END AS smoking_status,
    COUNT(policy_id) AS policy_count,
    ROUND(AVG(office_premium), 2) AS avg_office_premium,
    ROUND(AVG(net_pure_premium), 2) AS avg_net_pure_premium,
    -- Average loading charge in dollars (covers administration and risk capital)
    ROUND(AVG(office_premium - net_pure_premium), 2) AS avg_loading_dollars,
    -- Average margin percentage
    ROUND(AVG((office_premium - net_pure_premium) / office_premium) * 100, 1) AS loading_margin_percentage
FROM pricing_data
GROUP BY 1, 2
ORDER BY loading_margin_percentage DESC;
-- QUERY_4_END
