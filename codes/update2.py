import os
import sys
import requests
import datetime
import time
import re
import asyncio

import gspread
import pandas as pd
from bs4 import BeautifulSoup

arg = sys.argv

if len(arg) == 1:
    print("please enter sheet name")
else:
    sheetname = arg[1]


UPDATE_ALL = True
PRICE_ONLY = False


gc = gspread.service_account(filename=".keys/shimandou-bot-07299fe8b747.json")
wb = gc.open("stock_list")
ws = wb.worksheet(sheetname)
df = pd.DataFrame(ws.get_all_records())
print("worksheet loaded")


class CompanyProfile():
    def __init__(self, ticker):
        self.ticker = ticker
        self.updated = None
        self.name = None
        self.price = None
        self.daily_change = None
        self.weekly_change = None
        self.monthly_change = None
        self.yearly_change = None
        self.PER = None
        self.PSR = None
        self.PBR = None
        self.ROE = None
        self.ROA = None
        self.dividend_rate = None
        self.market_cap = None
        self.category = None
        self.description = None
        self.url_scouter = f'=HYPERLINK("https://monex.ifis.co.jp/index.php?sa=report_index&bcode={ticker}", "銘")'
        self.url_kabutan = f'=HYPERLINK("https://kabutan.jp/stock/?code={ticker}", "探")'
        self.url_tradingview = f'=HYPERLINK("https://jp.tradingview.com/chart/?symbol=TSE%3A{ticker}", "T")'
        self.url_keijiban = None
        self.announcement_date = None

    def update(self):
        loop = asyncio.get_event_loop()
        ticker = self.ticker

        yahoo_url = f"https://stocks.finance.yahoo.co.jp/stocks/detail/?code={ticker}.T"
        minkabu_url = f"https://minkabu.jp/stock/{ticker}"
        minkabu_url2 = f"https://minkabu.jp/stock/{ticker}/settlement"  # 決算情報
        kabutan_url = f"https://kabutan.jp/stock/?code={ticker}"
        kabutan_url_w = f"https://kabutan.jp/stock/kabuka?code={ticker}&ashi=wek"
        kabutan_url_m = f"https://kabutan.jp/stock/kabuka?code={ticker}&ashi=mon"
        kabutan_url_y = f"https://kabutan.jp/stock/kabuka?code={ticker}&ashi=yar"

        gather = asyncio.gather(
            self.get_soup_parallel(yahoo_url),
            self.get_soup_parallel(minkabu_url),
            self.get_soup_parallel(minkabu_url2),
            self.get_soup_parallel(kabutan_url),
            self.get_soup_parallel(kabutan_url_w),
            self.get_soup_parallel(kabutan_url_m),
            self.get_soup_parallel(kabutan_url_y)
        )

        yahoo_soup, minkabu_soup, minkabu_soup2, kabutan_soup, kabutan_soup_w, kabutan_soup_m, kabutan_soup_y \
            = loop.run_until_complete(gather)

        try:
            self.name = yahoo_soup.select_one(
                ".symbol").text.replace("(株)", "")
        except Exception as e:
            print("not found", e)
            return
        self.updated = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
        self.price = float(yahoo_soup.select(".stoksPrice")
                           [1].text.replace(",", ""))
        self.daily_change = float(re.findall(
            r"（(.*)%）", yahoo_soup.select_one(".change").text)[0])
        selector = "#stock_kabuka_table > table.stock_kabuka0 > tbody > tr > td:nth-child(7)"
        self.weekly_change = float(kabutan_soup_w.select_one(
            selector).text.replace("－", "nan"))
        self.monthly_change = float(kabutan_soup_m.select_one(
            selector).text.replace("－", "nan"))
        self.yearly_change = float(kabutan_soup_y.select_one(
            selector).text.replace("－", "nan"))

        self.url_keijiban = '=HYPERLINK("{}", "掲")'.format(
            yahoo_soup.select(".subNavi li a")[4]["href"]
        )

        minkabu_page = minkabu_soup.select(".wsnw.fwb")
        self.PER = float(
            minkabu_page[5].text[:-1].replace(",", "").replace("--", "0"))
        self.PBR = float(
            minkabu_page[7].text[:-1].replace(",", "").replace("--", "0"))
        self.PSR = float(
            minkabu_page[6].text[:-1].replace(",", "").replace("--", "0"))
        self.dividend_rate = float(
            minkabu_page[3].text[:-1].replace(",", "").replace("--", "0"))
        self.market_cap = int(
            minkabu_page[9].text[:-3].replace(",", "").replace("--", "0"))
        self.category = minkabu_soup.select(
            ".stock-detail div.ly_content_wrapper.size_ss")[0].select_one("a").text
        self.description = minkabu_soup.select(
            ".stock-detail div.ly_content_wrapper.size_ss")[1].text.strip()

        minkabu_table = minkabu_soup2.select(".data_table")[2].select(".num")
        self.ROA = float(minkabu_table[0].text[:-1].replace("--", "0"))
        self.ROE = float(minkabu_table[2].text[:-1].replace("--", "0"))

        try:
            self.announcement_date = kabutan_soup.select_one(
                "#kessan_happyoubi dd").text
            self.announcement_date = re.findall(
                r"[0-9/]+", self.announcement_date)[0]
        except Exception as e:
            print(e)

    def update_price(self):
        ticker = self.ticker
        yahoo_url = f"https://stocks.finance.yahoo.co.jp/stocks/detail/?code={ticker}.T"
        yahoo_soup = self.get_soup_parallel(yahoo_url)

        try:
            self.name = yahoo_soup.select_one(
                ".symbol").text.replace("(株)", "")
        except Exception as e:
            print("not found", e)
            return

        minkabu_url = f"https://minkabu.jp/stock/{ticker}"
        minkabu_soup = self.get_soup_parallel(minkabu_url)

        minkabu_page = minkabu_soup.select(".wsnw.fwb")
        self.PER = float(
            minkabu_page[5].text[:-1].replace(",", "").replace("--", "0"))
        self.PBR = float(
            minkabu_page[7].text[:-1].replace(",", "").replace("--", "0"))
        self.PSR = float(
            minkabu_page[6].text[:-1].replace(",", "").replace("--", "0"))
        self.dividend_rate = float(
            minkabu_page[3].text[:-1].replace(",", "").replace("--", "0"))
        self.market_cap = int(
            minkabu_page[9].text[:-3].replace(",", "").replace("--", "0"))

        self.updated = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
        self.price = float(yahoo_soup.select(".stoksPrice")
                           [1].text.replace(",", ""))
        self.daily_change = float(re.findall(
            r"（(.*)%）", yahoo_soup.select_one(".change").text)[0])

    async def get_soup_parallel(self, url):
        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(None, requests.get, url)
            soup = BeautifulSoup(res.text)
            return soup

        except Exception as e:
            print("ERROR: exception occured during requets or soup\n", e)
            return None


column_convertor = {
    "ticker": "code",
    "daily_change": "前日比",
    "weekly_change": "前週比",
    "monthly_change": "前月比",
    "yearly_change": "前年比",
    "dividend_rate": "利回",
    "market_cap": "cap",
    "description": "desc",
    "url_scouter": "銘",
    "url_kabutan": "探",
    "url_tradingview": "TV",
    "url_keijiban": "掲",
    "announcement_date": "決算日"
}

num = df.shape[0]

for i in df.index:
    ticker = df.loc[i, "code"]
    print(i+1, "/", num, "\t", ticker, end="")

    if not(UPDATE_ALL) and df.loc[i, "name"]:
        print("...skipped")
        continue

    company = CompanyProfile(ticker)

    if PRICE_ONLY:
        company.update_price()
    else:
        company.update()

    for attr in company.__dict__.keys():
        col = column_convertor[attr] if attr in column_convertor.keys(
        ) else attr
        if company.__dict__[attr] is None:
            continue
        df.loc[i, col] = company.__dict__[attr]
    print("...done")
    time.sleep(1)

list_to_draw = [df.columns.tolist()] + df.fillna("").values.tolist()
ws.update("A1", list_to_draw, value_input_option="USER_ENTERED")
print("update completed")
