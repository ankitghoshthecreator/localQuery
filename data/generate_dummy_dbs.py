import sqlite3
import os
import random

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def create_healthcare_db():
    db_path = os.path.join(DATA_DIR, "healthcare.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            dob DATE,
            gender TEXT
        );
        CREATE TABLE doctors (
            doctor_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            specialty TEXT
        );
        CREATE TABLE appointments (
            appointment_id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATE,
            status TEXT, -- 'completed', 'scheduled', 'cancelled'
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(doctor_id)
        );
    """)
    
    # Insert some dummy data
    cursor.executemany("INSERT INTO patients (first_name, last_name, dob, gender) VALUES (?, ?, ?, ?)", [
        ("John", "Doe", "1980-05-15", "M"),
        ("Jane", "Smith", "1992-11-20", "F")
    ])
    cursor.executemany("INSERT INTO doctors (first_name, last_name, specialty) VALUES (?, ?, ?)", [
        ("Alice", "Brown", "Cardiology"),
        ("Bob", "White", "General Practice")
    ])
    cursor.executemany("INSERT INTO appointments (patient_id, doctor_id, appointment_date, status) VALUES (?, ?, ?, ?)", [
        (1, 1, "2023-10-01", "completed"),
        (2, 2, "2023-10-05", "scheduled")
    ])
    
    conn.commit()
    conn.close()
    print(f"Created {db_path}")

def create_ecommerce_db():
    db_path = os.path.join(DATA_DIR, "ecommerce.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            country TEXT
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            price DECIMAL(10,2),
            category TEXT
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            order_date DATE,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        );
    """)
    
    cursor.executemany("INSERT INTO customers (name, email, country) VALUES (?, ?, ?)", [
        ("Tom Clark", "tom@example.com", "USA"),
        ("Sara Lee", "sara@example.com", "UK")
    ])
    cursor.executemany("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", [
        ("Laptop", 999.99, "Electronics"),
        ("Coffee Mug", 15.50, "Kitchen")
    ])
    cursor.executemany("INSERT INTO orders (customer_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?)", [
        (1, 1, 1, "2023-09-15"),
        (2, 2, 4, "2023-09-16")
    ])
    
    conn.commit()
    conn.close()
    print(f"Created {db_path}")

def create_hr_db():
    db_path = os.path.join(DATA_DIR, "hr.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT
        );
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            department_id INTEGER,
            salary DECIMAL(10,2),
            hire_date DATE,
            FOREIGN KEY(department_id) REFERENCES departments(department_id)
        );
    """)
    
    cursor.executemany("INSERT INTO departments (department_name) VALUES (?)", [("Engineering",), ("Sales",), ("Marketing",)])
    cursor.executemany("INSERT INTO employees (first_name, last_name, department_id, salary, hire_date) VALUES (?, ?, ?, ?, ?)", [
        ("Mike", "Davis", 1, 120000.00, "2020-01-10"),
        ("Emma", "Wilson", 2, 85000.00, "2021-03-15"),
        ("Liam", "Taylor", 1, 110000.00, "2022-06-20")
    ])
    
    conn.commit()
    conn.close()
    print(f"Created {db_path}")

if __name__ == "__main__":
    create_healthcare_db()
    create_ecommerce_db()
    create_hr_db()
    print("All dummy databases created successfully.")
