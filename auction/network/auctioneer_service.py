from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn

app = FastAPI(title="Auctioneer Service")

class AuctionRequest(BaseModel):
    req_id: str
    seller_id: str
    node_id: str
    delivery: str
    order_pk: str 
    min_price: float
    demand: int

class Bid(BaseModel):
    carrier_id: str
    req_id: str
    value: float

current_auction: Optional[AuctionRequest] = None
bids: List[Bid] = []

@app.get("/next_request")
def get_next_request():
    return {"status": "open", **current_auction.model_dump()} \
           if current_auction else {"status": "none"}

@app.post("/start_auction")
def start_auction(req: AuctionRequest):
    global current_auction, bids
    current_auction = req
    bids = []
    return {"status": "started", **req.dict()}

@app.post("/bid")
def place_bid(bid: Bid):
    if not current_auction or bid.req_id != current_auction.req_id:
        return {"status": "no_active_auction"}
    bids.append(bid)
    return {"status": "received"}

@app.post("/close_auction")
def close_auction():
    global current_auction
    if not current_auction:
        return {"status": "none"}
    sorted_bids = sorted(bids, key=lambda b: b.value, reverse=True)
    winner = sorted_bids[0] if sorted_bids else None
    price = sorted_bids[1].value if len(sorted_bids) > 1 else (winner.value if winner else 0)
    result = {"winner_id": winner.carrier_id if winner else None,
              "winner": winner.carrier_id if winner else None,
              "price": price,
              **current_auction.model_dump()}
    current_auction = None
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
