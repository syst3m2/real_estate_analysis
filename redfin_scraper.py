from bs4 import BeautifulSoup
import random
import requests
from fake_useragent import UserAgent
from urllib.request import Request, urlopen
import pandas as pd
from IPython.core.display import clear_output

CENSUS_API_KEY = "9a9f2312db84307a3e496ffb47bb6046f6ccbfe4"

class redfin_scraper():

    def __init__(self):
        self.proxies = []
        self.userAgent = ''
        self.home_df = pd.DataFrame()

    def user_agent(self):
        # Create a random user agent to use in request to obscure browser
        ua = UserAgent()
        self.userAgent = ua.random
        return self.userAgent

    ############################ Obfuscation ################################

    def proxy_generator(self):

        # Find a random proxy to use in the request to obscure source ip address
        # https://stackoverflow.com/questions/38785877/spoofing-ip-address-when-web-scraping-python

        # Grab proxies from website
        # Need to add try except for grabbing proxy and use regular ip address if proxies not working

        proxies = []
        delete_proxies = []
        proxies_req = Request('https://www.sslproxies.org/')
        proxies_req.add_header('User-Agent', self.user_agent())
        proxies_doc = urlopen(proxies_req).read().decode('utf8')
        soup = BeautifulSoup(proxies_doc, 'html.parser')
        proxies_table = soup.find("table", class_="table table-striped table-bordered")

        # Save proxies in array
        for row in proxies_table.tbody.find_all('tr'):
            proxies.append({
                'ip':   row.find_all('td')[0].string,
                'port': row.find_all('td')[1].string
            })

        # Retrieve a random index proxy (we need the index to delete it if not working)
        #proxy_index = random.randint(0, len(proxies) - 1)
        #proxy = proxies[proxy_index]


        # Iterate through proxies and test if they work, delete those that don't work
        for n in range(0, len(proxies)):
            proxy_index = n
            proxy = proxies[n]
            req = Request('http://icanhazip.com')
            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')

            # Make the test call, print what ip address the website sees
            try:
                my_ip = urlopen(req).read().decode('utf8')
                print('#' + str(n) + ': ' + my_ip)
                clear_output(wait = True)
            except: # If error, add to list of proxies to delete
                delete_proxies.append(n)
                #print('Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' deleted.')

        for i in sorted(delete_proxies, reverse=True):
            del proxies[i]
        
        self.proxies = proxies
        
        return self.proxies


    def scrape_listings(self):

        ############################ USER INPUT #############################

        # Set url for desired search in redfin
        # Update to possibly iterate through zip code or neighborhood through entire us, query with different proxy and user agent each time
        url = "https://www.redfin.com/city/16904/CA/San-Diego/filter/viewport=33.25527:32.98095:-116.97292:-117.32517,no-outline"

        # Set up iteration through list of every US city or every zip code
        #headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36', 'Accept': 'application/json'}

        zipcode = "92082"

        ########################## GET Request ###############################
        # Need to add try except for if proxy or something else stops working

        # Set request headers 

        # Mobile test
        #userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile/14E5239e Safari/602.1'
        headers = {'User-Agent': self.user_agent()}

        # Set proxy to use, then delete from list
        self.proxies = self.proxy_generator()
        proxy = random.choice(self.proxies)

        # Set request parameters
        params = {}

        # Set URL
        #url = "https://www.redfin.com/zipcode/" + zipcode + "/filter/property-type=house+multifamily" # This adds multifamily
        url = "https://www.redfin.com/zipcode/{1}/filter/property-type=house".format(zipcode) # Only searches single family

        # Query zip code
        #https://www.redfin.com/stingray/do/query-location?al=1&lat=33.257295&lng=-116.996475&location=92069&market=socal&num_homes=1000&ooa=true&v=2
        # Get request

        # Query city
        # https://www.redfin.com/stingray/do/query-location?al=1&lat=33.18197500000001&lng=-117.15870500000001&location=san%20diego&market=socal&num_homes=1000&ooa=true&v=2

        # Send get request
        r = requests.get(url=url, params=params, headers=headers, proxies=proxy)

        soup = BeautifulSoup(r.text)


        ###################### Extract Housing Data from Redfin ##############################
        from re import sub
        from decimal import Decimal
        import re

        # If return is mobile from mobile user agent, else normal request response

        if len(soup.select('div[data-rf-paint-id="mobile-homecard-list"]')) > 0:
            MOBILE = True
        else:
            MOBILE = False
            
        if MOBILE:
            home_list = soup.find_all(class_='mobileListHomeCard mobileListHomeCardV2')
        else:
            home_list = soup.select('div[id*="MapHomeCard_"]')

        # Iterate through homes
        home_data = {}
        n=0

        for home in home_list:
            
            #home = home_list[0]

            # Get address
            # <span class="collapsedAddress primaryLine" data-rf-test-id="abp-streetLine">
            address = home.find_all(class_="collapsedAddress primaryLine")[0].text
            address_parts = json.loads(home.find('script', type="application/ld+json").text)[0]
            street = address_parts['address']['streetAddress']
            city = address_parts['address']['addressLocality']
            state = address_parts['address']['addressRegion']
            zipcode = address_parts['address']['postalCode']

            # Get price
            # class="homecardV2Price"
            price = home.find_all(class_="homecardV2Price")[0].text
            price =  int(Decimal(sub(r'[^\d\-.]', '', price)))
            

            # Get beds, baths, sq ft
            # <div class="stats">
            stats = home.find_all(class_="stats")

            beds = int(re.sub("[^0-9]", "", stats[0].text))
            baths = float(re.findall(r"[-+]?(?:\d*\.\d+|\d+)", stats[1].text)[0]) 
            sq_ft = int(re.sub("[^0-9]", "", stats[2].text))
            

            # Get description
            # <div class="remarks withTitle">
            #         <p>
            #          92082 Home for Sale:
            #         </p>
            #         <p>
            descr_el = home.find_all(class_="remarks withTitle")
            descr = descr_el[0].find_all('p')[1].text

            # Get images
            #<a class="slider-item" data-rf-test-id="slider-item-0" data-rf-test-name="basic-card-photo" href="/CA/Valley-Center/31371-Justin-Pl-92082/home/3153655" style="transform:translateX(0px)" target="_self">
            #       <img alt="Photo of 31371 Justin Pl, Valley Center, CA 92082" class="homecard-image" fetchpriority="high" height="100%" src="https://ssl.cdn-redfin.com/photo/48/mbphoto/376/genMid.220028376_0.jpg" style="width:100%;height:100%;object-fit:cover;object-position:center" title="31371 Justin Pl, Valley Center, CA 92082" width="100%"/>
            
            '''
            Need to add images
            images = home.find_all(class_="homecard-image")
            image_urls = []
            for element in images:
                print(element)
                image_urls.append(element["src"])
            '''

            '''Need to grab lat/long from each listing to use in plotting on map'''

            # Get listing URL, navigate to the listing, grab redfin rent estimate
            for link in home.find_all("a"):
                try:
                    link_bool = (address == link["title"])
                    home_link = "https://www.redfin.com/" + link["href"]
                except:
                    continue

            # Calculate price per square foot

            price_sq_ft = round(price/sq_ft, 2)

            home_data[n] = {"address": address, "street": street, "city": city, "state": state, "zipcode": zipcode, "price": price, "beds": beds, "baths": baths, "sq_ft": sq_ft, "price_sq_ft": price_sq_ft, "home_link": home_link, "description":descr}

            n+=1

        #print(json.dumps(home_data, indent=4))

        self.home_df = pd.DataFrame.from_dict(home_data, orient='index')

        return self.home_df

    def address_geocode(self, street, city, state, zipcode):
        # returns geocoding information for every address to compare rent data to

        params = {'benchmark':'Public_AR_Current', 'vintage':'Current_Current', 'street':street, 'city':city, 'state':state, 'zip': zipcode, 'format':'json', 'layers':'all'}
        url = 'https://geocoding.geo.census.gov/geocoder/{0}/{1}?'.format('geographies','address')
        response = requests.get(url=url, params=params)
        geographies = response.json()

        county = geographies["result"]["addressMatches"][0]["geographies"]["Counties"][0]["COUNTY"]
        county_sub = geographies["result"]["addressMatches"][0]["geographies"]["County Subdivisions"][0]["COUSUB"]
        tract = geographies["result"]["addressMatches"][0]["geographies"]["Census Tracts"][0]["TRACT"]
        state_code = geographies["result"]["addressMatches"][0]["geographies"]["States"][0]["STATE"]

        geocode = {"county":county, "county_sub":county_sub, "tract":tract, "street":street, "city":city, "state":state_code, "zipcode":zipcode}

        return geocode

    def rent_processor(self, geocode, bed, bath):
        #   Finds rent rates for a particular geocode for an address and number of beds
        median_rent_bedrooms = {"all":"B25031_001E", "None":"B25031_002E", "1":"B25031_003E", "2":"B25031_004E", "3":"B25031_005E", "4":"B25031_006E", "5+":"B25031_007E"}

        if bed==0:
            med_rent_str = median_rent_bedrooms["None"]
        if bed==1:
            med_rent_str = median_rent_bedrooms["1"]
        elif bed==2:
            med_rent_str = median_rent_bedrooms["2"]
        elif bed==3:
            med_rent_str = median_rent_bedrooms["3"]
        elif bed==4:
            med_rent_str = median_rent_bedrooms["4"]
        elif bed==5:
            med_rent_str = median_rent_bedrooms["5+"]
        else:
            med_rent_str = median_rent_bedrooms["all"]

        # Query ACS 1 year data based on county subdivision from address geocode
        url_acs1_countysub = "https://api.census.gov/data/{0}/acs/{1}?get=NAME,{2}&for=county%20subdivision:{3}&in=state:{4}%20county:{5}&key={6}"\
            .format('2021', 'acs1', med_rent_str, geocode["county_sub"], geocode["state"], geocode["county"], CENSUS_API_KEY)

        response_acs1_countysub = requests.request("GET", url_acs1_countysub)
        rent_df_acs1_countysub = pd.DataFrame(response_acs1_countysub.json()[1:], columns=response_acs1_countysub.json()[0])

        # Query ACS 1 year based on place
        # Could find place based on looking up zip code in zcta place relationships.txt and 
        # searching for city name in place field string
        '''
        url_acs1_place = "https://api.census.gov/data/{0}/acs/{1}?get=NAME,{2}&for=place:{3}&in=state:{4}&key={5}"\
            .format('2021', 'acs1', med_rent_str, place, state, CENSUS_API_KEY)

        response_acs1_place = requests.request("GET", url_acs1_place)
        rent_df_acs1_place = pd.DataFrame(response_acs1_place.json()[1:], columns=response_acs1_place.json()[0])
        '''

        # Query ACS 5 year data based on census tract address is located in
        url_acs5_tract = "https://api.census.gov/data/{0}/acs/{1}?get=NAME,{2}&for=tract:{3}&in=state:{4}%20county:{5}&key={6}"\
                .format('2021', 'acs5', med_rent_str, geocode["tract"], geocode["state"], geocode["county"], CENSUS_API_KEY)

        response_acs5_tract = requests.request("GET", url_acs5_tract)
        rent_df_acs5_tract = pd.DataFrame(response_acs5_tract.json()[1:], columns=response_acs5_tract.json()[0])

        # Take rental estimates from all 3 in following priority
        #   Use acs 1 year first
        #   Fill gaps with acs 1 year place, and if not available, then fill with acs 5 year data. 
        #   If data available for both acs 1 year, then take lower amount

        return rent_est

    def deal_analysis(self):
        # Analyze the deals (NOI, Cap Rate, COC ROI, etc) for every Redfin Listing
        return self.home_data


# def main():
# rs = redfin_scraper()

# Scrape listings for set zip code, need to iterate through zip codes and rotate proxies
# home_df = rs.scrape_listings()

# Take returned house data, get all geocoded information for each address
# try to geocode the address, but if the address can't be geocoded, then need to pass and flag for using a redfin rent estimate based on the zip code
# try:
# home_df[['county', 'county_sub', 'tract', 'state_code']] = home_df.apply(lambda x: rs.address_geocode(street=x['street'], city=x['city'], state=x['state'], zipcode=x['zipcode']), axis=1)
# rs.address_geocode()

# Estimate rent for each address based on various data sources
# rs.rent_processor()

# Conduct deal analysis for each listing, calculate all standard investment metrics
