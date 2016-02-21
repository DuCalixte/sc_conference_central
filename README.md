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

- [Setup Instructions](#setup_instructions)
- [Design Choices](#design_choices)
- [Implemented Tasks](#implementedtasks)
- [Additional Endpoints](#additionalendpoints)



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




## Design Choices

My core *Design Choices*: ***Conference Central*** is responsible for maintaining **Conferences**, **Profile**, **Sessions** and **Speakers**. **Sessions** belong to **Conferences** while **Speakers** are parallel entity that can  be assigned to any **Sessions** across **Conferences**. In addition a registed user to a conference can *add or deleted* **Sessions** to his or her wishlist.


### Task 1:

In **Task 1**, the objectives were to implement a **Session** entity along with various endpoints methods.

A **Session** can have speakers, a starting time, a date of occurrence, and a duration alongn with highlights. I have chosen to implement a **Session** that belongs to a **Conference**, and can only be altered by its creator.

A registered user with profile can create a new **Session** and must assign each **Session** to a parent **Conference**. The creation of a **Session** also requires the inclusion of a *Speaker* (speaker name), which is also an entity. However, if the *speaker name* as inserted does not exist, a new **Speaker** object will be added along with the current **Session** key, otherwise the **Speaker** entity is updated with the **Session** key appended to the list of *session keys*.

A **Speaker** is an entity with a fullname, and Session keys. The keys are not mandatory to create a speaker, and a speaker may exist outside of any conference parameters. This design decision will allow the **Speaker** entity to be part of any **Session**.
Potential some restrictions should be provided to prevent a speaker to be part of multiple sessions at the same time.


> See ***[Implementations for Task 1]***(task1addsessionstoaconference) for further details on the implemenations.



### Task 2:

Each ***Session*** object comes with a unique *key* property. This property serves many additional roles. One of the roles is to allow a registered user to add sessions to his or her wishlist.

I have decided to implement the following key methods endpoints.

* **addSessionToWishlist(SessionKey)** - ***As required***, to allow the selection of a session to user whishlist
* **getSessionsInWishlist()** - ***As required***, to show the list of sessions in the whishlist.
* **getAllSessionsInWishlist()** - this method retrieves all sessions across all conferences from a user wishlist
* **deleteSessionFromWishlist()** - this method was deemed necessary as it makes sense. A user should be able to modify the list.

>Note: The sessions are listed as part of SessionForm class, which allows the presentation of all information pertainining to the session.


### Task 3:

This task had three core objectives.

First, I have made some few modifications to index.yaml, see ***[Implementations for Task 3]***(task3_worksonindexesandqueries) for more details. All my indeces were verified with the Admin Console.

Second, I have thought of quite a few interesting queries. Below are the list of new queries implemented. I have further described two of them in ***[Implementations for Task 3]***(task3_worksonindexesandqueries).
     -  getAllSessionsInWishlist	             
     -  getAllSpeakers	                     
     -  getConferenceSessions	                 
     -  getConferenceSessionsByDate	         
     -  getConferenceSessionsByLocation	     
     -  getConferenceSessionsByLocationType	 
     -  getConferenceSessionsByLocationTypeDate
     -  getConferenceSessionsBySpeakerRole	 
     -  getConferenceSessionsByType	         
     -  getFeaturedSpeaker	                 
     -  getSessionsBySpeaker	                 
     -  getSessionsInWishlist	                 
     -  querySpeakers    
     -  getAllSessionsForNonWorksopsBefore7PM


Lastly, I have solved the following query problem: *Provided multiple sessions of different types and start time, I should be able to retrieve non-worksop sessions that start prior to 7 PM*.

At first, I thought this query was straightfoward, but soon there diffulties stemming mostly from design.
- Date and Time objects are created with default value of None
- Restrictions on multiple queries with inequality filter

Given these restrictions, and perhaps more. I was able devise a solution that only queries for startTime values being not `None`, then I would restrict the results by excluding all *Session Types* for ***Workshop***.

As described earlier **startTime** is a property of kind ***TimeProperty*** and **typeOfSession** in enumeration string value stemming from the class SessionType. 


### Task 4:

My solutions for this task was to introduce a *Memcache* and then register the associated task for storing the latest speaker that has been added and already having more than one sessions. The result for ***getFeaturedSpeaker()*** is transfered to **SpeakerForm()** class for display.See ***[Implementations for Task 4]***(task4_addatask).




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
- ***sessionName*** the actual name of the session as required for creation.
- ***speaker*** is the actual speaker name as required for creation. A new **Speaker** object is created if not found.
- ***highlights*** optional field for description and or highlights related to session
- ***location*** location for the session within the conference.
- ***date*** the actual date for the session formatted as *YYYY-MM-DD*
- ***startTime*** the actual time when the session would begin formatted as *HH24:MI*.
- ***duration*** represents the length of time a session should last in minutes. By default a session should last 50 minutes.
- ***role*** is an enumeration object describing the role of the speaker for the session. The default value is ***Speaker***.
    These are the complete options:
    * NOT_SPECIFIED
    * Speaker
    * Host
    * Keynote
    * Presenter
- ***typeOfSession*** represents the enumeration field for the type of session. The Default value is ***TBD***.
    These are the complete options:
    * TBD
    * UNKNOWN
    * Workshop
    * Case_Study
    * Tutorial
    * Talk
    * Keynote
    * Demonstration
    * Panel
    * Special
    * Forum


Similarly the **Speaker** is implemented as an entity: name, sessionKeys.
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



### Task 3: Works on indexes and queries

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


Lastly:

The indeces were modified to provide a better return on the query:


    - kind: Session
      properties:
      - name: typeOfSession
      - name: startTime


Below are code excerpts:



        sessions = Session.query(ndb.AND(
            Session.startTime !=  None,
            Session.startTime < datetime.strptime('19:00'[:10], "%H:%M").time())
        ).fetch()

        return SessionForms(
            items=[(self._copySessionToForm(session)) for session in sessions if session.typeOfSession != 'Workshop']
        )



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
* getAllSessionsInWishlist	                -- *Queries for all the sessions accross all conferences that the user is interested in.*
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
