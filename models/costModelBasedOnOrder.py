import os
import csv
from typing import List

from models.pickupDelivery import solve_PnD_problem

# project-relative paths ------------------------------------------------
PATH_MODELS       = os.path.dirname(os.path.abspath(__file__))
PATH_PROJECT      = os.path.dirname(PATH_MODELS)
PATH_AUCTION      = os.path.join(PATH_PROJECT, "auction")
PATH_CARRIERS_INFO = os.path.join(PATH_AUCTION, "carriers_info")


class CostModel:
    """
    Order-based cost model:
        • a1, a2 determine revenue  = a1 + a2 · distance
        • b1, b2 determine cost     = b1 + b2 · (distance saved / added)
        • profit  = revenue − cost
    Helper vectors (index 0 = all orders):
        distance_information[i] … distance if order-i removed
        cost_information[i]      … cost saved if order-i removed
        profit_information[i]    … profit if order-i removed
    """

    # ──────────────────────────────────────────────────────────────────
    # constructor
    # ──────────────────────────────────────────────────────────────────
    def __init__(self, _a1, _a2, _b1, _b2, file_order, file_travelMatrix):
        self.a1 = _a1
        self.a2 = _a2
        self.b1 = _b1
        self.b2 = _b2

        # absolute paths to CSVs
        self.path_order         = os.path.join(PATH_CARRIERS_INFO, file_order)
        self.path_travel_matrix = os.path.join(PATH_CARRIERS_INFO, file_travelMatrix)

        # cached metrics
        self.revenue               = self.rj()
        self.distance_information  = self.distanceWithoutEachOrder()
        self.cost_information      = self.cj()
        self.profit_information    = self.pj()

    # ──────────────────────────────────────────────────────────────────
    # revenue with *all* current orders
    # ──────────────────────────────────────────────────────────────────
    def rj(self) -> float:
        dist_all = sum(solve_PnD_problem(self.path_order, self.path_travel_matrix)["distance"])
        self.revenue = self.a1 + self.a2 * dist_all
        return self.revenue

    # ──────────────────────────────────────────────────────────────────
    # distance if EACH order were removed once
    # ──────────────────────────────────────────────────────────────────
    def distanceWithoutEachOrder(self) -> List[float]:
        with open(self.path_order) as f:
            list_of_orders = list(csv.reader(f))[1:]          # skip header

        # baseline
        base_dist = sum(solve_PnD_problem(self.path_order,
                                          self.path_travel_matrix)["distance"])
        distances = [base_dist]

        # loop over orders, write tmp CSV without that row, re-solve
        for idx in range(len(list_of_orders)):
            tmp_orders = list_of_orders[:idx] + list_of_orders[idx + 1:]
            tmp_path   = os.path.join(PATH_CARRIERS_INFO, "tmp_rm.csv")
            with open(tmp_path, "w", newline="") as tf:
                w = csv.writer(tf)
                w.writerow(["Order ID(pk)", "pickup", "delivery"])
                w.writerows(tmp_orders)

            dist = sum(solve_PnD_problem(tmp_path,
                                          self.path_travel_matrix)["distance"])
            distances.append(dist)

        self.distance_information = distances
        return distances

    # ──────────────────────────────────────────────────────────────────
    # cost saved by removing each order
    # ──────────────────────────────────────────────────────────────────
    def cj(self) -> List[float]:
        costs = [self.b1 + self.b2 * 0]   # index‑0 = distance saved is 0
        for i in range(1, len(self.distance_information)):
            lj = self.distance_information[0] - self.distance_information[i]
            costs.append(self.b1 + self.b2 * lj)   # already marginal – OK
        self.cost_information = costs
        return costs

    # ──────────────────────────────────────────────────────────────────
    # profit if each order were removed
    # ──────────────────────────────────────────────────────────────────
    def pj(self) -> List[float]:
        profits = [
            self.revenue - self.cost_information[i]
            for i in range(len(self.cost_information))
        ]
        self.profit_information = profits
        return profits

    # ──────────────────────────────────────────────────────────────────
    # marginal profit if we *add* an external order
    # pickup_id & seller_id identify the row in seller‘s CSV.
    # Returns Δ(delta)profit  (>0   → worthwhile to bid)
    # ──────────────────────────────────────────────────────────────────
    def profit_if_added(self, seller_id: str, pickup_id: str, delivery_id: str) -> float:
        """
        Parameters
        ----------
        seller_id : "C0", "C1", …
        pickup_id : str – the pickup node ID announced in the auction
        delivery_id : str - the delivery node ID announced in the auction

        Notes
        -----
        • Delivery node is looked up in seller's order CSV.
        • We create a tmp CSV **with** that extra row, re-solve, then compute
          revenue & cost like in rj() / cj().
        """
        # 1. locate seller’s order row -----------------------------
        seller_csv = os.path.join(PATH_CARRIERS_INFO, f"order{seller_id}.csv")
        with open(seller_csv) as f:
            rows = list(csv.reader(f))[1:]

        candidate_row = next((r for r in rows if r[1] == pickup_id and r[2] == delivery_id), None)
        if candidate_row is None:
            # unknown order → certainly not profitable
            #print("returning -1e9")#debug
            return -1e9

        # 2. build augmented order list ----------------------------
        with open(self.path_order) as f:
            my_rows = list(csv.reader(f))[1:]

        augmented_rows = my_rows + [candidate_row]
        tmp_add_path = os.path.join(PATH_CARRIERS_INFO, "tmp_add.csv")
        with open(tmp_add_path, "w", newline="") as tf:
            w = csv.writer(tf)
            w.writerow(["Order ID(pk)", "pickup", "delivery"])
            w.writerows(augmented_rows)

        # 3. recompute distance / revenue / cost -------------------
        dist_aug = sum(solve_PnD_problem(tmp_add_path,
                                         self.path_travel_matrix)["distance"])
        revenue_aug = self.a1 + self.a2 * dist_aug
        extra_dist  = dist_aug - self.distance_information[0]
        cost_aug    = self.b1 + self.b2 * extra_dist
        profit_aug = revenue_aug - cost_aug

        # 4. Δprofit relative to current baseline ------------------
        delta = profit_aug - self.profit_information[0]
        return delta

    # ──────────────────────────────────────────────────────────────────
    # convenience – refresh every cached vector after external edit
    # ──────────────────────────────────────────────────────────────────
    def invalidate(self) -> None:
        self.revenue              = self.rj()
        self.distance_information = self.distanceWithoutEachOrder()
        self.cost_information     = self.cj()
        self.profit_information   = self.pj()
