# Итоговый проект по теме API
# В данном проекте демонстрируется взаимодейстивие трех различных сервисов. Обращение к трем сервисам происходит при помощи API
# С помощью сервиса Яндекс.Диалоги программа взаимодействует с пользоватлем и другими сервисами
# С помощью сервиса  Портала открытых данный Правительства Москвы data.mos.ru мы получаем инфомацию о координатах и времени работы всех входов-выходов (вестибюлей) станций Московского метро
# С помощью сервиса Яндекс.Карты мы отображаем полученную инфомацию на карте Москвы
# На основании введенного запроса Яндекс.Диалог определяет ввели ли мы название станции метро или Адрес объекта
# Если введено названии станции метро, то на карте выводятся расположение всех выходов данной станции
# Если введен адрес, то на карту выводится ближайший вход-выход ближайшей станции метро, с указанием расстояния до выхода и информацией о времени его работы.

from flask import Flask, request
import logging
import json
import requests
import math
# импортируем функции из нашего второго файла geo

app = Flask(__name__)

# Добавляем логирование в файл. Чтобы найти файл,
# перейдите на pythonwhere в раздел files, он лежит в корневой папке
logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

sessionStorage = {}

@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Request: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None,  # здесь будет храниться имя
            'game_started': False  # здесь информация о том, что пользователь начал игру. По умолчанию False
        }
        sessionStorage[user_id]['mosru'] = get_from_mos_ru()
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. \n Предлагаю тебе узнать информацию о станциях метрополитена в г. Москва.\nНапиши любую станцию метро Москвы и я запрошу актуальную информацию с сайта apidata.mos.ru и покажу тебе время работы и расположение всех вестибюлей данной станции.\n Или введи адрес, чтобы я при помощи api сервиса Яндекс.Карты показала ближайший к данному адресу вестибюль станции метро'
            res['response']['buttons'] = [
                {
                    'title': 'Чертановская',
                    'hide': True
                },
                {
                    'title': 'Варшавское шоссе, 102',
                    'hide': True
                },
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
    else:
        get_inf(res, req)


def get_image_id(coords=[], llt_metro=[], pt=""):

    try:
        map_request = "http://static-maps.yandex.ru/1.x/?l=map&pt="
        if len(coords) > 0:
            ll = ",".join(coords)
            # map_request = "http://static-maps.yandex.ru/1.x/?ll=" + ll + "&l=map&pt="
            map_request = "http://static-maps.yandex.ru/1.x/?ll=" + ll + "&z=14&l=map&pt="
            map_request += ll + ",pmrdl"
        if len(llt_metro) == 4:
            map_request += "~" + llt_metro[0] + "," + llt_metro[1] + ",pmgnl"
        if pt != "":
            map_request += pt
        response = requests.get(map_request)
        # Запишем полученное изображение в файл.
        map_file = "map.png"
        with open(map_file, "wb") as file:
            file.write(response.content)
        files = {'file': open(map_file, 'rb')}
        headers_upload = {'Authorization': 'OAuth AQAAAAAgMjS0AAT7oxlz6733GEdEiHTx6xFZzzc'}
        url = "https://dialogs.yandex.net/api/v1/skills/d4de82b1-df0c-4454-ae08-c2eb945cb883/images"
        # загружаем файл
        r = requests.post(url, files=files, headers=headers_upload)
        return r.json()['image']['id']
    except Exception as e:
        return False




def get_inf(res, req):
    user_id = req['session']['user_id']
    inf = metro_or_adr(req)
    sessionStorage[user_id]['MyStation'] = []
    pt = ''
    out_title = ''
    if req['request']['original_utterance'].lower() == 'помощь':
        res['response']['text'] = 'Предлагаю тебе узнать информацию о станциях метрополитена в г. Москва.\nНапиши любую станцию метро Москвы и я запрошу актуальную информацию с сайта apidata.mos.ru и покажу тебе время работы и расположение всех вестибюлей данной станции.\n Или введи адрес, чтобы я при помощи api сервиса Яндекс.Карты показала ближайший к данному адресу вестибюль станции метро'
        return
    for elem in sessionStorage[user_id]['mosru']:
        if req['request']['original_utterance'].lower() == elem['Cells']['NameOfStation'].lower():
            out_title = elem['Cells']['NameOfStation']
            sessionStorage[user_id]['MyStation'].append(elem['Cells'])
    if len(sessionStorage[user_id]['MyStation']):
        res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
        res['response']['text'] = 'Все выходы станции метро' + out_title
        out_desc = ''
        for elem in sessionStorage[user_id]['MyStation']:
            out_desc += elem['Name'] + "\n" + elem['ModeOnEvenDays'] + "\n\n"
            pt += str(elem['geoData']['coordinates'][0]) + "," + str(elem['geoData']['coordinates'][1]) + ",pmgnl~"
        img = get_image_id([], [], pt[:-1])
        if img:
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
            res['response']['card'] = {}
            res['response']['card']['type'] = "BigImage"
            res['response']['card']['image_id'] = str(img)
            res['response']['card']['title'] = "м. " + out_title
            res['response']['card']['description'] = "Расположение вестибюлей "
        else:
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
            res['response']['text'] = 'Хотела показать карту, но что-то пошло не так. Попробуй еще разок!'

    elif inf == None:
        res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
        res['response']['text'] = 'Я не поняла, что ты написал!'
    else:
        res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
        adress = inf['street'].title() + " " + inf['house_number']
        ll = get_coordinates(adress)
        res['response']['text'] = 'Ближейший выход метро'
        sessionStorage[user_id]['adress'] = ' '.join([elem for elem in inf.values()])
        llt_metro = get_near_metro(ll, sessionStorage[user_id]['mosru'])
        img = get_image_id([str(ll[0]),str(ll[1])], llt_metro)
        if img:
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
            res['response']['card'] = {}
            res['response']['card']['type'] = "BigImage"
            res['response']['card']['image_id'] = str(img)
            res['response']['card']['title'] = adress
            res['response']['card']['description'] = "Ближейший выход метро " + llt_metro[3] + "\n" + llt_metro[2]
        else:
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
            res['response']['text'] = 'Хотела показать карту, но что-то пошло не так. Попробуй еще разок!'



def metro_or_adr(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO, то пытаемся получить город(city), если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value']
    return None



def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)

def get_from_mos_ru():
    # не получается загрузить данные онлайн, так как похоже мос.ру не отдает данные зарубежным серверам
    # url = "https://apidata.mos.ru/v1/datasets/624/rows?api_key=c95e635847035ffad1dce6ae0800cf65"
    # req = requests.get(url, verify=False)
    # return req.json()
    # поэтому данные загружены в файл вручную и закачены на сервер в файл metro.json
    with open('/home/Bruks/mysite/metro.json', encoding='utf-8', newline='') as f:
        data = json.load(f)
    return data


def get_near_metro(ll, list_metro):

    min = 100000000
    min_ll = ["",""]
    min_text = ""
    min_dist = ""
    for elem in list_metro:
        try:
            cur = lonlat_distance([elem['Cells']['geoData']['coordinates'][0], elem['Cells']['geoData']['coordinates'][1]], [ll[0], ll[1]])
            if cur < min:
                min = cur
                min_ll = [elem['Cells']['geoData']['coordinates'][0], elem['Cells']['geoData']['coordinates'][1]]
                min_text = elem['Cells']['Name'] + "\n" + elem['Cells']['ModeOnEvenDays']
                min_dist = str(round(cur)) + "м. "
        except:
            pass
    return [str(min_ll[0]), str(min_ll[1]), min_text, min_dist]
    


# Определяем функцию, считающую расстояние между двумя точками, заданными координатами
def lonlat_distance(a, b):
    
    degree_to_meters_factor = 111 * 1000 # 111 километров в метрах
    a_lon = float(a[0])
    a_lat = float(a[1])
    b_lon = float(b[0])
    b_lat = float(b[1])

    # Берем среднюю по широте точку и считаем коэффициент для нее.
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    # Вычисляем смещения в метрах по вертикали и горизонтали.
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    # Вычисляем расстояние между точками.
    distance = math.sqrt(dx * dx + dy * dy)

    return distance


def get_coordinates(city_name):
    try:
        # url, по которому доступно API Яндекс.Карт
        url = "https://geocode-maps.yandex.ru/1.x/"
        # параметры запроса
        params = {
            'll': '37.618920,55.756994',
            'spn': '3.552069,2.400552',
            # город, координаты которого мы ищем
            'geocode': city_name,
            # формат ответа от сервера, в данном случае JSON
            'format': 'json'
        }
        # отправляем запрос
        response = requests.get(url, params)
        # получаем JSON ответа
        json = response.json()
        # получаем координаты города (там написаны долгота(longitude),
        # широта(latitude) через пробел).
        coordinates_str = json['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['Point']['pos']
        # Превращаем string в список, так как точка -
        # это пара двух чисел - координат
        long, lat = map(float, coordinates_str.split())
        # Вернем ответ
        return long, lat
    except Exception as e:
        return e