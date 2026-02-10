from src.parsers.flight_parser import parse_flight_email


def test_parse_vietjet_email():
    email = {
        "subject": "Your VietJet Reservation #ABC123",
        "from": "noreply@vietjetair.com",
        "body": (
            "Reservation # ABC123\n"
            "Flight No. VJ 1234\n"
            "From: SGN To: HAN\n"
            "Date: 12 March 2026\n"
        ),
    }

    result = parse_flight_email(email)

    assert result is not None
    assert result.airline == "VietJet Air"
    assert result.flight_number == "VJ1234"
    assert result.departure_airport == "SGN"
    assert result.arrival_airport == "HAN"
    assert result.departure_datetime == "12 March 2026"


def test_parse_generic_email():
    email = {
        "subject": "Flight confirmation",
        "from": "no-reply@example.com",
        "body": (
            "Flight: AA 123\n"
            "From: JFK To: LAX\n"
            "Confirmation Code: ZXCVBN\n"
        ),
    }

    result = parse_flight_email(email)

    assert result is not None
    assert result.flight_number == "AA123"
    assert result.departure_airport == "JFK"
    assert result.arrival_airport == "LAX"


def test_parse_generic_email_spanish():
    email = {
        "subject": "LATAM - Confirmacion de vuelo",
        "from": "info@latam.com",
        "body": (
            "Vuelo: LA 4567\n"
            "De: Sao Paulo (GRU) a Fortaleza (FOR)\n"
            "Codigo de reserva: ABC123\n"
        ),
    }

    result = parse_flight_email(email)

    assert result is not None
    assert result.airline == "LATAM Airlines"
    assert result.flight_number == "LA4567"
    assert result.departure_airport == "GRU"
    assert result.arrival_airport == "FOR"


def test_parse_generic_email_portuguese():
    email = {
        "subject": "Confirmacao de voo",
        "from": "noreply@voegol.com.br",
        "body": (
            "Voo: G3 4321\n"
            "Origem: Rio de Janeiro (GIG) Destino: Salvador (SSA)\n"
            "Confirmacao: QWERTY\n"
        ),
    }

    result = parse_flight_email(email)

    assert result is not None
    assert result.airline == "GOL"
    assert result.flight_number == "G34321"
    assert result.departure_airport == "GIG"
    assert result.arrival_airport == "SSA"
