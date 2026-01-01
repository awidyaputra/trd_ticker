"""Prompt for the query_ticker_agent."""

INFO_SEARCH_PROMPT = """
You are a helpful assistant that has access to google search.

- Provide a brief summary of the top result using `google_search` using context of stock market.
- **Always** provide a brief summary of the top result using `google_search` without using context of stock market.
"""

EXTRACT_TICKER_PROMPT = """
Your task is extract the company name and ticker from a given text.

IMPORTANT: Your response MUST be valid JSON matching this structure:
{
"name": "Company name here",
"ticker": "Company ticker here",
}

If no ticker is found the response will match the following structure:
{
"name": "Company name here",
"ticker": "",
}

DO NOT include any explanations or additional text outside the JSON response
"""
