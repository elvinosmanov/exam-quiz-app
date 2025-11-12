# GitHub Actions - Quick Start (5 Minutes)

## 🎯 Goal
Get Windows .exe without a Windows computer!

## ⚡ Super Quick Steps

### 1. Create GitHub Account (2 minutes)
- Go to https://github.com
- Sign up (it's free)
- Verify your email

### 2. Create Repository (1 minute)
- Click "+" icon → "New repository"
- Name: `quiz-exam-system` (or any name)
- Choose: **Public** (important for free builds!)
- Click "Create repository"

### 3. Push Your Code (2 minutes)

**Option A: Use the automated script**
```bash
./setup_github.sh
```
Follow the prompts!

**Option B: Manual commands**
```bash
# In your project folder
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your details.

### 4. Watch the Magic ✨

1. Go to your repo: `https://github.com/YOUR_USERNAME/YOUR_REPO`
2. Click **"Actions"** tab
3. See the build running (🟡 yellow dot)
4. Wait 5-10 minutes
5. Build completes (✅ green checkmark)

### 5. Download Windows .exe 📥

1. In Actions tab, click the completed workflow
2. Scroll to bottom → **"Artifacts"** section
3. Download **"QuizExamSystem-Windows"**
4. Extract the ZIP
5. You have `QuizExamSystem.exe`! 🎉

## 📋 That's It!

**Total time: ~15 minutes (including build time)**

You now have:
- ✅ Windows .exe
- ✅ macOS .app
- ✅ Linux binary

All built automatically in the cloud!

## 🔄 Next Time (Updates)

When you make changes:

```bash
git add .
git commit -m "Description of changes"
git push
```

GitHub automatically builds new executables!

## 📚 Need More Details?

See **GITHUB_ACTIONS_GUIDE.md** for complete instructions.

## 🆘 Troubleshooting

### Can't push to GitHub?
```bash
# Check if git is set up
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Try pushing again
git push -u origin main
```

### Build failed?
1. Click on the failed workflow
2. Read the error message
3. Fix the issue
4. Push again

### Can't find Actions tab?
- Make sure repository is **public**
- Refresh the page
- Check you're logged in

## 💡 Pro Tips

- **Manual trigger**: Actions tab → "Run workflow" button
- **Multiple versions**: Each build creates new artifacts
- **Free forever**: Unlimited builds for public repos

---

**Ready? Run `./setup_github.sh` to get started!**
