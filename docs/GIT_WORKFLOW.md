# Git Branching Workflow

## Branch Strategy

This project uses a **multi-branch workflow** where:
- **`main`** - Complete project (both motors and LEDs)
- **`motors`** - Motor system development (THIS PC)
- **`leds`** - LED system development (OTHER PC)

## Branch Overview

```
main (complete project)
├── motors/ (motor system)
├── leds/ (LED system)
└── shared/ (shared utilities)
```

## Workflow

### On THIS PC (Motor Development)

1. **Start working on motors:**
   ```bash
   git checkout motors
   git pull origin motors
   ```

2. **Make changes to motor code:**
   - Edit files in `motors/` folder
   - Test motor system

3. **Commit and push:**
   ```bash
   git add motors/
   git commit -m "Motor feature: description"
   git push origin motors
   ```

4. **Merge to main (when ready):**
   ```bash
   git checkout main
   git pull origin main
   git merge motors
   git push origin main
   ```

### On OTHER PC (LED Development)

1. **Start working on LEDs:**
   ```bash
   git checkout leds
   git pull origin leds
   ```

2. **Make changes to LED code:**
   - Edit files in `leds/` folder
   - Test LED system

3. **Commit and push:**
   ```bash
   git add leds/
   git commit -m "LED feature: description"
   git push origin leds
   ```

4. **Merge to main (when ready):**
   ```bash
   git checkout main
   git pull origin main
   git merge leds
   git push origin main
   ```

## Important Rules

### ✅ DO:
- Work on `motors` branch for motor changes (THIS PC)
- Work on `leds` branch for LED changes (OTHER PC)
- Merge to `main` when features are complete
- Pull latest `main` before creating new branches
- Keep `main` branch stable and complete

### ❌ DON'T:
- Don't push motor changes to `leds` branch
- Don't push LED changes to `motors` branch
- Don't work directly on `main` branch
- Don't merge incomplete features to `main`

## Branch Setup (One-Time)

### Initial Setup (Already Done)

```bash
# Create motors branch
git checkout -b motors
git push -u origin motors

# Create leds branch
git checkout main
git checkout -b leds
git push -u origin leds

# Return to main
git checkout main
```

## Daily Workflow

### THIS PC (Motors)

```bash
# Morning: Get latest changes
git checkout main
git pull origin main
git checkout motors
git merge main  # Get latest from main

# Work on motors...
git add motors/
git commit -m "Motor update"
git push origin motors

# End of day: Merge to main if ready
git checkout main
git merge motors
git push origin main
```

### OTHER PC (LEDs)

```bash
# Morning: Get latest changes
git checkout main
git pull origin main
git checkout leds
git merge main  # Get latest from main

# Work on LEDs...
git add leds/
git commit -m "LED update"
git push origin leds

# End of day: Merge to main if ready
git checkout main
git merge leds
git push origin main
```

## Resolving Conflicts

If conflicts occur when merging:

1. **Motor conflicts:**
   ```bash
   git checkout motors
   git merge main
   # Resolve conflicts in motors/ folder
   git add motors/
   git commit -m "Resolved conflicts"
   ```

2. **LED conflicts:**
   ```bash
   git checkout leds
   git merge main
   # Resolve conflicts in leds/ folder
   git add leds/
   git commit -m "Resolved conflicts"
   ```

## Quick Reference

| Task | Command |
|------|---------|
| Switch to motors branch | `git checkout motors` |
| Switch to leds branch | `git checkout leds` |
| Switch to main | `git checkout main` |
| See current branch | `git branch` |
| Pull latest changes | `git pull origin <branch>` |
| Push changes | `git push origin <branch>` |

## Branch Protection

- **main** - Should always contain complete, working project
- **motors** - Motor development branch (THIS PC)
- **leds** - LED development branch (OTHER PC)

## Best Practices

1. **Commit often** - Small, focused commits
2. **Pull before push** - Always pull latest before pushing
3. **Test before merge** - Test changes before merging to main
4. **Clear commit messages** - Describe what changed and why
5. **Keep branches in sync** - Regularly merge main into feature branches

## Example Commit Messages

### Motor Commits
```
Motor: Add servo calibration feature
Motor: Fix angle calculation bug
Motor: Update motor GUI layout
```

### LED Commits
```
LED: Add new mapping mode
LED: Fix panel rendering issue
LED: Improve LED controller performance
```

## Troubleshooting

### "Branch not found" error
```bash
# Fetch all branches
git fetch origin

# Check available branches
git branch -a
```

### "Your branch is behind" warning
```bash
# Pull latest changes
git pull origin <branch>
```

### Accidentally committed to wrong branch
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Switch to correct branch
git checkout <correct-branch>

# Commit again
git add .
git commit -m "Message"
```

