import os, glob, time, operator, sys, time, requests
from optparse import OptionParser
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

start = time.time()
parser = OptionParser()
parser.add_option("-e", "--email", type="string", dest="email", help="Crisis Cleanup login email")
parser.add_option("-p", "--password", type="string", dest="password", help="Crisis Cleanup login password")
parser.add_option("-m", "--map", type="string", dest="map", help="Crisis Cleanup map URL")
parser.add_option("-t", "--token", type="string", dest="token", help="Dropbox Auth Token") #https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/
parser.add_option("-f", "--filename", type="string", dest="filename", help="The file to name the backed up map data.",
                  default="disastermapdata.csv")

(options, args) = parser.parse_args()
if (options.email is None) or (options.password is None) or (options.map is None):
    parser.error("not enough number of arguments")


TOKEN = options.token
BACKUPPATH = '/'+options.filename
dbx = dropbox.Dropbox(TOKEN)

# Uploads contents of LOCALFILE to Dropbox https://github.com/dropbox/dropbox-sdk-python/blob/master/example/back-up-and-restore/backup-and-restore-example.py
def backup(localfile):
    with open(localfile, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + localfile + " to Dropbox as " + BACKUPPATH + "...")
        try:
            dbx.files_upload(f.read(), BACKUPPATH, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().error.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()

dir_path = os.path.dirname(os.path.realpath(__file__))
chrome_options = Options()
#chrome_options.add_argument("--disable-extensions")
#chrome_options.add_argument("--headless") # This makes Chrome run without the GUI, but disables downloading ;^(

print(dir_path)
prefs = {"download.default_directory" : dir_path}
chrome_options.add_experimental_option("prefs",prefs)
chrome_options.binary_location = "/app/.apt/usr/bin/google-chrome" # Remove for non-Heroku
#chrome_options.add_argument('--disable-gpu')
#chrome_options.add_argument('--no-sandbox')
driver = webdriver.Chrome(chrome_options=chrome_options)
driver.get("http://www.crisiscleanup.org/login")


try:
    element = WebDriverWait(driver, 10).until(EC.title_contains(("Crisis Cleanup")))
except TimeoutException:
    print('Crisis Cleanup website failed to load.')
    driver.close()
    sys.exit()

print('Crisis Cleanup website loaded.')

login = True
try:
    element = WebDriverWait(driver, 10).until(EC.title_contains(("Dashboard")))
except TimeoutException:
    print('Crisis Cleanup login page.')
    login = False

if login is False:
    try:
        email = driver.find_element_by_id('user_email')
        email.send_keys(options.email)
        password = driver.find_element_by_id('user_password')
        password.send_keys(options.password)
        driver.find_element(By.CLASS_NAME,'button').click()
    except WebDriverException:
        print('Failed to fill out login form.')
        driver.close()
        sys.exit()
    login = True
    try:
        element = WebDriverWait(driver, 10).until(EC.title_contains(("Dashboard")))
    except TimeoutException:
        print('Crisis Cleanup failed login page.')
        login = False

if login is False:
    print('Failed to login.')
    driver.close()
    sys.exit()
else:
    print('Crisis Cleanup dashboard page.')

headers = {
    'DNT': '1',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive',
}



s = requests.session()
s.headers.update(headers)
cookies = driver.get_cookies()
#s.cookies.update({'cc-joyride': 'ridden'})
sessionkey = ''
ga = ''
gid = ''
for cookie in driver.get_cookies():
    #c = {cookie['name']: cookie['value']}
    #print(cookie['name'], ' ' , cookie['value'])
    if cookie['name'] == '_ga':
        ga = cookie['value']
    if cookie['name'] == '_gid':
        gid = cookie['value']
    if cookie['name'] == '_crisiscleanup_session':
            sessionkey = cookie['value']#s.cookies.update(c)

requestcookies = {
    'cc-joyride': 'ridden',
    '_ga': ga,
    '_gid': gid,
    '_crisiscleanup_session': sessionkey,
}
#driver.get(options.map)
headeritems = s.headers.items()
for h in headeritems:
    print(h)
print(options.map)

r = requests.get(options.map, headers=headers, cookies=requestcookies,stream=True)
print(r.status_code)
#print(r.text)
downloadedcsv =  os.path.join(dir_path, options.filename)
with open(os.path.join(dir_path, options.filename), 'wb') as f:
    for chunk in r.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
            f.write(chunk)
            #print('Writing chunk')
                #f.flush() commented by recommendation from J.F.Sebastian

print('Downloaded the CSV.')
#time.sleep(60)
'''
try:
    element = WebDriverWait(driver, 10).until(EC.title_contains(("Map")))
except TimeoutException:
    print('Failed to load map page.')
    driver.close()
    sys.exit()
print('Crisis Cleanup Map.')
#Close hint if pops up
try:
    driver.find_element(By.CLASS_NAME, 'joyride-close-tip').click()
except WebDriverException:
    print('No need to press tip close.')
print('Waiting 15 seconds to make sure data is loaded...')
time.sleep(15)
try:
    driver.find_element(By.ID, 'download-csv-btn').click()
except WebDriverException:
    print('Failed to press csv download btn.')
    driver.close()
    sys.exit()

print('Assuming download is finished after 60 seconds.')

#login_link = driver.find_element_by_link_text('Login')
#driver.
'''
driver.close()

#Get name of latest file
#filelist = os.listdir(dir_path)
#for file in filelist:
#    print(file)
#files = glob.glob('*.csv')
#files.sort(key=lambda x: os.stat(os.path.join(dir_path, x)).st_mtime, reverse=True)
# Upload backup to Dropbox
backup(downloadedcsv)
# Remove all but the latest five CSV files

'''count = 0
for file in files:
    if count < 5:
        count = count + 1
    else:
        os.remove(file)
'''
print('Done')
print('It took {0:0.1f} seconds'.format(time.time() - start))