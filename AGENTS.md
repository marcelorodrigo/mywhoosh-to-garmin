# AI Agent Guide: MyWhoosh to Garmin Sync

## Architecture Overview

**Purpose:** Sync cycling activities from MyWhoosh to Garmin Connect, modifying FIT files to attribute them to a Garmin Edge 840 device.

**Core Flow:** `main.py` → `ActivityProcessor` → (MyWhoosh/FIT/Garmin services) → Upload to Garmin

### Service Architecture (Dependency Injection Pattern)

```
ActivityProcessor (orchestrator)
  ├── MyWhooshService (fetch activities, download FIT files)
  ├── FitFileService (modify device metadata)
  └── GarminService (authenticate, check duplicates, upload)
```

Each service:
- Takes dependencies via `__init__()` 
- Handles a single responsibility (MyWhoosh auth/download, FIT modification, Garmin auth/upload)
- Returns structured data (dicts for activities, bools for checks, responses for uploads)
- Logs extensively with `self.logger = logging.getLogger(__name__)`

## Key Files & Their Responsibilities

| File | Lines | Purpose | Key Methods |
|------|-------|---------|-------------|
| `main.py` | 230 | CLI entry point, config loading, mode selection | `main()`, `load_config()`, `setup_logging()` |
| `services/activity_processor.py` | 329 | Workflow orchestration, error handling | `process_latest_activity()`, `process_multiple_activities()` |
| `services/mywhoosh_service.py` | 307 | MyWhoosh API integration | `authenticate()`, `get_activities()`, `download_activity()` |
| `services/garmin_service.py` | 186 | Garmin Connect API integration | `authenticate()`, `upload_activity()`, `check_duplicate_activity()` |
| `services/fit_file_service.py` | 96 | FIT file parsing/modification | `modify_device_info()`, `cleanup_file()` |

## Critical Data Structures & Flows

### Activity Dictionary (from MyWhoosh API)
```python
activity = {
    'id': '69622c3121123aaced178584',           # Used for download requests
    'name': 'Morning Ride',                      # Activity name
    'date' or 'timestamp': 1768039347,           # Unix timestamp (seconds)
    'activityFileId': 'file123'                  # Used in download endpoint
}
```

### Download Flow
1. **MyWhoosh API endpoint:** `POST /v2/rider/profile/download-activity-file`
2. **Payload:** `{"key": whoosh_id, "fileId": activityFileId}`
3. **Response:** `{"data": "https://mywhooshprod.s3.eu-west-1.amazonaws.com/ride/..."}` (presigned S3 URL)
4. **Download:** Fetch from S3 URL, save to temp file, verify FIT header `".FIT"` magic bytes
5. **Return:** Path to temp file (cleaned up after upload)

### Duplicate Detection
- Garmin API returns activities with `startTimeLocal` or `startTime` fields
- Match window: ±2 hours from MyWhoosh activity timestamp
- Name matching: Case-insensitive substring match
- If name doesn't match despite time match, continue checking (multiple activities per day)

### FIT File Modification
- **Library:** `fit_tool` (parses FIT files into messages)
- **Target:** File info message containing manufacturer (Garmin=1) and product ID (Edge 840=4024)
- **Default:** Garmin Edge 840, software version 20.19
- **Modifiable:** `services/fit_file_service.py:44-46` for different devices

## Execution Modes

### Single Activity (Default)
```bash
python main.py
```
- Syncs only the latest activity
- Returns exit code 0 (success) or 1 (failure)

### Batch Mode
```bash
python main.py --batch 10
```
- Processes up to 10 activities
- Returns stats dict: `{'total': N, 'synced': N, 'skipped': N, 'errors': N}`
- Used in `process_multiple_activities()` (different workflow than single activity)

### Skip Duplicate Check
```bash
python main.py --batch 10 --no-duplicates
```
- Faster sync, may upload duplicates
- Skips Garmin authentication until upload step

## Error Handling Patterns

