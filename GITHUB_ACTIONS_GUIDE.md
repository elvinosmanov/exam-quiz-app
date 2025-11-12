# GitHub Actions - Automatic Multi-Platform Builds

This guide shows you how to automatically build Windows, macOS, and Linux executables using GitHub Actions (100% FREE!).

## 🎯 What This Does

- ✅ Automatically builds Windows .exe when you push code
- ✅ Automatically builds macOS .app
- ✅ Automatically builds Linux executable
- ✅ No Windows/Linux computer needed
- ✅ 100% FREE (for public repositories)
- ✅ Takes 5-10 minutes per build

## 📋 Prerequisites

1. **GitHub Account** (free)
   - Sign up at https://github.com if you don't have one

2. **Git installed on your Mac**
   - Check if installed: `git --version`
   - If not installed: `xcode-select --install`

## 🚀 Setup Instructions (One Time Only)

### Step 1: Create GitHub Repository

**Option A: Using GitHub Website**

1. Go to https://github.com
2. Click the "+" icon → "New repository"
3. Name it: `quiz-examination-system` (or any name)
4. Choose "Public" (for free GitHub Actions)
5. Click "Create repository"

**Option B: Using GitHub Desktop (Easier)**

1. Download GitHub Desktop: https://desktop.github.com/
2. Install and sign in with your GitHub account
3. Click "Create New Repository"
4. Fill in details and create

### Step 2: Initialize Git in Your Project

Open Terminal and run:

```bash
# Navigate to your project
cd /Users/elvin/Documents/Coding_Programming/Cursor/Claude/exam-quiz-app/exam-quiz-app

# Initialize git (if not already initialized)
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit with GitHub Actions workflow"

# Add GitHub as remote (replace YOUR_USERNAME and YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Replace:**
- `YOUR_USERNAME` with your GitHub username
- `YOUR_REPO` with your repository name

### Step 3: Verify Workflow File Exists

The workflow file is already created at:
```
.github/workflows/build-executables.yml
```

This file tells GitHub Actions how to build the executables.

### Step 4: Push to GitHub

```bash
# If you already pushed in Step 2, skip this
git push
```

### Step 5: Watch the Build

1. Go to your GitHub repository
2. Click the "Actions" tab
3. You'll see a workflow running
4. Click on it to watch the progress
5. Wait 5-10 minutes for builds to complete

## 📥 Downloading the Executables

### After Build Completes:

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on the latest workflow run
4. Scroll down to "Artifacts" section
5. Download:
   - **QuizExamSystem-Windows** (contains .exe)
   - **QuizExamSystem-macOS** (contains .app)
   - **QuizExamSystem-Linux** (contains Linux binary)

6. Extract the ZIP files
7. Your executables are ready!

## 🔄 How to Trigger Builds

### Automatic Triggers:
- **Push to main branch** - builds automatically
- **Pull request** - builds automatically for testing

### Manual Trigger:
1. Go to repository on GitHub
2. Click "Actions" tab
3. Click "Build Executables" workflow
4. Click "Run workflow" button
5. Select branch (main)
6. Click "Run workflow"

## 📊 Build Status

You can see build status in your repository:
- ✅ Green checkmark = Build successful
- ❌ Red X = Build failed
- 🟡 Yellow dot = Build in progress

## 🐛 Troubleshooting

### Problem: Workflow doesn't run

**Check:**
1. `.github/workflows/build-executables.yml` exists in your repository
2. File is in the correct location
3. You pushed to `main` or `master` branch

**Solution:**
```bash
# Verify file exists
ls -la .github/workflows/

# Make sure you're on main branch
git branch

