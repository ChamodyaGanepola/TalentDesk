"""One-time / startup migration for CV Mongo documents (experience field naming)."""
from __future__ import annotations

from app.services.utils_experience import (
    MONGO_CV_LEGACY_FIELD_UNSET,
    EXPERIENCE_ARRAY_KEY,
    experience_for_storage,
)


def migrate_cv_documents_experience_field(collection) -> int:
    """
    Rename legacy internships → experience and drop old field names.
    Returns number of documents updated.
    """
    if collection is None:
        return 0

    legacy_keys = tuple(MONGO_CV_LEGACY_FIELD_UNSET.keys())
    query = {"$or": [{key: {"$exists": True}} for key in legacy_keys]}
    updated = 0

    for doc in collection.find(query):
        set_fields: dict = {}
        unset_fields: dict = {}

        legacy_list = doc.get("internships")
        if isinstance(legacy_list, list) and not doc.get(EXPERIENCE_ARRAY_KEY):
            set_fields[EXPERIENCE_ARRAY_KEY] = experience_for_storage(legacy_list)

        legacy_work = doc.get("work_experience")
        if (
            isinstance(legacy_work, list)
            and EXPERIENCE_ARRAY_KEY not in set_fields
            and not doc.get(EXPERIENCE_ARRAY_KEY)
        ):
            set_fields[EXPERIENCE_ARRAY_KEY] = experience_for_storage(legacy_work)

        if doc.get("batch_intern_label") and not doc.get("batch_experience_label"):
            set_fields["batch_experience_label"] = doc["batch_intern_label"]

        if "include_internships" in doc and "include_trainee_experience" not in doc:
            set_fields["include_trainee_experience"] = doc["include_internships"]

        for key in legacy_keys:
            if key in doc:
                unset_fields[key] = ""

        if not set_fields and not unset_fields:
            continue

        update: dict = {}
        if set_fields:
            update["$set"] = set_fields
        if unset_fields:
            update["$unset"] = unset_fields

        collection.update_one({"_id": doc["_id"]}, update)
        updated += 1

    return updated
