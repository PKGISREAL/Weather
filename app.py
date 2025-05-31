from flask import Flask, render_template, url_for, request, make_response
import requests
from collections import Counter
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.jinja_env.globals.update(zip=zip)



def get_coordinates(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json"
        headers = {'User-Agent': 'MyWeatherApp/1.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None, None
    except Exception as e:
        print(f"Ошибка при получении координат: {e}")
        return None, None


def get_weather_icon(code):
    if code == 0: return '☀️'
    elif code in [1, 2, 3]: return '⛅'
    elif code in [45, 48]: return '🌫️'
    elif code in [51, 53, 55]: return '🌧️'
    elif code in [61, 63, 65]: return '🌧️'
    elif code in [71, 73, 75]: return '❄️'
    elif code in [80, 81, 82]: return '🌧️'
    elif code in [85, 86]: return '❄️'
    elif code in [95, 96, 99]: return '⛈️'
    else: return '🌀'


@app.route('/', methods=['GET', 'POST'])
def weather():

    city = request.form.get('city', '')


    if not city:
        city = request.cookies.get('last_city', 'Москва')


    weather_data, error = get_weather_data(city)


    response = make_response(render_template(
        'weather.html',
        weather=weather_data,
        error=error,
        last_city=city if city != 'Москва' else None
    ))


    if weather_data and not error:
        response.set_cookie(
            'last_city',
            city,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=True
        )

    return response


def get_weather_data(city):
    """Обертка для получения данных о погоде с обработкой ошибок"""
    weather_data = None
    error = None

    latitude, longitude = get_coordinates(city)

    if latitude is None or longitude is None:
        error = f"Не удалось найти город: {city}"
    else:
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': 'temperature_2m,weathercode',
                'current_weather': 'true',
                'timezone': 'auto',
                'forecast_days': 1
            }

            response = requests.get("https://api.open-meteo.com/v1/forecast", params=params)
            data = response.json()

            most_common_code = Counter(data['hourly']['weathercode']).most_common(1)[0][0]


            hourly_data = []
            for time, temp, code in zip(data['hourly']['time'],
                                        data['hourly']['temperature_2m'],
                                        data['hourly']['weathercode']):
                hour = datetime.fromisoformat(time).strftime('%H:%M')
                hourly_data.append({
                    'time': hour,
                    'temp': temp,
                    'icon': get_weather_icon(code)
                })

            weather_data = {
                'city': city,
                'current_temp': data['current_weather']['temperature'],
                'current_windspeed': data['current_weather']['windspeed'],
                'current_weather_icon': get_weather_icon(most_common_code),
                'hourly_forecast': hourly_data
            }

        except Exception as e:
            error = f"Ошибка при получении погоды: {e}"

    return weather_data, error



if __name__ == "__main__":
    app.run(debug=True)