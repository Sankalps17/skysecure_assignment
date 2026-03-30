# End-to-End Test Queries

Use these queries to test every feature of the assistant. Run them in order — later queries depend on tasks created by earlier ones.

---

## 1. Connection & Setup

After connecting via OAuth, you should see:
- ✅ Connected to Zoho
- Portal selector with your portal name
- Project selector showing your project(s)
- "👤 Logged in as: [Your Name]"

---

## 2. Read Operations

### 2.1 List All Projects
```
List all projects
```
**Expected**: Shows all projects with name, status, owner, open/closed task counts.

### 2.2 List All Tasks
```
Show all tasks
```
**Expected**: All tasks with status, owner, due date, priority. Adaptive cards rendered below the text response.

### 2.3 List Team Members
```
Who's on the team?
```
**Expected**: All team members with names, emails, and roles.

### 2.4 Filter by Status — Open
```
Show open tasks
```
**Expected**: Only tasks with status "Open". Cards should NOT include "In Progress" or other statuses.

### 2.5 Filter by Status — In Progress
```
Show tasks in progress
```
**Expected**: Only tasks with status "In Progress".

### 2.6 Filter by Status — Closed
```
Show closed tasks
```
**Expected**: Only tasks with status "Closed".

### 2.7 Filter by Owner
```
Show Dark P's tasks
```
**Expected**: Only tasks assigned to Dark P.

### 2.8 Filter by Owner + Status
```
Show open tasks assigned to Sankalp
```
**Expected**: Only open tasks where Sankalp is an owner.

### 2.9 Filter by Due Date
```
Show tasks due this month
```
**Expected**: Tasks with due dates within the current month.

### 2.10 Filter by Due Date — Next Month
```
Tasks due next month
```
**Expected**: Tasks with due dates in the next calendar month.

### 2.11 Task Details
```
Show details of Build REST API
```
**Expected**: Full details — ID, status, owner, priority, dates, completion %.

### 2.12 Milestones
```
Show milestones
```
**Expected**: Lists milestones if any exist, or "No milestones found" if none.

### 2.13 Team Utilisation
```
Show team utilisation
```
**Expected**: Hours logged per person. Bar chart + data table rendered. Shows total time each member has logged.

---

## 3. Create Operations

### 3.1 Basic Task Creation
```
Create a task called "Test Deletion Feature"
```
**Expected**: Task created with no assignee, no priority, no due date.

### 3.2 Full Task Creation
```
Create a task "Integration Testing" assigned to Dark P and NullSkull, high priority, due 06-15-2026
```
**Expected**: Task created with both users assigned, High priority, due date set.

---

## 4. Update Operations

### 4.1 Update Status
```
Move "Test Deletion Feature" to In Progress
```
**Expected**: Status updated from Open to In Progress.

### 4.2 Update Priority
```
Set priority of "Test Deletion Feature" to High
```
**Expected**: Priority changed to High, status unchanged.

### 4.3 Update Both Status and Priority
```
Move "Test Deletion Feature" to In Review with medium priority
```
**Expected**: Both status and priority updated in a single call.

### 4.4 Assign Task
```
Assign "Test Deletion Feature" to Sankalp
```
**Expected**: Task assigned to Sankalp.

### 4.5 Multi-Person Assignment
```
Assign "Test Deletion Feature" to Dark P and NullSkull
```
**Expected**: Task assigned to both people.

### 4.6 Close Task
```
Mark "Integration Testing" as complete
```
**Expected**: Status changed to Closed.

---

## 5. Delete Operations

### 5.1 Delete Task
```
Delete "Test Deletion Feature"
```
**Expected**: Task permanently removed. Assistant confirms deletion.

### 5.2 Verify Single Deletion
```
Show all tasks
```
**Expected**: "Test Deletion Feature" no longer appears. "Integration Testing" still exists.

### 5.3 Delete Second Test Task
```
Delete "Integration Testing"
```
**Expected**: Task removed.

