import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    db_exists, get_overview_stats, get_quick_insights,
    get_domain_stats, get_all_frameworks, get_framework_coverage,
    get_all_compliance_sources
)

st.set_page_config(page_title="Dashboard - GRC Platform", layout="wide", page_icon="📊")

# Custom CSS
st.markdown("""
<style>
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin: 0.5rem 0 0 0;
    }
    .chart-container {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .insight-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .insight-card h4 {
        margin: 0 0 0.5rem 0;
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
            key="dashboard_source_selector",
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
            if st.button("All", use_container_width=True, key="dash_select_all"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("None", use_container_width=True, key="dash_clear_all"):
                st.session_state.selected_sources = []
                st.rerun()
        
        st.sidebar.markdown("---")
        
    except Exception as e:
        pass


def render_metric_card(value, label, color_start="#667eea", color_end="#764ba2"):
    """Render a styled metric card."""
    st.markdown(f"""
    <div class="metric-container" style="background: linear-gradient(135deg, {color_start} 0%, {color_end} 100%);">
        <p class="metric-value">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """, unsafe_allow_html=True)


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


def create_horizontal_bar_chart(df, x_col, y_col, title, color_col=None, top_n=15):
    """Create a horizontal bar chart for better readability with many categories."""
    # Sort and limit to top N
    df_sorted = df.nlargest(top_n, x_col).sort_values(x_col, ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_sorted[x_col],
        y=df_sorted[y_col],
        orientation='h',
        marker=dict(
            color=df_sorted[x_col],
            colorscale='Blues',
            showscale=False
        ),
        text=df_sorted[x_col],
        textposition='outside',
        textfont=dict(size=11)
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=max(400, len(df_sorted) * 28),
        margin=dict(l=20, r=80, t=40, b=20),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_donut_chart(data, names_col, values_col, title, top_n=8):
    """Create a donut chart with top N categories, grouping others."""
    df = pd.DataFrame(data, columns=[names_col, values_col])
    
    # Sort by value
    df = df.sort_values(values_col, ascending=False)
    
    # Group small categories as "Other"
    if len(df) > top_n:
        top_df = df.head(top_n - 1)
        other_sum = df.iloc[top_n - 1:][values_col].sum()
        other_row = pd.DataFrame({names_col: ['Other'], values_col: [other_sum]})
        df = pd.concat([top_df, other_row], ignore_index=True)
    
    # Custom colors
    colors = ['#667eea', '#764ba2', '#4facfe', '#00f2fe', '#43e97b', 
              '#38f9d7', '#fa709a', '#fee140', '#a8edea', '#9e9e9e']
    
    fig = go.Figure(data=[go.Pie(
        labels=df[names_col],
        values=df[values_col],
        hole=0.5,
        marker=dict(colors=colors[:len(df)]),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=11),
        insidetextorientation='horizontal',
        showlegend=False
    )])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(
            text=f'{df[values_col].sum()}<br>Total',
            x=0.5, y=0.5,
            font_size=16,
            showarrow=False,
            font=dict(color='white')
        )]
    )
    
    return fig


def create_coverage_gauge(value, title, color="#4CAF50"):
    """Create a single coverage gauge."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        number={'suffix': '%', 'font': {'size': 36, 'color': 'white'}},
        title={'text': title, 'font': {'size': 14, 'color': 'white'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': 'white', 'tickfont': {'color': 'white'}},
            'bar': {'color': color, 'thickness': 0.7},
            'bgcolor': 'rgba(255,255,255,0.1)',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 33], 'color': 'rgba(244, 67, 54, 0.3)'},
                {'range': [33, 66], 'color': 'rgba(255, 152, 0, 0.3)'},
                {'range': [66, 100], 'color': 'rgba(76, 175, 80, 0.3)'}
            ],
            'threshold': {
                'line': {'color': '#ff5252', 'width': 3},
                'thickness': 0.8,
                'value': 80
            }
        }
    ))
    
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return fig


