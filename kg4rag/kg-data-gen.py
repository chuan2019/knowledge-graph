"""
Knowledge Graph RAG Sample Data Generator
Generates realistic, large-scale data for content rights, localization, and delivery workflows
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker
import uuid
import csv
from tqdm import tqdm
import os

# Initialize Faker for realistic names
fake = Faker()

# ============= CONFIGURATION =============
NUM_TITLES = 5000               # Movies/TV series
NUM_VERSIONS_PER_TITLE = 3      # Average versions per title
NUM_CLIENTS = 200               # Studios, broadcasters, streamers
NUM_REGIONS = 50                # Countries/territories
NUM_LANGUAGES = 30              # Audio/subtitle languages
NUM_AUDIO_FORMATS = 8           # Stereo, 5.1, 7.1, Atmos, etc.
NUM_VIDEO_FORMATS = 6           # HD, 4K, 8K, HDR, HDR10+, Dolby Vision
NUM_CONTAINERS = 5              # IMF, MXF, MP4, MKV, MOV
NUM_RIGHTS_TYPES = 5            # Exclusive, non-exclusive, territorial, windowed
NUM_DELIVERY_POINTS = 150       # Netflix, Hulu, Disney+, broadcasters, theaters

# Scale multipliers (adjust for demo size)
SCALE_FACTOR = 1  # Set to 0.1 for quick test, 1 for full demo, 10 for performance testing

actual_titles = int(NUM_TITLES * SCALE_FACTOR)
actual_clients = int(NUM_CLIENTS * SCALE_FACTOR)
actual_delivery_points = int(NUM_DELIVERY_POINTS * SCALE_FACTOR)

# ============= HELPER FUNCTIONS =============
def generate_titles(n):
    """Generate movie/TV titles with metadata"""
    title_types = ['Movie', 'TV Series', 'Documentary', 'Special', 'Miniseries']
    genres = ['Action', 'Drama', 'Comedy', 'Thriller', 'Sci-Fi', 'Romance', 'Horror', 'Animation']
    studios = ['Warner Bros', 'Universal', 'Paramount', 'Sony', 'Disney', 'Netflix Studios', 'Apple TV+']
    
    titles = []
    for i in tqdm(range(n), desc="Generating titles"):
        title_type = random.choice(title_types)
        year = random.randint(1980, 2025)
        titles.append({
            'title_id': f"TITLE_{i:06d}",
            'title_name': fake.catch_phrase() + f" {year}",
            'title_type': title_type,
            'genre': random.choice(genres),
            'studio': random.choice(studios),
            'release_year': year,
            'duration_minutes': random.randint(45, 180) if title_type == 'Movie' else random.randint(300, 6000),
            'season_count': random.randint(1, 8) if title_type == 'TV Series' else 0,
            'created_at': datetime.now().isoformat()
        })
    return pd.DataFrame(titles)

def generate_clients(n):
    """Generate client/studio data"""
    client_types = ['Major Studio', 'Streaming Service', 'Broadcaster', 'Aggregator', 'Independent']
    tiers = ['Tier 1', 'Tier 2', 'Tier 3']
    
    clients = []
    for i in tqdm(range(n), desc="Generating clients"):
        clients.append({
            'client_id': f"CLIENT_{i:05d}",
            'client_name': fake.company(),
            'client_type': random.choice(client_types),
            'tier': random.choice(tiers),
            'region_focus': random.choice(['North America', 'Europe', 'APAC', 'LATAM', 'Global']),
            'active_since': random.randint(1990, 2024),
            'credit_limit_usd': random.randint(100000, 5000000),
            'status': random.choice(['Active', 'Active', 'Active', 'On Hold'])  # Weighted
        })
    return pd.DataFrame(clients)

def generate_versions(titles_df):
    """Generate content versions (different formats/localizations)"""
    versions = []
    
    for _, title in tqdm(titles_df.iterrows(), total=len(titles_df), desc="Generating versions"):
        num_versions = random.randint(1, NUM_VERSIONS_PER_TITLE * 2)
        
        for v in range(num_versions):
            is_localized = random.choice([True, False])
            version_id = f"VER_{title['title_id']}_{v:03d}"
            
            versions.append({
                'version_id': version_id,
                'title_id': title['title_id'],
                'version_type': random.choice(['Original', 'Localized', 'Remastered', 'Edited']),
                'resolution': random.choice(['HD', '4K', '8K']),
                'frame_rate': random.choice(['23.976', '24', '25', '29.97', '30', '50', '60']),
                'audio_channels': random.choice(['2.0', '5.1', '7.1', 'Atmos']),
                'hdr_format': random.choice(['SDR', 'HDR10', 'HDR10+', 'Dolby Vision', 'None']),
                'file_size_gb': round(random.uniform(10, 500), 2),
                'is_localized': is_localized,
                'created_date': datetime.now() - timedelta(days=random.randint(1, 365))
            })
    return pd.DataFrame(versions)

def generate_rights(versions_df, clients_df, regions_df):
    """Generate rights relationships (complex multi-hop data)"""
    rights = []
    
    # Pre-filter active clients
    active_clients = clients_df[clients_df['status'] == 'Active']['client_id'].tolist()
    
    for _, version in tqdm(versions_df.iterrows(), total=min(50000, len(versions_df)), desc="Generating rights"):
        # Each version has 1-5 rights grants
        num_rights = random.randint(1, 5)
        
        for _ in range(num_rights):
            start_date = datetime.now() - timedelta(days=random.randint(1, 1095))
            end_date = start_date + timedelta(days=random.randint(90, 730))
            
            rights.append({
                'rights_id': str(uuid.uuid4()),
                'version_id': version['version_id'],
                'client_id': random.choice(active_clients),
                'region_id': random.choice(regions_df['region_id'].tolist()),
                'rights_type': random.choice(['Exclusive', 'Non-exclusive', 'Territorial', 'Windowed']),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'is_active': end_date > datetime.now(),
                'territorial_restrictions': random.choice(['None', 'Country-specific', 'Regional']),
                'exclusivity_window_days': random.randint(30, 365) if random.random() > 0.5 else None
            })
    return pd.DataFrame(rights)

def generate_localization_jobs(versions_df, languages_df):
    """Generate localization tasks (dubbing, subtitling)"""
    localized_versions = versions_df[versions_df['is_localized'] == True]
    localization = []
    
    for _, version in tqdm(localized_versions.iterrows(), total=len(localized_versions), desc="Generating localization"):
        # Each localized version has 1-3 language tracks
        num_langs = random.randint(1, 3)
        
        selected_langs = random.sample(languages_df['language_code'].tolist(), min(num_langs, len(languages_df)))
        
        for lang in selected_langs:
            status = random.choice(['Completed', 'In Progress', 'Pending', 'QA Review'])
            completion_date = datetime.now() - timedelta(days=random.randint(1, 180)) if status == 'Completed' else None
            
            localization.append({
                'job_id': str(uuid.uuid4()),
                'version_id': version['version_id'],
                'language_code': lang,
                'job_type': random.choice(['Dubbing', 'Subtitling', 'Voice-over', 'Audio Description']),
                'status': status,
                'completion_date': completion_date.isoformat() if completion_date else None,
                'quality_score': random.uniform(0.7, 1.0) if status == 'Completed' else None,
                'vendor': fake.company() if random.random() > 0.5 else 'Internal'
            })
    return pd.DataFrame(localization)

def generate_delivery_specs(delivery_points_df, versions_df):
    """Generate delivery specifications for each destination"""
    specs = []
    
    for dp_id in tqdm(delivery_points_df['delivery_point_id'].tolist(), desc="Generating delivery specs"):
        # Each delivery point requires multiple format specifications
        num_specs = random.randint(2, 6)
        
        for _ in range(num_specs):
            specs.append({
                'spec_id': str(uuid.uuid4()),
                'delivery_point_id': dp_id,
                'version_id': random.choice(versions_df['version_id'].tolist()),
                'required_resolution': random.choice(['HD', '4K', '8K']),
                'required_audio': random.choice(['2.0', '5.1', '7.1', 'Atmos']),
                'required_hdr': random.choice(['SDR', 'HDR10', 'HDR10+', 'Dolby Vision']),
                'required_container': random.choice(['IMF', 'MXF', 'MP4', 'MKV']),
                'max_bitrate_mbps': random.randint(5, 50),
                'is_mandatory': random.choice([True, False])
            })
    return pd.DataFrame(specs)

def generate_delivery_requests(versions_df, delivery_points_df, clients_df):
    """Generate active delivery requests (complex multi-hop path)"""
    requests = []
    
    # Sample a subset for reasonable dataset size
    sample_size = min(20000, len(versions_df) * 3)
    
    for i in tqdm(range(sample_size), desc="Generating delivery requests"):
        version = versions_df.sample(1).iloc[0]
        client = clients_df.sample(1).iloc[0]
        delivery_point = delivery_points_df.sample(1).iloc[0]
        
        created_date = datetime.now() - timedelta(days=random.randint(1, 90))
        status = random.choice(['Pending', 'In Progress', 'Completed', 'Failed', 'Delayed'])
        
        requests.append({
            'request_id': f"DELIVERY_{i:06d}",
            'version_id': version['version_id'],
            'client_id': client['client_id'],
            'delivery_point_id': delivery_point['delivery_point_id'],
            'request_date': created_date.isoformat(),
            'deadline': (created_date + timedelta(days=random.randint(5, 30))).isoformat(),
            'status': status,
            'actual_completion': (datetime.now() - timedelta(days=random.randint(1, 10))).isoformat() if status == 'Completed' else None,
            'priority': random.choice(['Low', 'Medium', 'High', 'Urgent']),
            'file_size_gb': round(random.uniform(10, 500), 2)
        })
    
    return pd.DataFrame(requests)

# ============= MAIN GENERATION FUNCTION =============
def generate_knowledge_graph_data(output_dir='./kg_demo_data', scale_factor=1):
    """Main orchestration function to generate all data"""
    
    global SCALE_FACTOR
    SCALE_FACTOR = scale_factor
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating Knowledge Graph Demo Data")
    print(f"Scale factor: {SCALE_FACTOR}x")
    print(f"Output directory: {output_dir}")
    print()
    
    # 1. Generate base entities
    print("Generating base entities...")
    titles_df = generate_titles(actual_titles)
    clients_df = generate_clients(actual_clients)
    
    # 2. Generate regions and languages
    regions_df = pd.DataFrame({
        'region_id': [f"REG_{i:03d}" for i in range(1, NUM_REGIONS + 1)],
        'region_name': [fake.country() for _ in range(NUM_REGIONS)],
        'continent': [random.choice(['NA', 'EU', 'APAC', 'LATAM', 'AF', 'ME'])[0] for _ in range(NUM_REGIONS)]
    })
    
    languages_df = pd.DataFrame({
        'language_code': [f"LANG_{i:03d}" for i in range(1, NUM_LANGUAGES + 1)],
        'language_name': [fake.language_name() for _ in range(NUM_LANGUAGES)],
        'language_family': [random.choice(['Indo-European', 'Sino-Tibetan', 'Afroasiatic', 'Other']) for _ in range(NUM_LANGUAGES)]
    })
    
    audio_formats_df = pd.DataFrame({
        'format_id': [f"AUDIO_{i:03d}" for i in range(1, NUM_AUDIO_FORMATS + 1)],
        'format_name': ['Stereo', '5.1 Surround', '7.1 Surround', 'Dolby Atmos', 'DTS:X', 'Auro-3D', 'Mono', '2.1 Stereo'][:NUM_AUDIO_FORMATS]
    })
    
    video_formats_df = pd.DataFrame({
        'format_id': [f"VIDEO_{i:03d}" for i in range(1, NUM_VIDEO_FORMATS + 1)],
        'format_name': ['HD', '4K UHD', '8K', 'HDR10', 'HDR10+', 'Dolby Vision'][:NUM_VIDEO_FORMATS]
    })
    
    delivery_points_df = pd.DataFrame({
        'delivery_point_id': [f"DP_{i:05d}" for i in range(1, actual_delivery_points + 1)],
        'point_name': [f"{fake.company()} - {random.choice(['Streaming', 'Broadcast', 'Theatrical', 'VOD'])}" for _ in range(actual_delivery_points)],
        'delivery_type': [random.choice(['Streaming', 'Broadcast', 'Theatrical', 'VOD', 'Physical']) for _ in range(actual_delivery_points)],
        'region_id': random.choices(regions_df['region_id'].tolist(), k=actual_delivery_points)
    })
    
    # 3. Generate relationships
    print("Generating relationships...")
    versions_df = generate_versions(titles_df)
    rights_df = generate_rights(versions_df, clients_df, regions_df)
    localization_df = generate_localization_jobs(versions_df, languages_df)
    delivery_specs_df = generate_delivery_specs(delivery_points_df, versions_df)
    delivery_requests_df = generate_delivery_requests(versions_df, delivery_points_df, clients_df)
    
    # 4. Save all datasets
    print("Saving datasets...")
    
    datasets = {
        'titles.csv': titles_df,
        'clients.csv': clients_df,
        'regions.csv': regions_df,
        'languages.csv': languages_df,
        'audio_formats.csv': audio_formats_df,
        'video_formats.csv': video_formats_df,
        'delivery_points.csv': delivery_points_df,
        'versions.csv': versions_df,
        'rights.csv': rights_df,
        'localization.csv': localization_df,
        'delivery_specs.csv': delivery_specs_df,
        'delivery_requests.csv': delivery_requests_df
    }
    
    for filename, df in datasets.items():
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"  OK {filename}: {len(df):,} records")
    
    # 5. Generate summary report
    total_nodes = sum(
        len(df)
        for df in [
            titles_df,
            clients_df,
            regions_df,
            languages_df,
            audio_formats_df,
            video_formats_df,
            delivery_points_df,
        ]
    )
    total_relationships = sum(
        len(df)
        for df in [
            versions_df,
            rights_df,
            localization_df,
            delivery_specs_df,
            delivery_requests_df,
        ]
    )

    print("\nGeneration Summary:")
    print(f"  Total Nodes: {total_nodes:,}")
    print(f"  Total Relationships: {total_relationships:,}")
    
    # 6. Generate sample Cypher queries for demo
    generate_demo_queries(output_dir)
    
    print(f"\nData generation complete. Files saved to {output_dir}")
    print("\nNext steps:")
    print("  1. Import CSV files into Neo4j using neo4j-admin import")
    print("  2. Run python -m http.server in the output directory to serve files")
    print("  3. Use the generated queries in demo_queries.txt for RAG examples")
    
    return datasets

def generate_demo_queries(output_dir):
    """Generate sample complex queries for demo"""
    queries = [
        "-- Complex Multi-Hop Query 1: Rights Compliance",
        "MATCH (v:Version)<-[:HAS_VERSION]-(t:Title)",
        "MATCH (v)-[:GRANTED_TO]->(c:Client)",
        "MATCH (v)-[:LOCALIZED_FOR]->(l:Language)",
        "WHERE c.tier = 'Tier 1' AND l.language_name CONTAINS 'Spanish'",
        "RETURN t.title_name, c.client_name, l.language_name",
        "LIMIT 10;",
        "",
        "-- Complex Multi-Hop Query 2: Delivery Chain Analysis",
        "MATCH (dr:DeliveryRequest)-[:FOR_VERSION]->(v:Version)",
        "MATCH (dr)-[:TO_POINT]->(dp:DeliveryPoint)",
        "MATCH (dp)-[:LOCATED_IN]->(r:Region)",
        "MATCH (v)-[:BELONGS_TO]->(t:Title)",
        "WHERE dr.status IN ['Delayed', 'Failed']",
        "AND r.continent = 'EU'",
        "RETURN t.title_name, dp.point_name, dr.status, dr.deadline",
        "ORDER BY dr.deadline ASC",
        "LIMIT 20;",
        "",
        "-- Complex Multi-Hop Query 3: Content Rights Optimization",
        "MATCH (c:Client)-[:HAS_RIGHTS]->(r:Rights)-[:FOR_VERSION]->(v:Version)",
        "MATCH (v)-[:HAS_AUDIO]->(a:AudioFormat)",
        "WHERE r.is_active = true",
        "AND r.end_date > date()",
        "AND a.format_name = 'Dolby Atmos'",
        "RETURN c.client_name, count(DISTINCT v) as atmos_titles",
        "ORDER BY atmos_titles DESC;",
        "",
        "-- Complex Multi-Hop Query 4: Localization Status Report",
        "MATCH (loc:Localization)-[:FOR_VERSION]->(v:Version)",
        "MATCH (v)-[:BELONGS_TO]->(t:Title)",
        "WHERE loc.status = 'In Progress'",
        "RETURN t.title_name, count(loc) as active_localizations",
        "HAVING count(loc) > 2;",
        "",
        "-- Complex Multi-Hop Query 5: Client Delivery Performance",
        "MATCH (c:Client)<-[:REQUESTED_BY]-(dr:DeliveryRequest)",
        "MATCH (dr)-[:FOR_VERSION]->(v:Version)",
        "WHERE dr.status IN ['Completed', 'Failed']",
        "RETURN c.client_name,",
        "       avg(CASE WHEN dr.status = 'Completed' THEN 1 ELSE 0 END) as success_rate,",
        "       count(dr) as total_requests",
        "ORDER BY success_rate ASC;"
    ]
    
    with open(os.path.join(output_dir, 'demo_queries.txt'), 'w') as f:
        f.write('\n'.join(queries))
    
    print(f"  OK demo_queries.txt: {len([q for q in queries if q and not q.startswith('--')])} sample queries")

# ============= EXECUTION =============
if __name__ == "__main__":
    # For quick test: scale_factor=0.1 (small dataset)
    # For full demo: scale_factor=1 (medium dataset)
    # For performance test: scale_factor=10 (large dataset)
    
    SCALE = 1  # Adjust this based on your needs
    
    data = generate_knowledge_graph_data(
        output_dir='./kg_demo_data',
        scale_factor=SCALE
    )
    
    print("\nDemo-ready data created.")
    print("Sample queries and data loading instructions saved in the output directory.")