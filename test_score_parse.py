from app import create_app
from app.models import Team, Fixture
import re

app = create_app()

def test_score_parse():
    test_input = """Pep and the City    83    Back Fixes Matter    96.5
Bayern Bru    92.75    Wirtz Case Scenario    73.25
Scharshank Redemption    107.25    Udogie Style    56
The Mask of Yoro    85.5    Freedyonfire    73.75
Pique Blinders    107    Chicken Tikka MoSalah    123.25
Huss will be missed !    100.5    Dango Unchained 👑    123.5"""

    print("Testing score parsing with actual input format:\n")
    
    with app.app_context():
        for line in test_input.split('\n'):
            # Split on multiple spaces
            parts = re.split(r'\s{2,}', line.strip())
            print(f"Line: {line}")
            print(f"Split into: {parts}")
            if len(parts) == 4:
                home_team = Team.query.filter_by(name=parts[0]).first()
                away_team = Team.query.filter_by(name=parts[2]).first()
                print(f"Home team found: {home_team.name if home_team else 'Not found'}")
                print(f"Away team found: {away_team.name if away_team else 'Not found'}")
            print("-" * 80)

if __name__ == '__main__':
    test_score_parse()