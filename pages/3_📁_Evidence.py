import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import db_exists, get_all_evidence, get_connection, get_all_compliance_sources

st.set_page_config(page_title="Evidence Tracker - GRC Platform", layout="wide", page_icon="📁")

# Custom CSS
st.markdown("""
<style>
    .evidence-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .evidence-ref {
        background: rgba(21, 101, 192, 0.2);
        color: #64b5f6;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    .stat-box h2 {
        margin: 0;
        font-size: 2rem;
    }
    .stat-box p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    .source-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
        border: 1px solid rgba(76, 175, 80, 0.4);
    }
</style>
""", unsafe_allow_html=True)


def get_selected_source_ids() -> list:
    """Get list of selected compliance source IDs from session state."""
    return st.session_state.get('selected_sources', [])


def render_source_selector_sidebar():
    """Render the compliance source selector in sidebar."""
    if not db_exists():
        return
    
    try:
        sources = get_all_compliance_sources()
        
        if not sources:
            st.sidebar.info("📚 No compliance frameworks imported yet.")
            return
        
        st.sidebar.markdown("### 📚 Compliance Frameworks")
        
        source_options = {s['id']: f"{s['short_name'] or s['name']} ({s['control_count']} controls)" for s in sources}
        
        if 'selected_sources' not in st.session_state or not st.session_state.selected_sources:
            st.session_state.selected_sources = [s['id'] for s in sources if s.get('is_active', True)]
        
        selected = st.sidebar.multiselect(
            "Select frameworks to view",
            options=list(source_options.keys()),
            default=st.session_state.selected_sources,
            format_func=lambda x: source_options.get(x, str(x)),
            key="evidence_source_selector",
            help="Choose which compliance frameworks to include"
        )
        
        st.session_state.selected_sources = selected
        
        if selected:
            total_evidence = sum(s.get('evidence_count', 0) for s in sources if s['id'] in selected)
            st.sidebar.caption(f"📊 **{len(selected)}** frameworks | **{total_evidence}** evidence items")
        else:
            st.sidebar.warning("⚠️ No frameworks selected")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("All", use_container_width=True, key="ev_select_all"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("None", use_container_width=True, key="ev_clear_all"):
                st.session_state.selected_sources = []
                st.rerun()
        
        st.sidebar.markdown("---")
        
    except Exception as e:
        pass


def render_active_sources_banner(source_ids: list):
    """Render banner showing active compliance sources."""
    try:
        sources = get_all_compliance_sources()
        if sources and source_ids:
            selected_sources = [s for s in sources if s['id'] in source_ids]
            if selected_sources:
                badges = " ".join([
                    f'<span class="source-badge">{s["short_name"] or s["name"]}</span>'
                    for s in selected_sources
                ])
                st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <strong>📚 Active Frameworks:</strong> {badges}
                </div>
                """, unsafe_allow_html=True)
    except:
        pass


def get_evidence_stats(source_ids: list = None):
    """Get evidence statistics, filtered by source."""
    if not db_exists():
        return {'total': 0, 'linked': 0, 'orphan': 0, 'domains': 0}
    
    with get_connection() as conn:
        # Check if source_id column exists
        cursor = conn.execute("PRAGMA table_info(evidence)")
        columns = [row[1] for row in cursor.fetchall()]
        has_source_id = 'source_id' in columns
        
        # Build filter
        source_filter = ""
        params = []
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            source_filter = f"WHERE source_id IN ({placeholders})"
            params = source_ids
        
        total = conn.execute(f"SELECT COUNT(*) FROM evidence {source_filter}", params).fetchone()[0]
        
        if has_source_id and source_ids:
            linked = conn.execute(f"""
                SELECT COUNT(DISTINCT e.id) 
                FROM evidence e
                JOIN control_evidence ce ON e.id = ce.evidence_id
                WHERE e.source_id IN ({placeholders})
            """, params).fetchone()[0]
            
            domains = conn.execute(f"""
                SELECT COUNT(DISTINCT domain) 
                FROM evidence 
                WHERE domain IS NOT NULL AND TRIM(domain) != ''
                AND source_id IN ({placeholders})
            """, params).fetchone()[0]
        else:
            linked = conn.execute("""
                SELECT COUNT(DISTINCT e.id) 
                FROM evidence e
                JOIN control_evidence ce ON e.id = ce.evidence_id
            """).fetchone()[0]
            
            domains = conn.execute("""
                SELECT COUNT(DISTINCT domain) 
                FROM evidence 
                WHERE domain IS NOT NULL AND TRIM(domain) != ''
            """).fetchone()[0]
        
        orphan = total - linked
        
        return {
            'total': total,
            'linked': linked,
            'orphan': orphan,
            'domains': domains
        }


def get_evidence_by_domain(source_ids: list = None):
    """Get evidence grouped by domain, filtered by source."""
    if not db_exists():
        return pd.DataFrame()
    
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(evidence)")
        columns = [row[1] for row in cursor.fetchall()]
        has_source_id = 'source_id' in columns
        
        query = """
            SELECT 
                COALESCE(domain, 'Unassigned') as domain,
                COUNT(*) as count
            FROM evidence
        """
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" WHERE source_id IN ({placeholders})"
            params = source_ids
        
        query += " GROUP BY domain ORDER BY count DESC"
        
        return pd.read_sql(query, conn, params=params)


def get_evidence_with_controls(source_ids: list = None, search: str = None):
    """Get evidence with linked control counts, filtered by source."""
    if not db_exists():
        return pd.DataFrame()
    
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(evidence)")
        columns = [row[1] for row in cursor.fetchall()]
        has_source_id = 'source_id' in columns
        
        query = """
            SELECT 
                e.ref_id,
                e.title,
                e.domain,
                COUNT(ce.control_id) as linked_controls
        """
        
        if has_source_id:
            query += ", cs.short_name as source"
        
        query += """
            FROM evidence e
            LEFT JOIN control_evidence ce ON e.id = ce.evidence_id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON e.source_id = cs.id"
        
        query += " WHERE 1=1"
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND e.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        if search and search.strip():
            query += " AND (e.ref_id LIKE ? OR e.title LIKE ? OR e.domain LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s])
        
        query += " GROUP BY e.id ORDER BY e.ref_id"
        
        return pd.read_sql(query, conn, params=params)


def get_controls_for_evidence(ref_id: str, source_ids: list = None):
    """Get all controls linked to a specific evidence item."""
    if not db_exists():
        return pd.DataFrame()
    
    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(controls)")
        columns = [row[1] for row in cursor.fetchall()]
        has_source_id = 'source_id' in columns
        
        query = """
            SELECT 
                c.ccf_id,
                c.title,
                d.name as domain
        """
        
        if has_source_id:
            query += ", cs.short_name as source"
        
        query += """
            FROM controls c
            JOIN control_evidence ce ON c.id = ce.control_id
            JOIN evidence e ON ce.evidence_id = e.id
            LEFT JOIN domains d ON c.domain_id = d.id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON c.source_id = cs.id"
        
        query += " WHERE e.ref_id = ?"
        params = [ref_id]
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND c.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        query += " ORDER BY c.ccf_id"
        
        return pd.read_sql(query, conn, params=params)


def main():
    # Sidebar source selector
    render_source_selector_sidebar()
    
    st.title("📁 Evidence Tracker")
    st.caption("Manage and track evidence artifacts for compliance controls")
    
    if not db_exists():
        st.warning("⚠️ No database found. Please seed your data first.")
        return
    
    # Get selected source IDs
    source_ids = get_selected_source_ids()
    
    # Show active sources banner
    render_active_sources_banner(source_ids)
    
    if not source_ids:
        sources = get_all_compliance_sources()
        if sources:
            st.warning("⚠️ No compliance frameworks selected. Please select at least one from the sidebar.")
            return
    
    # -----------------------
    # Statistics Row
    # -----------------------
    stats = get_evidence_stats(source_ids if source_ids else None)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <h2>{stats['total']}</h2>
            <p>Total Evidence Items</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h2>{stats['linked']}</h2>
            <p>Linked to Controls</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h2>{stats['orphan']}</h2>
            <p>Orphan Evidence</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <h2>{stats['domains']}</h2>
            <p>Evidence Domains</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # -----------------------
    # Tabs
    # -----------------------
    tab1, tab2, tab3 = st.tabs(["📋 Evidence List", "📊 By Domain", "🔗 Evidence Details"])
    
    with tab1:
        # Search
        search = st.text_input("🔍 Search evidence", placeholder="Search by ref ID, title, or domain...")
        
        # Get data
        evidence_df = get_evidence_with_controls(source_ids if source_ids else None, search)
        
        if evidence_df.empty:
            st.info("No evidence items found.")
        else:
            # Filters
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                domains = evidence_df['domain'].dropna().unique().tolist()
                selected_domain = st.selectbox("Filter by Domain", ["All"] + domains)
            
            with filter_col2:
                link_filter = st.selectbox(
                    "Filter by Status",
                    ["All", "Linked", "Orphan (Not Linked)"]
                )
            
            # Apply filters
            filtered_df = evidence_df.copy()
            
            if selected_domain != "All":
                filtered_df = filtered_df[filtered_df['domain'] == selected_domain]
            
            if link_filter == "Linked":
                filtered_df = filtered_df[filtered_df['linked_controls'] > 0]
            elif link_filter == "Orphan (Not Linked)":
                filtered_df = filtered_df[filtered_df['linked_controls'] == 0]
            
            # Build display columns
            display_cols = ['ref_id', 'title', 'domain', 'linked_controls']
            if 'source' in filtered_df.columns:
                display_cols = ['source'] + display_cols
            
            display_cols = [c for c in display_cols if c in filtered_df.columns]
            
            # Rename for display
            col_rename = {
                'source': 'Framework',
                'ref_id': 'Reference ID',
                'title': 'Title',
                'domain': 'Domain',
                'linked_controls': 'Linked Controls'
            }
            
            display_df = filtered_df[display_cols].copy()
            display_df.columns = [col_rename.get(c, c) for c in display_df.columns]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export
            st.download_button(
                "⬇️ Download Evidence List",
                data=filtered_df.to_csv(index=False),
                file_name="evidence_list.csv",
                mime="text/csv"
            )
    
    with tab2:
        # Evidence by domain chart
        domain_df = get_evidence_by_domain(source_ids if source_ids else None)
        
        if not domain_df.empty:
            import plotly.express as px
            
            fig = px.bar(
                domain_df,
                x='domain',
                y='count',
                color='count',
                color_continuous_scale='Blues',
                labels={'domain': 'Domain', 'count': 'Evidence Items'}
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                xaxis_tickangle=-45
            )
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Table
            st.dataframe(
                domain_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'domain': st.column_config.TextColumn('Domain', width='large'),
                    'count': st.column_config.NumberColumn('Evidence Items', width='medium')
                }
            )
        else:
            st.info("No evidence data available.")
    
    with tab3:
        # Evidence detail view
        evidence_df = get_evidence_with_controls(source_ids if source_ids else None)
        
        if evidence_df.empty:
            st.info("No evidence items available.")
        else:
            selected_ref = st.selectbox(
                "Select Evidence Item",
                evidence_df['ref_id'].tolist(),
                format_func=lambda x: f"{x} - {evidence_df[evidence_df['ref_id']==x]['title'].values[0] if not evidence_df[evidence_df['ref_id']==x].empty else ''}"
            )
            
            if selected_ref:
                # Get evidence details
                ev_row = evidence_df[evidence_df['ref_id'] == selected_ref].iloc[0]
                
                st.markdown("---")
                
                # Evidence info
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.markdown(f"### {ev_row['ref_id']}")
                    st.markdown(f"**Title:** {ev_row['title'] or 'No title'}")
                    st.markdown(f"**Domain:** {ev_row['domain'] or 'Unassigned'}")
                    if 'source' in ev_row and ev_row['source']:
                        st.markdown(f"**Framework:** {ev_row['source']}")
                
                with info_col2:
                    st.metric("Linked Controls", ev_row['linked_controls'])
                
                # Linked controls
                st.markdown("### Linked Controls")
                
                controls_df = get_controls_for_evidence(selected_ref, source_ids if source_ids else None)
                
                if controls_df.empty:
                    st.warning("This evidence item is not linked to any controls (orphan).")
                else:
                    # Build display columns
                    ctrl_cols = ['ccf_id', 'title', 'domain']
                    if 'source' in controls_df.columns:
                        ctrl_cols = ['source'] + ctrl_cols
                    
                    ctrl_cols = [c for c in ctrl_cols if c in controls_df.columns]
                    
                    st.dataframe(
                        controls_df[ctrl_cols],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Export
                    st.download_button(
                        f"⬇️ Download Controls for {selected_ref}",
                        data=controls_df.to_csv(index=False),
                        file_name=f"controls_for_{selected_ref}.csv",
                        mime="text/csv"
                    )


if __name__ == "__main__":
    main()