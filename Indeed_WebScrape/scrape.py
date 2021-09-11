from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
import pandas as pd
import re
from selenium import webdriver as wd
from selenium.webdriver.common.keys import Keys
import time
import requests
import geocoder
from datetime import timedelta
from datetime import datetime
import os

def removeWord(source,word):
    if word in source.lower():
        source = source.lower().replace(word,"")
    return source

def getDistanceAndTime(origin, originPostcode, goal):
    origin = origin.encode("ascii", "ignore").decode()
    goal = goal.encode("ascii", "ignore").decode()
    originPostcode = findPostcode(originPostcode)
    if originPostcode:
        startLoc = geocoder.osm(f'{originPostcode}')
    else:
        startLoc = geocoder.osm(f'{origin}, UK')
    startCoord = startLoc.latlng
    goal = removeWord(goal,"remote")
    goal = removeWord(goal,"temporarily")
    goal = removeWord(goal,"united kingdom")
    goal = removeWord(goal,"england")
    goal = removeWord(goal,"south west")
    goal = removeWord(goal,"south east")
    goal = removeWord(goal,"+1 location")
    if goal=="":
        return None,None    
    goalPostcode = findPostcode(goal)
    if goalPostcode:
        endLoc = geocoder.osm(f'{goalPostcode}, UK')
    else:
        endLoc = geocoder.osm(f'{goal}, UK')
    if not endLoc.ok:
        return None,None
    endCoord = endLoc.latlng
    url =rf'http://router.project-osrm.org/route/v1/driving/{startCoord[1]},{startCoord[0]};{endCoord[1]},{endCoord[0]}'

    r = requests.get(url)
    res = r.json()
    if res["code"] == 'Ok':
        distance=res["routes"][0]["distance"]/1000 # in km
        duration=str(timedelta(seconds=int(res["routes"][0]["duration"])))
        return distance, duration
    else:
        print(res["code"],"Location not working")
        return None,None

def hasClassAndName(tag):
    return tag.has_attr("data-mobtk") and tag.name=="a"

def returnAttrIfNotNone(obj,attr):
    if obj is not None:
        obj = getattr(obj,attr)
    else:
        obj = "Not Found"
    return obj

def findPostcode(string):
    postcodes = re.findall(r"[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$",string) #https://en.wikipedia.org/wiki/Postcodes_in_the_United_Kingdom    
    if postcodes:
        return postcodes[0]
    else:
        partialPostcode = re.findall(r"[A-Z]{1,2}[0-9][A-Z0-9]? ",string)
        if partialPostcode:
            return partialPostcode
        else:
            return None

driverOpts = wd.FirefoxOptions()
driverOpts.add_argument("--incognito")
#driverOpts.add_argument("--headless")


place="Poole"
place_postcode = "BH15 3RJ"
job = "Data Scientist".replace(" ","+")
radius = 75 # in miles

continueFileIfAvailable = 1
doDynamic = False

excelName = f"jobsDf_{place}_{job}.xlsx"
baseUrl = "https://uk.indeed.com"
url =f"{baseUrl}/jobs?q={job}&l={place}&radius={radius}"
print(f"Doing URL {url}")


