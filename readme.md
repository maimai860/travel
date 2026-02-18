# Name
AI 旅行プラン検索アプリ

# Overview
天気・予算・日程・移動手段を入力すると、
GPTを用いて複数日分の旅行プランを一括生成するStreamlitアプリです。

生成された観光地は自動で抽出され、Google Mapsルートも同時に作成されます。

# Requirement
本アプリは以下の環境で動作確認しています。
- Tested with Python 3.10.11
- streamlit
- langchain
- langchain-community
- langchain-core
- openai
- requests
- streamlit-authenticator

# Features
このアプリには以下の特徴を持ちます。
1. ログイン機能
    現在下記のユーザ情報でログイン可能としています。
    - ユーザ名：admin
    - パスワード：test123
2. 入力で必要な項目
    - 出発地・到着地の入力
    - 日程設定
    - 予算入力（日割り自動計算）
    - 天気条件指定
    - 利用交通手段選択

3. 出力結果
    - AIによる旅行プラン生成
    - Google Mapsルート生成


# このアプリの注意点
下記の事項の場合は利用できません。
- 日数が30日以上の場合
- 交通費が総予算を超える場合
- 1日あたりの最低必要予算を下回る場合
- 距離取得に失敗した場合
- OpenAI APIキーが未設定の場合
