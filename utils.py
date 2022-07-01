from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import sqlite3

class LinkedinConnection:

    """
        This class is for storing connections informations

        Attributes:
            name (str): The name of the connection
            occupation (str): The occupations of the connection
            connections_status (str): The date that connection has been established
            full_url (str): Link to connection's profile
    """

    def __init__(self, name, occupation, connection_status, full_url):
        self.name = name
        self.occupation = occupation
        self.connection_status = connection_status
        self.full_url = full_url
    
    def __str__(self):
        return self.name

class DataBase:

    """
        This class is used to interact with database

        Attributes:
            conn (Connectio): Used to establish connection with database
            is_empty (bool) : Indicates whether the database is empty (has no rows in it)

        Methods:
            create_table: Creates a new table in the database
            insert: Inserts a new row into the database
    """

    def __init__(self, file_name=':memory:'):

        """
            Creates a Database object and connects it to a file specified by file_name
            (if file_name is not provided then it stores databse in the memory)
        """

        self.conn = sqlite3.connect(file_name)
        self.is_empty = True
    
    def create_table(self, table_name, columns):

        """
            Creates a new table in the database

            Parameters:
                table_name (str): Name of the table to be created
                colums (dict): Name and Type of the columns to be added to the table

            Returns:
                None
        """

        columns_str = [f'{name} {columns[name]}' for name in columns.keys()]
        columns_str = ', '.join(columns_str)
        c = self.conn.cursor()
        with self.conn:
            command = f"CREATE TABLE {table_name} ({columns_str});"
            c.execute(command)

    def insert(self, table_name, info):

        """
            Inserts a new row into the database

            Parameters:
                table_name (str): Name of the target table
                info (dict): a dictionary that holds values of each column for a new row 

            Returns:
                None
        """

        c = self.conn.cursor()
        column_names = ', '.join([key for key in info.keys()])
        place_holders = [':' + key for key in info.keys()]
        place_holders = ', '.join(place_holders)
        with self.conn:
            command = f'INSERT INTO {table_name} ({column_names}) VALUES ({place_holders})'
            c.execute(command, info)


class LinkedinScraper:

    """
        This class is for crawling the linkedin page, extracting information and saving it to database

        Attributes:
            username (str): Username of the account to be scraped
            password (str): Password of the account to be scraped
            log (str): Stores the webdriver's log

        Methods:
            generate_log: Add page log
            save_log: Saves stored logs to a file
            get_source: Gets HTML content of the webpage
            scrape_my_profile: Extracts information of my profile from the HTML
            scrape_connections: Extracts connection's information
            save_to_db: Saves extracted information to database
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.log = ''
    
    def generate_log(self, log):

        """
            This method gets the log of the browser and appends to already existing logs

            Parameters:
                log (list): List of dictionaries containing browser logs

            Returns:
                None
        """

        for item in log:
            self.log += str(item) + '\n'

    def save_log(self, file_name):

        """
            This method saves the generated log into a file

            Parameters:
                file_name (str): Name of the file to store log
            
            Returns:
                None
        """

        with open(file_name, 'w') as f:
            f.write(self.log)

    def get_source(self, sleep_time):

        """
            Gets the HTML code of the connections page and my profile page

            Parameters:
                sleep_time (int): The amount of time that webdriver waits for a page to load (in seconds)

            Returns:
                Tuple containing HTML code of connections page and my own profile page
        """

        # enable browser logging
        dc = DesiredCapabilities.CHROME
        dc['goog:loggingPrefs'] = {'browser': 'ALL'}
        driver = webdriver.Chrome(desired_capabilities=dc)

        driver.get('https://linkedin.com/uas/login')

        time.sleep(sleep_time)

        # Login using username and password provided
        username = driver.find_element(value="username", by=By.ID)
        username.send_keys(self.username)  
        password = driver.find_element(value="password", by=By.ID)
        password.send_keys(self.password)        
        driver.find_element(value="//button[@type='submit']", by=By.XPATH).click()

        time.sleep(sleep_time)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        profile_url = soup.find('a', 'ember-view block')['href'].split('/')
        profile_url = f'https://www.linkedin.com/{profile_url[1]}/{profile_url[2]}'
        driver.get(profile_url)

        time.sleep(sleep_time)
        my_profile_src = (driver.page_source, profile_url)

        connections_page_url = 'https://www.linkedin.com/mynetwork/invite-connect/connections/'
        driver.get(connections_page_url)
        time.sleep(sleep_time)

        # Scroll connection page tp load all the connections
        initial_height = 0
        final_height = 1000
        reached_end = False
        while True:
            driver.execute_script(f"window.scrollTo({initial_height},{final_height})")
            final_height = driver.execute_script('return document.body.scrollHeight')
            if initial_height == final_height and initial_height!=0:
                if reached_end:
                    break
                driver.maximize_window()
                reached_end = True
            initial_height = final_height
            time.sleep(sleep_time//2)
            final_height += 10000

        time.sleep(sleep_time)

        # Get lof of the browser and close the webdriver
        self.generate_log(driver.get_log('browser'))
        connections_src = driver.page_source
        driver.close()
        driver.quit()
        return my_profile_src, connections_src

    def scrape_my_profile(self, source):
        """
            Gets information of my own profile and creates a Connection object using that

            Parameters:
                source (str): HTML code of the page

            Returns:
                list contatining only one LinkedinConnection object containing my own information
        """
        soup = BeautifulSoup(source[0], 'lxml')
        div = soup.find('div', class_='mt2 relative')
        name = div.find('h1', class_='text-heading-xlarge inline t-24 v-align-middle break-words')
        occupation = div.find('h2', class_='pv-text-details__right-panel-item-text hoverable-link-text break-words text-body-small inline')
        occupation = occupation.div
        connection_status = '-'
        full_url = source[1]
        connection = LinkedinConnection(name.text.strip(), occupation.text.strip(), connection_status, full_url)
        return [connection]

    def scrape_connections(self, source):

        """
            This method extracts connection information from the HTML of the page

            Parameters:
                source (str): HTML code of the webpage

            Returns:
                connections (list): list of all the connections 
        """

        soup = BeautifulSoup(source, 'lxml')
        ul = soup.find('div', class_='scaffold-finite-scroll__content').find('ul')
        data = ul.find_all('li')
        connections = []
        for item in data:
            profile_url = item.find('a', class_='ember-view mn-connection-card__link')['href']
            full_url = f'https://www.linkedin.com/{profile_url}'
            name = item.find('span', class_='mn-connection-card__name t-16 t-black t-bold')
            occupation = item.find('span', class_='mn-connection-card__occupation t-14 t-black--light t-normal')
            connection_status = item.find('time', class_='time-badge t-12 t-black--light t-normal')
            new_connection = LinkedinConnection(name.text.strip(), occupation.text.strip(), connection_status.text.strip(), full_url)
            connections.append(new_connection)
        return connections


    def save_to_db(self, connections, db):

        """
            Saves connections' information to the database

            Parameters:
                connections (list): A list containing all the connections
                db (Database): A database object to store connections' infromation

            Returns:
                None
        """

        table_name = 'connections'
        if db.is_empty:
            columns = {'id': 'integer primary key autoincrement', 'name': 'text', 'occupation': 'text',
                   'connection_status': 'text', 'profile_url': 'text'}

            db.create_table(table_name, columns)
            db.is_empty = False

        for connection in connections:
            info_dict = {'name': connection.name, 'occupation': connection.occupation,
                        'connection_status': connection.connection_status, 'profile_url': connection.full_url}
            db.insert(table_name, info_dict)
        