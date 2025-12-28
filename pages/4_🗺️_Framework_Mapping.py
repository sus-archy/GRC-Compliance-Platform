import streamlit as st
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    db_exists, get_all_frameworks, get_framework_coverage, search_controls,
    get_all_compliance_sources
)
from utils.exporters import generate_framework_matrix

st.set_page_config(page_title="Framework Mapping - GRC Platform", layout="wide", page_icon="🗺️")

# Custom CSS
st.markdown("""
<style>
    .framework-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
        margin: 4px;
    }
    .coverage-stat {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .coverage-stat h3 {
        margin: 0;
        font-size: 1.8rem;
        color: #667eea;
    }
    .coverage-stat p {
        margin: 0.5rem 0 0 0;
        color: #9e9e9e;
    }
    .mapping-cell {
        background: rgba(21, 101, 192, 0.2);
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .heatmap-container {
        overflow-x: auto;
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
            key="mapping_source_selector",
            help="Choose which compliance frameworks to include"
        )
        
        st.session_state.selected_sources = selected
        
        if selected:
            total_controls = sum(s['control_count'] for s in sources if s['id'] in selected)
            st.sidebar.caption(f"📊 **{len(selected)}** frameworks | **{total_controls}** controls")
        else:
            st.sidebar.warning("⚠️ No frameworks selected")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("All", use_container_width=True, key="map_select_all"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("None", use_container_width=True, key="map_clear_all"):
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


def get_framework_stats(source_ids: list = None):
    """Get statistics for each framework."""
    if not db_exists():
        return {}
    
    coverage_df = get_framework_coverage(source_ids=source_ids)
    
    if coverage_df.empty:
        return {}
    
    frameworks = get_all_frameworks(source_ids=source_ids)
    stats = {}
    
    for fw in frameworks:
        if fw in coverage_df.columns:
            mapped_count = coverage_df[fw].notna().sum()
            total_count = len(coverage_df)
            stats[fw] = {
                'mapped_controls': int(mapped_count),
                'total_controls': total_count,
                'coverage_pct': (mapped_count / total_count) * 100 if total_count > 0 else 0
            }
    
    return stats


def get_controls_by_framework(framework: str, source_ids: list = None):
    """Get all controls mapped to a specific framework."""
    coverage_df = get_framework_coverage(source_ids=source_ids)
    
    if coverage_df.empty or framework not in coverage_df.columns:
        return pd.DataFrame()
    
    # Filter to controls with this framework mapping
    filtered = coverage_df[coverage_df[framework].notna() & (coverage_df[framework] != '')]
    
    # Build columns
    cols = ['ccf_id', 'title', 'domain', framework]
    if 'source' in filtered.columns:
        cols = ['source'] + cols
    
    cols = [c for c in cols if c in filtered.columns]
    
    return filtered[cols].copy()


def main():
    # Sidebar source selector
    render_source_selector_sidebar()
    
    st.title("🗺️ Framework Mapping")
    st.caption("Cross-reference controls across compliance frameworks")
    
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
    # Framework Overview
    # -----------------------
    frameworks = get_all_frameworks(source_ids=source_ids if source_ids else None)
    
    if not frameworks:
        st.info("No framework mappings found in the database.")
        return
    
    st.subheader("📊 Framework Overview")
    
    # Display framework badges
    frameworks_html = " ".join([f'<span class="framework-badge">{fw}</span>' for fw in frameworks])
    st.markdown(frameworks_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Framework statistics
    fw_stats = get_framework_stats(source_ids if source_ids else None)
    
    if fw_stats:
        # Show stats in columns
        num_cols = min(len(fw_stats), 5)
        cols = st.columns(num_cols)
        
        for i, (fw, stats) in enumerate(list(fw_stats.items())[:5]):
            with cols[i]:
                st.markdown(f"""
                <div class="coverage-stat">
                    <h3>{stats['mapped_controls']}</h3>
                    <p>{fw}</p>
                    <small>{stats['coverage_pct']:.1f}% coverage</small>
                </div>
                """, unsafe_allow_html=True)
        
        if len(fw_stats) > 5:
            st.caption(f"Showing 5 of {len(fw_stats)} frameworks")
    
    st.markdown("---")
    
    # -----------------------
    # Tabs
    # -----------------------
    tab1, tab2, tab3 = st.tabs(["📋 Coverage Matrix", "🔍 Framework Explorer", "📊 Comparison"])
    
    with tab1:
        st.subheader("Framework Coverage Matrix")
        
        coverage_df = get_framework_coverage(source_ids=source_ids if source_ids else None)
        
        if coverage_df.empty:
            st.info("No coverage data available.")
        else:
            # Select frameworks to display
            selected_frameworks = st.multiselect(
                "Select Frameworks to Display",
                frameworks,
                default=frameworks[:5] if len(frameworks) > 5 else frameworks
            )
            
            if selected_frameworks:
                # Build display columns
                display_cols = ['ccf_id', 'title', 'domain'] + selected_frameworks
                if 'source' in coverage_df.columns:
                    display_cols = ['source'] + display_cols
                
                display_cols = [c for c in display_cols if c in coverage_df.columns]
                
                display_df = coverage_df[display_cols].copy()
                
                # Add coverage indicator
                def has_mapping(row):
                    for fw in selected_frameworks:
                        if fw in row and pd.notna(row[fw]) and str(row[fw]).strip():
                            return True
                    return False
                
                display_df['has_any_mapping'] = display_df.apply(has_mapping, axis=1)
                
                # Filter options
                filter_col1, filter_col2 = st.columns(2)
                
                with filter_col1:
                    show_only_mapped = st.checkbox("Show only controls with mappings")
                
                with filter_col2:
                    search = st.text_input("Search controls", placeholder="Filter by ID or title...")
                
                # Apply filters
                if show_only_mapped:
                    display_df = display_df[display_df['has_any_mapping']]
                
                if search:
                    mask = (
                        display_df['ccf_id'].str.contains(search, case=False, na=False) |
                        display_df['title'].str.contains(search, case=False, na=False)
                    )
                    display_df = display_df[mask]
                
                # Remove helper column
                display_df = display_df.drop(columns=['has_any_mapping'])
                
                # Display
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    height=500
                )
                
                st.caption(f"Showing {len(display_df)} controls")
                
                # Export
                export_col1, export_col2 = st.columns(2)
                
                with export_col1:
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        "⬇️ Download Matrix (CSV)",
                        data=csv,
                        file_name="framework_matrix.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with export_col2:
                    json_data = display_df.to_json(orient='records', indent=2)
                    st.download_button(
                        "⬇️ Download Matrix (JSON)",
                        data=json_data,
                        file_name="framework_matrix.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.info("Select at least one framework to display the matrix.")
    
    with tab2:
        st.subheader("Framework Explorer")
        
        # Select framework
        selected_fw = st.selectbox(
            "Select Framework",
            frameworks,
            key="explorer_framework"
        )
        
        if selected_fw:
            # Get stats for this framework
            fw_stat = fw_stats.get(selected_fw, {})
            
            # Stats row
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            
            with stat_col1:
                st.metric("Mapped Controls", fw_stat.get('mapped_controls', 0))
            
            with stat_col2:
                st.metric("Total Controls", fw_stat.get('total_controls', 0))
            
            with stat_col3:
                st.metric("Coverage", f"{fw_stat.get('coverage_pct', 0):.1f}%")
            
            st.markdown("---")
            
            # Controls for this framework
            fw_controls = get_controls_by_framework(selected_fw, source_ids if source_ids else None)
            
            if fw_controls.empty:
                st.info(f"No controls mapped to {selected_fw}")
            else:
                # Search within framework
                fw_search = st.text_input(
                    f"Search within {selected_fw}",
                    placeholder="Filter by control ID, title, or reference..."
                )
                
                if fw_search:
                    mask = (
                        fw_controls['ccf_id'].str.contains(fw_search, case=False, na=False) |
                        fw_controls['title'].str.contains(fw_search, case=False, na=False) |
                        fw_controls[selected_fw].str.contains(fw_search, case=False, na=False)
                    )
                    fw_controls = fw_controls[mask]
                
                # Rename columns for display
                rename_map = {
                    'source': 'Framework',
                    'ccf_id': 'Control ID',
                    'title': 'Title',
                    'domain': 'Domain',
                    selected_fw: f'{selected_fw} Reference'
                }
                fw_controls_display = fw_controls.rename(columns={k: v for k, v in rename_map.items() if k in fw_controls.columns})
                
                st.dataframe(
                    fw_controls_display,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # Export
                csv = fw_controls_display.to_csv(index=False)
                st.download_button(
                    f"⬇️ Download {selected_fw} Mappings",
                    data=csv,
                    file_name=f"{selected_fw.lower().replace(' ', '_')}_mappings.csv",
                    mime="text/csv"
                )
    
    with tab3:
        st.subheader("Framework Comparison")
        
        if len(frameworks) < 2:
            st.info("Need at least 2 frameworks for comparison.")
        else:
            # Select two frameworks
            compare_col1, compare_col2 = st.columns(2)
            
            with compare_col1:
                fw1 = st.selectbox("Framework 1", frameworks, key="compare_fw1")
            
            with compare_col2:
                fw2_options = [f for f in frameworks if f != fw1]
                fw2 = st.selectbox("Framework 2", fw2_options, key="compare_fw2")
            
            if fw1 and fw2:
                coverage_df = get_framework_coverage(source_ids=source_ids if source_ids else None)
                
                if coverage_df.empty:
                    st.info("No coverage data available.")
                else:
                    # Calculate overlap
                    has_fw1 = coverage_df[fw1].notna() & (coverage_df[fw1] != '')
                    has_fw2 = coverage_df[fw2].notna() & (coverage_df[fw2] != '')
                    
                    both = (has_fw1 & has_fw2).sum()
                    only_fw1 = (has_fw1 & ~has_fw2).sum()
                    only_fw2 = (~has_fw1 & has_fw2).sum()
                    neither = (~has_fw1 & ~has_fw2).sum()
                    
                    # Display stats
                    st.markdown("### Overlap Statistics")
                    
                    overlap_col1, overlap_col2, overlap_col3, overlap_col4 = st.columns(4)
                    
                    with overlap_col1:
                        st.metric(f"Both Frameworks", both)
                    
                    with overlap_col2:
                        st.metric(f"Only {fw1}", only_fw1)
                    
                    with overlap_col3:
                        st.metric(f"Only {fw2}", only_fw2)
                    
                    with overlap_col4:
                        st.metric("Neither", neither)
                    
                    # Visualization
                    try:
                        import plotly.graph_objects as go
                        
                        fig = go.Figure()
                        
                        categories = [f'Both', f'Only {fw1}', f'Only {fw2}', 'Neither']
                        values = [both, only_fw1, only_fw2, neither]
                        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9E9E9E']
                        
                        fig.add_trace(go.Bar(
                            x=categories,
                            y=values,
                            marker_color=colors,
                            text=values,
                            textposition='auto'
                        ))
                        
                        fig.update_layout(
                            title="Framework Coverage Comparison",
                            yaxis_title="Number of Controls",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        st.warning("Install plotly for visualization: pip install plotly")
                    
                    st.markdown("---")
                    
                    # Show controls in each category
                    category = st.selectbox(
                        "View Controls",
                        ["Both Frameworks", f"Only {fw1}", f"Only {fw2}", "Neither"]
                    )
                    
                    if category == "Both Frameworks":
                        filtered = coverage_df[has_fw1 & has_fw2]
                    elif category == f"Only {fw1}":
                        filtered = coverage_df[has_fw1 & ~has_fw2]
                    elif category == f"Only {fw2}":
                        filtered = coverage_df[~has_fw1 & has_fw2]
                    else:
                        filtered = coverage_df[~has_fw1 & ~has_fw2]
                    
                    display_cols = ['ccf_id', 'title', 'domain']
                    if 'source' in filtered.columns:
                        display_cols = ['source'] + display_cols
                    
                    if category != "Neither":
                        if category == "Both Frameworks" or category == f"Only {fw1}":
                            display_cols.append(fw1)
                        if category == "Both Frameworks" or category == f"Only {fw2}":
                            display_cols.append(fw2)
                    
                    display_cols = [c for c in display_cols if c in filtered.columns]
                    
                    st.dataframe(
                        filtered[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )


if __name__ == "__main__":
    main()