import json
import boto3
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import FAISS
import time
from bs4 import BeautifulSoup
import re
import requests
from langchain.agents import load_tools, AgentType, Tool, initialize_agent
from pandas_datareader import data as pdr
from datetime import date
import pandas as pd
import yfinance as yf
yf.pdr_override() 
import pandas as pd
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings("ignore")
from langchain.tools import DuckDuckGoSearchRun
import csv
from io import StringIO

import logging

from opentelemetry import trace

### Explicitly added for logging which is currently in experimental stage and not working with auto-instrumentation
### OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = true
### BEG
from opentelemetry._logs import get_logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
   OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

logger_provider = LoggerProvider(
   resource=Resource.create(
       {
           "service.name": "FinancialAgent"
       }
   ),
)
set_logger_provider(logger_provider)
exporter = OTLPLogExporter()
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
# Attach OTLP handler to root logger
logging.getLogger().addHandler(handler)
logger = logging.getLogger("FinancialAgent")
### END

## Creates a tracer from the global tracer provider
tracer = trace.get_tracer("FinancialAgent")

# initialize clients
athena = boto3.client('athena')
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
)


def claude_prompt_format(prompt: str) -> str:
    # Add headers to start and end of prompt
    return "\n\nHuman: " + prompt + "\n\nAssistant:"


def call_claude(prompt):
    prompt_config = {
        "prompt": claude_prompt_format(prompt),
        "max_tokens_to_sample": 4096,
        "temperature": 0,
        "top_k": 250,
        "top_p": 0.5,
        "stop_sequences": [],
    }

    body = json.dumps(prompt_config)

    modelId = "anthropic.claude-v2"
    accept = "application/json"
    contentType = "application/json"

    response = bedrock_runtime.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())

    results = response_body.get("completion")
    return results


# Call Titan model
def call_titan(prompt):
    prompt_config = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 4096,
            "stopSequences": [],
            "temperature": 0.7,
            "topP": 1,
        },
    }

    body = json.dumps(prompt_config)

    modelId = "amazon.titan-text-lite-v1"
    accept = "application/json"
    contentType = "application/json"

    response = bedrock_runtime.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())

    print(response_body)

    results = response_body.get("results")[0].get("outputText")
    return results


def get_company_name(query):

    prompt = f"""\n\nHuman: Extract the company name from the below extract. \
             Don't include any other information in the response, only return the company name. \
              {query} \
                \n\nAssistant: """
    
    company_name = call_claude(prompt)
    
    return company_name


def get_stock_ticker(company_name):
    
    search=DuckDuckGoSearchRun()
    available_information = search("Stock ticker of " + company_name)
    prompt = f"""\n\nHuman: Extract the company ticker from the below extract. \
             Don't include any other information in the response, only return the ticker name. \
              {available_information} \
                \n\nAssistant: """
    
    company_ticker = call_claude(prompt)
    ticker = company_ticker.strip()
    return ticker

@tracer.start_as_current_span("FinancialAgent_lambda_tools_get_investment_research_YahooFinanceStockAPI")
def get_stock_price(ticker, history=10):
    today = date.today()
    start_date = today - timedelta(days=history)
    data = pdr.get_data_yahoo(ticker, start=start_date, end=today)
    dataname= ticker+'_'+str(today)
    return data, dataname


def stock_news_search(company_name):
    search=DuckDuckGoSearchRun()
    return search("Stock news about " + company_name)


# Fetch top 5 google news for given company name
def google_query(search_term):
    if "news" not in search_term:
        search_term=search_term+" stock news"
    url=f"https://www.google.com/search?q={search_term}"
    url=re.sub(r"\s","+",url)
    return url


@tracer.start_as_current_span("FinancialAgent_lambda_tools_get_investment_research_GoogleStockNews")
def get_recent_stock_news(company_name):
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    g_query=google_query(company_name)
    res=requests.get(g_query,headers=headers).text
    soup=BeautifulSoup(res,"html.parser")
    news=[]
    for n in soup.find_all("div","n0jPhd ynAwRc tNxQIb nDgy9d"):
        news.append(n.text)
    for n in soup.find_all("div","IJl0Z"):
        news.append(n.text)

    if len(news)>6:
        news=news[:4]
    else:
        news=news
    news_string=""
    for i,n in enumerate(news):
        news_string+=f"{i}. {n}\n"
    top5_news="Recent News:\n\n"+news_string
    
    return top5_news


# Get financial statements from Yahoo Finance
@tracer.start_as_current_span("FinancialAgent_lambda_tools_get_investment_research_YahooFinanceAPI")
def get_financial_statements(ticker):
    if "." in ticker:
        ticker=ticker.split(".")[0]
    else:
        ticker=ticker
    print('submitted ticker: ' + ticker)

    company = yf.Ticker(ticker)
    balance_sheet = company.balance_sheet
    if balance_sheet.shape[1]>=3:
        balance_sheet=balance_sheet.iloc[:,:3]    # Only captures last 3 years of data
    balance_sheet=balance_sheet.dropna(how="any")
    balance_sheet = balance_sheet.to_string()
    return balance_sheet


@tracer.start_as_current_span("FinancialAgent_lambda_tools_get_investment_research")
def get_investment_research(query):
    company_name =get_company_name(query)
    ticker=get_stock_ticker(company_name)
    stock_data=get_stock_price(ticker,history=10)
    stock_financials=get_financial_statements(ticker)
    stock_news=get_recent_stock_news(company_name)

    available_public_information=f"Stock Price: {stock_data}\n\nStock Financials: {stock_financials}\n\nStock News: {stock_news}"
    
    return available_public_information

@tracer.start_as_current_span("FinancialAgent_lambda_tools_get_existing_portfolio")
def get_existing_portfolio(username):
    existing_portfolio = {}

    # get portfolio of user
    databaseName = 'investment_portfolio'
    tableName = 'stock_portfolio'
    csv_string = ''
    # create a query with athena
    query = 'SELECT * FROM "' + databaseName + '"."' + tableName + '";'

    # run the query
    logger.info('run Athena query ' + str(query))
    athena_response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': databaseName
        }
    )
    # Get the query execution ID
    query_execution_id = athena_response['QueryExecutionId']
    logger.info('Athena query execution id ' + str(query_execution_id))
    # Check the status of the query execution
    while True:
        response = athena.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        status = response['QueryExecution']['Status']['State']
        logger.info('Athena query execution status ' + str(status))
        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        logger.info('sleep 5')
        time.sleep(5)

    # Check if the query was successful
    if status == 'SUCCEEDED':
        # Get the results
        logger.info('Athena get query results')
        results_response = athena.get_query_results(
            QueryExecutionId=query_execution_id
        )

        # Convert results to CSV string
        csv_output = StringIO()
        csv_writer = csv.writer(csv_output)

        # Write header
        csv_writer.writerow([field['Name'] for field in results_response['ResultSet']['ResultSetMetadata']['ColumnInfo']])

        # Write data rows
        for row in results_response['ResultSet']['Rows']:
            csv_writer.writerow([field['VarCharValue'] for field in row['Data']])

        # Get the CSV string
        existing_portfolio =  "{" + csv_output.getvalue() + "}"
        logger.info(str(existing_portfolio))
    else:
        logger.error('Query execution failed: {}'.format(status))
            
    # table with holding name & percentage

    return existing_portfolio