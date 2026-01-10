# MyWhoosh to Garmin Connect Sync

Automatically sync your latest activity from MyWhoosh to Garmin Connect with proper device attribution (Garmin Edge 840).

## Features

✅ **Automatic Authentication** - No captcha! Uses official MyWhoosh API  
✅ **Latest Activity Sync** - Fetches and uploads your most recent ride  
✅ **Device Modification** - Changes FIT file to show as Garmin Edge 840  
✅ **Duplicate Detection** - Automatically skips activities already on Garmin Connect  
✅ **File Format Handling** - Automatically converts .dms to .fit  
✅ **Comprehensive Logging** - Detailed logs for debugging (console + file)  
✅ **Error Handling** - Graceful failure with clear error messages  

## Prerequisites

- Python 3.7 or higher
- Active MyWhoosh account
- Active Garmin Connect account

## Quick Start

### 1. Clone and Setup

```bash
cd /path/to/mywhoosh-to-garmin
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Credentials

Create a `.env` file with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
MYWHOOSH_EMAIL=your_email@example.com
MYWHOOSH_PASSWORD=your_password
GARMIN_USERNAME=your_garmin_username
GARMIN_PASSWORD=your_garmin_password
LOG_LEVEL=INFO
```

**Important:** Never commit your `.env` file! It's already in `.gitignore`.

### 3. Run the Sync

```bash
python main.py
```

or

```bash
./main.py
```

## How It Works

The application follows these steps:

1. **Authenticate with MyWhoosh** using the official API
2. **Fetch Latest Activity** from your MyWhoosh account
3. **Check for Duplicates** on Garmin Connect (within 2-hour window)
4. **Download FIT File** (automatically handles .dms format)
5. **Modify Device Info** to Garmin Edge 840 (Product ID: 4024)
6. **Upload to Garmin Connect**
7. **Cleanup** temporary files

## Configuration Options

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `MYWHOOSH_EMAIL` | Yes | Your MyWhoosh account email | - |
| `MYWHOOSH_PASSWORD` | Yes | Your MyWhoosh account password | - |
| `GARMIN_USERNAME` | Yes | Your Garmin Connect username | - |
| `GARMIN_PASSWORD` | Yes | Your Garmin Connect password | - |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |

### Device Settings

By default, the FIT file is modified to appear as:
- **Device:** Garmin Edge 840
- **Manufacturer:** Garmin (ID: 1)
- **Product ID:** 4024
- **Software Version:** 20.19

To change the device, modify `services/fit_file_service.py:services/fit_file_service.py:44-46`.

## Logging

The application logs to both:
- **Console** - Progress and key events
- **File** - `mywhoosh_to_garmin.log` with detailed logs

Example log output:

```
2026-01-10 15:30:00 - __main__ - INFO - main:45 - Starting MyWhoosh to Garmin sync
2026-01-10 15:30:01 - services.mywhoosh_service - INFO - authenticate:39 - Authenticating with MyWhoosh...
2026-01-10 15:30:02 - services.mywhoosh_service - INFO - authenticate:64 - Successfully authenticated
2026-01-10 15:30:03 - services.mywhoosh_service - INFO - get_latest_activity:145 - Latest activity: Morning Ride
2026-01-10 15:30:05 - services.mywhoosh_service - INFO - download_activity:198 - Downloaded 245,678 bytes
2026-01-10 15:30:06 - services.fit_file_service - INFO - modify_device_info:48 - Modifying FIT file...
2026-01-10 15:30:08 - services.garmin_service - INFO - upload_activity:72 - Uploading to Garmin Connect...
2026-01-10 15:30:12 - services.garmin_service - INFO - upload_activity:76 - Upload successful
✓ Sync completed successfully!
```

## Troubleshooting

### Authentication Errors

**MyWhoosh authentication failed:**
- ✓ Check your email and password in `.env`
- ✓ Verify your MyWhoosh account is active
- ✓ Check internet connection

**Garmin authentication failed:**
- ✓ Check your username and password in `.env`
- ✓ Try logging into Garmin Connect website manually
- ✓ Check if Garmin Connect is experiencing issues

### No Activities Found

- ✓ Make sure you have activities in MyWhoosh
- ✓ Check that you're logged into the correct MyWhoosh account
- ✓ Try running the MyWhoosh app to ensure activities are synced

### Duplicate Detected

This is **normal behavior** - the activity has already been uploaded to Garmin Connect. The tool automatically skips re-uploading to avoid duplicates.

### Upload Failed

- ✓ Check Garmin Connect status: [status.garmin.com](https://status.garmin.com)
- ✓ Verify the FIT file is valid (check logs for file size)
- ✓ Try again in a few minutes (temporary network issues)
- ✓ Check the detailed log file: `mywhoosh_to_garmin.log`

### File Download Issues

**Cannot find download URL:**
- The activity structure may have changed
- Check the logs for available keys
- Open an issue with the log output

**File format error:**
- The tool should handle .dms to .fit conversion automatically
- If you see this error, the downloaded file may be corrupted
- Try again or check your internet connection

## Advanced Usage

### Running as a Cron Job

To automatically sync after each ride, add to your crontab:

```bash
# Run every hour
0 * * * * cd /path/to/mywhoosh-to-garmin && ./venv/bin/python main.py >> sync.log 2>&1
```

### Disabling Duplicate Check

To disable duplicate detection (not recommended), modify `main.py:services/activity_processor.py:33`:

```python
success = processor.process_latest_activity(check_duplicates=False)
```

### Custom Device Type

To use a different Garmin device, edit `services/fit_file_service.py:services/fit_file_service.py:44-46` and change the product ID:

```python
# Example: Edge 530 (Product ID: 3121)
product = product or 3121
```

## Project Structure

```
mywhoosh-to-garmin/
├── services/
│   ├── __init__.py
│   ├── mywhoosh_service.py      # MyWhoosh API integration
│   ├── garmin_service.py         # Garmin Connect integration
│   ├── fit_file_service.py       # FIT file modification
│   ├── activity_processor.py     # Main workflow orchestration
│   └── zwift_service.py          # (Legacy - not used)
├── main.py                       # Application entry point
├── .env                          # Your credentials (DO NOT COMMIT)
├── .env.example                  # Credentials template
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## API Documentation

This project uses the official MyWhoosh API. For more details, see:
- [MyWhoosh API Documentation](https://github.com/mywhoosh-community/mywhoosh-api)

## Dependencies

- **requests** - HTTP client for API calls
- **garminconnect** - Garmin Connect API wrapper
- **fit-tool** - FIT file parsing and modification
- **python-dotenv** - Environment variable management

## Security Notes

- **Never commit your `.env` file** - It contains sensitive credentials
- **Use environment variables** - Don't hardcode credentials in code
- **Secure your credentials** - Keep your MyWhoosh and Garmin passwords safe
- **API tokens** - MyWhoosh tokens expire; re-authentication is automatic

## Known Limitations

- Only syncs the **latest activity** (not bulk import)
- Requires valid credentials for both services
- Duplicate detection uses a 2-hour time window
- Download URLs may be temporary (with expiration)

## Contributing

Found a bug or want to add a feature? Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is provided as-is for personal use.

## Acknowledgments

- MyWhoosh for their indoor cycling platform
- Garmin Connect for activity tracking
- The cycling community for inspiration

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the log file: `mywhoosh_to_garmin.log`
3. Ensure you're using the latest version
4. Open an issue with detailed logs (remove sensitive info!)

---

**Happy riding! 🚴**
