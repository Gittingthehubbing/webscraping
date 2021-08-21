from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
import pandas as pd
import re
from selenium import webdriver as wd
from selenium.webdriver.common.keys import Keys
import time

driverOpts = wd.FirefoxOptions()
driverOpts.add_argument("--incognito")
#driverOpts.add_argument("--headless")



place="Poole"
job = "Data Scientist".replace(" ","+")
url =rf"https://uk.indeed.com/jobs?q={job}&l={place}"
print(f"Doing URL {url}")

doDynamic = False

if not doDynamic:
    with urlopen(url) as page:
        pageHtml = page.read()

    pageSoupLxml = bs(pageHtml, "lxml")
    jobCardsPart = pageSoupLxml.find("div",{"id":"mosaic-provider-jobcards"})

    jobUrls = []
    for a in jobCardsPart.find_all("a"):
        url = a.get("href")
        if "pagead" in url:
            jobUrls.append(url)

    jobCards = jobCardsPart.find_all(
        "div",{"class":"slider_container"}
    )

    jobsDf = pd.DataFrame()

    for i,jobCard in enumerate(jobCards):

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
        oneShortDescr = jobCard.find_all(
            "div",{"class":"job-snippet"}
            )[0].text.strip()
        if oneJobTitleFind:
            if isinstance(oneJobTitleFind,list):
                temp = jobCard.find_all("h2")[0].find_all("span")
                for t in temp:
                    tempText = t.text                
                    if "new" not in tempText:
                        oneJobTitle = tempText            
            else:
                oneJobTitle = oneJobTitleFind.span.text
            #oneSnippet = oneSnippet[0].li.text
            jobsDf = jobsDf.append(
                pd.DataFrame(
                    {
                        "Job Title":oneJobTitle,
                        "Company":oneCompany,
                        "Location":oneLocation,
                        "Short Description":oneShortDescr,
                        },index=[i]))
        else:
            print("No job title for ",i)

    jobsDf.to_excel("jobsDf.xlsx")
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