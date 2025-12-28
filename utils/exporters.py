import pandas as pd
import json
import io
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def export_to_csv(df: pd.DataFrame, include_index: bool = False) -> str:
    """Export DataFrame to CSV string."""
    return df.to_csv(index=include_index)


def export_to_json(df: pd.DataFrame, orient: str = 'records') -> str:
    """Export DataFrame to JSON string."""
    return df.to_json(orient=orient, indent=2)


def export_to_excel(
    dataframes: Dict[str, pd.DataFrame],
    sheet_names: Dict[str, str] = None
) -> bytes:
    """
    Export multiple DataFrames to Excel workbook.
    
    Args:
        dataframes: Dict mapping keys to DataFrames
        sheet_names: Optional dict mapping keys to custom sheet names
    
    Returns:
        Excel file as bytes
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for key, df in dataframes.items():
            sheet_name = sheet_names.get(key, key) if sheet_names else key
            # Excel sheet names max 31 chars
            sheet_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output.getvalue()


def format_controls_for_export(
    controls_df: pd.DataFrame,
    include_mappings: bool = True,
    flatten_mappings: bool = False
) -> pd.DataFrame:
    """
    Format controls DataFrame for export.
    
    Args:
        controls_df: Raw controls DataFrame
        include_mappings: Whether to include framework mappings
        flatten_mappings: Whether to flatten mappings into separate columns
    
    Returns:
        Formatted DataFrame
    """
    df = controls_df.copy()
    
    # Ensure standard column order
    base_cols = ['ccf_id', 'domain', 'title', 'description', 'type', 'theme', 'guidance', 'testing']
    
    result_cols = [c for c in base_cols if c in df.columns]
    
    if include_mappings and 'mappings' in df.columns:
        if flatten_mappings:
            # Extract all unique framework names
            frameworks = set()
            for _, row in df.iterrows():
                m = row.get('mappings')
                if m and isinstance(m, dict):
                    frameworks.update(m.keys())
                elif m and isinstance(m, str):
                    try:
                        parsed = json.loads(m)
                        if isinstance(parsed, dict):
                            frameworks.update(parsed.keys())
                    except:
                        pass
            
            # Add framework columns
            for fw in sorted(frameworks):
                def get_framework_refs(mappings, fw=fw):
                    if not mappings:
                        return None
                    if isinstance(mappings, str):
                        try:
                            mappings = json.loads(mappings)
                        except:
                            return None
                    if isinstance(mappings, dict):
                        refs = mappings.get(fw)
                        if refs:
                            if isinstance(refs, list):
                                return ', '.join(str(r) for r in refs)
                            return str(refs)
                    return None
                
                df[fw] = df['mappings'].apply(get_framework_refs)
                result_cols.append(fw)
        else:
            # Keep mappings as JSON string
            def mappings_to_str(m):
                if not m or (isinstance(m, float) and pd.isna(m)):
                    return ''
                if isinstance(m, dict):
                    return json.dumps(m)
                return str(m)
            
            df['mappings'] = df['mappings'].apply(mappings_to_str)
            result_cols.append('mappings')
    
    return df[result_cols]


def generate_compliance_report(
    controls_df: pd.DataFrame,
    framework: str = None,
    include_evidence: bool = True
) -> Dict[str, Any]:
    """
    Generate a compliance report for a specific framework.
    
    Args:
        controls_df: Controls DataFrame
        framework: Specific framework to report on (or None for all)
        include_evidence: Whether to include evidence status
    
    Returns:
        Report dictionary
    """
    report = {
        'framework': framework or 'All Frameworks',
        'generated_at': pd.Timestamp.now().isoformat(),
        'summary': {},
        'details': []
    }
    
    if controls_df is None or controls_df.empty:
        report['summary'] = {'total_controls': 0}
        return report
    
    # Filter by framework if specified
    if framework and 'mappings' in controls_df.columns:
        def has_framework(m):
            if not m:
                return False
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                except:
                    return False
            if isinstance(m, dict):
                return framework in m
            return False
        
        filtered_df = controls_df[controls_df['mappings'].apply(has_framework)]
    else:
        filtered_df = controls_df
    
    total = len(filtered_df)
    report['summary'] = {
        'total_controls': total,
        'with_guidance': int(filtered_df['guidance'].notna().sum()) if 'guidance' in filtered_df.columns else 0,
        'with_testing': int(filtered_df['testing'].notna().sum()) if 'testing' in filtered_df.columns else 0,
        'with_evidence': int(filtered_df['evidence_count'].gt(0).sum()) if 'evidence_count' in filtered_df.columns else 0
    }
    
    # Calculate percentages
    if total > 0:
        report['summary']['guidance_coverage'] = (report['summary']['with_guidance'] / total) * 100
        report['summary']['testing_coverage'] = (report['summary']['with_testing'] / total) * 100
        report['summary']['evidence_coverage'] = (report['summary']['with_evidence'] / total) * 100
    
    # Add control details
    for _, row in filtered_df.iterrows():
        detail = {
            'ccf_id': row.get('ccf_id'),
            'title': row.get('title'),
            'domain': row.get('domain'),
            'has_guidance': bool(row.get('guidance')),
            'has_testing': bool(row.get('testing'))
        }
        
        if framework and 'mappings' in row:
            m = row['mappings']
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                except:
                    m = {}
            if isinstance(m, dict):
                detail['framework_refs'] = m.get(framework)
        
        report['details'].append(detail)
    
    return report


def export_gap_analysis(gap_data: Dict[str, pd.DataFrame]) -> bytes:
    """
    Export gap analysis to Excel workbook.
    
    Args:
        gap_data: Dict with gap analysis DataFrames
    
    Returns:
        Excel file as bytes
    """
    sheet_names = {
        'missing_guidance': 'Missing Guidance',
        'missing_testing': 'Missing Testing',
        'missing_evidence': 'Missing Evidence',
        'orphan_evidence': 'Orphan Evidence'
    }
    
    return export_to_excel(gap_data, sheet_names)


def generate_framework_matrix(controls_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a framework coverage matrix.
    
    Returns DataFrame with controls as rows and frameworks as columns,
    showing whether each control maps to each framework.
    """
    if controls_df is None or controls_df.empty:
        return pd.DataFrame()
    
    if 'mappings' not in controls_df.columns:
        return controls_df[['ccf_id', 'title', 'domain']].copy()
    
    # Extract all frameworks
    frameworks = set()
    for _, row in controls_df.iterrows():
        m = row.get('mappings')
        if m:
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                except:
                    continue
            if isinstance(m, dict):
                frameworks.update(m.keys())
    
    # Build matrix
    result = controls_df[['ccf_id', 'title', 'domain']].copy()
    
    for fw in sorted(frameworks):
        def get_refs(mappings, fw=fw):
            if not mappings:
                return ''
            if isinstance(mappings, str):
                try:
                    mappings = json.loads(mappings)
                except:
                    return ''
            if isinstance(mappings, dict):
                refs = mappings.get(fw)
                if refs:
                    if isinstance(refs, list):
                        return ', '.join(str(r) for r in refs)
                    return str(refs)
            return ''
        
        result[fw] = controls_df['mappings'].apply(get_refs)
    
    return result


def generate_evidence_checklist(
    controls_df: pd.DataFrame,
    evidence_df: pd.DataFrame,
    domain: str = None
) -> pd.DataFrame:
    """
    Generate an evidence collection checklist.
    
    Returns DataFrame with evidence items and their associated controls.
    """
    if evidence_df is None or evidence_df.empty:
        return pd.DataFrame(columns=['ref_id', 'title', 'domain', 'associated_controls', 'status'])
    
    result = evidence_df.copy()
    
    # Filter by domain if specified
    if domain and 'domain' in result.columns:
        result = result[result['domain'] == domain]
    
    # Add placeholder columns
    result['associated_controls'] = ''
    result['status'] = 'Not Collected'
    
    return result