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

st.header("🧭 移動ルート（区間ごと）")

if "legs" not in st.session_state:
    st.session_state.legs = [{"from": "東京", "to": "大阪"}]

for i, leg in enumerate(st.session_state.legs):
    col1, col2, col3 = st.columns([4, 4, 1])

    with col1:
        leg["from"] = st.text_input(f"出発地 {i+1}", value=leg["from"], key=f"from_{i}")

    with col2:
        leg["to"] = st.text_input(f"到着地 {i+1}", value=leg["to"], key=f"to_{i}")

    with col3:
        if st.button("❌", key=f"del_{i}") and len(st.session_state.legs) > 1:
            st.session_state.legs.pop(i)
            st.rerun()

if st.button("➕ 区間を追加"):
    st.session_state.legs.append({"from": "", "to": ""})
    st.rerun()


st.header("📅 日程")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日", value=date.today())
with col2:
    end_date = st.date_input("終了日")


st.header("👤 個人条件")

age = st.slider("年齢", 0, 100, 30)
budget_jpy = st.number_input("予算（円）", min_value=0, step=1000)

budget_type = st.radio(
    "予算の考え方",
    ["ポジティブ（余裕あり）", "ネガティブ（節約重視）", "全体"]
)


st.header("💱 為替")

currency = st.selectbox("表示通貨", ["USD", "EUR", "KRW", "CNY", "GBP"])


def get_exchange_rate(base="JPY", target="USD"):
    try:
        url = "https://api.frankfurter.app/latest"
        params = {"from": base, "to": target}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data["rates"][target]
    except:
        return None


rate = get_exchange_rate("JPY", currency)

if rate:
    budget_foreign = round(budget_jpy * rate, 2)
    st.info(f"1 JPY = {rate:.4f} {currency} ｜ 約 {budget_foreign} {currency}")
else:
    st.info(f"為替取得失敗 → 円ベース表示（{budget_jpy} 円）")


st.header("🚆 移動手段")

transport = st.multiselect(
    "利用する移動手段",
    ["飛行機", "新幹線", "バス", "車"]
)

st.header("☀️ 天気条件")

weather = st.radio("想定する天気", ["晴れ", "雨"])


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
        st.error("終了日は開始日より後にしてください")
        st.stop()

    if total_days <= 3:
        min_chars = 300
    elif total_days <= 6:
        min_chars = 250
    else:
        min_chars = 150

    st.subheader("🧳 AI 旅行プラン")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    places_set = set()

    for i in range(total_days):

        current_date = start_date + timedelta(days=i)

        if i == 0:
            stay_rule = f"この日だけ{start_city}から{end_city}へ移動する"
        else:
            stay_rule = f"すでに{end_city}に滞在している前提で書く。都市間移動は絶対に書かない"

        template = """
あなたはプロの旅行プランナーです。

【重要ルール】
- {stay_rule}
- 実在する観光地を使う
- 最低{min_chars}文字以上
- 最後に必ず以下形式で観光地だけ出力する

MAP_SPOTS:
["観光地1","観光地2","観光地3"]

Day{day_number}
日付: {current_date}
年齢: {age}
予算方針: {budget_type}
移動手段: {transport}
天気: {weather}
"""

        prompt = PromptTemplate(
            input_variables=[
                "stay_rule", "min_chars",
                "day_number", "current_date",
                "age", "budget_type",
                "transport", "weather"
            ],
            template=template
        )

        chain = prompt | llm | StrOutputParser()

        st.markdown(f"### 🗓 Day {i+1} ({current_date})")

        day_text = ""
        placeholder = st.empty()

        for chunk in chain.stream({
            "stay_rule": stay_rule,
            "min_chars": min_chars,
            "day_number": i+1,
            "current_date": current_date,
            "age": age,
            "budget_type": budget_type,
            "transport": ", ".join(transport),
            "weather": weather
        }):
            day_text += chunk
            placeholder.markdown(day_text)

        # ===== MAP_SPOTS抽出 =====
        match = re.search(r"MAP_SPOTS:\s*(\[[^\]]+\])", day_text)

        if match:
            try:
                spots = json.loads(match.group(1))
                for s in spots:
                    if s != start_city:
                        places_set.add(s)
            except:
                pass

    # =========================
    # Google Map
    # =========================
    st.subheader("📍 Google Maps ルート")

    places = list(places_set)[:8]

    if places:
        map_route = "/".join([urllib.parse.quote(p) for p in places])
        map_url = f"https://www.google.com/maps/dir/{map_route}"
        st.link_button("Google Mapでルートを開く", map_url)
    else:
        st.info("観光地が抽出できませんでした。")
