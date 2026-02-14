import streamlit as st
from datetime import date, timedelta
import urllib.parse
import requests
import re

# LangChain
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


# =========================
# タイトル
# =========================
st.title("🌤️ 天気 × AI 旅行プラン検索アプリ")


# =========================
# 区間入力
# =========================
st.header("🧭 移動ルート（区間ごと）")

if "legs" not in st.session_state:
    st.session_state.legs = [{"from": "東京", "to": "大阪"}]

for i, leg in enumerate(st.session_state.legs):
    col1, col2, col3 = st.columns([4, 4, 1])

    with col1:
        leg["from"] = st.text_input(
            f"出発地 {i+1}",
            value=leg["from"],
            key=f"from_{i}"
        )

    with col2:
        leg["to"] = st.text_input(
            f"到着地 {i+1}",
            value=leg["to"],
            key=f"to_{i}"
        )

    with col3:
        if st.button("❌", key=f"del_{i}") and len(st.session_state.legs) > 1:
            st.session_state.legs.pop(i)
            st.rerun()

if st.button("➕ 区間を追加"):
    st.session_state.legs.append({"from": "", "to": ""})
    st.rerun()


# =========================
# 日程
# =========================
st.header("📅 日程")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日", value=date.today())
with col2:
    end_date = st.date_input("終了日")


# =========================
# 個人条件
# =========================
st.header("👤 個人条件")

age = st.slider("年齢", 0, 100, 30)
budget_jpy = st.number_input("予算（円）", min_value=0, step=1000)

budget_type = st.radio(
    "予算の考え方",
    ["ポジティブ（余裕あり）", "ネガティブ（節約重視）", "全体"]
)


# =========================
# 為替
# =========================
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

if rate is None:
    budget_foreign = budget_jpy
    st.info(f"為替取得失敗 → 円ベース表示（{budget_jpy} 円）")
else:
    budget_foreign = round(budget_jpy * rate, 2)
    st.info(f"1 JPY = {rate:.4f} {currency} ｜ 約 {budget_foreign} {currency}")


# =========================
# 移動手段
# =========================
st.header("🚆 移動手段")

transport = st.multiselect(
    "利用する移動手段",
    ["飛行機", "新幹線", "バス", "車"]
)


# =========================
# 天気
# =========================
st.header("☀️ 天気条件")

weather = st.radio("想定する天気", ["晴れ", "雨"])


# =========================
# 検索ボタン
# =========================
if st.button("🔍 検索"):

    route = []
    for leg in st.session_state.legs:
        if leg["from"]:
            route.append(leg["from"])
        if leg["to"]:
            route.append(leg["to"])
    route = list(dict.fromkeys(route))
    route_text = " → ".join(route)

    total_days = (end_date - start_date).days + 1

    if total_days <= 0:
        st.error("終了日は開始日より後にしてください")
        st.stop()

    st.subheader("🧳 AI 旅行プラン")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # =========================
    # 日別テンプレート
    # =========================
    day_template = """
あなたはプロの旅行プランナーです。

【重要ルール】
- 必ず最後まで出力する
- 途中で省略しない
- 最低300文字以上
- 実在する地名を使う
- 年齢が20歳未満なら酒類を提案しない
- 晴れなら屋外中心、雨なら屋内中心

【条件】
Day{day_number}
日付: {current_date}
移動ルート: {route}
年齢: {age}
予算方針: {budget_type}
移動手段: {transport}
天気: {weather}

旅行ガイドのように魅力的に書いてください。
"""

    full_plan = ""
    places_set = set()

    for i in range(total_days):

        current_date = start_date + timedelta(days=i)

        prompt = PromptTemplate(
            input_variables=[
                "day_number", "current_date", "route",
                "age", "budget_type", "transport", "weather"
            ],
            template=day_template
        )

        chain = prompt | llm | StrOutputParser()

        st.markdown(f"### 🗓 Day {i+1} ({current_date})")

        day_text = ""
        placeholder = st.empty()

        for chunk in chain.stream({
            "day_number": i+1,
            "current_date": current_date,
            "route": route_text,
            "age": age,
            "budget_type": budget_type,
            "transport": ", ".join(transport),
            "weather": weather
        }):
            day_text += chunk
            placeholder.markdown(day_text)

        full_plan += f"\n\nDay{i+1}\n{day_text}"

        found_places = re.findall(r"[一-龠ぁ-んァ-ンA-Za-z]{3,}", day_text)
        for p in found_places:
            places_set.add(p)

    # =========================
    # Google Maps
    # =========================
    st.subheader("📍 Google Maps ルート")

    places = list(places_set)[:8]

    if places:
        map_route = "/".join([urllib.parse.quote(p) for p in places])
        map_url = f"https://www.google.com/maps/dir/{map_route}"
        st.link_button("Google Mapでルートを開く", map_url)
    else:
        st.info("地図用地点が抽出できませんでした。")
