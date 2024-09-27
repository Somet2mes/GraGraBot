import asyncio
import string
import sys
import random
import traceback

import aiohttp
import json
import re
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from urllib.parse import unquote, quote

from faker import Faker
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession

from .headers import headers
from .agents import generate_random_user_agent
from eth_account import Account
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def get_proxies() -> list[Proxy]:
    if settings.USE_PROXY_FROM_FILE:
        with open(file="bot/config/proxies.txt", encoding="utf-8-sig") as file:
            proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file]
    else:
        proxies = []

    return proxies
def address_to_base62(address: str) -> str:
    if not re.match(r'^0x[0-9a-fA-F]{40}$', address):
        raise ValueError("Invalid Ethereum address format")
    
    decimal = int(address[2:], 16)
    result = ""
    while decimal > 0:
        result = BASE62[decimal % 62] + result
        decimal //= 62
    
    return result.zfill(27)  # Pad to 27 characters

def base62_to_address(base62: str) -> str:
    if not re.match(r'^[0-9A-Za-z]{27}$', base62):
        raise ValueError("Invalid Base62 string format")
    
    decimal = 0
    for char in base62:
        decimal = decimal * 62 + BASE62.index(char)
    
    hex_address = hex(decimal)[2:].zfill(40)
    return f"0x{hex_address}"

