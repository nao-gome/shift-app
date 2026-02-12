import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import date
import plotly.express as px
import base64
import hashlib

# --- 0. セキュリティ関数 ---
def hash_password(password):
    """パスワードをSHA-256でハッシュ化（暗号化）する"""
    return hashlib.sha256(str(password).encode()).hexdigest()

# --- 1. ページ設定 ---
st.set_page_config(page_title="選手コンディション管理", page_icon="⚽", layout="wide")

def get_base64_image(image_path):
    if os.path.exists(str(image_path)):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

# カスタムCSS（デザイン・色の制御）
st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0 !important; }
    .full-width-header {
        background-color: #01579b; color: white; width: 100vw; position: relative;
        left: 50%; right: 50%; margin-left: -50vw; margin-right: -50vw; margin-bottom: 2rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center; min-height: 120px;
    }
    .full-width-header h1 { margin: 0 !important; font-size: 2.8rem; font-weight: 800; letter-spacing: 0.15em; }
    .stImage > img { object-fit: cover; width: 100%; height: 200px; border-radius: 8px; }
    .profile-container {
        display: flex; background-color: #f8f9fa; padding: 25px; border-radius: 15px;
        border-left: 10px solid #01579b; margin-bottom: 25px; align-items: center; gap: 35px;
        box-shadow: 2px 2px 12px rgba(0,0,0,0.08);
    }
    .profile-photo {
        width: 160px; height: 160px; border-radius: 50%; overflow: hidden;
        display: flex; justify-content: center; align-items: center;
        background-color: #eee; border: 4px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.15); flex-shrink: 0;
    }
    .profile-photo img { width: 100%; height: 100%; object-fit: cover; }
    .profile-details h2 { margin: 0 0 10px 0; color: #01579b; font-size: 2.2rem; }
    div.stButton > button { height: 100px; font-size: 22px !important; font-weight: 800 !important; border-radius: 12px; }
    button[kind="primary"] { background-color: #e1f5fe !important; color: #01579b !important; border-color: #81d4fa !important; }
    .leaderboard-card {
        background-color: #ffffff; padding: 12px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 8px; border-top: 4px solid #01579b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ準備 ---
MASTER_FILE = "player_master.csv"
CONDITION_FILE = "daily_condition.csv"
PHYSICAL_FILE = "physical_tests.csv"
IMAGE_DIR = "player_images"
if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

if os.path.exists(MASTER_FILE):
    df_players = pd.read_csv(MASTER_FILE)
    if not df_players.empty and len(str(df_players.iloc[0]["パスワード"])) != 64:
        df_players["パスワード"] = df_players["パスワード"].apply(hash_password)
        df_players.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
else:
    df_players = pd.DataFrame(columns=["背番号", "名前", "ポジション", "学年", "身長", "体重", "画像パス", "パスワード"])

if os.path.exists(CONDITION_FILE):
    df_cond = pd.read_csv(CONDITION_FILE)
    df_cond["日付"] = pd.to_datetime(df_cond["日付"]).dt.date
else:
    df_cond = pd.DataFrame(columns=["日付", "名前", "体重", "疲労度", "睡眠の質", "怪我痛み", "痛み詳細"])

if os.path.exists(PHYSICAL_FILE):
    df_phys = pd.read_csv(PHYSICAL_FILE)
    df_phys["日付"] = pd.to_datetime(df_phys["日付"]).dt.date
else:
    df_phys = pd.DataFrame(columns=["日付", "名前", "テスト種目", "数値"])

COLOR_MAP = {"睡眠の質": "#1f77b4", "疲労度": "#d62728"} #
PHYS_TESTS = ["30mスプリント (秒)", "プロアジリティ (秒)", "垂直跳び (cm)", "Yo-Yoテスト (m)"]

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_role" not in st.session_state: st.session_state.user_role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "show_form" not in st.session_state: st.session_state.show_form = None
if "selected_player_name" not in st.session_state: st.session_state.selected_player_name = None

# --- 3. ログイン画面 ---
if not st.session_state.authenticated:
    st.markdown('<div class="full-width-header"><h1>⚽ LOGIN</h1></div>', unsafe_allow_html=True)
    with st.container(border=True):
        u_id = st.text_input("名前（admin または 選手名）")
        u_pw = st.text_input("パスワード", type="password")
        if st.button("ログイン", width="stretch"):
            if u_id == "admin" and u_pw == st.secrets.get("admin_password", "admin123"):
                st.session_state.authenticated = True; st.session_state.user_role = "admin"; st.session_state.user_name = "管理者"; st.rerun()
            hashed_input = hash_password(u_pw)
            pm = df_players[(df_players["名前"] == u_id) & (df_players["パスワード"].astype(str) == hashed_input)]
            if not pm.empty:
                st.session_state.authenticated = True; st.session_state.user_role = "player"; st.session_state.user_name = u_id; st.rerun()
            else: st.error("ログイン情報が正しくありません")
    st.stop()

# --- 4. 共通ヘッダー ---
st.markdown(f'<div class="full-width-header"><h1>⚽ {st.session_state.user_name} モード</h1></div>', unsafe_allow_html=True)

with st.sidebar:
    st.write(f"👤: **{st.session_state.user_name}**")
    if st.button("ログアウト", key="logout_btn"): st.session_state.authenticated = False; st.rerun()
    st.divider()
    
    if st.session_state.user_role == "admin" and not df_players.empty:
        st.header("🛠️ 選手・テスト管理")
        plist = df_players["名前"].tolist()
        s_idx = plist.index(st.session_state.selected_player_name) if st.session_state.selected_player_name in plist else 0
        edit_target = st.selectbox("選手を選択", plist, index=s_idx)
        st.session_state.selected_player_name = edit_target
        target_row = df_players[df_players["名前"] == edit_target].iloc[0]
        
        # 【修正】プロフィール修正項目を5項目に拡大
        with st.expander("📝 選手プロフィール修正"):
            with st.form("edit_master_full"):
                e_na = st.text_input("名前", value=target_row["名前"])
                e_no = st.number_input("背番号", value=int(target_row["背番号"]))
                e_hi = st.number_input("身長 (cm)", value=float(target_row["身長"]))
                e_we = st.number_input("体重 (kg)", value=float(target_row["体重"]))
                e_pw = st.text_input("新PW（変更時のみ入力）", placeholder="未入力ならそのまま")
                if st.form_submit_button("選手情報を更新"):
                    idx = df_players[df_players["名前"] == edit_target].index[0]
                    final_pw = hash_password(e_pw) if e_pw else target_row["パスワード"]
                    df_players.loc[idx, ["名前", "背番号", "身長", "体重", "パスワード"]] = [e_na, e_no, e_hi, e_we, final_pw]
                    df_players.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig"); st.rerun()

        with st.expander("🏆 フィジカルテスト記録"):
            with st.form("add_phys_form"):
                t_type = st.selectbox("種目", PHYS_TESTS)
                t_val = st.number_input("数値", step=0.01)
                t_date = st.date_input("測定日", value=date.today())
                if st.form_submit_button("記録を保存"):
                    new_p = {"日付": t_date, "名前": edit_target, "テスト種目": t_type, "数値": t_val}
                    df_phys = pd.concat([df_phys, pd.DataFrame([new_p])], ignore_index=True)
                    df_phys.to_csv(PHYSICAL_FILE, index=False, encoding="utf-8-sig"); st.success("保存しました！"); st.rerun()

# --- 5. メインコンテンツ ---

if st.session_state.user_role == "admin":
    # --- 管理者ビュー (タブ順修正) ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕\n新規選手登録", width="stretch"): st.session_state.show_form = "p"; st.rerun()
    with col2:
        if st.button("📝\n体調データ入力", width="stretch"): st.session_state.show_form = "c"; st.rerun()

    if st.session_state.show_form == "p":
        with st.form("new_p", clear_on_submit=True):
            st.subheader("👤 選手新規登録")
            c1, c2 = st.columns(2)
            with c1:
                n_na = st.text_input("名前"); n_no = st.number_input("背番号", 1, 99); n_pw = st.text_input("初期PW", "1234")
            with c2:
                n_po = st.selectbox("ポジション", ["GK", "DF", "MF", "FW"]); n_hi = st.number_input("身長", value=170.0); n_we = st.number_input("体重", value=60.0); n_up = st.file_uploader("写真")
            if st.form_submit_button("登録"):
                path = os.path.join(IMAGE_DIR, f"{n_no}_{n_na}.jpg") if n_up else ""
                if n_up: Image.open(n_up).convert("RGB").resize((300, 300)).save(path)
                new_row = {"背番号": n_no, "名前": n_na, "ポジション": n_po, "学年": "高3", "身長": n_hi, "体重": n_we, "画像パス": path, "パスワード": hash_password(n_pw)}
                df_players = pd.concat([df_players, pd.DataFrame([new_row])], ignore_index=True); df_players.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig"); st.session_state.show_form = None; st.rerun()
    
    st.markdown("---")
    t1, t2, t3, t4, t5 = st.tabs(["📋 選手名簿", "📈 個別推移管理", "📊 チーム状況", "🏆 フィジカルテストボード", "✅ 未入力者"])
    
    with t1:
        cl = st.columns(4)
        for i, (idx, row) in enumerate(df_players.iterrows()):
            with cl[i%4]:
                with st.container(border=True):
                    if pd.notnull(row['画像パス']) and os.path.exists(str(row['画像パス'])): st.image(str(row['画像パス']), use_container_width=True)
                    st.markdown(f"### #{row['背番号']} {row['名前']}")
                    if st.button(f"詳細：{row['名前']}", key=f"v_{idx}", width="stretch"):
                        st.session_state.selected_player_name = row['名前']; st.rerun()
    
    with t2:
        if st.session_state.selected_player_name:
            p_name = st.session_state.selected_player_name
            p_cond = df_cond[df_cond["名前"] == p_name].sort_values("日付")
            st.write(f"### {p_name} 選手のデータ詳細")
            if not p_cond.empty:
                st.plotly_chart(px.line(p_cond, x="日付", y=["疲労度", "睡眠の質"], title="コンディション推移", markers=True, range_y=[0, 6], color_discrete_map=COLOR_MAP))
            
            p_phys = df_phys[df_phys["名前"] == p_name].sort_values("日付")
            if not p_phys.empty:
                st.write("#### フィジカルテスト推移")
                t_sel_admin = st.selectbox("種目を選択", PHYS_TESTS, key="admin_p_sel")
                t_data_admin = p_phys[p_phys["テスト種目"] == t_sel_admin]
                if not t_data_admin.empty:
                    st.plotly_chart(px.line(t_data_admin, x="日付", y="数値", title=f"{t_sel_admin} の推移", markers=True))
            
            with st.expander("🗑️ データの削除"):
                d_type = st.radio("削除するデータ", ["体調", "フィジカル"], horizontal=True)
                if d_type == "体調" and not p_cond.empty:
                    del_date = st.selectbox("日付を選択", p_cond["日付"].unique(), key="del_c_admin")
                    if st.button("体調データを削除"):
                        df_cond = df_cond.drop(df_cond[(df_cond["名前"] == p_name) & (df_cond["日付"] == del_date)].index)
                        df_cond.to_csv(CONDITION_FILE, index=False, encoding="utf-8-sig"); st.rerun()
                elif d_type == "フィジカル" and not p_phys.empty:
                    del_p_idx = st.selectbox("記録を選択", p_phys.index, format_func=lambda x: f"{p_phys.loc[x, '日付']} - {p_phys.loc[x, 'テスト種目']}: {p_phys.loc[x, '数値']}", key="del_p_admin")
                    if st.button("フィジカルデータを削除"):
                        df_phys = df_phys.drop(del_p_idx)
                        df_phys.to_csv(PHYSICAL_FILE, index=False, encoding="utf-8-sig"); st.rerun()
        else: st.info("選手を選択してください")

    with t3:
        today_data = df_cond[df_cond["日付"] == date.today()]
        alert_p = today_data[(today_data["疲労度"] >= 4) | (today_data["怪我痛み"] == "はい")]
        st.metric("要注意選手", f"{len(alert_p)} 名")
        for _, r in alert_p.iterrows():
            st.error(f"● {r['名前']} - 疲労:{r['疲労度']} / 痛み:{r['怪我痛み']} ({r['痛み詳細']})")
        if not df_cond.empty:
            team_avg = df_cond.groupby("日付")[["疲労度", "睡眠の質"]].mean().reset_index()
            st.plotly_chart(px.line(team_avg, x="日付", y=["疲労度", "睡眠の質"], title="チーム平均推移", markers=True, range_y=[0, 6], color_discrete_map=COLOR_MAP))

    with t4:
        st.subheader("🏆 フィジカルランキング & 成長分析")
        l_cols = st.columns(len(PHYS_TESTS))
        for i, test in enumerate(PHYS_TESTS):
            with l_cols[i]:
                st.markdown(f"#### {test}")
                test_data = df_phys[df_phys["テスト種目"] == test]
                if not test_data.empty:
                    ascending = True if "秒" in test else False
                    ranking = test_data.sort_values("数値", ascending=ascending).drop_duplicates("名前").head(5)
                    for rank, (_, r) in enumerate(ranking.iterrows(), 1):
                        p_hist = test_data[test_data["名前"] == r['名前']].sort_values("日付")
                        growth = ""
                        if len(p_hist) >= 2:
                            diff = p_hist.iloc[-1]["数値"] - p_hist.iloc[-2]["数値"]
                            is_growth = diff < 0 if ascending else diff > 0
                            growth = f" <span style='color:{'green' if is_growth else 'red'}; font-size:0.8rem;'>({'+' if diff>0 else ''}{diff:.2f})</span>"
                        st.markdown(f'<div class="leaderboard-card"><b>{rank}位: {r["名前"]}</b><br><span style="font-size: 1.2rem; color: #01579b;">{r["数値"]}</span>{growth}</div>', unsafe_allow_html=True)

    with t5:
        sub = df_cond[df_cond["日付"] == date.today()]["名前"].tolist()
        not_sub = [p for p in df_players["名前"].tolist() if p not in sub]
        if not not_sub: st.success("全員入力済み！")
        else:
            cols = st.columns(4)
            for i, name in enumerate(not_sub):
                with cols[i%4]: st.warning(f"・ {name}")

else:
    # --- 選手ビュー ---
    my_info = df_players[df_players["名前"] == st.session_state.user_name].iloc[0]
    img_tag = "https://via.placeholder.com/150"
    b64_img = get_base64_image(str(my_info['画像パス']))
    if b64_img: img_tag = f"data:image/jpeg;base64,{b64_img}"

    # 【修正】プロフィール表示に身長を追加、ベスト体重を体重に変更
    st.markdown(f"""
    <div class="profile-container">
        <div class="profile-photo"><img src="{img_tag}" /></div>
        <div class="profile-details">
            <h2>{my_info['名前']} <span style='font-size: 1.2rem; color: #666;'>#{my_info['背番号']}</span></h2>
            <b>ポジション:</b> {my_info['ポジション']} | <b>学年:</b> {my_info['学年']}<br>
            <b>身長:</b> {my_info['身長']}cm | <b>体重:</b> {my_info['体重']}kg
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tp1, tp2, tp3 = st.tabs(["📝 今日の体調入力", "📈 自分の履歴", "🏆 ランキング"])
    
    with tp1:
        with st.container(border=True):
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                # 【修正】デフォルト値を最新の登録体重から取得
                p_we = st.number_input("本日の体重 (kg)", value=float(my_info['体重']), step=0.1)
                p_pn = st.radio("怪我・痛み", ["いいえ", "はい"], horizontal=True, key="p_pn_user")
                p_dt = st.text_input("痛みの詳細") if p_pn == "はい" else ""
            with p_col2:
                p_fa = st.slider("疲労度 (1-5)", 1, 5, 3); p_sl = st.slider("睡眠 (1-5)", 1, 5, 3)
            if st.button("データを送信する", width="stretch", type="primary"):
                new_c = {"日付": str(date.today()), "名前": st.session_state.user_name, "体重": p_we, "疲労度": p_fa, "睡眠の質": p_sl, "怪我痛み": p_pn, "痛み詳細": p_dt}
                df_cond = pd.concat([df_cond, pd.DataFrame([new_c])], ignore_index=True); df_cond.to_csv(CONDITION_FILE, index=False, encoding="utf-8-sig"); st.success("送信完了！"); st.rerun()

    with tp2:
        # 【修正】グラフを上下に分割配置
        my_c = df_cond[df_cond["名前"] == st.session_state.user_name].sort_values("日付")
        if not my_c.empty:
            st.plotly_chart(px.line(my_c, x="日付", y=["疲労度", "睡眠の質"], title="体調推移グラフ", markers=True, range_y=[0, 6], color_discrete_map=COLOR_MAP), use_container_width=True)
        
        my_p = df_phys[df_phys["名前"] == st.session_state.user_name].sort_values("日付")
        if not my_p.empty:
            st.markdown("---")
            t_sel_user = st.selectbox("フィジカル種目を選択", PHYS_TESTS, key="user_p_sel")
            t_data_user = my_p[my_p["テスト種目"] == t_sel_user]
            if not t_data_user.empty:
                st.plotly_chart(px.line(t_data_user, x="日付", y="数値", title=f"{t_sel_user} の成長グラフ", markers=True), use_container_width=True)

        with st.expander("⚙️ 履歴の削除"):
            d_cat_user = st.radio("削除するデータ", ["体調", "フィジカル"], horizontal=True, key="d_cat_user")
            if d_cat_user == "体調" and not my_c.empty:
                d_day_user = st.selectbox("削除する日", my_c["日付"].unique(), key="del_c_user")
                if st.button("体調データを削除"):
                    df_cond = df_cond.drop(df_cond[(df_cond["名前"] == st.session_state.user_name) & (df_cond["日付"] == d_day_user)].index)
                    df_cond.to_csv(CONDITION_FILE, index=False, encoding="utf-8-sig"); st.rerun()
            elif d_cat_user == "フィジカル" and not my_p.empty:
                d_idx_user = st.selectbox("削除する記録", my_p.index, format_func=lambda x: f"{my_p.loc[x, '日付']} - {my_p.loc[x, 'テスト種目']}: {my_p.loc[x, '数値']}", key="del_p_user")
                if st.button("テスト記録を削除"):
                    df_phys = df_phys.drop(d_idx_user)
                    df_phys.to_csv(PHYSICAL_FILE, index=False, encoding="utf-8-sig"); st.rerun()

    with tp3:
        st.subheader("🏆 チーム内ランキング")
        l_cols = st.columns(len(PHYS_TESTS))
        for i, test in enumerate(PHYS_TESTS):
            with l_cols[i]:
                st.markdown(f"**{test}**")
                t_d = df_phys[df_phys["テスト種目"] == test]
                if not t_d.empty:
                    asc = True if "秒" in test else False
                    top = t_d.sort_values("数値", ascending=asc).iloc[0]
                    st.metric("1位", top["名前"], f"{top['数値']}")
                    my_h = t_d[t_d["名前"] == st.session_state.user_name].sort_values("日付")
                    if not my_h.empty:
                        curr = my_h.iloc[-1]["数値"]
                        if len(my_h) >= 2:
                            diff = curr - my_h.iloc[-2]["数値"]
                            is_imp = diff < 0 if asc else diff > 0
                            st.metric("自己最新", f"{curr}", delta=f"{diff:.2f}", delta_color="normal" if is_imp else "inverse")
                        else: st.write(f"自己最新: {curr}")