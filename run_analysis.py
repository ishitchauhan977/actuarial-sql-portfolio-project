# ====================================================================
# ACTUARIAL PORTFOLIO RUNNER (CS1, CM1, & CB2 ALIGNED)
# Description: SQLite database build, seeding, analysis, and outputs.
# ====================================================================

import sqlite3
import os
import math
import random

# Set seed for reproducible data generation
random.seed(42)

DB_NAME = "actuarial.db"
SCHEMA_FILE = "schema.sql"
SEED_FILE = "seed_data.sql"
QUERIES_FILE = "actuarial_queries.sql"

def rebuild_database():
    print("--------------------------------------------------")
    print(f"1. Building Actuarial Database ({DB_NAME})...")
    print("--------------------------------------------------")
    
    # Remove existing database file if it exists
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Read and execute schema.sql DDL
    if not os.path.exists(SCHEMA_FILE):
        print(f"Error: {SCHEMA_FILE} not found!")
        return None
        
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
        
    cursor.executescript(schema_sql)
    conn.commit()
    print("✔ Database schema created successfully.")
    return conn

def generate_and_seed_data(conn):
    print("\n--------------------------------------------------")
    print("2. Generating & Seeding Actuarial Experience...")
    print("--------------------------------------------------")
    
    cursor = conn.cursor()
    sql_statements = [
        "-- ====================================================================",
        "-- ACTUARIAL PORTFOLIO: SEED DATA (CS1 & CM1 REPRESENTATIVE DATA)",
        "-- Description: CSO-like mortality rates, policy underwriting, and claims.",
        "-- ====================================================================\n"
    ]
    
    # A. SEED MORTALITY LIFE TABLE (CM1: Life Tables)
    sql_statements.append("-- A. SEED MORTALITY LIFE TABLE")
    mortality_records = []
    for age in range(18, 81):
        for gender in ['Male', 'Female']:
            for is_smoker in [0, 1]:
                # Base qx modeling: qx = A * exp(B * age)
                base_qx = 0.00035 * math.exp((age - 18) * 0.075)
                if gender == 'Male':
                    base_qx *= 1.2
                if is_smoker == 1:
                    base_qx *= 2.3
                
                qx = min(base_qx, 0.99)
                ex = max(85.0 - age + (4.0 if gender == 'Female' else 0.0) - (6.0 if is_smoker == 1 else 0.0), 1.0)
                
                mortality_records.append((age, gender, is_smoker, qx, ex))
                sql_statements.append(
                    f"INSERT INTO mortality_life_table (age, gender, is_smoker, qx, ex) "
                    f"VALUES ({age}, '{gender}', {is_smoker}, {qx:.6f}, {ex:.1f});"
                )
                
    cursor.executemany(
        "INSERT INTO mortality_life_table (age, gender, is_smoker, qx, ex) VALUES (?, ?, ?, ?, ?)",
        mortality_records
    )
    
    # B. SEED POLICIES (CM1: Pricing & Underwriting)
    sql_statements.append("\n-- B. SEED POLICY PORTFOLIO")
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Wilson', 'Martinez', 'Anderson', 'Taylor', 'Thomas', 'Hernandez', 'Moore', 'Martin', 'Jackson', 'Thompson', 'White']
    
    policies = []
    policy_sql_records = []
    
    for i in range(1, 151):
        policy_id = f"POL-{1000 + i}"
        holder_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        holder_age = random.randint(20, 65)
        holder_gender = 'Male' if random.random() > 0.5 else 'Female'
        is_smoker = 1 if random.random() > 0.85 else 0
        sum_assured = random.choice([100000, 150000, 200000, 250000, 300000, 500000])
        
        risk_class = 'Standard'
        if is_smoker == 0 and holder_age < 35:
            risk_class = 'Preferred'
        elif is_smoker == 1 or holder_age > 55:
            risk_class = 'Substandard'
            
        # Calculate annual premium using rough pricing factors
        est_qx = 0.00035 * math.exp((holder_age - 18) * 0.075)
        if holder_gender == 'Male':
            est_qx *= 1.2
        if is_smoker == 1:
            est_qx *= 2.3
            
        net_premium = est_qx * sum_assured
        expense_loading = 120
        profit_loading = net_premium * 0.15
        annual_premium = round(net_premium + expense_loading + profit_loading)
        
        policies.append({
            'id': policy_id, 'age': holder_age, 'gender': holder_gender,
            'is_smoker': is_smoker, 'sum_assured': sum_assured
        })
        policy_sql_records.append((policy_id, holder_name, holder_age, holder_gender, is_smoker, sum_assured, annual_premium, risk_class))
        sql_statements.append(
            f"INSERT INTO policies (policy_id, holder_name, holder_age, holder_gender, is_smoker, sum_assured, annual_premium, risk_class, status) "
            f"VALUES ('{policy_id}', '{holder_name}', {holder_age}, '{holder_gender}', {is_smoker}, {sum_assured}, {annual_premium}, '{risk_class}', 'Active');"
        )
        
    cursor.executemany(
        "INSERT INTO policies (policy_id, holder_name, holder_age, holder_gender, is_smoker, sum_assured, annual_premium, risk_class, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')",
        policy_sql_records
    )
    
    # C. SEED CLAIMS EXPERIENCE (CS1: Distributions & Random variables)
    sql_statements.append("\n-- C. SEED CLAIMS")
    claim_records = []
    update_statements = []
    claimed_policies = []
    claim_counter = 1
    
    for policy in policies:
        base_qx = 0.00035 * math.exp((policy['age'] - 18) * 0.075)
        if policy['gender'] == 'Male':
            base_qx *= 1.2
        if policy['is_smoker'] == 1:
            base_qx *= 2.3
            
        claim_prob = base_qx * 8.0 # Scale claim factors to simulate a portfolio
        
        if random.random() < claim_prob:
            claim_id = f"CLM-{2000 + claim_counter}"
            claim_counter += 1
            claim_amount = policy['sum_assured']
            
            accident_year = random.choice([2023, 2024, 2025])
            accident_month = random.randint(1, 12)
            accident_day = random.randint(1, 28)
            accident_date = f"{accident_year}-{accident_month:02d}-{accident_day:02d}"
            
            # Report delay modeled as an exponential variable: CS1 statistics
            report_delay = int(random.expovariate(1.0 / 25.0))
            
            claim_records.append((claim_id, policy['id'], claim_amount, accident_date, report_delay))
            claimed_policies.append((policy['id'],))
            
            sql_statements.append(
                f"INSERT INTO claims (claim_id, policy_id, claim_amount, accident_date, report_delay_days) "
                f"VALUES ('{claim_id}', '{policy['id']}', {claim_amount}, '{accident_date}', {report_delay});"
            )
            sql_statements.append(
                f"UPDATE policies SET status = 'Claimed' WHERE policy_id = '{policy['id']}';"
            )
            
    cursor.executemany(
        "INSERT INTO claims (claim_id, policy_id, claim_amount, accident_date, report_delay_days) VALUES (?, ?, ?, ?, ?)",
        claim_records
    )
    cursor.executemany(
        "UPDATE policies SET status = 'Claimed' WHERE policy_id = ?",
        claimed_policies
    )
    
    conn.commit()
    
    # Write generated SQL to seed_data.sql for GitHub portfolio transparency
    with open(SEED_FILE, 'w') as f:
        f.write("\n".join(sql_statements))
        
    print(f"✔ Database seeded. Created {len(mortality_records)} life table cells, {len(policies)} policies, and {len(claim_records)} claim events.")
    print(f"✔ Static data seed file written to '{SEED_FILE}' (ready for GitHub).")

