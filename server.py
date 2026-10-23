import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, flash, url_for

MAX_PLACES_PER_COMPETITION = 12
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def loadClubs():
    with open('clubs.json') as c:
        return json.load(c)['clubs']


def loadCompetitions():
    with open('competitions.json') as comps:
        return json.load(comps)['competitions']


app = Flask(__name__)
app.secret_key = 'something_special'

competitions = loadCompetitions()
clubs = loadClubs()

# Places déjà réservées : {(nom_competition, nom_club): nombre_de_places}
bookings = {}


def find_club_by_email(email):
    email = email.strip().lower()
    return next(
        (c for c in clubs if c['email'].lower() == email), None
    )


def find_club_by_name(name):
    return next((c for c in clubs if c['name'] == name), None)


def find_competition(name):
    return next((c for c in competitions if c['name'] == name), None)


def is_past(competition):
    date = datetime.strptime(competition['date'], DATE_FORMAT)
    return date < datetime.now()


def render_welcome(club):
    competitionsWithStatus = [dict(c, past=is_past(c)) for c in competitions]
    return render_template(
        'welcome.html',
        club=club,
        competitions=competitionsWithStatus
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/showSummary', methods=['POST'])
def showSummary():
    club = find_club_by_email(request.form.get('email', ''))
    if club is None:
        flash("Sorry, that email wasn't found.")
        return redirect(url_for('index'))
    return render_welcome(club)


@app.route('/book/<competition>/<club>')
def book(competition, club):
    foundClub = find_club_by_name(club)
    foundCompetition = find_competition(competition)

    if foundClub is None or foundCompetition is None:
        flash("Something went wrong-please try again")
        if foundClub is None:
            return redirect(url_for('index'))
        return render_welcome(foundClub)

    if is_past(foundCompetition):
        flash("You cannot book places for a past competition.")
        return render_welcome(foundClub)

    return render_template(
        'booking.html',
        club=foundClub,
        competition=foundCompetition
    )


@app.route('/purchasePlaces', methods=['POST'])
def purchasePlaces():
    competition = find_competition(request.form.get('competition', ''))
    club = find_club_by_name(request.form.get('club', ''))

    if competition is None or club is None:
        flash("Something went wrong-please try again")
        return redirect(url_for('index'))

    # Validation du nombre de places
    try:
        placesRequired = int(request.form.get('places', ''))
    except ValueError:
        flash("Please enter a valid number of places.")
        return render_welcome(club)

    if placesRequired <= 0:
        flash("You must book at least 1 place.")
        return render_welcome(club)

    if is_past(competition):
        flash("You cannot book places for a past competition.")
        return render_welcome(club)

    bookingKey = (competition['name'], club['name'])
    alreadyBooked = bookings.get(bookingKey, 0)
    if alreadyBooked + placesRequired > MAX_PLACES_PER_COMPETITION:
        flash(
            f"You cannot book more than {MAX_PLACES_PER_COMPETITION} "
            "places per competition."
        )
        return render_welcome(club)

    if placesRequired > int(club['points']):
        flash("You do not have enough points.")
        return render_welcome(club)

    availablePlaces = int(competition['numberOfPlaces'])
    if placesRequired > availablePlaces:
        flash("Not enough places available in this competition.")
        return render_welcome(club)

    # Réservation valide : on met à jour places, points et compteur
    competition['numberOfPlaces'] = availablePlaces - placesRequired
    club['points'] = int(club['points']) - placesRequired
    bookings[bookingKey] = alreadyBooked + placesRequired

    flash('Great-booking complete!')
    return render_welcome(club)


@app.route('/points')
def points():
    return render_template('points.html', clubs=clubs)


@app.route('/logout')
def logout():
    return redirect(url_for('index'))
