import streamlit as st
from datetime import date, timedelta
import urllib.parse
import requests
import re
import json

from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


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

    daily_budget = int(budget_jpy / total_days) if total_days > 0 else budget_jpy

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    used_spots = set()
    all_spots = []

    st.subheader("🧳 旅行プラン")

    for i in range(total_days):

        current_date = start_date + timedelta(days=i)

        previous_spots = ", ".join(used_spots) if used_spots else "なし"

        template = """
あなたは旅行プランナーです。

【例】
朝：大阪城 - 天守閣から絶景
昼：黒門市場 - 食べ歩き
夜：通天閣 - 夜景散策

MAP_SPOTS:
["大阪城","黒門市場","通天閣"]

【重要ルール】
- 実在する観光地のみ使用
- 総予算: {budget_jpy}円
- 1日あたり予算: {daily_budget}円
- 予算タイプ: {budget_type}
- 天気: {weather}
- これまで訪れた観光地: {previous_spots}
- 上記は再提案しない
- 朝・昼・夜のみ出力
- 各行は「時間帯：場所 - 一言コメント」
- 最後にMAP_SPOTSをJSONで出力

Day{day_number}
日付: {current_date}
"""

        prompt = PromptTemplate(
            input_variables=[
                "budget_jpy",
                "daily_budget",
                "budget_type",
                "weather",
                "previous_spots",
                "day_number",
                "current_date"
            ],
            template=template
        )

        chain = prompt | llm | StrOutputParser()

        st.markdown(f"### Day{i+1} ({current_date})")

        day_text = ""
        placeholder = st.empty()

        for chunk in chain.stream({
            "budget_jpy": budget_jpy,
            "daily_budget": daily_budget,
            "budget_type": budget_type,
            "weather": weather,
            "previous_spots": previous_spots,
            "day_number": i+1,
            "current_date": current_date
        }):
            day_text += chunk
            placeholder.markdown(day_text)

        # Day1は移動を上に表示（Python制御）
        if i == 0:
            travel_info = get_travel_time(start_city, end_city, transport)
            st.markdown(
                f"**移動：{start_city} → {end_city}（{travel_info}）**"
            )

        match = re.search(r"MAP_SPOTS:\s*(\[[^\]]+\])", day_text)

        if match:
            try:
                spots = json.loads(match.group(1))
                for s in spots:
                    if s not in used_spots:
                        used_spots.add(s)
                        all_spots.append(s)
            except:
                pass

    # =========================
    # Google Map
    # =========================
    st.subheader("📍 Google Maps")

    if all_spots:
        route_url = "/".join([urllib.parse.quote(p) for p in all_spots])
        map_url = f"https://www.google.com/maps/dir/{route_url}"
        st.link_button("Google Mapで開く", map_url)
    else:
        st.info("観光地が抽出できませんでした")
