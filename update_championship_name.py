from app import create_app, db
from app.models import Division

app = create_app()

with app.app_context():
    # Find and update the Championship Division
    championship = Division.query.filter_by(name='Championship Division').first()
    if championship:
        championship.name = 'Championship'
        db.session.commit()
        print("Successfully updated division name to 'Championship'")
    else:
        print("Division not found") 