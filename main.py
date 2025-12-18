# Imports

# Built-In
import random
import time


# Installed
from discord_webhook import DiscordWebhook
from selenium.webdriver import ChromeOptions
from selenium import webdriver
from bs4 import BeautifulSoup

# Local
from config import DISCORD_WEBHOOK_URL, load_schedule_urls


SCHEDULE_URLS: list[str] = load_schedule_urls()


def isCourseAvailable(courseDict : dict) -> bool:

    if "labTotalSeats" in courseDict:
        return ((courseDict["lectureTakenSeats"] < courseDict["lectureTotalSeats"]) and
                (courseDict["labTakenSeats"] < courseDict["labTotalSeats"]))

    elif "lectureTotalSeats" in courseDict:
        return courseDict["lectureTakenSeats"] < courseDict["lectureTotalSeats"]

    else:
        raise Exception("Invalid Course Info")


def getCourseInfo(courseHTML : str) -> dict:


    # Initialize Variables
    courseInfo : dict = dict()


    # Use BeautifulSoup on Course HTML
    soup = BeautifulSoup(courseHTML, 'lxml')

    # Get Course Types and Sections
    seatTypeDiv : list = soup.find_all("strong", {"class" : "leftnclear type_block"})

    # Get Number of Seats
    seatDivs : list = soup.find_all("span", {"class": "seatText"})



    # Get the course name
    courseInfo["name"] = soup.find("h4", {"class": "course_title"}).text + " " + seatTypeDiv[0].text

    # Parse text from HTML tag
    for i in range(0, len(seatDivs)):
        seatDivs[i] = seatDivs[i].text

    # Check if course has more than a lecture portion
    if (len(seatDivs) == 2):

        # Add the Extra Course Type to Name:
        courseInfo["name"] += " " + seatTypeDiv[-2].text

        # Correctly define what is the lecture portion vs what is a lab
        if int(seatDivs[0].split("/")[1]) > int(seatDivs[1].split("/")[1]):
            courseInfo["lectureTakenSeats"] = int(seatDivs[0].split("/")[0])
            courseInfo["lectureTotalSeats"] = int(seatDivs[0].split("/")[1])

            courseInfo["labTakenSeats"] = int(seatDivs[1].split("/")[0])
            courseInfo["labTotalSeats"] = int(seatDivs[1].split("/")[1])
        else:
            courseInfo["labTakenSeats"] = int(seatDivs[0].split("/")[0])
            courseInfo["labTotalSeats"] = int(seatDivs[0].split("/")[1])

            courseInfo["lectureTakenSeats"] = int(seatDivs[1].split("/")[0])
            courseInfo["lectureTotalSeats"] = int(seatDivs[1].split("/")[1])

    # Only Lecture Portion
    elif (len(seatDivs) == 1):
        courseInfo["lectureTakenSeats"] = int(seatDivs[0].split("/")[0])
        courseInfo["lectureTotalSeats"] = int(seatDivs[0].split("/")[1])

    # Invalid Class
    else:
        raise Exception("Invalid Class")

    return courseInfo

def getScheduleAvailability(SCHEDULE_URL : str, print_info = False):

    # Define Selenium to be headless
    options = ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    # Load Website Dynamically
    driver.get(SCHEDULE_URL)

    # Found Course Divs
    scheduleDict : dict = dict()
    courseDiv : list = []

    # Wait for the page to load and get each course body
    while not courseDiv:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        courseDiv = soup.find_all("div", {"class": "td course_cell_legend one_col"})

    # Exit out of Chromium
    driver.quit()


    # Iterate though each course and get its info
    for courseHTML in courseDiv:
        courseInfo : dict = getCourseInfo(str(courseHTML))

        if print_info: print(courseInfo)

        # Add if the course is available or not
        scheduleDict[courseInfo["name"]] = isCourseAvailable(courseInfo)

    return scheduleDict

def sendDiscordWebhook(className : str):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=f"@everyone {className} is available!!!")
    webhook.execute()



def main():

    numChecks : int = 0
    while True:
        numChecks += 1

        print(f"Check Number: {numChecks}")


        for scheduleUrl in SCHEDULE_URLS:

            # Get availability of each course
            scheduleAvailability : dict = getScheduleAvailability(scheduleUrl, True)

            # Iterate through all the courses in the schedule and notify if course is available
            for course in scheduleAvailability:

                # Check if course is available
                if (scheduleAvailability[course]): sendDiscordWebhook(course)

        # Random Time Intervals
        randomMinuteInterval : int = random.randint(5, 15)
        randomSecInterval : int = random.randint(0,30)

        print(f"Waiting {randomMinuteInterval} minutes and {randomSecInterval} seconds")
        time.sleep((randomMinuteInterval * 60) + randomSecInterval)


if __name__ == "__main__":
    main()