def create_completeness_chart(domain_stats, top_n=10):
    """Create a stacked/grouped bar chart for completeness by domain."""
    if domain_stats.empty:
        return None
    
    # Get top N domains by control count
    df = domain_stats.nlargest(top_n, 'total_controls').copy()
    
    # Calculate percentages
    df['guidance_pct'] = (df['with_guidance'] / df['total_controls'] * 100).fillna(0)
    df['testing_pct'] = (df['with_testing'] / df['total_controls'] * 100).fillna(0)
    df['evidence_pct'] = (df['with_evidence'] / df['total_controls'] * 100).fillna(0)
    
    # Truncate long domain names
    df['domain_short'] = df['domain'].apply(lambda x: x[:25] + '...' if len(str(x)) > 25 else x)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Guidance',
        y=df['domain_short'],
        x=df['guidance_pct'],
        orientation='h',
        marker_color='#4CAF50',
        text=df['guidance_pct'].round(0).astype(int).astype(str) + '%',
        textposition='inside',
        textfont=dict(color='white', size=10)
    ))
    
    fig.add_trace(go.Bar(
        name='Testing',
        y=df['domain_short'],
        x=df['testing_pct'],
        orientation='h',
        marker_color='#2196F3',
        text=df['testing_pct'].round(0).astype(int).astype(str) + '%',
        textposition='inside',
        textfont=dict(color='white', size=10)
    ))
    
    fig.add_trace(go.Bar(
        name='Evidence',
        y=df['domain_short'],
        x=df['evidence_pct'],
        orientation='h',
        marker_color='#FF9800',
        text=df['evidence_pct'].round(0).astype(int).astype(str) + '%',
        textposition='inside',
        textfont=dict(color='white', size=10)
    ))
    
    fig.update_layout(
        barmode='group',
        height=max(350, len(df) * 45),
        margin=dict(l=20, r=20, t=30, b=40),
        xaxis=dict(
            title='Percentage (%)',
            range=[0, 105],
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            title='',
            tickfont=dict(size=11)
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=11)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        bargap=0.15,
        bargroupgap=0.05
    )
    
    return fig


