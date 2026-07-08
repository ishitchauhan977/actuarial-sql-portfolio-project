# Actuarial Seed Data Generator (Python Script)
# This script generates the 'seed_data.sql' file, populating it with:
# 1. Mortality Life Table data (ages 18-80 for Male/Female, Smoker/Non-Smoker)
# 2. 150 simulated Life Insurance Policies
# 3. Claim logs representing death events matching statistical risk models.

import random
import math

# Set random seed for reproducibility
random.seed(42)

def generate_seed_sql():
    sql_statements = []
    sql_statements.append("-- ====================================================================")
    sql_statements.append("-- ACTUARIAL PORTFOLIO: SEED DATA (CS1 & CM1 REPRESENTATIVE DATA)")
    sql_statements.append("-- Description: CSO-like mortality rates, policy underwriting, and claims.")
    sql_statements.append("-- ====================================================================\n")

    # 1. GENERATE MORTALITY LIFE TABLE (CS1 Probability & CM1 Mortality Rates)
    # qx starts at 0.0003 for age 18 and increases exponentially.
    # Smokers have 2.5x mortality risk. Males have ~20% higher than females.
    sql_statements.append("-- 1. SEED MORTALITY LIFE TABLE")
    for age in range(18, 81):
        for gender in ['Male', 'Female']:
            for is_smoker in [0, 1]:
                # Base qx modeling: qx = A * exp(B * age)
                base_qx = 0.00035 * math.exp((age - 18) * 0.075)
                if gender == 'Male':
                    base_qx *= 1.2
                if is_smoker == 1:
                    base_qx *= 2.3  # Smokers have much higher mortality
                
                # Cap qx at 0.99
                qx = min(base_qx, 0.99)
                
                # Life expectancy approximation (ex)
                ex = 85 - age
                if gender == 'Female':
                    ex += 4
                if is_smoker == 1:
                    ex -= 6
                ex = max(ex, 1.0)
                
                sql_statements.append(
                    f"INSERT INTO mortality_life_table (age, gender, is_smoker, qx, ex) "
                    f"VALUES ({age}, '{gender}', {is_smoker}, {qx:.6f}, {ex:.1f});"
                )
    
    # 2. GENERATE POLICIES (CM1 Pricing & Underwriting)
    sql_statements.append("\n-- 2. SEED POLICY PORTFOLIO")
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Wilson', 'Martinez', 'Anderson', 'Taylor', 'Thomas', 'Hernandez', 'Moore', 'Martin', 'Jackson', 'Thompson', 'White']
    
    policies = []
    
    for i in range(1, 151):
        policy_id = f"POL-{1000 + i}"
        holder_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        holder_age = random.randint(20, 65)
        holder_gender = 'Male' if random.random() > 0.5 else 'Female'
        is_smoker = 1 if random.random() > 0.85 else 0 # 15% smoker prevalence
        sum_assured = random.choice([100000, 150000, 200000, 250000, 300000, 500000])
        
        # Risk Class
        risk_class = 'Standard'
        if is_smoker == 0 and holder_age < 35:
            risk_class = 'Preferred'
        elif is_smoker == 1 or holder_age > 55:
            risk_class = 'Substandard'
            
        # CM1 Pricing: Office premium = Net Premium (qx * sum_assured) + Expense loading
        # Retrieve rough qx to calculate premium
        est_qx = 0.00035 * math.exp((holder_age - 18) * 0.075)
        if holder_gender == 'Male':
            est_qx *= 1.2
        if is_smoker == 1:
            est_qx *= 2.3
        
        # Gross premium charging model (Net expected claim cost + admin fee loading)
        net_premium = est_qx * sum_assured
        expense_loading = 120  # flat administrative fee (CB2 cost recovery)
        profit_loading = net_premium * 0.15 # profit loading
        annual_premium = round(net_premium + expense_loading + profit_loading)
        
        policies.append({
            'id': policy_id,
            'age': holder_age,
            'gender': holder_gender,
            'is_smoker': is_smoker,
            'sum_assured': sum_assured,
            'premium': annual_premium,
            'risk_class': risk_class
        })
        
        sql_statements.append(
            f"INSERT INTO policies (policy_id, holder_name, holder_age, holder_gender, is_smoker, sum_assured, annual_premium, risk_class, status) "
            f"VALUES ('{policy_id}', '{holder_name}', {holder_age}, '{holder_gender}', {is_smoker}, {sum_assured}, {annual_premium}, '{risk_class}', 'Active');"
        )
        
    # 3. GENERATE CLAIMS (CS1 Statistics & Claim Experience)
    # Simulate claims based on policyholder's mortality probability.
    sql_statements.append("\n-- 3. SEED CLAIMS")
    claim_id_counter = 1
    
    for policy in policies:
        # qx calculations matching table
        base_qx = 0.00035 * math.exp((policy['age'] - 18) * 0.075)
        if policy['gender'] == 'Male':
            base_qx *= 1.2
        if policy['is_smoker'] == 1:
            base_qx *= 2.3
            
        # Scale probability to simulate a small claims history
        claim_prob = base_qx * 8.0 # Scaled exposure factors
        
        if random.random() < claim_prob:
            claim_id = f"CLM-{2000 + claim_id_counter}"
            claim_id_counter += 1
            claim_amount = policy['sum_assured']
            
            # Simulate accident year and report lag (CS1 concept: statistical delay distributions)
            accident_year = random.choice([2023, 2024, 2025])
            accident_month = random.randint(1, 12)
            accident_day = random.randint(1, 28)
            accident_date = f"{accident_year}-{accident_month:02d}-{accident_day:02d}"
            
            # Report delay modeled as Exponential random variable (CS1 statistics)
            report_delay = int(random.expovariate(1.0 / 25.0)) # mean delay of 25 days
            
            sql_statements.append(
                f"INSERT INTO claims (claim_id, policy_id, claim_amount, accident_date, report_delay_days) "
                f"VALUES ('{claim_id}', '{policy['id']}', {claim_amount}, '{accident_date}', {report_delay});"
            )
            
            # Update matching policy status to 'Claimed'
            sql_statements.append(
                f"UPDATE policies SET status = 'Claimed' WHERE policy_id = '{policy['id']}';"
            )

    # Save to file
    with open("seed_data.sql", "w") as f:
        f.write("\n".join(sql_statements))
    print(f"Successfully generated seed_data.sql with {len(policies)} policies and {claim_id_counter-1} claims.")

if __name__ == "__main__":
    generate_seed_sql()
