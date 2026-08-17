# COUNTERWATCH

Overwatch のアンチピックを返すツールです。**Discord ボット**としてサーバーに入れ、スコアボード画像を投げるだけでヒーロー画像つきの立ち回りを返します。Webアプリも同じ知識で動きます。

AI にセットアップを任せる場合は、設定ページ `setup.html` か `prompts/discord-bot-setup.prompt.md` のプロンプトをそのまま渡してください。トークンはチャットに貼らず `.env` だけに書きます。

## Discord ボット（本番の使い方）

専用チャンネルを1つ作り、そこにボットを入れる想定です。スクショを投げる → ボットがマップの読み・敵の勝ち筋・今出すヒーロー（**ポートレート画像**）・クールタイム・動き方を Embed で返します。

### 1. Discord でアプリを作る

1. https://discord.com/developers/applications を開く
2. **New Application** → 名前は `COUNTERWATCH`
3. 左の **Bot** → **Add Bot**
4. **Reset Token** でトークンをコピー（これが `DISCORD_BOT_TOKEN`）
5. 同じページで **Message Content Intent** を ON
6. **Privileged Gateway Intents** の Message Content が必須
7. 左の **OAuth2 → General** で **Application ID** をコピー（`DISCORD_CLIENT_ID`）

### 2. サーバーに招待する

`.env` を置いてから:

```bash
cp .env.example .env
# DISCORD_BOT_TOKEN と DISCORD_CLIENT_ID を書く
pip install -r requirements.txt
python3 -m bot.bot
```

起動ログに招待URLが出ます。ブラウザで開き、自分のサーバーに **Send Messages / Embed Links / Attach Files / Read Message History / Use Slash Commands** で入れます。

直接URLを作る場合（`CLIENT_ID` を差し替え）:

```
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=2147593216&scope=bot%20applications.commands
```

### 3. チャンネルで使う

| 操作 | 内容 |
| --- | --- |
| 画像を投げる | **TAB（スコアボード）全体**のスクショ。日本語UIでも可。上段の青＝味方、下段の赤＝敵、ハイライト行＝自分として読む。同じヒーローが両チームにいても大丈夫。キャプション例: `dps route66 wrecking-ball genji ashe mercy juno` |
| `/counter` | スクショ添付 or テキストで解析。返信にヒーロー画像が付く |
| `/role` | tank / damage / support を覚える |
| `/side` | attack / defend / flex |
| `!cw role dps` | プレフィックス版 |

返信に **立ち回り**（どこに立つか、最初にやること、敵の対処）が付きます。出すヒーローの提案は「出すなら」で書きます。誰が今そのヒーローかは書きません。

立ち回り文は **DeepSeek** で具体化できます（公式APIはテキストのみ。スクショの画素は読めません）。`.env`:

```
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

TAB画像そのものをLLMに読ませるなら OpenAI 互換の Vision が別途必要です。DeepSeek キーを Vision に回しても画像は見えません。

OCR（文字読み）を使うなら:

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng
```

`DISCORD_LISTEN_ALL=0` にすると、チャンネル名に `counterwatch` / `overwatch` / `ow` / `アンチ` が含まれる部屋だけ反応します。専用部屋なら `1` のままで大丈夫です。

## GitHub と自動同期（チャットは切らない）

可能です。ボットは Discord に接続したまま、GitHub 上の `bot/knowledge.json` を定期的に読み直します。ヒーロー追加やマップ解説の更新は **再起動なし** で次の返信から使われます。

```
GitHub (main)  --数分ごと / /reload-->  動いている Discord ボット
     |                                      |
     +-- knowledge.json（ヒーロー・マップ）   チャットはそのまま
     +-- bot.py が変わったときだけ再起動
```

`.env` にリポジトリを書く:

```
GITHUB_REPO=yourname/counterwatch
GITHUB_BRANCH=main
GITHUB_SYNC_SECONDS=180
```

- **公開リポジトリ**: トークンなしで raw から読む
- **プライベート**: `GITHUB_TOKEN` に repo 読み取りできる PAT を入れる
- すぐ反映したいとき: Discord で `/reload`（サーバー管理者）
- ボット本体のコードも自動で揃えたいとき: サーバー上でこのリポジトリを `git clone` し、`GIT_AUTO_PULL=1`

コード（`bot.py` など）の変更だけは短い再接続が入ります。知識データだけの更新では切断しません。

GitHub Actions（`.github/workflows/validate.yml`）は push のたびに knowledge.json が壊れていないか確認します。ボット側は Actions を待たず、GitHub を直接見にいきます。

返信には次が含まれます。

- マップ画像（サムネ）と地形の読み
- 敵編成の勝ち筋と数えるクールタイム
- **1番手ヒーローの大きなポートレート**
- 2〜4番手もサムネ画像つき

## Web アプリ

```bash
python3 server.py
```

http://127.0.0.1:8080

## 中身

- `prompts/discord-bot-setup.prompt.md` — **AI に貼るセットアップ用プロンプト**（ボットを起動・設定させる）
- `bot/bot.py` — Discord ボット
- `bot/engine.py` — アンチピック推論
- `bot/knowledge.json` — 53ヒーロー＋マップ＋CD
- `assets/heroes` — Discord に添付する公式ポートレート
- `js/` — 同じ知識のブラウザ版
