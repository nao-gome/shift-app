import pandas as pd
import os
import random

os.makedirs('data', exist_ok=True)

# 1. 従業員マスタ (銀行情報を追加)
employees = [
    {
        "employee_id": "E001", "name": "山田 太郎", "base_salary": 1200, "salary_type": "Hourly", "transportation_daily": 500, "dependents": 0,
        "bank_code": "0001", "bank_name_kana": "ﾐｽﾞﾎ", "branch_code": "001", "branch_name_kana": "ﾎﾝﾃﾝ", "account_type": 1, "account_number": "1234567", "account_name_kana": "ﾔﾏﾀﾞ ﾀﾛｳ"
    },
    {
        "employee_id": "E002", "name": "鈴木 花子", "base_salary": 1300, "salary_type": "Hourly", "transportation_daily": 600, "dependents": 1,
        "bank_code": "0005", "bank_name_kana": "ﾐﾂﾋﾞｼUFJ", "branch_code": "002", "branch_name_kana": "ｼﾌﾞﾔ", "account_type": 1, "account_number": "2345678", "account_name_kana": "ｽｽﾞｷ ﾊﾅｺ"
    },
    {
        "employee_id": "E003", "name": "佐藤 次郎", "base_salary": 350000, "salary_type": "Monthly", "transportation_daily": 1000, "dependents": 3,
        "bank_code": "0009", "bank_name_kana": "ﾐﾂｲｽﾐﾄﾓ", "branch_code": "003", "branch_name_kana": "ｼﾝｼﾞｭｸ", "account_type": 1, "account_number": "3456789", "account_name_kana": "ｻﾄｳ ｼﾞﾛｳ"
    },
    {
        "employee_id": "E004", "name": "田中 美咲", "base_salary": 280000, "salary_type": "Monthly", "transportation_daily": 800, "dependents": 0,
        "bank_code": "0001", "bank_name_kana": "ﾐｽﾞﾎ", "branch_code": "001", "branch_name_kana": "ﾎﾝﾃﾝ", "account_type": 1, "account_number": "4567890", "account_name_kana": "ﾀﾅｶ ﾐｻｷ"
    },
    {
        "employee_id": "E005", "name": "高橋 健一", "base_salary": 1150, "salary_type": "Hourly", "transportation_daily": 0, "dependents": 2,
        "bank_code": "9900", "bank_name_kana": "ﾕｳﾁﾖ", "branch_code": "008", "branch_name_kana": "ｲﾁﾆｰｻﾝ", "account_type": 1, "account_number": "5678901", "account_name_kana": "ﾀｶﾊｼ ｹﾝｲﾁ"
    },
]
df_emp = pd.DataFrame(employees)
df_emp.to_csv('data/employees.csv', index=False)
print("✅ 従業員マスタを更新しました（銀行情報追加）")

# 2. 勤怠データ (変更なし)
attendance = []
for emp in employees:
    work_days = random.randint(18, 22)
    attendance.append({
        "employee_id": emp["employee_id"],
        "target_month": "2026-02",
        "work_days": work_days,
        "work_hours": work_days * 8,
        "overtime_hours": random.randint(0, 20),
        "late_night_hours": random.randint(0, 5)
    })
df_att = pd.DataFrame(attendance)
df_att.to_csv('data/attendance_input.csv', index=False)
print("✅ 勤怠データを更新しました")