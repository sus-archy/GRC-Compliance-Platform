import streamlit as st
import pandas as pd
import os
import sys
import tempfile
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    db_exists, get_connection, get_db_path,
    get_all_compliance_sources, update_compliance_source,
    delete_compliance_source, toggle_compliance_source
)

st.set_page_config(page_title="Admin - GRC Platform", layout="wide", page_icon="⚙️")

# Custom CSS
st.markdown("""
<style>
    .admin-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .status-success {
        background: rgba(76, 175, 80, 0.2);
        color: #81c784;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
    .status-error {
        background: rgba(244, 67, 54, 0.2);
        color: #e57373;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
    .status-warning {
        background: rgba(255, 152, 0, 0.2);
        color: #ffb74d;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
    .source-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .source-active {
        border-left: 4px solid #4caf50;
    }
    .source-inactive {
        border-left: 4px solid #9e9e9e;
        opacity: 0.7;
    }
</style>
""", unsafe_allow_html=True)


def clean_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame for safe display in Streamlit."""
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    new_columns = []
    for col in df.columns:
        col_str = str(col)
        col_str = col_str.replace('\xa0', ' ').replace('\u200b', '').replace('\u00a0', ' ')
        col_str = col_str.strip()
        new_columns.append(col_str)
    df.columns = new_columns
    
    for col in df.columns:
        try:
            df[col] = df[col].apply(lambda x: str(x).replace('\xa0', ' ').strip() if pd.notna(x) else '')
        except:
            df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
    
    return df


def get_import_history():
    """Get import history from database."""
    if not db_exists():
        return pd.DataFrame()
    
    try:
        with get_connection() as conn:
            # Check if source_id column exists
            cursor = conn.execute("PRAGMA table_info(import_history)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'source_id' in columns:
                df = pd.read_sql("""
                    SELECT 
                        cs.short_name as framework,
                        ih.source_file,
                        ih.source_type,
                        ih.controls_imported,
                        ih.evidence_imported,
                        ih.domains_created,
                        ih.imported_at,
                        ih.notes
                    FROM import_history ih
                    LEFT JOIN compliance_sources cs ON ih.source_id = cs.id
                    ORDER BY ih.imported_at DESC
                    LIMIT 20
                """, conn)
            else:
                df = pd.read_sql("""
                    SELECT 
                        source_file,
                        source_type,
                        controls_imported,
                        evidence_imported,
                        domains_created,
                        imported_at,
                        notes
                    FROM import_history
                    ORDER BY imported_at DESC
                    LIMIT 20
                """, conn)
            return clean_dataframe_for_display(df)
    except:
        return pd.DataFrame()


def get_database_info():
    """Get information about the current database."""
    db_path = get_db_path()
    
    info = {
        'path': db_path,
        'exists': os.path.exists(db_path),
        'size': 0,
        'tables': []
    }
    
    if info['exists']:
        info['size'] = os.path.getsize(db_path)
        
        try:
            with get_connection() as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                info['tables'] = [t[0] for t in tables]
        except:
            pass
    
    return info


def get_excel_sheets(file_path: str):
    """Get list of sheets from an Excel file."""
    try:
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return []


def preview_sheet(file_path: str, sheet_name: str, nrows: int = 5):
    """Preview a sheet from Excel file."""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)
        return clean_dataframe_for_display(df)
    except Exception as e:
        st.error(f"Error previewing sheet: {e}")
        return pd.DataFrame()


def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location and return path."""
    try:
        if 'temp_dir' not in st.session_state or not os.path.exists(st.session_state.get('temp_dir', '')):
            st.session_state.temp_dir = tempfile.mkdtemp(prefix='grc_upload_')
        
        temp_path = os.path.join(st.session_state.temp_dir, uploaded_file.name)
        
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.temp_path = temp_path
        st.session_state.uploaded_filename = uploaded_file.name
        
        return temp_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None


def cleanup_temp_files():
    """Clean up temporary files."""
    temp_dir = st.session_state.get('temp_dir')
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    for key in ['temp_dir', 'temp_path', 'uploaded_filename', 'import_stage', 
                'controls_df', 'evidence_df', 'validation_result',
                'source_name', 'source_short_name', 'source_description', 'source_version']:
        if key in st.session_state:
            del st.session_state[key]


