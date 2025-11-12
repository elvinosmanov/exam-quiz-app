#!/bin/bash
# Quick setup script for GitHub Actions

echo "=============================================="
echo "GitHub Actions Setup for Quiz Exam System"
echo "=============================================="
echo

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed!"
    echo "Install with: xcode-select --install"
    exit 1
fi

echo "✓ Git is installed"
echo

# Check if already a git repository
if [ -d ".git" ]; then
    echo "✓ Git repository already initialized"
else
    echo "Initializing Git repository..."
    git init
    echo "✓ Git repository initialized"
fi
echo

# Check if workflow file exists
if [ -f ".github/workflows/build-executables.yml" ]; then
    echo "✓ GitHub Actions workflow file exists"
else
    echo "❌ Workflow file not found!"
    echo "Expected: .github/workflows/build-executables.yml"
    exit 1
fi
echo

# Get GitHub repository details
echo "=============================================="
echo "GitHub Repository Setup"
echo "=============================================="
echo
echo "Please provide your GitHub repository details:"
echo
read -p "GitHub Username: " github_username
read -p "Repository Name: " repo_name
echo

# Set git config (if not already set)
if ! git config user.name &> /dev/null; then
    read -p "Your Name (for git commits): " user_name
    git config user.name "$user_name"
fi

if ! git config user.email &> /dev/null; then
    read -p "Your Email (for git commits): " user_email
    git config user.email "$user_email"
fi

echo
echo "✓ Git configuration set"
echo

# Add remote if not exists
if git remote get-url origin &> /dev/null; then
    echo "✓ Remote 'origin' already exists"
    echo "Current remote: $(git remote get-url origin)"
else
    repo_url="https://github.com/${github_username}/${repo_name}.git"
    echo "Adding remote: $repo_url"
    git remote add origin "$repo_url"
    echo "✓ Remote added"
fi
echo

# Show status
echo "=============================================="
echo "Current Status"
echo "=============================================="
echo
echo "Repository: https://github.com/${github_username}/${repo_name}"
echo "Branch: $(git branch --show-current 2>/dev/null || echo 'No branches yet')"
echo

# Offer to commit and push
echo "=============================================="
echo "Next Steps"
echo "=============================================="
echo
echo "Ready to commit and push to GitHub?"
echo
read -p "Add all files and commit? (y/n): " do_commit

if [ "$do_commit" = "y" ] || [ "$do_commit" = "Y" ]; then
    echo
    echo "Adding all files..."
    git add .

    echo "Creating commit..."
    git commit -m "Initial commit with GitHub Actions workflow for multi-platform builds"

    echo "Setting main branch..."
    git branch -M main

    echo "Pushing to GitHub..."
    git push -u origin main

    echo
    echo "=============================================="
    echo "✓ SUCCESS!"
    echo "=============================================="
    echo
    echo "Your code is now on GitHub!"
    echo
    echo "Next steps:"
    echo "1. Go to: https://github.com/${github_username}/${repo_name}"
    echo "2. Click the 'Actions' tab"
    echo "3. Watch the build process (takes ~5-10 minutes)"
    echo "4. Download executables from 'Artifacts' when complete"
    echo
    echo "Windows .exe will be available for download!"
    echo "=============================================="
else
    echo
    echo "Skipped commit and push."
    echo
    echo "To manually push later, run:"
    echo "  git add ."
    echo "  git commit -m 'Your commit message'"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi

echo
echo "For detailed instructions, see: GITHUB_ACTIONS_GUIDE.md"
