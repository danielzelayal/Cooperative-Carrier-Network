from models import nodeUtilities
from models import routing

# price to sell

# real cost

# rj, cj, pj

class CostModel:
    def __init__(self, _a1, _a2, _b1, _b2, _N:list[str]):
        self.a1 = _a1
        self.a2 = _a2
        self.b1 = _b1
        self.b2 = _b2
        # N only inclues avaliable nodes, warehouse is alway in the route and cannot be remove/ trade
        self.N  = _N

    def produceDemandList(self) -> list[int]:

        demand_list = [0]* nodeUtilities.getNumberOfNodes('nodeInfoFromGUI.csv')
        
        for every_node in self.N:
            index = int(every_node[1:])
            if index != 99:
                demand_list[index] = -1
        demand_list[-1] = len(self.N)
        return demand_list

    # price for request/ order
    def rj(self, distance:int):
        return self.a1+ self.a2* distance

    def lj(self, node_ID_without:str) -> int:
        
        demand_list = self.produceDemandList()
        result_old = routing.solve_CVRP_problem(demand_list)
        if not result_old or 'distance' not in result_old:
            return 0
        old_distance = result_old['distance'][0]

        # print("old", old_distance)

        index = int(node_ID_without[1:])
        if demand_list[index] == -1:
            demand_list[index] = 0

        new_distance = routing.solve_CVRP_problem(demand_list)['distance'][0]
        # print("new", new_distance)
        return old_distance - new_distance
    
    # real cost
    def cj(self, node_ID_without:str):
        return self.b1 + self.b2 * self.lj(node_ID_without)
    
    # earning
    def pj(self, node_ID_without:str, distance:int):
        return self.rj(distance) - self.cj(node_ID_without)