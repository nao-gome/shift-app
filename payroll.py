import streamlit as st
import pandas as pd
import os
import io
import datetime

# PDF生成用ライブラリ
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm

# 設定
st.set_page_config(page_title="給与計算システム", layout="wide")
DATA_DIR = 'data'

# --- 全銀フォーマット生成ロジック ---
def generate_zengin_data(df, payment_date_str, company_name_kana, company_code):
    """
    全銀協規定形式のテキストデータを生成する
    """
    def pad_str(s, length):
        if pd.isna(s): s = ""
        s = str(s)
        return s.ljust(length)[:length]

    def pad_num(n, length):
        if pd.isna(n): n = 0
        return str(int(n)).zfill(length)[:length]

    lines = []
    
    # 1. ヘッダーレコード
    header = (
        "1" + "21" + "0" +
        pad_num(company_code, 10) +
        pad_str(company_name_kana, 40) +
        payment_date_str +
        pad_num(1234, 4) + pad_str("ﾃｽﾄｷﾞﾝｺｳ", 15) +
        pad_num(111, 3) + pad_str("ﾎﾝﾃﾝ", 15) +
        "1" + pad_num(1234567, 7) + " " * 17
    )
    lines.append(header)

    # 2. データレコード
    total_count = 0
    total_amount = 0
    
    for _, row in df.iterrows():
        pay_amount = row['net_payment']
        if pay_amount <= 0: continue
            
        data_record = (
            "2" +
            pad_num(row.get('bank_code', ''), 4) +
            pad_str(row.get('bank_name_kana', ''), 15) +
            pad_num(row.get('branch_code', ''), 3) +
            pad_str(row.get('branch_name_kana', ''), 15) +
            "    " +
            pad_num(row.get('account_type', 1), 1) +
            pad_num(row.get('account_number', ''), 7) +
            pad_str(row.get('account_name_kana', ''), 30) +
            pad_num(pay_amount, 10) +
            "0" + " " * 20
        )
        data_record = data_record.ljust(120)
        lines.append(data_record)
        total_count += 1
        total_amount += pay_amount

    # 3. トレーラレコード
    trailer = (
        "8" + pad_num(total_count, 6) +
        pad_num(total_amount, 12) + " " * 101
    )
    lines.append(trailer.ljust(120))

    # 4. エンドレコード
    lines.append("9" + (" " * 119))
    
    text_data = "\r\n".join(lines) + "\r\n"
    return text_data.encode('cp932')

# --- 計算ロジック ---
def calculate_withholding_tax(taxable_income, dependents):
    """源泉徴収税額表（簡易版）"""
    if taxable_income < 88000: return 0
    adjusted_income = taxable_income - (dependents * 25000)
    if adjusted_income < 88000: return 0
    
    tax = 0
    if adjusted_income < 150000:
        tax = adjusted_income * 0.02
    elif adjusted_income < 300000:
        tax = (adjusted_income * 0.05) - 2000 
    else:
        tax = (adjusted_income * 0.10) - 10000 
    return max(0, int(tax))

def load_data():
    try:
        emp = pd.read_csv(os.path.join(DATA_DIR, 'employees.csv'), dtype={'employee_id': str, 'bank_code': str, 'branch_code': str, 'account_number': str})
        att = pd.read_csv(os.path.join(DATA_DIR, 'attendance_input.csv'), dtype={'employee_id': str})
        return emp, att
    except FileNotFoundError:
        st.error("データファイルが見つかりません。create_dummy.pyを実行してください。")
        return pd.DataFrame(), pd.DataFrame()

