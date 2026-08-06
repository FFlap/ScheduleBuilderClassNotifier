import json
import time
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from config import NTFY_TOPIC_URL, load_schedule_urls


SCHEDULE_URLS: list[str] = load_schedule_urls()


def isCourseAvailable(courseInfo: dict) -> bool:
    if "generalSeatsAvailable" not in courseInfo:
        raise ValueError("Invalid course info")

    return courseInfo["generalSeatsAvailable"] > 0


def _clock_parameters() -> tuple[int, int]:
    """Reproduce the short-lived clock check used by My Schedule Builder."""
    minute_window = int(time.time() // 60) % 1000
    check = minute_window % 3 + minute_window % 39 + minute_window % 42
    return minute_window, check


def _parse_schedule_url(
    schedule_url: str,
) -> tuple[str, list[dict], dict[str, str | int]]:
    parsed_url = urlparse(schedule_url)
    query = parse_qs(parsed_url.query, keep_blank_values=True)
    term = query.get("term", [""])[0]
    if not term:
        raise ValueError("Schedule URL is missing its term")

    courses: list[dict] = []
    index = 0
    while f"course_{index}_0" in query:
        course_key = query[f"course_{index}_0"][0]
        selection_key = query.get(f"cs_{index}_0", [""])[0]
        if not selection_key:
            raise ValueError(f"Schedule URL is missing a selected section for {course_key}")

        courses.append({
            "courseKey": course_key,
            "selectionKey": selection_key,
        })
        index += 1

    if not courses:
        raise ValueError("Schedule URL does not contain any courses")

    minute_window, clock_check = _clock_parameters()
    params: dict[str, str | int] = {
        "term": term,
        "t": minute_window,
        "e": clock_check,
        "nouser": 1,
    }

    for index, course in enumerate(courses):
        params[f"course_{index}_0"] = course["courseKey"]
        params[f"va_{index}_0"] = query.get(f"va_{index}_0", [""])[0]
        params[f"rq_{index}_0"] = query.get(f"rq_{index}_0", [""])[0]
        if f"seq_{index}_0" in query:
            params[f"seq_{index}_0"] = query[f"seq_{index}_0"][0]

    api_url = urljoin(schedule_url, "/api/class-data")
    return api_url, courses, params


def _reserved_seats(block: ET.Element) -> tuple[int, int]:
    extended_attributes = block.get("eattrs", "")
    if not extended_attributes:
        return 0, 0

    try:
        reservations = json.loads(extended_attributes).get("rcaps", [])
    except (json.JSONDecodeError, AttributeError) as error:
        raise ValueError("Invalid reserved-seat data returned by class-data") from error

    reserved_taken = sum(int(reservation.get("enrlTot", 0)) for reservation in reservations)
    reserved_total = sum(int(reservation.get("cap", 0)) for reservation in reservations)
    return reserved_taken, reserved_total


def _parse_course(course_node: ET.Element, selection_key: str) -> dict:
    selection = course_node.find(f".//selection[@key='{selection_key}']")
    if selection is None:
        raise ValueError(
            f"Selected sections {selection_key!r} were not returned for {course_node.get('key')}"
        )

    components: list[dict] = []
    for block in selection.findall("block"):
        total_seats = int(block.get("me", "0"))
        open_seats = int(block.get("os", "0"))
        reserved_taken, reserved_total = _reserved_seats(block)

        # Seats usable by a student who belongs to no reserved category.
        general_available = open_seats - (reserved_total - reserved_taken)
        label = block.get("disp") or " ".join(
            part for part in (block.get("type"), block.get("secNo")) if part
        )

        components.append({
            "label": label,
            "type": block.get("type", ""),
            "takenSeats": total_seats - open_seats,
            "totalSeats": total_seats,
            "reservedTaken": reserved_taken,
            "reservedTotal": reserved_total,
            "generalAvailable": general_available,
        })

    if not components:
        raise ValueError(f"No components returned for {course_node.get('key')}")

    course_code = course_node.get("key", "Unknown course")
    return {
        "name": f"{course_code} ({' / '.join(component['label'] for component in components)})",
        "isFull": any(block.get("isFull") == "1" for block in selection.findall("block")),
        "components": components,
        "generalSeatsAvailable": min(
            component["generalAvailable"] for component in components
        ),
    }


def getScheduleAvailability(schedule_url: str, print_info: bool = False) -> dict[str, bool]:
    api_url, requested_courses, params = _parse_schedule_url(schedule_url)
    response = requests.get(api_url, params=params, timeout=30)
    response.raise_for_status()

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as error:
        raise ValueError("class-data returned invalid XML") from error

    errors = [message.strip() for message in root.itertext() if message.strip()] \
        if root.find("errors/error") is not None else []
    if errors:
        raise RuntimeError("class-data error: " + "; ".join(errors))

    course_nodes = {node.get("key"): node for node in root.findall(".//course")}
    availability: dict[str, bool] = {}
    for requested_course in requested_courses:
        course_key = requested_course["courseKey"]
        course_node = course_nodes.get(course_key)
        if course_node is None:
            raise ValueError(f"class-data did not return {course_key}")

        course_info = _parse_course(course_node, requested_course["selectionKey"])
        if print_info:
            print(course_info)
        availability[course_info["name"]] = isCourseAvailable(course_info)

    return availability


def sendNtfyNotification(className: str) -> None:
    try:
        response = requests.post(
            NTFY_TOPIC_URL,
            data=f"{className} is available!".encode("utf-8"),
            headers={"Title": "U of A Course Available"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Error: Failed to send ntfy notification: {error}")


def main() -> None:
    for schedule_url in SCHEDULE_URLS:
        schedule_availability = getScheduleAvailability(schedule_url, True)
        for course, is_available in schedule_availability.items():
            if is_available:
                sendNtfyNotification(course)


if __name__ == "__main__":
    main()
