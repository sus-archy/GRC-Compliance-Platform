import streamlit as st
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db_path, db_exists

# -----------------------
# Page Configuration
# -----------------------
st.set_page_config(
    page_title="GRC Compliance Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/grc-platform',
        'Report a bug': 'https://github.com/your-repo/grc-platform/issues',
        'About': '# GRC Compliance Platform\nA comprehensive governance, risk, and compliance management system.'
    }
)

# -----------------------
# Custom CSS
# -----------------------
st.markdown("""
<style>
    /* Hide the default "app" label in sidebar */
    [data-testid="stSidebarNav"] > ul > li:first-child {
        display: none !important;
    }
    
    section[data-testid="stSidebarNav"] > ul > li:first-child {
        display: none !important;
    }
    
    /* Style sidebar navigation */
    [data-testid="stSidebarNav"] {
        padding-top: 0.5rem;
    }
    
    [data-testid="stSidebarNav"] > ul {
        padding-left: 0;
    }
    
    [data-testid="stSidebarNav"] a {
        padding: 0.6rem 1rem;
        border-radius: 8px;
        margin: 2px 8px;
        display: flex;
        align-items: center;
    }
    
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(102, 126, 234, 0.2);
    }
    
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: rgba(102, 126, 234, 0.3);
    }
    
    /* Main container */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #dee2e6;
    }
    
    /* DataFrames */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        background-color: #f1f3f4;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Success/Warning/Error boxes */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        border-radius: 10px;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* Custom classes */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .metric-card p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.9rem;
    }
    
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-complete { background: #d4edda; color: #155724; }
    .status-partial { background: #fff3cd; color: #856404; }
    .status-missing { background: #f8d7da; color: #721c24; }
    
    .framework-tag {
        background: #e3f2fd;
        color: #1565c0;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 2px;
        display: inline-block;
    }
    
    .domain-header {
        background: linear-gradient(90deg, #2196f3, #21cbf3);
        color: white;
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .highlight {
        background-color: #fff59d;
        padding: 2px 4px;
        border-radius: 3px;
    }
    
    /* Compliance source selector */
    .source-selector {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .source-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .source-active {
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
        border: 1px solid rgba(76, 175, 80, 0.4);
    }
    
    .source-inactive {
        background: rgba(158, 158, 158, 0.2);
        color: #9e9e9e;
        border: 1px solid rgba(158, 158, 158, 0.4);
    }
</style>
""", unsafe_allow_html=True)


# -----------------------
# Session State Init
# -----------------------
if 'db_path' not in st.session_state:
    st.session_state.db_path = get_db_path()

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

if 'selected_sources' not in st.session_state:
    st.session_state.selected_sources = []

if 'all_sources' not in st.session_state:
    st.session_state.all_sources = []


# -----------------------
# Helper Functions
# -----------------------
def get_selected_source_ids() -> list:
    """Get list of selected compliance source IDs."""
    return st.session_state.get('selected_sources', [])


def render_compliance_selector():
    """Render the compliance source selector in sidebar."""
    if not db_exists():
        return
    
    try:
        from utils.db import get_all_compliance_sources
        
        sources = get_all_compliance_sources()
        st.session_state.all_sources = sources
        
        if not sources:
            # No sources yet - show info
            st.info("📚 No compliance frameworks imported yet.")
            return
        
        st.markdown("### 📚 Compliance Frameworks")
        
        # Build options
        source_options = {s['id']: f"{s['short_name'] or s['name']} ({s['control_count']} controls)" for s in sources}
        
        # Get currently selected (default to all active)
        if not st.session_state.selected_sources:
            st.session_state.selected_sources = [s['id'] for s in sources if s.get('is_active', True)]
        
        # Multi-select
        selected = st.multiselect(
            "Select frameworks to view",
            options=list(source_options.keys()),
            default=st.session_state.selected_sources,
            format_func=lambda x: source_options.get(x, str(x)),
            key="source_selector",
            help="Choose which compliance frameworks to include in the analysis"
        )
        
        st.session_state.selected_sources = selected
        
        # Show selected count
        total_controls = sum(s['control_count'] for s in sources if s['id'] in selected)
        total_evidence = sum(s.get('evidence_count', 0) for s in sources if s['id'] in selected)
        
        if selected:
            st.caption(f"📊 **{len(selected)}** frameworks | **{total_controls}** controls | **{total_evidence}** evidence")
        else:
            st.warning("⚠️ No frameworks selected")
        
        # Quick toggle buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", use_container_width=True, key="select_all_sources"):
                st.session_state.selected_sources = [s['id'] for s in sources]
                st.rerun()
        with col2:
            if st.button("Clear All", use_container_width=True, key="clear_all_sources"):
                st.session_state.selected_sources = []
                st.rerun()
        
        st.markdown("---")
        
    except Exception as e:
        # Table might not exist yet (migration needed)
        pass


# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.markdown("## 🛡️ GRC Platform")
    st.caption("Governance • Risk • Compliance")
    st.markdown("---")
    
    # Compliance Source Selector
    render_compliance_selector()


