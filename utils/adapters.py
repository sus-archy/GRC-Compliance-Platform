import pandas as pd
import json
import os
import re
import zipfile
import tempfile
import logging
import xml.etree.ElementTree as ET
import unicodedata
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLEANING FUNCTIONS
# =============================================================================

def clean_text(val) -> Optional[str]:
    """Clean and normalize text values, removing special characters."""
    if pd.isna(val) or val == "" or val is None:
        return None
    
    # Convert to string
    s = str(val)
    
    # Replace non-breaking spaces and other special whitespace
    s = s.replace('\xa0', ' ')      # Non-breaking space
    s = s.replace('\u200b', '')     # Zero-width space
    s = s.replace('\u00a0', ' ')    # Another form of non-breaking space
    s = s.replace('\u2003', ' ')    # Em space
    s = s.replace('\u2002', ' ')    # En space
    s = s.replace('\u2009', ' ')    # Thin space
    s = s.replace('\r\n', '\n')     # Normalize line endings
    s = s.replace('\r', '\n')
    
    # Normalize unicode characters
    try:
        s = unicodedata.normalize('NFKC', s)
    except:
        pass
    
    # Strip whitespace
    s = s.strip()
    
    return s if s else None


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame column names by removing special characters."""
    if df is None or df.empty:
        return df
    
    new_columns = []
    for col in df.columns:
        # Convert to string and clean
        col_str = str(col)
        # Replace special characters
        col_str = col_str.replace('\xa0', ' ')
        col_str = col_str.replace('\u200b', '')
        col_str = col_str.replace('\u00a0', ' ')
        col_str = col_str.replace('\u2003', ' ')
        col_str = col_str.replace('\u2002', ' ')
        # Normalize unicode
        try:
            col_str = unicodedata.normalize('NFKC', col_str)
        except:
            pass
        # Strip whitespace
        col_str = col_str.strip()
        new_columns.append(col_str)
    
    df.columns = new_columns
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean entire DataFrame for Arrow compatibility.
    - Clean column names
    - Convert all object columns to clean strings
    - Handle mixed types
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # Clean column names
    df = clean_column_names(df)
    
    # Clean each column
    for col in df.columns:
        if df[col].dtype == 'object':
            # Apply clean_text to all values
            df[col] = df[col].apply(lambda x: clean_text(x) if pd.notna(x) else None)
    
    return df


def sanitize_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare DataFrame for Streamlit display by ensuring all data is Arrow-compatible.
    Converts all values to strings to prevent serialization errors.
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # Clean column names
    df = clean_column_names(df)
    
    # Convert all columns to string type for safe display
    for col in df.columns:
        try:
            # Convert to string and clean
            def safe_convert(x):
                if pd.isna(x) or x is None:
                    return ''
                s = str(x)
                # Clean special characters
                s = s.replace('\xa0', ' ')
                s = s.replace('\u200b', '')
                s = s.replace('\u00a0', ' ')
                try:
                    s = unicodedata.normalize('NFKC', s)
                except:
                    pass
                return s.strip()
            
            df[col] = df[col].apply(safe_convert)
        except Exception as e:
            # If conversion fails, convert entire column to string
            try:
                df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
            except:
                df[col] = ''
    
    return df


def split_list_string(s: Optional[str], delimiters=r"[\n\r,;|]+") -> List[str]:
    """Split a string by multiple delimiters."""
    if not s or not str(s).strip():
        return []
    # Clean the string first
    s = clean_text(s)
    if not s:
        return []
    return [x.strip() for x in re.split(delimiters, s) if x.strip()]


def fuzzy_match_column(columns: List[str], target: str, threshold: float = 0.6) -> Optional[str]:
    """Find the best matching column name using fuzzy matching."""
    target_lower = target.lower().replace("_", " ").replace("-", " ")
    
    best_match = None
    best_score = threshold
    
    for col in columns:
        col_lower = col.lower().replace("_", " ").replace("-", " ")
        
        # Exact match
        if col_lower == target_lower:
            return col
        
        # Contains match
        if target_lower in col_lower or col_lower in target_lower:
            score = 0.8
            if score > best_score:
                best_score = score
                best_match = col
                continue
        
        # Fuzzy match
        score = SequenceMatcher(None, target_lower, col_lower).ratio()
        if score > best_score:
            best_score = score
            best_match = col
    
    return best_match


# =============================================================================
# COLUMN MAPPER
# =============================================================================

class ColumnMapper:
    """Handles column name mapping with fuzzy matching."""
    
    DEFAULT_CONTROL_MAPPINGS = {
        'ccf_id': [
            'ccf_id', 'ccf id', 'control id', 'control_id', 'id', 'ref', 'reference',
            'scf #', 'scf#', 'scf id', 'control #', 'control#', 'identifier',
            'scf control', 'control identifier', 'ctrl id', '#', 'no', 'number',
            'control number', 'ctrl', 'control ref'
        ],
        'domain': [
            'control domain', 'domain', 'category', 'control category',
            'scf domain', 'security domain', 'control family', 'family',
            'domains & principles', 'security function', 'function'
        ],
        'title': [
            'control name', 'title', 'name', 'control title',
            'scf control', 'control', 'short description', 'control short name',
            'control summary', 'summary'
        ],
        'description': [
            'control description', 'description', 'desc', 'details',
            'control objective', 'objective', 'full description', 'control text',
            'scf control description', 'control question', 'long description',
            'control detail', 'control details'
        ],
        'type': [
            'control type', 'type', 'control_type', 'category type',
            'classification', 'control classification'
        ],
        'theme': [
            'control theme', 'theme', 'control_theme', 'control category',
            'subcategory', 'sub-category'
        ],
        'guidance': [
            'control implementation guidance', 'implementation guidance', 'guidance',
            'implementation', 'implementation notes', 'notes', 'control guidance',
            'implementation details', 'how to implement', 'supplemental guidance',
            'implementation instructions'
        ],
        'testing': [
            'control testing procedure', 'testing procedure', 'testing', 'test procedure',
            'audit procedure', 'assessment', 'assessment procedure', 'test', 'audit',
            'assessment objectives', 'testing guidance', 'audit steps', 'test steps',
            'verification', 'validation'
        ],
        'artifacts': [
            'audit artifacts', 'artifacts', 'evidence', 'evidence refs', 'evidence references',
            'required evidence', 'evidence required', 'evidence request', 'erl',
            'evidence list', 'documentation', 'required documentation'
        ]
    }
    
    DEFAULT_EVIDENCE_MAPPINGS = {
        'ref_id': [
            'reference #', 'reference', 'ref_id', 'ref', 'id', 'evidence id', 'evidence_id',
            'erl #', 'erl#', 'erl id', 'artifact id', 'artifact #', '#', 'no', 'number',
            'evidence number', 'evidence ref', 'evidence reference'
        ],
        'title': [
            'evidence title', 'title', 'name', 'evidence name', 'description',
            'artifact name', 'artifact title', 'evidence description',
            'artifact description', 'evidence summary'
        ],
        'domain': [
            'evidence domain', 'domain', 'category', 'evidence category',
            'artifact domain', 'artifact category'
        ]
    }
    
    def __init__(self, custom_mappings: Dict[str, List[str]] = None):
        self.control_mappings = self.DEFAULT_CONTROL_MAPPINGS.copy()
        self.evidence_mappings = self.DEFAULT_EVIDENCE_MAPPINGS.copy()
        
        if custom_mappings:
            if 'controls' in custom_mappings:
                for key, values in custom_mappings['controls'].items():
                    if key in self.control_mappings:
                        # Prepend custom values
                        self.control_mappings[key] = values + self.control_mappings[key]
                    else:
                        self.control_mappings[key] = values
            if 'evidence' in custom_mappings:
                for key, values in custom_mappings['evidence'].items():
                    if key in self.evidence_mappings:
                        self.evidence_mappings[key] = values + self.evidence_mappings[key]
                    else:
                        self.evidence_mappings[key] = values
    
    def map_columns(self, df_columns: List[str], mapping_type: str = 'controls') -> Dict[str, str]:
        """Map actual column names to canonical names."""
        mappings = self.control_mappings if mapping_type == 'controls' else self.evidence_mappings
        
        # Clean column names first
        df_columns_clean = [clean_text(str(c)) or str(c) for c in df_columns]
        df_columns_lower = {c.lower().strip(): orig for c, orig in zip(df_columns_clean, df_columns)}
        
        result = {}
        
        for canonical, alternatives in mappings.items():
            for alt in alternatives:
                alt_lower = alt.lower()
                if alt_lower in df_columns_lower:
                    result[canonical] = df_columns_lower[alt_lower]
                    break
            
            # If not found, try fuzzy matching
            if canonical not in result:
                matched = fuzzy_match_column(df_columns, alternatives[0])
                if matched:
                    result[canonical] = matched
        
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def detect_header_row(df_preview: pd.DataFrame, markers: List[str], max_rows: int = 15) -> int:
    """Detect the header row by looking for marker columns."""
    markers_lower = [m.lower() for m in markers]
    
    for i in range(min(max_rows, len(df_preview))):
        row = df_preview.iloc[i].astype(str).str.lower().str.strip().tolist()
        # Clean row values
        row = [clean_text(str(cell)) or '' for cell in row]
        row_lower = [r.lower() for r in row]
        
        matches = sum(1 for m in markers_lower if any(m in str(cell) for cell in row_lower))
        if matches >= max(2, len(markers) - 2):
            return i
    
    return 0  # Default to first row


# =============================================================================
# SOURCE ADAPTERS
# =============================================================================

class SourceAdapter(ABC):
    """Base class for source adapters."""
    
    @abstractmethod
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load data from source.
        
        Returns:
            controls_df: DataFrame with canonical columns
            evidence_df: DataFrame with canonical columns
        """
        raise NotImplementedError
    
    @abstractmethod
    def validate(self) -> Dict[str, Any]:
        """
        Validate the source and return a report.
        
        Returns:
            Dictionary with validation results
        """
        raise NotImplementedError


