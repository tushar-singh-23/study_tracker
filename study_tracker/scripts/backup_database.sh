#!/bin/bash
# backup_database.sh

# Define the backup directory
BACKUP_DIR="backups"
DATABASE_FILE="database.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create the backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Copy the database file to the backup directory with a timestamp
cp $DATABASE_FILE $BACKUP_DIR/database_$TIMESTAMP.db

echo "Backup completed at $TIMESTAMP"
