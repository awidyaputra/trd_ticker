from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import ToolContext, FunctionTool, agent_tool

from dotenv import load_dotenv
import os

from . import prompt

from functools import partial
import asyncio
import aiohttp
from aiohttp import ClientSession

load_dotenv()
FMP_API_KEY = os.getenv("FMP_API_KEY")


async def fetch_peers(session: ClientSession, ticker: str):
    params = {"symbol": ticker, "apikey": FMP_API_KEY}
    async with session.get(
        "https://financialmodelingprep.com/stable/stock-peers", params=params
    ) as resp:
        # TODO: handle exception
        peers = await resp.json()
        return peers


def sort_peers(peers):
    return sorted(peers, key=lambda p: p["price"], reverse=True)


async def fetch_profile(session: ClientSession, ticker: str):
    params = {"symbol": ticker, "apikey": FMP_API_KEY}
    async with session.get(
        "https://financialmodelingprep.com/stable/profile", params=params
    ) as resp:
        # TODO: handle exception
        profile = await resp.json()
        return profile[0]


async def fetch_top_peers_profile(session: ClientSession, ticker: str):
    peers = await fetch_peers(session, ticker)
    sorted_peers = sort_peers(peers)

    # Note: Only fetch profile for top 3 companies based on price
    partial_coroutines = [
        partial(fetch_profile, session, peer["symbol"]) for peer in sorted_peers[:3]
    ]
    coroutines = [coro() for coro in partial_coroutines]

    try:
        out = await asyncio.wait_for(asyncio.gather(*coroutines), 10)
    except asyncio.TimeoutError:
        print("time up")

    return out


async def fetch_curr_price(session: ClientSession, ticker: str):
    params = {"symbol": ticker, "apikey": FMP_API_KEY}
    async with session.get(
        "https://financialmodelingprep.com/stable/quote", params=params
    ) as resp:
        # TODO: handle exception
        quote = await resp.json()
        return quote[0]["price"]


async def fetch_company(session: ClientSession, ticker: str):
    params = {"query": ticker, "apikey": FMP_API_KEY}
    async with session.get(
        "https://financialmodelingprep.com/stable/search-symbol", params=params
    ) as resp:
        # TODO: handle exception
        symbol = await resp.json()
        return symbol[0]


async def fetch_competition(ticker: str, tool_context: ToolContext):
    if "company" not in tool_context.state:
        tool_context.state["company"] = {"name": "", "ticker": ticker, "exchange": ""}
    if "curr_price" not in tool_context.state:
        tool_context.state["curr_price"] = ""
    if "peers" not in tool_context.state:
        tool_context.state["peers"] = []

    async with aiohttp.ClientSession() as session:
        try:
            out = await asyncio.wait_for(
                asyncio.gather(
                    fetch_company(session, ticker),
                    fetch_curr_price(session, ticker),
                    fetch_top_peers_profile(session, ticker),
                ),
                10,
            )
            tool_context.state["company"]["exchange"] = out[0]["exchange"]
            tool_context.state["curr_price"] = out[1]
            tool_context.state["peers"] = out[2]
        except asyncio.TimeoutError:
            print("time up")


market_report_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="market_report_agent",
    description="Create a market report based on market data",
    instruction=prompt.SUMMARIZE_PROMPT,
)

market_peer_fetcher_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="market_peer_fetcher_agent",
    description="Fetch the latest market data and summarize it",
    instruction=prompt.FETCH_PROMPT,
    tools=[FunctionTool(fetch_competition)],
)

market_competition_agent = SequentialAgent(
    name="market_competition_agent",
    description="Answer questions on detailed data or competition of company or ticker",
    sub_agents=[market_peer_fetcher_agent, market_report_agent],
)


async def fetch_latest_exchange(session: ClientSession):
    params = {"apikey": FMP_API_KEY}
    async with session.get(
        "https://financialmodelingprep.com/stable/all-exchange-market-hours",
        params=params,
    ) as resp:
        # TODO: handle exception
        exchanges = await resp.json()
        return exchanges


async def fetch_ticker_exchange(ticker: str, tool_context: ToolContext):
    if "all_exchange" not in tool_context.state:
        tool_context.state["all_exchange"] = []
    if "open_exchange" not in tool_context.state:
        tool_context.state["open_exchange"] = []
    if "company" not in tool_context.state:
        tool_context.state["company"] = {"name": "", "ticker": ticker, "exchange": ""}

    tool_context.state["company"]["ticker"] = {"ticker": ticker}

    async with aiohttp.ClientSession() as session:
        try:
            out = await asyncio.wait_for(
                asyncio.gather(
                    fetch_company(session, ticker), fetch_latest_exchange(session)
                ),
                10,
            )
            tool_context.state["company"]["exchange"] = out[0]["exchange"]
            tool_context.state["company"]["name"] = out[0]["name"]
            tool_context.state["all_exchange"] = out[1]

            open_exchange = list(filter(lambda ex: ex["isMarketOpen"], out[1]))
            tool_context.state["open_exchange"] = open_exchange

            for ex in open_exchange:
                if out[0] == ex["exchange"]:
                    return {
                        "exchange": out[0],
                        "isExchangeOpen": True,
                    }
            return {"exchange": out[0], "isExchangeOpen": False}

        except asyncio.TimeoutError:
            print("time up")


fetch_exchange_ticker_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="fetch_exchange_ticker_agent",
    description="Answer questions about latest exchange information given a ticker",
    instruction=prompt.FETCH_EXCHANGE_TICKER_PROMPT,
    tools=[FunctionTool(fetch_ticker_exchange)],
)


async def fetch_exchange(tool_context: ToolContext):
    if "all_exchange" not in tool_context.state:
        tool_context.state["all_exchange"] = []
    if "open_exchange" not in tool_context.state:
        tool_context.state["open_exchange"] = []

    async with aiohttp.ClientSession() as session:
        try:
            out = await asyncio.wait_for(
                asyncio.gather(fetch_latest_exchange(session)),
                10,
            )
            tool_context.state["all_exchange"] = out[0]
            open_exchange = list(filter(lambda ex: ex["isMarketOpen"], out[0]))
            tool_context.state["open_exchange"] = open_exchange

            return {"open_exchange": open_exchange, "all_exchange": out[0]}

        except asyncio.TimeoutError:
            print("time up")


fetch_exchange_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="fetch_exchange_agent",
    description="Answer questions about exchange information only without ticker",
    instruction=prompt.FETCH_EXCHANGE_PROMPT,
    tools=[FunctionTool(fetch_exchange)],
)


market_fetcher_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="market_fetcher_agent",
    description="Answer queries on latest market information and latest exchange information",
    instruction=prompt.MARKET_FETCHER_PROMPT,
    sub_agents=[
        market_competition_agent,
        fetch_exchange_ticker_agent,
        fetch_exchange_agent,
    ],
)
