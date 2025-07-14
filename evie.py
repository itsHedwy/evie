import os, discord, logging, re, random
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
STAGE_CHANNEL_ID = int(os.getenv("STAGE_CHANNEL_ID"))
STAGE_TOPIC = os.getenv("STAGE_TOPIC", "?")
REACT_CHANNEL_ID = int(os.getenv("REACT_CHANNEL_ID", 0))
EMOJIS = ["<:icon_ivy:1098557226093908029>"]
REACT_CHANCE = 0.1

intents = discord.Intents.all()
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

bot = commands.Bot(command_prefix="@", intents=intents)
created: dict[int, discord.VoiceChannel] = {}
user_rooms: dict[int, int] = {}
name_pat = re.compile(r"^комната .+")

@bot.event
async def on_ready():
    stage = bot.get_channel(STAGE_CHANNEL_ID)
    if not isinstance(stage, discord.StageChannel):
        return

    for ch in stage.guild.voice_channels:
        if ch.category == stage.category and name_pat.match(ch.name):
            if ch.members:
                created[ch.id] = ch
                for m in ch.members:
                    if not m.bot:
                        user_rooms[m.id] = ch.id
            else:
                await ch.delete()

    try:
        await stage.fetch_instance()
    except discord.NotFound:
        await stage.create_instance(topic=STAGE_TOPIC, send_start_notification=False)
    await stage.connect()
    await stage.guild.me.edit(suppress=False)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    stage = bot.get_channel(STAGE_CHANNEL_ID)
    if after.channel == stage and before.channel != stage:
        if member.id in user_rooms:
            return
        vc = await stage.guild.create_voice_channel(name=f"комната {member.display_name}", category=stage.category)
        created[vc.id] = vc
        user_rooms[member.id] = vc.id
        await member.move_to(vc)
    if before.channel and before.channel.id in created and len(before.channel.members) == 0:
        await created.pop(before.channel.id).delete()
        user_rooms.pop(member.id, None)
    # Delete channels after every move
    if after.channel and after.channel.category == stage.category:
        for ch in list(stage.category.voice_channels):
            if len(ch.members) == 0:
#            if name_pat.match(ch.name) and len(ch.members) == 0:
                await ch.delete()
                created.pop(ch.id, None)
                for uid, cid in list(user_rooms.items()):
                    if cid == ch.id:
                        user_rooms.pop(uid)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id == REACT_CHANNEL_ID and random.random() < REACT_CHANCE:
        await message.add_reaction(random.choice(EMOJIS))
    await bot.process_commands(message)


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)