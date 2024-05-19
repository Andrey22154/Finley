import psycopg2
import os

def create_tables():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS forecasts (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            forecast_date DATE NOT NULL,
            predicted_price FLOAT NOT NULL
        )
        """,
    )
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT')
        )
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_tables()
