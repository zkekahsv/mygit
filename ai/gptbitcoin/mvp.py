import os
from dotenv import load_dotenv
load_dotenv()

# 1. 업비트 차트 데이터 가져오기 30일 일봉
import pyupbit
df = pyupbit.get_ohlcv("KRW-BTC", count=30)


# 2. AI 에게 데이터 제공하고 판단 받기
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "You are an expert in Bitcoin investing. Tell me whether to buy, sell, hold at the moment based on the chart data provided. response in json format.\n\n\nResponse Example:\n{:decision\":\"buy\",\"reason\":\"some technical reason\"}\n{:decision\":\"sell\",\"reason\":\"some technical reason\"}\n{:decision\":\"hold\",\"reason\":\"some technical reason\"}"
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": df.to_json()
        }
      ]
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "\n{\"decision\":\"hold\",\"reason\":\"The recent chart data shows sharp and significant price increases along with high volume, indicating that Bitcoin may have experienced a strong rally. However, the extreme price movements make it difficult to determine if this is a sustainable trend or simply market volatility. It may be prudent to hold and wait for further confirmation of direction before making a decisive move. Additionally, after such significant price increases, there could be a potential for a correction.\"}"
        }
      ]
    }
  ],
  response_format={
    "type": "json_object"
  }
)

result = response.choices[0].message.content
import json
result = json.loads(result)
import pyupbit
access = os.getenv("UPBIT_ACCESS_KEY")          # 본인 값으로 변경
secret = os.getenv("UPBIT_SECRET_KEY")          # 본인 값으로 변경
upbit = pyupbit.Upbit(access, secret)



if result["decision"] == "buy":
    my_krw = upbit.get_balance("KRW")
    if my_krw*0.9995 > 5000:
    # 매수
        print(upbit.buy_limit_order("KRW-BTC", my_krw*0.9995))
        print("buy:",result["reason"])
    else:
        print("krw 5000원 미만")

elif result["sell"] == "sell":
    # 매도
    my_btc = upbit.get_balance("KRW-BTC")
    current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]['ask_price']

    if my_btc*current_price > 5000:
         print(upbit.sell_limit_order("KRW-BTC", upbit.get_balance("KRW-BTC")))
         print("sell:",result["reason"])
    else:
        print("btc 5000원 미만")
elif result["decision"] =="hold":
    print("hold:",result["reason"])
    # 지나감
    pass
print(result)
print(type(result))
print(result["decision"])
# 3. AI의 판단에 따라 실제로 자동매매 진행하기




# {
#   "decision":"hold","reason":"The recent chart data indicates significant price increases with high levels of trading volume, suggesting a strong upward trend or rally in Bitcoin. However, given the magnitude of these price movements, it could also indicate increased market volatility. It is advisable to hold and observe the market for more stable trends, as a correction might follow such a rapid price increase."
# }
