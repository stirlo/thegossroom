name: Auto-Fix Jekyll Posts

on:
  push:
    paths:
      - "_posts/**"
      - "scripts/auto_fix_posts.py"  # Adjust if script is in a folder

jobs:
  fix-posts:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repo
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.x"

    - name: Install dependencies
      run: pip install pyyaml

    - name: Run auto-fix script
      run: python scripts/auto_fix_posts.py  # Adjust path if needed

    - name: Commit changes
      run: |
        git config --global user.name "GitHub Actions"
        git config --global user.email "actions@github.com"
        git add _posts
        git commit -m "Auto-fix Jekyll posts" || echo "No changes to commit"
        git push
