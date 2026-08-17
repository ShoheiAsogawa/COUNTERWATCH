#!/usr/bin/env python3
"""Generate js/data.js — Overwatch 2 hero/map/matchup knowledge base."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from map_coach import get_coach  # noqa: E402
from hero_specs import HERO_CDS, HERO_PLAY  # noqa: E402

heroes_api = json.loads(Path("/tmp/ow_heroes.json").read_text())
maps_api = json.loads(Path("/tmp/ow_maps.json").read_text())

NAME_JA = {
    "ana": "アナ", "anran": "アンラン", "ashe": "アッシュ", "baptiste": "バティスト",
    "bastion": "バスティオン", "brigitte": "ブリギッテ", "cassidy": "キャスディ",
    "dmon": "D.モン", "domina": "ドミナ", "doomfist": "ドゥームフィスト", "dva": "D.Va",
    "echo": "エコー", "emre": "エムレ", "freja": "フレイヤ", "genji": "ゲンジ",
    "hanzo": "ハンゾー", "hazard": "ハザード", "illari": "イラリー",
    "jetpack-cat": "ジェットパックキャット", "junker-queen": "ジャンカー・クイーン",
    "junkrat": "ジャンクラット", "juno": "ジュノ", "kiriko": "キリコ",
    "lifeweaver": "ライフウィーバー", "lucio": "ルシオ", "mauga": "マウガ",
    "mei": "メイ", "mercy": "マーシー", "mizuki": "ミズキ", "moira": "モイラ",
    "orisa": "オリーサ", "pharah": "ファラ", "ramattra": "ラマットラ",
    "reaper": "リーパー", "reinhardt": "ラインハルト", "roadhog": "ロードホッグ",
    "shion": "シオン", "sierra": "シエラ", "sigma": "シグマ", "sojourn": "ソジョーン",
    "soldier-76": "ソルジャー76", "sombra": "ソンブラ", "symmetra": "シンメトラ",
    "torbjorn": "トールビョーン", "tracer": "トレーサー", "vendetta": "ヴェンデッタ",
    "venture": "ベンチャー", "widowmaker": "ウィドウメイカー", "winston": "ウィンストン",
    "wrecking-ball": "レッキング・ボール", "wuyang": "ウーヤン", "zarya": "ザリア",
    "zenyatta": "ゼニヤッタ",
}

MAP_JA = {
    "aatlis": "アートリス", "antarctic-peninsula": "南極半島", "anubis": "アヌビス神殿",
    "arena-victoriae": "アリーナ・ウィクトリアエ", "ayutthaya": "アユタヤ",
    "black-forest": "黒い森", "blizzard-world": "ブリザード・ワールド",
    "busan": "釜山", "castillo": "カスティージョ", "chateau-guillard": "シャトー・ギヤール",
    "circuit-royal": "サーキット・ロイヤル", "colosseo": "コロッセオ",
    "dorado": "ドラド", "ecopoint-antarctica": "エコポイント：南極",
    "eichenwalde": "アイヒェンヴァルデ", "esperanca": "エスペランサ",
    "gogadoro": "ゴガドロ", "hanamura": "花村", "hanaoka": "花岡",
    "havana": "ハバナ", "hollywood": "ハリウッド", "horizon": "ホライゾン月面コロニー",
    "ilios": "イリオス", "junkertown": "ジャンカータウン", "lijiang-tower": "麗江タワー",
    "kanezaka": "金坂", "kings-row": "キングス・ロウ", "malevento": "マレヴェント",
    "midtown": "ミッドタウン", "necropolis": "ネクロポリス", "nepal": "ネパール",
    "neon-junction": "ネオンジャンクション", "new-junk-city": "ニュージャンクシティ",
    "new-queen-street": "ニュークイーンストリート", "numbani": "ヌンバニ",
    "oasis": "オアシス", "paraiso": "パライソ", "paris": "パリ", "petra": "ペトラ",
    "place-lacroix": "プラス・ラクロワ", "powder-keg-mine": "パウダーケッグ鉱山",
    "practice-range": "練習場", "redwood-dam": "レッドウッドダム",
    "rialto": "リアルト", "route-66": "ルート66", "runasapi": "ルナサピ",
    "samoa": "サモア", "shambali-monastery": "シャンバリ僧院", "suravasa": "スラヴァサ",
    "thames-district": "テムズ地区", "throne-of-anubis": "アヌビスの玉座",
    "volskaya": "ヴォルスカヤ・インダストリーズ", "watchpoint-gibraltar": "ウォッチポイント：ジブラルタル",
    "wuxing-university": "五星大学",
}

MODE_JA = {
    "control": "コントロール", "escort": "エスコート", "hybrid": "ハイブリッド",
    "push": "プッシュ", "flashpoint": "フラッシュポイント", "clash": "クラッシュ",
    "assault": "アサルト", "capture-the-flag": "キャプチャー・ザ・フラッグ",
    "elimination": "エリミネーション", "deathmatch": "デスマッチ",
    "team-deathmatch": "チームデスマッチ", "payload-race": "ペイロードレース",
    "practice-range": "練習場", "workshop": "ワークショップ",
}

# traits: choke, highground, longsight, vertical, open, flank, environmental, close, payload, control
MAP_TRAITS = {
    "kings-row": (["choke", "brawl", "payload", "close"], "狭いチョークが多く、盾＋近接のブロウルが強い。"),
    "eichenwalde": (["choke", "brawl", "highground", "payload"], "城門チョークはジャンクラット／メイ／ラインが輝く。"),
    "hollywood": (["flank", "highground", "payload", "choke"], "セットが多く、高所スナイプと側面ダイブの両方が通る。"),
    "numbani": (["open", "highground", "flank", "payload"], "開放的でファラ／エコーとウィドウが同時に成立しやすい。"),
    "paraiso": (["flank", "close", "payload", "vertical"], "カーブした道と高所。スピード構成とダイブが強い。"),
    "midtown": (["open", "longsight", "payload", "highground"], "長い視線とバス。ヒットスキャンとシグマが安定。"),
    "blizzard-world": (["choke", "flank", "payload"], "テーマパークの曲がり角が多く、ブロウルと boop が有効。"),
    "neon-junction": (["highground", "close", "payload", "flank"], "ネオン街の高低差。近距離とモビリティが重要。"),
    "circuit-royal": (["longsight", "highground", "payload", "open"], "カジノ大通りは超長射程。ウィドウ／アッシュ必須級。"),
    "dorado": (["highground", "flank", "payload", "vertical"], "高所と脇道だらけ。ダイブとスナイプが拮抗。"),
    "havana": (["longsight", "highground", "payload", "open"], "最終地点はスナイパー天堂。ヒットスキャンが支配する。"),
    "junkertown": (["longsight", "open", "payload", "highground"], "荒野の長視線。バスティオンやスナイプが強い。"),
    "rialto": (["choke", "payload", "flank", "environmental"], "運河 boop と狭い橋。ルシオ／ハザードが強い。"),
    "route-66": (["open", "longsight", "payload", "flank"], "ガソリンスタンド周辺は開放。ポークと flank が両立。"),
    "shambali-monastery": (["vertical", "choke", "payload", "highground"], "高低差が大きい僧院。ジュノ／ファラ向き。"),
    "watchpoint-gibraltar": (["highground", "vertical", "payload", "longsight"], "航空機の高所。ファラ／エコー／ジュノが天敵。"),
    "ilios": (["environmental", "control", "open", "vertical"], "井戸と崖。ブープとダイブが試合を決める。"),
    "busan": (["control", "close", "flank", "vertical"], "市街地とクラブ。近接ダイブとモビリティが強い。"),
    "lijiang-tower": (["control", "highground", "flank", "close"], "庭園の高所と夜市の近接。構成がポイントで変わる。"),
    "nepal": (["control", "choke", "close", "environmental"], "聖域は超近接。村は崖 boop。ブロウル向き。"),
    "oasis": (["control", "open", "highground", "vertical"], "大学は開放、庭園は高所。ポークとフライヤーが強い。"),
    "samoa": (["control", "open", "environmental", "close"], "ビーチと崖。 boop と近接が混在。"),
    "antarctic-peninsula": (["control", "open", "flank", "close"], "研究所と氷。中距離と側面が強い。"),
    "arena-victoriae": (["control", "open", "highground"], "コロッセオ系の円形。ポークと高所取り。"),
    "gogadoro": (["control", "close", "flank"], "釜山近郊の近接寄りコントロール。"),
    "wuxing-university": (["control", "open", "highground", "vertical"], "キャンパスの視線。ポークとフライヤーが通りやすい。"),
    "colosseo": (["push", "close", "flank", "choke"], "狭い路地のプッシュ。ブロウルとスピードが最強。"),
    "esperanca": (["push", "flank", "highground", "close"], "坂と脇道。ダイブとルシオが強い。"),
    "new-queen-street": (["push", "close", "flank", "environmental"], "橋と川。 boop と近接ダイブが有効。"),
    "runasapi": (["push", "vertical", "highground", "flank"], "垂直移動が多い。ジュノ／ウィンストン向き。"),
    "place-lacroix": (["push", "open", "flank"], "パリのプッシュ。中距離ポークが通りやすい。"),
    "redwood-dam": (["push", "open", "longsight"], "ダムの長視線。スナイプとシグマが強い。"),
    "aatlis": (["flashpoint", "open", "flank", "close"], "複数拠点をローテ。モビリティとルシオが最重要。"),
    "new-junk-city": (["flashpoint", "close", "flank", "open"], "ジャンクの拠点戦。近接と回転力が勝つ。"),
    "suravasa": (["flashpoint", "open", "flank", "vertical"], "寺院の回転。ダイブとスピード構成向き。"),
    "hanaoka": (["clash", "close", "choke"], "超近接のクラッシュ。ブロウル一択に近い。"),
    "throne-of-anubis": (["clash", "close", "choke", "highground"], "狭いクラッシュ。盾とメイが強い。"),
}

HERO_META = {
    "ana": {
        "hp": 250, "range": "long",
        "tags": ["hitscan", "antiheal", "cc", "poke", "sleeper", "long-range"],
        "strengths": ["バイオグレでタンクの回復を止める", "スリープでダイブとアルティメットを無効化"],
        "weaknesses": ["機動力が低く正面ダイブに弱い", "近距離のエイム勝負が苦手"],
        "abilities": [
            ("Biotic Rifle", "バイオティック・ライフル", "回復／ダメージの狙撃銃"),
            ("Sleep Dart", "スリープダーツ", "敵を睡眠状態にする"),
            ("Biotic Grenade", "バイオティック・グレネード", "味方回復増＋敵アンチヒール"),
        ],
        "ult": ("Nano Boost", "ナノブースト"),
    },
    "anran": {
        "hp": 225, "range": "close",
        "tags": ["flank", "fire", "mobile", "burn", "dive"],
        "strengths": ["炎DoTで集団を溶かす", "死亡時アルティメットで復活し脅威が残る"],
        "weaknesses": ["中遠距離のヒットスキャンに弱い", "CCで突進を止められる"],
        "abilities": [
            ("Zhuque Fans", "朱雀扇", "炎を付与する扇"),
            ("Inferno Rush", "インフェルノラッシュ", "炎の突進"),
            ("Dancing Blaze", "ダンシングブレイズ", "敵をすり抜けて回避"),
        ],
        "ult": ("Vermillion Ascent", "ヴァーミリオンアセント"),
    },
    "ashe": {
        "hp": 250, "range": "long",
        "tags": ["hitscan", "sniper", "poke", "long-range", "dynamite"],
        "strengths": ["スコープショットでフライヤーとタンクを削る", "ダイナマイトの範囲バースト"],
        "weaknesses": ["近距離ダイブ（ゲンジ／トレーサー）に弱い", "遮蔽が多いと価値が落ちる"],
        "abilities": [
            ("The Viper", "ザ・バイパー", "スコープ付きライフル"),
            ("Coach Gun", "コーチガン", "ノックバック散弾"),
            ("Dynamite", "ダイナマイト", "延焼爆弾"),
        ],
        "ult": ("B.O.B.", "B.O.B."),
    },
    "baptiste": {
        "hp": 250, "range": "mid",
        "tags": ["hitscan", "immortality", "poke", "burst-heal", "high-ground"],
        "strengths": ["イモータリティで味方を死なせない", "ヒットスキャンで空も取れる"],
        "weaknesses": ["Hackやアンチヒールでランプが腐る", "持続ダイブにCDが追いつかない"],
        "abilities": [
            ("Biotic Launcher", "バイオティック・ランチャー", "バースト銃＋回復グレ"),
            ("Regenerative Burst", "リジェネバースト", "周囲回復"),
            ("Immortality Field", "イモータリティ・フィールド", "致死ダメージ無効"),
        ],
        "ult": ("Amplification Matrix", "アンプ・マトリックス"),
    },
    "bastion": {
        "hp": 300, "range": "mid",
        "tags": ["bunker", "tankbuster", "transform", "choke"],
        "strengths": ["アサルト形態で盾とタンクを溶かす", "長視線マップで絶対的な火力"],
        "weaknesses": ["ダイブとハックに極端に弱い", "シールドのない近接戦で溶ける"],
        "abilities": [
            ("Configuration: Assault", "アサルト形態", "ガトリング"),
            ("A-36 Tactical Grenade", "戦術グレネード", "バウンド爆弾"),
            ("Ironclad", "アイアンクラッド", "変形中のダメージ軽減"),
        ],
        "ult": ("Configuration: Artillery", "アーティラリー"),
    },
    "brigitte": {
        "hp": 250, "range": "melee",
        "tags": ["brawl", "peel", "melee", "anti-flank", "armor"],
        "strengths": ["フランカーを鞭とバッシュで追放する", "インスパイアの範囲回復"],
        "weaknesses": ["ファラ／エコーなど空中に届かない", "長射程ポークで盾を削られる"],
        "abilities": [
            ("Rocket Flail", "ロケットフレイル", "近接フレイル"),
            ("Repair Pack", "リペアパック", "単体回復"),
            ("Whip Shot", "ウィップショット", "遠距離ノックバック"),
            ("Barrier Shield", "バリアシールド", "小型盾"),
        ],
        "ult": ("Rally", "ラリー"),
    },
    "cassidy": {
        "hp": 275, "range": "mid",
        "tags": ["hitscan", "anti-flank", "mid-range", "cc"],
        "strengths": ["中距離の安定ヒットスキャン", "マググレでダイブを罰する"],
        "weaknesses": ["超長射程ウィドウに負ける", "盾の厚いブロウルで火力不足"],
        "abilities": [
            ("Peacekeeper", "ピースキーパー", "リボルバー"),
            ("Combat Roll", "コンバットロール", "回避＋リロード"),
            ("Magnetic Grenade", "マグネティックグレネード", "追尾グレ"),
        ],
        "ult": ("Deadeye", "デッドアイ"),
    },
    "dmon": {
        "hp": 650, "range": "melee",
        "tags": ["melee", "barrier", "brawl", "mech", "mobile"],
        "strengths": ["剣盾の近接圧力と水平ブースト", "リミットブレイクのディスコード相当デバフ"],
        "weaknesses": ["垂直機動がなく空中に弱い", "遠距離ヒットスキャンとタレットに溶ける"],
        "abilities": [
            ("Plasma Saber", "プラズマセイバー", "近接エネルギー剣"),
            ("Power Barrier", "パワーバリア", "正面エネルギー盾"),
            ("Propulsors", "プロパルサー", "燃料式水平ダッシュ"),
            ("Surging Strike", "サージングストライク", "盾構えからの盾撃"),
        ],
        "ult": ("Limit Break", "リミットブレイク"),
    },
    "domina": {
        "hp": 550, "range": "long",
        "tags": ["poke", "barrier", "beam", "long-range", "cc"],
        "strengths": ["最長クラスのビームでポークする", "セグメント盾で味方を守る"],
        "weaknesses": ["側面ダイブとソンブラに崩壊する", "近接ブロウルでビームが活きない"],
        "abilities": [
            ("Photon Magnum", "フォトンマグナム", "チャージビーム"),
            ("Barrier Array", "バリアアレイ", "分割ハードライト盾"),
            ("Sonic Repulsors", "ソニックリパルサー", "直線ノックバック＋壁スタン"),
        ],
        "ult": ("Panopticon", "パノプティコン"),
    },
    "doomfist": {
        "hp": 450, "range": "close",
        "tags": ["dive", "melee", "burst", "mobile", "punch"],
        "strengths": ["パンチでバックラインを破壊する", "ブロックで弾をチャージに変える"],
        "weaknesses": ["ハック・スタン・フックで完全停止", "空中と遠距離に届かない"],
        "abilities": [
            ("Rocket Punch", "ロケットパンチ", "チャージパンチ"),
            ("Seismic Slam", "スラム", "着地範囲攻撃"),
            ("Power Block", "パワーブロック", "ダメージ吸収"),
        ],
        "ult": ("Meteor Strike", "メテオストライク"),
    },
    "dva": {
        "hp": 650, "range": "close",
        "tags": ["dive", "matrix", "mobile", "anti-projectile", "mech"],
        "strengths": ["ディフェンスマトリックスで爆弾とアルティメットを消す", "ブースターでバックラインへダイブ"],
        "weaknesses": ["ビーム（ザリア／シンメ／ Moira）にマトリックスが無効", "ザリアバブルでダイブが虚空に"],
        "abilities": [
            ("Fusion Cannons", "フュージョンキャノン", "ショットガンビーム"),
            ("Defense Matrix", "ディフェンスマトリックス", "弾消し"),
            ("Boosters", "ブースター", "飛行突進"),
            ("Micro Missiles", "マイクロミサイル", "小型ロケット"),
        ],
        "ult": ("Self-Destruct", "自爆"),
    },
    "echo": {
        "hp": 250, "range": "mid",
        "tags": ["flyer", "beam", "burst", "mobile", "duplicate"],
        "strengths": ["飛行からビームでタンクを溶かす", "デュプリケートで構成を盗む"],
        "weaknesses": ["ヒットスキャンの集中砲火", "カシスティ／アッシュ／バティスト"],
        "abilities": [
            ("Tri-Shot", "トライショット", "3点投射"),
            ("Flight", "フライト", "飛行"),
            ("Focusing Beam", "フォーカシングビーム", "低体力特化ビーム"),
        ],
        "ult": ("Duplicate", "デュプリケート"),
    },
    "emre": {
        "hp": 250, "range": "mid",
        "tags": ["hitscan", "burst", "mobile", "self-sustain", "grenade"],
        "strengths": ["バーストライフルの安定火力", "アルティメットで一時飛行し空を取る"],
        "weaknesses": ["純スナイプに射程負け", "ダイブに単体だと脆い"],
        "abilities": [
            ("Synthetic Burst Rifle", "バーストライフル", "3点バースト"),
            ("Siphon Blaster", "サイフォンブラスター", "吸血ピストル"),
            ("Cyber Frag", "サイバーフラグ", "バウンドグレ"),
        ],
        "ult": ("Override Protocol", "オーバーライドプロトコル"),
    },
    "freja": {
        "hp": 225, "range": "long",
        "tags": ["projectile", "mobile", "poke", "recon"],
        "strengths": ["ダッシュ更新の爆発ボルト", "ハンゾーより機動力が高いポーク"],
        "weaknesses": ["ヒットスキャンとの撃ち合い", "近接フランカー"],
        "abilities": [
            ("Redraw Crossbow", "クロスボウ", "連射ボルト"),
            ("Take Aim", "テイクエイム", "爆発チャージショット"),
            ("Quick Dash", "クイックダッシュ", "ダッシュ＋エイム更新"),
        ],
        "ult": ("Bola Shot", "ボーラショット"),
    },
    "genji": {
        "hp": 250, "range": "close",
        "tags": ["flank", "deflect", "mobile", "dive", "melee-ult"],
        "strengths": ["ディフレクトで投射物を返す", "バックライン暗殺と龍刃"],
        "weaknesses": ["ビームと Moira にディフレクトが無効", "ウィンストンのテスラで滑る"],
        "abilities": [
            ("Shuriken", "手裏剣", "3連／扇状"),
            ("Deflect", "ディフレクト", "弾き返し"),
            ("Swift Strike", "スイフトストライク", "斬撃ダッシュ"),
        ],
        "ult": ("Dragonblade", "龍刃"),
    },
    "hanzo": {
        "hp": 250, "range": "long",
        "tags": ["sniper", "projectile", "poke", "wallhack"],
        "strengths": ["ワンショットヘッドとソニック情報", "ドラゴンストライクのライン切り"],
        "weaknesses": ["ウィンストン／D.Va のダイブ", "至近距離"],
        "abilities": [
            ("Storm Bow", "ストームボウ", "チャージ弓"),
            ("Storm Arrows", "ストームアロー", "速射跳弾"),
            ("Sonic Arrow", "ソニックアロー", "索敵"),
        ],
        "ult": ("Dragonstrike", "龍撃波"),
    },
    "hazard": {
        "hp": 550, "range": "close",
        "tags": ["dive", "brawl", "wall", "cc", "mobile"],
        "strengths": ["ジャグドウォールで敵を分断", "リープでバックラインへ"],
        "weaknesses": ["空中と長射程", "アンチヒールでリープが自殺になる"],
        "abilities": [
            ("Bonespur", "ボーンスパー", "スパイクショットガン"),
            ("Jagged Wall", "ジャグドウォール", "地形生成"),
            ("Violent Leap", "バイオレントリープ", "突進斬撃"),
        ],
        "ult": ("Downpour", "ダウンポア"),
    },
    "illari": {
        "hp": 250, "range": "mid",
        "tags": ["hitscan", "pylon", "poke", "high-ground"],
        "strengths": ["パイロンの放置回復", "レール相当のサンショット"],
        "weaknesses": ["パイロン破壊とダイブ", "メインヒール量は状況次第"],
        "abilities": [
            ("Solar Rifle", "ソーラーライフル", "ダメージ／回復ビーム"),
            ("Outburst", "アウトバースト", "ノックバックジャンプ"),
            ("Healing Pylon", "ヒーリングパイロン", "設置回復"),
        ],
        "ult": ("Captive Sun", "キャプティブサン"),
    },
    "jetpack-cat": {
        "hp": 225, "range": "mid",
        "tags": ["flyer", "mobility-support", "heal", "peel"],
        "strengths": ["永久飛行で高所取り", "味方を運んでダイブ／退避させる"],
        "weaknesses": ["ヒットスキャンの的", "キャリー中は機動力が落ちる"],
        "abilities": [
            ("Biotic Pawjectiles", "バイオティックポウ", "回復／ダメージ弾"),
            ("Lifeline", "ライフライン", "味方運搬"),
            ("Purr", "パー", "拡大する回復ゾーン"),
        ],
        "ult": ("Catnapper", "キャットナッパー"),
    },
    "junker-queen": {
        "hp": 450, "range": "close",
        "tags": ["brawl", "antiheal-ult", "melee", "self-sustain"],
        "strengths": ["創傷で近接を支配", "ランページのアンチヒール"],
        "weaknesses": ["空中とキリコの浄化", "遠距離ポーク"],
        "abilities": [
            ("Scattergun", "スキャッターガン", "ショットガン"),
            ("Jagged Blade", "ジャグドブレイド", "引き寄せナイフ"),
            ("Commanding Shout", "シャウト", "移動速度＋オーバーHP"),
        ],
        "ult": ("Rampage", "ランページ"),
    },
    "junkrat": {
        "hp": 250, "range": "mid",
        "tags": ["spam", "choke", "mine", "projectile", "anti-shield"],
        "strengths": ["チョークと盾割り", "マインで環境キル"],
        "weaknesses": ["ヒットスキャンとダイブ", "開放マップで弾が無駄"],
        "abilities": [
            ("Frag Launcher", "フラグランチャー", "バウンドグレ"),
            ("Concussion Mine", "コンカッションマイン", "爆発移動"),
            ("Steel Trap", "スチールトラップ", "拘束罠"),
        ],
        "ult": ("RIP-Tire", "RIPタイヤ"),
    },
    "juno": {
        "hp": 75, "range": "mid",
        "tags": ["flyer", "speed", "heal", "mobile", "damage-amp"],
        "strengths": ["垂直マップの機動力", "ハイパーリングでダイブを加速"],
        "weaknesses": ["本体が極めて脆い", "ヒットスキャン"],
        "abilities": [
            ("Mediblaster", "メディブラスター", "バースト回復／ダメージ"),
            ("Hyper Ring", "ハイパーリング", "移動速度リング"),
            ("Glide Boost", "グライドブースト", "水平滑空"),
        ],
        "ult": ("Orbital Ray", "オービタルレイ"),
    },
    "kiriko": {
        "hp": 200, "range": "mid",
        "tags": ["cleanse", "teleport", "headshot", "peel", "mobile"],
        "strengths": ["鈴でアンチ・スタン・創傷を消す", "壁登りとTPで生存"],
        "weaknesses": ["メインヒールが投射で遅れる", "ソンブラEMP"],
        "abilities": [
            ("Healing Ofuda", "お札", "追尾回復"),
            ("Kunai", "クナイ", "クリティカル特化"),
            ("Swift Step", "神出鬼没", "味方へTP"),
            ("Protection Suzu", "鈴", "浄化＋無敵"),
        ],
        "ult": ("Kitsune Rush", "狐走り"),
    },
    "lifeweaver": {
        "hp": 275, "range": "mid",
        "tags": ["peel", "platform", "main-heal", "high-ground"],
        "strengths": ["ライフグリップで味方を無敵に近い状態で救う", "花台で高所を作る"],
        "weaknesses": ["攻撃力が低くプレッシャーが弱い", "ダイブの初動を止めにくい"],
        "abilities": [
            ("Healing Blossom", "ヒーリングブロッサム", "チャージ回復"),
            ("Petal Platform", "ペタルプラットフォーム", "上昇台"),
            ("Life Grip", "ライフグリップ", "味方引き上げ"),
        ],
        "ult": ("Tree of Life", "生命の樹"),
    },
    "lucio": {
        "hp": 250, "range": "close",
        "tags": ["speed", "brawl", "boop", "mobile", "aura"],
        "strengths": ["スピードでブロウルを成立させる", "環境キルと壁走り"],
        "weaknesses": ["遠距離ポーク戦", "個の火力不足"],
        "abilities": [
            ("Sonic Amplifier", "ソニックアンプ", "音波弾"),
            ("Soundwave", "サウンドウェーブ", "ブープ"),
            ("Crossfade", "クロスフェード", "回復／速度オーラ"),
        ],
        "ult": ("Sound Barrier", "サウンドバリア"),
    },
    "mauga": {
        "hp": 500, "range": "close",
        "tags": ["brawl", "tankbuster", "sustain", "cage", "fire"],
        "strengths": ["二丁機関銃で近距離を溶かす", "ケージで1vs1を強制"],
        "weaknesses": ["アナのアンチとスリープ", "ファラなど空中"],
        "abilities": [
            ("Incendiary Chaingun", "焼夷チェインガン", "炎上機関銃"),
            ("Overrun", "オーバーラン", "突進ストンプ"),
            ("Cardiac Overdrive", "オーバードライブ", "与ダメ回復オーラ"),
        ],
        "ult": ("Cage Fight", "ケージファイト"),
    },
    "mei": {
        "hp": 250, "range": "close",
        "tags": ["freeze", "wall", "anti-dive", "choke", "self-sustain"],
        "strengths": ["壁でダイブを分断", "スローでタンクを殴り殺す"],
        "weaknesses": ["長射程", "壁を焼かれるポーク"],
        "abilities": [
            ("Endothermic Blaster", "冷凍ブラスター", "スロー噴射＋氷柱"),
            ("Cryo-Freeze", "クライオフリーズ", "無敵回復"),
            ("Ice Wall", "アイスウォール", "地形壁"),
        ],
        "ult": ("Blizzard", "ブリザード"),
    },
    "mercy": {
        "hp": 250, "range": "mid",
        "tags": ["damage-boost", "rez", "mobile", "flyer-synergy", "main-heal"],
        "strengths": ["ダメージブーストでキャリーを伸ばす", "リザレクト"],
        "weaknesses": ["単独生存力が低くフォーカスされる", "アンチヒール"],
        "abilities": [
            ("Caduceus Staff", "カドゥケウス・スタッフ", "回復／攻撃強化"),
            ("Guardian Angel", "ガーディアンエンジェル", "味方へ飛行"),
            ("Resurrect", "リザレクト", "蘇生"),
        ],
        "ult": ("Valkyrie", "ヴァルキリー"),
    },
    "mizuki": {
        "hp": 250, "range": "mid",
        "tags": ["aggressive-support", "cc", "anti-flyer", "projectile"],
        "strengths": ["バインディングチェーンで空中を落とす", "攻撃的サポートとして前線に出られる"],
        "weaknesses": ["メインヒールが安定しにくい", "純粋ダイブの集中"],
        "abilities": [
            ("Spirit Glaive", "スピリットグレイブ", "跳弾刃"),
            ("Healing Kasa", "ヒーリングカサ", "回復帽子ブーメラン"),
            ("Binding Chain", "バインディングチェーン", "空中を接地させる鎖"),
        ],
        "ult": ("Kekkai Sanctuary", "結界サンクチュアリ"),
    },
    "moira": {
        "hp": 250, "range": "close",
        "tags": ["fade", "drain", "brawl", "anti-flank", "self-sustain", "beam"],
        "strengths": ["フェードで生存", "ビームはディフレクト無効でゲンジに強い"],
        "weaknesses": ["長射程と高精度ヒットスキャン", "アンチヒール"],
        "abilities": [
            ("Biotic Grasp", "バイオティックグラスプ", "回復／吸収ビーム"),
            ("Biotic Orb", "バイオティックオーブ", "回復／ダメージ球"),
            ("Fade", "フェード", "無敵移動"),
        ],
        "ult": ("Coalescence", "コアレッセンス"),
    },
    "orisa": {
        "hp": 275, "range": "mid",
        "tags": ["anti-dive", "cc", "brawl", "fortify", "spear"],
        "strengths": ["フォルティファイでCC無効", "ジャベリンでダイブを止める"],
        "weaknesses": ["ザリアのビームとバブル", "ハックとアンチヒール"],
        "abilities": [
            ("Augmented Fusion Driver", "フュージョンドライバー", "過熱機関砲"),
            ("Energy Javelin", "エナジャベリン", "スタン投槍"),
            ("Fortify", "フォルティファイ", "CC無効＋軽減"),
            ("Javelin Spin", "ジャベリンスピン", "弾消し回転"),
        ],
        "ult": ("Terra Surge", "テラクサージ"),
    },
    "pharah": {
        "hp": 250, "range": "mid",
        "tags": ["flyer", "splash", "high-ground", "mobile"],
        "strengths": ["頭上から盾と近接を無効化", "マーシーとのフォマシー"],
        "weaknesses": ["ヒットスキャン全員", "閉鎖空間"],
        "abilities": [
            ("Rocket Launcher", "ロケットランチャー", "爆発ロケット"),
            ("Jump Jet", "ジャンプジェット", "上昇"),
            ("Concussive Blast", "コンカッシブブラスト", "ノックバック"),
        ],
        "ult": ("Barrage", "バレッジ"),
    },
    "ramattra": {
        "hp": 450, "range": "mid",
        "tags": ["brawl", "poke", "barrier", "pull"],
        "strengths": ["ネメシスで近接を支配", "ボルテックスでフライヤーを落とす"],
        "weaknesses": ["アナと長射程", "ザリアビーム"],
        "abilities": [
            ("Void Accelerator", "ヴォイドアクセラレータ", "投射スタッフ"),
            ("Void Barrier", "ヴォイドバリア", "設置盾"),
            ("Nemesis Form", "ネメシスフォーム", "近接形態"),
            ("Ravenous Vortex", "ヴォルテックス", "引き下ろし"),
        ],
        "ult": ("Annihilation", "アナイアレーション"),
    },
    "reaper": {
        "hp": 250, "range": "close",
        "tags": ["tankbuster", "flank", "close", "self-sustain"],
        "strengths": ["ショットガンでタンクを溶かす", "レイスで離脱"],
        "weaknesses": ["空中と長射程", "CC連鎖"],
        "abilities": [
            ("Hellfire Shotguns", "ヘルファイアショットガン", "二丁散弾"),
            ("Shadow Step", "シャドウステップ", "テレポート"),
            ("Wraith Form", "レイスフォーム", "無敵移動"),
        ],
        "ult": ("Death Blossom", "デスブロッサム"),
    },
    "reinhardt": {
        "hp": 425, "range": "melee",
        "tags": ["barrier", "brawl", "choke", "melee", "shatter"],
        "strengths": ["巨大盾でチョークを押す", "アースシャターの集団CC"],
        "weaknesses": ["ファラ／ジャンクラット／バスティオン", "盾を無視するビーム"],
        "abilities": [
            ("Rocket Hammer", "ロケットハンマー", "近接ハンマー"),
            ("Charge", "チャージ", "突進"),
            ("Fire Strike", "ファイアストライク", "火の波動"),
            ("Barrier Field", "バリアフィールド", "大盾"),
        ],
        "ult": ("Earthshatter", "アースシャター"),
    },
    "roadhog": {
        "hp": 700, "range": "close",
        "tags": ["hook", "anti-dive", "tankbuster", "self-sustain"],
        "strengths": ["フックでダイバーとサポを処刑", "単体バースト"],
        "weaknesses": ["アナのアンチ", "ファラと長射程"],
        "abilities": [
            ("Scrap Gun", "スクラップガン", "散弾／中距離爆発"),
            ("Chain Hook", "チェーンフック", "引き寄せ"),
            ("Take a Breather", "テイクアブリーザー", "自己回復＋軽減"),
        ],
        "ult": ("Whole Hog", "ホールホッグ"),
    },
    "shion": {
        "hp": 250, "range": "close",
        "tags": ["flank", "mobile", "close", "burst"],
        "strengths": ["バイク機動力で側面を取る", "近距離バースト"],
        "weaknesses": ["CCとタレット", "長射程"],
        "abilities": [
            ("Kira Pistols", "キラピストル", "速射アニマ弾"),
            ("Evade", "イベイド", "ダッシュ＋オーバーHP"),
            ("Joyride", "ジョイライド", "バイク投擲機動"),
        ],
        "ult": ("Satsuriku Spree", "サツリクスプリー"),
    },
    "sierra": {
        "hp": 250, "range": "mid",
        "tags": ["hitscan", "mobile", "mid-range", "drone"],
        "strengths": ["ドローングラップルの機動力", "トラッキングショットで追撃"],
        "weaknesses": ["純スナイプに負ける", "至近フランカー"],
        "abilities": [
            ("Helix Rifle", "ヘリックスライフル", "収束エネルギー弾"),
            ("Tracking Shot", "トラッキングショット", "自動照準マーク"),
            ("Anchor Drone", "アンカードローン", "グラップル"),
        ],
        "ult": ("Trailblazer", "トレイルブレイザー"),
    },
    "sigma": {
        "hp": 350, "range": "long",
        "tags": ["poke", "barrier", "anti-projectile", "cc", "rock"],
        "strengths": ["遠距離ハイパースフィア", "キネティックグラスプで弾を盾に"],
        "weaknesses": ["ビームとソンブラ", "至近ダイブ"],
        "abilities": [
            ("Hyperspheres", "ハイパースフィア", "重力弾"),
            ("Kinetic Grasp", "キネティックグラスプ", "弾吸収"),
            ("Accretion", "アクリーション", "岩スタン"),
            ("Experimental Barrier", "実験バリア", "遠隔盾"),
        ],
        "ult": ("Gravitic Flux", "グラビティックフラックス"),
    },
    "sojourn": {
        "hp": 250, "range": "long",
        "tags": ["hitscan", "rail", "poke", "mobile"],
        "strengths": ["レールガンのワンタップ", "スライドで高所"],
        "weaknesses": ["ダイブ", "閉鎖チョーク"],
        "abilities": [
            ("Railgun", "レールガン", "溜め狙撃"),
            ("Power Slide", "パワースライド", "スライドジャンプ"),
            ("Disruptor Shot", "ディスラプター", "減速フィールド"),
        ],
        "ult": ("Overclock", "オーバークロック"),
    },
    "soldier-76": {
        "hp": 250, "range": "mid",
        "tags": ["hitscan", "self-heal", "sprint", "mid-range"],
        "strengths": ["安定したヒットスキャンと自己回復", "フライヤー対策の万能"],
        "weaknesses": ["特別な勝ち筋が薄い", "超高機動フランカー"],
        "abilities": [
            ("Heavy Pulse Rifle", "パルスライフル", "フルオート"),
            ("Sprint", "スプリント", "走り"),
            ("Biotic Field", "バイオティックフィールド", "設置回復"),
            ("Helix Rockets", "ヘリックスロケット", "直撃爆発"),
        ],
        "ult": ("Tactical Visor", "タクティカルバイザー"),
    },
    "sombra": {
        "hp": 250, "range": "close",
        "tags": ["hack", "flank", "emp", "anti-ability", "stealth"],
        "strengths": ["ハックでダイブタンクとバスティオンを止める", "EMPで盾と能力を破壊"],
        "weaknesses": ["トールビョーン／ブリギッテのアンチフランカー", "ハンゾーのワンショット"],
        "abilities": [
            ("Machine Pistol", "マシンピストル", "近距離SMG"),
            ("Hack", "ハック", "能力封じ"),
            ("Stealth", "ステルス", "透明"),
            ("Translocator", "トランスローケーター", "TPビーコン"),
        ],
        "ult": ("EMP", "EMP"),
    },
    "symmetra": {
        "hp": 225, "range": "close",
        "tags": ["beam", "teleporter", "bunker", "turret", "anti-barrier"],
        "strengths": ["ビームが盾とD.Vaに強い", "TPで奇襲"],
        "weaknesses": ["長射程ヒットスキャン", "範囲攻撃でタレット一掃"],
        "abilities": [
            ("Photon Projector", "フォトンプロジェクター", "強化ビーム"),
            ("Sentry Turret", "セントリー", "スロータレット"),
            ("Teleporter", "テレポーター", "瞬間移動門"),
        ],
        "ult": ("Photon Barrier", "フォトンバリア"),
    },
    "torbjorn": {
        "hp": 250, "range": "mid",
        "tags": ["bunker", "turret", "anti-flank", "armor"],
        "strengths": ["タレットでフランカーを監視", "溶岩でエリア拒否"],
        "weaknesses": ["盾持ちの正面突破とファラ", "ソンブラ以外の長射程破壊"],
        "abilities": [
            ("Rivet Gun", "リベットガン", "リベット／散弾"),
            ("Deploy Turret", "タレット", "自動砲台"),
            ("Overload", "オーバーロード", "強化"),
        ],
        "ult": ("Molten Core", "モルテンコア"),
    },
    "tracer": {
        "hp": 175, "range": "close",
        "tags": ["flank", "dive", "mobile", "pulse"],
        "strengths": ["バックライン崩壊", "リコールでミスを帳消し"],
        "weaknesses": ["キャスディ／トール／ブリギッテ", "フックとスリープ"],
        "abilities": [
            ("Pulse Pistols", "パルスピストル", "連射"),
            ("Blink", "ブリンク", "短距離TP"),
            ("Recall", "リコール", "時間巻き戻し"),
        ],
        "ult": ("Pulse Bomb", "パルスボム"),
    },
    "vendetta": {
        "hp": 250, "range": "melee",
        "tags": ["melee", "flank", "deflect", "close", "anti-barrier"],
        "strengths": ["剣で盾を割るアルティメット", "近接ディフレクト"],
        "weaknesses": ["射程とピール", "空中"],
        "abilities": [
            ("Palatine Fang", "パラタインファング", "3段剣撃"),
            ("Warding Stance", "ワーディングスタンス", "ガード＋近接跳ね返し"),
            ("Soaring Slice", "ソアリングスライス", "剣投擲追従"),
        ],
        "ult": ("Sundering Blade", "サンダリングブレイド"),
    },
    "venture": {
        "hp": 250, "range": "close",
        "tags": ["dive", "burrow", "close", "mobile"],
        "strengths": ["地中無敵でダイブイン", "バンカー崩し"],
        "weaknesses": ["CC待ちとアンチヒール", "空中"],
        "abilities": [
            ("Smart Excavator", "エクスカベーター", "地震チャージ"),
            ("Drill Dash", "ドリルダッシュ", "突進"),
            ("Burrow", "バロウ", "地中潜伏"),
        ],
        "ult": ("Tectonic Shock", "テクトニックショック"),
    },
    "widowmaker": {
        "hp": 200, "range": "long",
        "tags": ["sniper", "hitscan", "long-range", "grappling"],
        "strengths": ["ワンタップでバックラインを消す", "長視線マップの支配"],
        "weaknesses": ["ウィンストン／D.Va／ゲンジ／ソンブラ", "狭いマップ"],
        "abilities": [
            ("Widow's Kiss", "ウィドウズキス", "スナイパー／アサルト"),
            ("Grappling Hook", "グラップリングフック", "移動"),
            ("Venom Mine", "ヴェノムマイン", "毒罠"),
        ],
        "ult": ("Infra-Sight", "インフラサイト"),
    },
    "winston": {
        "hp": 475, "range": "close",
        "tags": ["dive", "beam", "anti-sniper", "mobile", "bubble"],
        "strengths": ["スナイプとガラスサポをダイブで潰す", "ビームはディフレクト無効"],
        "weaknesses": ["リーパー／ホッグ／バスティオン／メイ", "アンチヒール"],
        "abilities": [
            ("Tesla Cannon", "テスラキャノン", "範囲ビーム"),
            ("Jump Pack", "ジャンプパック", "跳躍"),
            ("Barrier Projector", "バリアドーム", "ドーム盾"),
        ],
        "ult": ("Primal Rage", "プライマルレイジ"),
    },
    "wrecking-ball": {
        "hp": 450, "range": "close",
        "tags": ["dive", "disrupt", "mobile", "mines"],
        "strengths": ["編成を崩壊させるピールドライバー", "機動力でポイントを掻き乱す"],
        "weaknesses": ["ハックとフック", "メイの壁とジャンクラット"],
        "abilities": [
            ("Grappling Claw", "グラップリングクロー", "振り子"),
            ("Piledriver", "パイルドライバー", "着地打ち上げ"),
            ("Adaptive Shield", "アダプティブシールド", "周囲人数で盾"),
        ],
        "ult": ("Minefield", "マインフィールド"),
    },
    "wuyang": {
        "hp": 250, "range": "mid",
        "tags": ["projectile", "peel", "knockback", "heal"],
        "strengths": ["操作オーブのライン切り", "タイダルブラストでダイブを返す"],
        "weaknesses": ["ヒール量がメインヒーラーに劣る", "至近集中砲火"],
        "abilities": [
            ("Xuanwu Staff", "玄武スタッフ", "操作水弾"),
            ("Restorative Stream", "レストレイティブストリーム", "持続回復"),
            ("Tidal Blast", "タイダルブラスト", "盾爆発ノックダウン"),
        ],
        "ult": ("Guardian Blast", "ガーディアンブラスト"),
    },
    "zarya": {
        "hp": 250, "range": "close",
        "tags": ["bubble", "beam", "anti-dive", "grav"],
        "strengths": ["バブルでダイブを無効化しチャージ", "ビームはマトリックス無効"],
        "weaknesses": ["チャージが低いと火力不足", "長射程ポーク"],
        "abilities": [
            ("Particle Cannon", "パーティクルキャノン", "ビーム／爆発弾"),
            ("Particle Barrier", "自己バブル", "ダメージ吸収"),
            ("Projected Barrier", "味方バブル", "ダメージ吸収"),
        ],
        "ult": ("Graviton Surge", "グラビトンサージ"),
    },
    "zenyatta": {
        "hp": 225, "range": "mid",
        "tags": ["discord", "poke", "glass", "projectile"],
        "strengths": ["ディスコードでタンクを溶かす", "トランスでアルティメットを打ち消す"],
        "weaknesses": ["ダイブに極端に弱い", "移動スキルがない"],
        "abilities": [
            ("Orb of Destruction", "破壊のオーブ", "弾／チャージ"),
            ("Orb of Discord", "不和のオーブ", "被ダメ増加"),
            ("Orb of Harmony", "調和のオーブ", "遠隔回復"),
        ],
        "ult": ("Transcendence", "超越"),
    },
}

# A counters B (1-5). Sparse expert overrides.
MATCHUPS = {
    "winston": {"widowmaker": 5, "hanzo": 4, "ashe": 3, "sojourn": 3, "zenyatta": 5, "torbjorn": 3, "illari": 4, "ana": 3, "freja": 4, "sierra": 3},
    "dva": {"pharah": 4, "echo": 4, "junkrat": 4, "hanzo": 3, "ana": 3, "tracer": 3, "zenyatta": 3, "baptiste": 3, "freja": 3, "juno": 3, "jetpack-cat": 3},
    "reinhardt": {"reaper": 2, "cassidy": 2, "soldier-76": 2, "mei": 2, "brigitte": 3},
    "orisa": {"doomfist": 4, "winston": 3, "tracer": 3, "genji": 3, "wrecking-ball": 4, "venture": 3, "shion": 3},
    "zarya": {"dva": 4, "winston": 4, "doomfist": 4, "genji": 4, "tracer": 3, "wrecking-ball": 3, "hazard": 3, "dmon": 3},
    "roadhog": {"tracer": 4, "genji": 3, "doomfist": 4, "wrecking-ball": 4, "winston": 3, "venture": 3, "zenyatta": 4, "ana": 2},
    "sigma": {"pharah": 3, "hanzo": 3, "junkrat": 3, "ashe": 2, "baptiste": 2, "freja": 3},
    "ramattra": {"pharah": 3, "echo": 3, "juno": 3, "reinhardt": 3, "brigitte": 3},
    "junker-queen": {"reinhardt": 3, "ramattra": 3, "moira": 3, "lucio": 3, "reaper": 2},
    "doomfist": {"zenyatta": 4, "widowmaker": 3, "ashe": 3, "ana": 3, "illari": 3, "sojourn": 3},
    "wrecking-ball": {"widowmaker": 4, "zenyatta": 4, "illari": 3, "ashe": 3, "hanzo": 3, "ana": 2},
    "mauga": {"reinhardt": 4, "winston": 3, "dva": 2, "ramattra": 3, "dmon": 3},
    "hazard": {"reinhardt": 3, "sigma": 3, "zenyatta": 3, "ana": 2, "widowmaker": 3},
    "domina": {"reinhardt": 4, "sigma": 3, "widowmaker": 3, "ashe": 3, "hanzo": 3, "orisa": 3},
    "dmon": {"reaper": 3, "cassidy": 2, "soldier-76": 2, "brigitte": 3, "mei": 2, "zenyatta": 2},
    "widowmaker": {"pharah": 4, "echo": 4, "mercy": 4, "juno": 5, "jetpack-cat": 4, "ana": 3, "ashe": 3, "sigma": 3, "domina": 3, "dmon": 4},
    "ashe": {"pharah": 5, "echo": 4, "mercy": 4, "juno": 4, "jetpack-cat": 4, "dmon": 4, "reinhardt": 3, "mauga": 3},
    "cassidy": {"pharah": 4, "echo": 3, "tracer": 4, "genji": 3, "venture": 3, "shion": 3, "mercy": 3},
    "soldier-76": {"pharah": 4, "echo": 3, "mercy": 3, "juno": 3, "jetpack-cat": 3, "bastion": 2},
    "sojourn": {"pharah": 4, "echo": 4, "mercy": 3, "sigma": 3, "orisa": 3, "juno": 4},
    "hanzo": {"pharah": 2, "bastion": 3, "orisa": 3, "roadhog": 3, "ana": 3},
    "genji": {"hanzo": 4, "widowmaker": 4, "zenyatta": 4, "ana": 3, "baptiste": 3, "sigma": 3, "domina": 3},
    "tracer": {"widowmaker": 4, "zenyatta": 5, "ana": 4, "ashe": 3, "hanzo": 3, "illari": 3},
    "pharah": {"reinhardt": 5, "dmon": 5, "mei": 4, "reaper": 5, "junkrat": 3, "brigitte": 4, "symmetra": 4, "vendetta": 5, "anran": 3, "bastion": 4, "torbjorn": 3},
    "echo": {"reinhardt": 4, "dmon": 4, "zarya": 3, "reaper": 4, "brigitte": 4, "mei": 3},
    "reaper": {"winston": 5, "dva": 4, "roadhog": 3, "mauga": 4, "ramattra": 3, "dmon": 4, "orisa": 3},
    "sombra": {"winston": 4, "wrecking-ball": 5, "dva": 3, "doomfist": 4, "bastion": 5, "illari": 3, "lifeweaver": 3, "domina": 4, "mauga": 3, "hazard": 3},
    "mei": {"winston": 4, "dva": 3, "doomfist": 4, "genji": 4, "tracer": 3, "reinhardt": 3, "venture": 4},
    "junkrat": {"reinhardt": 4, "orisa": 3, "sigma": 3, "dmon": 3, "torbjorn": 3, "bastion": 2},
    "bastion": {"reinhardt": 5, "orisa": 4, "sigma": 4, "dmon": 4, "roadhog": 3, "mauga": 3},
    "torbjorn": {"tracer": 4, "genji": 3, "sombra": 4, "venture": 3, "shion": 3, "dmon": 3},
    "symmetra": {"dva": 4, "winston": 3, "reinhardt": 3, "orisa": 3, "genji": 3},
    "venture": {"bastion": 4, "torbjorn": 3, "reinhardt": 3, "orisa": 3, "zenyatta": 3},
    "freja": {"pharah": 2, "orisa": 3, "sigma": 3, "ana": 3, "baptiste": 2},
    "vendetta": {"reinhardt": 4, "dmon": 3, "orisa": 3, "sigma": 3, "brigitte": 2},
    "anran": {"reinhardt": 3, "ramattra": 3, "moira": 3, "lucio": 3, "brigitte": 2},
    "emre": {"pharah": 3, "echo": 3, "juno": 3, "mercy": 3, "bastion": 2},
    "shion": {"zenyatta": 4, "ana": 3, "widowmaker": 3, "ashe": 2, "illari": 3},
    "sierra": {"pharah": 3, "echo": 3, "tracer": 2, "genji": 2, "juno": 3},
    "ana": {"orisa": 4, "mauga": 5, "roadhog": 4, "winston": 4, "dva": 3, "ramattra": 4, "doomfist": 4, "wrecking-ball": 3, "dmon": 3, "junker-queen": 4},
    "baptiste": {"pharah": 3, "echo": 3, "soldier-76": 2, "reaper": 3, "mauga": 2},
    "brigitte": {"tracer": 5, "genji": 4, "sombra": 3, "reaper": 3, "venture": 3, "shion": 4, "anran": 3, "vendetta": 3},
    "kiriko": {"ana": 3, "junker-queen": 4, "cassidy": 2, "sombra": 2, "mauga": 3},
    "lucio": {"reinhardt": 3, "junker-queen": 3, "ramattra": 3, "dmon": 3, "mauga": 2},
    "mercy": {"pharah": 4, "echo": 4, "ashe": 3, "soldier-76": 3, "sojourn": 3, "freja": 3},
    "moira": {"genji": 4, "tracer": 3, "sombra": 3, "winston": 2, "reaper": 2, "anran": 3},
    "zenyatta": {"orisa": 4, "mauga": 4, "roadhog": 3, "sigma": 3, "dmon": 4, "reinhardt": 3, "domina": 3},
    "illari": {"pharah": 3, "echo": 2, "winston": 2, "reinhardt": 2},
    "lifeweaver": {"doomfist": 3, "genji": 2, "tracer": 2, "pharah": 2},
    "juno": {"reinhardt": 3, "dmon": 3, "winston": 2, "lucio": 2},
    "jetpack-cat": {"reinhardt": 3, "dmon": 3, "mei": 2, "reaper": 3},
    "mizuki": {"pharah": 4, "echo": 4, "juno": 4, "jetpack-cat": 4, "mercy": 3},
    "wuyang": {"doomfist": 3, "winston": 3, "dva": 2, "reaper": 2, "genji": 2},
}

TAG_MATCHUPS = [
    {"a": "hitscan", "b": "flyer", "score": 4, "ja": "ヒットスキャンで空中ヒーローを落とす", "en": "Hitscan deletes flyers"},
    {"a": "flyer", "b": "melee", "score": 4, "ja": "近接の頭上を取り、盾を無効化する", "en": "Outranges melee and ignores shields"},
    {"a": "flyer", "b": "brawl", "score": 3, "ja": "ブロウル編成の頭上から一方的に撃てる", "en": "Pokes brawl comps from above"},
    {"a": "beam", "b": "barrier", "score": 3, "ja": "ビームはバリアを効率よく削る", "en": "Beams melt barriers"},
    {"a": "beam", "b": "deflect", "score": 3, "ja": "ビームはディフレクトできない", "en": "Beams ignore Deflect"},
    {"a": "beam", "b": "matrix", "score": 3, "ja": "ビームはマトリックスを貫通する", "en": "Beams pierce Defense Matrix"},
    {"a": "hack", "b": "dive", "score": 4, "ja": "ハックでダイブの機動力を止める", "en": "Hack shuts down dive mobility"},
    {"a": "hack", "b": "mech", "score": 3, "ja": "ハックでメカの能力を封じる", "en": "Hack disables mech tools"},
    {"a": "hack", "b": "bunker", "score": 4, "ja": "ハックでタレット／変形を止める", "en": "Hack collapses bunker setups"},
    {"a": "antiheal", "b": "self-sustain", "score": 4, "ja": "アンチヒールで自己回復タンクを無力化", "en": "Anti-heal guts sustain tanks"},
    {"a": "antiheal", "b": "brawl", "score": 3, "ja": "近接回復勝負をアンチで終わらせる", "en": "Anti-heal wins brawl heal wars"},
    {"a": "cc", "b": "dive", "score": 3, "ja": "CCでダイブの着地を罰する", "en": "CC punishes dive landings"},
    {"a": "sleeper", "b": "dive", "score": 4, "ja": "スリープでダイバーを完全停止", "en": "Sleep completely stops divers"},
    {"a": "flank", "b": "sniper", "score": 4, "ja": "側面からスナイパーを潰す", "en": "Flankers collapse snipers"},
    {"a": "flank", "b": "glass", "score": 4, "ja": "ガラスキャノンを暗殺する", "en": "Assassinates glass cannons"},
    {"a": "flank", "b": "long-range", "score": 3, "ja": "長射程の死角に入り込む", "en": "Gets into long-range blind spots"},
    {"a": "sniper", "b": "flyer", "score": 3, "ja": "長射程で空をワンタップできる", "en": "Long range one-taps flyers"},
    {"a": "anti-flank", "b": "flank", "score": 4, "ja": "フランカーを専用ツールで追放する", "en": "Peels flankers with dedicated tools"},
    {"a": "anti-dive", "b": "dive", "score": 4, "ja": "ダイブに対する専用回答", "en": "Built to punish dive"},
    {"a": "matrix", "b": "projectile", "score": 3, "ja": "マトリックスで投射物を消す", "en": "Matrix eats projectiles"},
    {"a": "matrix", "b": "spam", "score": 4, "ja": "爆弾とグレネードを無効化", "en": "Deletes spam damage"},
    {"a": "bubble", "b": "dive", "score": 3, "ja": "バブルでダイブのバーストを無効化", "en": "Bubbles negate dive burst"},
    {"a": "tankbuster", "b": "barrier", "score": 2, "ja": "近距離火力でタンクを溶かす", "en": "Close-range tank melting"},
    {"a": "choke", "b": "barrier", "score": 2, "ja": "チョークで盾を通過できないようにする", "en": "Choke control vs shields"},
    {"a": "freeze", "b": "dive", "score": 4, "ja": "スローと壁でダイブを分断", "en": "Slow and wall split dive"},
    {"a": "boop", "b": "melee", "score": 2, "ja": "近接を崖と距離で制御", "en": "Boops control melee spacing"},
    {"a": "speed", "b": "brawl", "score": 2, "ja": "スピードでブロウルの着地を合わせる", "en": "Speed enables brawl engages"},
    {"a": "cleanse", "b": "antiheal", "score": 3, "ja": "浄化でアンチヒールと創傷を消す", "en": "Cleanse removes anti-heal and wounds"},
    {"a": "immortality", "b": "burst", "score": 3, "ja": "ランプでバーストキルを拒否", "en": "Lamp denies burst kills"},
    {"a": "discord", "b": "brawl", "score": 3, "ja": "ディスコードで硬い対象を溶かす", "en": "Discord melts bulky targets"},
    {"a": "anti-flyer", "b": "flyer", "score": 4, "ja": "空中を強制落地・撃墜する", "en": "Grounds and deletes flyers"},
    {"a": "turret", "b": "flank", "score": 3, "ja": "タレットが側面を監視する", "en": "Turrets watch flanks"},
    {"a": "burrow", "b": "bunker", "score": 3, "ja": "地中からバンカーを崩す", "en": "Burrow collapses bunker"},
    {"a": "anti-barrier", "b": "barrier", "score": 3, "ja": "盾を無視または貫通する", "en": "Ignores or breaks barriers"},
]


def build_heroes():
    out = []
    for h in heroes_api:
        key = h["key"]
        meta = HERO_META.get(key)
        if not meta:
            raise SystemExit(f"missing meta for {key}")
        cds = HERO_CDS.get(key, {})
        abilities = []
        for a in meta["abilities"]:
            abilities.append({
                "name": a[0],
                "nameJa": a[1],
                "desc": a[2],
                "cd": cds.get(a[0], ""),
            })
        ult_cd = cds.get(meta["ult"][0], "ULT")
        out.append({
            "key": key,
            "name": h["name"],
            "nameJa": NAME_JA[key],
            "role": h["role"],
            "subrole": h.get("subrole") or "",
            "portrait": f"assets/heroes/{key}.png",
            "hp": meta["hp"],
            "range": meta["range"],
            "tags": meta["tags"],
            "strengths": meta["strengths"],
            "weaknesses": meta["weaknesses"],
            "abilities": abilities,
            "ult": {"name": meta["ult"][0], "nameJa": meta["ult"][1], "cd": ult_cd},
            "cds": cds,
            "play": HERO_PLAY.get(key, ""),
        })
    return out


COMPETITIVE_MODES = {
    "control", "escort", "hybrid", "push", "flashpoint", "clash"
}


def build_maps():
    out = []
    skip = {
        "practice-range", "workshop-chamber", "workshop-expanse",
        "workshop-green-screen", "workshop-island",
    }
    for m in maps_api:
        key = m["key"]
        if key in skip:
            continue
        modes = m.get("gamemodes") or []
        traits, note = MAP_TRAITS.get(key, (["open"], "標準的な構成が通りやすいマップ。"))
        shot = f"assets/maps/{key}.jpg"
        if not (ROOT / shot).exists():
            shot = ""
        coach = get_coach(key) or {
            "layout": note,
            "points": [],
            "attack": "本線より高所と側面を先に取る。",
            "defend": "チョークのこちら側で人数を揃える。",
            "move": "カートやポイントより『次の角の所有』を優先する。",
            "callouts": [],
        }
        out.append({
            "key": key,
            "name": m["name"],
            "nameJa": MAP_JA.get(key, m["name"]),
            "modes": modes,
            "modeJa": [MODE_JA.get(x, x) for x in modes],
            "location": m.get("location") or "",
            "screenshot": shot,
            "traits": traits,
            "noteJa": note,
            "coach": coach,
            "competitive": any(x in COMPETITIVE_MODES for x in modes),
        })
    out.sort(key=lambda x: (not x["competitive"], x["modes"][:1], x["name"]))
    return out


def main():
    data = {
        "version": "2026-season-4",
        "rosterSize": len(heroes_api),
        "heroes": build_heroes(),
        "maps": build_maps(),
        "matchups": MATCHUPS,
        "tagMatchups": TAG_MATCHUPS,
        "roles": [
            {"key": "tank", "name": "Tank", "nameJa": "タンク", "color": "#f99e1a"},
            {"key": "damage", "name": "Damage", "nameJa": "ダメージ", "color": "#f64e54"},
            {"key": "support", "name": "Support", "nameJa": "サポート", "color": "#3ce0a0"},
        ],
        "traitLabels": {
            "choke": {"ja": "チョーク", "en": "Choke"},
            "highground": {"ja": "高所", "en": "High ground"},
            "longsight": {"ja": "長視線", "en": "Long sightlines"},
            "vertical": {"ja": "垂直", "en": "Vertical"},
            "open": {"ja": "開放", "en": "Open"},
            "flank": {"ja": "側面", "en": "Flanks"},
            "environmental": {"ja": "環境キル", "en": "Environmental"},
            "close": {"ja": "近接", "en": "Close quarters"},
            "payload": {"ja": "ペイロード", "en": "Payload"},
            "control": {"ja": "コントロール", "en": "Control"},
            "brawl": {"ja": "ブロウル", "en": "Brawl"},
            "push": {"ja": "プッシュ", "en": "Push"},
            "flashpoint": {"ja": "フラッシュポイント", "en": "Flashpoint"},
            "clash": {"ja": "クラッシュ", "en": "Clash"},
        },
    }
    dest = ROOT / "js" / "data.js"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "/* Overwatch 2 knowledge base — generated, do not edit by hand */\n"
        "window.OW = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    bot_dest = ROOT / "bot" / "knowledge.json"
    bot_dest.parent.mkdir(parents=True, exist_ok=True)
    bot_dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", dest, "heroes", len(data["heroes"]), "maps", len(data["maps"]))
    print("wrote", bot_dest)


if __name__ == "__main__":
    main()
