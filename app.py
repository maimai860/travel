import streamlit as st
from streamlit_authenticator import Authenticate, Hasher
from datetime import date
import urllib.parse
import re
import json
import requests

from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# =========================
# ユーザー情報読み込み（旧形式）
# =========================
def load_users():
    try:
        with open("users.json", "r") as f:
            data = json.load(f)
        # 新形式にしてしまっていた場合を旧形式に戻す
        if "credentials" in data and "usernames" in data["credentials"]:
            data = {
                "usernames": data["credentials"]["usernames"]
            }
    except FileNotFoundError:
        data = {
            "usernames": {
                "admin": {
                    "name": "Admin",
                    # 既存のハッシュパスワード（bcrypt）
                    "password": "$2b$12$lJ3URr1sBkUj1Q8/KZnpSutxkzfcyIUknCnb8mrjOQ47lofiqCG7q"
                }
            }
        }
    return data

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users_data = load_users()

# =========================
# 新規ユーザー登録フォーム（0.1.x 仕様）
# =========================
with st.expander("新規ユーザー登録"):
    new_username = st.text_input("ユーザー名")
    new_name = st.text_input("表示名")
    new_password = st.text_input("パスワード", type="password")

    if st.button("登録"):
        usernames = users_data["usernames"]
        if not new_username or not new_password:
            st.error("ユーザー名とパスワードを入力してください")
        elif new_username in usernames:
            st.warning("ユーザー名は既に存在します")
        else:
            # ★ このバージョンで唯一動くハッシュ関数
            hashed_pw = Hasher.generate_password_hash(new_password)

            usernames[new_username] = {
                "name": new_name,
                "password": hashed_pw
            }

            save_users(users_data)
            st.success(f"{new_username} を登録しました。ログインしてください。")

# =========================
# 認証設定（0.1.x 仕様）
# =========================
authenticator = Authenticate(
    users_data,                 # credentials ではなく users_data そのもの
    "some_cookie_name",         # cookie_name
    "some_signature_key",       # key
    cookie_expiry_days=1
)

authenticator.login(location="main")

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

# =========================
# 距離取得関数
# =========================
def get_distance_and_time(origin, destination):
    try:
        geo_url = "https://nominatim.openstreetmap.org/search"
        params_origin = {"q": origin, "format": "json"}
        params_dest = {"q": destination, "format": "json"}

        origin_res = requests.get(geo_url, params=params_origin, headers={"User-Agent": "travel-app"}).json()
        dest_res = requests.get(geo_url, params=params_dest, headers={"User-Agent": "travel-app"}).json()

        if not origin_res or not dest_res:
            return None, None

        lat1 = origin_res[0]["lat"]
        lon1 = origin_res[0]["lon"]
        lat2 = dest_res[0]["lat"]
        lon2 = dest_res[0]["lon"]

        route_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        route_res = requests.get(route_url).json()

        if route_res["code"] != "Ok":
            return None, None

        distance_km = route_res["routes"][0]["distance"] / 1000
        duration_min = route_res["routes"][0]["duration"] / 60
        return distance_km, duration_min
    except:
        return None, None

# =========================
# 交通費計算関数
# =========================
def estimate_cost(method, distance_km):
    if method == "飛行機":
        if distance_km < 300: return 15000
        elif distance_km < 800: return 25000
        else: return 40000
    if method == "新幹線":
        if distance_km < 200: return 8000
        elif distance_km < 500: return 15000
        else: return 25000
    if method == "バス":
        return int(distance_km * 10)
    if method == "車":
        return int(distance_km * 18)
    return 10000

