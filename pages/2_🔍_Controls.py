import streamlit as st
import pandas as pd
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    db_exists, search_controls, get_control_by_id,
    get_all_domains, get_all_control_types, get_all_themes, get_all_frameworks,
    get_all_compliance_sources
)

st.set_page_config(page_title="Controls Browser - GRC Platform", layout="wide", page_icon="🔍")

# Custom CSS
st.markdown("""
<style>
    .control-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .control-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    .control-id {
        background: rgba(21, 101, 192, 0.2);
        color: #64b5f6;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .control-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .control-domain {
        color: #9e9e9e;
        font-size: 0.9rem;
    }
    .tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .tag-type {
        background: rgba(46, 125, 50, 0.2);
        color: #81c784;
    }
    .tag-theme {
        background: rgba(239, 108, 0, 0.2);
        color: #ffb74d;
    }
    .tag-framework {
        background: rgba(123, 31, 162, 0.2);
        color: #ce93d8;
    }
    .tag-source {
        background: rgba(21, 101, 192, 0.2);
        color: #64b5f6;
    }
    .evidence-badge {
        background: rgba(21, 101, 192, 0.2);
        color: #64b5f6;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
    }
    .highlight {
        background-color: rgba(255, 245, 157, 0.3);
        padding: 2px 4px;
        border-radius: 3px;
    }
    .guidance-box {
        background: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }
    .testing-box {
        background: rgba(255, 152, 0, 0.1);
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }
    .search-highlight {
        background: linear-gradient(120deg, rgba(255, 234, 167, 0.3) 0%, rgba(253, 203, 110, 0.3) 100%);
        padding: 2px 4px;
        border-radius: 3px;
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
            key="controls_source_selector",
            help="Choose which compliance frameworks to include"
        )
        
        st.session_state.selected_sources = selected
        
        total_controls = sum(s['control_count'] for s in sources if s['id'] in selected)
        
        if selected:
            st.sidebar.caption(f"📊 **{len(selected)}** frameworks | **{total_controls}** controls")
        else:
            st.sidebar.warning("⚠️ No frameworks selected")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("All", use_container_width=True, key="ctrl_select_all"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("None", use_container_width=True, key="ctrl_clear_all"):
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


def highlight_text(text: str, search_term: str) -> str:
    """Highlight search terms in text."""
    if not text or not search_term:
        return text or ""
    
    pattern = re.compile(f'({re.escape(search_term)})', re.IGNORECASE)
    return pattern.sub(r'<span class="search-highlight">\1</span>', text)


def render_control_card(control: dict, search_term: str = None, expanded: bool = False):
    """Render a control as a card."""
    ccf_id = control.get('ccf_id', '')
    title = control.get('title', 'Untitled')
    description = control.get('description', '')
    domain = control.get('domain', 'Unknown Domain')
    ctrl_type = control.get('type', '')
    theme = control.get('theme', '')
    evidence_count = control.get('evidence_count', 0)
    source_name = control.get('source_short') or control.get('source_name', '')
    
    # Highlight search terms
    if search_term:
        title = highlight_text(title, search_term)
        description = highlight_text(description, search_term)
    
    # Build header with source badge if available
    header = f"**{ccf_id}** — {title}"
    if source_name:
        header = f"**{ccf_id}** [{source_name}] — {title}"
    
    with st.expander(header, expanded=expanded):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**Domain:** {domain}")
            st.markdown(f"**Description:** {description}", unsafe_allow_html=True)
            
            # Tags
            tags_html = ""
            if source_name:
                tags_html += f'<span class="tag tag-source">{source_name}</span>'
            if ctrl_type:
                tags_html += f'<span class="tag tag-type">{ctrl_type}</span>'
            if theme:
                tags_html += f'<span class="tag tag-theme">{theme}</span>'
            
            if tags_html:
                st.markdown(tags_html, unsafe_allow_html=True)
        
        with col2:
            st.metric("Evidence Items", evidence_count)
            
            if st.button("View Details", key=f"view_{ccf_id}", use_container_width=True):
                st.session_state.selected_control = ccf_id
                st.session_state.show_detail = True
                st.rerun()


def render_control_detail(ccf_id: str):
    """Render detailed view of a control."""
    control = get_control_by_id(ccf_id)
    
    if not control:
        st.error("Control not found")
        return
    
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"## {control['ccf_id']}")
        st.markdown(f"### {control['title']}")
        # Show source if available
        if control.get('source_name'):
            st.caption(f"📚 Framework: **{control['source_name']}**")
    with col2:
        if st.button("← Back to List", use_container_width=True):
            st.session_state.show_detail = False
            st.rerun()
    
    # Metadata row
    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
    
    with meta_col1:
        st.markdown(f"**Domain**")
        st.info(control.get('domain_name') or 'Not specified')
    
    with meta_col2:
        st.markdown(f"**Type**")
        st.info(control.get('type') or 'Not specified')
    
    with meta_col3:
        st.markdown(f"**Theme**")
        st.info(control.get('theme') or 'Not specified')
    
    with meta_col4:
        st.markdown(f"**Evidence Items**")
        evidence = control.get('evidence', [])
        st.info(len(evidence))
    
    st.markdown("---")
    
    # Description
    st.markdown("### Description")
    st.write(control.get('description') or 'No description available.')
    
    st.markdown("---")
    
    # Tabs for detailed information
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Guidance", "🧪 Testing", "🗺️ Mappings", "📁 Evidence"])
    
    with tab1:
        guidance = control.get('guidance')
        if guidance:
            st.markdown(f"""
            <div class="guidance-box">
                {guidance}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No implementation guidance available for this control.")
    
    with tab2:
        testing = control.get('testing')
        if testing:
            st.markdown(f"""
            <div class="testing-box">
                {testing}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No testing procedure available for this control.")
    
    with tab3:
        mappings = control.get('mappings', {})
        if mappings:
            rows = []
            for framework, refs in mappings.items():
                if isinstance(refs, list):
                    for ref in refs:
                        rows.append({'Framework': framework, 'Reference': ref})
                else:
                    rows.append({'Framework': framework, 'Reference': str(refs)})
            
            if rows:
                mappings_df = pd.DataFrame(rows)
                st.dataframe(mappings_df, use_container_width=True, hide_index=True)
                
                st.markdown("**Frameworks:**")
                frameworks_html = " ".join([
                    f'<span class="tag tag-framework">{fw}</span>'
                    for fw in mappings.keys()
                ])
                st.markdown(frameworks_html, unsafe_allow_html=True)
            else:
                st.info("No framework mappings available.")
        else:
            st.info("No framework mappings available for this control.")
    
    with tab4:
        evidence = control.get('evidence', [])
        if evidence:
            evidence_df = pd.DataFrame(evidence)
            st.dataframe(evidence_df, use_container_width=True, hide_index=True)
            
            csv = evidence_df.to_csv(index=False)
            st.download_button(
                "⬇️ Download Evidence List",
                data=csv,
                file_name=f"evidence_{ccf_id}.csv",
                mime="text/csv"
            )
        else:
            st.info("No evidence items linked to this control.")
    
    # Related controls
    st.markdown("---")
    st.markdown("### Related Controls (Same Domain)")
    
    related = control.get('related_controls', [])
    if related:
        for rc in related[:5]:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{rc['ccf_id']}** — {rc['title']}")
            with col2:
                if st.button("View", key=f"related_{rc['ccf_id']}"):
                    st.session_state.selected_control = rc['ccf_id']
                    st.rerun()
    else:
        st.info("No related controls found.")


def main():
    # Sidebar source selector
    render_source_selector_sidebar()
    
    st.title("🔍 Controls Browser")
    st.caption("Search, filter, and explore compliance controls")
    
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
    
    # Initialize session state
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False
    if 'selected_control' not in st.session_state:
        st.session_state.selected_control = None
    
    # Show detail view if selected
    if st.session_state.show_detail and st.session_state.selected_control:
        render_control_detail(st.session_state.selected_control)
        return
    
    # -----------------------
    # Search and Filters
    # -----------------------
    with st.container():
        search_col, filter_toggle = st.columns([4, 1])
        
        with search_col:
            search_term = st.text_input(
                "🔍 Search controls",
                placeholder="Search by ID, title, description, guidance...",
                key="search_input"
            )
        
        with filter_toggle:
            st.write("")
            show_filters = st.toggle("Show Filters", value=True)
    
    # Filter panel
    if show_filters:
        with st.expander("🎛️ Advanced Filters", expanded=True):
            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            
            with filter_col1:
                domains = get_all_domains(source_ids=source_ids if source_ids else None)
                selected_domains = st.multiselect("Domains", domains, key="filter_domains")
            
            with filter_col2:
                types = get_all_control_types(source_ids=source_ids if source_ids else None)
                selected_types = st.multiselect("Control Types", types, key="filter_types")
            
            with filter_col3:
                themes = get_all_themes(source_ids=source_ids if source_ids else None)
                selected_themes = st.multiselect("Themes", themes, key="filter_themes")
            
            with filter_col4:
                frameworks = get_all_frameworks(source_ids=source_ids if source_ids else None)
                selected_frameworks = st.multiselect("Frameworks", frameworks, key="filter_frameworks")
            
            filter_col5, filter_col6, filter_col7, filter_col8 = st.columns(4)
            
            with filter_col5:
                has_evidence = st.selectbox(
                    "Evidence Status",
                    options=[None, True, False],
                    format_func=lambda x: "All" if x is None else ("Has Evidence" if x else "Missing Evidence"),
                    key="filter_evidence"
                )
            
            with filter_col6:
                has_guidance = st.selectbox(
                    "Guidance Status",
                    options=[None, True, False],
                    format_func=lambda x: "All" if x is None else ("Has Guidance" if x else "Missing Guidance"),
                    key="filter_guidance"
                )
            
            with filter_col7:
                st.write("")
                if st.button("Clear All Filters", use_container_width=True):
                    for key in ['filter_domains', 'filter_types', 'filter_themes', 
                               'filter_frameworks', 'filter_evidence', 'filter_guidance', 'search_input']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
    else:
        selected_domains = []
        selected_types = []
        selected_themes = []
        selected_frameworks = []
        has_evidence = None
        has_guidance = None
    
    # -----------------------
    # Load and Display Controls
    # -----------------------
    df = search_controls(
        source_ids=source_ids if source_ids else None,
        search_term=search_term,
        domains=selected_domains if selected_domains else None,
        types=selected_types if selected_types else None,
        themes=selected_themes if selected_themes else None,
        frameworks=selected_frameworks if selected_frameworks else None,
        has_evidence=has_evidence,
        has_guidance=has_guidance
    )
    
    # Results header
    st.markdown("---")
    
    results_col1, results_col2, results_col3 = st.columns([2, 2, 1])
    
    with results_col1:
        st.subheader(f"📋 Results ({len(df)} controls)")
    
    with results_col2:
        view_mode = st.radio(
            "View",
            options=["Cards", "Table"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with results_col3:
        sort_options = ["ccf_id", "title", "domain", "evidence_count"]
        if 'source_name' in df.columns or 'source_short' in df.columns:
            sort_options.insert(0, "source_short")
        
        sort_by = st.selectbox(
            "Sort by",
            options=sort_options,
            format_func=lambda x: {
                "ccf_id": "Control ID",
                "title": "Title",
                "domain": "Domain",
                "evidence_count": "Evidence Count",
                "source_short": "Framework"
            }.get(x, x),
            label_visibility="collapsed"
        )
    
    if df.empty:
        st.info("No controls found matching your criteria.")
        return
    
    # Sort
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by)
    else:
        df = df.sort_values(by='ccf_id')
    
    # Display
    if view_mode == "Cards":
        items_per_page = 10
        total_pages = (len(df) - 1) // items_per_page + 1
        
        page_col1, page_col2, page_col3 = st.columns([1, 3, 1])
        with page_col2:
            page = st.slider("Page", 1, max(1, total_pages), 1, label_visibility="collapsed") if total_pages > 1 else 1
        
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        for _, row in df.iloc[start_idx:end_idx].iterrows():
            render_control_card(row.to_dict(), search_term)
        
        st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(df))} of {len(df)} controls")
    
    else:
        # Table view - build columns based on what's available
        base_cols = ['ccf_id', 'title', 'domain', 'type', 'theme', 'evidence_count']
        if 'source_short' in df.columns:
            base_cols = ['source_short'] + base_cols
        elif 'source_name' in df.columns:
            base_cols = ['source_name'] + base_cols
        
        display_cols = [c for c in base_cols if c in df.columns]
        display_df = df[display_cols].copy()
        
        # Rename columns
        col_rename = {
            'source_short': 'Framework',
            'source_name': 'Framework',
            'ccf_id': 'ID',
            'title': 'Title',
            'domain': 'Domain',
            'type': 'Type',
            'theme': 'Theme',
            'evidence_count': 'Evidence'
        }
        display_df.columns = [col_rename.get(c, c) for c in display_df.columns]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=500
        )
        
        # Select control from table
        st.markdown("---")
        select_col1, select_col2 = st.columns([3, 1])
        
        with select_col1:
            control_ids = df['ccf_id'].tolist()
            selected_id = st.selectbox("Select a control to view details:", control_ids)
        
        with select_col2:
            st.write("")
            if st.button("View Details", key="view_from_table", use_container_width=True):
                st.session_state.selected_control = selected_id
                st.session_state.show_detail = True
                st.rerun()
    
    # -----------------------
    # Export Options
    # -----------------------
    st.markdown("---")
    st.subheader("📥 Export")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️ Download as CSV",
            data=csv,
            file_name="controls_export.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with export_col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            "⬇️ Download as JSON",
            data=json_data,
            file_name="controls_export.json",
            mime="application/json",
            use_container_width=True
        )
    
    with export_col3:
        md_content = "# Controls Export\n\n"
        for _, row in df.iterrows():
            md_content += f"## {row['ccf_id']} - {row['title']}\n\n"
            md_content += f"**Domain:** {row['domain']}\n\n"
            md_content += f"**Description:** {row['description']}\n\n"
            md_content += "---\n\n"
        
        st.download_button(
            "⬇️ Download as Markdown",
            data=md_content,
            file_name="controls_export.md",
            mime="text/markdown",
            use_container_width=True
        )


if __name__ == "__main__":
    main()