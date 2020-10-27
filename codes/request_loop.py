import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import json

header = {'content-type': "Application/json"}

parameter = {
    'key0': 'value0',
    'key1': 'value1'
}

session = requests.Session()

retries = Retry(total=5,  # リトライ回数
                backoff_factor=1,  # sleep時間
                status_forcelist=[500, 502, 503, 504])  # timeout以外でリトライするステータスコード

session.mount("https://", HTTPAdapter(max_retries=retries))

# connect timeoutを10秒, read timeoutを30秒に設定
response = session.get(url="https://xxx",
                       headers=header,
                       params=parameter,
                       stream=True,
                       timeout=(10.0, 30.0))

print(response.status_code)
print(response.json())
