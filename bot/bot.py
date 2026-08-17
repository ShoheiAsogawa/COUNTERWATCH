#!/usr/bin/env python3
"""COUNTERWATCH Discord bot — paste a scoreboard, get anti-picks with hero images."""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from bot.engine import (  # noqa: E402
    HEROES,
    cd_lines,
    map_shot_path,
    movement_lines,
    parse_text,
    portrait_path,
    recommend,
)
from bot.tactics import fight_plan, plan_embed_body  # noqa: E402
from bot.updater import sync_from_github  # noqa: E402
from bot.vision import read_scoreboard  # noqa: E402

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "").strip()
LISTEN_ALL = os.getenv("DISCORD_LISTEN_ALL", "1").strip() not in ("0", "false", "no")
OWNER_IDS = {
    int(x.strip())
    for x in os.getenv("DISCORD_OWNER_IDS", "").split(",")
    if x.strip().isdigit()
}
CHANNEL_FILTER = [
    x.strip().lower()
    for x in os.getenv("DISCORD_CHANNEL_NAMES", "counterwatch,アンチ,overwatch,ow").split(",")
    if x.strip()
]
SYNC_EVERY = max(30, int(os.getenv("GITHUB_SYNC_SECONDS", "180")))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=("!cw ", "!CW "), intents=intents)
prefs = defaultdict(lambda: {"role": "damage", "side": "flex"})


def invite_url() -> str:
    cid = CLIENT_ID or "YOUR_CLIENT_ID"
    perms = 2147593216
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={cid}&permissions={perms}&scope=bot%20applications.commands"
    )


def should_listen(message: discord.Message) -> bool:
    if LISTEN_ALL:
        return True
    name = (message.channel.name or "").lower()
    return any(n in name for n in CHANNEL_FILTER)


def merge_parse(caption: str, ocr: str, user_id: int, board: dict | None = None) -> dict:
    cap = parse_text(caption)
    vis = parse_text(ocr)
    board = board or {}
    p = prefs[user_id]
    role = cap["role"] or board.get("role") or vis["role"] or p["role"]
    if cap["side"] != "flex":
        side = cap["side"]
    elif board.get("side") in ("attack", "defend"):
        side = board["side"]
    else:
        side = vis["side"] if vis["side"] != "flex" else p["side"]
    map_key = cap["map_key"] or board.get("map_key") or vis["map_key"]
    if cap["hero_keys"]:
        heroes = cap["hero_keys"][:5]
    elif len(board.get("enemies") or []) >= 2:
        heroes = board["enemies"][:5]
    else:
        heroes = vis["hero_keys"]
        if len(heroes) >= 8:
            heroes = heroes[-5:]
        else:
            heroes = heroes[:5]
    p["role"] = role
    p["side"] = side
    return {
        "role": role,
        "side": side,
        "map_key": map_key,
        "enemies": heroes,
        "allies": board.get("allies") or [],
        "self_key": board.get("self_key"),
        "layout": board.get("layout"),
    }


