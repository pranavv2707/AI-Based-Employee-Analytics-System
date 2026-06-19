import mysql.connector
from mysql.connector import Error
from faker import Faker
import os
from dotenv import load_dotenv
import logging

logger=logging.getLogger("db")
load_dotenv()
fake = Faker()

db_config = {
    "host":     os.getenv("DB_HOST", "localhost"), #added the default also just in case
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "mydb"),
}


def get_conn():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        logger.error(f"DB connection failed: {e}")
        raise


def initialise_db():
    try:
        config = {k: v for k, v in db_config.items() if k != "database"}
        c = mysql.connector.connect(**config)
        cursor = c.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}")
        cursor.execute(f"USE {db_config['database']}")

        cursor.execute("DROP TABLE IF EXISTS employees")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                first_name  VARCHAR(50)  NOT NULL,
                last_name   VARCHAR(50)   NOT NULL,
                email       VARCHAR(50)  NOT NULL UNIQUE,
                department  VARCHAR(50)   NOT NULL,
                job_title   VARCHAR(50)   NOT NULL,
                salary      DECIMAL(10,2) NOT NULL,
                hire_date   DATE    NOT NULL,
                created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
            )
        """)

        departments = ["Engineering", "HR", "Finance", "Marketing", "Sales", "Operations", "Legal"]
        job_titles  = ["Analyst", "Manager", "Engineer", "Director", "Specialist", "Coordinator", "Lead"]

        records = []
        for i in range(1000):
            records.append((
                fake.first_name(),
                fake.last_name(),
                fake.unique.email(),
                fake.random_element(departments),
                fake.random_element(job_titles),
                round(fake.random_number(digits=5) + 30000, 2),
                fake.date_between(start_date="-10y", end_date="today"),
            ))

        cursor.executemany("""
            INSERT INTO employees
                (first_name, last_name, email, department, job_title, salary, hire_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, records)

        c.commit()
        #stored procedure creation
        cursor.execute("DROP PROCEDURE IF EXISTS getallemployees")
        cursor.execute("""
            CREATE PROCEDURE getallemployees()
            BEGIN
                SELECT * FROM employees ORDER BY id;
            END
        """)

        c.commit()
        c.close()
        print("the database initialised with 1000 employee records.")


    except Error as e:
        logger.error(f"DB connection failed: {e}")
        raise