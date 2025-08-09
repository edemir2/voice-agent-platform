### SQL Shell Kullanımı
Database bu şekilde oluşturulur:

1.  **PSQL Shell Aç:**
    ```bash
    CREATE DATABASE deneme_v1
    ```

2.  **Oluşturduğun veritabanını gör:**
    ```bash
    \l
    ```

3.  **Yeni oluşturulan veritabanına geç:**
    ```bash
    \c deneme_v1
    ```
4.  **TABLE oluştur**
    ```bash
    CREATE TABLE demo (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(150) NOT NULL,
    business_type VARCHAR(100) NOT NULL CHECK (business_type IN ('Retail Store', 'Restaurant/Cafe', 'Service Business', 'Healthcare', 'Real Estate', 'Other')),
    phone_number VARCHAR(20),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    ```

5.  **Oluşturulmuş TABLE'ları gör:**
    ```bash
    \dt
    ```
    
6.  **TABLE'ı sil <span style="color:red; font-weight:bold">KALICI OLARAK SİLER</span>**
    ```bash
    DROP TABLE demo;
    ```



