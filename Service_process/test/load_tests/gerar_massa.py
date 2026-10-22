import json
import uuid
import os

def generate_geojson(num_features, output_filename):
    features = []
    base_lon, base_lat = -46.6333, -23.5505
    
    for i in range(num_features):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [base_lon + (i * 0.0001), base_lat + (i * 0.0001)]
            },
            "properties": {
                "id": str(uuid.uuid4()),
                "data": "2024-01-01"
            }
        }
        features.append(feature)
        
    feature_collection = {
        "type": "FeatureCollection",
        "features": features
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(output_filename)), exist_ok=True)
    with open(output_filename, 'w') as f:
        json.dump(feature_collection, f)
        
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Geramos P (50 focos), M (500 focos) e G (5000 focos)
    generate_geojson(50, os.path.join(base_dir, "data", "small.geojson"))
    generate_geojson(500, os.path.join(base_dir, "data", "medium.geojson"))
    generate_geojson(1000, os.path.join(base_dir, "data", "large.geojson"))
    
    print("Arquivos de massa de dados gerados com sucesso na pasta data/ !")
