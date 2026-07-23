# Imports

# Built-In
import random
import re
import time


# Installed
import requests
from selenium.webdriver import ChromeOptions
from selenium import webdriver
from bs4 import BeautifulSoup

# Local
from config import NTFY_TOPIC_URL, load_schedule_urls


SCHEDULE_URLS: list[str] = load_schedule_urls()


RESERVED_SEAT_PATTERN = re.compile(r"(\d+)\s+taken of\s+(\d+)\s+seats reserved")


def isCourseAvailable(courseInfo : dict) -> bool:
    if "generalSeatsAvailable" not in courseInfo:
        raise Exception("Invalid Course Info")

    return courseInfo["generalSeatsAvailable"] > 0


def sumReservedSeats(node) -> tuple[int, int]:
    reservedTaken : int = 0
    reservedTotal : int = 0

    for rcap in node.find_all("div", {"class": "rcapInfo"}):
        match = RESERVED_SEAT_PATTERN.search(rcap.text)
        if match:
            reservedTaken += int(match.group(1))
            reservedTotal += int(match.group(2))

    return reservedTaken, reservedTotal


def parseComponents(soup) -> list[dict]:
    components : list[dict] = []

    for typeBlock in soup.find_all("strong", {"class": "type_block"}):
        label : str = typeBlock.text.strip()

        # The remarks header shares the type_block styling but is not a component.
        if label == "Class Remarks:":
            continue

        componentCell = typeBlock.find_parent("td")
        seatText = componentCell.find("span", {"class": "seatText"})
        if seatText is None:
            continue

        takenSeats, totalSeats = (int(part) for part in seatText.text.split("/"))

        # Reserved seats
        remarksRow = componentCell.find_parent("tr").find_next_sibling("tr")
        reservedTaken, reservedTotal = sumReservedSeats(remarksRow) if remarksRow else (0, 0)

        # Seats a student in no reserved category can actually take.
        generalAvailable : int = (totalSeats - reservedTotal) - (takenSeats - reservedTaken)

        components.append({
            "label": label,
            "type": label.split()[0],
            "takenSeats": takenSeats,
            "totalSeats": totalSeats,
            "reservedTaken": reservedTaken,
            "reservedTotal": reservedTotal,
            "generalAvailable": generalAvailable,
        })

    return components


def getCourseInfo(courseHTML : str) -> dict:

    soup = BeautifulSoup(courseHTML, 'lxml')

    components : list[dict] = parseComponents(soup)
    if not components:
        raise Exception("Invalid Class: no components found")

    courseCode : str = soup.find("h4", {"class": "course_title"}).text.strip()

    generalSeatsAvailable : int = min(component["generalAvailable"] for component in components)

    return {
        "name": courseCode + " (" + " / ".join(c["label"] for c in components) + ")",
        "isFull": soup.find("span", {"class": "fullText"}) is not None,
        "components": components,
        "generalSeatsAvailable": generalSeatsAvailable,
    }

def getScheduleAvailability(SCHEDULE_URL : str, print_info = False):

    scheduleDict : dict = dict()

    while True:
        try:
            # Define Selenium to be headless
            options = ChromeOptions()
            options.add_argument("--headless=new")
            driver = webdriver.Chrome(options=options)

            # Load Website Dynamically
            driver.get(SCHEDULE_URL)

            # Found Course Divs
            courseDiv : list = []

            # Wait for the page to load and get each course body
            while not courseDiv:
                soup = BeautifulSoup(driver.page_source, 'lxml')
                courseDiv = soup.find_all("div", {"class": "td course_cell_legend one_col"})

            # Exit out of Chromium
            driver.quit()
            break
        except:
            print("Error: Failed to fetch the url data, retrying")
            try:
                driver.quit()
            except:
                pass
            continue


    # Iterate though each course and get its info
    for courseHTML in courseDiv:
        courseInfo : dict = getCourseInfo(str(courseHTML))

        if print_info: print(courseInfo)

        # Add if the course is available or not
        scheduleDict[courseInfo["name"]] = isCourseAvailable(courseInfo)

    return scheduleDict

def sendNtfyNotification(className : str):
    try:
        response = requests.post(
            NTFY_TOPIC_URL,
            data=f"{className} is available!".encode("utf-8"),
            headers={
                "Title": "U of A Course Available",
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Error: Failed to send ntfy notification: {error}")

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
                if (scheduleAvailability[course]): sendNtfyNotification(course)

        # Random Time Intervals
        randomMinuteInterval : int = random.randint(5, 10)
        randomSecInterval : int = random.randint(0,30)

        print(f"Waiting {randomMinuteInterval} minutes and {randomSecInterval} seconds")
        time.sleep((randomMinuteInterval * 60) + randomSecInterval)


if __name__ == "__main__":
    main()
