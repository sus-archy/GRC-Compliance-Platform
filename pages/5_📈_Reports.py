import streamlit as st
import pandas as pd
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    db_exists, get_overview_stats, get_domain_stats,
    get_gap_analysis, get_all_frameworks, search_controls,
    get_all_compliance_sources, get_all_evidence
)
from utils.exporters import (
    export_to_csv, export_to_json, export_to_excel,
    generate_compliance_report, export_gap_analysis
)
from utils.security import escape_html, format_safe_source_badges

st.set_page_config(page_title="Reports - GRC Platform", layout="wide", page_icon="📈")

# Custom CSS
st.markdown("""
<style>
    .report-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .report-card:hover {
        border-color: rgba(102, 126, 234, 0.5);
    }
    .report-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    .report-icon {
        font-size: 2rem;
        margin-right: 1rem;
    }
    .report-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0;
    }
    .report-description {
        color: #9e9e9e;
        font-size: 0.9rem;
    }
    .gap-item {
        background: rgba(255, 243, 205, 0.2);
        border-left: 4px solid #ffc107;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
    }
    .gap-critical {
        background: rgba(248, 215, 218, 0.2);
        border-left-color: #dc3545;
    }
    .summary-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    .summary-box h2 {
        margin: 0;
        font-size: 2.5rem;
    }
    .summary-box p {
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
            key="reports_source_selector",
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
            if st.button("All", use_container_width=True, key="rpt_select_all"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("None", use_container_width=True, key="rpt_clear_all"):
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
                badges = format_safe_source_badges(selected_sources)
                st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <strong>📚 Active Frameworks:</strong> {badges}
                </div>
                """, unsafe_allow_html=True)
    except:
        pass


def generate_executive_summary(source_ids: list = None):
    """Generate executive summary data."""
    stats = get_overview_stats(source_ids=source_ids)
    domain_stats = get_domain_stats(source_ids=source_ids)
    gap_data = get_gap_analysis(source_ids=source_ids)
    
    summary = {
        'generated_at': datetime.now().isoformat(),
        'overview': stats,
        'domain_summary': domain_stats.to_dict('records') if not domain_stats.empty else [],
        'gaps': {
            'missing_guidance': len(gap_data.get('missing_guidance', pd.DataFrame())),
            'missing_testing': len(gap_data.get('missing_testing', pd.DataFrame())),
            'missing_evidence': len(gap_data.get('missing_evidence', pd.DataFrame())),
            'orphan_evidence': len(gap_data.get('orphan_evidence', pd.DataFrame()))
        }
    }
    
    # Calculate overall compliance score
    total_controls = stats['controls']
    if total_controls > 0:
        guidance_score = (total_controls - summary['gaps']['missing_guidance']) / total_controls * 100
        testing_score = (total_controls - summary['gaps']['missing_testing']) / total_controls * 100
        evidence_score = (total_controls - summary['gaps']['missing_evidence']) / total_controls * 100
        summary['compliance_score'] = (guidance_score + testing_score + evidence_score) / 3
    else:
        summary['compliance_score'] = 0
    
    return summary


