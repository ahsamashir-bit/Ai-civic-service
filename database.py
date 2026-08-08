import sqlite3
import json
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'civic_services.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create complaints table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            latitude REAL,
            longitude REAL,
            address TEXT,
            reporter_name TEXT,
            reporter_email TEXT,
            reporter_phone TEXT,
            ai_analysis TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolution_notes TEXT,
            assigned_team TEXT
        )
    ''')
    
    # Create settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['value']
    return default

def save_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, str(value)))
    conn.commit()
    conn.close()

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing complaints to start fresh
    cursor.execute('DELETE FROM complaints')
    
    # Mock data definitions (San Francisco coordinates centered around lat: 37.7749, lon: -122.4194)
    categories = [
        "Roads & Traffic", 
        "Water & Sanitation", 
        "Waste Management", 
        "Electrical & Lighting", 
        "Parks & Public Spaces", 
        "Public Safety"
    ]
    
    priorities = ["Low", "Medium", "High", "Critical"]
    statuses = ["Submitted", "Assigned", "In Progress", "Resolved"]
    
    teams = {
        "Roads & Traffic": "Roads & Infrastructure Team",
        "Water & Sanitation": "Municipal Water Utility Dept",
        "Waste Management": "Sanitation & Recycling Division",
        "Electrical & Lighting": "Grid and Lighting Maintenance",
        "Parks & Public Spaces": "Parks & Recreation Department",
        "Public Safety": "Community Safety & Transit Security"
    }

    mock_reports = [
        {
            "title": "Severe Water Main Leak on Market St",
            "description": "Clean water is gushing from the sidewalk under the fire hydrant. It is flooding the bike lane and causing a safety hazard for cyclists and pedestrians. Hundreds of gallons are being wasted.",
            "category": "Water & Sanitation",
            "priority": "Critical",
            "status": "In Progress",
            "lat": 37.7785,
            "lon": -122.4121,
            "address": "1100 Market St, San Francisco, CA",
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "555-0199",
            "days_ago": 1,
            "resolution_notes": "",
            "ai_reasoning": "Determined critical priority due to significant clean water waste, immediate flooding of a transportation lane (bike lane), and active pedestrian/cyclist hazard.",
            "suggested_steps": "1. Dispatch Emergency Water Utility team. 2. Shut off main supply valve on Section-B. 3. Repair/replace broken coupling assembly under hydrant."
        },
        {
            "title": "Large Dangerous Pothole near School Crossing",
            "description": "There is a massive pothole, at least 6 inches deep, right before the pedestrian crosswalk in front of the elementary school. Cars are swerving into the opposite lane to avoid it, which is extremely dangerous during morning drop-off times.",
            "category": "Roads & Traffic",
            "priority": "Critical",
            "status": "Assigned",
            "lat": 37.7699,
            "lon": -122.4468,
            "address": "400 Cole St, San Francisco, CA",
            "name": "Robert Chen",
            "email": "rob.chen@example.com",
            "phone": "555-0144",
            "days_ago": 2,
            "resolution_notes": "",
            "ai_reasoning": "Classified as critical priority because of high safety hazard to school children and drivers, causing dangerous vehicular swerving maneuvers in a school zone.",
            "suggested_steps": "1. Set up warning pylons/signage immediately. 2. Schedule rapid patching crew. 3. Clean loose debris and fill pothole with hot-mix asphalt."
        },
        {
            "title": "Broken Streetlights on 16th Street",
            "description": "Entire block of 16th street is completely dark because three consecutive streetlights are out. It feels very unsafe walking home from the BART station at night.",
            "category": "Electrical & Lighting",
            "priority": "High",
            "status": "Submitted",
            "lat": 37.7650,
            "lon": -122.4201,
            "address": "1900 16th St, San Francisco, CA",
            "name": "Marcus Vance",
            "email": "mvance@example.com",
            "phone": "555-0182",
            "days_ago": 0,
            "resolution_notes": "",
            "ai_reasoning": "High priority assigned due to public safety risk of consecutive streetlight outages near transit hubs, creating potential dark zones prone to accidents or crime.",
            "suggested_steps": "1. Run diagnostic on electrical line panel L-16. 2. Verify bulb failures vs circuit breaker trip. 3. Replace bulb fixtures with standard municipal LEDs."
        },
        {
            "title": "Illegal Dumping of Tires and Mattress",
            "description": "Someone dumped about 10 old car tires and a moldy mattress on the curb next to the community garden. It's blocking the sidewalk and attracting rodents.",
            "category": "Waste Management",
            "priority": "Medium",
            "status": "Resolved",
            "lat": 37.7521,
            "lon": -122.4102,
            "address": "2900 24th St, San Francisco, CA",
            "name": "Elena Rostova",
            "email": "elena.r@example.com",
            "phone": "555-0123",
            "days_ago": 5,
            "resolution_notes": "Waste management team dispatched on 2026-08-06. Tires and mattress successfully loaded into utility vehicle and transported to the hazardous waste recycling depot. Sidewalk washed clean.",
            "ai_reasoning": "Medium priority because it blocks the public sidewalk and creates a sanitary nuisance (attracting pests), but does not present immediate bodily harm.",
            "suggested_steps": "1. Schedule municipal heavy debris collection truck. 2. Load and transport items to municipal waste facility. 3. Send warning letter/inspect nearby CCTV footage."
        },
        {
            "title": "Broken Swings in Dolores Park",
            "description": "The chain on two of the child swings in the main playground is broken and hanging down. Kids might get hurt trying to play on them.",
            "category": "Parks & Public Spaces",
            "priority": "Medium",
            "status": "Resolved",
            "lat": 37.7596,
            "lon": -122.4269,
            "address": "Dolores Park, San Francisco, CA",
            "name": "David Miller",
            "email": "dmiller@example.com",
            "phone": "555-0133",
            "days_ago": 7,
            "resolution_notes": "Park rangers cordoned off the swing area. Maintenance crew replaced the heavy-duty swing chains and rubber seats on 2026-08-04. Swing set is fully safe and functional.",
            "ai_reasoning": "Medium priority. Affects public recreational equipment used by children, presenting a moderate safety hazard, but can be cordoned off easily.",
            "suggested_steps": "1. Lock/wrap warning tape around swing set. 2. Retrieve heavy-duty chain replacements. 3. Remove old chain links and secure new chains."
        },
        {
            "title": "Clogged Storm Drain Causing Minor Street Pooling",
            "description": "The storm drain at the corner of 20th and Mission is completely covered with dead leaves and garbage. Water is starting to pool about 2 inches deep. If it rains, the sidewalk will flood.",
            "category": "Water & Sanitation",
            "priority": "Medium",
            "status": "Assigned",
            "lat": 37.7587,
            "lon": -122.4191,
            "address": "2400 Mission St, San Francisco, CA",
            "name": "Sarah Jenkins",
            "email": "sarah.j@example.com",
            "phone": "555-0177",
            "days_ago": 3,
            "resolution_notes": "",
            "ai_reasoning": "Medium priority. Currently causing minor pooling, but poses elevated risk of localized street flooding if weather changes, which could block pedestrian crossings.",
            "suggested_steps": "1. Dispatch drainage clearance technician. 2. Clear surface debris (leaves, plastic waste). 3. Inspect underground grating for secondary blockage."
        },
        {
            "title": "Faded Crosswalk Markings at Busy Intersection",
            "description": "The paint on the crosswalk stripes at 18th and Guerrero has almost completely worn off. Drivers aren't stopping because they can barely see where the crosswalk begins.",
            "category": "Roads & Traffic",
            "priority": "Medium",
            "status": "In Progress",
            "lat": 37.7618,
            "lon": -122.4241,
            "address": "600 18th St, San Francisco, CA",
            "name": "Timothy Lee",
            "email": "tlee@example.com",
            "phone": "555-0151",
            "days_ago": 4,
            "resolution_notes": "",
            "ai_reasoning": "Medium priority. Traffic control safety issues, but can be resolved during normal operations rather than emergency response.",
            "suggested_steps": "1. Schedule road repainting crew for low-traffic hours. 2. Prepare high-visibility thermoplastic paint. 3. Cordon off lane during painting."
        },
        {
            "title": "Graffiti on Public Library Wall",
            "description": "The entire brick wall of the community library has been covered in spray paint graffiti overnight. It looks ugly and ruins the historic building face.",
            "category": "Parks & Public Spaces",
            "priority": "Low",
            "status": "Submitted",
            "lat": 37.7512,
            "lon": -122.4289,
            "address": "3800 24th St, San Francisco, CA",
            "name": "Helena V.",
            "email": "helena.v@example.com",
            "phone": "555-0112",
            "days_ago": 0,
            "resolution_notes": "",
            "ai_reasoning": "Low priority. Strictly cosmetic damage on a public building with no immediate threat to health, safety, or functional utility.",
            "suggested_steps": "1. Dispatch anti-graffiti detail. 2. Select appropriate solvent or paint-over shade. 3. Wash/repaint the affected library brick walls."
        },
        {
            "title": "Aggressive Raccoons in Playground Trash Cans",
            "description": "There is a family of raccoons nesting near the playground garbage bins. They hiss at children who walk past and tear garbage bags apart, scattering trash everywhere.",
            "category": "Waste Management",
            "priority": "Medium",
            "status": "In Progress",
            "lat": 37.7712,
            "lon": -122.4589,
            "address": "Golden Gate Park Playground, San Francisco, CA",
            "name": "Arthur Pendelton",
            "email": "arthur.p@example.com",
            "phone": "555-0163",
            "days_ago": 2,
            "resolution_notes": "",
            "ai_reasoning": "Medium priority due to health and safety risk of wild animal interactions in a child-centered playground environment, plus sanitary issues from scattered trash.",
            "suggested_steps": "1. Contact Animal Control for safe trapping/relocation. 2. Install raccoon-resistant animal-proof lids on all playground bins. 3. Cleanup loose litter."
        },
        {
            "title": "Fallen Tree Branch Blocking Sidewalk",
            "description": "A very large tree branch broke off and is lying completely across the sidewalk. Pedestrians, especially wheelchairs, have to walk in the busy street to bypass it.",
            "category": "Parks & Public Spaces",
            "priority": "High",
            "status": "Assigned",
            "lat": 37.7812,
            "lon": -122.4350,
            "address": "1800 Fillmore St, San Francisco, CA",
            "name": "Maria Sanchez",
            "email": "msanchez@example.com",
            "phone": "555-0176",
            "days_ago": 1,
            "resolution_notes": "",
            "ai_reasoning": "High priority assigned because it blocks ADA compliance (wheelchair access) on the sidewalk, forcing vulnerable pedestrians into a busy roadway.",
            "suggested_steps": "1. Send Park Maintenance crew. 2. Use chainsaws to cut branch into manageable logs. 3. Run logs through woodchipper and clear sidewalk."
        },
        {
            "title": "Suspicious Overloaded Power Pole Sparking",
            "description": "I noticed sparks coming from the transformer box on the wooden utility pole near the intersection. There are too many cables connected to it and it hums extremely loudly.",
            "category": "Electrical & Lighting",
            "priority": "Critical",
            "status": "Submitted",
            "lat": 37.7845,
            "lon": -122.4082,
            "address": "800 Howard St, San Francisco, CA",
            "name": "Gavin Lee",
            "email": "glee@example.com",
            "phone": "555-0105",
            "days_ago": 0,
            "resolution_notes": "",
            "ai_reasoning": "Critical priority because active electrical sparking and transformer load failure pose immediate high-risk of fire, power outage, or electrical shock.",
            "suggested_steps": "1. Alert PGE emergency electrical dispatch. 2. Evacuate/cordon off immediate base of the utility pole. 3. Shut off grid substation sector-9 for repair."
        }
    ]

    current_time = datetime.now()

    for item in mock_reports:
        # Create timestamps based on days_ago
        created = current_time - timedelta(days=item["days_ago"], hours=random.randint(1, 10))
        updated = created if item["status"] == "Submitted" else (created + timedelta(hours=random.randint(1, 12)))
        
        created_str = created.isoformat()
        updated_str = updated.isoformat()
        
        ai_data = {
            "category": item["category"],
            "priority": item["priority"],
            "urgency_score": random.randint(30, 45) if item["priority"] == "Low" else (
                             random.randint(46, 65) if item["priority"] == "Medium" else (
                             random.randint(66, 85) if item["priority"] == "High" else random.randint(86, 99))),
            "reasoning": item["ai_reasoning"],
            "suggested_steps": item["suggested_steps"],
            "estimated_hours": 4 if item["priority"] == "Critical" else (
                               12 if item["priority"] == "High" else (
                               48 if item["priority"] == "Medium" else 120)),
            "key_entities": [item["category"].split()[0], "infrastructure", item["address"].split(",")[0]]
        }
        
        assigned_team = teams.get(item["category"], "General Municipal Maintenance") if item["status"] != "Submitted" else None

        cursor.execute('''
            INSERT INTO complaints (
                title, description, category, priority, status, 
                latitude, longitude, address, reporter_name, reporter_email, reporter_phone, 
                ai_analysis, created_at, updated_at, resolution_notes, assigned_team
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item["title"], item["description"], item["category"], item["priority"], item["status"],
            item["lat"], item["lon"], item["address"], item["name"], item["email"], item["phone"],
            json.dumps(ai_data), created_str, updated_str, item["resolution_notes"], assigned_team
        ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database initialized and seeded with 11 realistic complaints.")
