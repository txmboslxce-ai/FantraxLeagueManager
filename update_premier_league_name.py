from app import create_app, db
from app.models import Division

def update_division_names():
    app = create_app()
    with app.app_context():
        # Find all divisions named "Premier Division"
        divisions = Division.query.filter(Division.name.ilike('Premier Division')).all()
        
        if not divisions:
            print("No divisions found with name 'Premier Division'")
            return
        
        # Update each division's name
        for division in divisions:
            old_name = division.name
            division.name = "Premier League"
            print(f"Updating division name from '{old_name}' to 'Premier League'")
        
        # Commit the changes
        try:
            db.session.commit()
            print("Successfully updated division names")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating division names: {e}")

if __name__ == '__main__':
    update_division_names() 