def calculate_salary(df):
    """給与計算実行"""
    hourly_mask = df['salary_type'] == 'Hourly'
    df.loc[hourly_mask, 'base_pay'] = df.loc[hourly_mask, 'base_salary'] * df.loc[hourly_mask, 'work_hours']
    monthly_mask = df['salary_type'] == 'Monthly'
    df.loc[monthly_mask, 'base_pay'] = df.loc[monthly_mask, 'base_salary']
    
    df.loc[hourly_mask, 'overtime_pay'] = df.loc[hourly_mask, 'base_salary'] * 1.25 * df.loc[hourly_mask, 'overtime_hours']
    df.loc[monthly_mask, 'overtime_pay'] = (df.loc[monthly_mask, 'base_salary'] / 160) * 1.25 * df.loc[monthly_mask, 'overtime_hours']
    
    df['transport_pay'] = df['transportation_daily'] * df['work_days']
    df['total_payment'] = df['base_pay'] + df['overtime_pay'] + df['transport_pay'] + df.get('allowance_position', 0)
    
    df['social_insurance'] = (df['total_payment'] * 0.145).astype(int)
    df['taxable_income'] = df['total_payment'] - df['social_insurance'] - df['transport_pay']
    
    if 'dependents' not in df.columns: df['dependents'] = 0
    else: df['dependents'] = df['dependents'].fillna(0)

    df['income_tax'] = df.apply(lambda row: calculate_withholding_tax(row['taxable_income'], row['dependents']), axis=1)
    df['deduction_total'] = df['social_insurance'] + df['income_tax']
    df['net_payment'] = df['total_payment'] - df['deduction_total']
    
    return df

def create_payslip_pdf(row):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    font_name = 'HeiseiKakuGo-W5'
    
    p.setFont(font_name, 20)
    p.drawString(20*mm, 270*mm, f"給与明細書 ({row['target_month']})")
    p.setFont(font_name, 12)
    p.drawString(20*mm, 255*mm, f"社員名: {row['name']} 様")
    p.drawString(130*mm, 255*mm, "株式会社バイブコーディング")
    p.line(20*mm, 250*mm, 190*mm, 250*mm)
    
    y_pos = 230
    p.drawString(20*mm, y_pos*mm, "【支給】")
    p.drawString(30*mm, (y_pos-10)*mm, f"基本給: ¥{row['base_pay']:,.0f}")
    p.drawString(30*mm, (y_pos-20)*mm, f"残業手当: ¥{row['overtime_pay']:,.0f}")
    p.drawString(30*mm, (y_pos-30)*mm, f"交通費: ¥{row['transport_pay']:,.0f}")
    p.drawString(30*mm, (y_pos-40)*mm, f"役職手当: ¥{row.get('allowance_position', 0):,.0f}")
    
    p.setFont(font_name, 14)
    p.drawString(30*mm, (y_pos-60)*mm, f"総支給額: ¥{row['total_payment']:,.0f}")

    p.setFont(font_name, 12)
    p.drawString(110*mm, y_pos*mm, "【控除】")
    p.drawString(120*mm, (y_pos-10)*mm, f"社会保険料: ¥{row['social_insurance']:,.0f}")
    p.drawString(120*mm, (y_pos-20)*mm, f"所得税: ¥{row['income_tax']:,.0f}")
    p.drawString(120*mm, (y_pos-40)*mm, f"控除合計: ¥{row['deduction_total']:,.0f}")
    
    p.rect(110*mm, (y_pos-60)*mm, 80*mm, 15*mm)
    p.setFont(font_name, 16)
    p.drawString(115*mm, (y_pos-55)*mm, f"差引支給額: ¥{row['net_payment']:,.0f}")
    
    p.setFont(font_name, 10)
    p.drawString(20*mm, 150*mm, "【勤怠備考】")
    p.drawString(20*mm, 140*mm, f"扶養人数: {int(row.get('dependents', 0))}人")
    p.drawString(20*mm, 130*mm, f"出勤日数: {row['work_days']}日 / 実働: {row['work_hours']}h / 残業: {row['overtime_hours']}h")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- UI構築 ---
st.title("💰 シンプル給与計算システム")

st.sidebar.header("メニュー")
menu = st.sidebar.radio("選択してください", ["ダッシュボード", "給与明細発行", "従業員マスタ編集"])

# 初期データの読み込み（マスタは必須）
emp_df, default_att_df = load_data()

