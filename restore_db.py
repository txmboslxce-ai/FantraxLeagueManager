#!/usr/bin/env python3
"""
Restore database from SQL dump file
"""
import sqlite3
import sys
import os

def restore_database(backup_file):
    if not os.path.exists(backup_file):
        print(f"Backup file {backup_file} does not exist!")
        return False
    
    db_path = 'fantasy_league.db'
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database {db_path}")
    
    # Create new database and restore
    conn = sqlite3.connect(db_path)
    
    with open(backup_file, 'r') as f:
        sql_script = f.read()
    
    conn.executescript(sql_script)
    conn.close()
    
    print(f"Database restored from {backup_file}")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python restore_db.py <backup_file.sql>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    restore_database(backup_file)