if not doDynamic:
    with urlopen(url) as page:
        pageHtml = page.read()

    pageSoupLxml = bs(pageHtml, "lxml")
    jobCardsPart = pageSoupLxml.find("div",{"id":"mosaic-zone-jobcards"})

    jobUrls = []
    otherUrls = []
    for a in jobCardsPart.find_all("a"):
        url_jobCard = a.get("href")
        if "pagead" in url_jobCard or "rc/clk" in url_jobCard:
            jobUrls.append(url_jobCard)
        else:
            otherUrls.append(url_jobCard)

    jobCards = jobCardsPart.find_all(
        hasClassAndName
    )

    navButtons = pageSoupLxml.find_all("ul",{"class":"pagination-list"})
    if navButtons:
        buttons = navButtons[0].find_all("li")
        navUrls=[]
        for idx in range(1,len(buttons)):
            navUrls.append(f"{url}&start={10*idx}")
    
        for navUrl in navUrls:
            with urlopen(navUrl) as page:
                navUrlHtml = page.read()
            navUrlSoup = bs(navUrlHtml,"lxml")
            navJobCardPart = navUrlSoup.find("div",{"id":"mosaic-zone-jobcards"})
            navJobCards = navJobCardPart.find_all(hasClassAndName)
            jobCards += navJobCards
        

    if continueFileIfAvailable and os.path.isfile(excelName):
        jobsDf = pd.read_excel(excelName)
    else:    
        jobsDf = pd.DataFrame()

    for i,jobListing in enumerate(jobCards):

        url = jobListing.get("href")
        id = jobListing.get("id")
        if "pagead" in url or "rc/clk" in url:
            jobUrl=f"{baseUrl}{url}"
        else:
            jobUrl = None
            print("No URL found for ",i)

        jobCard = jobListing.find(
        "div",{"class":"slider_container"}
        )

        easyApply = True if "Easily apply to this job" in jobCard.find("table",{"class":"jobCardShelfContainer"}).text else False

        oneJobTitleFind = jobCard.find_all(
            "h2",{"class":re.compile("jobTitle jobTitle-color-purple")}
            )

        td = jobCard.find_all(
            "td",{"class":"resultContent"}
            )[0]
        tdText=td.getText()
        oneCompany = jobCard.find_all(
            "span",{"class":"companyName"}
            )[0].text
        oneLocation = jobCard.find_all(
            "div",{"class":"companyLocation"}
            )[0].text
        
        oneShortDescr = jobCard.find(
            "div",{"class":"job-snippet"}
            ).text.strip()
        if oneJobTitleFind:
            if isinstance(oneJobTitleFind,list):
                temp = jobCard.find_all("h2")[0].find_all("span")
                for t in temp:
                    tempText = t.text                
                    if "new" not in tempText:
                        oneJobTitle = tempText            
            else:
                oneJobTitle = oneJobTitleFind.span.text    

            contractType = description =originalJobLink =postTime = None
            if jobUrl:
                with urlopen(jobUrl) as page:
                    subPageSoupLxml = bs(page.read(), "lxml")
                
                contractType = subPageSoupLxml.find("div",{"class":"jobsearch-JobMetadataHeader-item"})
                contractType = returnAttrIfNotNone(contractType,"text")
                
                description = subPageSoupLxml.find("div",{"id":"jobDescriptionText"}).text
                footer = subPageSoupLxml.find("div",{"class":"jobsearch-JobMetadataFooter"}).find_all("div")
                for foot in footer:
                    if "days ago" in foot.text:                        
                        postTime = int(foot.text[:foot.text.find(" days ago")].replace("+",""))
                    if "original job" in foot.text:
                        originalJobLink = foot.find("a").get("href")

            distance, duration = getDistanceAndTime(place, place_postcode, oneLocation)
            jobsDf = jobsDf.append(
                pd.DataFrame(
                    {
                        "id":id,
                        "Job Title":oneJobTitle,
                        "Company":oneCompany,
                        "Location":oneLocation,
                        "Easy_Apply": easyApply,
                        "Contract_Type": contractType,
                        "Posted_Days_Ago":postTime,
                        "Driving_Distance":distance,
                        "Travel_Time":duration,
                        "Short_Description":oneShortDescr,
                        "Full_Description": description,
                        "url":jobUrl,
                        "Original_Job_Link":originalJobLink,
                        },index=[i]))
        else:
            print("No job title for ",i)
    jobsDf.drop_duplicates(inplace=True)
    if "Unnamed: 0" in jobsDf.columns:
        jobsDf.drop("Unnamed: 0",axis=1,inplace=True)
    jobsDf.to_excel(excelName)
    markdown = jobsDf.drop(["Full_Description","url","Original_Job_Link"],axis=1).to_markdown(index=False)
    with open("jobsDf.md","w") as f:
        for l in markdown.split("\n"):
            try:
                f.write(f"{l}\n")
            except Exception as e:
                print(e,"\n","Problem with ",l)
    print(jobsDf)
        

else:
    drv = wd.Firefox(".",options=driverOpts)
    drv.get(url)
    #drv.find_element_by_xpath("slider_item")
    jobContainers = drv.find_elements_by_class_name("slider_container")

    jobsDf_sel = pd.DataFrame()
    for i,jobby in enumerate(jobContainers):
        drv.execute_script("arguments[0].scrollIntoView();", jobby)
        drv.execute_script("arguments[0].click();", jobby)
        #jobby.click()
        #print(dir(jobby))
        pageHtml_sel = drv.page_source
        time.sleep(2)
        pageSoupLxml_sel = bs(pageHtml_sel, "lxml")
        cont = pageSoupLxml_sel.find_all("div",{"id":"vjs-container"})[0]
        head = cont.find_all("div",{"id":"vjs-jobtitle"})[0].text
        jobsDf_sel = jobsDf_sel.append(
                pd.DataFrame(
                    {
                        "Job Title":head,
                        },index=[i]))
    jobsDf_sel.to_excel("jobsDf.xlsx")
    print(jobsDf_sel)
    drv.close()