def render_compliance_sources_manager():
    """Render the compliance sources management UI."""
    st.subheader("📚 Compliance Sources Management")
    st.write("Manage your imported compliance frameworks.")
    
    sources = get_all_compliance_sources()
    
    if not sources:
        st.info("No compliance sources imported yet. Import data in the 'Import Data' tab.")
        return
    
    # Summary
    total_sources = len(sources)
    active_sources = sum(1 for s in sources if s.get('is_active', True))
    total_controls = sum(s.get('control_count', 0) for s in sources)
    total_evidence = sum(s.get('evidence_count', 0) for s in sources)
    
    sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
    with sum_col1:
        st.metric("Total Sources", total_sources)
    with sum_col2:
        st.metric("Active Sources", active_sources)
    with sum_col3:
        st.metric("Total Controls", total_controls)
    with sum_col4:
        st.metric("Total Evidence", total_evidence)
    
    st.markdown("---")
    
    # Source list
    for source in sources:
        is_active = source.get('is_active', True)
        card_class = "source-active" if is_active else "source-inactive"
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                status_icon = "✅" if is_active else "⏸️"
                st.markdown(f"### {status_icon} {source['name']}")
                st.caption(f"Short: **{source.get('short_name', 'N/A')}** | Version: **{source.get('version', 'N/A')}**")
                st.caption(f"Controls: **{source.get('control_count', 0)}** | Evidence: **{source.get('evidence_count', 0)}**")
                if source.get('description'):
                    st.caption(f"_{source['description']}_")
            
            with col2:
                if st.button(
                    "⏸️ Deactivate" if is_active else "▶️ Activate",
                    key=f"toggle_{source['id']}",
                    use_container_width=True
                ):
                    toggle_compliance_source(source['id'])
                    st.rerun()
            
            with col3:
                if st.button("✏️ Edit", key=f"edit_{source['id']}", use_container_width=True):
                    st.session_state[f"editing_source_{source['id']}"] = True
                    st.rerun()
            
            with col4:
                if st.button("🗑️ Delete", key=f"delete_{source['id']}", type="secondary", use_container_width=True):
                    st.session_state[f"confirm_delete_{source['id']}"] = True
                    st.rerun()
            
            # Edit form
            if st.session_state.get(f"editing_source_{source['id']}"):
                with st.form(key=f"edit_form_{source['id']}"):
                    st.markdown("#### Edit Source")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        new_name = st.text_input("Name", value=source['name'])
                        new_short = st.text_input("Short Name", value=source.get('short_name', ''))
                    with edit_col2:
                        new_version = st.text_input("Version", value=source.get('version', ''))
                        new_desc = st.text_area("Description", value=source.get('description', ''))
                    
                    form_col1, form_col2 = st.columns(2)
                    with form_col1:
                        if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                            update_compliance_source(
                                source['id'],
                                name=new_name,
                                short_name=new_short,
                                version=new_version,
                                description=new_desc
                            )
                            del st.session_state[f"editing_source_{source['id']}"]
                            st.success("Source updated!")
                            st.rerun()
                    with form_col2:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            del st.session_state[f"editing_source_{source['id']}"]
                            st.rerun()
            
            # Delete confirmation
            if st.session_state.get(f"confirm_delete_{source['id']}"):
                st.warning(f"⚠️ Are you sure you want to delete **{source['name']}**? This will delete all associated controls and evidence!")
                
                del_col1, del_col2 = st.columns(2)
                with del_col1:
                    if st.button("Yes, Delete", key=f"confirm_del_{source['id']}", type="primary", use_container_width=True):
                        delete_compliance_source(source['id'])
                        del st.session_state[f"confirm_delete_{source['id']}"]
                        st.success(f"Deleted {source['name']}")
                        st.cache_data.clear()
                        st.rerun()
                with del_col2:
                    if st.button("Cancel", key=f"cancel_del_{source['id']}", use_container_width=True):
                        del st.session_state[f"confirm_delete_{source['id']}"]
                        st.rerun()
            
            st.markdown("---")