def run_case_studies(conn):
    print("\n==================================================")
    print("3. RUNNING EXAM-ALIGNED CASE STUDIES")
    print("==================================================")
    
    if not os.path.exists(QUERIES_FILE):
        print(f"Error: {QUERIES_FILE} not found!")
        return
        
    with open(QUERIES_FILE, 'r') as f:
        content = f.read()
        
    # Split queries by delimiters
    queries = {}
    for i in range(1, 5):
        start_tag = f"-- QUERY_{i}_START"
        end_tag = f"-- QUERY_{i}_END"
        try:
            start_idx = content.index(start_tag) + len(start_tag)
            end_idx = content.index(end_tag)
            queries[i] = content[start_idx:end_idx].strip()
        except ValueError:
            print(f"Error: Tags for Query {i} not found in {QUERIES_FILE}!")
            
    cursor = conn.cursor()
    
    titles = {
        1: "CASE STUDY 1 [CM1]: Life Table Analysis & Survival Probabilities",
        2: "CASE STUDY 2 [CM1]: Life Assurance Pricing (Net Single Premium)",
        3: "CASE STUDY 3 [CS1]: Expected Claims vs. Actual Incurred Experience",
        4: "CASE STUDY 4 [CB2]: Cost Loading & Underwriting Margin Analysis"
    }
    
    for num, sql in queries.items():
        print(f"\n👉 {titles[num]}")
        print("-" * 75)
        
        try:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Print columns
            col_format = " | ".join([f"{{:<{max(len(col), 12)}}}" for col in columns])
            print(col_format.format(*columns))
            print("-" * 75)
            
            # Print rows
            for row in rows:
                formatted_row = []
                for val in row:
                    if isinstance(val, float):
                        formatted_row.append(f"{val:.2f}" if "premium" in columns or "claim" in columns else f"{val:.5f}")
                    else:
                        formatted_row.append(str(val))
                print(col_format.format(*formatted_row))
                
        except sqlite3.Error as e:
            print(f"SQL execution failed: {e}")
        print("-" * 75)

def main():
    conn = rebuild_database()
    if conn:
        generate_and_seed_data(conn)
        run_case_studies(conn)
        conn.close()
        print("\n✔ Analysis completed successfully. SQLite database file is ready.")
        print("--------------------------------------------------")

if __name__ == "__main__":
    main()
