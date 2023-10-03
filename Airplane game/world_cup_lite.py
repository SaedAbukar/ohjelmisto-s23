import mysql.connector
import random
import story
from penalties import penalty_shootout
import colorama
from geopy import distance

conn = mysql.connector.connect(
    host='localhost',
    port=3306,
    database='footy',
    user='root',
    password='12345678',
    autocommit=True
)


def get_fields():
    sql = """SELECT * from wc_fields ORDER BY RAND();"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql)
    result = cursor.fetchall()
    return result


# get all goals
def get_opponents():
    sql = "SELECT * FROM world;"
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql)
    result = cursor.fetchall()
    return result


def create_game(start_points, p_range, cur_airport, p_name, a_fields):
    sql = "INSERT INTO game (points, player_range, location, screen_name) VALUES (%s, %s, %s, %s);"
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (start_points, p_range, cur_airport, p_name))
    o_id = cursor.lastrowid

    # add goals / loot boxes
    opponents = get_opponents()
    opp_list = []
    for opp in opponents:
        for i in range(0, opp['probability'], 1):
            opp_list.append(opp['id'])

    # exclude starting airport
    opp_ports = a_fields[1:].copy()
    random.shuffle(opp_ports)

    for i, opp_id in enumerate(opp_list):
        sql = "INSERT INTO arenas (game, airport, goal) VALUES (%s, %s, %s);"
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (o_id, opp_ports[i]['ident'], opp_id))

    return o_id


# get airport info
def get_field_info(icao):
    sql = f'''SELECT iso_country, ident, name, latitude_deg, longitude_deg
                  FROM wc_fields
                  WHERE ident = %s'''
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (icao,))
    result = cursor.fetchone()
    return result


def check_goal(g_id, cur_airport):
    sql = f'''SELECT arenas.id, goal, name, points 
    FROM arenas 
    JOIN world ON world.id = arenas.goal 
    WHERE game = %s 
    AND airport = %s'''
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (g_id, cur_airport))
    result = cursor.fetchone()
    if result is None:
        return False
    return result


def calculate_distance(current, target):
    start = get_field_info(current)
    end = get_field_info(target)
    return distance.distance((start['latitude_deg'], start['longitude_deg']),
                             (end['latitude_deg'], end['longitude_deg'])).km


# get airports in range
def fields_in_range(icao, a_fields, p_range):
    in_range = []
    for a_fields in a_fields:
        dist = calculate_distance(icao, a_fields['ident'])
        if dist <= p_range and not dist == 0:
            in_range.append(a_fields)
    return in_range


def update_location(icao, p_range, u_points, g_id):
    sql = f'''UPDATE game SET location = %s, player_range = %s, points = %s WHERE id = %s'''
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (icao, p_range, u_points, g_id))


# game stars
# game loop
def main():
    visited_fields = []
    lohkopeli_voitot = 0
    storyDialog = input('Haluatko lukea pelin tarinan? (K/E): ').lower()
    if storyDialog == 'k':
        for line in story.get_story():
            print(line)

    print('Tervetuloa Yhdysvaltojen, Meksikon ja Kanadan 2026 MM-kisoihin.')
    player = input('Syötä pelaaja nimesi: ')

    # check if the game is over
    game_over = False

    # check if the player has won
    win = False

    # starting money
    points = 0

    # starting range
    player_range = 5000

    played = 0

    # count the player score
    score = 0

    # all airports
    all_fields = get_fields()
    # starting point
    start_fields = all_fields[0]['ident']

    # current airport
    current_field = start_fields

    # game id
    game_id = create_game(points, player_range, start_fields, player, all_fields)

    while not game_over:
        print(f'Ottelut {played}/7. Voitot {score}/{played}. '
              f'Sinulla on jäljellä {7 - played} ottelua.')
        # get current airport info
        airport = get_field_info(current_field)
        print(f"Saavuit jalkapallokentälle: {airport['name']}.")
        input('\033[32mPaina Enteriä selvittääksesi onko kentällä vastustaja...\033[0m')
        # if airport has an opponent the player plays them
        # check the goal type and add if wins
        goal = check_goal(game_id, current_field)
        if goal:
            print('Tällä kentällä on vastustaja. Valmistaudu!')
            winning_team = penalty_shootout(goal['name'])
            if winning_team == 'Suomi':
                score += 1
                played += 1
                points += goal['points']
                player_range += 500
                lohkopeli_voitot += 1
                print(f"Ottelun voittaja on {winning_team}!")
            else:
                print(f'Peli päättyi. Hävisit ottelun. Onnea seuraavaan koitokseen!')
                played += 1

        else:
            print(f'Tällä kentällä ei ole vastustajaa. Siirry seuraavalle kentälle')

        if played >= 3 and lohkopeli_voitot >= 2:
            print(f'Onnittelut! Selvisit pudotuspelikierrokselle!')
            fields = fields_in_range(current_field, all_fields, player_range)
            print(f'Voit lentää näin monelle jalkapallokentälle {len(fields)}')
            print('Jalkapallokentät:')
            for field in fields:
                f_distance = calculate_distance(current_field, field['ident'])
                print(
                    f"ICAO: {field['ident']}, Name: {field['name']}, Distance: {f_distance:.0f}km")  # MIKÄLI ICAO KOODI ON LISTAA ÄLÄ NÄYTÄ
                # NÄYTÄ VÄRILLÄ MISSÄ KÄYNYT JA TULOKSET

            try:
                dest = input('Syötä kohdekentän ICAO: ')
                while dest in visited_fields:
                    print("Olet jo vieraillut tässä kentässä!")
                    dest = input('Syötä uuden kohdekentän ICAO: ')

                else:
                    selected_distance = calculate_distance(current_field, dest)
                    update_location(dest, player_range, points, game_id)
                    current_field = dest
                    # Inside the loop where the player selects the destination field (after updating current_field):
                    visited_fields.append(current_field)
            except ValueError:
                print(f'Virheellinen syöte. Syötä vaihtoehdoista haluamasi kohdekentän ICAO-koodi:')

            i = 0
            pudotuspeli_voitot = 0
            pudotuspeli_häviöt = 0
            while pudotuspeli_voitot < 4 and pudotuspeli_häviöt < 1:
                if played >= 7 and pudotuspeli_voitot >= 4 or pudotuspeli_häviöt > 0:
                    game_over = True
                vaiheet = ['16-parhaan joukko', '8-parhaan joukko', 'Semi-finaali', 'Finaali']
                print(f'Pudotuspelivaihe: {vaiheet[i]}.')
                input('\033[32mPaina Enteriä selvittääksesi onko kentällä vastustaja...\033[0m')
                goal = check_goal(game_id, current_field)
                if goal:
                    print('Tällä kentällä on vastustaja. Valmistaudu!')
                    winning_team = penalty_shootout(goal['name'])
                    if winning_team == 'Suomi':
                        score += 1
                        played += 1
                        pudotuspeli_voitot += 1
                        points += goal['points']
                        player_range += 500
                        i += 1
                        print(f"Ottelun voittaja on {winning_team}!")
                        if played >= 7 and pudotuspeli_voitot >= 4 or pudotuspeli_häviöt > 0:
                            game_over = True
                        else:
                            # Move to the next field
                            fields = fields_in_range(current_field, all_fields, player_range)
                            print(f'Voit lentää näin monelle jalkapallokentälle. {len(fields)}')
                            print('Jalkapallokentät:')
                            for field in fields:
                                f_distance = calculate_distance(current_field, field['ident'])
                                print(
                                    f"ICAO: {field['ident']}, Name: {field['name']}, Distance: {f_distance:.0f}km")  # MIKÄLI ICAO KOODI ON LISTAA ÄLÄ NÄYTÄ
                                # NÄYTÄ VÄRILLÄ MISSÄ KÄYNYT JA TULOKSET

                            try:
                                dest = input('Syötä kohdekentän ICAO: ')
                                while dest in visited_fields:
                                    print("Olet jo vieraillut tässä kentässä!")
                                    dest = input('Syötä uuden kohdekentän ICAO: ')

                                else:
                                    selected_distance = calculate_distance(current_field, dest)
                                    update_location(dest, player_range, points, game_id)
                                    current_field = dest
                                    # Inside the loop where the player selects the destination field (after updating current_field):
                                    visited_fields.append(current_field)
                            except ValueError:
                                print(f'Virheellinen syöte. Syötä vaihtoehdoista haluamasi kohdekentän ICAO-koodi:')
                    else:
                        print(f'Voi ei! Hävisit rangaistuspotkukilpailun!'
                              f' Tällä kertaa matkasi loppui pudotuspelivaiheeseen: {vaiheet[i]}.')
                        pudotuspeli_häviöt += 1
                        played += 1
                        game_over = True
                else:
                    print(f'Tällä kentällä ei ole vastustajaa. Siirry seuraavalle kentälle')

        if played >= 3 and lohkopeli_voitot < 2:
            print(f'Valitettavasti et voittanut kahta peliä kolmesta lohkopeliotteluista.'
                  f'Sinun MM-kisa taivel päättyy tähän. Parempaa onnea seuraaviin kisoihin!')
            game_over = True

        if played == 7:
            game_over = True

        if played < 3:
            fields = fields_in_range(current_field, all_fields, player_range)
            print(f'Voit lentää näin monelle jalkapallokentälle {len(fields)}.')
            print('Jalkapallokentät:')
            for field in fields:
                f_distance = calculate_distance(current_field, field['ident'])
                print(
                    f"ICAO: {field['ident']}, Name: {field['name']}, Distance: {f_distance:.0f}km")  # MIKÄLI ICAO KOODI ON LISTAA ÄLÄ NÄYTÄ
                # NÄYTÄ VÄRILLÄ MISSÄ KÄYNYT JA TULOKSET

            try:
                dest = input('Syötä kohdekentän ICAO: ')
                while dest in visited_fields:
                    print("Olet jo vieraillut tässä kentässä!")
                    dest = input('Syötä uuden kohdekentän ICAO: ')

                else:
                    selected_distance = calculate_distance(current_field, dest)
                    update_location(dest, player_range, points, game_id)
                    current_field = dest
                    # Inside the loop where the player selects the destination field (after updating current_field):
                    visited_fields.append(current_field)
            except ValueError:
                print(f'Virheellinen syöte. Syötä vaihtoehdoista haluamasi kohdekentän ICAO-koodi:')

    if score == 7:
        print(f'Se oli siinä! POIKA TULI KOTIIN!!!')
        print(f'Pelasit turnauksen kunniakkaasti loppuun ja voitit jokaisen ottelun!')
        print(f'SUOMI ON MAAILMANMESTARI!')
        print(f'Pelasit {played} ottelua ja voitit {score} ottelua. Sait {points} verran pisteitä!')
    else:
        print(f'Taistelit hienosti, mutta et valitettavasti voittanut jokaista peliä.')
        print(f'Pelasit {played} ottelua ja voitit {score} ottelua. Sait {points} verran pisteitä!')
        print(f'Parempaa menestystä seuraavalle kerralle!')


main()

# TODO
"""
Lisää peliin virhekontrollit. 
Parantele pelin käyttettävyyttä yksinkertaistamalla ja selkeyttämällä python terminaalia.
Jos ehdit lisää vinkki kysymyksiä ja muita pelejä
"""