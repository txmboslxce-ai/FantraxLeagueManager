from app import create_app
from startup import init_db_if_empty

app = create_app()
init_db_if_empty()  # Initialize database if empty