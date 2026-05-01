import discord
import json
from discord.ext import commands, tasks
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

handler = CacheFileHandler(cache_path=".cache")
cache_content = os.getenv("spotify_cache")
if cache_content and not os.path.exists(".cache"):
    with open(".cache", "w") as f:
        f.write(cache_content)

bot_token = os.getenv("bot_token")
channel_id = int(os.getenv("channel_id"))
spotify_client_id = os.getenv("spotify_client_id")
spotify_client_secret = os.getenv("spotify_client_secret")
spotify_redirect_uri = os.getenv("spotify_redirect_uri")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id, client_secret=spotify_client_secret,
    redirect_uri=spotify_redirect_uri, scope="playlist-modify-public playlist-modify-private", open_browser = False, cache_handler = handler), requests_timeout = 30)
spotify_check = "https://open.spotify.com/track/"


try:
    with open("submissions_list.json", "r") as f:
        submissions_list = json.load(f)
except FileNotFoundError:
    submissions_list = []
    
    

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    monthly_reset.start()
    print(f"Bot is online! Logged in as {bot.user}")
    
@bot.command()
async def submit(ctx, url: str):
    if url.startswith(spotify_check):
        for i in submissions_list:
            if url == i['url']:
                await ctx.send(f"<@{ctx.author.id}> submission failed. Duplicate song.")
                break
        else:
            track_id = url.removeprefix("https://open.spotify.com/track/").split("?")[0]
            try:   
                sp.track(track_id)
            except:
                await ctx.send(f"<@{ctx.author.id}> Invalid Spotify Link. Please Try Again.")
                return
            submissions_list.append({ "user": ctx.author.name, "user_id": ctx.author.id, "url": url})
            await ctx.send(f"Added <@{ctx.author.id}>'s Submission.")
            
            with open("submissions_list.json", "w") as f:
                json.dump(submissions_list, f)
    else:
        await ctx.send(f"<@{ctx.author.id}> submission failed. Please submit a Spotify link.")

@bot.command()
async def remove(ctx, url: str):
    for i in submissions_list:
        if i["user_id"] == ctx.author.id and i["url"] == url:
            submissions_list.remove(i)
            
            with open("submissions_list.json", "w") as f:
                json.dump(submissions_list, f)
        
            await ctx.send(f"<@{ctx.author.id}>'s Submissions Sucessfully Removed")
            break
    else:
        await ctx.send("You don't have a submission to remove.")
@bot.command()
async def submissions(ctx):
    if len(submissions_list) == 0:
        await ctx.send("There are currently no submissions in the list.")
    else:
        for i in submissions_list:
            track_id = i["url"].removeprefix("https://open.spotify.com/track/").split("?")[0]
            track_key = sp.track(track_id)
            songtitleartist = discord.Embed(title = f"{track_key['name']} - {track_key['artists'][0]['name']}")
            songtitleartist.set_image(url = track_key["album"]["images"][0]["url"])
            songtitleartist.set_footer(text = f"Submitted by {i['user']}")
            await ctx.send(embed=songtitleartist)

        
@bot.command()
@commands.has_any_role("eboard", "leadership", "advisor", "scary")
async def reset(ctx):
    with open("submissions_list.json",  "w") as f:
        submissions_list.clear()
        json.dump(submissions_list, f)  
    await ctx.send(f"Submissions successfully reset.")

    
@bot.command()
@commands.has_any_role("eboard", "leadership", "advisor", "scary")
async def makeplaylist(ctx):
    last_month = (datetime.now() - timedelta(days = 1)).strftime("Musicheads %B %Y")
    songs_of_month = []
    playlist = sp.current_user_playlist_create(last_month, public = True, collaborative = False, description ="Musicheads' Favorite Songs of the Month")
    for i in submissions_list:
        song = i["url"].removeprefix("https://open.spotify.com/track/").split("?")[0]
        songs_of_month.append(song)
    sp.playlist_add_items(playlist["id"], songs_of_month)
    
    await ctx.send(f'Success! Playlist can be found at {playlist["external_urls"]["spotify"]}')

@tasks.loop(hours=24)
async def monthly_reset():
    last_month = (datetime.now() - timedelta(days = 1)).strftime("Musicheads %B %Y")
    if datetime.now().day == 1:
        if len(submissions_list) == 0:
            channel = bot.get_channel(channel_id)
            await channel.send("No submissions this month :(. Skipping playlist creation.")
            return
        channel = bot.get_channel(channel_id)
        songs_of_month = []
        playlist = sp.current_user_playlist_create(last_month, public = True, collaborative = False, description ="Musicheads' Favorite Songs of the Month")
        for i in submissions_list:
            song = i["url"].removeprefix("https://open.spotify.com/track/").split("?")[0]
            songs_of_month.append(song)
        sp.playlist_add_items(playlist["id"], songs_of_month)
        
        with open("submissions_list.json",  "w") as f:
            submissions_list.clear()
            json.dump(submissions_list, f)
    
        await channel.send(f'Success! Playlist can be found at {playlist["external_urls"]["spotify"]}')
        
bot.run(bot_token)
