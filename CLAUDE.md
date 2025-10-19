# Quiz Examination System

A comprehensive, enterprise-grade quiz examination system built with Python and Flet framework. This application provides secure, user-friendly interfaces for both administrators and examinees with role-based access control.

## Features

### 🔐 Authentication & Security
- Secure user authentication with bcrypt password hashing
- Role-based access control (Admin/Examinee)
- Session management with automatic timeout
- Audit logging for all user actions

### 👨‍💼 Admin Dashboard
- **User Management**: Create, edit, and manage user accounts
- **Exam Management**: Create and configure exams with customizable settings
- **Question Bank**: Manage questions with multiple question types
- **Bulk Import**: Import questions from CSV/Excel files
- **Reports & Analytics**: View system statistics and user performance
- **Real-time Dashboard**: Monitor system activity and key metrics

### 👨‍🎓 Examinee Interface
- **Available Exams**: View and start available examinations
- **Exam Taking**: ✅ Full exam interface with timer and navigation
- **Results History**: View past exam results and performance
- **Profile Management**: Update personal information and passwords

### 📊 Question Types Supported
- ✅ Multiple Choice Questions (fully implemented)
- ✅ True/False Questions (fully implemented)
- ✅ Short Answer Questions (fully implemented)
- ✅ Essay Questions (fully implemented)

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python3 test_db.py
```

This will:
- Create the SQLite database with all required tables
- Create a default admin user
- Create sample data for testing
- Verify the setup

### 3. Run the Application
```bash
python3 main.py
```

or alternatively:
```bash
python3 run.py
```

## Default Credentials

### Admin Account
- **Username**: admin
- **Password**: admin123

### Test User Account
- **Username**: testuser
- **Password**: testpass123

**⚠️ Important**: Change the default admin password after first login!

## Project Structure

```
quiz_app/
├── 📄 main.py                 # Application entry point
├── 📄 run.py                  # Alternative entry point
├── 📄 requirements.txt        # Python dependencies
├── 📄 test_db.py             # Database initialization script
├── 📄 quiz_app.db            # SQLite database (created after setup)
└── 📁 quiz_app/
    ├── 📄 config.py          # Application configuration
    ├── 📁 assets/
    │   └── 📁 images/        # Application images and backgrounds
    ├── 📁 database/
    │   ├── 📄 database.py    # Database models and operations
    │   ├── 📄 migration_001_question_types.py
    │   └── 📄 migration_remove_categories.py
    ├── 📁 utils/
    │   ├── 📄 auth.py        # Authentication utilities
    │   ├── 📄 session.py     # Session management
    │   ├── 📄 bulk_import.py # Bulk import functionality
    │   └── 📄 logging_config.py # Audit logging
    ├── 📁 models/            # Data models (reserved for future use)
    ├── 📁 controllers/       # Business logic (reserved for future use)
    └── 📁 views/
        ├── 📁 auth/          # Login and authentication views
        ├── 📁 admin/         # Admin dashboard views
        ├── 📁 common/        # Shared UI components
        └── 📁 examinee/      # Examinee dashboard views
