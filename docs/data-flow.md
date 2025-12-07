
Data Flow:

  API/Source → raw → staging → mart → Dashboard
     ↓          ↓        ↓        ↓
   ดึงมา     เก็บดิบ   transform  aggregate
                      + clean    + พร้อมใช้

  ตัวอย่างจริง:

  | Layer   | ข้อมูล                     | ตัวอย่าง
             |
  |---------|----------------------------|---------------------------
  ---------------|
  | raw     | ข้อมูลดิบจาก API ทุก field | JSON จาก Shopee API
             |
  | staging | Clean + normalize          | stg_orders - format
  เดียวกันทุก platform |
  | mart    | Aggregate พร้อมใช้         | mart_daily_performance -
  สรุปรายวัน      |

  ทำไมต้อง 3 layers?

  1. raw → เก็บไว้ debug / audit trail
  2. staging → รวม data จากหลาย source เป็น format เดียว
  3. mart → Dashboard query เร็ว, ไม่ต้อง join เยอะ

  ---
  ในงานจริง ETL Pipeline จะรันอัตโนมัติ (Cloud Scheduler) ทุกวัน:
  ดึง API → raw → staging → mart → Dashboard refresh