"""
Mesa agents for the Collaborative Carrier Network
— PnD version (uses costModelBasedOnOrder).
"""

# stdlib
import csv
import sys
import os
from typing import Dict, List, Optional

# third-party
import requests
from mesa import Agent

# project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.pickupDelivery import solve_PnD_problem
from models.costModelBasedOnOrder import CostModel

# FastAPI auctioneer
AUCTIONEER_URL = "http://localhost:8000"


# ──────────────────────────────────────────────────────────────────────
# CarrierAgent
# ──────────────────────────────────────────────────────────────────────
class CarrierAgent(Agent):
    """A carrier that sells its worst order and (later) bids for others."""

    CYCLE_LENGTH = 5  # 0 = apply; 1 = offer; 2-4 = bid

    # ── init ───────────────────────────────────────────────────────────
    def __init__(
        self,
        unique_id: int,
        model,
        carrier_id: str,
        order_csv: str,
        travel_csv: str,
        a1: float,
        a2: float,
        b1: float,
        b2: float,
        depot_coord: tuple[float, float]
    ):
        #super().__init__()
        self.unique_id = unique_id
        self.model = model
        #self.random = model.random
        self.carrier_id = carrier_id
        self.order_csv = order_csv
        self.travel_csv = travel_csv
        self.depot_coord = {"x": depot_coord[0], "y": depot_coord[1]}
        self.depot_id = f"W{unique_id}"      # or "N9{unique_id}"
        self._already_bid_req: Optional[str] = None
        self.cost_model = CostModel(a1, a2, b1, b2, order_csv, travel_csv)
        self.offers_made   = 0      # total offers so far
        self.OFFERS_LIMIT  = 3      # limit offers


        # bookkeeping
        self._cycle_pos = 0
        self._auction_req_id: Optional[str] = None   # request we are selling
        self._auction_order_row: Optional[int] = None  # row index in CSV

    # ── helpers ────────────────────────────────────────────────────────
    @property
    def _orders(self) -> List[List[str]]:
        """Return current order rows [Order ID(pk), pickup, delivery]."""
        with open(self.cost_model.path_order) as f:
            return list(csv.reader(f))[1:]          # skip header

    def _write_orders(self, rows: List[List[str]]) -> None:
        with open(self.cost_model.path_order, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Order ID(pk)","pickup","delivery"])
            w.writerows(rows)

    # route distance (for GUI, not strictly needed here)
    def route_distance(self) -> float:
        return sum(solve_PnD_problem(self.cost_model.path_order, self.cost_model.path_travel_matrix, 
                                     depot_id=self.depot_id)["distance"])

    # ── Mesa step ──────────────────────────────────────────────────────
    def step(self) -> None:
        # phase 0 – apply result from last auction
        if self._cycle_pos == 0 and self.model.last_auction_result:
            self._apply_result(self.model.last_auction_result)

        # phase 1 – start our own auction (worst order)
        if self._cycle_pos == 1:
            self._offer_worst_order()

        # phase 2-4 – bid on others 
        if self._cycle_pos in (2, 3, 4):
            self._maybe_bid()

        # advance cycle
        self._cycle_pos = (self._cycle_pos + 1) % self.CYCLE_LENGTH

    # ── phase 1 : offer ────────────────────────────────────────────────
    def _offer_worst_order(self) -> None:
        if self.offers_made >= self.OFFERS_LIMIT:
            return # stop offering if limit reached
        profits = self.cost_model.pj()               # [all, without 1, without 2, …]
        base = profits[0]
        gains = [profits[i] - base for i in range(1, len(profits))]
        # pick order whose removal gives biggest gain (or smallest loss)
        idx = max(range(len(gains)), key=lambda i: gains[i])
        if gains[idx] <= 0:
            idx = 0  # nothing improves profit → just drop first order

        worst_row = self._orders[idx]
        pickup_id = worst_row[1]
        order_row = self._orders[idx]             # [pk, pickup, delivery]

        payload = {
            "req_id": self.model.next_req_id(),
            "seller_id": self.carrier_id,
            "node_id": pickup_id,
            "delivery":   order_row[2],
            "order_pk":   order_row[0],
            "demand": 0,                   # legacy field
            "min_price": self.cost_model.rj(),     # revenue baseline
        }
        requests.post(f"{AUCTIONEER_URL}/start_auction", json=payload, timeout=5)
        print(f"[{self.carrier_id}] OFFER order {order_row[0]} "
              f"({pickup_id}->{order_row[2]}) min={payload['min_price']:.1f}")
        self._auction_req_id = payload["req_id"]
        self._auction_order_row = idx
        self.offers_made += 1

    # ── phase 2-4 : bid ──────────────────────────────────
    def _maybe_bid(self) -> None:
        r = requests.get(f"{AUCTIONEER_URL}/next_request", timeout=5).json()
        if r.get("status") == "none" or r["seller_id"] == self.carrier_id:
            return
        delta = self.cost_model.profit_if_added(r["seller_id"], r["node_id"], r["delivery"])
        #print(f"[{self.carrier_id}] Δprofit if added = {delta:.1f}")#debug
        if delta > 0:
            payload = {"carrier_id": self.carrier_id, "req_id": r["req_id"], "value": delta}
            if r["req_id"] == self._already_bid_req:
                return
            print(f"[{self.carrier_id}] BID {delta:.1f} on {r['seller_id']}:{r['order_pk']}")
            requests.post(f"{AUCTIONEER_URL}/bid", json=payload, timeout=5)
            self._already_bid_req = r["req_id"]

    # ── apply auction outcome ──────────────────────────────────────────
    def _apply_result(self, res: Dict) -> None:
        # we SOLD the order
        self._already_bid_req = None
        winner = res.get("winner_id", res.get("winner"))
        print(f"[{self.carrier_id}] AUCTION closed winner={winner} "
              f"seller={res['seller_id']} req={res['req_id']}")

        if res["seller_id"] == self.carrier_id and winner != self.carrier_id:
            rows = self._orders
            if self._auction_order_row is not None and self._auction_order_row < len(rows):
                del rows[self._auction_order_row]
                self._write_orders(rows)
                self.cost_model.invalidate()
                # refresh caches
                """self.cost_model = CostModel(
                    self.cost_model.a1,
                    self.cost_model.a2,
                    self.cost_model.b1,
                    self.cost_model.b2,
                    self.order_csv,
                    self.travel_csv,
                )"""
        # ── we BOUGHT the order ──
        elif winner == self.carrier_id and res["seller_id"] != self.carrier_id:
            new_row = [res["order_pk"], res["node_id"], res["delivery"]]
            rows = self._orders + [new_row]
            self._write_orders(rows)
            self.cost_model.invalidate()

        # clear bid memo so we can bid in next auction
        self._already_bid_req = None

        if res.get("status") != "closed":
            return

# ──────────────────────────────────────────────────────────────────────
# AuctioneerAgent – unchanged (just closes auction every cycle)
# ──────────────────────────────────────────────────────────────────────
class AuctioneerAgent(Agent):
    def __init__(self, unique_id: int, model):
        self.unique_id = unique_id
        self.model = model
    def step(self) -> None:
        if self.model.tick % CarrierAgent.CYCLE_LENGTH == 0:
            try:
                r = requests.post(f"{AUCTIONEER_URL}/close_auction", timeout=5)
                r.raise_for_status()
                self.model.last_auction_result = r.json()
            except requests.RequestException:
                self.model.last_auction_result = {}


