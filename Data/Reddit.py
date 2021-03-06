import json
from collections import namedtuple
from operator import attrgetter

from BeautifulSoup import BeautifulSoup

import PluginUtils



# CONSTANTS
LOLEVENTURL = "http://www.reddit.com/r/loleventvods/new/.json"
LOLMATCHESURL = "http://www.reddit.com/r/loleventvods/comments/%s/.json"
ACTIVE_STRING = "In progress"
FINISHED_STRING = "Finished"
NOTSTREAMED_STRING = "**Not Streamed**"

def loadEvents(sortByStatus):

    response = PluginUtils.doRequest(LOLEVENTURL)
    if (response is None):
        return None

    events = []

    # Now lets parse results
    decoded_data = json.load(response)
    root = decoded_data['data']

    LoLEvent = namedtuple('LoLEvent', 'title status eventId imageUrl')

    # For Each Item in Children
    for post in root['children']:
        html = post['data']['selftext_html']
        if (html is not None):
            soup = BeautifulSoup(PluginUtils.unescape(html))

            imgUrl = ''
            link = soup.find('a', href='#EVENT_PICTURE')
            if (link is not None):
                imgUrl = link.title

        status = 99
        # Using numbers for status so we can easily sort by this
        if (post['data']['link_flair_text']== ACTIVE_STRING):
            status = 0

        if (post['data']['link_flair_text']== FINISHED_STRING):
            status = 1

        childEvent = LoLEvent(title = post['data']['title'],
                              status = status,
                              eventId = post['data']['id'],
                              imageUrl = imgUrl)

        events.append(childEvent)


    if (sortByStatus):
        # sort
        return sorted(events, key=attrgetter('status'))
    else:
        return events

def loadEventContent(eventId):

    LoLEventDay = namedtuple('LoLEventDay', 'dayId day matches recommended imageUrl')
    LoLEventMatch = namedtuple('LoLEventMatch', 'gameId team1 team2 videoLinks')

    url = LOLMATCHESURL % eventId

    response = PluginUtils.doRequest(url)
    if (response is None):
        return None
    # Now lets parse results
    decoded_data = json.load(response)

    selfText = decoded_data[0]['data']['children'][0]['data']['selftext_html']

    eventTitle = ''
    days = []

    soup = BeautifulSoup(PluginUtils.unescape(selfText))

    # Get all the recommended matches, we add those to the events
    # We do it like this Game H1_C1_C4
    recommended = ''
    #a href="/spoiler"
    spoilers = soup.findAll("a", href="/spoiler")
    if (spoilers is not None):
        for spoiler in spoilers:
            # add them to the list
            games = spoiler.text.replace(',', '_')
            recommended += games + "_"

    imgUrl = ''
    link = soup.find('a', href='#EVENT_PICTURE')
    if (link is not None):
        imgUrl = link.title

    # find all tables
    tables = soup.findAll("table")
    for idx, table in enumerate(tables):
        if (table is not None):

            titleLink = table.find("a", href="http://www.table_title.com")
            if (titleLink is not None):
                eventTitle = titleLink['title']

            YouTubeColumns = []
            Team1Index = -1
            Team2Index = -1

            # Investigate the right columns for youtube links
            rows = table.find("thead").findAll("tr")
            for row in rows :
                cols = row.findAll("th")
                for i, col in enumerate(cols):
                 if (col.text.lower() == "youtube"):
                     YouTubeColumns.append(i)
                 if (col.text.lower() == "team 1"):
                     Team1Index = i
                 if (col.text.lower() == "team 2"):
                     Team2Index = i

            #
            matches=[]

            rows = table.find("tbody").findAll("tr")
            for row in rows :
                videos = []
                cols = row.findAll("td")
                if (cols is not None):
                    for yv in YouTubeColumns:
                        if (cols[yv] is not None):
                            if (cols[yv].a is not None):

                                youTubeData = PluginUtils.parseYouTubeUrl(cols[yv].a['href'])
                                videos.append({'text' : cols[yv].a.text,
                                               'videoId' : youTubeData['videoId'],
                                               'time' : youTubeData['time'] })

                matches.append(LoLEventMatch(cols[0].text, cols[Team1Index].text, cols[Team2Index].text, videos))

            days.append(LoLEventDay(dayId = idx,
                                day=eventTitle,
                                matches = matches,
                                recommended = recommended,
                                imageUrl = imgUrl))
    return days

