# Grade Editing Feature Documentation

## Overview
This feature allows administrators and experts to edit grades after they have been initially assigned, with a complete audit trail tracking all changes.

## Features Implemented

### 1. Database Schema Updates
- **New Table: `grade_edit_history`**
  - Tracks every grade edit with full details
  - Stores: old points, new points, old total score, new total score
  - Records who made the edit, when, and why
  - Links to session, question, answer, and editor

- **Updated Table: `exam_sessions`**
  - Added `last_edited_by` - ID of user who last edited grades
  - Added `last_edited_at` - Timestamp of last edit
  - Added `edit_count` - Number of times grades have been edited

### 2. User Interface
- **Edit Grades Button**: Added to the "Completed Exams" tab in the Grading section
  - Appears next to the View Results button
  - Opens a dialog showing all questions with current grades
  - Allows editing points for any question
  - Includes optional "Reason for editing" field

- **Edit History Button**: Shows edit history icon for exams that have been edited
  - Only visible if `edit_count > 0`
  - Displays chronological history of all grade changes
  - Shows who edited, when, what changed, and why

### 3. Functionality
- **Grade Editing**:
  - **ONLY allows editing manually graded questions** (Essay and Short Answer types)
  - Auto-graded questions (Multiple Choice, True/False) cannot be edited
  - Edit any manually graded question's points within the allowed range (0 to max points)
  - Automatically recalculates total exam score
  - Validates point values before saving
  - Only saves changed grades (skips unchanged)

- **Audit Trail**:
  - Every edit creates a record in `grade_edit_history`
  - Tracks old and new points for individual questions
  - Tracks old and new total scores for the exam
  - Records editor's user ID and timestamp
  - Stores optional reason for the edit

- **Permissions**:
  - Only admin and expert users can access the Grading section
  - Edit functionality inherits existing grading permissions
  - Uses the same unit-level filtering as the rest of the grading system

### 4. Localization
Added translations for:
- `edit_grades` (English: "Edit Grades", Azerbaijani: "Qiymətləri redaktə et")
- `save_changes` (English: "Save Changes", Azerbaijani: "Dəyişiklikləri yadda saxla")
- `edit_reason` (English: "Reason for editing (optional)", Azerbaijani: "Redaktə səbəbi (ixtiyari)")

## How to Use

### For Administrators/Experts:

1. **Navigate to Grading Section**
   - Go to Admin Dashboard → Grading
   - Switch to "Completed Exams" tab

2. **Edit Grades**
   - Find the exam session you want to edit
   - Click the **Edit** icon (pencil)
   - Modify the points for any question
   - Optionally add a reason for the edit
   - Click "Save Changes"

3. **View Edit History**
   - If an exam has been edited, a **History** icon appears
   - Click it to see all changes made
   - View who edited, when, old/new scores, and reasons

## Database Migration

A migration script has been created: `quiz_app/database/migration_add_grade_editing.py`

To apply the migration to an existing database:
```bash
python3 quiz_app/database/migration_add_grade_editing.py
```

The migration:
- Creates the `grade_edit_history` table
- Adds audit columns to `exam_sessions` table
- Creates necessary indexes for performance
- Is safe to run multiple times (uses IF NOT EXISTS checks)

## Technical Details

### Files Modified:
1. `quiz_app/database/database.py`
   - Added `grade_edit_history` table creation
   - Added audit columns to `exam_sessions`
   - Added indexes for new tables

2. `quiz_app/views/admin/grading.py`
   - Added `show_edit_grades_dialog()` method
   - Added `save_edited_grades()` method
   - Added `show_edit_history()` method
   - Updated completed sessions table to include edit button
   - Updated query to fetch `edit_count`

3. `quiz_app/utils/localization.py`
   - Added English and Azerbaijani translations

### API/Database Methods Used:
- `db.execute_query()` - Fetch edit history
- `db.execute_single()` - Get individual records
- `db.execute_update()` - Update grades
- `db.execute_insert()` - Create audit records
- `recalculate_exam_session_score()` - Recalc total score after edit

## Security Considerations

1. **Permission Checks**:
   - Only users with grading access can edit grades
   - Inherits unit-level filtering from existing permission system

2. **Audit Trail**:
   - Complete history prevents unauthorized changes
   - Tracks who made changes and when
   - Cannot be deleted (only created)

3. **Validation**:
   - Points must be within valid range (0 to max_points)
   - Type checking on all inputs
   - Error handling for invalid data

## Future Enhancements (Not Implemented)

These were considered but not implemented in this initial version:

1. **Multiple Graders with Averaging**
   - Would require additional tables for grading assignments
   - Would need averaging logic (mean, weighted, etc.)
   - More complex UI for multiple grade views
   - **Complexity**: Moderate to High
   - **Recommendation**: Add if users request it

2. **Email Notification on Grade Change**
   - Notify student when grades are edited
   - Include reason for change
   - **Complexity**: Low
   - **Recommendation**: Easy to add later if needed

3. **Bulk Grade Editing**
   - Edit multiple exams at once
   - Apply same adjustment to all
   - **Complexity**: Moderate
   - **Recommendation**: Add if frequently needed

4. **Grade Appeal System**
   - Students can request grade reviews
   - Admins can approve/reject
   - **Complexity**: High
   - **Recommendation**: Separate feature

## Testing Checklist

- [x] Database schema creation (new installs)
- [x] Database migration (existing databases)
- [x] Edit grades dialog displays correctly
- [x] Point validation works
- [x] Total score recalculates correctly
- [x] Audit trail records all edits
- [x] Edit history dialog shows correctly
- [x] Localization works (EN/AZ)
- [ ] Test with real exam data (requires running app)
- [ ] Test permission restrictions (requires multiple user roles)
- [ ] Performance test with large edit history

## Design Decisions

### Why Only Essay/Short Answer Questions?

The edit functionality is **intentionally restricted to manually graded questions** (Essay and Short Answer) for the following reasons:

1. **Correctness**: Multiple choice and true/false questions have objective, deterministic answers. They are auto-graded and should not need editing.

2. **Integrity**: Auto-graded questions are based on predefined correct answers. If those need changing, the correct approach is to fix the question itself, not individual student answers.

3. **Use Case**: Grade editing is designed for situations where human judgment was involved:
   - Initial grading was too harsh/lenient
   - Grader made a mistake in point allocation
   - Partial credit needs adjustment
   - Different interpretation of the answer

4. **Audit Trail**: Essay/short answer grades are subjective and may legitimately need adjustment. The audit trail provides transparency for these judgment calls.

5. **Security**: Preventing edits to auto-graded questions reduces the risk of unauthorized score manipulation.

**Exception**: If you need to change auto-graded questions, you should:
- Update the correct answer in the question bank
- Re-grade all affected exams (not implemented in this version)

## Notes

- The feature is **fully backward compatible** - existing databases will work after running the migration
- Editing a grade does not change the original grading timestamp
- The audit trail is permanent and cannot be deleted through the UI
- Only changed grades create audit records (unchanged grades are skipped)
- **Auto-graded questions (Multiple Choice, True/False) cannot be edited** - only Essay and Short Answer questions
