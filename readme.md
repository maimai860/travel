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
8. 宿泊費を自動算出すること
9. 最低観光費を保証すること
10. 条件を満たした場合のみGPTを呼び出すこと
11. 全日程を一度に生成すること
12. 観光地を抽出しGoogle Mapsルートを生成すること

## 非機能要件
1. 日数30日以上は不可
2. APIキー未設定時は利用不可
3. 交通費＋宿泊費が予算超過時は生成不可
4. 観光最低予算未満の場合は生成不可

# 使用技術
## フロントエンド
- streamlit
## バックエンド
- バックエンド
## 認証
- 認証
- OpenAI API
## LangChain
- Google Maps Distance Matrix API

## 使用ライブラリ
- streamlit
- langchain
- langchain-community
- langchain-core
- openai
- requests
- streamlit-authenticator