-- ====================================================================
-- ACTUARIAL PORTFOLIO: POSTGRESQL DATABASE SCHEMA
-- Author: Actuarial Student Portfolio
-- Description: Schema optimized for PostgreSQL database engines.
-- ====================================================================

-- Drop tables if they exist (for clean rebuilding)
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS mortality_life_table CASCADE;

-- 1. Baseline Actuarial Life Table (CM1 Syllabus: Life Tables)
CREATE TABLE mortality_life_table (
    age INT NOT NULL,
    gender VARCHAR(10) CHECK(gender IN ('Male', 'Female')) NOT NULL,
    is_smoker BOOLEAN NOT NULL,
    qx DOUBLE PRECISION NOT NULL CHECK(qx >= 0 AND qx <= 1), -- Probability of dying within 1 year
    ex DOUBLE PRECISION NOT NULL CHECK(ex >= 0),            -- Life expectancy remaining
    PRIMARY KEY (age, gender, is_smoker)
);

-- 2. Underwritten Policy Portfolio (CM1 & CB2 Syllabus: Underwriting & Pricing)
CREATE TABLE policies (
    policy_id VARCHAR(50) PRIMARY KEY,
    holder_name VARCHAR(100) NOT NULL,
    holder_age INT NOT NULL CHECK(holder_age BETWEEN 18 AND 80),
    holder_gender VARCHAR(10) CHECK(holder_gender IN ('Male', 'Female')) NOT NULL,
    is_smoker BOOLEAN NOT NULL,
    sum_assured NUMERIC(12, 2) NOT NULL CHECK(sum_assured > 0),
    annual_premium NUMERIC(10, 2) NOT NULL CHECK(annual_premium > 0),
    risk_class VARCHAR(20) CHECK(risk_class IN ('Preferred', 'Standard', 'Substandard')) NOT NULL,
    status VARCHAR(20) CHECK(status IN ('Active', 'Expired', 'Claimed')) DEFAULT 'Active'
);

-- 3. Incurred Claim Log (CS1 & CM1 Syllabus: Claims Experience)
CREATE TABLE claims (
    claim_id VARCHAR(50) PRIMARY KEY,
    policy_id VARCHAR(50) REFERENCES policies(policy_id) ON DELETE CASCADE NOT NULL,
    claim_amount NUMERIC(12, 2) NOT NULL CHECK(claim_amount > 0),
    accident_date DATE NOT NULL,
    report_delay_days INT NOT NULL CHECK(report_delay_days >= 0)
);

-- ====================================================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- ====================================================================
CREATE INDEX idx_policies_risk ON policies(holder_age, holder_gender, is_smoker);
CREATE INDEX idx_claims_policy ON claims(policy_id);