def main():
    st.title("⚙️ Admin Panel")
    st.caption("Manage data imports, compliance sources, database settings, and system configuration")
    
    # Initialize session state
    if 'show_reset_confirm' not in st.session_state:
        st.session_state.show_reset_confirm = False
    if 'import_stage' not in st.session_state:
        st.session_state.import_stage = 'upload'
    
    # -----------------------
    # Tabs
    # -----------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Import Data",
        "📚 Compliance Sources",
        "🗄️ Database",
        "📜 Import History",
        "🔧 Settings"
    ])
    
    with tab1:
        st.subheader("Import Data")
        st.write("Upload compliance data files to import into the platform.")
        
        # Debug info
        with st.expander("🔧 Debug Info", expanded=False):
            st.write(f"Import Stage: `{st.session_state.get('import_stage', 'upload')}`")
            st.write(f"Temp Path: `{st.session_state.get('temp_path', 'None')}`")
            st.write(f"Uploaded Filename: `{st.session_state.get('uploaded_filename', 'None')}`")
        
        # Reset button
        if st.session_state.get('import_stage') != 'upload':
            if st.button("🔄 Start Over", type="secondary"):
                cleanup_temp_files()
                st.rerun()
        
        # =====================
        # STAGE 1: FILE UPLOAD
        # =====================
        if st.session_state.get('import_stage', 'upload') == 'upload':
            st.markdown("### 📁 Upload File")
            
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['xls', 'xlsx', 'json', 'xml', 'zip', 'csv'],
                help="Supported formats: Excel (.xls, .xlsx), JSON (.json), CSV (.csv), XML (.xml), ZIP archive (.zip)",
                key="file_uploader"
            )
            
            if uploaded_file is not None:
                st.success(f"✅ File received: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
                
                temp_path = save_uploaded_file(uploaded_file)
                
                if temp_path:
                    # Compliance Source Info
                    st.markdown("### 📚 Compliance Source Information")
                    st.info("Give this compliance framework a name to identify it in the system.")
                    
                    src_col1, src_col2 = st.columns(2)
                    with src_col1:
                        # Auto-generate name from filename
                        default_name = os.path.splitext(uploaded_file.name)[0].replace('_', ' ').replace('-', ' ').title()
                        source_name = st.text_input(
                            "Framework Name *",
                            value=default_name,
                            help="e.g., 'Adobe CCF', 'SCF 2024', 'NIST 800-53'"
                        )
                        st.session_state.source_name = source_name
                        
                        source_short = st.text_input(
                            "Short Name",
                            value=source_name[:10] if source_name else "",
                            help="Short identifier (e.g., 'CCF', 'SCF')"
                        )
                        st.session_state.source_short_name = source_short
                    
                    with src_col2:
                        source_version = st.text_input(
                            "Version",
                            placeholder="e.g., 3.0, 2024.1",
                            help="Version of this compliance framework"
                        )
                        st.session_state.source_version = source_version
                        
                        source_desc = st.text_area(
                            "Description",
                            placeholder="Brief description of this framework...",
                            help="Optional description"
                        )
                        st.session_state.source_description = source_desc
                    
                    # Excel sheet selection
                    if uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
                        st.markdown("### 📋 Sheet Selection")
                        
                        sheets = get_excel_sheets(temp_path)
                        
                        if sheets:
                            st.info(f"Found **{len(sheets)}** sheets: {', '.join(sheets)}")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                main_sheet = st.selectbox(
                                    "📊 Main Controls Sheet *",
                                    options=["(Auto-detect)"] + sheets,
                                    help="Sheet containing the main controls data",
                                    key="main_sheet_select"
                                )
                            
                            with col2:
                                guidance_sheet = st.selectbox(
                                    "📝 Guidance Sheet (optional)",
                                    options=["(None)"] + sheets,
                                    help="Sheet containing implementation guidance",
                                    key="guidance_sheet_select"
                                )
                            
                            with col3:
                                evidence_sheet = st.selectbox(
                                    "📁 Evidence Sheet (optional)",
                                    options=["(None)"] + sheets,
                                    help="Sheet containing evidence/artifacts list",
                                    key="evidence_sheet_select"
                                )
                            
                            # Preview
                            st.markdown("### 👁️ Sheet Preview")
                            
                            preview_sheet_name = st.selectbox(
                                "Select sheet to preview",
                                options=sheets,
                                key="preview_sheet_select"
                            )
                            
                            if preview_sheet_name:
                                preview_df = preview_sheet(temp_path, preview_sheet_name, nrows=10)
                                if not preview_df.empty:
                                    st.write(f"**Columns ({len(preview_df.columns)}):** {', '.join(preview_df.columns.tolist())}")
                                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
                                else:
                                    st.warning("Sheet appears to be empty or could not be read.")
                        else:
                            st.error("Could not read sheets from Excel file.")
                    
                    st.markdown("---")
                    
                    # Import options
                    st.markdown("### ⚙️ Import Options")
                    
                    opt_col1, opt_col2 = st.columns(2)
                    
                    with opt_col1:
                        force_recreate = st.checkbox(
                            "🗑️ Force Recreate Database",
                            help="Delete existing data and recreate the schema (USE WITH CAUTION!)",
                            key="force_recreate_check"
                        )
                        st.session_state.force_recreate = force_recreate
                    
                    with opt_col2:
                        validate_only = st.checkbox(
                            "🔍 Validate Only",
                            help="Only validate the file, don't import",
                            key="validate_only_check"
                        )
                        st.session_state.validate_only = validate_only
                    
                    st.markdown("---")
                    
                    # Validation check
                    if not source_name:
                        st.warning("⚠️ Please enter a Framework Name before proceeding.")
                    else:
                        if st.button("🚀 Validate & Preview", type="primary", use_container_width=True):
                            st.session_state.import_stage = 'validate'
                            st.rerun()
            else:
                st.info("👆 Please upload a file to continue")
                
                # Alternative: specify path
                st.markdown("---")
                st.markdown("### 📂 Or Specify File Path")
                
                path_col1, path_col2 = st.columns([3, 1])
                
                with path_col1:
                    file_path = st.text_input(
                        "File/Folder Path",
                        placeholder="/path/to/data.xlsx or /path/to/csv_folder",
                        help="Enter the path to a file or folder containing CSV files"
                    )
                
                with path_col2:
                    format_hint = st.selectbox(
                        "Format",
                        ["auto", "excel", "json", "csv", "xml", "zip"],
                        help="auto will detect based on file extension"
                    )
                
                if file_path and st.button("📥 Import from Path", use_container_width=True):
                    if os.path.exists(file_path):
                        st.session_state.temp_path = file_path
                        st.session_state.uploaded_filename = os.path.basename(file_path)
                        st.session_state.source_name = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ').title()
                        st.session_state.import_stage = 'validate'
                        st.rerun()
                    else:
                        st.error(f"Path not found: {file_path}")
        
        # =====================
        # STAGE 2: VALIDATION
        # =====================
        elif st.session_state.get('import_stage') == 'validate':
            st.markdown("### 🔍 Validating Data...")
            
            temp_path = st.session_state.get('temp_path')
            filename = st.session_state.get('uploaded_filename', 'unknown')
            source_name = st.session_state.get('source_name', 'Unknown Framework')
            
            if not temp_path or not os.path.exists(temp_path):
                st.error("❌ File not found. Please upload again.")
                st.session_state.import_stage = 'upload'
                st.rerun()
            
            try:
                sheet_main = None
                sheet_guidance = None
                sheet_evidence = None
                
                if filename.lower().endswith(('.xls', '.xlsx')):
                    main_sel = st.session_state.get('main_sheet_select', '(Auto-detect)')
                    guidance_sel = st.session_state.get('guidance_sheet_select', '(None)')
                    evidence_sel = st.session_state.get('evidence_sheet_select', '(None)')
                    
                    if main_sel != "(Auto-detect)":
                        sheet_main = main_sel
                    if guidance_sel != "(None)":
                        sheet_guidance = guidance_sel
                    if evidence_sel != "(None)":
                        sheet_evidence = evidence_sel
                
                from utils.adapters import get_adapter, clean_dataframe, sanitize_for_display
                
                with st.spinner("Loading adapter..."):
                    adapter = get_adapter(
                        temp_path,
                        format_hint='auto',
                        sheet_main=sheet_main,
                        sheet_guidance=sheet_guidance,
                        sheet_evidence=sheet_evidence,
                        column_mappings=None
                    )
                
                with st.spinner("Validating data..."):
                    validation = adapter.validate()
                
                st.session_state.validation_result = validation
                
                st.markdown("### 📋 Validation Results")
                st.info(f"**Framework:** {source_name}")
                
                if validation['valid']:
                    st.success("✅ Validation passed!")
                else:
                    st.error("❌ Validation failed!")
                
                if validation.get('errors'):
                    st.markdown("**Errors:**")
                    for err in validation['errors']:
                        st.error(f"❌ {err}")
                
                if validation.get('warnings'):
                    st.markdown("**Warnings:**")
                    for warn in validation['warnings']:
                        st.warning(f"⚠️ {warn}")
                
                if validation.get('info'):
                    st.markdown("**Info:**")
                    for info in validation['info']:
                        st.info(f"ℹ️ {info}")
                
                if validation['valid']:
                    st.markdown("---")
                    st.markdown("### 📥 Data Preview")
                    
                    with st.spinner("Loading data..."):
                        controls_df, evidence_df = adapter.load()
                        controls_df = clean_dataframe(controls_df)
                        evidence_df = clean_dataframe(evidence_df)
                    
                    st.session_state.controls_df = controls_df
                    st.session_state.evidence_df = evidence_df
                    
                    qual_col1, qual_col2, qual_col3 = st.columns(3)
                    with qual_col1:
                        st.metric("Total Controls", len(controls_df))
                    with qual_col2:
                        st.metric("Total Evidence", len(evidence_df))
                    with qual_col3:
                        domains = controls_df['domain'].dropna().nunique() if 'domain' in controls_df.columns else 0
                        st.metric("Unique Domains", domains)
                    
                    with st.expander("📊 Preview Controls (first 10 rows)", expanded=True):
                        display_df = sanitize_for_display(controls_df.head(10))
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    if not evidence_df.empty:
                        with st.expander("📁 Preview Evidence (first 10 rows)"):
                            display_df = sanitize_for_display(evidence_df.head(10))
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    
                    if st.session_state.get('validate_only'):
                        st.success("✅ Validation complete! (Validate-only mode)")
                        if st.button("🔄 Start Over"):
                            cleanup_temp_files()
                            st.rerun()
                    else:
                        if st.session_state.get('force_recreate'):
                            st.warning("⚠️ This will DELETE all existing data!")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Confirm Import", type="primary", use_container_width=True):
                                st.session_state.import_stage = 'import'
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancel", use_container_width=True):
                                cleanup_temp_files()
                                st.rerun()
                else:
                    if st.button("🔄 Go Back"):
                        st.session_state.import_stage = 'upload'
                        st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error during validation: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                
                if st.button("🔄 Start Over"):
                    cleanup_temp_files()
                    st.rerun()
        
        # =====================
        # STAGE 3: IMPORT
        # =====================
        elif st.session_state.get('import_stage') == 'import':
            st.markdown("### 📥 Importing Data...")
            
            controls_df = st.session_state.get('controls_df')
            evidence_df = st.session_state.get('evidence_df')
            filename = st.session_state.get('uploaded_filename', 'unknown')
            force_recreate = st.session_state.get('force_recreate', False)
            
            # Source info
            source_name = st.session_state.get('source_name', 'Unknown Framework')
            source_short = st.session_state.get('source_short_name')
            source_desc = st.session_state.get('source_description')
            source_version = st.session_state.get('source_version')
            
            if controls_df is None:
                st.error("❌ No data to import. Please start over.")
                st.session_state.import_stage = 'upload'
                st.rerun()
            
            try:
                progress_bar = st.progress(0, text="Starting import...")
                
                from seed import seed_from_dataframes, create_schema
                
                progress_bar.progress(20, text="Preparing database...")
                
                if force_recreate:
                    create_schema(get_db_path(), force_recreate=True)
                
                progress_bar.progress(40, text="Importing data...")
                
                stats = seed_from_dataframes(
                    controls_df,
                    evidence_df,
                    get_db_path(),
                    source_info=filename,
                    source_name=source_name,
                    source_short_name=source_short,
                    source_description=source_desc,
                    source_version=source_version
                )
                
                progress_bar.progress(100, text="Complete!")
                
                st.success("🎉 Import completed successfully!")
                st.info(f"📚 Framework: **{source_name}**")
                
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("Controls Imported", stats.get('controls_imported', 0))
                with stat_col2:
                    st.metric("Evidence Imported", stats.get('evidence_imported', 0))
                with stat_col3:
                    st.metric("Domains Created", stats.get('domains_created', 0))
                with stat_col4:
                    st.metric("Evidence Links", stats.get('evidence_links', 0))
                
                st.cache_data.clear()
                st.balloons()
                
                st.session_state.import_stage = 'done'
                cleanup_temp_files()
                
                st.info("✅ Import complete! Navigate to other pages to see your data.")
                
                if st.button("📊 Go to Dashboard"):
                    st.switch_page("pages/1_📊_Dashboard.py")
            
            except Exception as e:
                st.error(f"❌ Import failed: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                
                if st.button("🔄 Start Over"):
                    cleanup_temp_files()
                    st.rerun()
        
        # =====================
        # STAGE 4: DONE
        # =====================
        elif st.session_state.get('import_stage') == 'done':
            st.success("🎉 Import completed!")
            st.info("Navigate to other pages to see your data, or import another file.")
            
            if st.button("📤 Import Another File", type="primary"):
                cleanup_temp_files()
                st.rerun()
    
    # =====================
    # TAB 2: COMPLIANCE SOURCES
    # =====================
    with tab2:
        render_compliance_sources_manager()
    
    # =====================
    # TAB 3: DATABASE
    # =====================
    with tab3:
        st.subheader("Database Management")
        
        db_info = get_database_info()
        
        st.markdown("### 📊 Current Database")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown(f"**Path:** `{db_info['path']}`")
            st.markdown(f"**Exists:** {'Yes ✅' if db_info['exists'] else 'No ❌'}")
        
        with info_col2:
            if db_info['exists']:
                size_kb = db_info['size'] / 1024
                size_mb = size_kb / 1024
                if size_mb >= 1:
                    st.markdown(f"**Size:** {size_mb:.2f} MB")
                else:
                    st.markdown(f"**Size:** {size_kb:.2f} KB")
                
                st.markdown(f"**Tables:** {', '.join(db_info['tables'])}")
        
        st.markdown("---")
        
        if db_info['exists']:
            st.markdown("### 📈 Table Statistics")
            
            try:
                with get_connection() as conn:
                    table_stats = []
                    for table in db_info['tables']:
                        if not table.startswith('sqlite_'):
                            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            table_stats.append({'Table': table, 'Rows': count})
                    
                    if table_stats:
                        stats_df = pd.DataFrame(table_stats)
                        st.dataframe(stats_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error reading table stats: {e}")
        
        st.markdown("### 🔧 Database Actions")
        
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🔄 Refresh Stats", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        with action_col2:
            if db_info['exists']:
                with open(db_info['path'], 'rb') as f:
                    st.download_button(
                        "⬇️ Download Database",
                        data=f.read(),
                        file_name="grc_backup.db",
                        mime="application/octet-stream",
                        use_container_width=True
                    )
        
        with action_col3:
            if st.button("🗑️ Reset Database", type="secondary", use_container_width=True):
                st.session_state.show_reset_confirm = True
        
        if st.session_state.get('show_reset_confirm'):
            st.warning("⚠️ This will DELETE ALL DATA! This action cannot be undone.")
            
            confirm_col1, confirm_col2 = st.columns(2)
            
            with confirm_col1:
                if st.button("Yes, Delete Everything", type="primary"):
                    try:
                        if os.path.exists(db_info['path']):
                            os.remove(db_info['path'])
                        st.success("Database deleted.")
                        st.session_state.show_reset_confirm = False
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            with confirm_col2:
                if st.button("Cancel"):
                    st.session_state.show_reset_confirm = False
                    st.rerun()
    
    # =====================
    # TAB 4: HISTORY
    # =====================
    with tab4:
        st.subheader("Import History")
        
        history_df = get_import_history()
        
        if history_df.empty:
            st.info("No import history available.")
        else:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
    
    # =====================
    # TAB 5: SETTINGS
    # =====================
        # =====================
    # TAB 5: SETTINGS
    # =====================
    with tab5:
        st.subheader("Settings")
        
        st.markdown("### 📋 Supported File Formats")
        
        st.markdown("""
        | Format | Extension | Description |
        |--------|-----------|-------------|
        | Excel | .xls, .xlsx | Adobe CCF, SCF, or custom Excel files |
        | JSON | .json | Structured JSON with controls/evidence |
        | CSV | .csv | Single CSV file or folder with multiple CSVs |
        | XML | .xml | XML formatted controls data |
        | ZIP | .zip | ZIP archive containing any of the above |
        """)
        
        st.markdown("---")
        
        st.markdown("### 🔧 System Information")
        
        sys_col1, sys_col2 = st.columns(2)
        
        with sys_col1:
            st.markdown(f"**Python Version:** {sys.version.split()[0]}")
            st.markdown(f"**Streamlit Version:** {st.__version__}")
            st.markdown(f"**Pandas Version:** {pd.__version__}")
        
        with sys_col2:
            st.markdown(f"**Working Directory:** `{os.getcwd()}`")
            st.markdown(f"**Database Path:** `{get_db_path()}`")
        
        st.markdown("---")
        
        st.markdown("### 📦 Dependencies Status")
        
        dependencies = {
            'pandas': 'Data processing',
            'streamlit': 'Web interface',
            'plotly': 'Charts and visualizations',
            'openpyxl': 'Excel export (.xlsx)',
            'xlrd': 'Legacy Excel reading (.xls)',
        }
        
        dep_status = []
        for dep, desc in dependencies.items():
            try:
                __import__(dep)
                dep_status.append({'Package': dep, 'Description': desc, 'Status': '✅ Installed'})
            except ImportError:
                dep_status.append({'Package': dep, 'Description': desc, 'Status': '❌ Not installed'})
        
        st.dataframe(pd.DataFrame(dep_status), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        st.markdown("### 🎨 Application Settings")
        
        settings_col1, settings_col2 = st.columns(2)
        
        with settings_col1:
            st.markdown("#### Cache Management")
            st.caption("Clear cached data to refresh all statistics and queries.")
            
            if st.button("🗑️ Clear All Cache", use_container_width=True):
                st.cache_data.clear()
                st.success("✅ Cache cleared successfully!")
                st.rerun()
        
        with settings_col2:
            st.markdown("#### Session State")
            st.caption("Reset session state to clear temporary data.")
            
            if st.button("🔄 Reset Session State", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key not in ['db_path']:
                        del st.session_state[key]
                st.success("✅ Session state reset!")
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### 📊 Database Schema Info")
        
        if db_exists():
            with st.expander("View Database Schema", expanded=False):
                try:
                    with get_connection() as conn:
                        # Get all tables
                        tables = conn.execute("""
                            SELECT name FROM sqlite_master 
                            WHERE type='table' AND name NOT LIKE 'sqlite_%'
                            ORDER BY name
                        """).fetchall()
                        
                        for table in tables:
                            table_name = table[0]
                            st.markdown(f"#### 📁 `{table_name}`")
                            
                            # Get columns
                            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                            
                            col_data = []
                            for col in columns:
                                col_data.append({
                                    'Column': col[1],
                                    'Type': col[2],
                                    'Nullable': 'No' if col[3] else 'Yes',
                                    'Primary Key': '✅' if col[5] else ''
                                })
                            
                            if col_data:
                                st.dataframe(
                                    pd.DataFrame(col_data),
                                    use_container_width=True,
                                    hide_index=True
                                )
                            
                            st.markdown("---")
                except Exception as e:
                    st.error(f"Error reading schema: {e}")
        else:
            st.info("No database exists yet. Import data to create the database.")
        
        st.markdown("---")
        
        st.markdown("### 📝 About")
        
        st.markdown("""
        **GRC Compliance Platform** v1.0.0
        
        A comprehensive Governance, Risk, and Compliance management system built with:
        - 🐍 Python & Streamlit
        - 📊 Plotly for visualizations
        - 🗄️ SQLite for data storage
        
        **Features:**
        - Multi-compliance framework support
        - Import from Excel, JSON, CSV, XML, ZIP
        - Framework mapping and cross-reference
        - Gap analysis and reporting
        - Evidence tracking
        
        ---
        
        Built with ❤️ for compliance professionals.
        """)


if __name__ == "__main__":
    main()