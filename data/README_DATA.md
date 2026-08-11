# Data Directory

This directory stores temporary PDF contract uploads and mock data used for ingestion testing.

### Supported Document Formats
- Binary `.pdf` files parsed via PySpark UDF and `pypdf`.

### Sample Contract Layout
A typical contract parsed by this system contains:
- Contracting Parties (Party A / Party B)
- Effective Date
- Financial Terms (Initial Price, Payment Terms)
- Renewal and Termination Clauses
