import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app import app, get_coordinates, get_weather_icon, get_weather_data


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_get_weather_icon():
    assert get_weather_icon(0) == '☀️'
    assert get_weather_icon(1) == '⛅'
    assert get_weather_icon(45) == '🌫️'
    assert get_weather_icon(95) == '⛈️'
    assert get_weather_icon(100) == '🌀'


@patch('app.requests.get')
def test_get_coordinates_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{'lat': '55.7558', 'lon': '37.6173'}]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    lat, lon = get_coordinates("Москва")
    assert lat == 55.7558
    assert lon == 37.6173


@patch('app.requests.get')
def test_get_coordinates_failure(mock_get):
    mock_get.side_effect = Exception("API Error")
    lat, lon = get_coordinates("Несуществующий город")
    assert lat is None
    assert lon is None


@patch('app.requests.get')
def test_get_weather_data_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'hourly': {
            'time': ['2023-01-01T00:00', '2023-01-01T01:00'],
            'temperature_2m': [15.0, 14.5],
            'weathercode': [0, 1]
        },
        'current_weather': {
            'temperature': 15.5,
            'windspeed': 10.2
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with patch('app.get_coordinates', return_value=(55.75, 37.61)):
        weather_data, error = get_weather_data("Москва")
        assert error is None
        assert weather_data['city'] == "Москва"
        assert weather_data['current_temp'] == 15.5
        assert len(weather_data['hourly_forecast']) == 2
        assert weather_data['hourly_forecast'][0]['time'] == '00:00'


@patch('app.get_coordinates')
def test_get_weather_data_city_not_found(mock_get_coords):
    mock_get_coords.return_value = (None, None)
    weather_data, error = get_weather_data("Несуществующий город")
    assert weather_data is None
    assert error == "Не удалось найти город: Несуществующий город"


def test_index_route_get(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Прогноз погоды'.encode('utf-8') in response.data


def test_index_route_post(client):
    with patch('app.get_weather_data', return_value=({'city': 'Москва'}, None)):
        response = client.post('/', data={'city': 'Москва'})
        assert response.status_code == 200
        assert 'Москва'.encode('utf-8') in response.data


def test_index_route_with_cookie(client):
    with patch('app.get_weather_data', return_value=({'city': 'Санкт-Петербург'}, None)):

        response = client.get('/', headers={'Cookie': 'last_city=Санкт-Петербург'})
        assert response.status_code == 200
        assert 'Санкт-Петербург'.encode('utf-8') in response.data


def test_cookie_setting(client):
    with patch('app.get_weather_data', return_value=({'city': 'Казань'}, None)):
        response = client.post('/', data={'city': 'Казань'})
        assert response.status_code == 200

        set_cookie_header = response.headers.get('Set-Cookie', '')

        assert 'last_city=' in set_cookie_header


@patch('app.requests.get')
def test_full_flow(mock_get, client):
    mock_nominatim = MagicMock()
    mock_nominatim.json.return_value = [{'lat': '55.7558', 'lon': '37.6173'}]
    mock_nominatim.raise_for_status.return_value = None

    mock_meteo = MagicMock()
    mock_meteo.json.return_value = {
        'hourly': {
            'time': ['2023-01-01T00:00'],
            'temperature_2m': [15.0],
            'weathercode': [0]
        },
        'current_weather': {
            'temperature': 15.5,
            'windspeed': 10.2
        }
    }
    mock_meteo.raise_for_status.return_value = None

    mock_get.side_effect = [mock_nominatim, mock_meteo]

    response = client.post('/', data={'city': 'Москва'})
    assert response.status_code == 200
    assert 'Москва'.encode('utf-8') in response.data
    assert '15.5'.encode('utf-8') in response.data


@patch('app.requests.get')
def test_weather_api_error(mock_get):
    mock_get.side_effect = Exception("Weather API Error")
    with patch('app.get_coordinates', return_value=(55.75, 37.61)):
        weather_data, error = get_weather_data("Москва")
        assert weather_data is None
        assert "Ошибка при получении погоды: Weather API Error" in error


def test_time_formatting():
    from app import datetime
    test_time = "2023-01-01T12:34:56"
    formatted = datetime.fromisoformat(test_time).strftime('%H:%M')
    assert formatted == "12:34"