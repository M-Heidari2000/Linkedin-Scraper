from utils import DataBase, LinkedinScraper
import os

# Clean directory from old database files
if os.path.isfile('linkedin.db'):
    os.remove('linkedin.db')
if os.path.isfile('linkedin.log'):
    os.remove('linkedin.log')

db = DataBase('linkedin.db')    # Create a database object
# Enter username and password below
username = ''
password = ''
scraper = LinkedinScraper(username, password)
# In case of having poor connection, set sleep_time to a larger value
my_profile_source, connections_source = scraper.get_source(sleep_time=10)
scraper.save_log('linkedin.log')
# Get my profile information
my_profile = scraper.scrape_my_profile(my_profile_source)
scraper.save_to_db(my_profile, db)
# Get connections' profile information
connections = scraper.scrape_connections(connections_source)
scraper.save_to_db(connections, db)