if menu == "ダッシュボード":
    st.subheader("給与計算実行")
    
    # ★追加機能: 勤怠CSVアップロード
    uploaded_file = st.file_uploader("勤怠CSVファイルをアップロードしてください（未指定の場合はテストデータを使用）", type=['csv'])
    
    if uploaded_file is not None:
        try:
            att_df = pd.read_csv(uploaded_file, dtype={'employee_id': str})
            st.info(f"📄 アップロードされたファイルを使用します: {uploaded_file.name}")
        except Exception as e:
            st.error(f"ファイル読み込みエラー: {e}")
            att_df = default_att_df
    else:
        st.caption("※ファイルが選択されていないため、dataフォルダ内のテスト用データを使用します。")
        att_df = default_att_df

    if st.button("計算実行"):
        # データ結合と計算
        merged_df = pd.merge(att_df, emp_df, on='employee_id', how='left')
        result_df = calculate_salary(merged_df)
        st.session_state['result_df'] = result_df
        
        st.success("計算が完了しました！")
        
        # サマリー表示
        total_payout = result_df['total_payment'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("総支給額合計", f"¥{total_payout:,.0f}")
        col2.metric("対象人数", f"{len(result_df)}名")
        col3.metric("平均支給額", f"¥{total_payout/len(result_df):,.0f}")
        
        # 詳細テーブル
        st.dataframe(result_df[['name', 'salary_type', 'total_payment', 'social_insurance', 'income_tax', 'net_payment']].style.format({
            'total_payment': '¥{:,.0f}', 'social_insurance': '¥{:,.0f}', 'income_tax': '¥{:,.0f}', 'net_payment': '¥{:,.0f}'
        }))
        
        # CSVダウンロード
        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("計算結果をCSVでダウンロード", csv, "salary_result.csv")
    
    # 全銀データ作成エリア
    if 'result_df' in st.session_state:
        st.divider()
        st.subheader("🏦 全銀フォーマット（振込用ファイル）出力")
        
        col_fb1, col_fb2 = st.columns(2)
        with col_fb1:
            today = datetime.date.today()
            default_date = datetime.date(today.year, today.month, 25)
            pay_date = st.date_input("振込指定日", default_date)
            pay_date_str = pay_date.strftime('%m%d')
            
        with col_fb2:
            company_name_kana = st.text_input("振込依頼人名（半角カナ）", "ｶ)ﾊﾞｲﾌﾞｺｰﾃﾞｨﾝｸﾞ")
            company_code = st.text_input("会社コード（10桁）", "1234567890")
            
        if st.button("全銀ファイル生成 (.txt)"):
            try:
                zengin_bytes = generate_zengin_data(st.session_state['result_df'], pay_date_str, company_name_kana, company_code)
                st.download_button(
                    label="全銀データをダウンロード",
                    data=zengin_bytes,
                    file_name=f"zengin_{pay_date_str}.txt",
                    mime="text/plain"
                )
                st.info("💡 ダウンロードしたファイルは、ネットバンキングの「総合振込」メニューからアップロードしてください。")
            except Exception as e:
                st.error(f"生成エラー: {e}")

elif menu == "給与明細発行":
    st.subheader("📄 給与明細PDF発行")
    if 'result_df' in st.session_state:
        result_df = st.session_state['result_df']
        selected_employee = st.selectbox("社員を選択してください", result_df['name'])
        
        if st.button("PDFプレビュー生成"):
            target_row = result_df[result_df['name'] == selected_employee].iloc[0]
            pdf_data = create_payslip_pdf(target_row)
            st.success(f"{selected_employee} さんの明細を作成しました")
            st.download_button("PDFをダウンロード", pdf_data, f"payslip_{target_row['employee_id']}.pdf", "application/pdf")
    else:
        st.warning("まずは「ダッシュボード」で計算を実行してください。")

elif menu == "従業員マスタ編集":
    st.subheader("従業員マスタ編集")
    employees_path = os.path.join(DATA_DIR, 'employees.csv')
    if os.path.exists(employees_path):
        employees_df = pd.read_csv(employees_path, dtype={'employee_id': str, 'bank_code': str, 'branch_code': str, 'account_number': str})
        
        required_cols = ['bank_code', 'bank_name_kana', 'branch_code', 'branch_name_kana', 'account_type', 'account_number', 'account_name_kana']
        for col in required_cols:
            if col not in employees_df.columns:
                employees_df[col] = ""

        edited_df = st.data_editor(employees_df, num_rows="dynamic")
        if st.button("変更を保存"):
            edited_df.to_csv(employees_path, index=False, encoding='utf-8-sig')
            st.success("マスタ保存完了！")
            st.rerun()