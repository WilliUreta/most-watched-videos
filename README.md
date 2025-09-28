# YouTube Most Viewed Videos Fetcher

A PyQt5-based desktop application that retrieves the most viewed videos from a specified YouTube channel within a given time range. The application features a responsive GUI and background processing for a smooth user experience. It requires a free Google API key which has a limit of 10K tokens each day. In my testing, checking 1 channel for a year uses around ~200 tokens.

App coded with assistance of Claude Sonnet 3.5 model.

## Features

- Fetch 20-40 most viewed videos from any YouTube channel
- Filter videos by custom date range
- Display video thumbnails and statistics
- Open videos directly in browser
- Copy results to clipboard in a formatted text
- Responsive UI with background processing
- Support for different channel URL formats (@handle, /c/, /user/, /channel/)

## Project Structure

```
youtube-gui-app/
├── src/
│   ├── gui/
│   │   └── app_window.py     # Main GUI implementation
│   ├── youtube/
│   │   └── fetch_videos.py   # YouTube API interaction
│   ├── utils/
│   │   └── env.py           # Environment configuration
│   └── main.py              # Application entry point
├── .env                     # Environment variables (API key)
├── requirements.txt         # Python dependencies
└── README.md               # Project documentation
```

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd youtube-gui-app
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   ```
   
   On Windows:
   ```powershell
   .\venv\Scripts\activate
   ```
   On Unix/MacOS:
   ```bash
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your YouTube API key:
   ```
   YOUTUBE_API_KEY=your_api_key_here
   ```
   To get an API key:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one
   - Enable YouTube Data API v3
   - Create credentials (API key)

5. Run the application:
   ```bash
   python src/main.py
   ```

## Usage

1. **Channel URL**:
   - Enter any YouTube channel URL format:
     - `https://youtube.com/@ChannelName`
     - `https://youtube.com/c/CustomName`
     - `https://youtube.com/user/Username`
     - `https://youtube.com/channel/ChannelID`

2. **Date Range**:
   - Set start and end dates in YYYY-MM-DD format
   - Default is set to last 365 days

3. **Number of Videos**:
   - Choose how many top videos to fetch (1-50)
   - Default is 40

4. **Results**:
   - View thumbnails and statistics
   - Open videos in browser
   - Copy formatted results to clipboard

## Technical Implementation

### Video Fetching Logic

The video fetching process is implemented in three main stages:

1. **Channel ID Resolution** (`extract_channel_id` method):
   ```python
   def extract_channel_id(self, channel_url):
       # Supports multiple URL formats:
       patterns = [
           r'youtube\.com/channel/([\w-]+)',  # Direct channel ID
           r'youtube\.com/c/([\w-]+)',        # Custom URL
           r'youtube\.com/user/([\w-]+)',     # Username
           r'youtube\.com/@([\w-]+)'          # Handle
       ]
   ```
   - Resolves different URL formats to a channel ID
   - Uses appropriate YouTube API endpoints based on URL type
   - Handles custom URLs and handles through search API

2. **Video Collection** (`fetch_videos` method):
   - Gets channel's uploads playlist
   - Fetches videos in batches (50 videos per API call)
   - Collects video metadata:
     - Title, view count, publication date
     - Thumbnail URL
     - Video URL

3. **Processing and Filtering**:
   - Filters videos within specified date range
   - Sorts by view count (descending)
   - Returns top N most viewed videos

### Multithreading Architecture

To maintain UI responsiveness, the application uses Qt's thread system:

1. **Worker Thread Implementation**:
   ```python
   class FetchWorker(QThread):
       finished = pyqtSignal(list)  # Emits video list
       error = pyqtSignal(str)      # Emits errors
       
       def run(self):
           try:
               videos = self.fetcher.get_most_viewed_videos(...)
               self.finished.emit(videos)
           except Exception as e:
               self.error.emit(str(e))
   ```

2. **Thread Management**:
   ```python
   def fetch_videos(self):
       self.worker = FetchWorker(...)
       self.worker.finished.connect(self.display_results)
       self.worker.error.connect(self.handle_error)
       self.worker.start()
   ```

3. **Progress Feedback**:
   - Uses `QProgressDialog` for visual feedback
   - Cancelable operation
   - Error handling and thread cleanup


## Dependencies

- **PyQt5**: GUI framework
- **google-api-python-client**: YouTube Data API v3 interaction
- **python-dotenv**: Environment variable management
- **requests**: HTTP requests for thumbnails


## Error Handling

The application includes comprehensive error handling:

- Invalid URL format detection
- Date validation
- API errors (quota exceeded, invalid channel, etc.)
- Network connectivity issues
- Thread cleanup on errors or cancellation

## License

This project is licensed under the MIT License. See the LICENSE file for more details.