# GRC Compliance Platform
## Comprehensive Project Documentation

---

# Table of Contents

1. [Introduction and Objectives](#1-introduction-and-objectives)
2. [Theoretical Background](#2-theoretical-background-domain)
3. [System Design and Architecture](#3-system-design-and-architecture)
4. [Database Schema Reference](#4-database-schema-reference)
5. [Module and File Reference](#5-module-and-file-reference)
6. [Functional Walkthrough](#6-functional-walkthrough)
7. [Data Import and Validation](#7-data-import-and-validation)
8. [Exports and Reports](#8-exports-and-reports)
9. [Screenshots and Sample Outputs](#9-screenshots-and-sample-outputs)
10. [API and Function Reference](#10-api-and-function-reference)
11. [Configuration Reference](#11-configuration-reference)
12. [Installation and Setup](#12-installation-and-setup)
13. [Usage Guide](#13-usage-guide)
14. [Troubleshooting](#14-troubleshooting)
15. [Limitations](#15-limitations)
16. [Future Improvements](#16-future-improvements)
17. [Glossary](#17-glossary)
18. [Appendix](#18-appendix)

---

# 1. Introduction and Objectives

## 1.1 Project Overview

The **GRC Compliance Platform** is a comprehensive web-based application designed to help organizations manage their Governance, Risk, and Compliance (GRC) activities. Built using Python and Streamlit, this platform provides a centralized solution for managing compliance controls, tracking evidence artifacts, mapping controls across multiple regulatory frameworks, and generating compliance reports.

## 1.2 Purpose Statement

The primary purpose of this platform is to provide organizations with a unified system to:

- **Centralize Compliance Data**: Import and manage controls from various compliance frameworks (such as Adobe Common Controls Framework - CCF) in a single, searchable database.
- **Streamline Evidence Management**: Track and link evidence artifacts to specific controls, ensuring audit readiness and regulatory compliance.
- **Enable Cross-Framework Mapping**: Map controls across different regulatory standards including ISO 27001, NIST CSF, SOC 2, PCI-DSS, and HIPAA.
- **Provide Visibility and Insights**: Deliver dashboard analytics, gap analysis, and compliance scoring to identify areas requiring attention.
- **Generate Compliance Reports**: Export comprehensive reports in multiple formats for stakeholders, auditors, and management.

## 1.3 Target Audience

This platform is designed for:

| Role | Use Case |
|------|----------|
| **Compliance Officers** | Managing and tracking organizational compliance posture |
| **Security Analysts** | Reviewing control implementations and evidence |
| **Auditors** | Assessing compliance status and reviewing evidence |
| **IT Managers** | Understanding security control requirements |
| **Risk Managers** | Identifying gaps and prioritizing remediation |
| **GRC Consultants** | Helping clients organize compliance documentation |

## 1.4 Key Features Summary

| Feature | Description |
|---------|-------------|
| **Multi-Framework Support** | Import and manage multiple compliance frameworks simultaneously |
| **Control Management** | Browse, search, and filter controls with detailed metadata |
| **Evidence Tracking** | Link evidence artifacts to controls for audit traceability |
| **Framework Mapping** | Cross-reference controls across NIST, ISO, SOC 2, PCI-DSS, HIPAA |
| **Gap Analysis** | Identify missing guidance, testing procedures, and evidence |
| **Compliance Scoring** | Calculate and visualize compliance posture |
| **Report Generation** | Export reports in CSV, JSON, and Excel formats |
| **Data Validation** | Validate imported data for quality and consistency |
| **Admin Portal** | Manage sources, imports, and database operations |

---

# 2. Theoretical Background (Domain)

## 2.1 What is GRC?

**Governance, Risk, and Compliance (GRC)** is an integrated approach to managing an organization's overall governance, enterprise risk management, and compliance with regulations. The three components work together:

- **Governance**: The framework of rules, practices, and processes by which an organization is directed and controlled.
- **Risk Management**: The process of identifying, assessing, and controlling threats to an organization's capital and earnings.
- **Compliance**: The act of conforming to rules, policies, standards, and laws.

## 2.2 Key GRC Concepts Implemented

### 2.2.1 Compliance Frameworks

A compliance framework is a structured set of guidelines and best practices that organizations follow to meet regulatory requirements, manage risks, and ensure proper governance. This platform supports:

| Framework | Full Name | Primary Focus |
|-----------|-----------|---------------|
| **NIST CSF** | National Institute of Standards and Technology Cybersecurity Framework | Cybersecurity risk management |
| **ISO 27001** | International Organization for Standardization 27001 | Information security management |
| **SOC 2** | Service Organization Control 2 | Service organization controls |
| **PCI-DSS** | Payment Card Industry Data Security Standard | Payment card data protection |
| **HIPAA** | Health Insurance Portability and Accountability Act | Healthcare data privacy |
| **CCF** | Common Controls Framework | Unified security controls |

### 2.2.2 Controls

Controls are safeguards or countermeasures designed to protect the confidentiality, integrity, and availability of data and systems. Each control in this platform includes:

- **Control ID**: Unique identifier (e.g., CCF-001)
- **Title**: Short descriptive name
- **Description**: Detailed explanation of the control objective
- **Domain**: Category or family the control belongs to
- **Type**: Classification (Preventive, Detective, Corrective)
- **Theme**: Subcategory or theme
- **Guidance**: Implementation guidance and instructions
- **Testing Procedures**: How to verify the control is effective
- **Framework Mappings**: References to external standards

### 2.2.3 Control Domains

Domains are logical groupings of related controls. Common domains include:

| Domain | Description |
|--------|-------------|
| **Identity & Access Management** | User authentication, authorization, and access control |
| **Data Protection** | Data classification, encryption, and handling |
| **Infrastructure Security** | Network, server, and endpoint protection |
| **Application Security** | Secure software development and deployment |
| **Incident Management** | Detection, response, and recovery procedures |
| **Business Continuity** | Backup, disaster recovery, and resilience |
| **Human Resources** | Security awareness and personnel security |
| **Cryptography** | Encryption standards and key management |
| **Physical Security** | Facility access and environmental controls |
| **Compliance** | Regulatory and policy adherence |

### 2.2.4 Evidence Artifacts

Evidence artifacts are documents, records, screenshots, logs, or other proof items that demonstrate a control has been implemented and is operating effectively. Types of evidence include:

- **Policies and Procedures**: Documented rules and guidelines
- **Configuration Screenshots**: System settings and configurations
- **Audit Logs**: System and application event records
- **Training Records**: Employee awareness and certification
- **Assessment Reports**: Third-party or internal evaluations
- **Ticket/Change Records**: ITSM documentation
- **Access Reviews**: Periodic entitlement reviews

### 2.2.5 Control-Evidence Relationships

The platform maintains many-to-many relationships between controls and evidence:

- One control may require multiple evidence items
- One evidence item may satisfy multiple controls
- This relationship enables efficient evidence reuse and gap identification

### 2.2.6 Gap Analysis

Gap analysis identifies areas where compliance requirements are not fully met:

| Gap Type | Description |
|----------|-------------|
| **Missing Guidance** | Controls without implementation instructions |
| **Missing Testing** | Controls without verification procedures |
| **Missing Evidence** | Controls without linked evidence artifacts |
| **Orphan Evidence** | Evidence not linked to any control |

### 2.2.7 Compliance Scoring

The platform calculates compliance scores based on:

- **Guidance Coverage**: Percentage of controls with implementation guidance
- **Testing Coverage**: Percentage of controls with testing procedures
- **Evidence Coverage**: Percentage of controls with linked evidence
- **Overall Score**: Average of the three coverage metrics

---

# 3. System Design and Architecture

## 3.1 Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend/UI** | Streamlit | ≥1.28.0 | Web application framework |
| **Backend** | Python | 3.8+ | Core application logic |
| **Database** | SQLite | 3.x | Data persistence |
| **Data Processing** | Pandas | ≥2.0.0 | Data manipulation and analysis |
| **Visualization** | Plotly | ≥5.15.0 | Interactive charts and graphs |
| **Excel Processing** | openpyxl, xlrd | ≥3.1.0, ≥2.0.0 | Excel file handling |
| **Configuration** | PyYAML | ≥6.0 | YAML configuration parsing |

## 3.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GRC COMPLIANCE PLATFORM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      PRESENTATION LAYER                              │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐   │   │
│  │  │ Dashboard │ │ Controls  │ │ Evidence  │ │ Framework Mapping │   │   │
│  │  │    📊     │ │    🔍     │ │    📁     │ │        🗺️         │   │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘   │   │
│  │  ┌───────────┐ ┌───────────┐                                        │   │
│  │  │  Reports  │ │   Admin   │      Streamlit Multi-Page App          │   │
│  │  │    📈     │ │    ⚙️     │                                        │   │
│  │  └───────────┘ └───────────┘                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       BUSINESS LOGIC LAYER                           │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │   db.py     │  │ adapters.py │  │validators.py│  │exporters.py│  │   │
│  │  │             │  │             │  │             │  │            │  │   │
│  │  │ • Queries   │  │ • Cleaning  │  │ • Validate  │  │ • CSV      │  │   │
│  │  │ • CRUD      │  │ • Mapping   │  │ • Quality   │  │ • JSON     │  │   │
│  │  │ • Stats     │  │ • Transform │  │ • Reports   │  │ • Excel    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                        seed.py                               │    │   │
│  │  │  CLI Importer: Schema creation, data loading, validation    │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                    SQLite Database (grc.db)                    │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌──────────────────┐    ┌──────────────────┐                 │  │   │
│  │  │  │compliance_sources│    │     domains      │                 │  │   │
│  │  │  └────────┬─────────┘    └────────┬─────────┘                 │  │   │
│  │  │           │                       │                           │  │   │
│  │  │           ▼                       ▼                           │  │   │
│  │  │  ┌──────────────────┐    ┌──────────────────┐                 │  │   │
│  │  │  │     controls     │◄───│    evidence      │                 │  │   │
│  │  │  └────────┬─────────┘    └────────┬─────────┘                 │  │   │
│  │  │           │                       │                           │  │   │
│  │  │           └───────────┬───────────┘                           │  │   │
│  │  │                       ▼                                       │  │   │
│  │  │              ┌──────────────────┐                             │  │   │
│  │  │              │ control_evidence │                             │  │   │
│  │  │              └──────────────────┘                             │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌──────────────────┐                                         │  │   │
│  │  │  │  import_history  │                                         │  │   │
│  │  │  └──────────────────┘                                         │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3.3 Directory Structure

```
GRC/
├── app.py                          # Main application entry point
├── seed.py                         # CLI database seeder/importer
├── requirements.txt                # Python dependencies
├── README.md                       # Project readme
├── READ_BEFORE_RUN_THE_PROGRAM     # Quick start instructions
├── grc.db                          # SQLite database (generated)
│
├── config/
│   └── column_mappings.yaml        # Column mapping configuration
│
├── pages/
│   ├── 1_📊_Dashboard.py           # Dashboard with KPIs and charts
│   ├── 2_🔍_Controls.py            # Controls browser and search
│   ├── 3_📁_Evidence.py            # Evidence tracker
│   ├── 4_🗺️_Framework_Mapping.py  # Cross-framework mapping
│   ├── 5_📈_Reports.py             # Report generation and exports
│   └── 6_⚙️_Admin.py               # Administration and imports
│
├── utils/
│   ├── __init__.py                 # Package initializer
│   ├── db.py                       # Database operations (~940 lines)
│   ├── adapters.py                 # Data cleaning and mapping (~1190 lines)
│   ├── validators.py               # Data validation (~360 lines)
│   └── exporters.py                # Export utilities (~300 lines)
│
└── docs/
    └── PROJECT_DOCUMENTATION.md    # This documentation file
```

## 3.4 Data Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Excel/CSV   │────▶│   seed.py    │────▶│   SQLite     │
│  Source File │     │   Importer   │     │   Database   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                     │
                            ▼                     │
                     ┌──────────────┐             │
                     │  Validation  │             │
                     │  & Cleaning  │             │
                     └──────────────┘             │
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Export     │◀────│  Streamlit   │◀────│   db.py      │
│  CSV/JSON/XLS│     │     UI       │     │   Queries    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

# 4. Database Schema Reference

## 4.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐          ┌─────────────────────────┐          │
│  │   compliance_sources    │          │        domains          │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ PK id INTEGER           │──────┐   │ PK id INTEGER           │          │
│  │    name TEXT UNIQUE     │      │   │ FK source_id INTEGER    │◀─────┐   │
│  │    short_name TEXT      │      │   │    name TEXT            │      │   │
│  │    description TEXT     │      │   │    description TEXT     │      │   │
│  │    version TEXT         │      │   │    created_at TIMESTAMP │      │   │
│  │    source_file TEXT     │      │   └─────────────────────────┘      │   │
│  │    control_count INT    │      │              │                     │   │
│  │    evidence_count INT   │      │              │ 1:N                 │   │
│  │    is_active INT        │      │              ▼                     │   │
│  │    color TEXT           │      │   ┌─────────────────────────┐      │   │
│  │    created_at TIMESTAMP │      │   │       controls          │      │   │
│  │    updated_at TIMESTAMP │      │   ├─────────────────────────┤      │   │
│  └─────────────────────────┘      └──▶│ PK id INTEGER           │      │   │
│              │                        │ FK source_id INTEGER    │──────┘   │
│              │                        │ FK domain_id INTEGER    │◀─────────┤
│              │ 1:N                    │    ccf_id TEXT UNIQUE   │          │
│              │                        │    title TEXT           │          │
│              ▼                        │    description TEXT     │          │
│  ┌─────────────────────────┐          │    type TEXT            │          │
│  │      evidence           │          │    theme TEXT           │          │
│  ├─────────────────────────┤          │    guidance TEXT        │          │
│  │ PK id INTEGER           │          │    testing TEXT         │          │
│  │ FK source_id INTEGER    │◀─────────│    mappings JSON        │          │
│  │    ref_id TEXT          │          │    artifacts TEXT       │          │
│  │    title TEXT           │          │    created_at TIMESTAMP │          │
│  │    domain TEXT          │          └─────────────────────────┘          │
│  │    description TEXT     │                     │                         │
│  │    created_at TIMESTAMP │                     │                         │
│  └─────────────────────────┘                     │                         │
│              │                                   │                         │
│              │                                   │                         │
│              │              N:M                  │                         │
│              │     ┌─────────────────────────┐   │                         │
│              └────▶│   control_evidence      │◀──┘                         │
│                    ├─────────────────────────┤                             │
│                    │ FK control_id INTEGER   │                             │
│                    │ FK evidence_id INTEGER  │                             │
│                    │    PRIMARY KEY (both)   │                             │
│                    └─────────────────────────┘                             │
│                                                                             │
│  ┌─────────────────────────┐                                               │
│  │    import_history       │                                               │
│  ├─────────────────────────┤                                               │
│  │ PK id INTEGER           │                                               │
│  │ FK source_id INTEGER    │                                               │
│  │    source_file TEXT     │                                               │
│  │    source_type TEXT     │                                               │
│  │    controls_imported INT│                                               │
│  │    evidence_imported INT│                                               │
│  │    domains_created INT  │                                               │
│  │    imported_at TIMESTAMP│                                               │
│  │    notes TEXT           │                                               │
│  └─────────────────────────┘                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 Table Definitions

### 4.2.1 compliance_sources

Stores metadata about each imported compliance framework.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| name | TEXT | UNIQUE NOT NULL | Full framework name |
| short_name | TEXT | | Abbreviated name (e.g., "CCF") |
| description | TEXT | | Framework description |
| version | TEXT | | Framework version (e.g., "3.0") |
| source_file | TEXT | | Original import file name |
| control_count | INTEGER | DEFAULT 0 | Number of controls |
| evidence_count | INTEGER | DEFAULT 0 | Number of evidence items |
| is_active | INTEGER | DEFAULT 1 | Active flag (1=active, 0=inactive) |
| color | TEXT | DEFAULT '#667eea' | UI color for badges |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

### 4.2.2 domains

Stores control domain/category information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| source_id | INTEGER | FOREIGN KEY | Reference to compliance_sources |
| name | TEXT | NOT NULL | Domain name |
| description | TEXT | | Domain description |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

### 4.2.3 controls

Stores individual compliance controls with all metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| source_id | INTEGER | FOREIGN KEY | Reference to compliance_sources |
| domain_id | INTEGER | FOREIGN KEY | Reference to domains |
| ccf_id | TEXT | UNIQUE | Control identifier (e.g., "CCF-001") |
| title | TEXT | | Control title/name |
| description | TEXT | | Full control description |
| type | TEXT | | Control type (Preventive/Detective/Corrective) |
| theme | TEXT | | Control theme/subcategory |
| guidance | TEXT | | Implementation guidance |
| testing | TEXT | | Testing/audit procedures |
| mappings | TEXT (JSON) | | Framework mappings as JSON |
| artifacts | TEXT | | Evidence artifact references |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

### 4.2.4 evidence

Stores evidence artifact metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| source_id | INTEGER | FOREIGN KEY | Reference to compliance_sources |
| ref_id | TEXT | | Evidence reference ID |
| title | TEXT | | Evidence title/name |
| domain | TEXT | | Evidence domain/category |
| description | TEXT | | Evidence description |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

### 4.2.5 control_evidence

Junction table for many-to-many control-evidence relationships.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| control_id | INTEGER | FOREIGN KEY, PRIMARY KEY | Reference to controls |
| evidence_id | INTEGER | FOREIGN KEY, PRIMARY KEY | Reference to evidence |

### 4.2.6 import_history

Tracks all data import operations for audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| source_id | INTEGER | FOREIGN KEY | Reference to compliance_sources |
| source_file | TEXT | | Imported file name |
| source_type | TEXT | | File type (excel, csv, etc.) |
| controls_imported | INTEGER | | Number of controls imported |
| evidence_imported | INTEGER | | Number of evidence items imported |
| domains_created | INTEGER | | Number of domains created |
| imported_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Import timestamp |
| notes | TEXT | | Import notes or messages |

## 4.3 Mappings JSON Structure

The `mappings` field in the controls table stores framework crosswalks as JSON:

```json
{
  "NIST CSF": ["PR.AC-1", "PR.AC-2"],
  "ISO 27001": ["A.9.1.1", "A.9.2.1"],
  "SOC 2": ["CC6.1"],
  "PCI-DSS": ["7.1", "7.1.2"],
  "HIPAA": ["164.312(a)(1)"]
}
```

---

# 5. Module and File Reference

## 5.1 Core Application Files

### 5.1.1 app.py (Main Entry Point)

**Purpose**: Application configuration, global styling, and Streamlit page setup.

**Key Components**:
- Page configuration (title, icon, layout)
- Custom CSS styling for UI components
- Sidebar navigation configuration
- Database existence checking
- Welcome page content

**Lines of Code**: ~557

### 5.1.2 seed.py (CLI Importer)

**Purpose**: Command-line tool for importing data from Excel files into the database.

**Key Components**:
- Argument parsing (source file, name, version, force flag)
- Schema creation with foreign keys
- Data extraction from Excel sheets
- Column mapping and data cleaning
- Control-evidence relationship building
- Import history logging

**Usage**:
```bash
python seed.py --source Open_Source_CCF.xls \
    --source-name "Adobe CCF" \
    --source-short "CCF" \
    --source-version "3.0" \
    --force
```

**Arguments**:
| Argument | Description | Default |
|----------|-------------|---------|
| --source | Path to Excel source file | Open_Source_CCF.xls |
| --source-name | Full name of the compliance source | Required |
| --source-short | Short name/abbreviation | Auto-generated |
| --source-version | Version string | None |
| --force | Force recreate database schema | False |
| --db | Database file path | grc.db |

**Lines of Code**: ~694

## 5.2 Utility Modules

### 5.2.1 utils/db.py (Database Operations)

**Purpose**: All database access functions, queries, and CRUD operations.

**Key Functions**:

| Function | Description |
|----------|-------------|
| `get_db_path()` | Get database file path (from env or default) |
| `db_exists()` | Check if database file exists |
| `get_connection()` | Context manager for database connections |
| `get_all_compliance_sources()` | Retrieve all compliance sources |
| `get_active_compliance_sources()` | Retrieve only active sources |
| `create_compliance_source()` | Create new compliance source |
| `update_compliance_source()` | Update source metadata |
| `delete_compliance_source()` | Delete source and all related data |
| `toggle_compliance_source()` | Toggle active/inactive status |
| `get_overview_stats()` | Get dashboard statistics |
| `get_quick_insights()` | Get quick insight data |
| `get_domain_stats()` | Get domain-level statistics |
| `search_controls()` | Search controls with filters |
| `get_control_by_id()` | Get single control details |
| `get_all_domains()` | Get all domains |
| `get_all_control_types()` | Get distinct control types |
| `get_all_themes()` | Get distinct themes |
| `get_all_frameworks()` | Get all mapped frameworks |
| `get_framework_coverage()` | Get framework mapping matrix |
| `get_all_evidence()` | Get all evidence items |
| `get_gap_analysis()` | Get gap analysis data |

**Lines of Code**: ~939

### 5.2.2 utils/adapters.py (Data Cleaning & Mapping)

**Purpose**: Data cleaning, column mapping, and format transformation utilities.

**Key Components**:

**Cleaning Functions**:
| Function | Description |
|----------|-------------|
| `clean_text()` | Normalize text, remove special characters |
| `clean_column_names()` | Clean DataFrame column names |
| `clean_dataframe()` | Clean entire DataFrame for Arrow compatibility |
| `sanitize_for_display()` | Prepare DataFrame for Streamlit display |
| `split_list_string()` | Split string by multiple delimiters |
| `fuzzy_match_column()` | Find best matching column name |

**ColumnMapper Class**:
- Default control column mappings (ccf_id, domain, title, description, type, theme, guidance, testing, artifacts)
- Default evidence column mappings (ref_id, title, domain)
- Fuzzy matching support for flexible imports

**Lines of Code**: ~1193

### 5.2.3 utils/validators.py (Data Validation)

**Purpose**: Validate imported data for quality and consistency.

**DataValidator Class Methods**:
| Method | Description |
|--------|-------------|
| `validate_controls()` | Validate controls DataFrame |
| `validate_evidence()` | Validate evidence DataFrame |
| `validate_artifact_references()` | Verify artifact refs exist in evidence |
| `full_validation()` | Run all validations |

**Validation Checks**:
- Required columns (ccf_id, ref_id)
- Empty/null IDs
- Duplicate IDs
- Missing important fields (title, description, domain)
- Invalid mapping JSON format
- Broken artifact references

**Output Report Structure**:
```python
{
    'valid': True/False,
    'errors': [],
    'warnings': [],
    'info': [],
    'error_count': 0,
    'warning_count': 0
}
```

**Lines of Code**: ~358

### 5.2.4 utils/exporters.py (Export Utilities)

**Purpose**: Export data to various formats and generate reports.

**Export Functions**:
| Function | Description |
|----------|-------------|
| `export_to_csv()` | Export DataFrame to CSV string |
| `export_to_json()` | Export DataFrame to JSON string |
| `export_to_excel()` | Export multiple DataFrames to Excel workbook |
| `format_controls_for_export()` | Format controls for export with optional mapping flattening |
| `generate_compliance_report()` | Generate framework-specific compliance report |
| `export_gap_analysis()` | Export gap analysis to Excel |
| `generate_framework_matrix()` | Generate framework coverage matrix |

**Lines of Code**: ~299

## 5.3 Page Modules

### 5.3.1 pages/1_📊_Dashboard.py

**Purpose**: Overview dashboard with KPIs, charts, and quick insights.

**Features**:
- Metric cards (Controls, Evidence, Domains, Frameworks)
- Evidence coverage percentage
- Domain distribution charts
- Control type distribution
- Missing guidance/evidence warnings
- Top domains by control count
- Framework selector in sidebar

**Lines of Code**: ~622

### 5.3.2 pages/2_🔍_Controls.py

**Purpose**: Browse, search, and view control details.

**Features**:
- Full-text search
- Filter by domain, type, theme
- Control cards with expandable details
- Guidance and testing procedure display
- Framework mapping badges
- Linked evidence count
- Search term highlighting

**Lines of Code**: ~663

### 5.3.3 pages/3_📁_Evidence.py

**Purpose**: Track and manage evidence artifacts.

**Features**:
- Evidence statistics (total, linked, orphan)
- Evidence listing with details
- Evidence-by-domain grouping
- Source filtering
- Linked controls display

**Lines of Code**: ~548

### 5.3.4 pages/4_🗺️_Framework_Mapping.py

**Purpose**: Cross-framework control mapping and coverage analysis.

**Features**:
- Framework coverage statistics
- Coverage percentage per framework
- Cross-reference matrix table
- Filter by specific framework
- Per-framework control listing
- Matrix export options

**Lines of Code**: ~541

### 5.3.5 pages/5_📈_Reports.py

**Purpose**: Generate and export compliance reports.

**Features**:
- Executive summary generation
- Gap analysis (missing guidance/testing/evidence)
- Orphan evidence identification
- Compliance score calculation
- Export to CSV, JSON, Excel
- Gap analysis workbook export
- Domain-level reporting

**Lines of Code**: ~639

### 5.3.6 pages/6_⚙️_Admin.py

**Purpose**: Administration, imports, and database management.

**Features**:
- Compliance sources management (list, activate, deactivate, edit, delete)
- Import wizard with Excel upload
- Sheet preview and selection
- Column mapping preview
- Import validation display
- Database info (path, size, tables)
- Import history log

**Lines of Code**: ~1040

## 4. Functional Walkthrough
- **Dashboard (pages/1_📊_Dashboard.py):** KPIs (controls, evidence, domains, frameworks), evidence coverage, top domains, missing guidance/evidence, and charts. Sidebar allows selecting active frameworks.
- **Controls Browser (pages/2_🔍_Controls.py):** Search and filter by domain/type/theme; view control cards with guidance, testing, mappings, and linked evidence badges.
- **Evidence Tracker (pages/3_📁_Evidence.py):** Evidence stats (total, linked, orphan), evidence listings, evidence-by-domain grouping, and source filters.
- **Framework Mapping (pages/4_🗺️_Framework_Mapping.py):** Coverage per framework, crosswalk matrix (control vs. NIST/ISO/SOC2/PCI/HIPAA), and per-framework mapped controls view.
- **Reports (pages/5_📈_Reports.py):** Executive summary, gap analysis (missing guidance/testing/evidence, orphan evidence), compliance score, and exports (CSV/JSON/Excel, gap analysis workbook).
- **Admin (pages/6_⚙️_Admin.py):** Import wizard (Excel upload, sheet preview), source activation/deactivation, editing metadata, delete source, database info, import history log.

## 5. Data Import and Validation
- **Seeder CLI:** `python seed.py --source Open_Source_CCF.xls --source-name "Adobe CCF" --source-short "CCF" --source-version "3.0" --force`
  - Creates/recreates schema and loads controls/evidence/mappings/artifacts.
- **Column mapping:** Fuzzy and configured mappings in [config/column_mappings.yaml](../config/column_mappings.yaml) and defaults inside [utils/adapters.py](../utils/adapters.py) `ColumnMapper`.
- **Cleaning:** `clean_text`, `clean_dataframe`, `sanitize_for_display` remove special whitespace, normalize unicode, and prepare Arrow-safe data.
- **Validation:** [utils/validators.py](../utils/validators.py)
  - Controls: required `ccf_id`, duplicate checks, missing fields, mapping format.
  - Evidence: required `ref_id`, duplicates, missing titles.
  - Artifact references: verifies control artifact refs exist in evidence set.
  - Combined quality report: errors, warnings, info, totals.

## 6. Exports and Reports
- **Exports:** CSV, JSON, Excel (multi-sheet) via [utils/exporters.py](../utils/exporters.py).
- **Compliance report:** Summaries per framework (coverage of guidance/testing/evidence) plus per-control detail.
- **Gap analysis export:** Excel workbook with sheets for missing guidance/testing/evidence and orphan evidence.
- **Framework matrix:** Builds matrix (controls as rows, frameworks as columns) from `mappings` JSON.

## 7. Example Screenshots to Capture
- Dashboard: KPIs and charts; sidebar framework selector.
- Controls: list with filters applied; one expanded control showing guidance/testing/mappings/evidence.
- Evidence: stats panel and evidence list; evidence-by-domain view.
- Framework Mapping: coverage cards; crosswalk matrix table.
- Reports: gap analysis view; export buttons.
- Admin: compliance sources list (active/inactive, counts); import wizard sheet preview; import history table.

## 8. Sample Outputs (illustrative)
- **Dashboard KPIs:** Controls 847; Evidence 312; Domains 18; Frameworks 6; Evidence coverage 78.4%; Missing guidance 23; Missing evidence 45.
- **Framework mapping row:** Control CCF-001 (Access Control Policy) mapped to NIST PR.AC-1, ISO 27001 A.9.1.1, SOC 2 CC6.1, PCI-DSS 7.1.
- **Gap analysis headline:** Missing guidance 23; Missing testing 31; Missing evidence 45; Orphan evidence 12; Compliance score ~82.4% (average of guidance/testing/evidence coverage).
- **Import summary (example):** Controls imported ~800-900; Evidence ~250-400; Domains ~10-25; Control-evidence links ~1k+; Source Adobe CCF v3.0.

## 9. Limitations
- SQLite local-first (single-user/demo) and limited concurrency.
- No authentication/RBAC in-app.
- Evidence handled as metadata; no file storage/versioning/retention.
- Import expectations biased to CCF-like Excel layouts (though fuzzy mapping helps).
- No workflow/remediation (tasks, SLAs, approvals).
- No external integrations (Jira/ServiceNow/cloud security APIs) yet.

## 10. Future Improvements
- Add authentication and role-based access control.
- Migrate to PostgreSQL/MySQL for multi-user and scale.
- Evidence file storage (S3/Blob/local) with retention and versioning.
- Workflow and remediation: tasks, owners, due dates, statuses.
- Integrations: ticketing systems, cloud/security tooling, SIEM/policy exports.
- Smarter mapping assistance (rule-based or ML suggestions) and mapping review UI.
- Custom dashboards and report builder; notifications (email/Slack).
- Multi-tenant support.

## 11. How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Seed database (example):
   - `python seed.py --source Open_Source_CCF.xls --source-name "Adobe CCF" --source-short "CCF" --source-version "3.0" --force`
3. Run the app: `streamlit run app.py`
4. Open: http://localhost:8501

## 12. Operational Notes
- Default DB path: `grc.db` (can override via `GRC_DB_PATH`).
- If tables or schema are missing, re-run the seeder with `--force` to recreate.
- Source activation/deactivation and deletion are available in the Admin page; deletion cascades controls/evidence/mappings for that source.
- Import history is logged for traceability (file name, counts, timestamps).

## 13. Quick Reference (Files)
- Main app: [app.py](../app.py)
- Seeder CLI: [seed.py](../seed.py)
- Pages: [pages](../pages)
- Database helpers: [utils/db.py](../utils/db.py)
- Adapters/cleaning/mapping: [utils/adapters.py](../utils/adapters.py)
- Validation: [utils/validators.py](../utils/validators.py)
- Export/report utilities: [utils/exporters.py](../utils/exporters.py)
- Column mappings config: [config/column_mappings.yaml](../config/column_mappings.yaml)
