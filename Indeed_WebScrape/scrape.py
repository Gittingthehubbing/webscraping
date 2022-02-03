from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
import pandas as pd
import numpy as np
import re
from selenium import webdriver as wd
from selenium.webdriver.common.keys import Keys
import time
import requests
import geocoder
from datetime import timedelta
from datetime import datetime
import os
from string import ascii_uppercase 
import webbrowser

def removeWord(source,word):
    if word in source.lower():
        source = source.lower().replace(word,"")
    return source

def getDistanceAndTime(origin, originPostcode, goal,country):
    origin = origin.encode("ascii", "ignore").decode()
    goal = goal.encode("ascii", "ignore").decode()
    originPostcode = findPostcode(originPostcode,country)
    if originPostcode:
        startLoc = geocoder.osm(f'{originPostcode}')
    else:
        startLoc = geocoder.osm(f'{origin}, {country}')
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
    goalPostcode = findPostcode(goal,country)
    if goalPostcode:
        endLoc = geocoder.osm(f'{goalPostcode}, {country}')
    else:
        endLoc = geocoder.osm(f'{goal}, {country}')
    if not endLoc.ok:
        return None,None
    endCoord = endLoc.latlng
    url =rf'http://router.project-osrm.org/route/v1/driving/{startCoord[1]},{startCoord[0]};{endCoord[1]},{endCoord[0]}'

    r = requests.get(url)
    if r.ok:
        res = r.json()
        distance=round(res["routes"][0]["distance"]/1000) # in km
        duration=str(timedelta(seconds=int(res["routes"][0]["duration"])))
        return distance, duration
    else:
        print(r,"Location not working")
        return None,None

def hasClassAndName(tag):
    return tag.has_attr("data-mobtk") and tag.name=="a"

def returnAttrIfNotNone(obj,attr):
    if obj is not None:
        obj = getattr(obj,attr)
    else:
        obj = "Not Found"
    return obj

def findPostcode(string,country):
    if country == "UK":
        postcodes = re.findall(r"[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$",string) #https://en.wikipedia.org/wiki/Postcodes_in_the_United_Kingdom    
    elif country == "DE":
        postcodes = re.findall(r"^(?!01000|99999)(0[1-9]\d{3}|[1-9]\d{4})$",string)
    if postcodes:
        return postcodes[0]
    else:
        partialPostcode = re.findall(r"[A-Z]{1,2}[0-9][A-Z0-9]? ",string)
        if partialPostcode:
            return partialPostcode
        else:
            return None


def makeTempDf(jobListing,baseUrl,keywords,place,place_postcode,country,doSummary,jobIdx):

    url = jobListing.get("href")
    if any(jobStr in url for jobStr in ["pagead","rc/clk","/company/"]):
        jobUrl=f"{baseUrl}{url}"
    else:
        jobUrl = None
        print("No URL found for ",jobIdx)

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
            if "£" in contractType:
                salary_min = int(contractType[contractType.find("£")+1:contractType.find(" ")].replace(",",""))
                substr = contractType[contractType.find("£")+1:]
                if "£" in substr:
                    salary_max_str = substr[substr.find("£")+1:]
                    salary_max= int(salary_max_str[:salary_max_str.find(" ")].replace(",",""))
                elif "€" in substr:
                    salary_max_str = substr[substr.find("€")+1:]
                    salary_max= int(salary_max_str[:salary_max_str.find(" ")].replace(",",""))
                else:
                    salary_max = np.nan
            else:
                salary_min = salary_max = np.nan
            
            description = subPageSoupLxml.find("div",{"id":"jobDescriptionText"}).text.strip().replace("\n","")
            keywordCountsDict = {word:description.lower().count(word) for word in keywords}
            if keywordCountsDict:
                keywordCount = sum(keywordCountsDict.values())
                if keywordCount>0:
                    mostCommenKeyword = max(keywordCountsDict,key=keywordCountsDict.get) # returns key of highest value in dict
                else:
                    mostCommenKeyword = None
            else:
                keywordCount,mostCommenKeyword = None,None
            footer = subPageSoupLxml.find("div",{"class":"jobsearch-JobMetadataFooter"}).find_all("div")
            for foot in footer:
                if "days ago" in foot.text:                        
                    postTime = int(foot.text[:foot.text.find(" days ago")].replace("+",""))
                if "original job" in foot.text:
                    originalJobLink = foot.find("a").get("href")
        else:
            return pd.DataFrame()

        distance, duration = getDistanceAndTime(place, place_postcode, oneLocation,country)
        shortSummary = makeSummaryCustom(description,int(len(description)/10),60) if doSummary else None
        return pd.DataFrame(
            {
                "Job_Title":oneJobTitle,
                "Company":oneCompany,
                "Location":oneLocation,
                "Contract_Type": contractType,
                "Minimum_Salary":salary_min,
                "Maximum_Salary":salary_max,
                "Posted_Days_Ago":postTime,
                "Driving_Distance":distance,
                "Travel_Time":duration,
                "Matching_Keywords_Count":keywordCount,
                "Most_Common_Keyword": mostCommenKeyword,
                "Short_Description":oneShortDescr,
                "Summary":shortSummary,
                "Easy_Apply": easyApply,
                "url":jobUrl,
                "Full_Description": description,
                "Original_Job_Link":originalJobLink,
                },index=[jobIdx])
    
    else:
        print("No job title for ",jobIdx)
        return pd.DataFrame()