def build_reply(state: dict) -> tuple[discord.Embed, list[discord.Embed], list[discord.File]]:
    rec = recommend(state["role"], state["enemies"], state["map_key"], state["side"])
    mp = rec["map"]
    picks = rec["picks"]
    enemies = rec["comp"]["heroes"]
    files: list[discord.File] = []
    used_names = set()

    def attach(path: Path, name: str) -> str | None:
        if not path.exists() or name in used_names:
            return None
        used_names.add(name)
        files.append(discord.File(path, filename=name))
        return f"attachment://{name}"

    role_ja = {"tank": "タンク", "damage": "ダメージ", "support": "サポート"}[state["role"]]
    side_ja = {"attack": "攻撃", "defend": "防衛", "flex": "フレックス"}[state["side"]]
    enemy_txt = " · ".join(h["nameJa"] for h in enemies) or "（編成が読めませんでした）"
    self_h = HEROES.get(state.get("self_key") or "")
    ally_keys = state.get("allies") or []
    tank_n = sum(1 for k in ally_keys if HEROES.get(k, {}).get("role") == "tank")
    queue_note = "オープンキュー編成（タンクが2人）" if tank_n >= 2 else ""

    main = discord.Embed(
        title="COUNTERWATCH",
        color=0xF99E1A,
        description="TABスクショの上段＝味方・下段＝敵として読み、今の立ち回りを返します。",
    )
    if mp:
        main.add_field(
            name="🗺️ マップの読み",
            value="\n".join(
                x for x in [
                    f"**{mp['nameJa']}**（{' / '.join(mp.get('modeJa') or mp.get('modes') or [])}）",
                    (mp.get("coach") or {}).get("layout") or mp.get("noteJa") or "",
                    *(((mp.get("coach") or {}).get("points") or [])[:3]),
                    (mp.get("coach") or {}).get("move") or "",
                ]
                if x
            )[:1024],
            inline=False,
        )
        shot = map_shot_path(mp["key"])
        url = attach(shot, "map.jpg")
        if url:
            main.set_thumbnail(url=url)

    you = f"あなたは **{self_h['nameJa']}**（{role_ja}）" if self_h else f"{role_ja} / {side_ja}"
    bits = [f"**{rec['comp_label']}**　{you}"]
    if queue_note:
        bits.append(queue_note)
    bits.append(enemy_txt)
    bits.append(rec["weakness"])
    main.add_field(
        name="敵の勝ち筋",
        value="\n".join(bits)[:1024],
        inline=False,
    )

    if enemies:
        cds = cd_lines(enemies)
        if cds:
            main.add_field(name="数えるクールタイム", value="\n".join(cds)[:1024], inline=False)

    extras: list[discord.Embed] = []
    plan = fight_plan(state.get("self_key"), state["map_key"], state["side"], state["enemies"], pick_hero=(picks[0]["hero"] if picks else None))
    if plan.get("where") or plan.get("threats"):
        hero = plan.get("hero")
        img = attach(portrait_path(hero["key"]), f"{hero['key']}.png") if hero else None
        fight = discord.Embed(
            title=f"こう戦え — {plan['title']}",
            description=plan_embed_body(plan),
            color=0x3CE0A0,
        )
        if img:
            fight.set_thumbnail(url=img)
        extras.append(fight)

    if picks:
        top = picks[0]
        h = top["hero"]
        # Already playing this hero: skip "switch to X" as the lead card.
        if not state.get("self_key") or h["key"] != state.get("self_key"):
            img = attach(portrait_path(h["key"]), f"{h['key']}.png")
            move = movement_lines(h, rec, state["side"])
            specs = [f"HP {h.get('hp')}"]
            for a in (h.get("abilities") or []):
                if a.get("cd"):
                    specs.append(f"{a['nameJa']} {a['cd']}")
            body = "\n".join(
                [
                    f"**{h['nameJa']}**（{h['name']}）  `{top['score']}`",
                    *top["reasons"][:3],
                    "",
                    "**こう動け**",
                    *[f"• {x}" for x in move],
                    "",
                    " / ".join(specs[:5]),
                ]
            )[:4096]
            title = "乗り換え候補" if state.get("self_key") else "今出すヒーロー"
            pick_embed = discord.Embed(title=title, description=body, color=0xF99E1A)
            if img:
                pick_embed.set_image(url=img)
            extras.append(pick_embed)

        for i, row in enumerate(picks[1:3], start=2):
            hh = row["hero"]
            if hh["key"] == state.get("self_key"):
                continue
            thumb = attach(portrait_path(hh["key"]), f"{hh['key']}.png")
            e = discord.Embed(
                title=f"{i}. {hh['nameJa']}",
                description=f"{hh['name']}　`{row['score']}`\n{row['reasons'][0] if row['reasons'] else ''}"[:2048],
                color=0x5865F2,
            )
            if thumb:
                e.set_thumbnail(url=thumb)
            extras.append(e)
    elif not extras:
        main.add_field(
            name="ヒント",
            value="ヒーローが読めませんでした。TAB画面全体を送るか、キャプションに `dps route66 wrecking-ball genji ashe mercy juno` のように書いて再投稿してください。",
            inline=False,
        )

    main.set_footer(text="ロール変更は /role　例: /role tank")
    return main, extras, files


async def reply_analysis(destination, state: dict, mention: discord.Message | None = None):
    main, extras, files = build_reply(state)
    kwargs = {"embeds": [main, *extras][:10], "files": files[:10]}
    if mention is not None:
        await mention.reply(**kwargs)
    else:
        await destination.send(**kwargs)


def can_reload(user: discord.abc.User, guild: discord.Guild | None) -> bool:
    if user.id in OWNER_IDS:
        return True
    if isinstance(user, discord.Member) and user.guild_permissions.administrator:
        return True
    if guild and guild.owner_id == user.id:
        return True
    return not OWNER_IDS and not guild


@tasks.loop(seconds=180)
async def github_sync():
    try:
        msg = await sync_from_github(pull_code=True)
        print("[github]", msg)
    except Exception as exc:
        print("[github] fail", exc)


