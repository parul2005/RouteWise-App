from math import atan2, cos, radians, sin, sqrt


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth ka radius, kilometers mein

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


def optimize_route(store_location, orders):
    unvisited = orders.copy()
    route = []
    current_location = store_location
    total_distance = 0

    while unvisited:
        nearest_order = None
        nearest_distance = float('inf')

        for order in unvisited:
            dist = calculate_distance(
                current_location[0], current_location[1],
                order['latitude'], order['longitude']
            )
            if dist < nearest_distance:
                nearest_distance = dist
                nearest_order = order

        route.append({**nearest_order, 'leg_distance_km': round(nearest_distance, 2)})
        total_distance += nearest_distance
        current_location = (nearest_order['latitude'], nearest_order['longitude'])
        # remove original object ko karna hai (copy ko nahi)
        unvisited.remove(nearest_order)

    return route, round(total_distance, 2)


if __name__ == '__main__':
    store = (28.7041, 77.1025)

    orders = [
        {'id': 1, 'customer_name': 'Priya Sharma', 'latitude': 28.7041, 'longitude': 77.1025},
        {'id': 2, 'customer_name': 'Aman Kumar', 'latitude': 28.6942, 'longitude': 77.1310},
        {'id': 3, 'customer_name': 'Rina Gupta', 'latitude': 28.7132, 'longitude': 77.1569},
        {'id': 4, 'customer_name': 'Vikas Singh', 'latitude': 28.6942, 'longitude': 77.1806}
    ]

    best_route, total_km = optimize_route(store, orders)

    print("Best delivery order:")
    for i, order in enumerate(best_route, 1):
        print(f"{i}. {order['customer_name']} (leg: {order['leg_distance_km']} km)")

    print(f"\nTotal distance: {total_km} km")