import streamlit as st
from datetime import date
import urllib.parse
import requests
import json

# ===== LangChain =====
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser



# =========================
# タイトル
# =========================
st.title("🌤️ 天気 × AI 旅行プラン検索アプリ")

# =========================
# 区間入力（Google Flights風）
# =========================
st.header("🧭 移動ルート（区間ごと）")

if "legs" not in st.session_state:
    st.session_state.legs = [
        {"from": "東京", "to": "大阪"}
    ]

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
        params = {
            "from": base,
            "to": target
        }
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data["rates"][target]
    except Exception as e:
        st.warning(f"為替取得エラー: {e}")
        return None

rate = get_exchange_rate("JPY", currency)

if rate is None:
    budget_foreign = budget_jpy
    st.info(f"為替レート取得失敗のため、円ベースで表示します（{budget_jpy} 円）")
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
# 検索
# =========================
if st.button("🔍 検索"):

    # ---- ルート構築 ----
    route = []
    for leg in st.session_state.legs:
        if leg["from"]:
            route.append(leg["from"])
        if leg["to"]:
            route.append(leg["to"])
    route = list(dict.fromkeys(route))

    route_text = " → ".join(route)

    # =========================
    # 条件まとめ
    # =========================
    st.subheader("📝 検索条件まとめ（コピー用）")

    summary = {
        "移動ルート": route_text,
        "日程": f"{start_date} 〜 {end_date}",
        "年齢": age,
        "予算": f"{budget_jpy} 円（約 {budget_foreign} {currency}）",
        "予算方針": budget_type,
        "移動手段": transport,
        "天気": weather,
    }

    st.code(summary, language="json")

    # =========================
    # LangChain
    # =========================
    st.subheader("🧳 AI 旅行プラン")

    template = """
    あなたは優秀な旅行プランナーです。

    【条件】
    移動ルート: {route}
    日程: {start_date} 〜 {end_date}
    年齢: {age}
    予算: {budget_jpy}円（約 {budget_foreign} {currency}）
    予算方針: {budget_type}
    移動手段: {transport}
    天気: {weather}

    【ルール】
    - 晴れなら屋外中心、雨なら屋内中心
    - 実在する地名を使う
    - 1日ごとに分けて書く

    【出力形式】
    以下のJSON形式で出力してください。

    {
    "plan": "旅行プラン文章",
    "places": ["訪問地1", "訪問地2", "訪問地3"]
    }
    """


    prompt = PromptTemplate(
        input_variables=[
            "route", "start_date", "end_date",
            "age", "budget_jpy", "budget_foreign",
            "currency", "budget_type",
            "transport", "weather"
        ],
        template=template
    )

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({
        "route": route_text,
        "start_date": start_date,
        "end_date": end_date,
        "age": age,
        "budget_jpy": budget_jpy,
        "budget_foreign": budget_foreign,
        "currency": currency,
        "budget_type": budget_type,
        "transport": ", ".join(transport),
        "weather": weather
    })

    data = json.loads(response)

    plan = data["plan"]
    places = data["places"]

    st.markdown(plan)



    st.markdown(plan)

    # =========================
    # Google Maps
    # =========================
    st.subheader("📍 Google Maps ルート")

    map_route = "/".join([urllib.parse.quote(p) for p in places])
    map_url = f"https://www.google.com/maps/dir/{map_route}"

    st.markdown(f"### 🗺️ ルートを地図で表示")
    st.link_button(
        "Google Mapでルートを開く",
        map_url
    )

