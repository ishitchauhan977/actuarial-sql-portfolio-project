# Generates seed_data.sql — mortality table, a book of policies, and a matching claims log.
# Ages 18-80, split by gender and smoker status. 150 policies, claims simulated
# off the same mortality assumptions so the numbers stay internally consistent.

import random
import math

random.seed(42)  # keeping this fixed so results are reproducible

def generate_seed_sql():
    sql_statements = []
    sql_statements.append("-- mortality table, policies, and claims seed data\n")

    # qx roughly follows an exponential curve with age — starts around 0.0003 at 18.
    # smokers get ~2.3x the base rate, males run about 20% higher than females.
    # these multipliers aren't from a real table, just rough enough to be plausible.
    sql_statements.append("-- mortality table")
    for age in range(18, 81):
        for gender in ['Male', 'Female']:
            for is_smoker in [0, 1]:
                base_qx = 0.00035 * math.exp((age - 18) * 0.075)
                if gender == 'Male':
                    base_qx *= 1.2
                if is_smoker == 1:
                    base_qx *= 2.3
                
                qx = min(base_qx, 0.99)
                
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
    
    sql_statements.append("\n-- policies")
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Wilson', 'Martinez', 'Anderson', 'Taylor', 'Thomas', 'Hernandez', 'Moore', 'Martin', 'Jackson', 'Thompson', 'White']
    
    policies = []
    
    for i in range(1, 151):
        policy_id = f"POL-{1000 + i}"
        holder_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        holder_age = random.randint(20, 65)
        holder_gender = 'Male' if random.random() > 0.5 else 'Female'
        is_smoker = 1 if random.random() > 0.85 else 0  # roughly 15% smokers
        sum_assured = random.choice([100000, 150000, 200000, 250000, 300000, 500000])
        
        risk_class = 'Standard'
        if is_smoker == 0 and holder_age < 35:
            risk_class = 'Preferred'
        elif is_smoker == 1 or holder_age > 55:
            risk_class = 'Substandard'
            
        # rough qx estimate for pricing — same formula as the table above
        est_qx = 0.00035 * math.exp((holder_age - 18) * 0.075)
        if holder_gender == 'Male':
            est_qx *= 1.2
        if is_smoker == 1:
            est_qx *= 2.3
        
        # premium = net mortality cost + flat admin fee + a profit margin on top
        net_premium = est_qx * sum_assured
        expense_loading = 120
        profit_loading = net_premium * 0.15
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
        
    # claims are drawn per policy using that same mortality probability, scaled up
    # a bit so the dataset actually has a decent number of claims to analyze
    sql_statements.append("\n-- claims")
    claim_id_counter = 1
    
    for policy in policies:
        base_qx = 0.00035 * math.exp((policy['age'] - 18) * 0.075)
        if policy['gender'] == 'Male':
            base_qx *= 1.2
        if policy['is_smoker'] == 1:
            base_qx *= 2.3
            
        claim_prob = base_qx * 8.0
        
        if random.random() < claim_prob:
            claim_id = f"CLM-{2000 + claim_id_counter}"
            claim_id_counter += 1
            claim_amount = policy['sum_assured']
            
            accident_year = random.choice([2023, 2024, 2025])
            accident_month = random.randint(1, 12)
            accident_day = random.randint(1, 28)
            accident_date = f"{accident_year}-{accident_month:02d}-{accident_day:02d}"
            
            # delay between accident and report modeled as exponential, mean ~25 days
            report_delay = int(random.expovariate(1.0 / 25.0))
            
            sql_statements.append(
                f"INSERT INTO claims (claim_id, policy_id, claim_amount, accident_date, report_delay_days) "
                f"VALUES ('{claim_id}', '{policy['id']}', {claim_amount}, '{accident_date}', {report_delay});"
            )
            
            sql_statements.append(
                f"UPDATE policies SET status = 'Claimed' WHERE policy_id = '{policy['id']}';"
            )

    with open("seed_data.sql", "w") as f:
        f.write("\n".join(sql_statements))
    print(f"generated seed_data.sql — {len(policies)} policies, {claim_id_counter-1} claims")

if __name__ == "__main__":
    generate_seed_sql()