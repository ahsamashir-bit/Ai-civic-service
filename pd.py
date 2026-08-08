import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import database
import ai_engine
import json
import os
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(
    page_title="CivicAI Smart Services",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure DB is initialized
if not os.path.exists(database.DB_PATH):
    database.init_db()
    database.seed_db()

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Custom Styling for Streamlit App */
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
    }
    
    /* Headers styling */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }
    
    /* Glowing sidebar status */
    .sidebar-status {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.2);
        padding: 0.75rem;
        border-radius: 8px;
        margin-top: 2rem;
        font-size: 0.85rem;
    }
    
    /* Custom Glassmorphic Cards */
    .glass-card {
        background: rgba(19, 27, 46, 0.7);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    /* Custom Badges */
    .prio-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 0.5rem;
    }
    .badge-critical { background: rgba(255, 77, 109, 0.15); color: #ff4d6d; border: 1px solid rgba(255, 77, 109, 0.3); }
    .badge-high { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-medium { background: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); }
    .badge-low { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
    
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .status-submitted { background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }
    .status-assigned { background: rgba(99, 102, 241, 0.15); color: #6366f1; border: 1px solid rgba(99, 102, 241, 0.3); }
    .status-inprogress { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .status-resolved { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }

    /* AI panel styling */
    .ai-container {
        background: rgba(99, 102, 241, 0.05);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.markdown(
    "<h2 style='text-align: center; margin-bottom: 1.5rem; background: linear-gradient(to right, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>CivicAI</h2>", 
    unsafe_allow_html=True
)

page = st.sidebar.radio(
    "Navigation Menu",
    ["📝 Citizen Portal", "🏢 Operations Service Desk", "📊 Analytical Insights", "⚙️ System Settings"]
)

st.sidebar.markdown(
    """
    <div class="sidebar-status">
        <span style="color: #10b981;">●</span> All City Nodes Operational<br>
        <span style="color: #94a3b8; font-size: 0.75rem;">Database: SQLite Active</span>
    </div>
    """, 
    unsafe_allow_html=True
)

# Fetch latest data from sqlite
def get_all_complaints():
    conn = database.get_db_connection()
    df = pd.read_sql_query("SELECT * FROM complaints ORDER BY created_at DESC", conn)
    conn.close()
    return df

# --- Page 1: Citizen Portal ---
if page == "📝 Citizen Portal":
    st.markdown("<h1 style='margin-bottom: 0.5rem;'>Submit a Civic Complaint</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; margin-bottom: 2rem;'>Report neighborhood issues. Our AI classifies, prioritizes, and routes your request instantly.</p>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["File a New Report", "Track Existing Report"])

    with tab1:
        st.subheader("Issue Details")
        
        # Form inputs
        col1, col2 = st.columns([2, 1])
        
        with col1:
            title = st.text_input("Title / Short Summary", placeholder="e.g., Clogged storm drain on Mission St")
            description = st.text_area("Detailed Description", placeholder="Describe the issue, dimensions, accessibility issues, or urgency details...")
            address = st.text_input("Address / Location Reference", placeholder="1200 Market St, San Francisco, CA")
            
        with col2:
            lat = st.number_input("Latitude", value=37.7749, format="%.6f")
            lng = st.number_input("Longitude", value=-122.4194, format="%.6f")
            st.info("💡 Tip: You can look up coordinates for your spot in Google Maps or use SF coordinates (37.75 to 37.80, -122.40 to -122.48).")
            
        st.subheader("Contact Information (Optional)")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Full Name", placeholder="Jane Doe")
        email = c2.text_input("Email", placeholder="jane@example.com")
        phone = c3.text_input("Phone", placeholder="555-0199")
        
        if st.button("Submit to CivicAI Desk", type="primary"):
            if not title or not description:
                st.error("Please fill in the title and description.")
            else:
                with st.spinner("AI analyzing and classifying complaint..."):
                    # 1. Analyze with AI
                    ai_res = ai_engine.analyze_complaint(title, description)
                    
                    # 2. Extract values
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
                        lat, lng, address, name, email, phone,
                        json.dumps(ai_res), created_at, created_at
                    ))
                    new_id = cursor.lastrowid
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Report Submitted Successfully! Reference ID: REF #{new_id}")
                    
                    # AI Receipt Card
                    st.markdown(f"""
                    <div class="glass-card">
                        <h3 style="color: #10b981; margin-bottom: 1rem;"><i class="fa-solid fa-circle-check"></i> AI Diagnostic Receipt</h3>
                        <p><strong>Reference:</strong> REF #{new_id}</p>
                        <div style="margin-bottom: 1rem;">
                            <strong>Category:</strong> <span class="prio-badge badge-medium">{category}</span>
                            <strong>Priority:</strong> <span class="prio-badge badge-{priority.lower()}">{priority}</span>
                        </div>
                        <p><strong>Response SLA:</strong> {ai_res.get('estimated_hours', 48)} Hours SLA Target</p>
                        <div class="ai-container">
                            <strong style="color: #818cf8;">AI Reasoning:</strong>
                            <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.25rem;">{ai_res.get('reasoning')}</p>
                        </div>
                        <div class="ai-container" style="border-color: rgba(168, 85, 247, 0.2);">
                            <strong style="color: #a855f7;">Recommended Actions:</strong>
                            <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.25rem; white-space: pre-line;">{ai_res.get('suggested_steps')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.subheader("Track Complaint Status")
        track_id = st.number_input("Enter Complaint ID", min_value=1, step=1)
        if st.button("Query Database"):
            conn = database.get_db_connection()
            row = conn.execute("SELECT * FROM complaints WHERE id = ?", (track_id,)).fetchone()
            conn.close()
            
            if row:
                st.markdown(f"### Complaint details: {row['title']}")
                
                # Badges
                st.markdown(f"""
                <div style="margin-bottom: 1.5rem;">
                    <strong>Category:</strong> <span class="prio-badge badge-medium">{row['category']}</span>
                    <strong>Status:</strong> <span class="status-badge status-{row['status'].replace(" ", "").lower()}">{row['status']}</span>
                    <strong>Priority:</strong> <span class="prio-badge badge-{row['priority'].lower()}">{row['priority']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Description:** {row['description']}")
                    st.write(f"**Address:** {row['address']}")
                with col2:
                    st.write(f"**Assigned Team:** {row['assigned_team'] or 'Not yet assigned'}")
                    if row['resolution_notes']:
                        st.info(f"**Resolution Notes:** {row['resolution_notes']}")
                    else:
                        st.write("**Resolution Notes:** No updates recorded.")
            else:
                st.error("Complaint ID not found. Please verify the ID.")

# --- Page 2: Operations Service Desk ---
elif page == "🏢 Operations Service Desk":
    st.markdown("<h1>Operations Service Desk</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Review AI triage data, dispatch maintenance teams, and update statuses.</p>", unsafe_allow_html=True)
    
    df = get_all_complaints()
    
    if df.empty:
        st.info("No complaints found in the system. Go to settings to seed sample data.")
    else:
        # KPI row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total = len(df)
        resolved = len(df[df['status'] == 'Resolved'])
        pending = len(df[df['status'] == 'Submitted'])
        critical = len(df[(df['priority'] == 'Critical') & (df['status'] != 'Resolved')])
        
        kpi1.metric("Total Reports", total)
        kpi2.metric("Critical Backlog", critical)
        kpi3.metric("Pending Triage", pending)
        kpi4.metric("Resolution Rate", f"{round(resolved / total * 100 if total > 0 else 0, 1)}%")

        # Filters
        st.subheader("Filter Reports")
        f1, f2, f3 = st.columns(3)
        cat_filter = f1.selectbox("Filter Category", ["All"] + list(df['category'].unique()))
        prio_filter = f2.selectbox("Filter Priority", ["All", "Low", "Medium", "High", "Critical"])
        stat_filter = f3.selectbox("Filter Status", ["All", "Submitted", "Assigned", "In Progress", "Resolved"])
        
        filtered_df = df.copy()
        if cat_filter != "All":
            filtered_df = filtered_df[filtered_df['category'] == cat_filter]
        if prio_filter != "All":
            filtered_df = filtered_df[filtered_df['priority'] == prio_filter]
        if stat_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == stat_filter]
            
        # Display split
        col_list, col_detail = st.columns([3, 2])
        
        with col_list:
            st.subheader("Service Desk List")
            # Create selector list
            options = [f"#{row['id']} - {row['title']} ({row['priority']})" for idx, row in filtered_df.iterrows()]
            if not options:
                st.write("No complaints match selected filters.")
                selected_row_idx = None
            else:
                selected_option = st.selectbox("Select complaint to edit:", options)
                selected_id = int(selected_option.split(" - ")[0].replace("#", ""))
                selected_row = filtered_df[filtered_df['id'] == selected_id].iloc[0]
                selected_row_idx = selected_row['id']
                
                # Render mini table for visualization
                display_table = filtered_df[['id', 'title', 'category', 'priority', 'status']].copy()
                st.dataframe(display_table, use_container_width=True, hide_index=True)
                
        with col_detail:
            if selected_row_idx:
                # Reload row to ensure fresh database values
                conn = database.get_db_connection()
                fresh_row = conn.execute("SELECT * FROM complaints WHERE id = ?", (int(selected_row_idx),)).fetchone()
                conn.close()
                
                st.subheader(f"REF #{fresh_row['id']} details")
                st.markdown(f"### {fresh_row['title']}")
                
                # Status & Priority badges
                st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <span class="status-badge status-{fresh_row['status'].replace(" ", "").lower()}">{fresh_row['status']}</span>
                    <span class="prio-badge badge-{fresh_row['priority'].lower()}">{fresh_row['priority']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Description
                st.write(f"**Description:** {fresh_row['description']}")
                st.write(f"**Address:** {fresh_row['address']}")
                
                # AI info
                ai_data = {}
                if fresh_row['ai_analysis']:
                    try:
                        ai_data = json.loads(fresh_row['ai_analysis'])
                    except:
                        pass
                
                st.markdown(f"""
                <div class="ai-container">
                    <strong style="color: #818cf8;"><i class="fa-solid fa-brain"></i> AI Diagnostics</strong><br>
                    <strong>Urgency Score:</strong> {ai_data.get('urgency_score', '--')}% | <strong>SLA:</strong> {ai_data.get('estimated_hours', '--')} Hours<br>
                    <p style="font-size:0.85rem; color:#cbd5e1; margin-top:0.5rem;">{ai_data.get('reasoning', '')}</p>
                    <p style="font-size:0.85rem; color:#a855f7; white-space: pre-line; margin-top:0.5rem;">{ai_data.get('suggested_steps', '')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Map point
                if fresh_row['latitude'] and fresh_row['longitude']:
                    map_df = pd.DataFrame({
                        'lat': [fresh_row['latitude']],
                        'lon': [fresh_row['longitude']]
                    })
                    st.map(map_df, zoom=14, use_container_width=True)
                
                # Update Operations form
                st.subheader("Operations Control")
                u_status = st.selectbox("Update Status", ["Submitted", "Assigned", "In Progress", "Resolved"], index=["Submitted", "Assigned", "In Progress", "Resolved"].index(fresh_row['status']))
                u_team = st.selectbox("Assign Team", ["", "Roads & Infrastructure Team", "Municipal Water Utility Dept", "Sanitation & Recycling Division", "Grid and Lighting Maintenance", "Parks & Recreation Department", "Community Safety & Transit Security"], index=["", "Roads & Infrastructure Team", "Municipal Water Utility Dept", "Sanitation & Recycling Division", "Grid and Lighting Maintenance", "Parks & Recreation Department", "Community Safety & Transit Security"].index(fresh_row['assigned_team'] or ""))
                u_notes = st.text_area("Resolution Notes", value=fresh_row['resolution_notes'] or "")
                
                if st.button("Commit Updates"):
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE complaints
                        SET status = ?, assigned_team = ?, resolution_notes = ?, updated_at = ?
                        WHERE id = ?
                    ''', (u_status, u_team, u_notes, datetime.now().isoformat(), fresh_row['id']))
                    conn.commit()
                    conn.close()
                    st.success("Updates successfully committed to database!")
                    st.rerun()

# --- Page 3: Analytical Insights ---
elif page == "📊 Analytical Insights":
    st.markdown("<h1>Analytical Insights</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Analyze spatial hotspots and SLA performance trends.</p>", unsafe_allow_html=True)
    
    df = get_all_complaints()
    
    if df.empty:
        st.info("No complaints found to analyze.")
    else:
        # Spatial Map
        st.subheader("Spatial Distribution Map")
        fig_map = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            hover_name="title",
            hover_data=["category", "priority", "status"],
            color="priority",
            color_discrete_map={"Low": "#94a3b8", "Medium": "#06b6d4", "High": "#f59e0b", "Critical": "#ff4d6d"},
            zoom=12,
            height=450
        )
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # Bottom charts
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Category Distribution")
            cat_counts = df['category'].value_counts()
            fig_cat = px.pie(
                values=cat_counts.values,
                names=cat_counts.index,
                hole=0.4,
                color_discrete_sequence=['#6366f1', '#06b6d4', '#a855f7', '#f59e0b', '#10b981', '#ff4d6d']
            )
            fig_cat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8'
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
        with c2:
            st.subheader("Urgency Breakdown")
            prio_counts = df['priority'].value_counts()
            fig_prio = px.bar(
                x=prio_counts.index,
                y=prio_counts.values,
                labels={'x': 'Priority Level', 'y': 'Count'},
                color=prio_counts.index,
                color_discrete_map={"Low": "#94a3b8", "Medium": "#06b6d4", "High": "#f59e0b", "Critical": "#ff4d6d"}
            )
            fig_prio.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                showlegend=False
            )
            st.plotly_chart(fig_prio, use_container_width=True)

        c3, c4 = st.columns(2)
        
        with c3:
            st.subheader("Complaint Volume Trend")
            df['date'] = df['created_at'].str.slice(0, 10)
            trend_df = df.groupby('date').size().reset_index(name='count')
            fig_trend = px.line(
                trend_df,
                x='date',
                y='count',
                labels={'date': 'Date', 'count': 'Complaints'},
                markers=True
            )
            fig_trend.update_traces(line_color='#10b981')
            fig_trend.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8'
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with c4:
            st.subheader("SLA targets by Category")
            categories = ["Roads & Traffic", "Water & Sanitation", "Waste Management", "Electrical & Lighting", "Parks & Public Spaces", "Public Safety"]
            sla_hours = [48, 12, 48, 24, 120, 4]
            fig_sla = px.bar(
                x=categories,
                y=sla_hours,
                labels={'x': 'Department Category', 'y': 'Target SLA Hours'},
                color=categories,
                color_discrete_sequence=['#6366f1', '#06b6d4', '#a855f7', '#f59e0b', '#10b981', '#ff4d6d']
            )
            fig_sla.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                showlegend=False
            )
            st.plotly_chart(fig_sla, use_container_width=True)

# --- Page 4: System Settings ---
elif page == "⚙️ System Settings":
    st.markdown("<h1>Settings & Configuration</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Manage AI credentials and system database seeding.</p>", unsafe_allow_html=True)
    
    st.subheader("AI Credentials")
    openai_key = database.get_setting("openai_api_key", "")
    gemini_key = database.get_setting("gemini_api_key", "")
    
    u_gemini = st.text_input("Google Gemini API Key", value=gemini_key, type="password", placeholder="AIzaSy...")
    u_openai = st.text_input("OpenAI API Key", value=openai_key, type="password", placeholder="sk-proj-...")
    
    if st.button("Save Credentials", type="primary"):
        database.save_setting("openai_api_key", u_openai)
        database.save_setting("gemini_api_key", u_gemini)
        st.success("API credentials saved successfully!")
        
    st.markdown("---")
    st.subheader("Administrative Controls")
    st.warning("⚠️ Warning: Seeding the database will wipe all current reports and generate 11 realistic mock complaints across San Francisco.")
    
    if st.button("Reset & Seed Database"):
        with st.spinner("Seeding database..."):
            database.seed_db()
            st.success("Database has been reset and seeded with 11 complaints!")
            st.rerun()
