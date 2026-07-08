-- ====================================================================
-- ACTUARIAL PORTFOLIO: DATABASE SCHEMA (CS1 & CM1 ALIGNED)
-- Author: Actuarial Student Portfolio
-- Description: Schema for life insurance underwriting and experience tracking.
-- ====================================================================

-- 1. Baseline Actuarial Life Table (CM1 Syllabus: Life Tables)
-- Contains single-year mortality probabilities (qx) and remaining life expectancies (ex).
CREATE TABLE mortality_life_table (
    age INTEGER NOT NULL,
    gender TEXT CHECK(gender IN ('Male', 'Female')) NOT NULL,
    is_smoker INTEGER CHECK(is_smoker IN (0, 1)) NOT NULL,
    qx REAL NOT NULL CHECK(qx >= 0 AND qx <= 1), -- Probability of dying within 1 year at age x
    ex REAL NOT NULL CHECK(ex >= 0),            -- Life expectancy remaining in years
    PRIMARY KEY (age, gender, is_smoker)
);

-- 2. Underwritten Policy Portfolio (CM1 & CB2 Syllabus: Underwriting & Pricing)
-- Represents policy contracts active or claimed.
CREATE TABLE policies (
    policy_id TEXT PRIMARY KEY,
    holder_name TEXT NOT NULL,
    holder_age INTEGER NOT NULL CHECK(holder_age BETWEEN 18 AND 80),
    holder_gender TEXT CHECK(holder_gender IN ('Male', 'Female')) NOT NULL,
    is_smoker INTEGER CHECK(is_smoker IN (0, 1)) NOT NULL,
    sum_assured REAL NOT NULL CHECK(sum_assured > 0),       -- Sum assured payable on death (S)
    annual_premium REAL NOT NULL CHECK(annual_premium > 0), -- Office premium charged per year
    risk_class TEXT CHECK(risk_class IN ('Preferred', 'Standard', 'Substandard')) NOT NULL,
    status TEXT CHECK(status IN ('Active', 'Expired', 'Claimed')) DEFAULT 'Active'
);

-- 3. Incurred Claim Log (CS1 & CM1 Syllabus: Claims Experience)
-- Logs death claim events. In life insurance, claim amount equals sum assured.
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL,
    claim_amount REAL NOT NULL CHECK(claim_amount > 0),
    accident_date TEXT NOT NULL, -- Format: YYYY-MM-DD
    report_delay_days INTEGER NOT NULL CHECK(report_delay_days >= 0), -- CS1: delay distributions
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id) ON DELETE CASCADE
);

-- ====================================================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- ====================================================================
-- Speed up experience study queries linking policies to standard life tables
CREATE INDEX idx_policies_risk ON policies(holder_age, holder_gender, is_smoker);
-- Speed up claim audit joins
CREATE INDEX idx_claims_policy ON claims(policy_id);
