from flask import render_template, redirect, url_for, flash
from app.admin import bp
from app.admin.decorators import admin_required
from app import db
from app.models import *
import os

@bp.route('/import_data')
@admin_required
def import_data():
    """Manually trigger full data import."""
    try:
        # Execute the full import script
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        script_path = os.path.join(app_dir, 'full_data_import.py')
        
        if os.path.exists(script_path):
            exec(open(script_path).read())
            flash('✅ Full data import completed successfully!', 'success')
        else:
            flash('❌ Import script not found', 'error')
            
    except Exception as e:
        flash(f'❌ Import failed: {str(e)}', 'error')
        
    return redirect(url_for('admin.dashboard'))
