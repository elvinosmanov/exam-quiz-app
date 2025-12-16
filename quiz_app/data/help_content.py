"""
Help Content for Quiz Examination System
Organized by role: admin, examinee, and common sections
All text uses translation keys for localization support
"""

import flet as ft

HELP_CONTENT = {
    'admin': {
        'categories': [
            {
                'id': 'user_management',
                'title_key': 'help_user_mgmt',
                'icon': ft.icons.PEOPLE,
                'topics': ['create_user', 'edit_user', 'manage_roles', 'organizational_structure', 'activate_deactivate_users']
            },
            {
                'id': 'exam_management',
                'title_key': 'help_exam_mgmt',
                'icon': ft.icons.QUIZ,
                'topics': ['create_exam', 'assign_exam', 'exam_scheduling', 'exam_settings', 'multi_template_assignment', 'preset_templates', 'archived_assignments', 'pdf_delivery']
            },
            {
                'id': 'question_management',
                'title_key': 'help_questions',
                'icon': ft.icons.HELP,
                'topics': ['create_question', 'question_types', 'add_question_images', 'bulk_import_questions', 'question_difficulty', 'question_explanations']
            },
            {
                'id': 'grading',
                'title_key': 'help_grading',
                'icon': ft.icons.GRADING,
                'topics': ['manual_grading', 'view_submissions', 'release_results', 'grading_status']
            },
            {
                'id': 'reports',
                'title_key': 'help_reports',
                'icon': ft.icons.ANALYTICS,
                'topics': ['view_statistics', 'export_results', 'pdf_reports', 'user_performance']
            },
            {
                'id': 'settings',
                'title_key': 'help_settings',
                'icon': ft.icons.SETTINGS,
                'topics': ['change_language', 'database_backup', 'system_settings', 'email_templates', 'organizational_structure']
            }
        ],
        'topics': {
            # User Management Topics
            'create_user': {
                'title_key': 'help_create_user_title',
                'content_key': 'help_create_user_desc',
                'steps': [
                    'help_create_user_step1',
                    'help_create_user_step2',
                    'help_create_user_step3',
                    'help_create_user_step4',
                    'help_create_user_step5'
                ],
                'tips': [
                    'help_create_user_tip1',
                    'help_create_user_tip2',
                    'help_create_user_tip3'
                ],
                'related': ['edit_user', 'manage_roles', 'activate_deactivate_users']
            },
            'edit_user': {
                'title_key': 'help_edit_user_title',
                'content_key': 'help_edit_user_desc',
                'steps': [
                    'help_edit_user_step1',
                    'help_edit_user_step2',
                    'help_edit_user_step3',
                    'help_edit_user_step4'
                ],
                'tips': [
                    'help_edit_user_tip1',
                    'help_edit_user_tip2'
                ],
                'related': ['create_user', 'activate_deactivate_users']
            },
            'manage_roles': {
                'title_key': 'help_manage_roles_title',
                'content_key': 'help_manage_roles_desc',
                'steps': [
                    'help_manage_roles_step1',
                    'help_manage_roles_step2',
                    'help_manage_roles_step3'
                ],
                'tips': [
                    'help_manage_roles_tip1',
                    'help_manage_roles_tip2',
                    'help_manage_roles_tip3'
                ],
                'related': ['create_user', 'organizational_structure']
            },
            'organizational_structure': {
                'title_key': 'help_org_structure_title',
                'content_key': 'help_org_structure_desc',
                'steps': [
                    'help_org_structure_step1',
                    'help_org_structure_step2',
                    'help_org_structure_step3'
                ],
                'tips': [
                    'help_org_structure_tip1',
                    'help_org_structure_tip2'
                ],
                'related': ['manage_roles', 'create_user']
            },
            'activate_deactivate_users': {
                'title_key': 'help_activate_users_title',
                'content_key': 'help_activate_users_desc',
                'steps': [
                    'help_activate_users_step1',
                    'help_activate_users_step2',
                    'help_activate_users_step3'
                ],
                'tips': [
                    'help_activate_users_tip1',
                    'help_activate_users_tip2'
                ],
                'related': ['edit_user']
            },

            # Exam Management Topics
            'create_exam': {
                'title_key': 'help_create_exam_title',
                'content_key': 'help_create_exam_desc',
                'steps': [
                    'help_create_exam_step1',
                    'help_create_exam_step2',
                    'help_create_exam_step3',
                    'help_create_exam_step4',
                    'help_create_exam_step5',
                    'help_create_exam_step6'
                ],
                'tips': [
                    'help_create_exam_tip1',
                    'help_create_exam_tip2',
                    'help_create_exam_tip3'
                ],
                'related': ['assign_exam', 'exam_settings', 'question_difficulty']
            },
            'assign_exam': {
                'title_key': 'help_assign_exam_title',
                'content_key': 'help_assign_exam_desc',
                'steps': [
                    'help_assign_exam_step1',
                    'help_assign_exam_step2',
                    'help_assign_exam_step3',
                    'help_assign_exam_step4',
                    'help_assign_exam_step5'
                ],
                'tips': [
                    'help_assign_exam_tip1',
                    'help_assign_exam_tip2',
                    'help_assign_exam_tip3'
                ],
                'related': ['create_exam', 'exam_scheduling', 'multi_template_assignment']
            },
            'exam_scheduling': {
                'title_key': 'help_exam_scheduling_title',
                'content_key': 'help_exam_scheduling_desc',
                'steps': [
                    'help_exam_scheduling_step1',
                    'help_exam_scheduling_step2',
                    'help_exam_scheduling_step3'
                ],
                'tips': [
                    'help_exam_scheduling_tip1',
                    'help_exam_scheduling_tip2'
                ],
                'related': ['assign_exam']
            },
            'exam_settings': {
                'title_key': 'help_exam_settings_title',
                'content_key': 'help_exam_settings_desc',
                'steps': [
                    'help_exam_settings_step1',
                    'help_exam_settings_step2',
                    'help_exam_settings_step3',
                    'help_exam_settings_step4'
                ],
                'tips': [
                    'help_exam_settings_tip1',
                    'help_exam_settings_tip2'
                ],
                'related': ['create_exam']
            },
            'multi_template_assignment': {
                'title_key': 'help_multi_template_title',
                'content_key': 'help_multi_template_desc',
                'steps': [
                    'help_multi_template_step1',
                    'help_multi_template_step2',
                    'help_multi_template_step3',
                    'help_multi_template_step4'
                ],
                'tips': [
                    'help_multi_template_tip1',
                    'help_multi_template_tip2'
                ],
                'related': ['assign_exam', 'exam_scheduling']
            },
            'preset_templates': {
                'title_key': 'help_preset_templates_title',
                'content_key': 'help_preset_templates_desc',
                'steps': [
                    'help_preset_templates_step1',
                    'help_preset_templates_step2',
                    'help_preset_templates_step3',
                    'help_preset_templates_step4'
                ],
                'tips': [
                    'help_preset_templates_tip1',
                    'help_preset_templates_tip2'
                ],
                'related': ['multi_template_assignment', 'assign_exam']
            },
            'archived_assignments': {
                'title_key': 'help_archived_assignments_title',
                'content_key': 'help_archived_assignments_desc',
                'steps': [
                    'help_archived_assignments_step1',
                    'help_archived_assignments_step2',
                    'help_archived_assignments_step3'
                ],
                'tips': [
                    'help_archived_assignments_tip1'
                ],
                'related': ['assign_exam']
            },
            'pdf_delivery': {
                'title_key': 'help_pdf_delivery_title',
                'content_key': 'help_pdf_delivery_desc',
                'steps': [
                    'help_pdf_delivery_step1',
                    'help_pdf_delivery_step2',
                    'help_pdf_delivery_step3',
                    'help_pdf_delivery_step4'
                ],
                'tips': [
                    'help_pdf_delivery_tip1',
                    'help_pdf_delivery_tip2'
                ],
                'related': ['assign_exam', 'exam_settings']
            },

            # Question Management Topics
            'create_question': {
                'title_key': 'help_create_question_title',
                'content_key': 'help_create_question_desc',
                'steps': [
                    'help_create_question_step1',
                    'help_create_question_step2',
                    'help_create_question_step3',
                    'help_create_question_step4',
                    'help_create_question_step5'
                ],
                'tips': [
                    'help_create_question_tip1',
                    'help_create_question_tip2',
                    'help_create_question_tip3'
                ],
                'related': ['question_types', 'add_question_images', 'question_difficulty']
            },
            'question_types': {
                'title_key': 'help_question_types_title',
                'content_key': 'help_question_types_desc',
                'steps': [
                    'help_question_types_step1',
                    'help_question_types_step2',
                    'help_question_types_step3',
                    'help_question_types_step4'
                ],
                'tips': [
                    'help_question_types_tip1',
                    'help_question_types_tip2'
                ],
                'related': ['create_question', 'manual_grading']
            },
            'add_question_images': {
                'title_key': 'help_question_images_title',
                'content_key': 'help_question_images_desc',
                'steps': [
                    'help_question_images_step1',
                    'help_question_images_step2',
                    'help_question_images_step3'
                ],
                'tips': [
                    'help_question_images_tip1',
                    'help_question_images_tip2'
                ],
                'related': ['create_question']
            },
            'bulk_import_questions': {
                'title_key': 'help_bulk_import_questions_title',
                'content_key': 'help_bulk_import_questions_desc',
                'steps': [
                    'help_bulk_import_questions_step1',
                    'help_bulk_import_questions_step2',
                    'help_bulk_import_questions_step3',
                    'help_bulk_import_questions_step4'
                ],
                'tips': [
                    'help_bulk_import_questions_tip1',
                    'help_bulk_import_questions_tip2',
                    'help_bulk_import_questions_tip3'
                ],
                'related': ['create_question', 'question_types']
            },
            'question_difficulty': {
                'title_key': 'help_question_difficulty_title',
                'content_key': 'help_question_difficulty_desc',
                'steps': [
                    'help_question_difficulty_step1',
                    'help_question_difficulty_step2',
                    'help_question_difficulty_step3'
                ],
                'tips': [
                    'help_question_difficulty_tip1',
                    'help_question_difficulty_tip2'
                ],
                'related': ['create_question', 'create_exam']
            },
            'question_explanations': {
                'title_key': 'help_question_explanations_title',
                'content_key': 'help_question_explanations_desc',
                'steps': [
                    'help_question_explanations_step1',
                    'help_question_explanations_step2',
                    'help_question_explanations_step3'
                ],
                'tips': [
                    'help_question_explanations_tip1'
                ],
                'related': ['create_question']
            },

            # Grading Topics
            'manual_grading': {
                'title_key': 'help_manual_grading_title',
                'content_key': 'help_manual_grading_desc',
                'steps': [
                    'help_manual_grading_step1',
                    'help_manual_grading_step2',
                    'help_manual_grading_step3',
                    'help_manual_grading_step4',
                    'help_manual_grading_step5'
                ],
                'tips': [
                    'help_manual_grading_tip1',
                    'help_manual_grading_tip2'
                ],
                'related': ['view_submissions', 'release_results', 'question_types']
            },
            'view_submissions': {
                'title_key': 'help_view_submissions_title',
                'content_key': 'help_view_submissions_desc',
                'steps': [
                    'help_view_submissions_step1',
                    'help_view_submissions_step2',
                    'help_view_submissions_step3'
                ],
                'tips': [
                    'help_view_submissions_tip1'
                ],
                'related': ['manual_grading', 'grading_status']
            },
            'release_results': {
                'title_key': 'help_release_results_title',
                'content_key': 'help_release_results_desc',
                'steps': [
                    'help_release_results_step1',
                    'help_release_results_step2',
                    'help_release_results_step3'
                ],
                'tips': [
                    'help_release_results_tip1',
                    'help_release_results_tip2'
                ],
                'related': ['manual_grading', 'grading_status']
            },
            'grading_status': {
                'title_key': 'help_grading_status_title',
                'content_key': 'help_grading_status_desc',
                'steps': [
                    'help_grading_status_step1',
                    'help_grading_status_step2',
                    'help_grading_status_step3'
                ],
                'tips': [
                    'help_grading_status_tip1'
                ],
                'related': ['manual_grading', 'release_results']
            },

            # Reports Topics
            'view_statistics': {
                'title_key': 'help_view_statistics_title',
                'content_key': 'help_view_statistics_desc',
                'steps': [
                    'help_view_statistics_step1',
                    'help_view_statistics_step2',
                    'help_view_statistics_step3'
                ],
                'tips': [
                    'help_view_statistics_tip1'
                ],
                'related': ['export_results', 'user_performance']
            },
            'export_results': {
                'title_key': 'help_export_results_title',
                'content_key': 'help_export_results_desc',
                'steps': [
                    'help_export_results_step1',
                    'help_export_results_step2',
                    'help_export_results_step3'
                ],
                'tips': [
                    'help_export_results_tip1',
                    'help_export_results_tip2'
                ],
                'related': ['view_statistics']
            },
            'pdf_reports': {
                'title_key': 'help_pdf_reports_title',
                'content_key': 'help_pdf_reports_desc',
                'steps': [
                    'help_pdf_reports_step1',
                    'help_pdf_reports_step2',
                    'help_pdf_reports_step3'
                ],
                'tips': [
                    'help_pdf_reports_tip1',
                    'help_pdf_reports_tip2'
                ],
                'related': ['view_statistics', 'export_results']
            },
            'user_performance': {
                'title_key': 'help_user_performance_title',
                'content_key': 'help_user_performance_desc',
                'steps': [
                    'help_user_performance_step1',
                    'help_user_performance_step2',
                    'help_user_performance_step3',
                    'help_user_performance_step4'
                ],
                'tips': [
                    'help_user_performance_tip1'
                ],
                'related': ['view_statistics', 'export_results']
            },

            # Settings Topics
            'change_language': {
                'title_key': 'help_change_language_title',
                'content_key': 'help_change_language_desc',
                'steps': [
                    'help_change_language_step1',
                    'help_change_language_step2',
                    'help_change_language_step3'
                ],
                'tips': [
                    'help_change_language_tip1'
                ],
                'related': ['system_settings']
            },
            'database_backup': {
                'title_key': 'help_database_backup_title',
                'content_key': 'help_database_backup_desc',
                'steps': [
                    'help_database_backup_step1',
                    'help_database_backup_step2',
                    'help_database_backup_step3',
                    'help_database_backup_step4'
                ],
                'tips': [
                    'help_database_backup_tip1',
                    'help_database_backup_tip2'
                ],
                'related': ['system_settings']
            },
            'system_settings': {
                'title_key': 'help_system_settings_title',
                'content_key': 'help_system_settings_desc',
                'steps': [
                    'help_system_settings_step1',
                    'help_system_settings_step2',
                    'help_system_settings_step3'
                ],
                'tips': [
                    'help_system_settings_tip1'
                ],
                'related': ['change_language', 'database_backup']
            },
            'email_templates': {
                'title_key': 'help_email_templates_title',
                'content_key': 'help_email_templates_desc',
                'steps': [
                    'help_email_templates_step1',
                    'help_email_templates_step2',
                    'help_email_templates_step3',
                    'help_email_templates_step4'
                ],
                'tips': [
                    'help_email_templates_tip1',
                    'help_email_templates_tip2'
                ],
                'related': ['system_settings']
            },
            'organizational_structure': {
                'title_key': 'help_org_structure_manage_title',
                'content_key': 'help_org_structure_manage_desc',
                'steps': [
                    'help_org_structure_manage_step1',
                    'help_org_structure_manage_step2',
                    'help_org_structure_manage_step3',
                    'help_org_structure_manage_step4'
                ],
                'tips': [
                    'help_org_structure_manage_tip1',
                    'help_org_structure_manage_tip2'
                ],
                'related': ['create_user', 'system_settings']
            }
        }
    },

    'examinee': {
        'categories': [
            {
                'id': 'taking_exams',
                'title_key': 'help_taking_exams',
                'icon': ft.icons.ASSIGNMENT,
                'topics': ['find_exams', 'start_exam', 'navigate_questions', 'mark_for_review', 'exam_timer', 'submit_exam', 'attempt_limits']
            },
            {
                'id': 'viewing_results',
                'title_key': 'help_my_results',
                'icon': ft.icons.ASSESSMENT,
                'topics': ['access_results', 'score_breakdown', 'review_answers', 'pending_grading']
            }
        ],
        'topics': {
            # Taking Exams Topics
            'find_exams': {
                'title_key': 'help_find_exams_title',
                'content_key': 'help_find_exams_desc',
                'steps': [
                    'help_find_exams_step1',
                    'help_find_exams_step2',
                    'help_find_exams_step3'
                ],
                'tips': [
                    'help_find_exams_tip1',
                    'help_find_exams_tip2'
                ],
                'related': ['start_exam']
            },
            'start_exam': {
                'title_key': 'help_start_exam_title',
                'content_key': 'help_start_exam_desc',
                'steps': [
                    'help_start_exam_step1',
                    'help_start_exam_step2',
                    'help_start_exam_step3',
                    'help_start_exam_step4'
                ],
                'tips': [
                    'help_start_exam_tip1',
                    'help_start_exam_tip2',
                    'help_start_exam_tip3'
                ],
                'related': ['find_exams', 'navigate_questions', 'exam_timer']
            },
            'navigate_questions': {
                'title_key': 'help_navigate_questions_title',
                'content_key': 'help_navigate_questions_desc',
                'steps': [
                    'help_navigate_questions_step1',
                    'help_navigate_questions_step2',
                    'help_navigate_questions_step3',
                    'help_navigate_questions_step4'
                ],
                'tips': [
                    'help_navigate_questions_tip1',
                    'help_navigate_questions_tip2'
                ],
                'related': ['mark_for_review', 'submit_exam']
            },
            'mark_for_review': {
                'title_key': 'help_mark_review_title',
                'content_key': 'help_mark_review_desc',
                'steps': [
                    'help_mark_review_step1',
                    'help_mark_review_step2',
                    'help_mark_review_step3'
                ],
                'tips': [
                    'help_mark_review_tip1',
                    'help_mark_review_tip2'
                ],
                'related': ['navigate_questions', 'submit_exam']
            },
            'exam_timer': {
                'title_key': 'help_exam_timer_title',
                'content_key': 'help_exam_timer_desc',
                'steps': [
                    'help_exam_timer_step1',
                    'help_exam_timer_step2',
                    'help_exam_timer_step3'
                ],
                'tips': [
                    'help_exam_timer_tip1',
                    'help_exam_timer_tip2',
                    'help_exam_timer_tip3'
                ],
                'related': ['start_exam', 'submit_exam']
            },
            'submit_exam': {
                'title_key': 'help_submit_exam_title',
                'content_key': 'help_submit_exam_desc',
                'steps': [
                    'help_submit_exam_step1',
                    'help_submit_exam_step2',
                    'help_submit_exam_step3',
                    'help_submit_exam_step4'
                ],
                'tips': [
                    'help_submit_exam_tip1',
                    'help_submit_exam_tip2'
                ],
                'related': ['navigate_questions', 'access_results']
            },
            'attempt_limits': {
                'title_key': 'help_attempt_limits_title',
                'content_key': 'help_attempt_limits_desc',
                'steps': [
                    'help_attempt_limits_step1',
                    'help_attempt_limits_step2',
                    'help_attempt_limits_step3'
                ],
                'tips': [
                    'help_attempt_limits_tip1'
                ],
                'related': ['start_exam', 'submit_exam']
            },

            # Viewing Results Topics
            'access_results': {
                'title_key': 'help_access_results_title',
                'content_key': 'help_access_results_desc',
                'steps': [
                    'help_access_results_step1',
                    'help_access_results_step2',
                    'help_access_results_step3'
                ],
                'tips': [
                    'help_access_results_tip1'
                ],
                'related': ['score_breakdown', 'review_answers']
            },
            'score_breakdown': {
                'title_key': 'help_score_breakdown_title',
                'content_key': 'help_score_breakdown_desc',
                'steps': [
                    'help_score_breakdown_step1',
                    'help_score_breakdown_step2',
                    'help_score_breakdown_step3'
                ],
                'tips': [
                    'help_score_breakdown_tip1',
                    'help_score_breakdown_tip2'
                ],
                'related': ['access_results', 'review_answers']
            },
            'review_answers': {
                'title_key': 'help_review_answers_title',
                'content_key': 'help_review_answers_desc',
                'steps': [
                    'help_review_answers_step1',
                    'help_review_answers_step2',
                    'help_review_answers_step3'
                ],
                'tips': [
                    'help_review_answers_tip1',
                    'help_review_answers_tip2'
                ],
                'related': ['score_breakdown', 'pending_grading']
            },
            'pending_grading': {
                'title_key': 'help_pending_grading_title',
                'content_key': 'help_pending_grading_desc',
                'steps': [
                    'help_pending_grading_step1',
                    'help_pending_grading_step2',
                    'help_pending_grading_step3'
                ],
                'tips': [
                    'help_pending_grading_tip1'
                ],
                'related': ['access_results', 'review_answers']
            }
        }
    },

    'common': {
        'categories': [
            {
                'id': 'account',
                'title_key': 'help_account',
                'icon': ft.icons.ACCOUNT_CIRCLE,
                'topics': ['update_profile', 'change_password', 'language_settings']
            },
            {
                'id': 'login_auth',
                'title_key': 'help_login',
                'icon': ft.icons.LOGIN,
                'topics': ['first_login', 'password_reset', 'session_timeout']
            },
            {
                'id': 'navigation',
                'title_key': 'help_navigation',
                'icon': ft.icons.DASHBOARD,
                'topics': ['dashboard_overview', 'sidebar_usage', 'quick_actions']
            },
            {
                'id': 'troubleshooting',
                'title_key': 'help_troubleshooting',
                'icon': ft.icons.BUILD,
                'topics': ['exam_wont_start', 'timer_issues', 'results_unavailable', 'login_issues']
            }
        ],
        'topics': {
            # Account Topics
            'update_profile': {
                'title_key': 'help_update_profile_title',
                'content_key': 'help_update_profile_desc',
                'steps': [
                    'help_update_profile_step1',
                    'help_update_profile_step2',
                    'help_update_profile_step3',
                    'help_update_profile_step4'
                ],
                'tips': [
                    'help_update_profile_tip1'
                ],
                'related': ['change_password', 'language_settings']
            },
            'change_password': {
                'title_key': 'help_change_password_title',
                'content_key': 'help_change_password_desc',
                'steps': [
                    'help_change_password_step1',
                    'help_change_password_step2',
                    'help_change_password_step3',
                    'help_change_password_step4',
                    'help_change_password_step5'
                ],
                'tips': [
                    'help_change_password_tip1',
                    'help_change_password_tip2',
                    'help_change_password_tip3'
                ],
                'related': ['update_profile', 'first_login']
            },
            'language_settings': {
                'title_key': 'help_language_settings_title',
                'content_key': 'help_language_settings_desc',
                'steps': [
                    'help_language_settings_step1',
                    'help_language_settings_step2',
                    'help_language_settings_step3'
                ],
                'tips': [
                    'help_language_settings_tip1'
                ],
                'related': ['update_profile']
            },

            # Login & Authentication Topics
            'first_login': {
                'title_key': 'help_first_login_title',
                'content_key': 'help_first_login_desc',
                'steps': [
                    'help_first_login_step1',
                    'help_first_login_step2',
                    'help_first_login_step3',
                    'help_first_login_step4'
                ],
                'tips': [
                    'help_first_login_tip1',
                    'help_first_login_tip2'
                ],
                'related': ['change_password', 'password_reset']
            },
            'password_reset': {
                'title_key': 'help_password_reset_title',
                'content_key': 'help_password_reset_desc',
                'steps': [
                    'help_password_reset_step1',
                    'help_password_reset_step2',
                    'help_password_reset_step3'
                ],
                'tips': [
                    'help_password_reset_tip1'
                ],
                'related': ['first_login', 'login_issues']
            },
            'session_timeout': {
                'title_key': 'help_session_timeout_title',
                'content_key': 'help_session_timeout_desc',
                'steps': [
                    'help_session_timeout_step1',
                    'help_session_timeout_step2',
                    'help_session_timeout_step3'
                ],
                'tips': [
                    'help_session_timeout_tip1',
                    'help_session_timeout_tip2'
                ],
                'related': ['login_issues']
            },

            # Navigation Topics
            'dashboard_overview': {
                'title_key': 'help_dashboard_overview_title',
                'content_key': 'help_dashboard_overview_desc',
                'steps': [
                    'help_dashboard_overview_step1',
                    'help_dashboard_overview_step2',
                    'help_dashboard_overview_step3'
                ],
                'tips': [
                    'help_dashboard_overview_tip1'
                ],
                'related': ['sidebar_usage', 'quick_actions']
            },
            'sidebar_usage': {
                'title_key': 'help_sidebar_usage_title',
                'content_key': 'help_sidebar_usage_desc',
                'steps': [
                    'help_sidebar_usage_step1',
                    'help_sidebar_usage_step2',
                    'help_sidebar_usage_step3'
                ],
                'tips': [
                    'help_sidebar_usage_tip1'
                ],
                'related': ['dashboard_overview']
            },
            'quick_actions': {
                'title_key': 'help_quick_actions_title',
                'content_key': 'help_quick_actions_desc',
                'steps': [
                    'help_quick_actions_step1',
                    'help_quick_actions_step2',
                    'help_quick_actions_step3'
                ],
                'tips': [
                    'help_quick_actions_tip1'
                ],
                'related': ['dashboard_overview', 'sidebar_usage']
            },

            # Troubleshooting Topics
            'exam_wont_start': {
                'title_key': 'help_exam_wont_start_title',
                'content_key': 'help_exam_wont_start_desc',
                'steps': [
                    'help_exam_wont_start_step1',
                    'help_exam_wont_start_step2',
                    'help_exam_wont_start_step3',
                    'help_exam_wont_start_step4'
                ],
                'tips': [
                    'help_exam_wont_start_tip1'
                ],
                'related': ['timer_issues', 'login_issues']
            },
            'timer_issues': {
                'title_key': 'help_timer_issues_title',
                'content_key': 'help_timer_issues_desc',
                'steps': [
                    'help_timer_issues_step1',
                    'help_timer_issues_step2',
                    'help_timer_issues_step3'
                ],
                'tips': [
                    'help_timer_issues_tip1'
                ],
                'related': ['exam_wont_start', 'results_unavailable']
            },
            'results_unavailable': {
                'title_key': 'help_results_unavailable_title',
                'content_key': 'help_results_unavailable_desc',
                'steps': [
                    'help_results_unavailable_step1',
                    'help_results_unavailable_step2',
                    'help_results_unavailable_step3'
                ],
                'tips': [
                    'help_results_unavailable_tip1'
                ],
                'related': ['pending_grading']
            },
            'login_issues': {
                'title_key': 'help_login_issues_title',
                'content_key': 'help_login_issues_desc',
                'steps': [
                    'help_login_issues_step1',
                    'help_login_issues_step2',
                    'help_login_issues_step3',
                    'help_login_issues_step4'
                ],
                'tips': [
                    'help_login_issues_tip1',
                    'help_login_issues_tip2'
                ],
                'related': ['change_password', 'exam_wont_start']
            }
        }
    }
}
