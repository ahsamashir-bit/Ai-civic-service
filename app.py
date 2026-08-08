from flask import Flask, render_template, request, jsonify, redirect, url_for
import database
import ai_engine
import json
import os
from datetime import datetime

app = Flask(__name__)

# Ensure DB is initialized and seeded if empty on startup
if not os.path.exists(database.DB_PATH):
    print("Database not found. Initializing...")
    database.init_db()
    database.seed_db()
else:
    # Check if empty, seed if empty
    conn = database.get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    conn.close()
    if count == 0:
        print("Database is empty. Seeding...")
        database.seed_db()

@app.route('/')
def citizen_portal():
    return render_template('citizen_portal.html')

@app.route('/admin')
def admin_dashboard():
    # Fetch all complaints to display in table/map
    conn = database.get_db_connection()
    complaints = conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()
    
    # Calculate quick metrics
    total = len(complaints)
    resolved = len([c for c in complaints if c['status'] == 'Resolved'])
    pending = len([c for c in complaints if c['status'] == 'Submitted'])
    in_progress = len([c for c in complaints if c['status'] in ['Assigned', 'In Progress']])
    critical = len([c for c in complaints if c['priority'] == 'Critical' and c['status'] != 'Resolved'])
    
    # Convert list of rows to serializable dicts
    complaints_list = []
    for c in complaints:
        cdict = dict(c)
        # Parse AI analysis json string
        if cdict.get('ai_analysis'):
            try:
                cdict['ai_analysis'] = json.loads(cdict['ai_analysis'])
            except:
                cdict['ai_analysis'] = {}
        complaints_list.append(cdict)
        
    conn.close()
    
    metrics = {
        'total': total,
        'resolved': resolved,
        'pending': pending,
        'in_progress': in_progress,
        'critical': critical,
        'resolved_rate': round((resolved / total * 100) if total > 0 else 0, 1)
    }
    
    return render_template('admin_dashboard.html', complaints=complaints_list, metrics=metrics)

@app.route('/analytics')
def analytics():
    # We will pass raw data to front-end for Chart.js rendering
    conn = database.get_db_connection()
    complaints = conn.execute("SELECT * FROM complaints").fetchall()
    conn.close()
    
    complaints_list = []
    for c in complaints:
        cdict = dict(c)
        if cdict.get('ai_analysis'):
            try:
                cdict['ai_analysis'] = json.loads(cdict['ai_analysis'])
            except:
                cdict['ai_analysis'] = {}
        complaints_list.append(cdict)
        
    return render_template('analytics.html', complaints=complaints_list)

@app.route('/settings')
def settings_page():
    openai_key = database.get_setting("openai_api_key", "")
    gemini_key = database.get_setting("gemini_api_key", "")
    return render_template('settings.html', openai_key=openai_key, gemini_key=gemini_key)

# API ENDPOINTS
@app.route('/api/complaints', methods=['POST'])
def create_complaint():
    try:
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address', '').strip()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not title or not description:
            return jsonify({"error": "Title and description are required"}), 400
            
        # 1. Run AI analysis
        ai_res = ai_engine.analyze_complaint(title, description)
        
        # 2. Extract classified values
        category = ai_res.get('category', 'Roads & Traffic')
        priority = ai_res.get('priority', 'Low')
        
        # 3. Save to database
        conn = database.get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO complaints (
                title, description, category, priority, status, 
                latitude, longitude, address, reporter_name, reporter_email, reporter_phone, 
                ai_analysis, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title, description, category, priority, 'Submitted',
            latitude, longitude, address, name, email, phone,
            json.dumps(ai_res), created_at, created_at
        ))
        complaint_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        response_data = {
            "id": complaint_id,
            "title": title,
            "category": category,
            "priority": priority,
            "ai_analysis": ai_res,
            "created_at": created_at
        }
        return jsonify(response_data), 201
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/complaints/<int:cid>', methods=['GET'])
def get_complaint(cid):
    conn = database.get_db_connection()
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", (cid,)).fetchone()
    conn.close()
    
    if not row:
        return jsonify({"error": "Complaint not found"}), 404
        
    cdict = dict(row)
    if cdict.get('ai_analysis'):
        try:
            cdict['ai_analysis'] = json.loads(cdict['ai_analysis'])
        except:
            cdict['ai_analysis'] = {}
            
    return jsonify(cdict)

@app.route('/api/complaints/<int:cid>', methods=['PATCH'])
def update_complaint(cid):
    try:
        data = request.json
        status = data.get('status')
        assigned_team = data.get('assigned_team')
        resolution_notes = data.get('resolution_notes')
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Check if exists
        row = cursor.execute("SELECT * FROM complaints WHERE id = ?", (cid,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Complaint not found"}), 404
            
        update_fields = []
        params = []
        
        if status:
            update_fields.append("status = ?")
            params.append(status)
        if assigned_team:
            update_fields.append("assigned_team = ?")
            params.append(assigned_team)
        if resolution_notes is not None:
            update_fields.append("resolution_notes = ?")
            params.append(resolution_notes)
            
        if update_fields:
            update_fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            params.append(cid)
            query = f"UPDATE complaints SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
        # Refetch
        updated_row = cursor.execute("SELECT * FROM complaints WHERE id = ?", (cid,)).fetchone()
        conn.close()
        
        udict = dict(updated_row)
        if udict.get('ai_analysis'):
            udict['ai_analysis'] = json.loads(udict['ai_analysis'])
            
        return jsonify(udict)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def save_settings():
    try:
        data = request.json
        openai_key = data.get('openai_api_key', '')
        gemini_key = data.get('gemini_api_key', '')
        
        database.save_setting("openai_api_key", openai_key)
        database.save_setting("gemini_api_key", gemini_key)
        
        return jsonify({"message": "Settings saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/seed', methods=['POST'])
def reseed_database():
    try:
        database.seed_db()
        return jsonify({"message": "Database successfully re-seeded with sample complaints."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
