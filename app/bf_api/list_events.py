import betfairlightweight
from betfairlightweight import filters
import time

# Initialize Betfair API client
app_key = 'your_app_key'
username = 'your_username'
password = 'your_password'
cert_file = 'path_to_your_cert_file.pem'  # Optional: for SSL certificate (depends on your setup)
key_file = 'path_to_your_key_file.pem'  # Optional

# Create Betfair API client
trading = betfairlightweight.APIClient(username, password, app_key=app_key, cert_file=cert_file, key_file=key_file)

# Log in to Betfair API
trading.login()