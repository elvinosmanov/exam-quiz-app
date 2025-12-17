from typing import List, Dict, Any


def deduplicate_templates_by_exam_id(templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate exam templates by exam_id while preserving original order.

    This is used as a safety net for legacy data where assignment_exam_templates
    might contain multiple rows for the same (assignment_id, exam_id) pair.
    The first occurrence is kept, subsequent duplicates are discarded.
    """
    seen_exam_ids = set()
    unique_templates: List[Dict[str, Any]] = []

    for tpl in templates:
        # Defensive: handle both 'id' and 'exam_id' keys, depending on query aliasing
        exam_id = tpl.get('exam_id', tpl.get('id'))
        if exam_id is None:
            unique_templates.append(tpl)
            continue

        if exam_id in seen_exam_ids:
            continue

        seen_exam_ids.add(exam_id)
        unique_templates.append(tpl)

    return unique_templates