@github_sync.before_loop
async def before_github_sync():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    github_sync.change_interval(seconds=SYNC_EVERY)
    if not github_sync.is_running():
        github_sync.start()
    try:
        boot = await sync_from_github(pull_code=False)
        print("[github] boot", boot)
    except Exception as exc:
        print("[github] boot fail", exc)
    await bot.tree.sync()
    print(f"logged in as {bot.user}")
    print("invite:", invite_url())
    print(f"github sync every {SYNC_EVERY}s")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    images = [
        a
        for a in message.attachments
        if (a.content_type or "").startswith("image/") or a.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    mentioned = bot.user and bot.user.mentioned_in(message)
    if not images:
        return
    if not (mentioned or should_listen(message)):
        return

    await message.channel.typing()
    data = await images[0].read()
    board = read_scoreboard(data)
    caption = message.clean_content or ""
    state = merge_parse(caption, board.get("ocr_text") or "", message.author.id, board)
    if not state["enemies"] and not state["map_key"]:
        await message.reply(
            "画像は受け取った。TABのスコアボード（味方上が青・敵下が赤）が画面に入っているか確認してほしい。"
            "読めないときはキャプションにマップと敵を書いて再投稿して。\n"
            "例: `dps route66 wrecking-ball genji ashe mercy juno`"
        )
        return
    await reply_analysis(message.channel, state, mention=message)


@bot.tree.command(name="role", description="自分のロールを覚える（tank / damage / support）")
@app_commands.describe(role="今プレイするロール")
@app_commands.choices(
    role=[
        app_commands.Choice(name="Tank", value="tank"),
        app_commands.Choice(name="Damage", value="damage"),
        app_commands.Choice(name="Support", value="support"),
    ]
)
async def slash_role(interaction: discord.Interaction, role: app_commands.Choice[str]):
    prefs[interaction.user.id]["role"] = role.value
    await interaction.response.send_message(f"ロールを **{role.name}** にした。次のスクショからこれを使う。", ephemeral=True)


@bot.tree.command(name="side", description="攻撃 / 防衛 / フレックス")
@app_commands.choices(
    side=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Defend", value="defend"),
        app_commands.Choice(name="Flex", value="flex"),
    ]
)
async def slash_side(interaction: discord.Interaction, side: app_commands.Choice[str]):
    prefs[interaction.user.id]["side"] = side.value
    await interaction.response.send_message(f"サイドを **{side.name}** にした。", ephemeral=True)


@bot.tree.command(name="counter", description="マップと敵ヒーローからアンチピック（画像つき）")
@app_commands.describe(
    screenshot="TAB / スコアボードのスクショ",
    text="例: gibraltar pharah mercy reinhardt lucio brigitte",
)
async def slash_counter(
    interaction: discord.Interaction,
    screenshot: discord.Attachment | None = None,
    text: str | None = None,
):
    await interaction.response.defer()
    board: dict = {}
    if screenshot is not None:
        data = await screenshot.read()
        board = read_scoreboard(data)
    state = merge_parse(text or "", board.get("ocr_text") or "", interaction.user.id, board)
    if not state["enemies"] and not state["map_key"]:
        await interaction.followup.send(
            "編成が読めない。スクショを付けるか、`text` にヒーロー名を書いて。"
        )
        return
    main, extras, files = build_reply(state)
    await interaction.followup.send(embeds=[main, *extras][:10], files=files[:10])


@bot.tree.command(name="reload", description="GitHub の最新 knowledge.json を取り込み直す（チャットは切断しない）")
async def slash_reload(interaction: discord.Interaction):
    if not can_reload(interaction.user, interaction.guild):
        await interaction.response.send_message("管理者だけが実行できる。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        msg = await sync_from_github(pull_code=True)
        await interaction.followup.send(msg, ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"更新に失敗した: {exc}", ephemeral=True)


@bot.command(name="role")
async def prefix_role(ctx: commands.Context, role: str):
    key = role.lower()
    mapping = {"tank": "tank", "dps": "damage", "damage": "damage", "sup": "support", "support": "support", "タンク": "tank", "ダメージ": "damage", "サポート": "support"}
    if key not in mapping:
        await ctx.reply("tank / dps / support で指定して。")
        return
    prefs[ctx.author.id]["role"] = mapping[key]
    await ctx.reply(f"ロールを {mapping[key]} にした。")


def main():
    if not TOKEN:
        print("DISCORD_BOT_TOKEN がありません。.env を見てください。")
        print("invite:", invite_url())
        raise SystemExit(1)
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
