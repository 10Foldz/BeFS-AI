import networkx as nx
import xml.etree.ElementTree as ET
import requests
import matplotlib.pyplot as plt
import os

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

def main():
    xml_files = [f"data/{file}" for file in os.listdir("data") if file.endswith(".xml")]
    
    graph = nx.Graph()
    for file in xml_files:
        G = parse_osm(file)
        graph = nx.compose(graph, G)
    
    # file = "data/data1.xml"  # specify the file you want to check
    # graph = parse_osm(file)
    
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

    # Find and count hospitals
    hospital_nodes = []
    for node in graph.nodes(data=True):
        if 'amenity' in node[1] and node[1]['amenity'] == 'hospital':
            hospital_nodes.append(node[0])
            print(node[1].get('name', 'Unnamed Hospital'))  # Print the name if available, otherwise 'Unnamed Hospital'
            print(f"Latitude: {node[1].get('lat', 'Unknown')}, Longitude: {node[1].get('lon', 'Unknown')}")  # Print coordinates if available

    print("Total number of hospitals:", len(hospital_nodes))

    # Draw the graph with hospitals highlighted
    pos = {node: (data['lon'], data['lat']) for node, data in graph.nodes(data=True) if 'lat' in data and 'lon' in data}
    plt.figure(figsize=(12, 12))
    
    # Draw all nodes
    nx.draw(graph, pos, node_size=10, node_color='blue', edge_color='gray', alpha=0.5, with_labels=False)
    
    # Highlight hospital nodes
    hospital_pos = {node: pos[node] for node in hospital_nodes if node in pos}
    nx.draw_networkx_nodes(graph, hospital_pos, node_size=50, node_color='red')
    
    plt.title("Graph with Hospitals Highlighted")
    plt.show()

if __name__ == "__main__":
    main()