# Push again
git push
```

### Problem: Build fails

**Check the logs:**
1. Go to Actions tab
2. Click the failed workflow
3. Click the failed job
4. Read the error messages

**Common issues:**
- Missing dependencies (already handled in workflow)
- Syntax error in code (fix and push again)
- Database initialization failed (check test_db.py)

### Problem: Can't download artifacts

**Check:**
- Artifacts are only kept for 30 days
- You must be signed in to GitHub
- Workflow must complete successfully

## 💡 Tips

### Viewing Build Logs
Click on any step in the workflow to see detailed logs:
```
Install dependencies
Initialize Database
Build Executable
```

### Build Time
- Windows: ~8-10 minutes
- macOS: ~6-8 minutes
- Linux: ~6-8 minutes

### Multiple Versions
Each workflow run creates new artifacts. You can:
- Keep multiple versions
- Download old builds within 30 days
- Compare different builds

## 🔐 Private Repositories

If your repository is private:
- GitHub Actions has 2,000 free minutes/month
- After that, builds cost money
- Solution: Make repository public for unlimited free builds

## 📝 Workflow Customization

### Change Python Version
Edit `.github/workflows/build-executables.yml`:
```yaml
python-version: ['3.11']  # Change to 3.12, etc.
```

### Build on Specific Events Only
Edit the `on:` section:
```yaml
on:
  push:
    branches: [ main ]  # Only build on main branch
```

### Add Release Creation
Automatically create GitHub releases with executables (advanced).

## 🎓 Example Workflow

### Developer Workflow:

1. **Make code changes on Mac**
   ```bash
   # Edit files in your project
   ```

2. **Test locally**
   ```bash
   python3 main.py
   ```

3. **Commit and push**
   ```bash
   git add .
   git commit -m "Added new feature"
   git push
   ```

4. **Wait for GitHub Actions** (5-10 minutes)
   - GitHub automatically builds all platforms

5. **Download executables**
   - Go to Actions tab
   - Download artifacts

6. **Distribute to users**
   - Send Windows .exe to Windows users
   - Send macOS .app to Mac users
   - Send Linux binary to Linux users

## 📦 What Gets Built

### Windows:
```
QuizExamSystem-Windows.zip
└── QuizExamSystem.exe  (~100-150 MB)
```

### macOS:
```
QuizExamSystem-macOS.zip
└── QuizExamSystem.app  (~100-150 MB)
```

### Linux:
```
QuizExamSystem-Linux.zip
└── QuizExamSystem  (~100-150 MB)
```

## ⚡ Quick Commands Reference

```bash
# Initial setup
cd /path/to/project
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main

# Regular updates
git add .
git commit -m "Description of changes"
git push

# Check git status
git status

# View commit history
git log --oneline

# Create a new branch
git checkout -b feature-name

# Switch back to main
git checkout main
```

## 🎯 Benefits of GitHub Actions

| Benefit | Description |
|---------|-------------|
| **No Windows PC needed** | Builds Windows .exe in the cloud |
| **Automatic** | Builds on every push |
| **Free** | Unlimited for public repos |
| **All platforms** | Windows, macOS, Linux at once |
| **Version history** | Keep all previous builds |
| **Professional** | Used by major projects |
| **Reliable** | Clean build environment every time |

## 🔗 Useful Links

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Your Workflows**: https://github.com/USERNAME/REPO/actions
- **Workflow Syntax**: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions

## 📞 Getting Help

### Check workflow status:
```
https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

### View build logs:
1. Click on workflow run
2. Click on job (build on windows-latest, etc.)
3. Expand steps to see details

### Re-run failed builds:
1. Click on failed workflow
2. Click "Re-run jobs" button
3. Select "Re-run failed jobs"

## ✅ Success Checklist

After setup, verify:

- [ ] Repository created on GitHub
- [ ] Code pushed to GitHub
- [ ] `.github/workflows/build-executables.yml` visible in repo
- [ ] Actions tab shows workflow runs
- [ ] All three builds complete successfully (✅ green checkmarks)
- [ ] Artifacts available for download
- [ ] Downloaded .exe/.app files work correctly

## 🎉 You're Done!

Now whenever you push code to GitHub:
1. GitHub Actions automatically builds executables
2. Wait 5-10 minutes
3. Download from Actions → Artifacts
4. Distribute to users

**No Windows computer needed!** 🚀

---

## Next Steps

1. **Push your code to GitHub** (follow Step 2 above)
2. **Watch the Actions tab** for automatic builds
3. **Download the Windows .exe** from artifacts
4. **Test it** and distribute to users

Need help? Check the troubleshooting section above or the build logs in GitHub Actions.
