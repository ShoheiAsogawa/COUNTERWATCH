# COUNTERWATCH Discord ボット — AI 実行プロンプト

次のブロックを、設定を任せる AI（Cursor / Claude / ChatGPT など）に **そのまま貼り付けて** ください。
トークンは人間が Developer Portal からコピーし、AI には **チャットに貼らない** こと。`.env` にだけ書く。

---

## プロンプト本文（ここからコピー）

```
あなたは COUNTERWATCH（Overwatch 2 アンチピック Discord ボット）のセットアップ担当です。
リポジトリのルートで作業してください。ゴールは「Discord サーバーの専用チャンネルにボットが入り、スコアボード画像またはテキストに対してヒーロー画像つきのアンチピックを返す」状態にすることです。

# 絶対に守ること
- DISCORD_BOT_TOKEN をチャット・コミット・ログ・スクリーンショットに出さない。
- `.env` は git に入れない（`.gitignore` 済みのはず。確認する）。
- トークンが無いのにボットを起動しようとして失敗したら、人間に Developer Portal の操作だけ依頼し、自分はファイルとコマンドを進める。
- 既存の `bot/` `js/` `assets/` の知識データは消さない。
- Python はリポジトリルートから `python3 -m bot.bot` で起動する（`from bot.engine` のため）。

# このボットがすること
- チャンネルに Overwatch のタブ/スコアボード画像、または「gibraltar pharah mercy reinhardt lucio brigitte」のようなテキストが来たら解析する。
- Embed でマップの読み・敵の勝ち筋・今出すヒーロー（ポートレート PNG を添付）・クールタイム・動き方を返す。
- GitHub の `bot/knowledge.json` を数分おきに取りに行き、プロセスを落とさず知識だけ差し替える。

# フェーズ A — Discord Developer Portal（人間のブラウザが必要。AI は手順を出し、可能なら一緒に確認する）

1. https://discord.com/developers/applications を開く。
2. New Application。名前は `COUNTERWATCH`。Create。
3. 左メニュー Bot。
   - Add Bot（未作成なら）。
   - USERNAME は COUNTERWATCH でよい。
   - Privileged Gateway Intents で **MESSAGE CONTENT INTENT** を ON にして Save Changes。
     （これがないと画像のキャプションもテキストも読めない。）
   - Reset Token → Yes → トークンをコピー。これが DISCORD_BOT_TOKEN。一度しか完全表示されないことがある。
   - Public Bot は ON のままでよい。
4. 左メニュー OAuth2 → General。
   - APPLICATION ID をコピー。これが DISCORD_CLIENT_ID。
5. 左メニュー OAuth2 → URL Generator（任意・招待URLを手動で作る場合）。
   - SCOPES: `bot` と `applications.commands` にチェック。
   - BOT PERMISSIONS: Send Messages, Embed Links, Attach Files, Read Message History, Use Slash Commands, View Channels, Read Message History, Add Reactions（任意）。
   - 数値パーミッションは `2147593216` で足りる（Send Messages + Embed Links + Attach Files + Read Message History + Use Slash Commands + View Channel 相当）。
   - Generated URL を控える。
6. Discord サーバー側:
   - テキストチャンネルを1つ作る。名前例: `counterwatch`。
   - ボットをそのサーバーに招待（Generated URL または起動ログの URL）。
   - チャンネル権限でボットに「メッセージを見る / 送る / ファイル添付 / 埋め込みリンク」を許可。

# フェーズ B — マシン側のファイル

1. リポジトリルートにいることを確認する。
2. `cp .env.example .env`（無ければ作成）。
3. `.env` を次の形にする（値は人間が埋める。AI はプレースホルダを残したままコミットしない）:

DISCORD_BOT_TOKEN=<portalのBotトークン>
DISCORD_CLIENT_ID=<Application ID>
DISCORD_LISTEN_ALL=1
DISCORD_CHANNEL_NAMES=counterwatch,アンチ,overwatch,ow
DISCORD_SERVER_ID=
DISCORD_OWNER_IDS=
GITHUB_REPO=<githubの owner/repo。未公開なら空でよい>
GITHUB_BRANCH=main
GITHUB_KNOWLEDGE_PATH=bot/knowledge.json
GITHUB_TOKEN=
GITHUB_SYNC_SECONDS=180
GIT_AUTO_PULL=0

説明:
- DISCORD_LISTEN_ALL=1 … 招待した全チャンネルで画像に反応。専用部屋なら 1 が簡単。
- DISCORD_LISTEN_ALL=0 … チャンネル名が CHANNEL_NAMES に含まれるときだけ反応。
- DISCORD_OWNER_IDS … カンマ区切りの Discord ユーザー雪花ID。/reload を管理者以外にも許可するとき。
- GITHUB_REPO … 知識の自動更新。空だと同期をスキップ。
- GIT_AUTO_PULL=1 はこのマシンが git clone のときだけ。bot.py が変わるとプロセス再起動する。

4. `.gitignore` に `.env` があるか確認。無ければ追加。
5. `pip install -r requirements.txt`
   必要パッケージ: discord.py, python-dotenv, Pillow, pytesseract
6. 任意: システムに tesseract-ocr が入っていると画像OCRが強い。無ければキャプション解析で動く。
   Debian/Ubuntu: `sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn`（権限があれば）。

# フェーズ C — 知識ファイルの健全性

1. `assets/heroes/` にヒーロー PNG が約53枚あること。
2. `bot/knowledge.json` が JSON として読めること。
3. 次でエンジンをスモークする:

python3 -c "from bot.engine import recommend, parse_text; s=parse_text('dps route66 wrecking-ball genji ashe mercy juno'); print(s); r=recommend('damage', s['hero_keys'], s['map_key'], 'attack'); print([x['hero']['key'] for x in r['picks'][:5]])"

期待: map_key が route-66。敵に wrecking-ball / genji / ashe / mercy / juno。TABスクショはポートレート照合で読む。

# フェーズ D — 起動

1. ルートで: `python3 -m bot.bot`
2. 成功ログ例:
   - COUNTERWATCH online as ...
   - invite: https://discord.com/oauth2/authorize?client_id=...&permissions=2147593216&scope=bot%20applications.commands
3. 失敗したら:
   - LoginFailure / Improper token → トークン誤り。Reset Token し直す。MESSAGE CONTENT を忘れていないか確認。
   - PrivilegedIntentsRequired → Portal で Message Content Intent が OFF。
   - ModuleNotFoundError: bot → カレントディレクトリがルートではない。
4. 招待URLをブラウザで開き、対象サーバーを選んで Authorize。
5. Discord で `/` を押し、counter / role / side / reload が出るか確認。出ない場合は最大1時間待つか、ボットをキックして再招待。開発中は Bot をオフ→オン。

# フェーズ E — 動作確認（必須）

専用チャンネルで次を順に送る。

1. `/role dps` と `/side attack`（または `!cw role dps`）。
2. テキスト:
   gibraltar pharah mercy reinhardt lucio brigitte
   ボットが Embed を返し、ヒーローの顔画像が添付されること。
3. 可能なら Overwatch のスコアボードスクショを添付。キャプションにマップ名と敵ヒーローを書くと精度が上がる。
4. 管理者で `/reload`。GitHub 未設定なら「GitHub 未設定」でよい。設定済みなら knowledge を取りに行く。

# フェーズ F — GitHub 自動更新（任意）

知識だけ自動更新したい場合:
- このリポジトリを GitHub に push。
- `.env` の GITHUB_REPO=owner/name
- プライベートリポジトリなら GITHUB_TOKEN に contents:read の PAT。
- ボットは 180 秒ごとに raw.githubusercontent.com（または API）から bot/knowledge.json を取得し、メモリ上の ENGINE を差し替える。チャット接続は切らない。
- マップ解説やヒーローを直したら `python3 tools/build_data.py` で js/data.js と bot/knowledge.json を再生成して push。

# フェーズ G — 報告

作業後、人間に次だけ返す（トークンは伏せる）:
- Portal で Message Content Intent が ON か
- .env のキー一覧（値は ****）
- pip と起動コマンド
- 招待URL（client_id は出してよい。token は出さない）
- スモークテストの推薦ヒーロー5体
- 残っている人手作業
```

---

## プロンプト本文（ここまで）

人間が先に用意するもの: Discord アカウント、ボットを入れるサーバーの管理権限、Bot トークン。
AI がやるもの: `.env` 作成、依存インストール、スモークテスト、起動、招待URL提示、動作確認手順。
