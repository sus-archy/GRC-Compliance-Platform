#!/usr/bin/env python3
"""
GRC Platform Seeder - Multi-format data importer with multi-compliance support.
"""

import sqlite3
import json
import uuid
import os
import sys
import re
import logging
import argparse
from contextlib import contextmanager
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.adapters import get_adapter, clean_text, split_list_string
from utils.validators import DataValidator, generate_quality_report

# -----------------------
# Configuration
# -----------------------
DEFAULT_SOURCE = "Open_Source_CCF.xls"
DEFAULT_DB_NAME = "grc.db"

# Default colors for compliance sources
SOURCE_COLORS = [
    '#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a',
    '#a8edea', '#fed6e3', '#d299c2', '#fef9d7', '#d4fc79'
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# -----------------------
# Database Functions
# -----------------------
@contextmanager
def get_db(db_name: str):
    """Context manager for database connections."""
    conn = sqlite3.connect(db_name)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def create_schema(db_name: str, force_recreate: bool = False) -> bool:
    """Create or recreate the database schema with multi-compliance support."""
    if not force_recreate and os.path.exists(db_name):
        logger.info(f"Database '{db_name}' already exists. Use --force to recreate.")
        return False
    
    if force_recreate and os.path.exists(db_name):
        os.remove(db_name)
        logger.info(f"Removed existing database: {db_name}")
    
    with get_db(db_name) as conn:
        cursor = conn.cursor()
        
        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS control_evidence")
        cursor.execute("DROP TABLE IF EXISTS controls")
        cursor.execute("DROP TABLE IF EXISTS evidence")
        cursor.execute("DROP TABLE IF EXISTS domains")
        cursor.execute("DROP TABLE IF EXISTS import_history")
        cursor.execute("DROP TABLE IF EXISTS compliance_sources")
        
        # 1. Compliance Sources table
        cursor.execute("""
            CREATE TABLE compliance_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                short_name TEXT,
                description TEXT,
                version TEXT,
                source_file TEXT,
                control_count INTEGER DEFAULT 0,
                evidence_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                color TEXT DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Domains table
        cursor.execute("""
            CREATE TABLE domains (
                id TEXT PRIMARY KEY,
                source_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES compliance_sources(id),
                UNIQUE(source_id, name)
            );
        """)
        
        # 3. Evidence table
        cursor.execute("""
            CREATE TABLE evidence (
                id TEXT PRIMARY KEY,
                source_id INTEGER,
                ref_id TEXT NOT NULL,
                title TEXT,
                domain TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES compliance_sources(id),
                UNIQUE(source_id, ref_id)
            );
        """)
        
        # 4. Controls table
        cursor.execute("""
            CREATE TABLE controls (
                id TEXT PRIMARY KEY,
                source_id INTEGER,
                ccf_id TEXT NOT NULL,
                domain_id TEXT,
                title TEXT,
                description TEXT,
                type TEXT,
                theme TEXT,
                guidance TEXT,
                testing TEXT,
                mappings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES compliance_sources(id),
                FOREIGN KEY(domain_id) REFERENCES domains(id),
                UNIQUE(source_id, ccf_id)
            );
        """)
        
        # 5. Control-Evidence junction table
        cursor.execute("""
            CREATE TABLE control_evidence (
                control_id TEXT,
                evidence_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (control_id, evidence_id),
                FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
                FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
            );
        """)
        
        # 6. Import history table
        cursor.execute("""
            CREATE TABLE import_history (
                id TEXT PRIMARY KEY,
                source_id INTEGER,
                source_file TEXT,
                source_type TEXT,
                controls_imported INTEGER,
                evidence_imported INTEGER,
                domains_created INTEGER,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY(source_id) REFERENCES compliance_sources(id)
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_controls_source ON controls(source_id);")
        cursor.execute("CREATE INDEX idx_controls_domain ON controls(domain_id);")
        cursor.execute("CREATE INDEX idx_controls_type ON controls(type);")
        cursor.execute("CREATE INDEX idx_controls_theme ON controls(theme);")
        cursor.execute("CREATE INDEX idx_evidence_source ON evidence(source_id);")
        cursor.execute("CREATE INDEX idx_evidence_domain ON evidence(domain);")
        cursor.execute("CREATE INDEX idx_domains_source ON domains(source_id);")
        cursor.execute("CREATE INDEX idx_control_evidence_control ON control_evidence(control_id);")
        cursor.execute("CREATE INDEX idx_control_evidence_evidence ON control_evidence(evidence_id);")
        
        conn.commit()
        logger.info("✅ Database schema created successfully.")
        return True


def get_or_create_compliance_source(
    conn,
    name: str,
    short_name: str = None,
    description: str = None,
    version: str = None,
    source_file: str = None,
    color: str = None
) -> int:
    """Get existing compliance source or create new one."""
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM compliance_sources WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Get next color
    if not color:
        cursor.execute("SELECT COUNT(*) FROM compliance_sources")
        count = cursor.fetchone()[0]
        color = SOURCE_COLORS[count % len(SOURCE_COLORS)]
    
    # Create new
    cursor.execute("""
        INSERT INTO compliance_sources (name, short_name, description, version, source_file, color)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, short_name or name[:15], description, version, source_file, color))
    
    conn.commit()
    return cursor.lastrowid


def update_compliance_source_counts(conn, source_id: int):
    """Update control and evidence counts for a compliance source."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM controls WHERE source_id = ?", (source_id,))
    control_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM evidence WHERE source_id = ?", (source_id,))
    evidence_count = cursor.fetchone()[0]
    
    cursor.execute("""
        UPDATE compliance_sources 
        SET control_count = ?, evidence_count = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (control_count, evidence_count, source_id))
    
    conn.commit()


def seed_from_dataframes(
    controls_df: pd.DataFrame,
    evidence_df: pd.DataFrame,
    db_name: str,
    source_info: str = None,
    source_name: str = None,
    source_short_name: str = None,
    source_description: str = None,
    source_version: str = None
) -> Dict[str, int]:
    """
    Seed database from canonical DataFrames with compliance source tracking.
    """
    stats = {
        'controls_imported': 0,
        'evidence_imported': 0,
        'domains_created': 0,
        'evidence_links': 0,
        'source_id': None
    }
    
    # Determine source name from file if not provided
    if not source_name and source_info:
        # Extract name from filename
        base_name = os.path.basename(source_info)
        name_without_ext = os.path.splitext(base_name)[0]
        # Clean up the name
        source_name = name_without_ext.replace('_', ' ').replace('-', ' ').title()
    
    if not source_name:
        source_name = f"Import {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    evidence_lookup: Dict[str, str] = {}
    
    with get_db(db_name) as conn:
        cursor = conn.cursor()
        
        # Get or create compliance source
        source_id = get_or_create_compliance_source(
            conn,
            name=source_name,
            short_name=source_short_name,
            description=source_description,
            version=source_version,
            source_file=source_info
        )
        stats['source_id'] = source_id
        logger.info(f"Using compliance source: {source_name} (ID: {source_id})")
        
        # -----------------------
        # Insert Evidence
        # -----------------------
        if evidence_df is not None and not evidence_df.empty:
            logger.info(f"Inserting {len(evidence_df)} evidence items...")
            
            for _, row in evidence_df.iterrows():
                ref_id = clean_text(row.get('ref_id'))
                if not ref_id:
                    continue
                
                ev_id = str(uuid.uuid4())
                
                # Check if exists for this source
                cursor.execute(
                    "SELECT id FROM evidence WHERE source_id = ? AND ref_id = ?",
                    (source_id, ref_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    ev_id = existing[0]
                    cursor.execute("""
                        UPDATE evidence SET title = ?, domain = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (clean_text(row.get('title')), clean_text(row.get('domain')), ev_id))
                else:
                    cursor.execute("""
                        INSERT INTO evidence (id, source_id, ref_id, title, domain)
                        VALUES (?, ?, ?, ?, ?)
                    """, (ev_id, source_id, ref_id, clean_text(row.get('title')), clean_text(row.get('domain'))))
                
                stats['evidence_imported'] += 1
            
            conn.commit()
            
            # Build lookup
            rows = cursor.execute(
                "SELECT id, ref_id FROM evidence WHERE source_id = ?",
                (source_id,)
            ).fetchall()
            evidence_lookup = {r[1]: r[0] for r in rows}
            logger.info(f"✅ Inserted {stats['evidence_imported']} evidence items")
        
        # -----------------------
        # Insert Controls
        # -----------------------
        if controls_df is None or controls_df.empty:
            logger.warning("No controls to import")
            return stats
        
        logger.info(f"Inserting {len(controls_df)} controls...")
        
        domain_cache: Dict[str, str] = {}
        
        for idx, row in controls_df.iterrows():
            ccf_id = clean_text(row.get('ccf_id'))
            if not ccf_id:
                continue
            
            # Handle domain
            domain_name = clean_text(row.get('domain'))
            domain_id = None
            
            if domain_name:
                cache_key = f"{source_id}:{domain_name}"
                if cache_key in domain_cache:
                    domain_id = domain_cache[cache_key]
                else:
                    cursor.execute(
                        "SELECT id FROM domains WHERE source_id = ? AND name = ?",
                        (source_id, domain_name)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        domain_id = result[0]
                    else:
                        domain_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO domains (id, source_id, name) VALUES (?, ?, ?)",
                            (domain_id, source_id, domain_name)
                        )
                        stats['domains_created'] += 1
                    
                    domain_cache[cache_key] = domain_id
            
            # Handle mappings
            mappings = row.get('mappings')
            if mappings is None or (isinstance(mappings, float) and pd.isna(mappings)):
                mappings_json = '{}'
            elif isinstance(mappings, dict):
                mappings_json = json.dumps(mappings)
            elif isinstance(mappings, str):
                try:
                    json.loads(mappings)
                    mappings_json = mappings
                except:
                    mappings_json = '{}'
            else:
                mappings_json = '{}'
            
            # Check if control exists for this source
            cursor.execute(
                "SELECT id FROM controls WHERE source_id = ? AND ccf_id = ?",
                (source_id, ccf_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                ctrl_id = existing[0]
                cursor.execute("DELETE FROM control_evidence WHERE control_id = ?", (ctrl_id,))
                
                cursor.execute("""
                    UPDATE controls SET
                        domain_id = ?, title = ?, description = ?, type = ?, theme = ?,
                        guidance = ?, testing = ?, mappings = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    domain_id,
                    clean_text(row.get('title')),
                    clean_text(row.get('description')),
                    clean_text(row.get('type')),
                    clean_text(row.get('theme')),
                    clean_text(row.get('guidance')),
                    clean_text(row.get('testing')),
                    mappings_json,
                    ctrl_id
                ))
            else:
                ctrl_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO controls (id, source_id, ccf_id, domain_id, title, description, type, theme, guidance, testing, mappings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ctrl_id, source_id, ccf_id, domain_id,
                    clean_text(row.get('title')),
                    clean_text(row.get('description')),
                    clean_text(row.get('type')),
                    clean_text(row.get('theme')),
                    clean_text(row.get('guidance')),
                    clean_text(row.get('testing')),
                    mappings_json
                ))
            
            stats['controls_imported'] += 1
            
            # Link evidence
            artifacts = row.get('artifacts')
            if artifacts and not (isinstance(artifacts, float) and pd.isna(artifacts)):
                refs = split_list_string(str(artifacts))
                for ref in refs:
                    ev_id = evidence_lookup.get(ref)
                    if ev_id:
                        cursor.execute("""
                            INSERT OR IGNORE INTO control_evidence (control_id, evidence_id)
                            VALUES (?, ?)
                        """, (ctrl_id, ev_id))
                        stats['evidence_links'] += 1
            
            if (idx + 1) % 100 == 0:
                logger.info(f"  Processed {idx + 1} controls...")
        
        # Update source counts
        update_compliance_source_counts(conn, source_id)
        
        # Record import history
        import_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO import_history (id, source_id, source_file, source_type, controls_imported, evidence_imported, domains_created, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            import_id, source_id, source_info or 'unknown', 'seed',
            stats['controls_imported'], stats['evidence_imported'], stats['domains_created'],
            f"Evidence links created: {stats['evidence_links']}"
        ))
        
        conn.commit()
    
    logger.info(f"✅ Import complete:")
    logger.info(f"   - Source: {source_name} (ID: {source_id})")
    logger.info(f"   - Controls: {stats['controls_imported']}")
    logger.info(f"   - Evidence: {stats['evidence_imported']}")
    logger.info(f"   - Domains: {stats['domains_created']}")
    logger.info(f"   - Evidence links: {stats['evidence_links']}")
    
    return stats


def run_seed(
    source: str,
    db_name: str = DEFAULT_DB_NAME,
    force_recreate: bool = False,
    format_hint: str = 'auto',
    sheet_main: str = None,
    sheet_guidance: str = None,
    sheet_evidence: str = None,
    validate_only: bool = False,
    column_mappings: Dict = None,
    source_name: str = None,
    source_short_name: str = None,
    source_description: str = None,
    source_version: str = None
) -> Dict[str, Any]:
    """Main seeding function."""
    result = {
        'success': False,
        'validation': None,
        'quality_report': None,
        'import_stats': None,
        'errors': []
    }
    
    try:
        if not validate_only:
            if force_recreate or not os.path.exists(db_name):
                create_schema(db_name, force_recreate=force_recreate)
        
        logger.info(f"Loading source: {source} (format: {format_hint})")
        adapter = get_adapter(
            source,
            format_hint=format_hint,
            sheet_main=sheet_main,
            sheet_guidance=sheet_guidance,
            sheet_evidence=sheet_evidence,
            column_mappings=column_mappings
        )
        
        validation = adapter.validate()
        result['validation'] = validation
        
        if not validation['valid']:
            result['errors'].extend(validation['errors'])
            logger.error(f"Validation failed: {validation['errors']}")
            return result
        
        logger.info("Loading data from source...")
        controls_df, evidence_df = adapter.load()
        
        if controls_df is None or controls_df.empty:
            result['errors'].append("No controls found in source")
            return result
        
        logger.info(f"Loaded {len(controls_df)} controls, {len(evidence_df)} evidence items")
        
        validator = DataValidator()
        data_validation = validator.full_validation(controls_df, evidence_df)
        result['data_validation'] = data_validation
        
        if data_validation['controls']['errors']:
            for err in data_validation['controls']['errors']:
                logger.error(f"Control validation error: {err}")
        
        if data_validation['controls']['warnings']:
            for warn in data_validation['controls']['warnings']:
                logger.warning(f"Control validation warning: {warn}")
        
        quality_report = generate_quality_report(controls_df, evidence_df)
        result['quality_report'] = quality_report
        logger.info(f"Data quality score: {quality_report['overall_score']:.1f}%")
        
        if validate_only:
            logger.info("Validation complete (validate-only mode)")
            result['success'] = True
            return result
        
        if not data_validation['valid']:
            result['errors'].append("Data validation failed with critical errors")
            for err in data_validation['controls']['errors']:
                result['errors'].append(err)
            return result
        
        logger.info("Importing data into database...")
        import_stats = seed_from_dataframes(
            controls_df,
            evidence_df,
            db_name,
            source_info=source,
            source_name=source_name,
            source_short_name=source_short_name,
            source_description=source_description,
            source_version=source_version
        )
        
        result['import_stats'] = import_stats
        result['success'] = True
        
        logger.info("🎉 Seeding completed successfully!")
        
    except FileNotFoundError as e:
        result['errors'].append(str(e))
        logger.error(f"File not found: {e}")
    except ValueError as e:
        result['errors'].append(str(e))
        logger.error(f"Value error: {e}")
    except Exception as e:
        result['errors'].append(f"Unexpected error: {str(e)}")
        logger.exception(f"Unexpected error during seeding: {e}")
    
    return result


def load_column_mappings(config_path: str) -> Optional[Dict]:
    """Load column mappings from YAML or JSON config file."""
    if not os.path.exists(config_path):
        return None
    
    try:
        ext = os.path.splitext(config_path)[1].lower()
        
        if ext in ('.yaml', '.yml'):
            try:
                import yaml
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except ImportError:
                logger.warning("PyYAML not installed. Install with: pip install pyyaml")
                return None
        
        elif ext == '.json':
            with open(config_path, 'r') as f:
                return json.load(f)
        
        else:
            logger.warning(f"Unsupported config file format: {ext}")
            return None
    
    except Exception as e:
        logger.warning(f"Failed to load column mappings: {e}")
        return None


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the GRC database from multiple source formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Seed from Excel file (auto-detect name from filename)
    python seed.py --source data.xlsx --db grc.db --force
    
    # Seed with custom compliance source name
    python seed.py --source data.xlsx --source-name "SCF 2024" --source-short "SCF"
    
    # Seed multiple frameworks
    python seed.py --source ccf.xlsx --source-name "Adobe CCF" --source-short "CCF"
    python seed.py --source scf.xlsx --source-name "SCF 2024" --source-short "SCF"
        """
    )
    
    parser.add_argument('--source', default=DEFAULT_SOURCE, help='Path to source file or folder')
    parser.add_argument('--db', default=DEFAULT_DB_NAME, help='Path to SQLite database')
    parser.add_argument('--force', action='store_true', help='Force recreate the database schema')
    parser.add_argument('--format', default='auto', choices=['auto', 'excel', 'json', 'csv', 'xml', 'zip'])
    parser.add_argument('--sheet-main', default=None, help='Excel main controls sheet name')
    parser.add_argument('--sheet-guidance', default=None, help='Excel guidance sheet name')
    parser.add_argument('--sheet-evidence', default=None, help='Excel evidence sheet name')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not import')
    parser.add_argument('--config', default=None, help='Path to column mappings config file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # New compliance source arguments
    parser.add_argument('--source-name', default=None, help='Name for this compliance source/framework')
    parser.add_argument('--source-short', default=None, help='Short name (e.g., CCF, SCF)')
    parser.add_argument('--source-desc', default=None, help='Description of this compliance source')
    parser.add_argument('--source-version', default=None, help='Version of this compliance framework')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    column_mappings = None
    if args.config:
        column_mappings = load_column_mappings(args.config)
        if column_mappings:
            logger.info(f"Loaded column mappings from {args.config}")
    
    result = run_seed(
        source=args.source,
        db_name=args.db,
        force_recreate=args.force,
        format_hint=args.format,
        sheet_main=args.sheet_main,
        sheet_guidance=args.sheet_guidance,
        sheet_evidence=args.sheet_evidence,
        validate_only=args.validate_only,
        column_mappings=column_mappings,
        source_name=args.source_name,
        source_short_name=args.source_short,
        source_description=args.source_desc,
        source_version=args.source_version
    )
    
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()