### API Errors
- **409 Conflict:** Activity already exists on Garmin → Treated as success (no retry)
- **Authentication:** Logged and re-raised as RuntimeError (stops processing)
- **Network/Rate limit:** Logged, exception bubbles to main() for exit code 1

### Date Parsing
- Accepts multiple formats: ISO strings, Unix timestamps (seconds/milliseconds)
- **Fallback:** If unparseable, logs warning and continues without duplicate check
- See `_parse_activity_date()` in `activity_processor.py:150-196`

### File Operations
- Temp files created in system temp dir: `/var/folders/.../T/mywhoosh_*.fit`
- **Always cleaned up** in `finally` block (even on errors)
- Cleanup uses `fit_file_service.cleanup_file()` → `os.unlink()`

## Logging System

**Setup:** `main.py:setup_logging()` configures root logger with:
- Console handler → stdout (human-readable)
- File handler → `mywhoosh_to_garmin.log` (detailed)
- Format: `%(asctime)s - %(levelname)s - %(name)s - %(message)s`

**Pattern:** Each service logs progress with `self.logger.info()`, errors with `self.logger.exception()`

**urllib3 Warning:** Suppressed for macOS LibreSSL compatibility (see `main.py:24`)

## Configuration & Secrets

**Source:** `.env` file (DO NOT COMMIT - in `.gitignore`)

**Required:**
```
MYWHOOSH_EMAIL=user@example.com
MYWHOOSH_PASSWORD=password
GARMIN_USERNAME=username
GARMIN_PASSWORD=password
LOG_LEVEL=INFO  # Optional, defaults to INFO
```

**Loading:** `main.py:load_config()` uses `python-dotenv`
- Validates all required vars present
- Raises `ValueError` if missing (exit code 2)

## Common Workflows for Agents

### Adding a New Sync Feature
1. Add method to `ActivityProcessor` (follows `process_latest_activity()` pattern)
2. Add CLI argument in `main.py:117-127`
3. Call new method in `main()` based on args
4. Return bool (success) or dict (stats)

### Handling New MyWhoosh API Changes
1. MyWhoosh endpoint: `https://service14.mywhoosh.com/v2/rider/profile/*`
2. All requests: Add headers (Bearer token, Content-Type, User-Agent)
3. Response format: Check for both `{data: [...]}` and `{data: {results: [...]}}`
4. Download: Get presigned S3 URL, verify FIT header after download

### Modifying FIT File Device Info
1. `fit_file_service.py:modify_device_info()` reads original, iterates messages
2. Find "file_id" message type (contains manufacturer/product/serial)
3. Create new message with modified values
4. Write modified FIT file to new temp file
5. Return path to modified file

## Testing & Debugging

**Run latest activity sync:**
```bash
source venv/bin/activate
python main.py
```

**Run batch sync with logging:**
```bash
python main.py --batch 2 2>&1 | tee debug.log
```

**Check log file:** `mywhoosh_to_garmin.log` contains full details (timestamps, API responses in debug mode)

**Common issues:**
- 409 Conflict = Activity exists (success, no retry)
- Date parse warning = Timestamp format not recognized (continues without dup check)
- Auth error = Check `.env` credentials

## Dependencies & Integration Points

- **requests:** HTTP calls to MyWhoosh/S3
- **garminconnect:** High-level Garmin API wrapper (handles auth)
- **fit_tool:** FIT message parsing/modification
- **python-dotenv:** Credentials from `.env`

**External APIs:**
- MyWhoosh: `service14.mywhoosh.com/v2/rider/profile/*`
- AWS S3: Presigned URLs from MyWhoosh for file download
- Garmin Connect: Via `garminconnect` library (abstracts HTTP details)

## Git Commit Conventions

Recent commits use conventional format:
```
fix: Handle 409 Conflict gracefully
feat: Add batch mode for syncing multiple activities
```

Related to features/fixes in code - maintain this pattern for consistency.
