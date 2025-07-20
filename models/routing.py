#we were previously using CVRP, this is now unused
"""Capacited Vehicles Routing Problem (CVRP)."""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas

from models import nodeUtilities

def create_data_model(demands:list[int]):
    """Stores the data for the problem."""

    def importTravelMatrix() -> list[list[float]]:
        df = pandas.read_csv("./models/metadata/travelMatrixFromGUI.csv", index_col=0)
        matrix = df.values.tolist()
        matrix = [[int(value) for value in row] for row in matrix]

        return matrix 

    data = {}
    data["distance_matrix"] = importTravelMatrix()
    # the sum of demands should be 0 or a positive int
    data["demands"] = demands
    data["vehicle_capacities"] = [5]
    data["num_vehicles"] = len(data["vehicle_capacities"])
    # set warehouse as the depot
    data["depot"] = len(demands) - 1
    return data


def print_solution(data, manager, routing, solution) -> dict:
    """Prints solution on console."""

    resolved_solution = {}
    resolved_solution["objective"] = solution.ObjectiveValue()
    resolved_solution["distance"] = []
    resolved_solution["route_map_index"] = []
    resolved_solution["route_map_ID"] = []

    warehouse = nodeUtilities.getNodeWithNodeID("N99")
    resolved_solution["warehouse_location"] = [warehouse.x, warehouse.y]

    total_load = 0
    
    for vehicle_id in range(data["num_vehicles"]):
        resolved_solution["route_map_index"].append([])
        resolved_solution["route_map_ID"].append([])
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue
        index = routing.Start(vehicle_id)
        route_distance = 0
        route_load = [0]    # route_load[0] is for init
        route_map_index = [0]     # route_map[0] is for init
        route_map_ID = [""]

        # resolve the solution
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_map_index.append(node)
            route_load.append(data["demands"][node] + route_load[-1])

            # move the index pointer forward
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            # data["demands"][node] = 0

            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )

        # # return to the warehouse
        # node = manager.IndexToNode(index)
        # route_map.append(node)
        # route_load.append(data["demands"][node] + route_load[-1])

        # print info
        plan_output = f"==== START of ROUTING MODEL OUTPUT ====\nRoute for vehicle {vehicle_id}:\n"
        for i in range(1, len(route_map_index)):
            plan_output += f" {route_map_index[i]} Load({route_load[i]}) -> "
        plan_output += f"\nDistance of the route: {route_distance}m\n"
        # print(plan_output)

        # save resolved solution into a dict
        resolved_solution["distance"].append(route_distance)
        resolved_solution["route_map_index"][-1] = route_map_index

        for i in route_map_index[1:]:
            route_map_ID.append(nodeUtilities.getNodeIDWithIndex(i))        
        resolved_solution["route_map_ID"][-1] = route_map_ID
        total_load += route_load[-1]

    # print(f"Total distance of all routes: {sum(resolved_solution['distance'])}m")
    # print(f"Total load of all routes: {total_load}")
    # print(f"Objective: {resolved_solution['objective']}")
    # print("==== END of ROUTING MODEL OUTPUT ====")

    return resolved_solution

def solve_CVRP_problem(demand_for_each_nodes:list[int]) -> dict:
    """Solve the CVRP problem."""

    # Instantiate the data problem.
    data = create_data_model(demand_for_each_nodes)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data["vehicle_capacities"],  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity",
    )

    # Add penalty to nodes without any demain
    PENALTY = 10
    for node in range(len(data["demands"])):
        if data["demands"][node] == 0:
            routing.AddDisjunction([manager.NodeToIndex(node)], PENALTY)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(1)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        resolved_solution = print_solution(data, manager, routing, solution)
        return resolved_solution
    else:
        return None