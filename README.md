# Conference Central Application


## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

**Conference Centrall Application** is a cloud-based API server designed to support a conference organization that exists on the web as well as a native mobile applications. 
The API supports the following functionalities found within the app: 
- create new conferences and sessions within the conference
- Adding new speakers for the company
- user authentication and user profiles store/retrieval
- register for conferences and add interested session into user wishlists
- various manners to query the data.

This project is hosted on a cloud-based hosting platform - Google App Engine. It allows to develop applications quickly, horizontally scale to support hundreds of thousands of users on a variety of platforms including web or mobile.


## Table of contents

- [Setup Instructions](#setupinstructions)
- [Implemented Tasks](#implementedtasks)
- [Additional Endpoints](#additionaledendpoints)



## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting your local server's address (by default [localhost:8080][5].)
1. Generate your client library(ies) with [the endpoints tool][6].
1. Open the Google app engine launcher, choose File > Add Existing Application, and then browse the files, add this application. After this, run this application after deploying it.
1. You can also visit the [google api explorer][7] to test all the endpoints.
1. Deploy your application.


## Implemented Tasks

### Task 1: Add Sessions to a Conference

#### Endpoints implemented:

1. getConferenceSessions(websafeConferenceKey)
    - Given a conference, return all sessions
1. getConferenceSessionsByType(websafeConferenceKey,typeOfSession)​
    - Given a conference, return all sessions of a specified type (eg lecture, keynote, workshop)
1. getSessionsBySpeaker(speaker)
    - Given a speaker, return all sessions given by this particular speaker, across all conferences
1. createSession(SessionForm,websafeConferenceKey)
    - Create a session, open only to the organizer of the conference


#### Reasoning behind Sessions and Speaker implementations:

Sessions was implemented with the following attributes: 
##### sessionName, highlights, webSafeKey, typeOfSession, speaker, role, location, date, startTime, duration 

- ***webSafeKey*** corresponds to the the Conference (ancestor) to which the session belongs
_ ***role*** is an enumeration object describing the role of the speaker for the session
- ***typeOfSession*** represents the enumeration field for the type of session
- ***speaker*** is the actual speaker name

However Speaker is implemented as an object: name, sessionKeys.
Where:

- ***name*** is the speaker name
- ***sessionKeys*** are keys of the actual sessions that the speaker would present.
 
 
> Note:
A session belongs to a conference as its parent ancestor, each session may have a speaker. However the speaker entity exists outside of a conference.
The method endpoint `getAllSpeakers` will return all available speakers outside of conferences.


### Task 2: Add Sessions to User Wishlist

A user can add, retrieve and delete session to a wishlist of sessions to attend.

The following API methoods were defined to support Session Whishlist

1. ***addSessionToWishlist(SessionKey)***
    - adding the session to the user's list of sessions they are interested in attending.
1. ***deleteSessionFromWishlist(SessionKey)***
    - deletes the session from the user's list of sessions expected to attend.
1. ***getSessionsInWishlist()***
    - query for all the sessions in a conference that the user is interested in.


### Task 3: Work on indexes and queries

New indeces were added to `index.yaml` representing queries of more than one search items in addition to ancestor key.

These are some of the method endpoints to use complex queries:

- getConferenceSessionsByLocationByTypeByDate
- getConferenceSessionsByLocationByType


These are excerpts from indeces added to support complex queries:


    - kind: Session
      ancestor: yes
      properties:
      - name: location
      - name: typeOfSession
      
     - kind: Session
      ancestor: yes
      properties:
      - name: location
      - name: typeOfSession
      - name: date



### Task 4: Add a Task

Whenever a new session is added to a conference, a new task is queued to check whether the speaker has more than one session in the conference. If so a new Memcache entry is created for 
feature the speaker and session names.
As such the following single Endpoint is defined:

1. ***getFeaturedSpeaker()***
    - returns the featured speaker, if any.



## Additional Endpoints

####These the endpoints implemented in this project:

* addSessionToWishlist	                    -- *Adding the session to the user's list of sessions they are interested in attending.*
* addSpeaker                                -- *Adding a speaker to Conference Central App*
* createSession                             -- *Creates new session in a conference.*
* deleteSessionFromWishlist                 -- *Deletes the session from the user's list of sessions expected to attend.*
* getAllSessionsInWishlist	                -- *Queries for all the sessions in a conference that the user is interested in.*
* getAllSpeakers	                        -- *Returns all speakers across all conferences and sessions.*
* getConferenceSessions	                    -- *Returns all sessions in a given conference.*
* getConferenceSessionsByDate	            -- *Returns all sessions in a given conference, provided a date.
* getConferenceSessionsByLocation	        -- *Returns all sessions in a given conference, given a location.*
* getConferenceSessionsByLocationType	    -- *Returns all sessions in a given conference, given a combination of session type and location.*
* getConferenceSessionsByLocationTypeDate	-- *Returns all sessions in a given conference, given a combination of session type, location and date.*
* getConferenceSessionsBySpeakerRole	    -- *Returns all sessions in a given conference, given a specific type.*
* getConferenceSessionsByType	            -- *Returns all sessions in a given conference, given a specific type.
* getFeaturedSpeaker	                    -- *Returns featured speaker from memcache.*
* getSessionsBySpeaker	                    -- *Returns all sessions from a given speaker.*
* getSessionsInWishlist	                    -- *Returns all the sessions in a conference that the user is interested in.*
* querySpeakers                             -- *Implements Custom Queries for speakers.*




[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool
[7]: https://apis-explorer.appspot.com/apis-explorer/?base=https://winged-comfort-119815.appspot.com/_ah/api#p/conference/v1/
