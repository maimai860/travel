import streamlit as st
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
from datetime import date, timedelta
import urllib.parse
import re
import json

from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser



# =========================
# 認証設定
# =========================

config = {
    'credentials': {
        'usernames': {
            'admin': {
                'name': 'Admin',
                # ↓ ここに生成したハッシュを貼る
                'password': '$2b$12$lJ3URr1sBkUj1Q8/KZnpSutxkzfcyIUknCnb8mrjOQ47lofiqCG7q'
            }
        }
    },
    'cookie': {
        'expiry_days': 1,
        'key': 'some_signature_key',
        'name': 'some_cookie_name'
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login(location="main")

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")


# =========================
# ログイン成功時のみアプリ表示
# =========================

if authentication_status:

    authenticator.logout(location="sidebar")
    st.sidebar.write(f"ようこそ {name}")

    st.title("🌤️ 天気 × AI 旅行プラン検索アプリ")

    # =========================
    # ルート入力
    # =========================
    st.header("🧭 移動ルート")

    if "legs" not in st.session_state:
        st.session_state.legs = [{"from": "東京", "to": "大阪"}]

    for i, leg in enumerate(st.session_state.legs):
        col1, col2 = st.columns(2)
        leg["from"] = col1.text_input(f"出発地{i+1}", value=leg["from"], key=f"from_{i}")
        leg["to"] = col2.text_input(f"到着地{i+1}", value=leg["to"], key=f"to_{i}")

    # =========================
    # 日程
    # =========================
    st.header("📅 日程")

    start_date = st.date_input("開始日", value=date.today())
    end_date = st.date_input("終了日")

    # =========================
    # 条件
    # =========================
    st.header("👤 条件")

    age = st.slider("年齢", 0, 100, 30)
    budget_jpy = st.number_input("総予算（円）", min_value=0, step=1000)

    budget_type = st.radio(
        "予算タイプ",
        ["ポジティブ（余裕あり）", "ネガティブ（節約重視）", "全体"]
    )

    weather = st.radio("天気", ["晴れ", "雨"])

    transport = st.multiselect(
        "利用交通手段",
        ["飛行機", "新幹線", "バス", "車"]
    )

    # =========================
    # 所要時間辞書
    # =========================
    travel_time_table = {
        ("東京", "大阪", "新幹線"): "約2時間30分",
        ("東京", "大阪", "飛行機"): "約1時間（＋空港移動約1時間）",
        ("東京", "大阪", "車"): "約6時間",
        ("東京", "大阪", "バス"): "約8時間",
    }

    def get_travel_time(start, end, methods):
        for m in methods:
            key = (start, end, m)
            if key in travel_time_table:
                return f"{m} {travel_time_table[key]}"
        if methods:
            return f"{methods[0]} 約3〜5時間"
        return "移動 約3時間"

    # =========================
    # 検索
    # =========================
    if st.button("🔍 検索"):

        route = []
        for leg in st.session_state.legs:
            if leg["from"]:
                route.append(leg["from"])
            if leg["to"]:
                route.append(leg["to"])
        route = list(dict.fromkeys(route))

        if len(route) < 2:
            st.error("出発地と到着地を入力してください")
            st.stop()

        start_city = route[0]
        end_city = route[-1]

        total_days = (end_date - start_date).days + 1

        if total_days <= 0:
            st.error("日程が不正です")
            st.stop()

        daily_budget = int(budget_jpy / total_days)

        travel_info = get_travel_time(start_city, end_city, transport)

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

【Day1最初に必ず書く】
移動：{start_city} → {end_city}（{travel_info}）

総予算: {budget_jpy}円
1日予算: {daily_budget}円
予算タイプ: {budget_type}
天気: {weather}

最後に必ず以下形式で出力：
ALL_SPOTS:
["観光地1","観光地2",...]

開始日: {start_date}
"""

        prompt = PromptTemplate(
            input_variables=[
                "total_days","end_city","start_city","travel_info",
                "budget_jpy","daily_budget","budget_type",
                "weather","start_date"
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
            "budget_type": budget_type,
            "weather": weather,
            "start_date": start_date
        }):
            full_text += chunk
            placeholder.markdown(full_text)

        # 観光地抽出
        match = re.search(r"ALL_SPOTS:\s*(\[[^\]]+\])", full_text)

        if match:
            try:
                spots = json.loads(match.group(1))
                route_url = "/".join([urllib.parse.quote(p) for p in spots])
                map_url = f"https://www.google.com/maps/dir/{route_url}"
                st.subheader("📍 Google Maps")
                st.link_button("Google Mapで開く", map_url)
            except:
                st.warning("地図生成に失敗しました")


elif authentication_status is False:
    st.error("ユーザー名またはパスワードが間違っています")

elif authentication_status is None:
    st.warning("ユーザー名とパスワードを入力してください")