class ExcelAdapter(SourceAdapter):
    """Adapter for Excel files (.xls, .xlsx)."""
    
    def __init__(
        self,
        path: str,
        sheet_main: str = None,
        sheet_guidance: str = None,
        sheet_evidence: str = None,
        column_mappings: Dict = None,
        auto_detect_sheets: bool = True
    ):
        self.path = path
        self.sheet_main = sheet_main
        self.sheet_guidance = sheet_guidance
        self.sheet_evidence = sheet_evidence
        self.column_mapper = ColumnMapper(column_mappings)
        self.auto_detect_sheets = auto_detect_sheets
        self._validation_report = None
    
    def _auto_detect_sheets(self, xls: pd.ExcelFile) -> Dict[str, str]:
        """Auto-detect sheet purposes based on content."""
        sheet_purposes = {}
        
        main_markers = ['ccf id', 'control id', 'control name', 'control domain', 'scf #', 'scf control']
        guidance_markers = ['implementation guidance', 'testing procedure', 'control guidance']
        evidence_markers = ['evidence title', 'reference #', 'evidence domain', 'erl']
        
        for sheet_name in xls.sheet_names:
            try:
                preview = pd.read_excel(xls, sheet_name=sheet_name, nrows=5, header=None)
                all_text = ' '.join(preview.astype(str).values.flatten()).lower()
                # Clean special characters
                all_text = clean_text(all_text) or all_text
                
                main_score = sum(1 for m in main_markers if m in all_text)
                guidance_score = sum(1 for m in guidance_markers if m in all_text)
                evidence_score = sum(1 for m in evidence_markers if m in all_text)
                
                if main_score >= 2 and 'main' not in sheet_purposes:
                    sheet_purposes['main'] = sheet_name
                elif guidance_score >= 2 and 'guidance' not in sheet_purposes:
                    sheet_purposes['guidance'] = sheet_name
                elif evidence_score >= 2 and 'evidence' not in sheet_purposes:
                    sheet_purposes['evidence'] = sheet_name
            except Exception as e:
                logger.debug(f"Could not analyze sheet {sheet_name}: {e}")
        
        return sheet_purposes
    
    def validate(self) -> Dict[str, Any]:
        """Validate the Excel file."""
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not os.path.exists(self.path):
            report['valid'] = False
            report['errors'].append(f"File not found: {self.path}")
            return report
        
        try:
            xls = pd.ExcelFile(self.path)
            report['info'].append(f"Found {len(xls.sheet_names)} sheets: {', '.join(xls.sheet_names)}")
            
            # Auto-detect sheets if needed
            if self.auto_detect_sheets:
                detected = self._auto_detect_sheets(xls)
                report['info'].append(f"Auto-detected sheets: {detected}")
                
                if not self.sheet_main and 'main' in detected:
                    self.sheet_main = detected['main']
                if not self.sheet_guidance and 'guidance' in detected:
                    self.sheet_guidance = detected['guidance']
                if not self.sheet_evidence and 'evidence' in detected:
                    self.sheet_evidence = detected['evidence']
            
            if not self.sheet_main:
                report['valid'] = False
                report['errors'].append("Could not determine main controls sheet")
            else:
                report['info'].append(f"Using main sheet: {self.sheet_main}")
            
            if not self.sheet_guidance:
                report['warnings'].append("No guidance sheet detected - controls may lack implementation details")
            
            if not self.sheet_evidence:
                report['warnings'].append("No evidence sheet detected - evidence linking will be limited")
            
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Failed to read Excel file: {str(e)}")
        
        self._validation_report = report
        return report
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from Excel file."""
        if not self._validation_report:
            self.validate()
        
        if not self._validation_report['valid']:
            raise ValueError(f"Validation failed: {self._validation_report['errors']}")
        
        xls = pd.ExcelFile(self.path)
        
        # Load evidence
        evidence_df = pd.DataFrame(columns=['ref_id', 'title', 'domain'])
        if self.sheet_evidence and self.sheet_evidence in xls.sheet_names:
            try:
                df_ev = pd.read_excel(xls, sheet_name=self.sheet_evidence)
                df_ev = clean_dataframe(df_ev)
                
                col_map = self.column_mapper.map_columns(df_ev.columns.tolist(), 'evidence')
                
                if 'ref_id' in col_map:
                    evidence_df = pd.DataFrame({
                        'ref_id': df_ev[col_map['ref_id']].apply(clean_text),
                        'title': df_ev[col_map.get('title', col_map['ref_id'])].apply(clean_text) if 'title' in col_map else None,
                        'domain': df_ev[col_map.get('domain')].apply(clean_text) if 'domain' in col_map else None
                    })
                    evidence_df = evidence_df[evidence_df['ref_id'].notna()]
                    logger.info(f"Loaded {len(evidence_df)} evidence items")
            except Exception as e:
                logger.warning(f"Error loading evidence sheet: {e}")
        
        # Load guidance
        guidance_lookup = {}
        if self.sheet_guidance and self.sheet_guidance in xls.sheet_names:
            try:
                df_guide = pd.read_excel(xls, sheet_name=self.sheet_guidance)
                df_guide = clean_dataframe(df_guide)
                
                col_map = self.column_mapper.map_columns(df_guide.columns.tolist(), 'controls')
                
                if 'ccf_id' in col_map:
                    for _, row in df_guide.iterrows():
                        ccf_id = clean_text(row.get(col_map['ccf_id']))
                        if ccf_id:
                            guidance_lookup[ccf_id] = {
                                'type': clean_text(row.get(col_map.get('type', ''))) if 'type' in col_map else None,
                                'theme': clean_text(row.get(col_map.get('theme', ''))) if 'theme' in col_map else None,
                                'guidance': clean_text(row.get(col_map.get('guidance', ''))) if 'guidance' in col_map else None,
                                'testing': clean_text(row.get(col_map.get('testing', ''))) if 'testing' in col_map else None,
                                'artifacts': clean_text(row.get(col_map.get('artifacts', ''))) if 'artifacts' in col_map else None
                            }
                    logger.info(f"Loaded guidance for {len(guidance_lookup)} controls")
            except Exception as e:
                logger.warning(f"Error loading guidance sheet: {e}")
        
        # Load main controls
        # First, detect header row
        preview = pd.read_excel(xls, sheet_name=self.sheet_main, header=None, nrows=15)
        header_row = detect_header_row(preview, ['ccf id', 'control id', 'control name', 'control domain', 'scf #'])
        
        df_main = pd.read_excel(xls, sheet_name=self.sheet_main, header=header_row)
        df_main = clean_dataframe(df_main)
        
        col_map = self.column_mapper.map_columns(df_main.columns.tolist(), 'controls')
        logger.info(f"Column mapping: {col_map}")
        
        if 'ccf_id' not in col_map:
            raise ValueError("Could not find CCF ID / Control ID column in main sheet")
        
        # Extract mapping columns (framework references)
        mapping_cols = [c for c in df_main.columns if 'ref' in c.lower() and c not in col_map.values()]
        
        controls_rows = []
        for _, row in df_main.iterrows():
            ccf_id = clean_text(row.get(col_map['ccf_id']))
            if not ccf_id:
                continue
            
            # Build framework mappings
            mappings = {}
            for col in mapping_cols:
                v = row.get(col)
                if pd.notna(v) and str(v).strip():
                    key = re.sub(r'\s*ref\s*#?\s*', '', str(col), flags=re.IGNORECASE).strip().replace(' ', '_')
                    if key:
                        mappings[key] = split_list_string(str(v))
            
            # Merge with guidance
            guide = guidance_lookup.get(ccf_id, {})
            
            controls_rows.append({
                'ccf_id': ccf_id,
                'domain': clean_text(row.get(col_map.get('domain', ''))) if 'domain' in col_map else None,
                'title': clean_text(row.get(col_map.get('title', ''))) if 'title' in col_map else None,
                'description': clean_text(row.get(col_map.get('description', ''))) if 'description' in col_map else None,
                'type': guide.get('type') or (clean_text(row.get(col_map.get('type', ''))) if 'type' in col_map else None),
                'theme': guide.get('theme') or (clean_text(row.get(col_map.get('theme', ''))) if 'theme' in col_map else None),
                'guidance': guide.get('guidance') or (clean_text(row.get(col_map.get('guidance', ''))) if 'guidance' in col_map else None),
                'testing': guide.get('testing') or (clean_text(row.get(col_map.get('testing', ''))) if 'testing' in col_map else None),
                'mappings': mappings,
                'artifacts': guide.get('artifacts') or (clean_text(row.get(col_map.get('artifacts', ''))) if 'artifacts' in col_map else None)
            })
        
        controls_df = pd.DataFrame(controls_rows)
        logger.info(f"Loaded {len(controls_df)} controls")
        
        return controls_df, evidence_df


class JSONAdapter(SourceAdapter):
    """Adapter for JSON files."""
    
    def __init__(self, path: str, column_mappings: Dict = None):
        self.path = path
        self.column_mapper = ColumnMapper(column_mappings)
        self._validation_report = None
    
    def validate(self) -> Dict[str, Any]:
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not os.path.exists(self.path):
            report['valid'] = False
            report['errors'].append(f"File not found: {self.path}")
            return report
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                report['info'].append(f"JSON is a list with {len(data)} items (assuming controls)")
            elif isinstance(data, dict):
                if 'controls' in data:
                    report['info'].append(f"Found 'controls' key with {len(data['controls'])} items")
                else:
                    report['warnings'].append("No 'controls' key found - will attempt to parse root object")
                
                if 'evidence' in data:
                    report['info'].append(f"Found 'evidence' key with {len(data['evidence'])} items")
            else:
                report['valid'] = False
                report['errors'].append("JSON root must be a list or object")
        
        except json.JSONDecodeError as e:
            report['valid'] = False
            report['errors'].append(f"Invalid JSON: {str(e)}")
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Error reading file: {str(e)}")
        
        self._validation_report = report
        return report
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if not self._validation_report:
            self.validate()
        
        if not self._validation_report['valid']:
            raise ValueError(f"Validation failed: {self._validation_report['errors']}")
        
        with open(self.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            controls_data = data
            evidence_data = []
        else:
            controls_data = data.get('controls', [])
            evidence_data = data.get('evidence', [])
        
        # Normalize controls
        controls_df = pd.json_normalize(controls_data) if controls_data else pd.DataFrame()
        
        if not controls_df.empty:
            controls_df = clean_dataframe(controls_df)
            col_map = self.column_mapper.map_columns(controls_df.columns.tolist(), 'controls')
            
            normalized = pd.DataFrame()
            for canonical, actual in col_map.items():
                if actual in controls_df.columns:
                    normalized[canonical] = controls_df[actual].apply(clean_text)
            
            # Ensure required columns exist
            for col in ['ccf_id', 'domain', 'title', 'description', 'type', 'theme', 'guidance', 'testing', 'mappings', 'artifacts']:
                if col not in normalized.columns:
                    normalized[col] = None
            
            controls_df = normalized[normalized['ccf_id'].notna()]
        
        # Normalize evidence
        evidence_df = pd.json_normalize(evidence_data) if evidence_data else pd.DataFrame()
        
        if not evidence_df.empty:
            evidence_df = clean_dataframe(evidence_df)
            col_map = self.column_mapper.map_columns(evidence_df.columns.tolist(), 'evidence')
            
            normalized = pd.DataFrame()
            for canonical, actual in col_map.items():
                if actual in evidence_df.columns:
                    normalized[canonical] = evidence_df[actual].apply(clean_text)
            
            for col in ['ref_id', 'title', 'domain']:
                if col not in normalized.columns:
                    normalized[col] = None
            
            evidence_df = normalized[normalized['ref_id'].notna()]
        else:
            evidence_df = pd.DataFrame(columns=['ref_id', 'title', 'domain'])
        
        logger.info(f"Loaded {len(controls_df)} controls, {len(evidence_df)} evidence items from JSON")
        return controls_df, evidence_df


class CSVFolderAdapter(SourceAdapter):
    """Adapter for CSV folder structure."""
    
    def __init__(self, folder: str, column_mappings: Dict = None):
        self.folder = folder
        self.column_mapper = ColumnMapper(column_mappings)
        self._validation_report = None
        self._controls_file = None
        self._guidance_file = None
        self._evidence_file = None
    
    def validate(self) -> Dict[str, Any]:
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not os.path.isdir(self.folder):
            report['valid'] = False
            report['errors'].append(f"Folder not found: {self.folder}")
            return report
        
        csv_files = [f for f in os.listdir(self.folder) if f.lower().endswith('.csv')]
        report['info'].append(f"Found CSV files: {', '.join(csv_files)}")
        
        # Look for controls file
        controls_file = None
        for pattern in ['controls.csv', 'control.csv', 'main.csv', 'ccf.csv']:
            if pattern in [f.lower() for f in csv_files]:
                idx = [f.lower() for f in csv_files].index(pattern)
                controls_file = csv_files[idx]
                break
        
        if not controls_file:
            for f in csv_files:
                try:
                    preview = pd.read_csv(os.path.join(self.folder, f), nrows=5)
                    cols_lower = [c.lower() for c in preview.columns]
                    if any('control' in c or 'ccf' in c for c in cols_lower):
                        controls_file = f
                        break
                except:
                    pass
        
        if controls_file:
            report['info'].append(f"Using controls file: {controls_file}")
            self._controls_file = controls_file
        else:
            report['valid'] = False
            report['errors'].append("Could not find controls CSV file")
        
        # Look for guidance file
        for pattern in ['guidance.csv', 'guide.csv', 'implementation.csv']:
            if pattern in [f.lower() for f in csv_files]:
                idx = [f.lower() for f in csv_files].index(pattern)
                self._guidance_file = csv_files[idx]
                report['info'].append(f"Using guidance file: {csv_files[idx]}")
                break
        else:
            self._guidance_file = None
            report['warnings'].append("No guidance CSV found")
        
        # Look for evidence file
        for pattern in ['evidence.csv', 'artifacts.csv', 'audit.csv']:
            if pattern in [f.lower() for f in csv_files]:
                idx = [f.lower() for f in csv_files].index(pattern)
                self._evidence_file = csv_files[idx]
                report['info'].append(f"Using evidence file: {csv_files[idx]}")
                break
        else:
            self._evidence_file = None
            report['warnings'].append("No evidence CSV found")
        
        self._validation_report = report
        return report
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from CSV folder."""
        if not self._validation_report:
            self.validate()
        
        if not self._validation_report['valid']:
            raise ValueError(f"Validation failed: {self._validation_report['errors']}")
        
        # Load evidence
        evidence_df = pd.DataFrame(columns=['ref_id', 'title', 'domain'])
        if self._evidence_file:
            try:
                df_ev = pd.read_csv(os.path.join(self.folder, self._evidence_file))
                df_ev = clean_dataframe(df_ev)
                
                col_map = self.column_mapper.map_columns(df_ev.columns.tolist(), 'evidence')
                
                if 'ref_id' in col_map:
                    evidence_df = pd.DataFrame({
                        'ref_id': df_ev[col_map['ref_id']].apply(clean_text),
                        'title': df_ev[col_map.get('title', col_map['ref_id'])].apply(clean_text) if 'title' in col_map else None,
                        'domain': df_ev[col_map.get('domain')].apply(clean_text) if 'domain' in col_map else None
                    })
                    evidence_df = evidence_df[evidence_df['ref_id'].notna()]
                    logger.info(f"Loaded {len(evidence_df)} evidence items from CSV")
            except Exception as e:
                logger.warning(f"Error loading evidence CSV: {e}")
        
        # Load guidance
        guidance_lookup = {}
        if self._guidance_file:
            try:
                df_guide = pd.read_csv(os.path.join(self.folder, self._guidance_file))
                df_guide = clean_dataframe(df_guide)
                
                col_map = self.column_mapper.map_columns(df_guide.columns.tolist(), 'controls')
                
                if 'ccf_id' in col_map:
                    for _, row in df_guide.iterrows():
                        ccf_id = clean_text(row.get(col_map['ccf_id']))
                        if ccf_id:
                            guidance_lookup[ccf_id] = {
                                'type': clean_text(row.get(col_map.get('type', ''))) if 'type' in col_map else None,
                                'theme': clean_text(row.get(col_map.get('theme', ''))) if 'theme' in col_map else None,
                                'guidance': clean_text(row.get(col_map.get('guidance', ''))) if 'guidance' in col_map else None,
                                'testing': clean_text(row.get(col_map.get('testing', ''))) if 'testing' in col_map else None,
                                'artifacts': clean_text(row.get(col_map.get('artifacts', ''))) if 'artifacts' in col_map else None
                            }
                    logger.info(f"Loaded guidance for {len(guidance_lookup)} controls from CSV")
            except Exception as e:
                logger.warning(f"Error loading guidance CSV: {e}")
        
        # Load main controls
        df_main = pd.read_csv(os.path.join(self.folder, self._controls_file))
        df_main = clean_dataframe(df_main)
        
        col_map = self.column_mapper.map_columns(df_main.columns.tolist(), 'controls')
        logger.info(f"Controls column mapping: {col_map}")
        
        if 'ccf_id' not in col_map:
            raise ValueError("Could not find CCF ID / Control ID column in controls CSV")
        
        # Extract mapping columns (framework references)
        mapping_cols = [c for c in df_main.columns if 'ref' in c.lower() and c not in col_map.values()]
        
        controls_rows = []
        for _, row in df_main.iterrows():
            ccf_id = clean_text(row.get(col_map['ccf_id']))
            if not ccf_id:
                continue
            
            # Build framework mappings
            mappings = {}
            for col in mapping_cols:
                v = row.get(col)
                if pd.notna(v) and str(v).strip():
                    key = re.sub(r'\s*ref\s*#?\s*', '', str(col), flags=re.IGNORECASE).strip().replace(' ', '_')
                    if key:
                        mappings[key] = split_list_string(str(v))
            
            # Merge with guidance data
            guide = guidance_lookup.get(ccf_id, {})
            
            controls_rows.append({
                'ccf_id': ccf_id,
                'domain': clean_text(row.get(col_map.get('domain', ''))) if 'domain' in col_map else None,
                'title': clean_text(row.get(col_map.get('title', ''))) if 'title' in col_map else None,
                'description': clean_text(row.get(col_map.get('description', ''))) if 'description' in col_map else None,
                'type': guide.get('type') or (clean_text(row.get(col_map.get('type', ''))) if 'type' in col_map else None),
                'theme': guide.get('theme') or (clean_text(row.get(col_map.get('theme', ''))) if 'theme' in col_map else None),
                'guidance': guide.get('guidance') or (clean_text(row.get(col_map.get('guidance', ''))) if 'guidance' in col_map else None),
                'testing': guide.get('testing') or (clean_text(row.get(col_map.get('testing', ''))) if 'testing' in col_map else None),
                'mappings': mappings,
                'artifacts': guide.get('artifacts') or (clean_text(row.get(col_map.get('artifacts', ''))) if 'artifacts' in col_map else None)
            })
        
        controls_df = pd.DataFrame(controls_rows)
        logger.info(f"Loaded {len(controls_df)} controls from CSV folder")
        
        return controls_df, evidence_df


