# asari-muse (Slack版)

チームのSlackワークスペース用の常駐Bot。Discord版 asari-muse と同じ橋渡し方式:
Botがオーナーのメンション/DMをキューに記録 → 別マシンのフック（30秒間隔、SSH同期）が
Claudeを起こしてBot経由でスレッド返信する。

公開リポジトリ: asari194617/muse-chat-bots（`slack/` 配下）

## ファイル
- `bot.py` — slack_bolt 製 Bot 本体（Socket Mode）。オーナーのメンション/DMのみキューに入れる
- `manifest.yaml` — Slackアプリ作成用マニフェスト（api.slack.com/apps で「From a manifest」）
- `queue_tool.py` / `history.py` / `fetch_channel.py` / `reply.py` / `post.py` — 橋渡し用ヘルパー
- `sync_remote_queue.py` — Bot常駐マシン上のキューを橋渡し側へSSH同期（接続先ホストは環境変数 `ASARI_MUSE_SSH_HOST`）
- `asari-muse-slack-bot.service` — systemd ユーザーユニット
- `owner.json` — オーナーのSlackメンバーID（Git管理外）
- `.env` — SLACK_BOT_TOKEN (xoxb) と SLACK_APP_TOKEN (xapp)（Git管理外、権限600）

## 稼働形態
- 稼働先: 自宅マシン（Ubuntu）の systemd ユーザーサービス `asari-muse-slack-bot`、配置は `~/asari-muse-slack/`
- 状態確認: `ssh <bot-host> 'systemctl --user status asari-muse-slack-bot'`

## 運用方針（ワークスペース管理者のルールに準拠）
- 本Botは「オーナーのメンション/DMへの応答」だけを行う。自発的な投稿や、他メンバーへの自動メンション・大量投稿はしない
- ワークスペース内の情報を外部送信したり、第三者へ無断共有したりしない
- 誤作動で周囲に影響が出る場合は速やかに停止する
- 橋渡し側のプライバシー規則はDiscord版より厳しく、予定の詳細・メール内容・個人的な情報はSlackに出さない（持ち主との直接のチャットで回答する）

## アプリ作成・トークン設定（オーナー作業）
1. https://api.slack.com/apps → Create New App → From a manifest → 対象ワークスペースを選び、`manifest.yaml` を貼り付けて作成
2. 「Install App」→ Install to Workspace（管理者承認が求められた場合は承認リクエストを送信）
3. 「Basic Information」→ App-Level Tokens → Generate Token: scope `connections:write` を付けて生成（xapp-...）
4. 「OAuth & Permissions」の Bot User OAuth Token（xoxb-...）と 3. の xapp を、常駐マシンの `~/asari-muse-slack/.env` に記入
5. 対象チャンネルにアプリを追加（チャンネルで @asari-muse を招待）
