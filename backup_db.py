#!/usr/bin/env python3
"""
Backup database to SQL dump file
"""
import sqlite3
import os
from datetime import datetime

def backup_database():
    db_path = 'fantasy_league.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist!")
        return
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'db_backup_{timestamp}.sql'
    
    # Connect to database and dump
    conn = sqlite3.connect(db_path)
    
    with open(backup_filename, 'w') as f:
        for line in conn.iterdump():
            f.write('%s\n' % line)
    
    conn.close()
    print(f"Database backed up to {backup_filename}")
    return backup_filename

if __name__ == '__main__':
    backup_database()
