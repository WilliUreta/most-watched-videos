from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QPushButton, QLineEdit, QTextEdit, QMessageBox,
                             QSpinBox, QScrollArea, QGridLayout, QFrame, QProgressDialog)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QPixmap, QClipboard
import sys
import os
import requests
from datetime import datetime, timedelta
from src.youtube.fetch_videos import YouTubeFetcher
from src.utils.env import load_dotenv

# Load environment variables
load_dotenv()

class FetchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, fetcher, channel_url, start_date, end_date, num_videos):
        super().__init__()
        self.fetcher = fetcher
        self.channel_url = channel_url
        self.start_date = start_date
        self.end_date = end_date
        self.num_videos = num_videos

    def run(self):
        try:
            videos = self.fetcher.get_most_viewed_videos(
                self.channel_url,
                self.start_date,
                self.end_date,
                self.num_videos
            )
            self.finished.emit(videos)
        except Exception as e:
            self.error.emit(str(e))

class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Fetcher")
        self.setGeometry(100, 100, 1024, 768)
        
        # Initialize YouTubeFetcher with API key from environment variable
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YouTube API key not found in environment variables")
        self.fetcher = YouTubeFetcher(api_key)
        
        self.worker = None
        self.progress_dialog = None
        
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Channel URL input
        self.channel_url_label = QLabel("YouTube Channel URL:")
        self.channel_url_input = QLineEdit(self)
        self.channel_url_input.setPlaceholderText("https://youtube.com/@ChannelName")
        layout.addWidget(self.channel_url_label)
        layout.addWidget(self.channel_url_input)

        # Date inputs
        self.start_date_label = QLabel("Start Date (YYYY-MM-DD):")
        self.start_date_input = QLineEdit(self)
        layout.addWidget(self.start_date_label)
        layout.addWidget(self.start_date_input)

        self.end_date_label = QLabel("End Date (YYYY-MM-DD):")
        self.end_date_input = QLineEdit(self)
        layout.addWidget(self.end_date_label)
        layout.addWidget(self.end_date_input)

        # Set default dates to last year
        today = datetime.now()
        last_year = today - timedelta(days=365)
        self.start_date_input.setText(last_year.strftime('%Y-%m-%d'))
        self.end_date_input.setText(today.strftime('%Y-%m-%d'))

        # Number of videos to fetch
        self.num_videos_label = QLabel("Number of videos to fetch:")
        self.num_videos_input = QSpinBox(self)
        self.num_videos_input.setRange(1, 50)
        self.num_videos_input.setValue(30)
        layout.addWidget(self.num_videos_label)
        layout.addWidget(self.num_videos_input)

        # Fetch button
        self.fetch_button = QPushButton("Fetch Videos", self)
        self.fetch_button.clicked.connect(self.fetch_videos)
        layout.addWidget(self.fetch_button)

        # Results area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.results_layout = QGridLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def clear_results_layout(self):
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def copy_results_to_clipboard(self, videos, start_date, end_date):
        text = f"Top {len(videos)} most viewed videos between {start_date} and {end_date}:\n\n"
        
        for i, video in enumerate(videos, 1):
            text += f"{i}. {video['title']}\n"
            text += f"   Views: {video['viewCount']:,}\n"
            text += f"   Published: {video['publishedAt']}\n"
            text += f"   URL: {video['url']}\n\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Success", "Results copied to clipboard!")

    def fetch_videos(self):
        channel_url = self.channel_url_input.text().strip()
        start_date = self.start_date_input.text().strip()
        end_date = self.end_date_input.text().strip()
        num_videos = self.num_videos_input.value()
        
        # Validate inputs
        if not channel_url:
            QMessageBox.warning(self, "Error", "Please enter a channel URL")
            return
            
        if not self.validate_date(start_date) or not self.validate_date(end_date):
            QMessageBox.warning(self, "Error", "Please enter valid dates in YYYY-MM-DD format")
            return
            
        self.fetch_button.setEnabled(False)
        self.clear_results_layout()
        
        # Create and show progress dialog
        self.progress_dialog = QProgressDialog("Fetching videos...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        
        # Create worker thread
        self.worker = FetchWorker(self.fetcher, channel_url, start_date, end_date, num_videos)
        self.worker.finished.connect(lambda videos: self.display_results(videos, start_date, end_date))
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.cleanup_worker)
        self.worker.start()
    
    def handle_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", error_message)
        self.fetch_button.setEnabled(True)
    
    def cleanup_worker(self):
        self.progress_dialog.close()
        self.worker.deleteLater()
        self.worker = None
        self.fetch_button.setEnabled(True)
    
    def display_results(self, videos, start_date, end_date):
        try:
            # Create header row with copy button
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add header
            header = QLabel(f"Top {len(videos)} most viewed videos between {start_date} and {end_date}:")
            header.setStyleSheet("font-weight: bold; font-size: 14px;")
            header_layout.addWidget(header)
            
            # Add copy button
            copy_button = QPushButton("Copy to Clipboard")
            copy_button.clicked.connect(lambda: self.copy_results_to_clipboard(videos, start_date, end_date))
            copy_button.setMaximumWidth(150)
            header_layout.addWidget(copy_button)
            header_layout.addStretch()
            
            self.results_layout.addWidget(header_widget, 0, 0, 1, 2)
            
            for i, video in enumerate(videos, 1):
                row = i * 2  # Use multiple rows for each video for better spacing
                
                # Create frame for video info
                frame = QFrame()
                frame.setFrameStyle(QFrame.Box | QFrame.Raised)
                frame_layout = QVBoxLayout(frame)
                
                # Add thumbnail
                try:
                    thumbnail_data = requests.get(video['thumbnail']).content
                    pixmap = QPixmap()
                    pixmap.loadFromData(thumbnail_data)
                    thumbnail_label = QLabel()
                    thumbnail_label.setPixmap(pixmap)
                    frame_layout.addWidget(thumbnail_label)
                except Exception as e:
                    print(f"Error loading thumbnail: {e}")
                
                # Add video info
                title_label = QLabel(f"{i}. {video['title']}")
                title_label.setWordWrap(True)
                title_label.setStyleSheet("font-weight: bold;")
                
                views_label = QLabel(f"Views: {video['viewCount']:,}")
                date_label = QLabel(f"Published: {video['publishedAt']}")
                
                frame_layout.addWidget(title_label)
                frame_layout.addWidget(views_label)
                frame_layout.addWidget(date_label)
                
                # Add open in browser button
                open_button = QPushButton("Open in Browser")
                open_button.clicked.connect(lambda checked, url=video['url']: self.open_url(url))
                frame_layout.addWidget(open_button)
                
                self.results_layout.addWidget(frame, row, 0)
            
            # Add stretch to bottom to keep everything aligned to top
            self.results_layout.setRowStretch(len(videos) * 2 + 1, 1)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec_())