import asyncio
import discord
import youtube_dl

from discord.ext import commands

youtube_dl.utils.bug_reports_message = lambda: ''

bot = commands.Bot(command_prefix='!')

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # ipv4, ipv6 can have issues
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.command()
async def play(ctx, url):
    vc = ctx.voice_client
    if vc is None:
        return

    if vc.is_playing():
        return await ctx.send('Already playing audio.')

    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    vc.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
    await ctx.send('Now playing: {}'.format(player.title))

@bot.command()
async def join(ctx):
    channel = ctx.author.voice.channel

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(channel)

    await channel.connect()
    
@bot.command()
async def leave(ctx):
    vc = ctx.voice_client
    if vc is not None:
        await vc.disconnect()

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc is not None and vc.is_playing():
        vc.pause()

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc is not None and vc.is_paused():
        vc.resume()


with open('token.txt') as f:
    token = f.read()

bot.run(token)
