@echo off
set GH="C:\Program Files\GitHub CLI\gh.exe"

echo Creating labels...
%GH% label create performance --color "0E8A16" --description "Performance improvements"
%GH% label create reliability --color "D93F0B" --description "Reliability and stability improvements"
%GH% label create user-experience --color "1D76DB" --description "User experience enhancements"
%GH% label create observability --color "5319E7" --description "Monitoring and observability features"
%GH% label create algorithm --color "006B75" --description "Algorithm improvements"
%GH% label create frontend --color "FEF2C0" --description "Frontend changes"
%GH% label create backend --color "BFD4F2" --description "Backend changes"
%GH% label create qa --color "FBCA04" --description "Quality assurance"
%GH% label create priority-high --color "B60205" --description "High priority task"
%GH% label create priority-medium --color "D93F0B" --description "Medium priority task"

echo.
echo Creating MVP Improvements milestone via first issue...
%GH% issue create --title "MVP Improvements" --body "Key improvements for MVP functionality, performance, and observability" --label "enhancement"

echo.
echo [1/8] Creating Smart Caching Strategy issue...
%GH% issue create --title "Implement Smart Caching Strategy" --body-file github_issues.yml --label "enhancement,performance,priority-high,backend"

echo.
echo [2/8] Creating Error Handling issue...
%GH% issue create --title "Implement Error Handling and Recovery" --body-file github_issues.yml --label "enhancement,reliability,priority-high,backend,frontend"

echo.
echo [3/8] Creating Browser Session Management issue...
%GH% issue create --title "Enhance Browser Session Management" --body-file github_issues.yml --label "enhancement,performance,priority-high,backend"

echo.
echo [4/8] Creating Progress Indicators issue...
%GH% issue create --title "Add Progress Indicators & Status Updates" --body-file github_issues.yml --label "enhancement,user-experience,priority-high,frontend,backend"

echo.
echo [5/8] Creating Structured Logging issue...
%GH% issue create --title "Implement Structured Logging" --body-file github_issues.yml --label "enhancement,observability,priority-high,backend,qa"

echo.
echo [6/8] Creating Debug Dashboard issue...
%GH% issue create --title "Create Debug Dashboard" --body-file github_issues.yml --label "enhancement,observability,priority-medium,frontend,backend,qa"

echo.
echo [7/8] Creating Rate Limit Management issue...
%GH% issue create --title "Implement Rate Limit Management" --body-file github_issues.yml --label "enhancement,reliability,priority-high,backend"

echo.
echo [8/8] Creating Connection Path Optimization issue...
%GH% issue create --title "Add Connection Path Optimization" --body-file github_issues.yml --label "enhancement,algorithm,priority-medium,backend"

echo.
echo ✅ All issues created successfully! 