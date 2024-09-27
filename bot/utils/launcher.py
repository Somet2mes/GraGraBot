import os
import glob
import asyncio
import argparse
from itertools import cycle
import random
from pyrogram import Client
from better_proxy import Proxy
from asyncio import Semaphore

from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.registrator import register_sessions

start_text = """
```
   ____            ____           ____        _   
  / ___|_ __ __ _ / ___|_ __ __ _| __ )  ___ | |_ 
 | |  _| '__/ _` | |  _| '__/ _` |  _ \ / _ \| __|
 | |_| | | | (_| | |_| | | | (_| | |_) | (_) | |_ 
  \____|_|  \__,_|\____|_|  \__,_|____/ \___/ \__|
                                                  
```
Select an action:

    1. Run clicker
    2. Create session
"""

global tg_clients


def get_session_names() -> list[str]:
    session_names = sorted(glob.glob("sessions/*.session"))
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names


def get_proxies() -> list[Proxy]:
    if settings.USE_PROXY_FROM_FILE:
        with open(file="bot/config/proxies.txt", encoding="utf-8-sig") as file:
            proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file]
    else:
        proxies = []

    return proxies


async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2"]:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 1:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)

    elif action == 2:
        await register_sessions()




async def run_tasks(tg_clients: list[Client]):
    proxies = get_proxies()
    proxies_cycle = cycle(proxies) if proxies else None
    tasks = []
    import os
    if os.path.exists('stat.json'):
        with open('stat.json', 'r') as f:
            stat = f.read()
    else:
        stat = None
        
        
    semaphore = Semaphore(20)

    async def run_tapper_with_semaphore(tg_client, proxy):
        async with semaphore:
            if tg_client.name in stat:
                logger.info(f"{tg_client.name} | Already registered")
                return
            await run_tapper(tg_client=tg_client, proxy=proxy)

    for i, tg_client in enumerate(tg_clients):
        proxy = random.choice(proxies) if proxies else None
        task = asyncio.create_task(run_tapper_with_semaphore(tg_client, proxy))
        tasks.append(task)
    await asyncio.gather(*tasks)
    
    
    # for i, tg_client in enumerate(tg_clients):
    #     # 添加一个小的延迟，每个任务间隔 0.5 秒启动
    #     await asyncio.sleep(0.1)
    #     if tg_client.name in stat:
    #         logger.info(f"{tg_client.name} | Already registered")
    #         continue

    #     else:
    #         task = asyncio.create_task(
    #             run_tapper(
    #                 tg_client=tg_client,
    #                  proxy=random.choice(proxies) if proxies else None,
    #             # proxy=next(proxies_cycle) if proxies_cycle else None )
    #         ))
    #         tasks.append(task)
    #     if (i + 1) % 10 == 0:
    #         await asyncio.sleep(1)
        # 每启动 5 个任务，额外等待 2 秒


    # await asyncio.gather(*tasks)