# =========================
# ログイン成功時の画面
# =========================
if authentication_status:

    authenticator.logout(location="sidebar")
    st.sidebar.write(f"ようこそ {name}")

    st.title("🌤️ 天気 × AI 旅行プラン検索アプリ")

    # ===== 移動ルート =====
    st.header("🧭 移動ルート")
    if "legs" not in st.session_state:
        st.session_state.legs = [{"from": "東京", "to": "大阪"}]

    for i, leg in enumerate(st.session_state.legs):
        col1, col2 = st.columns(2)
        leg["from"] = col1.text_input(f"出発地{i+1}", value=leg["from"], key=f"from_{i}")
        leg["to"] = col2.text_input(f"到着地{i+1}", value=leg["to"], key=f"to_{i}")

    # ===== 日程 =====
    st.header("📅 日程")
    start_date = st.date_input("開始日", value=date.today())
    end_date = st.date_input("終了日")

    # ===== 条件 =====
    st.header("👤 条件")
    age = st.slider("年齢", 0, 100, 30)
    budget_jpy = st.number_input("総予算（円）", min_value=0, step=1000)
    min_daily_budget = st.number_input("希望する1日あたり最低使用額（円）", min_value=0, step=1000, value=10000)
    weather = st.radio("天気", ["晴れ", "雨"])
    transport = st.radio("利用交通手段", ["飛行機", "新幹線", "バス", "車"])

    # 入力チェック
    if not start_date or not end_date:
        st.error("日程を入力してください")
        st.stop()
    if budget_jpy <= 0:
        st.error("予算を入力してください")
        st.stop()
    if not transport:
        st.error("利用交通手段を選択してください")
        st.stop()
    if not weather:
        st.error("天気を選択してください")
        st.stop()

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        st.error("日程が不正です")
        st.stop()
    if total_days >= 30:
        st.error("30日以上の旅行プランは生成できません")
        st.stop()

    # 検索ボタン
    if st.button("🔍 検索"):

        # 出発・到着地の整理
        route = []
        for leg in st.session_state.legs:
            if leg["from"]: route.append(leg["from"])
            if leg["to"]: route.append(leg["to"])
        route = list(dict.fromkeys(route))
        if len(route) < 2:
            st.error("出発地と到着地を入力してください")
            st.stop()
        start_city = route[0]
        end_city = route[-1]

        # 距離計算
        distance_km, _ = get_distance_and_time(start_city, end_city)
        if distance_km is None:
            st.error("距離取得に失敗しました")
            st.stop()

        # 交通費計算
        one_way_cost = estimate_cost(transport, distance_km)
        travel_cost = one_way_cost * 2
        travel_info = f"{transport} 往復 約{travel_cost}円"

        # 予算計算
        remaining_budget = budget_jpy - travel_cost
        if remaining_budget <= 0:
            st.error("交通費で予算を超えています")
            st.stop()
        daily_budget = remaining_budget / total_days
        if daily_budget < min_daily_budget:
            st.error("入力された1日最低予算を満たせません")
            st.stop()

        # ===== AI旅行プラン生成 =====
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            streaming=True,
            openai_api_key=st.secrets["OPENAI_API_KEY"]
        )

        template = """
あなたはプロ旅行プランナーです。

【絶対ルール】
- 全{total_days}日分を一度に生成する
- Day1のみ移動を書く
- Day2以降は{end_city}滞在前提
- 観光地は絶対に重複させない
- 実在する観光地のみ
- 朝・昼・夜のみ
- 各行は「時間帯：場所 - 一言コメント」
- 徒歩10〜15分圏内は必ず同日にまとめる
- 同一エリアは別日に分けない
- 地理的に非効率な分割は禁止
- 1日予算を超えるプランは絶対に作らない
- 予算不足の場合は「予算不足のため生成不可」と出力する
- 観光地は必ず {end_city} 市内に存在するもののみ
- {end_city} 以外の都道府県の観光地は絶対に出さない
- 住所が {end_city} に属するものだけ使用する

【Day1最初に必ず書く】
移動：{start_city} → {end_city}（{travel_info}）

総予算: {budget_jpy}円
交通費: {travel_cost}円
観光に使える残額: {remaining_budget}円
1日あたり利用可能額: {daily_budget}円
※この金額を絶対に超えないこと
ユーザー指定1日最低予算: {min_daily_budget}円
天気: {weather}

【最終日に必ず書く】
移動：{end_city} → {start_city}

最後に必ず以下形式で出力：
ALL_SPOTS:
["観光地1","観光地2",...]

開始日: {start_date}
"""

        prompt = PromptTemplate(
            input_variables=[
                "total_days","end_city","start_city","travel_info",
                "budget_jpy","daily_budget","min_daily_budget","travel_cost",
                "remaining_budget","weather","start_date"
            ],
            template=template
        )

        chain = prompt | llm | StrOutputParser()
        st.subheader("🧳 旅行プラン")
        full_text = ""
        placeholder = st.empty()

        for chunk in chain.stream({
            "total_days": total_days,
            "end_city": end_city,
            "start_city": start_city,
            "travel_info": travel_info,
            "budget_jpy": budget_jpy,
            "daily_budget": daily_budget,
            "min_daily_budget": min_daily_budget,
            "travel_cost": travel_cost,
            "remaining_budget": remaining_budget,
            "weather": weather,
            "start_date": start_date
        }):
            full_text += chunk
            placeholder.markdown(full_text)

        # 観光地抽出 & Google Mapsリンク
        match = re.search(r"ALL_SPOTS:\s*(\[[^\]]+\])", full_text)
        if match:
            try:
                spots = json.loads(match.group(1))
                route_url = "/".join([urllib.parse.quote(f"{p} {end_city}") for p in spots])
                map_url = f"https://www.google.com/maps/dir/{route_url}"
                st.subheader("📍 Google Maps")
                st.markdown(f"[Google Mapで開く]({map_url})", unsafe_allow_html=True)
            except:
                st.warning("地図生成に失敗しました")

elif authentication_status is False:
    st.error("ユーザー名またはパスワードが間違っています")
elif authentication_status is None:
    st.warning("ユーザー名とパスワードを入力してください")