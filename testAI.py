import networkx as nx
import xml.etree.ElementTree as ET
import requests
import folium
import os
import math
import tkinter as tk
from tkinter import ttk, messagebox

def parse_osm(xml_file):
    G = nx.Graph()
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    for node in root.findall('.//node'):
        node_id = node.attrib['id']
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in node.findall('tag')}
        G.add_node(node_id, **tags)
    
    return G

def get_node_coordinates(node_id):
    url = f"https://api.openstreetmap.org/api/0.6/node/{node_id}"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        lat = root.find('.//node').attrib['lat']
        lon = root.find('.//node').attrib['lon']
        return float(lat), float(lon)
    else:
        return None

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    return c * r

def best_first_search(graph, start_node, hospital_nodes, pos):
    visited = set()
    path = []
    current_node = start_node

    while hospital_nodes:
        visited.add(current_node)
        path.append(current_node)
        hospital_nodes.remove(current_node)

        if not hospital_nodes:
            break

        closest_node = min(hospital_nodes, key=lambda node: haversine(pos[current_node][0], pos[current_node][1], pos[node][0], pos[node][1]))
        current_node = closest_node

    return path

def get_route(osrm_url, coordinates):
    locs = ";".join([f"{lon},{lat}" for lon, lat in coordinates])
    url = f"{osrm_url}/route/v1/driving/{locs}?geometries=geojson&overview=full"
    response = requests.get(url)
    if response.status_code == 200:
        route = response.json()['routes'][0]['geometry']['coordinates']
        return [(lat, lon) for lon, lat in route]
    else:
        return []

def main():
    # Adjust this path to your XML data directory
    data_dir = "data"
    xml_files = [os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith(".xml")]
    
    graph = nx.Graph()
    for file in xml_files:
        G = parse_osm(file)
        graph = nx.compose(graph, G)
    
    total_nodes = len(graph.nodes())
    print(f"Total nodes in graph: {total_nodes}")
    print("Checking coordinates...")

    for node in graph.nodes():
        coordinates = get_node_coordinates(node)
        if coordinates:
            graph.nodes[node]['lat'] = coordinates[0]
            graph.nodes[node]['lon'] = coordinates[1]
    
    nodes_with_coords = [node for node, data in graph.nodes(data=True) if 'lat' in data and 'lon' in data]
    print(f"Total nodes with coordinates: {len(nodes_with_coords)}")

    hospital_nodes = []
    hospital_info = {}
    for node in graph.nodes(data=True):
        if 'amenity' in node[1] and node[1]['amenity'] == 'hospital':
            hospital_nodes.append(node[0])
            hospital_name = node[1].get('name', 'Unnamed Hospital')
            hospital_info[node[0]] = hospital_name

    print(f"Total hospitals identified: {len(hospital_nodes)}")
    for node, name in hospital_info.items():
        print(f"Hospital ID: {node}, Name: {name}")
        
    pos = {node: (data['lon'], data['lat']) for node, data in graph.nodes(data=True) if 'lat' in data and 'lon' in data}

    root = tk.Tk()
    root.title("Select Starting Hospital")
    root.geometry("400x200")

    hospital_list = [f"{hospital_info[node]}" for node in hospital_nodes]
    hospital_id_list = [node for node in hospital_nodes]

    def on_select(event):
        selected_hospital_name = combo.get()
        if selected_hospital_name not in hospital_list:
            messagebox.showerror("Error", "Invalid hospital name. Exiting.")
            return
        
        starting_hospital = hospital_id_list[hospital_list.index(selected_hospital_name)]
        
        path = best_first_search(graph, starting_hospital, hospital_nodes.copy(), pos)
        
        m = folium.Map(location=[pos[starting_hospital][1], pos[starting_hospital][0]], zoom_start=14)
        
        osrm_url = "http://router.project-osrm.org"
        colors = ["green", "red"]
        
        for i in range(len(path) - 1):
            node1, node2 = path[i], path[i + 1]
            route = get_route(osrm_url, [(pos[node1][0], pos[node1][1]), (pos[node2][0], pos[node2][1])])
            folium.PolyLine(route, color=colors[i % len(colors)]).add_to(m)
        
        for node in path:
            folium.Marker(location=[pos[node][1], pos[node][0]], popup=hospital_info.get(node, "Hospital")).add_to(m)
        
        m.save("map.html")
        os.system("map.html")

    combo = ttk.Combobox(root, values=hospital_list, font=('Helvetica', 10), width=40)
    combo.set("Select a Hospital")
    combo.bind("<<ComboboxSelected>>", on_select)
    combo.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()