### 5.4 Verify All Deletions
```
Show all tasks
```
**Expected**: Neither "Test Deletion Feature" nor "Integration Testing" appear in the list. Only the original project tasks remain.

### 5.5 Delete Non-Existent Task
```
Delete "XXXXXX Does Not Exist"
```
**Expected**: "No task found matching..." with a list of available tasks.

### 5.6 Delete by Partial Name
```
Create a task called "Temporary Cleanup Task"
```
Then:
```
Delete "Temporary Cleanup"
```
**Expected**: Partial name match works — "Temporary Cleanup Task" is deleted.

### 5.7 Verify Cleanup
```
Show all tasks
```
**Expected**: "Temporary Cleanup Task" is gone.

---

## 6. Conversation Memory

### 6.1 Contextual Follow-up
```
Show open tasks
```
Then:
```
How many are there?
```
**Expected**: The assistant remembers the previous query and answers with the count.

### 6.2 Pronoun Resolution
```
Show details of Build REST API
```
Then:
```
Who is assigned to it?
```
**Expected**: The assistant knows "it" refers to "Build REST API".

---

## 7. Edge Cases

### 7.1 Non-existent Task
```
Show details of "XXXXXX"
```
**Expected**: "No task found matching..." with a list of available tasks.

### 7.2 Non-existent User
```
Assign "Build REST API" to John Doe
```
**Expected**: "No team member matching..." with available team members listed.

### 7.3 Greeting (No Tool Call)
```
Hello!
```
**Expected**: A friendly greeting without calling any API tool.

### 7.4 My Tasks (User-Specific)
```
Show my tasks
```
**Expected**: Tasks owned by the logged-in user (detected automatically from OAuth).

---

## 8. Quick Action Buttons

### 8.1 Sidebar — My Tasks
Click the **📋 My Tasks** button in the sidebar.
**Expected**: Same as "Show my open tasks" — filtered by logged-in user.

### 8.2 Sidebar — Team Utilisation
Click the **📊 Team Utilisation** button in the sidebar.
**Expected**: Same as "Show team utilisation" — chart + table.

### 8.3 Card Buttons — Complete
After listing tasks, click **✅ Complete** on any task card.
**Expected**: That task's status changes to Closed.

### 8.4 Card Buttons — Reassign
After listing tasks, click **👤 Reassign** on any task card.
**Expected**: The assistant asks who to reassign to.

---

## Summary Checklist

| # | Test | Pass? |
|---|------|-------|
| 2.1 | List projects | |
| 2.2 | List all tasks | |
| 2.3 | List team members | |
| 2.4 | Open tasks filter | |
| 2.5 | In Progress filter | |
| 2.6 | Closed filter | |
| 2.7 | Owner filter | |
| 2.8 | Owner + status filter | |
| 2.9 | Due this month | |
| 2.10 | Due next month | |
| 2.11 | Task details | |
| 2.12 | Milestones | |
| 2.13 | Team utilisation | |
| 3.1 | Create basic task | |
| 3.2 | Create full task | |
| 4.1 | Update status | |
| 4.2 | Update priority | |
| 4.3 | Update both | |
| 4.4 | Assign task | |
| 4.5 | Multi-assign | |
| 4.6 | Close task | |
| 5.1 | Delete task | |
| 5.2 | Verify single deletion | |
| 5.3 | Delete second task | |
| 5.4 | Verify all deletions | |
| 5.5 | Delete non-existent | |
| 5.6 | Delete by partial name | |
| 5.7 | Verify cleanup | |
| 6.1 | Contextual follow-up | |
| 6.2 | Pronoun resolution | |
| 7.1 | Non-existent task | |
| 7.2 | Non-existent user | |
| 7.3 | Greeting | |
| 7.4 | My tasks | |
| 8.1 | Quick: My Tasks | |
| 8.2 | Quick: Utilisation | |
| 8.3 | Card: Complete | |
| 8.4 | Card: Reassign | |
