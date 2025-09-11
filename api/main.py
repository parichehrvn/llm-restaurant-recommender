from fastapi import FastAPI
from rag import get_suggestions, get_summary, restaurant_qna
import uvicorn
from pydantic import BaseModel
from typing import Optional

import json


app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    restaurant_name: Optional[str] = None

class QueryResponse(BaseModel):
    response: str


@app.get('/')
def home():
    return {'message': 'Connected'}


@app.get('/suggest')
async def suggest_restaurant(query: str):
    result = get_suggestions(query)
    return json.loads(result)


@app.get('/summary/{restaurant_name}')
async def summarize(restaurant_name: str):
    result = get_summary(restaurant_name)
    return json.loads(result)


@app.post('/query')
async def query_index(request: QueryRequest):
    result = restaurant_qna(request.restaurant_name, request.query)
    return json.loads(result)


if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)





