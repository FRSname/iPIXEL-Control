import unittest
from unittest.mock import MagicMock, patch
from integrations.youtube_api import YouTubeAPI
from integrations.weather_api import WeatherAPI
from integrations.stock_api import StockAPI
from integrations.teams_api import TeamsAPI

class TestIntegrations(unittest.TestCase):

    @patch('googleapiclient.discovery.build')
    def test_youtube_api(self, mock_build):
        # Mock YouTube client
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        
        # Mock search response
        mock_youtube.search().list().execute.return_value = {
            'items': [{'id': {'channelId': 'UC123'}}]
        }
        
        # Mock channels response
        mock_youtube.channels().list().execute.return_value = {
            'items': [{
                'snippet': {'title': 'Test Channel'},
                'statistics': {
                    'subscriberCount': '1000',
                    'viewCount': '5000',
                    'videoCount': '50'
                }
            }]
        }
        
        api = YouTubeAPI("fake_key")
        stats = api.get_channel_stats("@test")
        
        self.assertEqual(stats['channel_title'], 'Test Channel')
        self.assertEqual(stats['subscribers'], 1000)
        self.assertEqual(stats['views'], 5000)
        self.assertEqual(stats['videos'], 50)

    @patch('requests.get')
    def test_weather_api(self, mock_get):
        # Mock requests response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'London',
            'main': {'temp': 20.5, 'feels_like': 19.0, 'humidity': 50},
            'weather': [{'main': 'Clear', 'description': 'clear sky'}],
            'wind': {'speed': 5.0}
        }
        mock_get.return_value = mock_response
        
        api = WeatherAPI("fake_key")
        weather = api.get_weather("London")
        
        self.assertEqual(weather['city'], 'London')
        self.assertEqual(weather['temp'], 20.5)
        self.assertEqual(weather['condition'], 'Clear')

    @patch('yfinance.Ticker')
    def test_stock_api(self, mock_ticker):
        # Mock yfinance ticker
        mock_stock = MagicMock()
        mock_stock.info = {
            'currentPrice': 150.0,
            'previousClose': 145.0,
            'shortName': 'Apple Inc.'
        }
        mock_ticker.return_value = mock_stock
        
        api = StockAPI()
        data = api.get_stock_data("AAPL")
        
        self.assertEqual(data['ticker'], 'AAPL')
        self.assertEqual(data['price'], 150.0)
        self.assertEqual(data['name'], 'Apple Inc.')
        self.assertAlmostEqual(data['change'], 5.0)

    @patch('requests.post')
    @patch('requests.get')
    def test_teams_api(self, mock_get, mock_post):
        # Mock token response
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {'access_token': 'fake_token'}
        mock_post.return_value = mock_post_resp
        
        # Mock presence response
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            'availability': 'Available',
            'activity': 'Available'
        }
        mock_get.return_value = mock_get_resp
        
        api = TeamsAPI("tenant", "client", "secret")
        presence = api.get_user_presence("user@example.com")
        
        self.assertEqual(presence['availability'], 'Available')
        self.assertEqual(presence['activity'], 'Available')

if __name__ == '__main__':
    unittest.main()
