import networkx as nx
import xml.etree.ElementTree as ET
import requests
import matplotlib.pyplot as plt
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
    
    for way in root.findall('.//way'):
        way_id = way.attrib['id']
        tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
        G.add_node(way_id, **tags)
        
        nds = [nd.attrib['ref'] for nd in way.findall('nd')]
        for i in range(len(nds) - 1):
            G.add_edge(nds[i], nds[i+1])
    
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
    # Convert degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
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

def main():
    data_dir = "data"
    xml_files = [os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith(".xml")]
    
    graph = nx.Graph()
    for file in xml_files:
        G = parse_osm(file)
        graph = nx.compose(graph, G)
    
    # Add coordinates to nodes
    total_nodes = len(graph.nodes())
    print(f"Total nodes in graph: {total_nodes}")

    for node in graph.nodes():
        coordinates = get_node_coordinates(node)
        if coordinates:
            graph.nodes[node]['lat'] = coordinates[0]
            graph.nodes[node]['lon'] = coordinates[1]
    
    # Check how many nodes have coordinates
    nodes_with_coords = [node for node, data in graph.nodes(data=True) if 'lat' in data and 'lon' in data]
    print(f"Total nodes with coordinates: {len(nodes_with_coords)}")

    # List hospitals
    hospital_nodes = []
    hospital_info = {}
    for node in graph.nodes(data=True):
        if 'amenity' in node[1] and node[1]['amenity'] == 'hospital':
            hospital_nodes.append(node[0])
            hospital_name = node[1].get('name', 'Unnamed Hospital')
            hospital_info[node[0]] = hospital_name

    pos = {node: (data['lon'], data['lat']) for node, data in graph.nodes(data=True) if 'lat' in data and 'lon' in data}

    # GUI for selecting starting hospital
    root = tk.Tk()
    root.title("Select Starting Hospital")

    hospital_list = [f"{hospital_info[node]}" for node in hospital_nodes]
    hospital_id_list = [node for node in hospital_nodes]

    def on_select(event):
        selected_hospital_name = combo.get()
        if selected_hospital_name not in hospital_list:
            messagebox.showerror("Error", "Invalid hospital name. Exiting.")
            return
        
        starting_hospital = hospital_id_list[hospital_list.index(selected_hospital_name)]
        
        # Best First Search to find the path
        path = best_first_search(graph, starting_hospital, hospital_nodes.copy(), pos)

        # Draw the graph with distances from the starting hospital
        plt.figure(figsize=(15, 15))

        edge_labels = {}
        for i in range(len(path) - 1):
            node1, node2 = path[i], path[i + 1]
            lon1, lat1 = pos[node1]
            lon2, lat2 = pos[node2]
            distance = haversine(lon1, lat1, lon2, lat2)
            plt.plot([lon1, lon2], [lat1, lat2], 'g-', alpha=0.5)
            edge_labels[(node1, node2)] = f"{distance:.2f} km"

        # Draw nodes without text
        nx.draw_networkx_nodes(graph, pos, node_size=50, node_color='red')
        
        # Highlight and label hospital nodes
        for node in hospital_nodes:
            node_pos = pos[node]
            hospital_name = hospital_info[node]
            color = 'red' if node == starting_hospital else 'blue'
            plt.text(node_pos[0], node_pos[1], f"{hospital_name}", fontsize=9, ha='right', color=color)
        
        # Draw edge labels
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8)
        
        plt.title(f"Graph with Distances from Hospital Node {starting_hospital}")
        plt.axis('equal')  # Ensures the aspect ratio is equal for better visualization
        plt.show()

    combo = ttk.Combobox(root, values=hospital_list)
    combo.set("Select a Hospital")
    combo.bind("<<ComboboxSelected>>", on_select)
    combo.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