# -----------------------
# Main Landing Page
# -----------------------
def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🛡️ GRC Compliance Platform")
        st.caption("Governance • Risk • Compliance — All in one place")
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Check if database exists
    if not db_exists():
        st.warning("⚠️ No database found. Please seed your data first.")
        st.info("""
        ### Getting Started
        
        1. **From Command Line:**
        ```bash
        python seed.py --source your_data.xlsx --db grc.db --force
        ```
        
        2. **From Admin Panel:**
        Navigate to ⚙️ Admin in the sidebar to upload and seed data.
        
        ### Supported Formats
        - Excel (.xls, .xlsx)
        - JSON (.json)
        - CSV folder
        - ZIP archives
        - XML files
        """)
        return
    
    # Import here to avoid issues when DB doesn't exist
    from utils.db import get_overview_stats, get_quick_insights, get_all_compliance_sources
    
    # Get selected source IDs
    source_ids = get_selected_source_ids()
    
    # Show active frameworks banner
    sources = get_all_compliance_sources()
    if sources:
        selected_names = [s['short_name'] or s['name'] for s in sources if s['id'] in source_ids]
        if selected_names:
            badges = " ".join([f'<span class="source-badge source-active">{name}</span>' for name in selected_names])
            st.markdown(f"""
            <div style="margin-bottom: 1rem;">
                <strong>📚 Active Frameworks:</strong> {badges}
            </div>
            """, unsafe_allow_html=True)
        elif sources:
            st.warning("⚠️ No compliance frameworks selected. Please select at least one from the sidebar.")
            return
    
    # Quick Stats (filtered by selected sources)
    stats = get_overview_stats(source_ids=source_ids if source_ids else None)
    
    st.subheader("📊 Quick Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{stats['controls']}</h3>
            <p>Total Controls</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h3>{stats['domains']}</h3>
            <p>Domains</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h3>{stats['evidence']}</h3>
            <p>Evidence Items</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <h3>{stats['frameworks']}</h3>
            <p>Frameworks</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        coverage = stats.get('coverage_pct', 0)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h3>{coverage:.0f}%</h3>
            <p>Evidence Coverage</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Navigation Cards
    st.subheader("🚀 Quick Navigation")
    
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    
    with nav_col1:
        st.markdown("""
        ### 📊 Dashboard
        View comprehensive analytics, charts, and compliance metrics.
        """)
        if st.button("Go to Dashboard →", key="nav_dash", use_container_width=True):
            st.switch_page("pages/1_📊_Dashboard.py")
    
    with nav_col2:
        st.markdown("""
        ### 🔍 Controls Browser
        Search, filter, and inspect all controls with detailed guidance.
        """)
        if st.button("Browse Controls →", key="nav_ctrl", use_container_width=True):
            st.switch_page("pages/2_🔍_Controls.py")
    
    with nav_col3:
        st.markdown("""
        ### 📁 Evidence Tracker
        Manage evidence artifacts and track collection status.
        """)
        if st.button("View Evidence →", key="nav_ev", use_container_width=True):
            st.switch_page("pages/3_📁_Evidence.py")
    
    nav_col4, nav_col5, nav_col6 = st.columns(3)
    
    with nav_col4:
        st.markdown("""
        ### 🗺️ Framework Mapping
        Cross-reference controls across compliance frameworks.
        """)
        if st.button("View Mappings →", key="nav_map", use_container_width=True):
            st.switch_page("pages/4_🗺️_Framework_Mapping.py")
    
    with nav_col5:
        st.markdown("""
        ### 📈 Reports
        Generate compliance reports and gap analysis.
        """)
        if st.button("Generate Reports →", key="nav_rep", use_container_width=True):
            st.switch_page("pages/5_📈_Reports.py")
    
    with nav_col6:
        st.markdown("""
        ### ⚙️ Admin
        Upload data, configure settings, and manage the platform.
        """)
        if st.button("Admin Panel →", key="nav_admin", use_container_width=True):
            st.switch_page("pages/6_⚙️_Admin.py")
    
    # Quick Insights (filtered by selected sources)
    st.markdown("---")
    st.subheader("💡 Quick Insights")
    
    insights = get_quick_insights(source_ids=source_ids if source_ids else None)
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        st.markdown("##### 📋 Top Domains by Control Count")
        top_domains = insights.get('top_domains', [])
        if top_domains:
            max_count = max(c for _, c in top_domains) if top_domains else 1
            for domain, count in top_domains[:5]:
                progress_value = count / max_count if max_count > 0 else 0
                st.progress(progress_value, text=f"{domain}: {count} controls")
        else:
            st.info("No domain data available")
    
    with insight_col2:
        st.markdown("##### ⚠️ Compliance Gaps")
        
        missing_guidance = insights.get('missing_guidance', 0)
        missing_evidence = insights.get('missing_evidence', 0)
        total = stats['controls']
        
        if total > 0:
            guidance_pct = ((total - missing_guidance) / total) * 100
            evidence_pct = ((total - missing_evidence) / total) * 100
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric(
                    "Guidance Coverage", 
                    f"{guidance_pct:.1f}%", 
                    delta=f"{missing_guidance} missing",
                    delta_color="inverse"
                )
            with col_b:
                st.metric(
                    "Evidence Coverage", 
                    f"{evidence_pct:.1f}%", 
                    delta=f"{missing_evidence} missing",
                    delta_color="inverse"
                )
            
            if missing_guidance > 0 or missing_evidence > 0:
                st.warning("📊 Visit the **Reports** page for detailed gap analysis")
        else:
            st.info("No control data available")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d; font-size: 0.85rem;">
        <p>🛡️ GRC Compliance Platform | Built with Streamlit</p>
        <p>Powered by Adobe Common Controls Framework (Open Source)</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()