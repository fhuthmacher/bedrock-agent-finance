import tools

# test get_company_name
query = "Should I invest in Amazon?"
company_name = tools.get_company_name(query)
print(company_name)

stock_ticker = tools.get_stock_ticker(company_name)
print(stock_ticker)

stock_price = tools.get_stock_price(stock_ticker)
print(stock_price)

print("financial statements: /n")
financial_statements = tools.get_financial_statements(stock_ticker)
print(financial_statements)

print("stock_news search results: /n")
stock_news = tools.stock_news_search(company_name)
print(stock_news)

print("recent_stock_news: /n")
recent_stock_news = tools.get_recent_stock_news(company_name)
print(recent_stock_news)

print("get_existing_portfolio: /n")
existing_portfolio = tools.get_existing_portfolio('')
print(existing_portfolio)

print("get_investment_research: /n")
existing_portfolio = tools.get_investment_research(query)
print(existing_portfolio)