"""
Mesa model orchestrating all carriers + one auctioneer.
Now uses PnD routing & order-based cost model.
"""

import os
import json
import time
from typing import List

from mesa import Model
from mesa.time import RandomActivation

from auction.agents import CarrierAgent, AuctioneerAgent
from models.pickupDelivery import solve_PnD_problem

# quick param table  (a1, a2, b1, b2) per carrier
PARAMS = [
    (1.0, 1.4, 2.0, 1.0),
    (1.5, 1.2, 1.9, 1.0),
    (0.9, 1.4, 2.9, 0.9),
]


class CarrierModel(Model):
    def __init__(self, n_carriers: int = 3):
        super().__init__()
        self.schedule = RandomActivation(self)
        self.tick = 0
        self._next_req = 0
        self.last_auction_result = {}

        # carriers -------------------------------------------------------
        self.carriers: List[CarrierAgent] = []
        for i in range(n_carriers):
            depot_coord = {
                0: (-40, -290),
                1: (-170, 200),
                2: (110, 200),
            }[i]
            c = CarrierAgent(
                i,
                self,
                f"C{i}",
                f"orderC{i}.csv",
                f"travelMatrixC{i}.csv",
                *PARAMS[i],
                depot_coord=depot_coord
            )
            self.carriers.append(c)
            self.schedule.add(c)

        # single auctioneer ---------------------------------------------
        self.auctioneer = AuctioneerAgent(unique_id=999, model=self)
        self.schedule.add(self.auctioneer)

    # helper for unique request IDs -------------------------------------
    def next_req_id(self) -> str:
        self._next_req += 1
        return f"R{self._next_req}"

    # Mesa tick ----------------------------------------------------------
    def step(self) -> None:
        self.tick += 1
        self.schedule.step()

        # dump snapshots each cycle end (GUI expects *_vrp.json) ---------
        from_path = "auction/carriers_info"
        if self.tick % CarrierAgent.CYCLE_LENGTH == 0:
            for c in self.carriers:
                res = solve_PnD_problem(c.cost_model.path_order, c.cost_model.path_travel_matrix, 
                                        depot_id=c.depot_id)
                res["warehouse_location"] = [c.depot_coord["x"], c.depot_coord["y"]]
                out = os.path.join(from_path, f"{c.carrier_id}_vrp.json")
                os.makedirs(from_path, exist_ok=True)
                with open(out, "w") as fp:
                    json.dump(res, fp, indent=2)


