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
    """パスワードをSHA-256でハッシュ化して保護"""
    return hashlib.sha256(str(password).encode()).hexdigest()

# --- 1. ページ設定 ---
st.set_page_config(page_title="選手コンディション管理", page_icon="⚽", layout="wide")

def get_base64_image(image_path):
    if os.path.exists(str(image_path)):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

# カスタムCSS
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
    .bmi-box {
        margin-bottom: 20px; padding: 20px; background: #e3f2fd; border-radius: 12px; 
        border: 2px solid #01579b; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データロード ---
MASTER_FILE, CONDITION_FILE, PHYSICAL_FILE = "player_master.csv", "daily_condition.csv", "physical_tests.csv"
IMAGE_DIR = "player_images"
if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

if os.path.exists(MASTER_FILE):
    df_players = pd.read_csv(MASTER_FILE)
    if not df_players.empty and len(str(df_players.iloc[0]["パスワード"])) != 64:
        df_players["パスワード"] = df_players["パスワード"].apply(hash_password)
        df_players.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
else: df_players = pd.DataFrame(columns=["背番号", "名前", "ポジション", "学年", "身長", "体重", "画像パス", "パスワード"])

df_cond = pd.read_csv(CONDITION_FILE) if os.path.exists(CONDITION_FILE) else pd.DataFrame(columns=["日付", "名前", "体重", "疲労度", "睡眠の質", "怪我痛み", "痛み詳細"])
if not df_cond.empty: df_cond["日付"] = pd.to_datetime(df_cond["日付"]).dt.date

df_phys = pd.read_csv(PHYSICAL_FILE) if os.path.exists(PHYSICAL_FILE) else pd.DataFrame(columns=["日付", "名前", "テスト種目", "数値"])
if not df_phys.empty: df_phys["日付"] = pd.to_datetime(df_phys["日付"]).dt.date

COLOR_MAP = {"睡眠の質": "#1f77b4", "疲労度": "#d62728"} #
PHYS_TESTS = ["30mスプリント (秒)", "プロアジリティ (秒)", "垂直跳び (cm)", "Yo-Yoテスト (m)"]

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_role" not in st.session_state: st.session_state.user_role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "show_form" not in st.session_state: st.session_state.show_form = None
if "selected_player_name" not in st.session_state: st.session_state.selected_player_name = None

# --- 3. ログイン ---
if not st.session_state.authenticated:
    st.markdown('<div class="full-width-header"><h1>⚽ LOGIN</h1></div>', unsafe_allow_html=True)
    with st.container(border=True):
        u_id = st.text_input("名前（admin または 選手名）")
        u_pw = st.text_input("パスワード", type="password")
        if st.button("ログイン", width="stretch"):
            if u_id == "admin" and u_pw == st.secrets.get("admin_password", "admin123"):
                st.session_state.authenticated, st.session_state.user_role, st.session_state.user_name = True, "admin", "管理者"; st.rerun()
            h_pw = hash_password(u_pw)
            pm = df_players[(df_players["名前"] == u_id) & (df_players["パスワード"].astype(str) == h_pw)]
            if not pm.empty:
                st.session_state.authenticated, st.session_state.user_role, st.session_state.user_name = True, "player", u_id; st.rerun()
            else: st.error("ログイン情報が正しくありません")
    st.stop()

# --- 4. 共通ヘッダー ---
st.markdown(f'<div class="full-width-header"><h1>⚽ {st.session_state.user_name} モード</h1></div>', unsafe_allow_html=True)

# --- 5. サイドバー (管理者機能) ---
with st.sidebar:
    st.write(f"👤: **{st.session_state.user_name}**")
    if st.button("ログアウト", key="lo_btn"): st.session_state.authenticated = False; st.rerun()
    st.divider()
    if st.session_state.user_role == "admin" and not df_players.empty:
        st.header("🛠️ 選手・テスト管理")
        plist = df_players["名前"].tolist()
        s_idx = plist.index(st.session_state.selected_player_name) if st.session_state.selected_player_name in plist else 0
        edit_target = st.selectbox("選手を選択", plist, index=s_idx)
        st.session_state.selected_player_name = edit_target
        row = df_players[df_players["名前"] == edit_target].iloc[0]
        
        with st.expander("📝 プロフィール修正(5項目)"):
            with st.form("edit_p"):
                e_na = st.text_input("名前", row["名前"])
                e_no = st.number_input("背番号", value=int(row["背番号"]))
                e_hi = st.number_input("身長 (cm)", value=float(row["身長"]))
                e_we = st.number_input("体重 (kg)", value=float(row["体重"]))
                e_pw = st.text_input("新パスワード(変更時のみ)")
                if st.form_submit_button("選手情報を更新"):
                    idx = df_players[df_players["名前"] == edit_target].index[0]
                    final_pw = hash_password(e_pw) if e_pw else row["パスワード"]
                    df_players.loc[idx, ["名前","背番号","身長","体重","パスワード"]] = [e_na, e_no, e_hi, e_we, final_pw]
                    df_players.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig"); st.rerun()
        
        with st.expander("🏆 フィジカルテスト記録"):
            with st.form("add_ph"):
                t_t, t_v, t_d = st.selectbox("種目", PHYS_TESTS), st.number_input("計測数値", step=0.01), st.date_input("測定日")
                if st.form_submit_button("記録を保存"):
                    new_ph = pd.DataFrame([{"日付": t_d, "名前": edit_target, "テスト種目": t_t, "数値": t_v}])
                    df_phys = pd.concat([df_phys, new_ph], ignore_index=True); df_phys.to_csv(PHYSICAL_FILE, index=False); st.success("保存完了"); st.rerun()

# --- 6. メインコンテンツ ---
if st.session_state.user_role == "admin":
    # 管理者ビュー
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ 新規選手登録", width="stretch"): st.session_state.show_form = "p"; st.rerun()
    with col2:
        if st.button("📝 体調代行入力", width="stretch"): st.session_state.show_form = "c"; st.rerun()
    
    if st.session_state.show_form == "p":
        with st.form("new_p"):
            n_na, n_no, n_pw = st.text_input("名前"), st.number_input("番号", 1, 99), st.text_input("PW", "1234")
            n_po, n_hi, n_we = st.selectbox("Pos", ["GK","DF","MF","FW"]), st.number_input("身長", 170.0), st.number_input("体重", 60.0)
            n_up = st.file_uploader("写真を選択")
            if st.form_submit_button("登録"):
                path = os.path.join(IMAGE_DIR, f"{n_no}_{n_na}.jpg") if n_up else ""
                if n_up: Image.open(n_up).convert("RGB").resize((300, 300)).save(path)
                new_entry = pd.DataFrame([{"背番号":n_no,"名前":n_na,"ポジション":n_po,"学年":"高3","身長":n_hi,"体重":n_we,"画像パス":path,"パスワード":hash_password(n_pw)}])
                df_players = pd.concat([df_players, new_entry], ignore_index=True); df_players.to_csv(MASTER_FILE, index=False); st.session_state.show_form=None; st.rerun()

    st.markdown("---")
    t1, t2, t3, t4, t5 = st.tabs(["📋 選手名簿", "📈 個別推移管理", "📊 チーム状況", "🏆 フィジカルテストボード", "✅ 未入力者"])
    
    with t1:
        cls = st.columns(4)
        for i, (idx, row) in enumerate(df_players.iterrows()):
            with cls[i%4]:
                with st.container(border=True):
                    if pd.notnull(row['画像パス']) and os.path.exists(str(row['画像パス'])): st.image(str(row['画像パス']), use_container_width=True)
                    st.markdown(f"### #{row['背番号']} {row['名前']}")
                    if st.button(f"詳細：{row['名前']}", key=f"v_{idx}", width="stretch"): st.session_state.selected_player_name = row['名前']; st.rerun()
    
    with t2:
        if st.session_state.selected_player_name:
            p_n = st.session_state.selected_player_name
            p_c = df_cond[df_cond["名前"] == p_n].sort_values("日付")
            st.write(f"### {p_n} 選手の分析データ")
            if not p_c.empty: st.plotly_chart(px.line(p_c, x="日付", y=["疲労度", "睡眠の質"], title="体調推移", markers=True, range_y=[0,6], color_discrete_map=COLOR_MAP))
            p_ph = df_phys[df_phys["名前"] == p_n].sort_values("日付")
            if not p_ph.empty:
                t_s = st.selectbox("種目", PHYS_TESTS)
                st.plotly_chart(px.line(p_ph[p_ph["テスト種目"]==t_s], x="日付", y="数値", title=f"{t_s}推移", markers=True))
            with st.expander("🗑️ 入力データの削除"):
                cat = st.radio("削除するデータ種類", ["体調","テスト"], horizontal=True)
                if cat=="体調" and not p_c.empty:
                    d_d = st.selectbox("日付を選択", p_c["日付"].unique(), key="dc_admin")
                    if st.button("体調データを削除"): df_cond = df_cond.drop(df_cond[(df_cond["名前"]==p_n)&(df_cond["日付"]==d_d)].index); df_cond.to_csv(CONDITION_FILE, index=False); st.rerun()
                elif cat=="テスト" and not p_ph.empty:
                    d_i = st.selectbox("記録を選択", p_ph.index, format_func=lambda x: f"{p_ph.loc[x,'日付']} {p_ph.loc[x,'テスト種目']}: {p_ph.loc[x,'数値']}", key="dp_admin")
                    if st.button("フィジカル記録を削除"): df_phys = df_phys.drop(d_i); df_phys.to_csv(PHYSICAL_FILE, index=False); st.rerun()
        else: st.info("選手名簿から選手を選択してください")
    
    with t3:
        today_c = df_cond[df_cond["日付"]==date.today()]
        alert = today_c[(today_c["疲労度"]>=4)|(today_c["怪我痛み"]=="はい")]
        st.metric("要注意選手", f"{len(alert)}名")
        for _, r in alert.iterrows(): st.error(f"● {r['名前']} - 疲労:{r['疲労度']} / 痛み:{r['怪我痛み']} ({r['痛み詳細']})")
        if not df_cond.empty:
            team_avg = df_cond.groupby("日付")[["疲労度", "睡眠の質"]].mean().reset_index()
            st.plotly_chart(px.line(team_avg, x="日付", y=["疲労度", "睡眠の質"], title="チーム平均推移", markers=True, range_y=[0, 6], color_discrete_map=COLOR_MAP))
    
    with t4:
        st.subheader("🏆 フィジカルランキング & 成長分析")
        lcls = st.columns(4)
        for i, test in enumerate(PHYS_TESTS):
            with lcls[i]:
                st.markdown(f"#### {test}")
                td = df_phys[df_phys["テスト種目"]==test]
                if not td.empty:
                    asc = True if "秒" in test else False
                    rank = td.sort_values("数値", ascending=asc).drop_duplicates("名前").head(5)
                    for rk, (_, r) in enumerate(rank.iterrows(), 1):
                        hist = td[td["名前"]==r['名前']].sort_values("日付")
                        gt = ""
                        if len(hist)>=2:
                            diff = hist.iloc[-1]["数値"] - hist.iloc[-2]["数値"]
                            clr = "green" if (diff<0 if asc else diff>0) else "red"
                            gt = f" <span style='color:{clr}; font-size:0.8rem;'>({'+' if diff>0 else ''}{diff:.2f})</span>"
                        st.markdown(f'<div class="leaderboard-card"><b>{rk}位: {r["名前"]}</b><br><span style="font-size:1.2rem; color:#01579b;">{r["数値"]}</span>{gt}</div>', unsafe_allow_html=True)
                else: st.info("データなし")
    
    with t5:
        sub = df_cond[df_cond["日付"]==date.today()]["名前"].tolist()
        not_s = [p for p in df_players["名前"].tolist() if p not in sub]
        if not not_s: st.success("全員入力が完了しています！")
        else:
            cs = st.columns(4)
            for i, n in enumerate(not_s):
                with cs[i%4]: st.warning(f"・ {n}")

else:
    # 選手ビュー
    my_info = df_players[df_players["名前"] == st.session_state.user_name].iloc[0]
    img_tag = "https://via.placeholder.com/150"
    b64 = get_base64_image(str(my_info['画像パス']))
    if b64: img_tag = f"data:image/jpeg;base64,{b64}"

    # プロフィール表示 (BMIはここから移動)
    st.markdown(f"""
    <div class="profile-container">
        <div class="profile-photo"><img src="{img_tag}" /></div>
        <div class="profile-details">
            <h2>{my_info['名前']} <span style='font-size: 1.2rem; color: #666;'>#{my_info['背番号']}</span></h2>
            <b>ポジション:</b> {my_info['ポジション']} | <b>学年:</b> {my_info['学年']}<br>
            <b>身長:</b> {my_info['身長']}cm | <b>登録体重:</b> {my_info['体重']}kg
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tp1, tp2, tp3 = st.tabs(["📝 今日の体調入力", "📈 自分の履歴", "🏆 ランキング"])
    
    with tp1:
        latest_c = df_cond[df_cond["名前"] == st.session_state.user_name].sort_values("日付", ascending=False)
        cur_w = latest_c.iloc[0]["体重"] if not latest_c.empty else my_info['体重']
        with st.container(border=True):
            p_c1, p_c2 = st.columns(2)
            with p_c1:
                p_we = st.number_input("本日の体重 (kg)", value=float(cur_w), step=0.1)
                p_pn = st.radio("怪我・痛み", ["いいえ", "はい"], horizontal=True, key="p_pn_u")
                p_dt = st.text_input("詳細") if p_pn == "はい" else ""
            with p_c2:
                p_fa, p_sl = st.slider("疲労度", 1, 5, 3, key="s_fa"), st.slider("睡眠", 1, 5, 3, key="s_sl")
            if st.button("データを送信する", width="stretch", type="primary"):
                n_c = pd.DataFrame([{"日付": date.today(), "名前": st.session_state.user_name, "体重": p_we, "疲労度": p_fa, "睡眠の質": p_sl, "怪我痛み": p_pn, "痛み詳細": p_dt}])
                df_cond = pd.concat([df_cond, n_c], ignore_index=True); df_cond.to_csv(CONDITION_FILE, index=False, encoding="utf-8-sig"); st.success("送信完了"); st.rerun()
    
    with tp2:
        # 【修正】BMIと目標体重を「自分の履歴」タブへ移動
        mc = df_cond[df_cond["名前"]==st.session_state.user_name].sort_values("日付")
        if not mc.empty:
            # 最新の入力体重でBMIを計算
            h_m = my_info['身長'] / 100
            latest_weight = mc.iloc[-1]["体重"]
            bmi = latest_weight / (h_m ** 2)
            t_min, t_max = 21.0, 23.0 # U-18目標範囲
            w_min, w_max = t_min * (h_m ** 2), t_max * (h_m ** 2)
            
            status, s_clr, t_msg = "", "", ""
            if bmi < t_min: status, s_clr, t_msg = "エネルギー不足注意 (低め)", "orange", f"目標: **あと +{w_min - latest_weight:.1f} kg** でBMI 21.0"
            elif bmi > t_max: status, s_clr, t_msg = "キレ・重さに注意 (高め)", "#FF4B4B", f"目標: **あと -{latest_weight - w_max:.1f} kg** でBMI 23.0"
            else: status, s_clr, t_msg = "アスリート適正範囲", "#28a745", "目標: **現在の体重を維持しましょう**"

            st.markdown(f"""
            <div class="bmi-box">
                <h4 style="margin-top:0; color:#01579b;">📊 最新のBMI判定 (本日: {latest_weight}kg)</h4>
                <span style="font-size:1.8rem; font-weight:bold; color:{s_clr};">{bmi:.1f}</span>
                <span style="margin-left:15px; font-size:1.2rem; font-weight:bold; color:{s_clr};">{status}</span><br>
                <p style="margin:10px 0; font-size:1.1rem; color:#333; background:white; padding:10px; border-radius:5px;">{t_msg}</p>
                <span style="font-size:0.85rem; color:#666;">※U-18推奨体重: {w_min:.1f}kg 〜 {w_max:.1f}kg (BMI:{t_min}-{t_max})</span>
            </div>
            """, unsafe_allow_html=True)
            
            # グラフは上下に配置
            st.plotly_chart(px.line(mc, x="日付", y=["疲労度", "睡眠の質"], title="体調コンディション推移", markers=True, range_y=[0,6], color_discrete_map=COLOR_MAP), use_container_width=True)
        
        mp = df_phys[df_phys["名前"]==st.session_state.user_name].sort_values("日付")
        if not mp.empty:
            st.markdown("---")
            us_t = st.selectbox("フィジカル種目を選択", PHYS_TESTS, key="us_t")
            st.plotly_chart(px.line(mp[mp["テスト種目"]==us_t], x="日付", y="数値", title=f"{us_t}成長推移", markers=True), use_container_width=True)
        
        with st.expander("⚙️ 履歴の削除"):
            ut = st.radio("削除対象を選択", ["体調","テスト"], horizontal=True, key="ut_u")
            if ut=="体調" and not mc.empty:
                ud = st.selectbox("日付を選択", mc["日付"].unique(), key="ud_u")
                if st.button("体調データを削除"): df_cond = df_cond.drop(df_cond[(df_cond["名前"]==st.session_state.user_name)&(df_cond["日付"]==ud)].index); df_cond.to_csv(CONDITION_FILE, index=False); st.rerun()
            elif ut=="テスト" and not mp.empty:
                ui = st.selectbox("テスト記録を選択", mp.index, format_func=lambda x: f"{mp.loc[x,'日付']} {mp.loc[x,'テスト種目']}: {mp.loc[x,'数値']}", key="ui_u")
                if st.button("フィジカル記録を削除"): df_phys = df_phys.drop(ui); df_phys.to_csv(PHYSICAL_FILE, index=False); st.rerun()
    
    with tp3:
        st.subheader("🏆 チームランキング")
        lcls = st.columns(4)
        for i, test in enumerate(PHYS_TESTS):
            with lcls[i]:
                st.markdown(f"**{test}**")
                td = df_phys[df_phys["テスト種目"]==test]
                if not td.empty:
                    asc = True if "秒" in test else False
                    top = td.sort_values("数値", ascending=asc).iloc[0]
                    st.metric("1位", top["名前"], f"{top['数値']}")
                    my_h = td[td["名前"]==st.session_state.user_name].sort_values("日付")
                    if not my_h.empty:
                        cur = my_h.iloc[-1]["数値"]
                        if len(my_h)>=2:
                            diff = cur - my_h.iloc[-2]["数値"]
                            st.metric("あなた", f"{cur}", delta=f"{diff:.2f}", delta_color="normal" if (diff<0 if asc else diff>0) else "inverse")
                        else: st.write(f"最新: {cur}")