def main():
    # Sidebar source selector
    render_source_selector_sidebar()
    
    st.title("📊 Dashboard")
    st.caption("Comprehensive view of your GRC compliance posture")
    
    if not db_exists():
        st.warning("⚠️ No database found. Please seed your data first.")
        st.info("Go to ⚙️ Admin to upload and import data.")
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
    
    # Get data (filtered by selected sources)
    stats = get_overview_stats(source_ids=source_ids if source_ids else None)
    insights = get_quick_insights(source_ids=source_ids if source_ids else None)
    domain_stats = get_domain_stats(source_ids=source_ids if source_ids else None)
    
    # -----------------------
    # Key Metrics Row
    # -----------------------
    st.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_metric_card(stats['controls'], "Total Controls")
    
    with col2:
        render_metric_card(stats['domains'], "Domains", "#f093fb", "#f5576c")
    
    with col3:
        render_metric_card(stats['evidence'], "Evidence Items", "#4facfe", "#00f2fe")
    
    with col4:
        render_metric_card(stats['frameworks'], "Frameworks", "#43e97b", "#38f9d7")
    
    with col5:
        coverage = stats.get('coverage_pct', 0)
        render_metric_card(f"{coverage:.0f}%", "Evidence Coverage", "#fa709a", "#fee140")
    
    st.markdown("---")
    
    # -----------------------
    # Charts Row 1: Controls by Domain (Horizontal) + Type Distribution (Donut)
    # -----------------------
    chart_col1, chart_col2 = st.columns([3, 2])
    
    with chart_col1:
        st.subheader("📊 Top Domains by Control Count")
        
        if not domain_stats.empty:
            fig = create_horizontal_bar_chart(
                domain_stats, 
                'total_controls', 
                'domain', 
                '',
                top_n=12
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No domain data available")
    
    with chart_col2:
        st.subheader("🎯 Control Type Distribution")
        
        type_dist = insights.get('type_distribution', [])
        if type_dist:
            fig = create_donut_chart(type_dist, 'type', 'count', '', top_n=8)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No control type data available")
    
    st.markdown("---")
    
    # -----------------------
    # Charts Row 2: Completeness + Coverage Gauges
    # -----------------------
    chart_col3, chart_col4 = st.columns([2, 30])
    
    with chart_col4:
        st.subheader("📈 Overall Coverage")
        
        total_controls = stats['controls']
        missing_guidance = insights.get('missing_guidance', 0)
        missing_evidence = insights.get('missing_evidence', 0)
        
        guidance_pct = ((total_controls - missing_guidance) / total_controls * 100) if total_controls > 0 else 0
        evidence_pct = ((total_controls - missing_evidence) / total_controls * 100) if total_controls > 0 else 0
        
        gauge_col1, gauge_col2 = st.columns(2)
        
        with gauge_col1:
            fig = create_coverage_gauge(guidance_pct, "Guidance", "#4CAF50")
            st.plotly_chart(fig, use_container_width=True)
        
        with gauge_col2:
            fig = create_coverage_gauge(evidence_pct, "Evidence", "#2196F3")
            st.plotly_chart(fig, use_container_width=True)
        
        # Additional metrics below gauges
        st.markdown("##### 📋 Gap Summary")
        gap_col1, gap_col2 = st.columns(2)
        with gap_col1:
            st.metric(
                "Missing Guidance",
                missing_guidance,
                delta=f"-{missing_guidance}" if missing_guidance > 0 else "0",
                delta_color="inverse"
            )
        with gap_col2:
            st.metric(
                "Missing Evidence",
                missing_evidence,
                delta=f"-{missing_evidence}" if missing_evidence > 0 else "0",
                delta_color="inverse"
            )
    
    st.markdown("---")
    
    # -----------------------
    # Quick Insights Row
    # -----------------------
    st.subheader("💡 Quick Insights")
    
    insight_col1, insight_col2, insight_col3 = st.columns(3)
    
    with insight_col1:
        st.markdown("""
        <div class="insight-card">
            <h4>📋 Top 5 Domains</h4>
        </div>
        """, unsafe_allow_html=True)
        
        top_domains = insights.get('top_domains', [])
        if top_domains:
            max_count = max(c for _, c in top_domains) if top_domains else 1
            for domain, count in top_domains[:5]:
                # Truncate long names
                display_name = domain[:30] + '...' if len(domain) > 30 else domain
                progress = count / max_count
                st.progress(progress, text=f"{display_name}: {count}")
        else:
            st.info("No domain data")
    
    with insight_col2:
        st.markdown("""
        <div class="insight-card">
            <h4>⚠️ Attention Required</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Compliance score
        if total_controls > 0:
            overall_score = (guidance_pct + evidence_pct) / 2
            
            if overall_score >= 80:
                score_color = "🟢"
            elif overall_score >= 50:
                score_color = "🟡"
            else:
                score_color = "🔴"
            
            st.markdown(f"**Overall Score:** {score_color} **{overall_score:.1f}%**")
            st.progress(overall_score / 100)
            
            if missing_guidance > 0 or missing_evidence > 0:
                st.warning("📊 Visit **Reports** for detailed gap analysis")
        else:
            st.info("No control data available")
    
    with insight_col3:
        st.markdown("""
        <div class="insight-card">
            <h4>🗺️ Framework Mappings</h4>
        </div>
        """, unsafe_allow_html=True)
        
        frameworks = get_all_frameworks(source_ids=source_ids if source_ids else None)
        if frameworks:
            st.markdown(f"**{len(frameworks)}** frameworks mapped")
            
            # Show frameworks as tags
            fw_display = frameworks[:8]  # Show first 8
            for fw in fw_display:
                st.markdown(f"• {fw}")
            
            if len(frameworks) > 8:
                st.caption(f"...and {len(frameworks) - 8} more")
        else:
            st.info("No framework mappings found")
    
    st.markdown("---")
    
    # -----------------------
    # Domain Details Table (Collapsible)
    # -----------------------
    with st.expander("📊 Detailed Domain Statistics", expanded=False):
        domain_stats_table = get_domain_stats(source_ids=source_ids if source_ids else None)
        
        if not domain_stats_table.empty:
            # Calculate percentages
            display_df = domain_stats_table.copy()
            display_df['guidance_pct'] = (display_df['with_guidance'] / display_df['total_controls'] * 100).fillna(0).round(1)
            display_df['testing_pct'] = (display_df['with_testing'] / display_df['total_controls'] * 100).fillna(0).round(1)
            display_df['evidence_pct'] = (display_df['with_evidence'] / display_df['total_controls'] * 100).fillna(0).round(1)
            
            # Build columns for display
            cols = ['domain', 'total_controls', 'with_guidance', 'with_testing', 'with_evidence',
                   'guidance_pct', 'testing_pct', 'evidence_pct']
            if 'source' in display_df.columns:
                cols = ['source'] + cols
            cols = [c for c in cols if c in display_df.columns]
            
            st.dataframe(
                display_df[cols],
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    'source': st.column_config.TextColumn('Framework', width='small'),
                    'domain': st.column_config.TextColumn('Domain', width='large'),
                    'total_controls': st.column_config.NumberColumn('Total', format='%d'),
                    'with_guidance': st.column_config.NumberColumn('Guidance', format='%d'),
                    'with_testing': st.column_config.NumberColumn('Testing', format='%d'),
                    'with_evidence': st.column_config.NumberColumn('Evidence', format='%d'),
                    'guidance_pct': st.column_config.ProgressColumn('Guidance %', min_value=0, max_value=100),
                    'testing_pct': st.column_config.ProgressColumn('Testing %', min_value=0, max_value=100),
                    'evidence_pct': st.column_config.ProgressColumn('Evidence %', min_value=0, max_value=100)
                }
            )
            
            # Download option
            csv = display_df.to_csv(index=False)
            st.download_button(
                "⬇️ Download Domain Statistics",
                data=csv,
                file_name="domain_statistics.csv",
                mime="text/csv"
            )
        else:
            st.info("No domain statistics available")


if __name__ == "__main__":
    main()