#!/usr/bin/python3

import discord
from discord.ext import commands
import asyncio
import aiohttp
import functools
import random


PREFIX = "!"
MAX_IMG = 5

bot = commands.Bot(command_prefix=PREFIX, description="Test description.")


# {"command_name": command_func, ...}
commands = {}  # Initialized lower down, after all the functions 

session = None  # aiohttp.ClientSession()


@bot.event
async def on_ready():
    print("--- Ready ---")


@bot.event
async def on_connect():
    global session
    session = aiohttp.ClientSession(skip_auto_headers=["User-Agent"],
                                    headers={"User-Agent": "Linux:reddit-image-discord-bot:0 (by /u/makeworld)"})


@bot.event
async def on_disconnect():
    await session.close()


@bot.command(name='r')
async def process_commands(ctx, *args):
    """All commands start here."""

    if args == [] or args[0].strip() == "":
        await ctx.send("A command is needed.")
        return

    if args[0] in commands.keys():
        # It's a command that already exists, so call it
        func = commands[args[0]]
        await func(ctx, args)  # Give it all the args except the command's name
        return
    
    # The user wants a subreddit image
    await subreddit_image(ctx, args)  # Include subreddit name and possible other args


async def subreddit_image(ctx, args):
    subreddit = args[0]
    sort = "hot"
    n = 1
    og_n = 1
    # Check if there's a different sort specified
    if len(args) == 2:
        if args[1].lower() in ["top", "hot", "rising", "new"]:
            sort = args[1].lower()
        elif args[1].isdigit():
            # They specified a number, not a sort
            og_n = int(args[1])
            n = sorted((0, int(args[1]), MAX_IMG))[1]
        else:
            await ctx.send(f"Unrecognized sort/number: {args[1]}")
            return

    # Check number of posts asked for
    if len(args) == 3:
        try:
            # Clamp the value to 5
            og_n = int(args[2])
            n = sorted((0, int(args[2]), MAX_IMG))[1]
        except ValueError:
            pass
    
    # Check subreddit exists
    async with session.get("https://www.reddit.com/r/" + subreddit + "/" + sort + "/.json?raw_json=1&count=200", allow_redirects=False) as resp:
        if resp.status != 200:
            await ctx.send(f"{subreddit} is not a valid and public subreddit")
            return

        # Find image url
        data = await resp.json()
        urls = []
        titles = []
        links = []
        for post in data["data"]["children"]:
            try:
                if post["data"]["post_hint"] == "image" and post["data"]["over_18"] != True:
                    urls.append(post["data"]["preview"]["images"][0]["source"]["url"])
                    titles.append(post["data"]["title"])
                    links.append("https://www.reddit.com" + post["data"]["permalink"])
            except KeyError:
                # Maybe a mod post or something, move on
                continue

        if len(urls) == 0:
            await ctx.send(f"No SFW images found on the front page with sort {sort}")
            return

        # Sent multiple images, as the user asked for
        for i in range(0, n):
            if len(urls) == 0:
                break

            choice = random.randrange(0, len(urls))
            embed = discord.Embed(title=titles[choice], url=links[choice])
            embed.set_image(url=urls[choice])
            await ctx.send(embed=embed)
            # Remove that image so no duplicates are sent
            urls.pop(choice)
            titles.pop(choice)
            links.pop(choice)
        if og_n > MAX_IMG:
            await ctx.send(f"This bot will only send {MAX_IMG} images at a time.")


async def ping(ctx, args):
    await ctx.send(f"Latency: {bot.latency}")


async def _help(ctx, args):
    await ctx.send("Subreddit syntax: `!r subreddit [top|hot|rising|new] [1-5]`\nLatency: `!r ping`\nExamples:\n```\n!r pics\n!r pics new\n!r pics 3\n!r pics top 2\n```")


commands = {"ping": ping, "help": _help}

# Read token from file, so it's not stored in public code
f = open("token", 'r')
token = f.readline().strip()
f.close()
bot.run(token)
