"""Simple Pickup Delivery Problem (PDP)."""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas
import models.nodeUtilities as nu
import os

PATH_MODELS = os.path.dirname(os.path.abspath(__file__))
PATH_METADATA = os.path.join(PATH_MODELS, 'metadata')
PATH_INPUT = os.path.join(PATH_MODELS, 'input')

def create_data_model(FILE_ORDER:str, FILE_TRAVELMATRIX:str, DEPOT_ID:str = "W0"):
    """Stores the data for the problem."""
    def getPickupDeliveryNodeIDPairs() -> list[str]:
        import csv
        PATH_FILE = os.path.join(PATH_INPUT, FILE_ORDER)
        with open(PATH_FILE) as f:
            orderInfo = list(csv.reader(f))

        pickup_delivery_nodeID_paris:list[str] = []
        for row in orderInfo[1:]:
            pickup_delivery_nodeID_paris.append([row[1], row[2]])
        
        return(pickup_delivery_nodeID_paris)
    
    def getPickupDeliveryNodes() -> list:        
        pickup_delivery_nodeID_paris = getPickupDeliveryNodeIDPairs()
        pickup_delivery_nodes:list[int] = []

        for pair in pickup_delivery_nodeID_paris:
            pickup_delivery_nodes.append(nu.getNodeWithNodeID(pair[0]))
            pickup_delivery_nodes.append(nu.getNodeWithNodeID(pair[1]))
        pickup_delivery_nodes.append(nu.getNodeWithNodeID(DEPOT_ID))
        
        return(pickup_delivery_nodes)
        
    def getNodesIndexWithDemand() -> list[int]:
        nodes_with_demand:list[int] = []
        for order in data["pickup_delivery_index_pairs"]:
            for node in order:
                nodes_with_demand.append(node)

        return(nodes_with_demand)
    
    def readTravelMatrix(file_name):
        PATH_FILE = os.path.join(PATH_METADATA, file_name)

        df = pandas.read_csv(PATH_FILE, index_col=0)
        matrix = df.values.tolist()
        matrix = [[int(value) for value in row] for row in matrix]

        return matrix

    def convertNodeIDToNodeIndex(pair_of_nodeID:list[list[str]]) -> list[int]:
        pair_of_nodeIndex:list[list[int]] = []
        list_of_nodeID:list[str] = []
        for pair in pair_of_nodeID:
            list_of_nodeID.append(pair[0])
            list_of_nodeID.append(pair[1])
        list_of_sorted_nodeID = sorted(list_of_nodeID)

        for i in range(len(list_of_nodeID)//2):
            pair_of_nodeIndex.append([list_of_sorted_nodeID.index(list_of_nodeID[2*i]), list_of_sorted_nodeID.index(list_of_nodeID[2*i+1])])

        return pair_of_nodeIndex

    nu.writeTravelMatrix(getPickupDeliveryNodes(), FILE_TRAVELMATRIX)

    data = {}
    data["pickup_delivery_ID_pairs"] = getPickupDeliveryNodeIDPairs()
    data["pickup_delivery_index_pairs"] = convertNodeIDToNodeIndex(data["pickup_delivery_ID_pairs"])
    data["nodes_with_demand"] = getNodesIndexWithDemand()    
    data["distance_matrix"] = readTravelMatrix(FILE_TRAVELMATRIX)
    data["num_vehicles"] = 1
    data["depot"] = len(data["nodes_with_demand"])

    return data

def print_solution(data, manager, routing, solution, depot_id:str):
    """Prints solution on console."""

    resolved_solution = {}
    resolved_solution["objective"] = solution.ObjectiveValue()
    resolved_solution["distance"] = []
    resolved_solution["route_map_index"] = []
    resolved_solution["route_map_ID"] = []

    warehouse = nu.getNodeWithNodeID(depot_id)
    resolved_solution["warehouse_location"] = [warehouse.x, warehouse.y]

    #print(f"Objective: {solution.ObjectiveValue()}")
    total_distance = 0
    for vehicle_id in range(data["num_vehicles"]):
        resolved_solution["route_map_index"].append([])
        resolved_solution["route_map_ID"].append([])
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue
        index = routing.Start(vehicle_id)

        route_distance = 0
        start_node = manager.IndexToNode(routing.Start(vehicle_id))
        route_map_index = [start_node]
        route_map_ID = []

        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_distance = 0

        while not routing.IsEnd(index):

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            node = manager.IndexToNode(index)
            route_map_index.append(node)

            plan_output += f" {manager.IndexToNode(previous_index)} -> "
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
        plan_output += f"{manager.IndexToNode(index)}\n"
        plan_output += f"Distance of the route: {route_distance}m\n"
        #print(plan_output)
        total_distance += route_distance

        # return to the warehouse
        node = manager.IndexToNode(index)
        route_map_index.append(node)

        # save resolved solution into a dict
        resolved_solution["distance"].append(route_distance)
        resolved_solution["route_map_index"][-1] = route_map_index

        def convertNodeIndexToNodeID(index:int) -> str:
            list_of_nodeID:list[str] = []
            if index == len(data["nodes_with_demand"]):
                return depot_id
            for pair in data["pickup_delivery_ID_pairs"]:
                list_of_nodeID.append(pair[0])
                list_of_nodeID.append(pair[1])
            list_of_sorted_nodeID = sorted(list_of_nodeID)

            return list_of_sorted_nodeID[index]
    
        for node_index in route_map_index:
            route_map_ID.append(convertNodeIndexToNodeID(node_index))
            # print(node_index, "->", convertNodeIndexToNodeID(node_index))     
        resolved_solution["route_map_ID"][-1] = route_map_ID
        
    #print(f"Total Distance of all routes: {total_distance}m")

    return resolved_solution

def solve_PnD_problem(file_order, file_travelMatrix, depot_id:str = "W0"):
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model(file_order, file_travelMatrix, depot_id)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)
    # forbid using the depot as an intermediate stop
    depot_idx = manager.NodeToIndex(data["depot"])
    routing.AddDisjunction([depot_idx], 10_000_000)   # huge penalty

    # Define cost of each arc.
    def distance_callback(from_index, to_index):
        """Returns the manhattan distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = "Distance"
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        8000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name,
    )
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Define Transportation Requests.
    for request in data["pickup_delivery_index_pairs"]:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])

        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            distance_dimension.CumulVar(pickup_index)
            <= distance_dimension.CumulVar(delivery_index) - 1
        )

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # print(solution)

    # Print solution on console.
    if solution:
        return print_solution(data, manager, routing, solution, depot_id)
    else:
        print("NO SOLUTION")
        return None
