import sqlite3
import json
from typing import Any, Optional
from ..queries import (
    CREATE_DOCUMENT_ONTOLOGIES_TABLE,
    INSERT_DOCUMENT_ONTOLOGY,
    CREATE_INDEX_DOCUMENT_ONTOLOGIES_DOCUMENT_VERSION,
    CREATE_INDEX_DOCUMENT_ONTOLOGIES_STATUS,
)
from .queries import (
    CREATE_CSV_PROFILES_TABLE,
    UPSERT_CSV_PROFILE,
    CREATE_CSV_MAPPINGS_TABLE,
    INSERT_CSV_MAPPING,
)
import logging

logger = logging.getLogger(__name__)

class SQLiteTabularDocumentRepository():
    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_tables(self) -> bool:
        logger.info("📦 [INIT] Creating tabular document tables if they don't exist")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")

                # csv_profiles
                logger.info("  → Creating csv_profiles table...")
                cur.execute(CREATE_CSV_PROFILES_TABLE)

                # csv_mappings
                logger.info("  → Creating csv_mappings table...")
                cur.execute(CREATE_CSV_MAPPINGS_TABLE)

                # document_ontologies table + indexes
                logger.info("  → Creating document_ontologies table...")
                cur.execute(CREATE_DOCUMENT_ONTOLOGIES_TABLE)
                logger.info("  → Creating indexes for document_ontologies...")
                cur.execute(CREATE_INDEX_DOCUMENT_ONTOLOGIES_DOCUMENT_VERSION)
                cur.execute(CREATE_INDEX_DOCUMENT_ONTOLOGIES_STATUS)

                conn.commit()
                logger.info("✅ [INIT] Tabular document tables created successfully")
                return True
        except Exception as e:
            logger.error(f"❌ [INIT] Error creating tabular document tables: {e}", exc_info=True)
            return False



    def save_csv_profile(self, profile: Any) -> bool:
        """Save a CSV profile to the database.
        
        Maps CSVProfile fields to database columns:
        - document_id: from profile.document_id
        - delimiter: from profile.delimiter
        - has_header: True if headers_original exists and is not empty
        - encoding: from profile.encoding
        - row_count: from profile.row_count_sampled
        - column_count: from profile.column_count
        - headers: JSON serialized from profile.headers_original
        - sample_rows: JSON serialized from profile.sample_rows
        - profile_stats: JSON serialized from profile.columns
        """
        doc_id = getattr(profile, "document_id", None)
        if doc_id is None:
            logger.error("❌ [SAVE] CSV profile missing required document_id")
            return False
            
        logger.info(f"💾 [SAVE] Starting CSV profile save for document_id={doc_id}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Verify document exists (foreign key constraint check)
                cur.execute("SELECT id FROM documents WHERE id = ?", (doc_id,))
                doc_exists = cur.fetchone()
                if not doc_exists:
                    logger.error(f"❌ [SAVE] Document with id={doc_id} does not exist in documents table. Cannot save CSV profile.")
                    return False
                
                # Determine has_header: True if headers exist and are not empty
                has_header = 1 if (hasattr(profile, "headers_original") and 
                                  profile.headers_original and 
                                  len(profile.headers_original) > 0) else 0
                
                # Serialize headers to JSON
                headers_json = None
                if hasattr(profile, "headers_original") and profile.headers_original:
                    headers_json = json.dumps(profile.headers_original)
                
                # Serialize sample_rows to JSON
                sample_rows_json = None
                if hasattr(profile, "sample_rows") and profile.sample_rows:
                    sample_rows_json = json.dumps(profile.sample_rows)
                
                # Serialize columns (profile_stats) to JSON
                profile_stats_json = None
                if hasattr(profile, "columns") and profile.columns:
                    # Convert ColumnStat objects to dicts for JSON serialization
                    columns_data = [
                        {
                            "name": col.name,
                            "non_null": col.non_null,
                            "nulls": col.nulls,
                            "distinct": getattr(col, "distinct", 0),
                            "inferred_type": col.inferred_type,
                            "example_values": col.example_values,
                        }
                        for col in profile.columns
                    ]
                    profile_stats_json = json.dumps(columns_data)
                
                logger.info(f"  → Preparing CSV profile data: document_id={doc_id}, "
                           f"delimiter={getattr(profile, 'delimiter', ',')}, "
                           f"has_header={has_header}, "
                           f"row_count={getattr(profile, 'row_count_sampled', None)}, "
                           f"column_count={getattr(profile, 'column_count', None)}")
                
                # Execute the UPSERT query
                # Note: RETURNING clause is supported in SQLite 3.35.0+, but we'll handle it gracefully
                try:
                    cur.execute(
                        UPSERT_CSV_PROFILE,
                        (
                            profile.document_id,
                            getattr(profile, "delimiter", ","),
                            has_header,
                            getattr(profile, "encoding", "utf-8"),
                            getattr(profile, "row_count_sampled", None),  # Map row_count_sampled to row_count
                            getattr(profile, "column_count", None),
                            headers_json,  # JSON serialized headers
                            sample_rows_json,  # JSON serialized sample_rows
                            profile_stats_json,  # JSON serialized columns as profile_stats
                        ),
                    )
                    # Fetch the returned ID if RETURNING is supported
                    result = cur.fetchone()
                    if result:
                        profile_id = result[0]
                        logger.debug(f"  → CSV profile saved with id={profile_id}")
                except sqlite3.OperationalError as e:
                    # If RETURNING is not supported, try without it
                    if "RETURNING" in str(e).upper():
                        logger.warning(f"  → SQLite version doesn't support RETURNING, using fallback")
                        # Remove RETURNING from query
                        query_without_returning = UPSERT_CSV_PROFILE.replace("RETURNING id;", ";")
                        cur.execute(
                            query_without_returning,
                            (
                                profile.document_id,
                                getattr(profile, "delimiter", ","),
                                has_header,
                                getattr(profile, "encoding", "utf-8"),
                                getattr(profile, "row_count_sampled", None),
                                getattr(profile, "column_count", None),
                                headers_json,
                                sample_rows_json,
                                profile_stats_json,
                            ),
                        )
                    else:
                        raise
                
                conn.commit()
                
                # Verify the save worked by checking if the profile exists
                cur.execute("SELECT id FROM csv_profiles WHERE document_id = ?", (doc_id,))
                saved_profile = cur.fetchone()
                if saved_profile:
                    logger.info(f"✅ [SAVE] CSV profile saved successfully for document_id={doc_id}, profile_id={saved_profile[0]}")
                    return True
                else:
                    logger.error(f"❌ [SAVE] CSV profile save appeared to succeed but profile not found for document_id={doc_id}")
                    return False
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ [SAVE] Foreign key constraint failed for document_id={doc_id}: {e}")
            logger.error(f"  → This usually means the document with id={doc_id} does not exist in the documents table")
            return False
        except Exception as e:
            logger.error(f"❌ [SAVE] Failed to save CSV profile for document_id={doc_id}: {e}", exc_info=True)
            return False

    def save_document_ontology(self, doc_ontology: Any) -> Optional[Any]:
        """Save a document ontology to the database.
        
        Args:
            doc_ontology: DocumentOntology instance to save
            
        Returns:
            DocumentOntology instance with id set, or None on error
        """
        doc_id = doc_ontology.document_id
        logger.info(f"💾 [SAVE] Starting document ontology save for document_id={doc_id}")
        logger.debug(f"  → Ontology data: status={doc_ontology.status}, version={doc_ontology.version}, is_canonical={doc_ontology.is_canonical}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Convert specification dict to JSON string
                spec_json = json.dumps(doc_ontology.specification) if doc_ontology.specification else "{}"
                spec_size = len(spec_json)
                logger.debug(f"  → Specification JSON size: {spec_size} bytes")
                
                # Count entities and relationships for logging
                entities_count = len(doc_ontology.specification.get("entities", [])) if doc_ontology.specification else 0
                relationships_count = len(doc_ontology.specification.get("relationships", [])) if doc_ontology.specification else 0
                logger.debug(f"  → Ontology contains: {entities_count} entities, {relationships_count} relationships")
                
                # Convert boolean to int for is_canonical
                is_canonical_int = 1 if doc_ontology.is_canonical else 0
                
                logger.debug(f"  → Executing INSERT into document_ontologies table...")
                cur.execute(
                    INSERT_DOCUMENT_ONTOLOGY,
                    (
                        doc_ontology.document_id,
                        spec_json,
                        doc_ontology.status,
                        doc_ontology.version,
                        doc_ontology.proposed_by,
                        doc_ontology.reviewed_by,
                        doc_ontology.created_at,
                        doc_ontology.approved_at,
                        is_canonical_int,
                    ),
                )
                conn.commit()
                
                # Set the id on the ontology object
                ontology_id = cur.lastrowid
                doc_ontology.id = ontology_id
                logger.info(f"✅ [SAVE] Document ontology saved successfully: ontology_id={ontology_id}, document_id={doc_id}, status={doc_ontology.status}")
                logger.debug(f"  → Ontology ID {ontology_id} assigned to document {doc_id}")
                return doc_ontology
        except Exception as e:
            logger.error(f"❌ [SAVE] Failed to save document ontology for document_id={doc_id}: {e}", exc_info=True)
            logger.error(f"  → Error details: {type(e).__name__}: {str(e)}")
            return None