class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.start_param = None
        self.url = 'https://api.onetime.dog'

        # self.session_ug_dict = self.load_user_agents() or []

        # headers['User-Agent'] = self.check_user_agent()
        headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')
    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | User agent saved successfully")

            return user_agent_str
    def generate_wallet(self):
        # Generate a random mnemonic (24 words by default)
        mnemonic = Bip39MnemonicGenerator().FromWordsNumber(words_num=12)
        
        # Generate seed from mnemonic
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
        
        # Generate BIP44 master key
        bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
        
        # Derive the first account
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        
        # Derive the external chain
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        
        # Derive the first address index
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0)
        
        # Get the private key
        priv_key = bip44_addr_ctx.PrivateKey().Raw().ToBytes()
        
        # Create Ethereum account from private key
        account = Account.from_key(priv_key)
        
        return {
            'address': account.address,
            'private_key': account._private_key.hex(),
            'mnemonic': mnemonic.ToStr()
        }
    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def get_gra_hash(self, http_client: aiohttp.ClientSession,address):
        url = "https://wl-api.gra.fun/api/hash_addr"
        payload = "{\"sign\":\"\",\"referrer\":\""+"0xc2FF3997A1Bc7dB020a8b95A6C0B228dEaaDE064"+"\",\"wallet_name\":\"OKX Wallet\",\"wallet_address\":\""+address+"\"}\n"

        response = await http_client.post(url, data=payload)
        if response.status not in (200, 201):
            return None
        resp = await response.json()
        try:
            return resp['hashed_wallet_address']
        except:
            return None
    async def check_youtube(self,http_client: aiohttp.ClientSession,address):

        url = "https://wl-api.gra.fun/api/check_youtube/"+address

        payload = {}
        response = await http_client.post(url, data=payload)
        if response.status ==200:
            return True
        else:
            return False
    async def check_address_status(self,http_client: aiohttp.ClientSession,address):
        url = "https://wl-api.gra.fun/api/status/"+address
        response = await http_client.get(url)
        '''
        response={
            "user_id": 347076672,
            "wallet_address": "0x77331dbe4432a164d536b84371de7d97af63ffea",
            "user_referrer": "",
            "wallet_connected": true,
            "tg_bot_connected": true,
            "user_tg_customization": true,
            "tg_channel_sub": true,
            "twitter_sub": true,
            "youtube_sub": true,
            "bnb_task_activated": false,
            "bnb_points": 0,
            "bnb_points_per_hour": "0",
            "bnb_points_multiplier": 0,
            "offchain_points": 900,
            "invited_people": 0
        }
        '''
        if response.status ==200:
            resp = await response.json()
            try:
                offchain_points=resp.get('offchain_points')
                return address,offchain_points
            except:
                return address,None
        else:
            return address,None
        
            # with open('stat.json', 'a') as f:
            #     if resp['user_id']  not in f.read():
            #     else:
            #         json.dump(resp, f, indent=4)

    
    async def get_tg_web_data(self, proxy: str | None, http_client: aiohttp.ClientSession) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme="socks5",
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict
        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    with open('error.txt', 'a') as error_file:
                        error_file.write(f"{self.session_name} | Invalid Session\n")
                    raise InvalidSession(self.session_name)
            
            registered = False
            me = await self.tg_client.get_me()
            user_id = me.id
            with open("user_id.json","a") as f:
                f.write(str(user_id)+'-'+self.session_name+"\n")
            first_name = me.first_name
            user_id=str(user_id)
            with open("sum.txt","r") as f:
                all=f.read()
            if user_id in all:
                logger.info(f"{self.session_name}|{user_id}|Already registered")
                return
            if not registered :
                wallet = self.generate_wallet()
                with open("wallet.json","a") as f:
                    f.write(str(wallet)+"\n")
                print(str(wallet))
                wallet_address = wallet['address']
                logger.info(f"{self.session_name}| {first_name}")
                if "🐤" not in first_name:
                    await self.tg_client.update_profile(first_name=f"🐤{first_name} Gra-Gra")
                    await asyncio.sleep(1)
                    await self.tg_client.join_chat("grafunmeme")
                gra_hash = await self.get_gra_hash(http_client=http_client,address=wallet_address)
                await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")
                await asyncio.sleep(1)
                await self.check_youtube(http_client=http_client,address=wallet_address)
                await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")

                await asyncio.sleep(1)
                await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")

                await asyncio.sleep(2)
                await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")
                await asyncio.sleep(1)
                address,offchain_points = await self.check_address_status(http_client=http_client,address=wallet_address)
                await self.tg_client.update_profile(first_name=f"{first_name}")
                if offchain_points == None:
                    await asyncio.sleep(1)
                    await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")
                    address,offchain_points = await self.check_address_status(http_client=http_client,address=wallet_address)
                else:
                    if offchain_points == 400:
                        logger.info(f"{self.session_name}| {first_name}")
                        await self.tg_client.send_message("GraFunBot",f"/start {gra_hash}")

                    if int(offchain_points) == 800:
                        await self.check_youtube(http_client=http_client,address=wallet_address)
                        address,offchain_points = await self.check_address_status(http_client=http_client,address=wallet_address)
                if offchain_points is not None and offchain_points != 400:
                    logger.info(f"{self.session_name} | {address} | {offchain_points}")
                    with open('stat.json', 'a') as f:
                        f.write(f"{self.session_name} | {address} | {offchain_points}\n")
            
        except FloodWait as fl:
            logger.warning(f"{self.session_name} | FloodWait {fl}")
            fls = fl.value
            logger.info(f"{self.session_name} | Sleep {fls}s")
            return

        except InvalidSession as error:
            raise error
        except UserDeactivated as error:
            with open('error.txt', 'a') as error_file:
                error_file.write(f"{self.session_name} | User Deactivated\n")
            raise error
        
        except Exception as error:
            if "401 USER_DEACTIVATED_BAN" in str(error):
                with open('error.txt', 'a') as error_file:
                    error_file.write(f"{self.session_name} | User Deactivated\n")
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            logger.error(f"{self.session_name} | {traceback.format_exc()}")
            await asyncio.sleep(delay=3)
        finally:
            await self.tg_client.disconnect()

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy, attempt: int = 1) -> None:
        if attempt > 3:
            logger.error(f"{self.session_name} | Max proxy check attempts reached. Unable to find a working proxy.")
            return 

        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            proxies = get_proxies()
            if proxies:
                new_proxy = random.choice(proxies)
                logger.info(f"{self.session_name} | New Proxy: {new_proxy} | Attempt: {attempt}")
                await self.check_proxy(http_client=http_client, proxy=new_proxy, attempt=attempt + 1)
            else:
                logger.error(f"{self.session_name} | No proxies available")

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            proxy_check = await self.check_proxy(http_client=http_client, proxy=proxy)
        try:
            tg_web_data = await self.get_tg_web_data(proxy=proxy, http_client=http_client)
        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error: {error}")
            await asyncio.sleep(delay=3)
        finally:
            await http_client.close()

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
