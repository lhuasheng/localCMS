---
name: cronjob
description: 'Create, manage, and troubleshoot cron jobs and scheduled tasks. Use for recurring automation, one-shot reminders, periodic scripts, and cron debugging.'
argument-hint: 'Schedule expression, command or script, and operational goal'
user-invocable: true
---

# Cronjob

## When to Use
- Creating or editing a scheduled task (one-shot, recurring, or interval).
- Automating periodic scripts, backups, health checks, or reports.
- Debugging cron jobs that fail to fire or produce unexpected output.
- Managing cron job lifecycle on Linux/macOS (crontab, systemd timers, launchd).

## Cron Expression Format
Standard 5-field cron expression: `minute hour day-of-month month day-of-week`

| Field         | Values        | Special characters       |
|---------------|---------------|--------------------------|
| Minute        | 0–59          | `, - * /`                |
| Hour          | 0–23          | `, - * /`                |
| Day of month  | 1–31          | `, - * /`                |
| Month         | 1–12 or names | `, - * /`                |
| Day of week   | 0–7 (0,7=Sun) | `, - * /`                |

When both day-of-month and day-of-week are set (non-`*`), standard Vixie cron uses **OR** logic — the job fires when either field matches.

## Common Expressions
| Expression          | Meaning                          |
|---------------------|----------------------------------|
| `* * * * *`         | Every minute                     |
| `0 * * * *`         | Every hour on the hour           |
| `0 9 * * *`         | Daily at 9:00 AM                 |
| `0 9 * * 1`         | Every Monday at 9:00 AM          |
| `0 0 1 * *`         | First day of each month at midnight |
| `*/15 * * * *`      | Every 15 minutes                 |
| `0 6,18 * * *`      | At 6:00 AM and 6:00 PM daily     |
| `@reboot`           | Once at startup (crontab only)   |

## Procedure
1. Determine the schedule expression and timezone for the job.
2. Write and test the command or script independently before scheduling.
3. Add the cron entry using the appropriate mechanism for the OS.
4. Redirect output to a log file or logging system for observability.
5. Verify the job is registered and test with a near-future schedule if possible.
6. Monitor logs to confirm execution.

## Linux Crontab
```bash
# Edit the current user's crontab
crontab -e

# List current crontab entries
crontab -l

# Example entries
# Daily backup at 2:30 AM
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# Every 15 minutes, run a health check
*/15 * * * * /usr/local/bin/healthcheck.sh >> /var/log/healthcheck.log 2>&1

# Weekly report on Mondays at 9 AM
0 9 * * 1 /usr/local/bin/weekly-report.sh >> /var/log/report.log 2>&1

# One-shot via at (alternative for single future execution)
echo "/usr/local/bin/task.sh" | at now + 20 minutes
```

## Systemd Timers (Linux alternative)
```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily backup timer

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true

[Install]
WantedBy=timers.target
```
```bash
systemctl enable --now backup.timer
systemctl list-timers --all
journalctl -u backup.service --since today
```

## macOS launchd
```xml
<!-- ~/Library/LaunchAgents/com.user.backup.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/backup.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/backup.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/backup.stderr.log</string>
</dict>
</plist>
```
```bash
launchctl load ~/Library/LaunchAgents/com.user.backup.plist
launchctl list | grep com.user.backup
launchctl unload ~/Library/LaunchAgents/com.user.backup.plist
```

## Best Practices
- Always redirect stdout and stderr (`>> /var/log/job.log 2>&1`).
- Use absolute paths for commands and scripts in cron entries.
- Set `PATH` and other environment variables explicitly inside cron scripts (cron has a minimal environment).
- Use `flock` or a lockfile to prevent overlapping runs of long jobs.
- Test scripts manually before scheduling.

```bash
# Prevent overlapping runs with flock
*/5 * * * * /usr/bin/flock -n /tmp/myjob.lock /usr/local/bin/myjob.sh
```

## Troubleshooting
- **Job not firing**: verify entry with `crontab -l`, check cron daemon is running (`systemctl status cron` or `pgrep cron`), review `/var/log/syslog` or `/var/log/cron`.
- **Command not found in cron**: cron uses a minimal `PATH`; use absolute paths or set `PATH=` at the top of the crontab.
- **Permission denied**: ensure the script is executable (`chmod +x`) and the user has access.
- **No output or silent failure**: always redirect stderr; check mail (`mail` command) as cron may email output to the user.
- **Timezone issues**: cron uses the system timezone by default. Set `TZ` in the crontab or use `timedatectl` to verify.
- **Day-of-month + day-of-week**: remember OR logic in Vixie cron — both fields set means the job runs when either matches.

## Review Checklist
- Cron expression matches the intended schedule and timezone.
- Command uses absolute paths and handles its own environment.
- Output is redirected to logs or a logging system.
- Overlapping runs are guarded with a lockfile if the job is long-running.
- Script is tested independently before being scheduled.