def makeSummary(text,max_length=100,min_length=20):
    summarizer = pipeline("summarization",model="sshleifer/distilbart-cnn-12-6")
    try:
        s = summarizer(text,max_length=max_length, min_length=min_length, do_sample=False)
        return s[0]["summary_text"]
    except Exception as e:
        print(e)
        return None


def makeSummaryCustom(text,max_length=100,min_length=20):
    model = AutoModelForSeq2SeqLM.from_pretrained("t5-base")
    tokenizer = AutoTokenizer.from_pretrained("t5-base")
    try:
        inputs = tokenizer("summarize: " + text, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(
            inputs["input_ids"], max_length=max_length, min_length=min_length, length_penalty=2.0,
            num_beams=4, early_stopping=True
        )
        s = tokenizer.decode(outputs[0]).replace("<pad> ","").replace("</s>","")
        return s        
    except Exception as e:
        print(e)
        return None
     
     
def dfColToLetter(df,col,upperCaseLetters):
    cols = list(df.columns)
    num = cols.index(col)
    return upperCaseLetters[num]

def main():

    driverOpts = wd.FirefoxOptions()
    driverOpts.add_argument("--incognito")
    #driverOpts.add_argument("--headless")


    place="Poole"
    place_postcode = "BH14 0BN "
    country = ["UK","DE"][0]
    job = "Machine Learning".replace(" ","+")
    radius = 25 # in miles
    keywords = ["python", "pandas","pytorch","scikit","keras","sql","tensorflow","photonics","FDTD"]


    dbTableName = 'indeed_jobs'
    saveToSQL = False
    continueFileIfAvailable = False
    doDynamic = False
    doSummary = False # English only atm

    if country != "UK":
        doSummary = False

    excelName = f"jobsDf_{place}_{job}.xlsx"

    if country == "UK":
        baseUrl = "https://uk.indeed.com"
    elif country == "DE":
        baseUrl = "https://de.indeed.com"

    url =f"{baseUrl}/jobs?q={job}&l={place}&radius={radius}"
    print(f"Doing URL {url}")

    

    if doSummary:
        from transformers import pipeline
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer



    if not doDynamic:
        with urlopen(url) as page:
            pageHtml = page.read()

        pageSoupLxml = bs(pageHtml, "lxml")
        jobCardsPart = pageSoupLxml.find("div",{"id":"mosaic-zone-jobcards"})

        jobUrls = []
        otherUrls = []
        if jobCardsPart is not None:
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
                    if "Captcha" in navUrlSoup.text:
                        webbrowser.open_new_tab(navUrl)
                        continue
                    else:
                        navJobCards = navJobCardPart.find_all(hasClassAndName)
                        jobCards += navJobCards
                

            if continueFileIfAvailable and os.path.isfile(excelName):
                jobsDf = pd.read_excel(excelName)
            else:    
                jobsDf = pd.DataFrame()

            for jobIdx,jobListing in enumerate(jobCards):
                try:
                    jobsDf = jobsDf.append(makeTempDf(jobListing,baseUrl,keywords,place,place_postcode,country,doSummary,jobIdx))
                except Exception as e:
                    print(e,"makeTempDf Failed, trying again in 60s")
                    time.sleep(60)
                    try:
                        jobsDf = jobsDf.append(makeTempDf(jobListing,baseUrl,keywords,place,place_postcode,country,doSummary,jobIdx))
                    except Exception as e:
                        print(e,"makeTempDf Failed again")

            jobsDf.drop_duplicates(["url"],inplace=True)
            if "Unnamed: 0" in jobsDf.columns:
                jobsDf.drop("Unnamed: 0",axis=1,inplace=True)

            totalRows,totalCols = jobsDf.shape
            wr = pd.ExcelWriter(f"Formatted_{excelName}",engine="xlsxwriter")
            jobsDf.to_excel(wr,sheet_name="Jobs",index=False)
            wb = wr.book
            ws = wr.sheets["Jobs"]
            ws.set_column(0,len(jobsDf.columns)+1,20)
            format1 = wb.add_format({"num_format":'£#,##0'})
            format2 = wb.add_format({"num_format":'#,##0"km"'})
            wrapFormat = wb.add_format({"text_wrap":True})
            ws.set_column("D:F",10,format1)
            ws.set_column("H:H",10,format2)
            ws.set_column("L:M",20,wrapFormat)
            ws.set_column("A:B",20,wrapFormat)
            ws.set_column("P:P",50,wrapFormat)
            for rowIdx in range(2,jobsDf.shape[0]):
                ws.set_row(rowIdx,20)
            
            ws2 = wb.add_worksheet("Charts")
            chart = wb.add_chart({"type":"bar"})
            chart.set_size({"width":720,"height":540})#in pixels
            plotCols = ['Minimum_Salary','Maximum_Salary']
            for plotCol in plotCols:
                chart.add_series({
                    "values": f"=Jobs!${dfColToLetter(jobsDf,plotCol,ascii_uppercase)}$2:${dfColToLetter(jobsDf,plotCol,ascii_uppercase)}${totalRows+1}",
                    'categories': f"=Jobs!${dfColToLetter(jobsDf,'Job_Title',ascii_uppercase)}$2:${dfColToLetter(jobsDf,'Job_Title',ascii_uppercase)}${totalRows+1}",
                    "name":f"=Jobs!${dfColToLetter(jobsDf,plotCol,ascii_uppercase)}$1"})
            chart.set_title({"name":"Salary"})
            ws2.insert_chart("A1",chart)
            wr.save()
            markdown = jobsDf.drop(["Full_Description","url","Original_Job_Link"],axis=1).to_markdown(index=False)
            with open("jobsDf.md","w") as f:
                for l in markdown.split("\n"):
                    try:
                        f.write(f"{l}\n")
                    except Exception as e:
                        print(e,"\n","Problem with ",l)
            print(jobsDf)

                
            if saveToSQL:
                
                from sqlalchemy import create_engine
                with open("sqlpass.txt","r") as f:
                    lines = f.readlines()
                    loginName = lines[0].strip()
                    loginPass = lines[1]
                engine = create_engine(f'postgresql://{loginName}:{loginPass}@localhost:5432/webscdb')
                if not engine.has_table(dbTableName):
                    jobsDf.to_sql(dbTableName,engine)
                else:
                    if continueFileIfAvailable:
                        sqlDf = pd.read_sql(dbTableName,engine)
                        sqlDf = sqlDf.append(jobsDf)
                        if "level_0" in sqlDf.columns:
                            sqlDf.drop(["level_0","index"],axis=1,inplace=True)
                        sqlDf.reset_index(inplace=True,drop=True)
                        sqlDf.drop_duplicates(["url"],inplace=True)
                    else:
                        sqlDf = jobsDf
                    sqlDf.to_sql(dbTableName,engine,if_exists="replace")
        else:
            if "Captcha" in pageSoupLxml.text:
                print("Captcha blocked scraping, try opening the website in the browser")
                webbrowser.open(url)
            else:
                print("No job ads found")
            

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

if __name__ == "__main__":
    main()