def main():
    # Sidebar source selector
    render_source_selector_sidebar()
    
    st.title("📈 Reports & Analysis")
    st.caption("Generate compliance reports and analyze gaps")
    
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
    # Executive Summary
    # -----------------------
    st.subheader("📊 Executive Summary")
    
    summary = generate_executive_summary(source_ids if source_ids else None)
    
    # Escape all summary values for safe HTML display
    safe_score = escape_html(f"{summary['compliance_score']:.0f}%")
    safe_controls = escape_html(str(summary['overview']['controls']))
    total_gaps = summary['gaps']['missing_guidance'] + summary['gaps']['missing_evidence']
    safe_gaps = escape_html(str(total_gaps))
    safe_frameworks = escape_html(str(summary['overview']['frameworks']))
    
    # Summary metrics
    sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
    
    with sum_col1:
        st.markdown(f"""
        <div class="summary-box">
            <h2>{safe_score}</h2>
            <p>Compliance Score</p>
        </div>
        """, unsafe_allow_html=True)
    
    with sum_col2:
        st.markdown(f"""
        <div class="summary-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h2>{safe_controls}</h2>
            <p>Total Controls</p>
        </div>
        """, unsafe_allow_html=True)
    
    with sum_col3:
        st.markdown(f"""
        <div class="summary-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h2>{safe_gaps}</h2>
            <p>Total Gaps</p>
        </div>
        """, unsafe_allow_html=True)
    
    with sum_col4:
        st.markdown(f"""
        <div class="summary-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <h2>{safe_frameworks}</h2>
            <p>Frameworks</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # -----------------------
    # Report Types
    # -----------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Gap Analysis",
        "📋 Compliance Report",
        "📊 Domain Report",
        "⬇️ Export Center"
    ])
    
    with tab1:
        st.subheader("Gap Analysis")
        st.write("Identify controls missing key compliance elements.")
        
        gap_data = get_gap_analysis(source_ids=source_ids if source_ids else None)
        
        # Gap summary cards
        gap_col1, gap_col2, gap_col3, gap_col4 = st.columns(4)
        
        with gap_col1:
            missing_guidance = len(gap_data.get('missing_guidance', pd.DataFrame()))
            st.metric("Missing Guidance", missing_guidance)
        
        with gap_col2:
            missing_testing = len(gap_data.get('missing_testing', pd.DataFrame()))
            st.metric("Missing Testing", missing_testing)
        
        with gap_col3:
            missing_evidence = len(gap_data.get('missing_evidence', pd.DataFrame()))
            st.metric("Missing Evidence Links", missing_evidence)
        
        with gap_col4:
            orphan_evidence = len(gap_data.get('orphan_evidence', pd.DataFrame()))
            st.metric("Orphan Evidence", orphan_evidence)
        
        st.markdown("---")
        
        # Detailed gap views
        gap_type = st.selectbox(
            "Select Gap Type to View",
            ["Missing Guidance", "Missing Testing", "Missing Evidence Links", "Orphan Evidence"]
        )
        
        gap_key_map = {
            "Missing Guidance": "missing_guidance",
            "Missing Testing": "missing_testing",
            "Missing Evidence Links": "missing_evidence",
            "Orphan Evidence": "orphan_evidence"
        }
        
        selected_gap_df = gap_data.get(gap_key_map[gap_type], pd.DataFrame())
        
        if selected_gap_df.empty:
            st.success(f"✅ No items in {gap_type} - Great job!")
        else:
            # Search within gaps
            gap_search = st.text_input("Search within gaps", placeholder="Filter by ID, title, or domain...")
            
            if gap_search:
                mask = selected_gap_df.apply(
                    lambda row: gap_search.lower() in str(row).lower(),
                    axis=1
                )
                selected_gap_df = selected_gap_df[mask]
            
            st.dataframe(
                selected_gap_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Export gap report
            st.download_button(
                f"⬇️ Download {gap_type} Report",
                data=selected_gap_df.to_csv(index=False),
                file_name=f"gap_{gap_key_map[gap_type]}.csv",
                mime="text/csv"
            )
    
    with tab2:
        st.subheader("Compliance Report Generator")
        
        # Framework selection
        frameworks = get_all_frameworks(source_ids=source_ids if source_ids else None)
        
        report_col1, report_col2 = st.columns(2)
        
        with report_col1:
            selected_framework = st.selectbox(
                "Select Framework (optional)",
                ["All Frameworks"] + frameworks
            )
        
        with report_col2:
            report_format = st.selectbox(
                "Report Format",
                ["Summary", "Detailed", "Full Export"]
            )
        
        if st.button("Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                # Get controls data
                controls_df = search_controls(
                    source_ids=source_ids if source_ids else None,
                    frameworks=[selected_framework] if selected_framework != "All Frameworks" else None
                )
                
                if controls_df.empty:
                    st.warning("No controls found for the selected criteria.")
                else:
                    # Generate report
                    fw = selected_framework if selected_framework != "All Frameworks" else None
                    report = generate_compliance_report(controls_df, framework=fw)
                    
                    # Display report
                    st.markdown("### Report Summary")
                    
                    rpt_col1, rpt_col2, rpt_col3, rpt_col4 = st.columns(4)
                    
                    with rpt_col1:
                        st.metric("Total Controls", report['summary']['total_controls'])
                    with rpt_col2:
                        st.metric("With Guidance", report['summary']['with_guidance'])
                    with rpt_col3:
                        st.metric("With Testing", report['summary']['with_testing'])
                    with rpt_col4:
                        st.metric("With Evidence", report['summary']['with_evidence'])
                    
                    # Coverage bars
                    if report['summary']['total_controls'] > 0:
                        st.markdown("### Coverage Metrics")
                        
                        guidance_pct = report['summary'].get('guidance_coverage', 0)
                        testing_pct = report['summary'].get('testing_coverage', 0)
                        evidence_pct = report['summary'].get('evidence_coverage', 0)
                        
                        st.progress(guidance_pct / 100, text=f"Guidance Coverage: {guidance_pct:.1f}%")
                        st.progress(testing_pct / 100, text=f"Testing Coverage: {testing_pct:.1f}%")
                        st.progress(evidence_pct / 100, text=f"Evidence Coverage: {evidence_pct:.1f}%")
                    
                    # Export report
                    st.markdown("---")
                    
                    exp_col1, exp_col2 = st.columns(2)
                    
                    with exp_col1:
                        st.download_button(
                            "⬇️ Download Report (JSON)",
                            data=json.dumps(report, indent=2, default=str),
                            file_name="compliance_report.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with exp_col2:
                        if report['details']:
                            details_df = pd.DataFrame(report['details'])
                            st.download_button(
                                "⬇️ Download Details (CSV)",
                                data=details_df.to_csv(index=False),
                                file_name="compliance_report_details.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
    
    with tab3:
        st.subheader("Domain Analysis Report")
        
        domain_stats = get_domain_stats(source_ids=source_ids if source_ids else None)
        
        if domain_stats.empty:
            st.info("No domain data available.")
        else:
            # Domain statistics table
            st.markdown("### Domain Statistics")
            
            # Calculate percentages
            domain_display = domain_stats.copy()
            domain_display['guidance_pct'] = (
                domain_display['with_guidance'] / domain_display['total_controls'] * 100
            ).fillna(0).round(1)
            domain_display['testing_pct'] = (
                domain_display['with_testing'] / domain_display['total_controls'] * 100
            ).fillna(0).round(1)
            domain_display['evidence_pct'] = (
                domain_display['with_evidence'] / domain_display['total_controls'] * 100
            ).fillna(0).round(1)
            
            # Build columns for display
            display_cols = ['domain', 'total_controls', 'with_guidance', 'with_testing', 'with_evidence',
                          'guidance_pct', 'testing_pct', 'evidence_pct']
            if 'source' in domain_display.columns:
                display_cols = ['source'] + display_cols
            
            display_cols = [c for c in display_cols if c in domain_display.columns]
            
            st.dataframe(
                domain_display[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'source': st.column_config.TextColumn('Framework', width='small'),
                    'domain': st.column_config.TextColumn('Domain', width='large'),
                    'total_controls': st.column_config.NumberColumn('Total', width='small'),
                    'with_guidance': st.column_config.NumberColumn('Guidance', width='small'),
                    'with_testing': st.column_config.NumberColumn('Testing', width='small'),
                    'with_evidence': st.column_config.NumberColumn('Evidence', width='small'),
                    'guidance_pct': st.column_config.ProgressColumn('Guidance %', min_value=0, max_value=100),
                    'testing_pct': st.column_config.ProgressColumn('Testing %', min_value=0, max_value=100),
                    'evidence_pct': st.column_config.ProgressColumn('Evidence %', min_value=0, max_value=100)
                }
            )
            
            # Chart
            try:
                import plotly.express as px
                
                fig = px.bar(
                    domain_display,
                    x='domain',
                    y=['guidance_pct', 'testing_pct', 'evidence_pct'],
                    barmode='group',
                    labels={
                        'domain': 'Domain',
                        'value': 'Coverage %',
                        'variable': 'Metric'
                    },
                    title='Domain Coverage Comparison'
                )
                fig.update_layout(
                    xaxis_tickangle=-45,
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.info("Install plotly for charts: pip install plotly")
            
            # Export
            st.download_button(
                "⬇️ Download Domain Report",
                data=domain_display.to_csv(index=False),
                file_name="domain_report.csv",
                mime="text/csv"
            )
    
    with tab4:
        st.subheader("Export Center")
        st.write("Download comprehensive exports of your GRC data.")
        
        # Export options
        st.markdown("### Available Exports")
        
        export_grid_col1, export_grid_col2 = st.columns(2)
        
        with export_grid_col1:
            st.markdown("""
            <div class="report-card">
                <div class="report-header">
                    <span class="report-icon">📋</span>
                    <div>
                        <h4 class="report-title">Full Controls Export</h4>
                        <p class="report-description">All controls with full details</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            controls_df = search_controls(source_ids=source_ids if source_ids else None)
            if not controls_df.empty:
                st.download_button(
                    "⬇️ Download Controls (CSV)",
                    data=controls_df.to_csv(index=False),
                    file_name="all_controls.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No controls data available")
        
        with export_grid_col2:
            st.markdown("""
            <div class="report-card">
                <div class="report-header">
                    <span class="report-icon">🔍</span>
                    <div>
                        <h4 class="report-title">Gap Analysis Export</h4>
                        <p class="report-description">All gaps in Excel workbook</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            gap_data = get_gap_analysis(source_ids=source_ids if source_ids else None)
            if gap_data:
                try:
                    excel_data = export_gap_analysis(gap_data)
                    st.download_button(
                        "⬇️ Download Gaps (Excel)",
                        data=excel_data,
                        file_name="gap_analysis.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.warning(f"Excel export requires openpyxl: pip install openpyxl")
                    # Fallback to CSV
                    csv_data = gap_data.get('missing_guidance', pd.DataFrame()).to_csv(index=False)
                    st.download_button(
                        "⬇️ Download Missing Guidance (CSV)",
                        data=csv_data,
                        file_name="missing_guidance.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.info("No gap data available")
        
        export_grid_col3, export_grid_col4 = st.columns(2)
        
        with export_grid_col3:
            st.markdown("""
            <div class="report-card">
                <div class="report-header">
                    <span class="report-icon">📁</span>
                    <div>
                        <h4 class="report-title">Evidence List</h4>
                        <p class="report-description">All evidence artifacts</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            evidence_df = get_all_evidence(source_ids=source_ids if source_ids else None)
            if not evidence_df.empty:
                st.download_button(
                    "⬇️ Download Evidence (CSV)",
                    data=evidence_df.to_csv(index=False),
                    file_name="evidence_list.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No evidence data available")
        
        with export_grid_col4:
            st.markdown("""
            <div class="report-card">
                <div class="report-header">
                    <span class="report-icon">📊</span>
                    <div>
                        <h4 class="report-title">Executive Summary</h4>
                        <p class="report-description">High-level overview JSON</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button(
                "⬇️ Download Summary (JSON)",
                data=json.dumps(summary, indent=2, default=str),
                file_name="executive_summary.json",
                mime="application/json",
                use_container_width=True
            )


if __name__ == "__main__":
    main()