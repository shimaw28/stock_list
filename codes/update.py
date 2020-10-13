import os
import sys
import requests
import datetime
import re

import gspread
import pandas as pd
from bs4 import BeautifulSoup

arg = sys.argv

if len(arg) > 1 and arg[1] == "all":
    UPDATE_ALL = True
else:
    UPDATE_ALL = False

gc = gspread.service_account(filename=".keys/shimandou-bot-07299fe8b747.json")
wb = gc.open("stock_list")
ws = wb.worksheet("jp")
df = pd.DataFrame(ws.get_all_records())
print("worksheet loaded")


class CompanyProfile():
    def __init__(self, ticker):
        self.ticker = ticker
        self.updated = None
        self.name = None
        self.price = None
        self.daily_change = None
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
        self.url_keijiban = None


    def update(self):
        ticker = self.ticker
        yahoo_url = f"https://stocks.finance.yahoo.co.jp/stocks/detail/?code={ticker}.T"
        yahoo_soup = self.get_soup(yahoo_url)

        minkabu_url = f"https://minkabu.jp/stock/{ticker}"
        minkabu_soup = self.get_soup(minkabu_url)

        minkabu_url2 = f"https://minkabu.jp/stock/{ticker}/settlement" #決算情報@みんかぶ
        minkabu_soup2 = self.get_soup(minkabu_url2)

        try:
            self.name = yahoo_soup.select_one(".symbol").text.replace("(株)", "")
        except Exception as e:
            print("not found", e)
            return
        self.updated = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
        self.price = float(yahoo_soup.select(".stoksPrice")[1].text.replace(",", ""))
        self.daily_change = float(re.findall(r"（(.*)%）", yahoo_soup.select_one(".change").text)[0])
        self.url_keijiban = '=HYPERLINK("{}", "掲")'.format(
            yahoo_soup.select(".subNavi li a")[4]["href"]
        )

        minkabu_page = minkabu_soup.select(".wsnw.fwb")
        self.PER = float(minkabu_page[5].text[:-1].replace(",", "").replace("--", "0"))
        self.PBR = float(minkabu_page[7].text[:-1].replace(",", "").replace("--", "0"))
        self.PSR = float(minkabu_page[6].text[:-1].replace(",", "").replace("--", "0"))
        self.dividend_rate  = float(minkabu_page[3].text[:-1].replace(",", "").replace("--", "0"))
        self.market_cap = int(minkabu_page[9].text[:-3].replace(",", "").replace("--", "0"))
        self.category = minkabu_soup.select(".stock-detail div.ly_content_wrapper.size_ss")[0].select_one("a").text
        self.description = minkabu_soup.select(".stock-detail div.ly_content_wrapper.size_ss")[1].text.strip()


        minkabu_table = minkabu_soup2.select(".data_table")[2].select(".num")
        self.ROA = float(minkabu_table[0].text[:-1].replace("--", "0"))
        self.ROE = float(minkabu_table[2].text[:-1].replace("--", "0"))



    def get_soup(self, url):
        try:
            res = requests.get(url)
            soup = BeautifulSoup(res.text)
            return soup

        except Exception as e:
            print("ERROR: exception occured during requets or soup\n", e)
            return None

column_convertor = {
    "ticker": "code",
    "dividend_rate": "利回",
    "market_cap": "cap",
    "description": "desc",
    "url_scouter": "銘",
    "url_kabutan": "探",
    "url_keijiban": "掲"
}

for i in df.index:
    ticker = df.loc[i, "code"]
    print(ticker, end="")

    if not(UPDATE_ALL) and df.loc[i, "name"]:
        print("...skipped")
        continue

    company = CompanyProfile(ticker)
    company.update()

    for attr in company.__dict__.keys():
        col = column_convertor[attr] if attr in column_convertor.keys() else attr
        df.loc[i, col] = company.__dict__[attr]
    print("...done")

list_to_draw = [df.columns.tolist()] + df.fillna("").values.tolist()
ws.update("A1", list_to_draw, value_input_option="USER_ENTERED")
print("update completed")    