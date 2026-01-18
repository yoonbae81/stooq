#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys
import pickle
import warnings

# Suppress urllib3 v2 OpenSSL warning on macOS
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

# Add src to python path to allow importing download
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import download

class TestDownload(unittest.TestCase):

    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.headers = {}
        self.mock_session.cookies = MagicMock()
        
    @patch('src.download.os.makedirs')
    def test_setup_directories(self, mock_makedirs):
        # Test with custom arguments
        data_dir, cookie_dir = download.setup_directories("custom_data", "custom_cookies")
        self.assertEqual(data_dir, "custom_data") 
        self.assertEqual(cookie_dir, "custom_cookies")
        self.assertEqual(mock_makedirs.call_count, 2)

    @patch('src.download.requests.Session')
    def test_create_session(self, mock_session_cls):
        mock_instance = MagicMock()
        mock_session_cls.return_value = mock_instance
        
        session = download.create_session(user_agent="TestAgent")
        
        mock_session_cls.assert_called_once()
        self.assertEqual(session, mock_instance)
        mock_instance.headers.update.assert_called_with({'User-Agent': 'TestAgent'})

    @patch('builtins.open', new_callable=mock_open)
    @patch('src.download.pickle.dump')
    def test_save_session(self, mock_dump, mock_file):
        mock_context = MagicMock()
        mock_context.cookies.return_value = [{'name': 'test_cookie', 'value': 'test_value'}]
        
        download.save_session(mock_context, self.mock_session, "dummy_path.pkl")
        
        self.mock_session.cookies.set.assert_called_with('test_cookie', 'test_value')
        mock_file.assert_called_with("dummy_path.pkl", 'wb')
        mock_dump.assert_called()

    @patch('src.download.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.download.pickle.load')
    def test_load_session_valid(self, mock_load, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_load.return_value = {'saved_cookie': 'value'}
        
        # Mocking the session.get response to simulate a valid session
        mock_response = MagicMock()
        mock_response.text = "Logged in content" # Does not contain "Potwierdzam" or "f15"
        self.mock_session.get.return_value = mock_response

        result = download.load_session(self.mock_session, "dummy_path.pkl")
        
        self.assertTrue(result)
        self.mock_session.cookies.update.assert_called()
        self.mock_session.get.assert_called_with("https://stooq.com/db/", timeout=10)

    @patch('src.download.os.path.exists')
    def test_load_session_no_file(self, mock_exists):
        mock_exists.return_value = False
        result = download.load_session(self.mock_session, "dummy_path.pkl")
        self.assertFalse(result)

    def test_get_latest_download_link_found_1200(self):
        # Mock HTML content with a 12:00 row
        html_content = """
        <html><body>
        <table>
        <tr><td>Some Data</td></tr>
        <tr><td>12:00</td><td><a href="db/d/?d=20260116&t=d">0116_d</a></td><td><a href="db/d/?d=20260116&t=h">0116_h</a></td><td><a href="db/d/?d=20260116&t=5">0116_5</a></td></tr>
        </table>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        self.mock_session.get.return_value = mock_response
        
        links = download.get_latest_download_link(self.mock_session)
        
        self.assertIsNotNone(links)
        self.assertEqual(len(links), 3)
        expected_links = [
            ("https://stooq.com/db/d/?d=20260116&t=d", "0116_d"),
            ("https://stooq.com/db/d/?d=20260116&t=h", "0116_h"),
            ("https://stooq.com/db/d/?d=20260116&t=5", "0116_5")
        ]
        self.assertEqual(links, expected_links)

    def test_get_latest_download_link_fallback(self):
        # Mock HTML content WITHOUT a 12:00 row but with data links
        html_content = """
        <html><body>
        <table>
        <tr><td>No Time</td><td><a href="db/d/?d=20260116&t=d">0116_d</a></td></tr>
        </table>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        self.mock_session.get.return_value = mock_response
        
        links = download.get_latest_download_link(self.mock_session)
        
        self.assertIsNotNone(links)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], ("https://stooq.com/db/d/?d=20260116&t=d", "0116_d"))

    @patch('builtins.open', new_callable=mock_open)
    def test_start_download_success(self, mock_file):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
        self.mock_session.get.return_value = mock_response
        
        result = download.start_download(self.mock_session, "http://example.com/file.zip", "test_file", "/tmp")
        
        self.assertTrue(result)
        self.mock_session.get.assert_called_with("http://example.com/file.zip", stream=True)
        # Expect .csv extension now
        mock_file.assert_called_with("/tmp/test_file.csv", 'wb')
        handle = mock_file()
        handle.write.assert_any_call(b'chunk1')
        handle.write.assert_any_call(b'chunk2')

    def test_start_download_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        self.mock_session.get.return_value = mock_response
        
        result = download.start_download(self.mock_session, "http://example.com/file.zip", "test_file", "/tmp")
        
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