```

## ✅ Implementation Status (90% Complete)

### ✅ Phase 1: Foundation (100% Complete)
- [x] Project structure and dependencies
- [x] SQLite database with comprehensive schema (8 tables)
- [x] User authentication and session management
- [x] Role-based access control (Admin/Examinee)
- [x] Security with bcrypt password hashing
- [x] Audit logging system

### ✅ Phase 2: Admin Interface (100% Complete)
- [x] Modern admin dashboard with statistics
- [x] User management (CRUD operations with search/filter)
- [x] Exam management with full configuration
- [x] Question management with 4 question types
- [x] Bulk question import from CSV/Excel
- [x] Question bank with images support
- [x] Grading and result management

### ✅ Phase 3: Examinee Interface (100% Complete)
- [x] Clean examinee dashboard
- [x] Available exams listing with status
- [x] Results history and performance tracking
- [x] Profile management and password updates

### ✅ Phase 4: Exam Taking System (95% Complete)
- [x] Full exam interface with timer
- [x] Question navigation and review
- [x] Auto-save functionality
- [x] Support for all question types
- [x] Automatic grading system
- [x] Result calculation and storage
- [x] Progress tracking during exam
- [ ] Advanced anti-cheating measures (planned)

### 🚧 Phase 5: Advanced Features (30% Complete)
- [x] Basic reporting and analytics
- [x] Database backup support
- [ ] PDF report generation (planned)
- [ ] Email notifications (planned)
- [ ] Certificate generation (planned)
- [ ] Advanced analytics dashboard (planned)

## 🗄️ Database Schema

The application uses SQLite with 8 comprehensive tables:

- **users**: User accounts, profiles, roles, and authentication data
- **exams**: Exam configurations, settings, duration, and scheduling
- **questions**: Question bank with 4 types, images, and explanations
- **question_options**: Multiple choice options with correct answers
- **exam_sessions**: User exam attempts, scores, and completion tracking
- **user_answers**: Individual question responses and time tracking
- **exam_permissions**: User-specific exam access and scheduling
- **audit_log**: Comprehensive system activity and security tracking

## Configuration

Key settings can be modified in `quiz_app/config.py`:

- Database path
- Session timeout duration
- File upload settings
- UI color scheme
- Security settings

## Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **Session Management**: Automatic session timeout and validation
- **Input Validation**: Prevents SQL injection and XSS attacks
- **Audit Logging**: Comprehensive logging of all user actions
- **Role-based Access**: Strict separation between admin and examinee functions

## 🎯 What Actually Works (Tested & Verified)

### ✅ Authentication System
- **Login/Logout**: Secure authentication with bcrypt
- **Session Management**: Automatic timeout and validation
- **Role-based Access**: Admin and Examinee dashboards
- **Password Security**: Strong hashing and validation

### ✅ Admin Features (100% Functional)
- **Dashboard**: Real-time statistics and system overview
- **User Management**: Create, edit, activate/deactivate users with search
- **Exam Creation**: Full exam configuration with all settings
- **Question Management**: All 4 question types with image support
- **Bulk Import**: CSV/Excel question import with validation
- **Grading System**: Automatic and manual grading capabilities

### ✅ Examinee Features (100% Functional)
- **Dashboard**: Clean interface with exam status
- **Available Exams**: View and filter available examinations
- **Exam Taking**: Complete exam interface with timer and navigation
- **Results**: View detailed exam results and history
- **Profile**: Update personal information and passwords

### ✅ Exam System (95% Functional)
- **Timer**: Countdown timer with visual warnings
- **Navigation**: Question-by-question navigation with review
- **Auto-save**: Answers automatically saved
- **All Question Types**: Multiple choice, True/False, Short answer, Essay
- **Grading**: Automatic scoring and result calculation
- **Progress Tracking**: Real-time exam progress indicators

### ✅ Technical Features
- **Database**: All CRUD operations working perfectly
- **File Handling**: Image uploads and management
- **Security**: Audit logging and session management
- **UI/UX**: Modern Material Design 3 interface

## Usage Guidelines

### For Administrators
1. **Login**: Use admin/admin123 credentials
2. **Create Users**: Add examinees via User Management
3. **Create Exams**: Set up exams with duration and settings
4. **Add Questions**: Manually add or bulk import questions
5. **Monitor**: View real-time dashboard statistics

### For Examinees
1. **Login**: Use provided credentials (testuser/testpass123)
2. **View Exams**: Check available examinations
3. **Take Exams**: Complete exams with timer interface
4. **View Results**: Check scores and performance history
5. **Update Profile**: Manage personal information

## 🔧 Areas for Improvement

### Minor Issues Identified
- **Anti-cheating**: Basic security implemented, advanced measures planned
- **Email Notifications**: Framework ready, SMTP integration needed
- **PDF Reports**: Basic reporting works, PDF generation planned
- **Certificate Generation**: Not yet implemented
- **Advanced Analytics**: Basic stats available, detailed analytics planned

### Future Enhancements
- **Multi-language Support**: Currently English only
- **Mobile Responsiveness**: Desktop-optimized, mobile improvements planned
- **Bulk User Import**: Manual user creation only
- **Advanced Question Types**: Code evaluation, drag-drop planned
- **Integration APIs**: REST API for external systems planned

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure all dependencies are installed via `pip install -r requirements.txt`
2. **Database Error**: Run `python test_db.py` to reinitialize the database
3. **Permission Error**: Check file permissions for the database file
4. **Module Not Found**: Ensure you're running from the project root directory

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify the database exists and is accessible
3. Ensure all dependencies are properly installed
4. Review the audit logs for any security issues

## Development Notes

### Running Tests
```bash
python test_db.py
```

### Development Mode
The application is configured for development with:
- Debug logging enabled
- Detailed error messages
- Default test data

### Production Deployment
For production use:
1. Change default passwords
2. Update SECRET_KEY in config.py
3. Configure proper backup procedures
4. Set up SSL/TLS encryption
5. Review and adjust security settings

## Flet Framework Technical Notes

This section documents important technical knowledge about working with the Flet framework to prevent common issues and ensure consistent solutions.

### 🐛 **UserControl Expand Issue (CRITICAL)**

**Problem:** The `expand=True` property doesn't work properly when used inside `UserControl` classes in Flet framework.

**Symptoms:**
- Containers don't expand to fill available space
- Background images only cover partial window area (e.g., 60% width with gray areas)
- Layout appears to have fixed dimensions instead of responsive sizing
- Container behaves as if `width` and `height` are set to 0

**Root Cause:** This is a known bug in Flet framework documented in [GitHub Issue #2565](https://github.com/flet-dev/flet/issues/2565).

**✅ Solution (Official Workaround):**

Add `self.expand = True` to the UserControl constructor:

```python
class MyUserControl(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.expand = True  # ← CRITICAL: Fix for UserControl expand issue
        
    def build(self):
        return ft.Container(
            expand=True,  # This will now work properly
            # ... rest of container properties
        )
```

### 🖼️ **Full-Screen Background Images**

**Correct Implementation:**

```python
class LoginView(ft.UserControl):
    def __init__(self, session_manager, on_login_success):
        super().__init__()
        self.expand = True  # Required for UserControl
        
    def build(self):
        return ft.Container(
            content=your_content,
            image_src="images/background.jpg",
            image_fit=ft.ImageFit.COVER,
            image_opacity=0.9,
            expand=True,  # Full screen expansion
            # Do NOT use explicit width/height parameters
        )
```

**Page Configuration Required:**

```python
# In main.py
page.padding = 0  # Remove default padding for full coverage
page.spacing = 0  # Remove default spacing for full coverage
```

### ❌ **Common Pitfalls to Avoid**

1. **Don't use explicit width/height for full-screen containers:**
   ```python
   # WRONG - causes partial coverage and layout issues
   ft.Container(
       width=page.width,
       height=page.height,
       expand=True  # This conflicts with explicit dimensions
   )
   ```

2. **Don't pass page dimensions to UserControl:**
   ```python
   # WRONG - over-engineering the solution
   class MyControl(ft.UserControl):
       def __init__(self, page_width, page_height):
           # This approach is unnecessarily complex
   ```

3. **Don't forget the UserControl expand fix:**
   ```python
   # WRONG - will not expand properly
   class MyControl(ft.UserControl):
       def __init__(self):
           super().__init__()
           # Missing: self.expand = True
   ```

### 🔧 **When to Apply These Patterns**

- **Full-screen background images** (login pages, splash screens)
- **Dashboard layouts** that need to fill entire window
- **Any UserControl** that contains containers with `expand=True`
- **Responsive layouts** that adapt to window resizing

### 📚 **Official References**

- [Flet UserControl Expand Issue #2565](https://github.com/flet-dev/flet/issues/2565)
- [Flet Container Documentation](https://flet.dev/docs/controls/container/)
- [Flet Background Image Discussion #2545](https://github.com/flet-dev/flet/discussions/2545)

### ⚠️ **Important Notes**

- Always apply the `self.expand = True` fix when creating UserControl classes
- Test full-screen layouts across different window sizes
- Use `expand=True` instead of explicit dimensions for responsive design
- Set `page.padding = 0` and `page.spacing = 0` for true full-screen coverage

### 🚫 **CRITICAL: Never Claim Testing Without User Verification**

**IMPORTANT RULE**: Claude Code assistant CANNOT actually see the running application UI and MUST NEVER claim that "testing passed" or "everything works" without explicit user verification.

**What Claude Code CAN do:**
- Check that code compiles/runs without errors
- Verify database connections work
- Ensure no syntax errors exist
- Run basic functionality checks

**What Claude Code CANNOT do:**
- See the actual user interface
- Verify visual layout and responsiveness
- Confirm that UI elements appear correctly
- Test user interaction flows

**Always state**: "Please test the changes and let me know if the UI behavior is correct" instead of claiming the application works properly.

## Contributing

This application follows modern software development practices:
- Modular architecture with clear separation of concerns
- Comprehensive error handling and logging
- Security-first design principles
- User-friendly interface design

## Collaboration Guidelines

### 🤝 Extended Thinking & Communication Protocol

This project follows an **extended thinking approach** with clear collaboration expectations:

#### Question-Asking Policy
- **Do not hesitate to ask me questions** - Clarification is always preferred over assumptions
- Ask about unclear requirements, ambiguous specifications, or implementation details
- Request confirmation before making significant architectural changes
- Seek guidance when multiple valid approaches exist

#### Scope Management
- **Do not touch any other things beside what I wanted** - Stay strictly within the defined scope
- Only modify files and components explicitly requested
- Avoid making "helpful" changes outside the current task
- Focus on the specific requirements without adding unrequested features

#### Extended Thinking Process
1. **Analyze**: Thoroughly understand the request and current codebase
2. **Question**: Ask for clarification on any ambiguous points
3. **Plan**: Create a detailed implementation plan
4. **Confirm**: Verify the approach aligns with expectations
5. **Execute**: Implement only what was requested
6. **Validate**: Ensure the solution meets the exact requirements

### 📋 Development Workflow

#### Before Starting Any Task:
- Read and understand the complete request
- Identify potential ambiguities or unclear requirements
- Ask questions about scope, approach, or expected outcomes
- Confirm the implementation plan before proceeding

#### During Implementation:
- Stay within the defined scope boundaries
- Ask questions if new requirements emerge during development
- Provide progress updates and seek feedback when needed
- Avoid making assumptions about unspecified behavior

#### After Completion:
- Verify all requested features are implemented
- Ensure no unrelated changes were made
- Document any decisions made during implementation
- Provide clear summary of what was accomplished

### 🎯 Key Principles

1. **Clarity First**: Always ask questions rather than making assumptions
2. **Scope Discipline**: Never exceed the requested changes
3. **Collaborative Approach**: Treat development as a collaborative conversation
4. **Quality Focus**: Deliver exactly what was requested, done well
5. **Communication**: Keep dialogue open throughout the development process

## License

This project is developed for educational and internal use purposes.
- never try to test app by running yourself. You can not do anything by just running it.