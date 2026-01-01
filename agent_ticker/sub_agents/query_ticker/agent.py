from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from pydantic import BaseModel, Field

from . import prompt


class Company(BaseModel):
    name: str = Field(description="The name of the company being discussed.")
    ticker: str = Field(description="The stock exchange ticker of the company.")


extract_ticker_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="extract_ticker_agent",
    description=("Extract the company name and ticker based "),
    instruction=prompt.EXTRACT_TICKER_PROMPT,
    output_schema=Company,
    output_key="company",
)

info_search_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="info_search_agent",
    description=("Use google search to find"),
    instruction=prompt.INFO_SEARCH_PROMPT,
    tools=[google_search],
)


query_ticker_agent = SequentialAgent(
    name="query_ticker_agent",
    description=(
        "Identify and extract company name and stock market ticker from the user"
    ),
    sub_agents=[info_search_agent, extract_ticker_agent],
)
