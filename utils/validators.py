import pandas as pd
from typing import Dict, List, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates control and evidence data before insertion."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def reset(self):
        """Reset validation state."""
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_controls(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate controls DataFrame.
        
        Returns:
            Dictionary with validation results
        """
        self.reset()
        
        if df is None or df.empty:
            self.errors.append("Controls DataFrame is empty")
            return self._get_report()
        
        self.info.append(f"Validating {len(df)} controls")
        
        # Check required columns
        required = ['ccf_id']
        for col in required:
            if col not in df.columns:
                self.errors.append(f"Missing required column: {col}")
        
        if self.errors:
            return self._get_report()
        
        # Check for empty ccf_ids
        empty_ids = df['ccf_id'].isna().sum()
        if empty_ids > 0:
            self.warnings.append(f"{empty_ids} rows have empty CCF IDs (will be skipped)")
        
        # Check for duplicate ccf_ids
        duplicates = df[df['ccf_id'].notna()]['ccf_id'].duplicated()
        dup_count = duplicates.sum()
        if dup_count > 0:
            dup_ids = df[df['ccf_id'].notna()][duplicates]['ccf_id'].unique().tolist()[:10]
            self.warnings.append(f"{dup_count} duplicate CCF IDs found (first few: {dup_ids})")
        
        # Check for missing important fields
        important = ['title', 'description', 'domain']
        for col in important:
            if col in df.columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    pct = (missing / len(df)) * 100
                    if pct > 50:
                        self.warnings.append(f"{missing} ({pct:.1f}%) controls missing {col}")
                    else:
                        self.info.append(f"{missing} ({pct:.1f}%) controls missing {col}")
        
        # Check guidance and testing
        for col in ['guidance', 'testing']:
            if col in df.columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    pct = (missing / len(df)) * 100
                    self.info.append(f"{missing} ({pct:.1f}%) controls missing {col}")
        
        # Validate CCF ID format (if it should follow a pattern)
        if 'ccf_id' in df.columns:
            valid_df = df[df['ccf_id'].notna()]
            # Check for reasonable ID format (letters, numbers, hyphens, underscores)
            invalid_ids = valid_df[~valid_df['ccf_id'].astype(str).str.match(r'^[\w\-\.]+$', na=False)]
            if len(invalid_ids) > 0:
                self.warnings.append(f"{len(invalid_ids)} CCF IDs contain unusual characters")
        
        # Check mappings format
        if 'mappings' in df.columns:
            def check_mapping(m):
                if m is None or (isinstance(m, float) and pd.isna(m)):
                    return True
                if isinstance(m, dict):
                    return True
                if isinstance(m, str):
                    try:
                        import json
                        json.loads(m)
                        return True
                    except:
                        return False
                return False
            
            invalid_mappings = df[~df['mappings'].apply(check_mapping)]
            if len(invalid_mappings) > 0:
                self.warnings.append(f"{len(invalid_mappings)} controls have invalid mapping format")
        
        return self._get_report()
    
    def validate_evidence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate evidence DataFrame.
        
        Returns:
            Dictionary with validation results
        """
        self.reset()
        
        if df is None or df.empty:
            self.info.append("Evidence DataFrame is empty (this may be intentional)")
            return self._get_report()
        
        self.info.append(f"Validating {len(df)} evidence items")
        
        # Check required columns
        required = ['ref_id']
        for col in required:
            if col not in df.columns:
                self.errors.append(f"Missing required column: {col}")
        
        if self.errors:
            return self._get_report()
        
        # Check for empty ref_ids
        empty_ids = df['ref_id'].isna().sum()
        if empty_ids > 0:
            self.warnings.append(f"{empty_ids} evidence items have empty ref IDs (will be skipped)")
        
        # Check for duplicates
        duplicates = df[df['ref_id'].notna()]['ref_id'].duplicated()
        dup_count = duplicates.sum()
        if dup_count > 0:
            dup_ids = df[df['ref_id'].notna()][duplicates]['ref_id'].unique().tolist()[:10]
            self.warnings.append(f"{dup_count} duplicate evidence ref IDs found (first few: {dup_ids})")
        
        # Check for missing title
        if 'title' in df.columns:
            missing = df['title'].isna().sum()
            if missing > 0:
                pct = (missing / len(df)) * 100
                self.info.append(f"{missing} ({pct:.1f}%) evidence items missing title")
        
        return self._get_report()
    
    def validate_artifact_references(
        self,
        controls_df: pd.DataFrame,
        evidence_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate that artifact references in controls exist in evidence.
        
        Returns:
            Dictionary with validation results
        """
        self.reset()
        
        if controls_df is None or controls_df.empty:
            self.info.append("No controls to validate artifact references")
            return self._get_report()
        
        if evidence_df is None or evidence_df.empty:
            if 'artifacts' in controls_df.columns:
                has_artifacts = controls_df['artifacts'].notna().sum()
                if has_artifacts > 0:
                    self.warnings.append(f"{has_artifacts} controls have artifact references but no evidence data provided")
            return self._get_report()
        
        # Build evidence lookup
        evidence_refs = set(evidence_df['ref_id'].dropna().astype(str).str.strip().tolist())
        
        # Check artifact references
        if 'artifacts' not in controls_df.columns:
            self.info.append("No artifacts column in controls")
            return self._get_report()
        
        missing_refs = set()
        controls_with_missing = 0
        
        for _, row in controls_df.iterrows():
            artifacts = row.get('artifacts')
            if not artifacts or (isinstance(artifacts, float) and pd.isna(artifacts)):
                continue
            
            refs = re.split(r'[\n\r,;|]+', str(artifacts))
            refs = [r.strip() for r in refs if r.strip()]
            
            row_missing = [r for r in refs if r not in evidence_refs]
            if row_missing:
                missing_refs.update(row_missing)
                controls_with_missing += 1
        
        if missing_refs:
            self.warnings.append(
                f"{len(missing_refs)} unique artifact references not found in evidence "
                f"(affects {controls_with_missing} controls). First few: {list(missing_refs)[:10]}"
            )
        else:
            self.info.append("All artifact references found in evidence data")
        
        return self._get_report()
    
    def _get_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
            'info': self.info.copy(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    def full_validation(
        self,
        controls_df: pd.DataFrame,
        evidence_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Run full validation on both datasets.
        
        Returns:
            Combined validation report
        """
        self.reset()
        
        # Validate controls
        ctrl_report = self.validate_controls(controls_df)
        
        # Validate evidence
        ev_report = self.validate_evidence(evidence_df)
        
        # Validate references
        ref_report = self.validate_artifact_references(controls_df, evidence_df)
        
        # Combine
        combined = {
            'valid': ctrl_report['valid'] and ev_report['valid'] and ref_report['valid'],
            'controls': ctrl_report,
            'evidence': ev_report,
            'references': ref_report,
            'summary': {
                'total_errors': ctrl_report['error_count'] + ev_report['error_count'] + ref_report['error_count'],
                'total_warnings': ctrl_report['warning_count'] + ev_report['warning_count'] + ref_report['warning_count']
            }
        }
        
        return combined


def generate_quality_report(
    controls_df: pd.DataFrame,
    evidence_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Generate a comprehensive data quality report.
    
    Returns:
        Dictionary with quality metrics and recommendations
    """
    report = {
        'controls': {},
        'evidence': {},
        'overall_score': 0,
        'recommendations': []
    }
    
    if controls_df is not None and not controls_df.empty:
        total = len(controls_df)
        
        # Calculate completeness scores
        fields = {
            'ccf_id': 1.0,  # Required
            'title': 0.9,
            'description': 0.9,
            'domain': 0.8,
            'type': 0.5,
            'theme': 0.5,
            'guidance': 0.7,
            'testing': 0.7,
            'mappings': 0.6
        }
        
        completeness_scores = {}
        for field, weight in fields.items():
            if field in controls_df.columns:
                if field == 'mappings':
                    # Special handling for mappings
                    filled = controls_df[field].apply(
                        lambda x: x is not None and x != {} and not (isinstance(x, float) and pd.isna(x))
                    ).sum()
                else:
                    filled = controls_df[field].notna().sum()
                completeness_scores[field] = {
                    'filled': int(filled),
                    'total': total,
                    'percentage': (filled / total) * 100,
                    'weight': weight
                }
            else:
                completeness_scores[field] = {
                    'filled': 0,
                    'total': total,
                    'percentage': 0,
                    'weight': weight
                }
        
        report['controls'] = {
            'total': total,
            'completeness': completeness_scores
        }
        
        # Generate recommendations
        for field, data in completeness_scores.items():
            if data['percentage'] < 50 and data['weight'] >= 0.7:
                report['recommendations'].append(
                    f"Consider adding {field} to more controls ({data['percentage']:.0f}% complete)"
                )
    
    if evidence_df is not None and not evidence_df.empty:
        total = len(evidence_df)
        
        fields = ['ref_id', 'title', 'domain']
        completeness_scores = {}
        
        for field in fields:
            if field in evidence_df.columns:
                filled = evidence_df[field].notna().sum()
                completeness_scores[field] = {
                    'filled': int(filled),
                    'total': total,
                    'percentage': (filled / total) * 100
                }
        
        report['evidence'] = {
            'total': total,
            'completeness': completeness_scores
        }
    
    # Calculate overall score
    if report['controls']:
        ctrl_scores = [
            d['percentage'] * d['weight']
            for d in report['controls']['completeness'].values()
        ]
        total_weight = sum(d['weight'] for d in report['controls']['completeness'].values())
        report['overall_score'] = sum(ctrl_scores) / total_weight if total_weight > 0 else 0
    
    return report