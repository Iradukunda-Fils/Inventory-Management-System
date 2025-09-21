import httpx
from httpx import AsyncClient
import asyncio

async def get_data(url, data):
    token = "eyJhbGciOiJIUzUxMiJ9.eyJpZCI6IjM3MCIsInJldm9rZWRfdG9rZW5fY291bnQiOjAsImlhdCI6MTcyNDk5Njg0NiwiZXhwIjoxODE5NjA0ODQ2fQ.wRtZzYMe6W4wEKWDfIUe32lzC_voHT2m-i0FHefwxjv6-YPvlrYp_FfZjtwipIMbfiMyPnCukZzxSr22VGWdkQ"
    async with AsyncClient() as client:
        headers = {"Authorization": "Bearer " + token}
        res = await client.post(url, headers=headers, json=data)
        return res
    
async def main():
    message = "Hello, I am happy for my first message api call!"
    data = await get_data("https://api.pindo.io/v1/sms/", data={"to": "+25" + "0783071229", "text": message, "sender": "IMS"})
    print(data.json())
    
if __name__ == "__main__":
    asyncio.run(main())