class XMLAdapter(SourceAdapter):
    """Adapter for XML files."""
    
    def __init__(self, path: str, column_mappings: Dict = None):
        self.path = path
        self.column_mapper = ColumnMapper(column_mappings)
        self._validation_report = None
    
    def validate(self) -> Dict[str, Any]:
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not os.path.exists(self.path):
            report['valid'] = False
            report['errors'].append(f"File not found: {self.path}")
            return report
        
        try:
            tree = ET.parse(self.path)
            root = tree.getroot()
            
            report['info'].append(f"Root element: {root.tag}")
            report['info'].append(f"Child elements: {len(list(root))}")
            
            # Look for controls element
            controls_elem = root.find('.//controls') or root.find('.//Controls')
            if controls_elem is not None:
                report['info'].append(f"Found controls element with {len(list(controls_elem))} children")
            else:
                first_child = list(root)[0] if list(root) else None
                if first_child is not None:
                    report['info'].append(f"Assuming root children are controls (first child tag: {first_child.tag})")
            
            # Look for evidence element
            evidence_elem = root.find('.//evidence') or root.find('.//Evidence')
            if evidence_elem is not None:
                report['info'].append(f"Found evidence element with {len(list(evidence_elem))} children")
            else:
                report['warnings'].append("No evidence element found")
        
        except ET.ParseError as e:
            report['valid'] = False
            report['errors'].append(f"Invalid XML: {str(e)}")
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Error reading file: {str(e)}")
        
        self._validation_report = report
        return report
    
    def _element_to_dict(self, elem) -> Dict:
        """Convert XML element to dictionary."""
        result = {}
        
        # Add attributes
        result.update(elem.attrib)
        
        # Add child elements
        for child in elem:
            if len(child) == 0:
                result[child.tag] = clean_text(child.text)
            else:
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(self._element_to_dict(child))
                else:
                    result[child.tag] = self._element_to_dict(child)
        
        if elem.text and elem.text.strip():
            result['_text'] = clean_text(elem.text)
        
        return result
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from XML file."""
        if not self._validation_report:
            self.validate()
        
        if not self._validation_report['valid']:
            raise ValueError(f"Validation failed: {self._validation_report['errors']}")
        
        tree = ET.parse(self.path)
        root = tree.getroot()
        
        # Find controls
        controls_elem = root.find('.//controls') or root.find('.//Controls')
        if controls_elem is not None:
            control_items = list(controls_elem)
        else:
            control_items = list(root)
        
        controls_data = [self._element_to_dict(item) for item in control_items]
        
        # Find evidence
        evidence_elem = root.find('.//evidence') or root.find('.//Evidence')
        if evidence_elem is not None:
            evidence_items = list(evidence_elem)
            evidence_data = [self._element_to_dict(item) for item in evidence_items]
        else:
            evidence_data = []
        
        # Convert to DataFrames
        controls_df = pd.json_normalize(controls_data) if controls_data else pd.DataFrame()
        evidence_df = pd.json_normalize(evidence_data) if evidence_data else pd.DataFrame(columns=['ref_id', 'title', 'domain'])
        
        # Clean DataFrames
        controls_df = clean_dataframe(controls_df)
        evidence_df = clean_dataframe(evidence_df)
        
        # Map columns for controls
        if not controls_df.empty:
            col_map = self.column_mapper.map_columns(controls_df.columns.tolist(), 'controls')
            
            normalized = pd.DataFrame()
            for canonical in ['ccf_id', 'domain', 'title', 'description', 'type', 'theme', 'guidance', 'testing', 'artifacts']:
                if canonical in col_map and col_map[canonical] in controls_df.columns:
                    normalized[canonical] = controls_df[col_map[canonical]].apply(clean_text)
                else:
                    normalized[canonical] = None
            
            # Handle mappings
            mapping_cols = [c for c in controls_df.columns if 'ref' in c.lower() or 'mapping' in c.lower()]
            if mapping_cols:
                def build_mappings(row):
                    m = {}
                    for col in mapping_cols:
                        v = row.get(col)
                        if pd.notna(v) and str(v).strip():
                            key = re.sub(r'\s*ref\s*#?\s*', '', str(col), flags=re.IGNORECASE).strip().replace(' ', '_')
                            if key:
                                m[key] = split_list_string(str(v))
                    return m
                normalized['mappings'] = controls_df.apply(build_mappings, axis=1)
            else:
                normalized['mappings'] = None
            
            controls_df = normalized[normalized['ccf_id'].notna()]
        
        # Map columns for evidence
        if not evidence_df.empty:
            col_map = self.column_mapper.map_columns(evidence_df.columns.tolist(), 'evidence')
            
            normalized = pd.DataFrame()
            for canonical in ['ref_id', 'title', 'domain']:
                if canonical in col_map and col_map[canonical] in evidence_df.columns:
                    normalized[canonical] = evidence_df[col_map[canonical]].apply(clean_text)
                else:
                    normalized[canonical] = None
            
            evidence_df = normalized[normalized['ref_id'].notna()]
        
        logger.info(f"Loaded {len(controls_df)} controls, {len(evidence_df)} evidence items from XML")
        return controls_df, evidence_df


class ZIPAdapter(SourceAdapter):
    """Adapter for ZIP archives containing data files."""
    
    def __init__(self, path: str, column_mappings: Dict = None):
        self.path = path
        self.column_mapper = ColumnMapper(column_mappings)
        self._validation_report = None
        self._inner_adapter = None
        self._temp_dir = None
        self._primary_file = None
        self._adapter_type = None
    
    def _is_safe_path(self, base_path: str, target_path: str) -> bool:
        """
        Check if a path is safe (doesn't escape the base directory).
        
        This prevents ZIP slip attacks where malicious archives contain
        paths like "../../../etc/passwd" to write outside the target directory.
        """
        # Resolve to absolute paths
        abs_base = os.path.abspath(base_path)
        abs_target = os.path.abspath(os.path.join(base_path, target_path))
        
        # Check that the target is within the base
        return abs_target.startswith(abs_base + os.sep) or abs_target == abs_base
    
    def _safe_extract(self, zf: zipfile.ZipFile, target_dir: str) -> None:
        """
        Safely extract a ZIP file, preventing ZIP slip attacks.
        
        Args:
            zf: The ZipFile object to extract from.
            target_dir: The directory to extract to.
            
        Raises:
            ValueError: If a malicious path is detected.
        """
        for member in zf.namelist():
            # Skip directories
            if member.endswith('/'):
                continue
            
            # Check for path traversal attempts
            if not self._is_safe_path(target_dir, member):
                raise ValueError(f"ZIP contains potentially malicious path: {member}")
            
            # Extract the file safely
            target_path = os.path.join(target_dir, member)
            target_parent = os.path.dirname(target_path)
            
            # Create parent directories if needed
            if target_parent and not os.path.exists(target_parent):
                os.makedirs(target_parent, exist_ok=True)
            
            # Extract the file
            with zf.open(member) as source, open(target_path, 'wb') as target:
                target.write(source.read())
    
    def validate(self) -> Dict[str, Any]:
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not os.path.exists(self.path):
            report['valid'] = False
            report['errors'].append(f"File not found: {self.path}")
            return report
        
        try:
            with zipfile.ZipFile(self.path, 'r') as zf:
                file_list = zf.namelist()
                report['info'].append(f"ZIP contains {len(file_list)} files")
                
                # Security check: validate all paths before extraction
                for member in file_list:
                    # Check for path traversal attempts
                    if '..' in member or member.startswith('/'):
                        report['valid'] = False
                        report['errors'].append(f"ZIP contains potentially unsafe path: {member}")
                        return report
                
                # Categorize files
                excel_files = [f for f in file_list if f.lower().endswith(('.xls', '.xlsx')) and not f.startswith('__MACOSX')]
                json_files = [f for f in file_list if f.lower().endswith('.json') and not f.startswith('__MACOSX')]
                csv_files = [f for f in file_list if f.lower().endswith('.csv') and not f.startswith('__MACOSX')]
                xml_files = [f for f in file_list if f.lower().endswith('.xml') and not f.startswith('__MACOSX')]
                
                report['info'].append(f"Excel: {len(excel_files)}, JSON: {len(json_files)}, CSV: {len(csv_files)}, XML: {len(xml_files)}")
                
                # Determine which adapter to use
                if excel_files:
                    report['info'].append(f"Will use Excel adapter for: {excel_files[0]}")
                    self._primary_file = excel_files[0]
                    self._adapter_type = 'excel'
                elif json_files:
                    report['info'].append(f"Will use JSON adapter for: {json_files[0]}")
                    self._primary_file = json_files[0]
                    self._adapter_type = 'json'
                elif csv_files:
                    report['info'].append("Will use CSV folder adapter for extracted CSVs")
                    self._adapter_type = 'csv'
                elif xml_files:
                    report['info'].append(f"Will use XML adapter for: {xml_files[0]}")
                    self._primary_file = xml_files[0]
                    self._adapter_type = 'xml'
                else:
                    report['valid'] = False
                    report['errors'].append("No supported data files found in ZIP")
        
        except zipfile.BadZipFile:
            report['valid'] = False
            report['errors'].append("Invalid ZIP file")
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Error reading ZIP: {str(e)}")
        
        self._validation_report = report
        return report
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from ZIP archive."""
        if not self._validation_report:
            self.validate()
        
        if not self._validation_report['valid']:
            raise ValueError(f"Validation failed: {self._validation_report['errors']}")
        
        # Extract to temp directory
        self._temp_dir = tempfile.mkdtemp(prefix='grc_zip_')
        
        try:
            with zipfile.ZipFile(self.path, 'r') as zf:
                # Use safe extraction to prevent ZIP slip attacks
                self._safe_extract(zf, self._temp_dir)
            
            # Create appropriate adapter
            if self._adapter_type == 'excel':
                extracted_path = os.path.join(self._temp_dir, self._primary_file)
                self._inner_adapter = ExcelAdapter(extracted_path, column_mappings=self.column_mapper.control_mappings)
            elif self._adapter_type == 'json':
                extracted_path = os.path.join(self._temp_dir, self._primary_file)
                self._inner_adapter = JSONAdapter(extracted_path, column_mappings=self.column_mapper.control_mappings)
            elif self._adapter_type == 'csv':
                self._inner_adapter = CSVFolderAdapter(self._temp_dir, column_mappings=self.column_mapper.control_mappings)
            elif self._adapter_type == 'xml':
                extracted_path = os.path.join(self._temp_dir, self._primary_file)
                self._inner_adapter = XMLAdapter(extracted_path, column_mappings=self.column_mapper.control_mappings)
            
            return self._inner_adapter.load()
        
        finally:
            # Cleanup temp directory
            import shutil
            if self._temp_dir and os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_adapter(
    source: str,
    format_hint: str = 'auto',
    sheet_main: str = None,
    sheet_guidance: str = None,
    sheet_evidence: str = None,
    column_mappings: Dict = None
) -> SourceAdapter:
    """
    Factory function to get the appropriate adapter for a source.
    
    Args:
        source: Path to file or folder
        format_hint: 'auto', 'excel', 'json', 'csv', 'xml', 'zip'
        sheet_main: For Excel, the main sheet name
        sheet_guidance: For Excel, the guidance sheet name
        sheet_evidence: For Excel, the evidence sheet name
        column_mappings: Custom column name mappings
    
    Returns:
        Appropriate SourceAdapter instance
    """
    if format_hint == 'auto':
        if os.path.isdir(source):
            return CSVFolderAdapter(source, column_mappings=column_mappings)
        
        ext = os.path.splitext(source)[1].lower()
        
        if ext in ('.xls', '.xlsx'):
            return ExcelAdapter(
                source,
                sheet_main=sheet_main,
                sheet_guidance=sheet_guidance,
                sheet_evidence=sheet_evidence,
                column_mappings=column_mappings
            )
        elif ext == '.json':
            return JSONAdapter(source, column_mappings=column_mappings)
        elif ext == '.xml':
            return XMLAdapter(source, column_mappings=column_mappings)
        elif ext == '.zip':
            return ZIPAdapter(source, column_mappings=column_mappings)
        elif ext == '.csv':
            folder = os.path.dirname(source) or '.'
            return CSVFolderAdapter(folder, column_mappings=column_mappings)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    elif format_hint == 'excel':
        return ExcelAdapter(
            source,
            sheet_main=sheet_main,
            sheet_guidance=sheet_guidance,
            sheet_evidence=sheet_evidence,
            column_mappings=column_mappings
        )
    elif format_hint == 'json':
        return JSONAdapter(source, column_mappings=column_mappings)
    elif format_hint == 'csv':
        if os.path.isdir(source):
            return CSVFolderAdapter(source, column_mappings=column_mappings)
        else:
            folder = os.path.dirname(source) or '.'
            return CSVFolderAdapter(folder, column_mappings=column_mappings)
    elif format_hint == 'xml':
        return XMLAdapter(source, column_mappings=column_mappings)
    elif format_hint == 'zip':
        return ZIPAdapter(source, column_mappings=column_mappings)
    else:
        raise ValueError(f"Unknown format hint: {format_hint}")