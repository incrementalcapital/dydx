import pymongo

from dbconnection import dbclient

# Connect
# Uses the default project named "test"
# Uses the cluster specified in the connection string of the configuration file (in dbconnection)
db = dbclient.test

# Test the connection
print ( db )
