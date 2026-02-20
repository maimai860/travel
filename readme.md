# 名前
AI 旅行プラン検索アプリ

# デモURL
- https://travel-8hmuwhlqjyqtefzguudazh.streamlit.app/

# デモアカウント
- ユーザー名：admin
- パスワード：test123

# 概要
天気・予算・日程・移動手段を入力すると、
GPTを用いて複数日分の旅行プランを一括生成するStreamlitアプリです。
距離APIを利用して移動距離を取得し、交通費を自動算出します。
総予算から交通費を差し引いた残額を日数で按分し、
1日あたりの利用可能額を超えない旅行プランのみを生成します。

生成された観光地は自動で抽出され、Google Mapsルートも同時に作成されます。

# 要件定義
## 機能要件
1. ログイン機能を持つこと
2. 出発地・到着地を入力できること
3. 複数日程を指定できること
4. 総予算を入力できること
5. 交通手段を選択できること
6. Google Maps Distance Matrix APIで距離取得できること
7. 交通費を往復で自動算出すること
8. 最低観光費を保証すること
9. 条件を満たした場合のみGPTを呼び出すこと
10. 全日程を一度に生成すること
11. 観光地を抽出しGoogle Mapsルートを生成すること
12. 初日最終日は移動のみとすること
13. 日数は1日以上30日未満であること
14. 1日あたり利用可能額がユーザー指定最低予算を下回る場合は生成不可とする
15. 旅行期間中は毎日一定の費用が発生する前提で総日数で按分すること

## 非機能要件
1. 日数30日以上は不可
2. APIキー未設定時は利用不可
3. 認証機能を必須とする

# 使用技術
## フロントエンド
- streamlit
## バックエンド
- バックエンド
## 認証
- 認証
- OpenAI API
## AI生成
- LangChain + ChatOpenAI

## 距離API
- Nominatim + OSRM

## 使用ライブラリ
- streamlit
- langchain
- langchain-community
- langchain-core
- openai
- requests
- streamlit-authenticator