from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools import agent_tool

import os
from dotenv import load_dotenv

from . import prompt

import aiohttp
import asyncio

from agent_ticker.sub_agents.query_ticker.agent import query_ticker_agent
from agent_ticker.sub_agents.market_fetcher.agent import market_fetcher_agent


stock_market_info_aggregator = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="stock_market_info_aggregator",
    description=("Answer questions about latest market data."),
    instruction=prompt.STOCK_MARKET_INFO_AGGREGATOR_PROMPT,
    sub_agents=[
        query_ticker_agent,
        market_fetcher_agent,
    ],
)

root_agent = stock_market_info_aggregator
