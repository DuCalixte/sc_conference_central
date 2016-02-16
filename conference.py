#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Stanley Calixte)'


from datetime import datetime

import argparse as argparse
import logging
import sys
import os
import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote


from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import StringMessage
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize
from models import Speaker
from models import AddSpeakerForm
from models import SpeakerForm
from models import SpeakerForms
from models import SpeakerQueryForm
from models import SpeakerQueryForms

from models import Session
from models import SessionForm
from models import SessionForms
from models import SessionBySpeakerQueryForm
from models import SessionBySessionTypeQueryForm
from models import SessionBySpeakerRoleForm
from models import SessionByLocationQueryForm
from models import SessionByDateQueryForm
from models import SessionLocationTypeOfSessionQueryForm
from models import SessionLocationTypeOfSessionDateQueryForm
from models import QuerySessionsToWishlistForm
from models import SessionWishListForm
from models import SessionQueryForm
from models import SessionQueryForms
from models import SessionType
from models import SessionRole

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId


EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
MEMCACHE_FEATURED_SPEAKER_KEY = "FEATURED_SPEAKER"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')
SPEAKER_TPL = ('Welcoming %s, to many more sessions: %s!')
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

OPERATORS = {
    'EQ': '=',
    'GT': '>',
    'GTEQ': '>=',
            'LT': '<',
            'LTEQ': '<=',
            'NE': '!='
}

FIELDS = {
    'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
}

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_WISHLIST_REQUEST = endpoints.ResourceContainer(
    QuerySessionsToWishlistForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_WISHLIST_REQUEST = endpoints.ResourceContainer(
    SessionWishListForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_CONFERENCE_GET_WISHLIST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)


SESSION_TYPE_POST_REQUEST = endpoints.ResourceContainer(
    SessionBySessionTypeQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_SPEAKER_ROLE_POST_REQUEST = endpoints.ResourceContainer(
    SessionBySpeakerRoleForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_LOCATION_POST_REQUEST = endpoints.ResourceContainer(
    SessionByLocationQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_DATE_POST_REQUEST = endpoints.ResourceContainer(
    SessionByDateQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_LOCATION_TYPE_POST_REQUEST = endpoints.ResourceContainer(
    SessionLocationTypeOfSessionQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_LOCATION_TYPE_DATE_POST_REQUEST = endpoints.ResourceContainer(
    SessionLocationTypeOfSessionDateQueryForm,
    websafeConferenceKey=messages.StringField(1),
)


SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
)

SPEAKER_IN_SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionBySpeakerQueryForm,
    websafeConferenceKey=messages.StringField(1),
)
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(
    name='conference',
    version='v1',
    audiences=[ANDROID_AUDIENCE],
    allowed_client_ids=[
        WEB_CLIENT_ID,
        API_EXPLORER_CLIENT_ID,
        ANDROID_CLIENT_ID,
        IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeConferenceKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeConferenceKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound
        # Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on
        # start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(
                data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(
                data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email'
                      )
        return request

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf,
                    getattr(
                        prof,
                        'displayName')) for conf in confs])

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(
                filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException(
                    "Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is
                # performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf, names[
                        conf.organizerUserId]) for conf in conferences])


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(
                        pf, field.name, getattr(
                            TeeShirtSize, getattr(
                                prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
                sessionWishList=[],
            )
            profile.put()

        if not profile.sessionWishList:
            profile.sessionWishList = []
            profile.put()

        return profile      # return Profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()
        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        if field == 'teeShirtSize':
                            setattr(prof, field, str(val).upper())
                        else:
                            setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @staticmethod
    def _cacheFeaturedSpeakerAnnouncement(speaker, conferenceKey):
        """Announcing featured speaker. If current checked speaker
           should be featured, replace any previous speaker"""
        logging.info('caching information on speaker %s' % speaker)
        sessions = Session.query(ancestor=ndb.Key(urlsafe=conferenceKey))
        sessions = sessions.filter(Session.speaker == speaker).fetch()

        cache_speaker = {}
        if len(sessions) > 1:
            sessionNames = [session.sessionName for session in sessions]
            cache_speaker['speaker'] = speaker
            cache_speaker['sessionNames'] = sessionNames

            if not memcache.set(MEMCACHE_FEATURED_SPEAKER_KEY, cache_speaker):
                logging.error(
                    'Memcache has failed to add speaker %s:.' %
                    speaker)
        else:
            logging.warning('Speaker is %s is not cached' % speaker)

        return cache_speaker

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(data=memcache.get(
            MEMCACHE_ANNOUNCEMENTS_KEY) or "")

    @endpoints.method(SPEAKER_GET_REQUEST, SpeakerForm,
                      path='showfeaturedSpeaker',
                      http_method='POST', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Return featured speaker from memcache."""
        try:
            data = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        except:
            # raise endpoints.UnauthorizedException('Bad Session')
            raise endpoints.UnauthorizedException(
                'Bad Session %s' % sys.exc_info()[0])

        # data = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        speaker_form = SpeakerForm()
        if data is not None:
            raise endpoints.UnauthorizedException('Bad Session %s' % data)
            # logging.info('showing information for data %s:' % data)
            # setattr(speaker_form, 'speaker', data['speaker'])
            # setattr(speaker_form, 'sessionNames', data['sessionNames'])
        else:
            logging.warning('No information has been cached.')
            setattr(speaker_form, 'speaker', 'No Featured Speaker')
            setattr(speaker_form, 'sessionNames', [])

        speaker_form.check_initialized()
        return speaker_form

# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser()  # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser()  # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId)
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[
                self._copyConferenceToForm(
                    conf, names[
                        conf.organizerUserId]) for conf in conferences])

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground',
                      http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.filter(Conference.month == 6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )


# - - - Speaker objects - - - - - - - - - - - - - - - - - - -

    def _copySpeakerToForm(self, speaker):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        spf = SpeakerForm()
        for field in spf.all_fields():
            if hasattr(speaker, field.name):
                setattr(spf, field.name, getattr(speaker, field.name))

        spf.check_initialized()
        return spf

    def _addSpeakerObject(self, request, data=None):
        """
        :param request: The sequence of object parameters to create a Speaker object
        :return: object contents
        """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        if request is not None:
            if not request.speaker:
                raise endpoints.BadRequestException(
                    "Speaker 'speaker' field required")
            data = {field.name: getattr(request, field.name)
                    for field in request.all_fields()}

            if request.sessionName:
                session = Session.query(
                    Session.sessionName == data['sessionName']).get()
                if session:
                    data['session_key'] = session.key
                    del data['sessionName']
                else:
                    raise endpoints.ForbiddenException(
                        "Session does not exist")
        elif not data['speaker']:
            raise endpoints.BadRequestException(
                "Speaker 'speaker' field required")

        speaker = Speaker.query(Speaker.name == data['speaker']).get()

        if speaker:
            if data['session_key'] in speaker.session_keys:
                raise endpoints.ForbiddenException(
                    "Speaker is already part of session")
            else:
                # raise endpoints.UnauthorizedException('Bad speaker2 %s' % data)
                speaker.session_keys.append(data['session_key'])
        else:
            speaker = Speaker(
                name=data['speaker'], session_keys=[
                    data['session_key']])

        speaker.put()

        return BooleanMessage(data=True)

    @endpoints.method(AddSpeakerForm, AddSpeakerForm, path='speaker',
                      http_method='POST', name='addSpeaker')
    def addSpeaker(self, request):
        """Adding new speaker"""
        return self._addSpeakerObject(request)

    @endpoints.method(SpeakerQueryForms, SpeakerForms,
                      path='querySpeakers',
                      http_method='POST',
                      name='querySpeakers')
    def querySpeakers(self, request):
        """Query for conferences."""
        speakers = Speaker.query()

        # return set of SpeakerForm objects
        return SpeakerForms(
            items=[self._copySpeakerToForm(speaker) for speaker in speakers]
        )

# - - - Session objects - - - - - - - - - - - - - - - - - - -

    def _copySessionToForm(self, session):
        """Copy fields from Session to SessionForm."""
        session_form = SessionForm()
        for field in session_form.all_fields():
            if hasattr(session, field.name):
                if field.name == 'typeOfSession':
                    setattr(
                        session_form, field.name, getattr(
                            SessionType, getattr(
                                session, field.name)))
                elif field.name == 'role':
                    setattr(
                        session_form, field.name, getattr(
                            SessionRole, getattr(
                                session, field.name)))
                elif field.name in ['date', 'startTime']:
                    setattr(
                        session_form, field.name, str(
                            getattr(
                                session, field.name)))
                else:
                    setattr(
                        session_form, field.name, getattr(
                            session, field.name))
            elif field.name == 'webSafeKey':
                setattr(session_form, field.name, session.key.urlsafe())
        return session_form

    def _createSessionObject(self, request):
        """Create or update Session object, returning ConferenceForm/request."""

        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        user_id = getUserId(user)

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the ownerof the conference can create new sessions.')

        if not request.sessionName:
            raise endpoints.BadRequestException(
                "Session 'sessionName' field required")

        if not request.speaker:
            raise endpoints.BadRequestException(
                "Session 'speaker' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        session = Session.query(
            Session.sessionName == request.sessionName).get()
        if session:
            if session.speaker != data['speaker']:
                session.speaker = data['speaker']

                # update session
                # Adjust session type enum field
                if data['role']:
                    session.role = str(data['role'])

                if data['duration']:
                    session.duration = data['duration']

                if data['startTime']:
                    session.startTime = datetime.strptime(
                        data['startTime'][:10], "%H:%M").time()

                # Adjust session type enum field
                if data['typeOfSession']:
                    session.typeOfSession = str(data['typeOfSession'])

                if data['date']:
                    session.date = datetime.strptime(
                        data['date'][:10], "%Y-%m-%d").date()
        else:
            self._addNewSession(request)

        taskqueue.add(params={'speaker': data['speaker'],
                              'conferenceKey': request.websafeConferenceKey},
                      url='/tasks/set_featured_speaker')

        return BooleanMessage(data=True)

    def _addNewSession(self, request):
        # raise endpoints.UnauthorizedException('Bad Session %s' % request)
        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # convert dates from strings to Date objects; set month based on
        # start_date
        if data['date']:
            data['date'] = datetime.strptime(
                data['date'][:10], "%Y-%m-%d").date()

        # convert dates from strings to Date objects; set month based on
        if data['startTime']:
            data['startTime'] = datetime.strptime(
                data['startTime'][:10], "%H:%M").time()

        # Adjust session type enum field
        if data['typeOfSession']:
            data['typeOfSession'] = str(data['typeOfSession'])
        else:
            data['typeOfSession'] = 'TBD'

        # Adjust session type enum field
        if data['role']:
            data['role'] = str(data['role'])
        else:
            data['role'] = 'Speaker'

        # use the Conference websafe key as parent key for the session
        data['webSafeKey'] = request.websafeConferenceKey
        p_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        s_id = Session.allocate_ids(size=1, parent=p_key)[0]
        s_key = ndb.Key(Session, s_id, parent=p_key)
        data['key'] = s_key

        speaker_data = {'session_key': s_key, 'speaker': data['speaker']}

        self._addSpeakerObject(None, speaker_data)

        del data['websafeConferenceKey']

        Session(**data).put()

        return BooleanMessage(data=True)

    def _manageSessionsWishlist(self, request, addToSession=True):
        """Add or remove sessions from user wishlist."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        retval = False
        prof = self._getProfileFromUser()  # get user Profile

        if request.websafeConferenceKey not in prof.conferenceKeysToAttend:
            raise endpoints.ForbiddenException(
                "You must register to the conference in order to add sessions to wishlist.")

        if not request.session:
            raise endpoints.ForbiddenException(
                "You must provide a 'sessionName' for the query.")

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey))

        sessions = sessions.filter(Session.sessionName == request.session)

        if request.speaker:
            sessions = sessions.filter(Session.speaker == request.speaker)

        if not sessions:
            raise endpoints.NotFoundException(
                'No sessions found to add to wishlist')

        key = sessions.fetch()[0].key

        # add to session
        if addToSession:
            # check if session is already in wishlist
            if key in prof.sessionWishList:
                raise ConflictException(
                    "You already have this session in your wishlist")

            # register user, take away one seat
            prof.sessionWishList.append(key)
            retval = True

        # unregister
        else:
            # check if session exists in wishlist, and remove it
            if key in prof.sessionWishList:
                prof.sessionWishList.remove(key)
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()

        return BooleanMessage(data=retval)

    @endpoints.method(SESSION_POST_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}/createSession',
                      http_method='POST', name='createSession')
    def createSession(self, request):
        """Create new session in a conference."""
        return self._createSessionObject(request)

    @endpoints.method(
        SESSION_GET_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getSessionsInConference',
        http_method='GET',
        name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Return all sessions in a given conference."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SPEAKER_IN_SESSION_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getSessionsBySpeaker',
        http_method='POST',
        name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Return all sessions from a given speaker."""

        # query sessions by speaker name in the conference
        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.speaker == request.speakerName).fetch()
        if not sessions:
            raise endpoints.ForbiddenException(
                "no sessions found.")

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_TYPE_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getConferenceSessionsByType',
        http_method='POST',
        name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Return all sessions in a given conference, given a specific type."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.typeOfSession == str(request.typeOfSession)).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_SPEAKER_ROLE_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getConferenceSessionsBySpeakerRole',
        http_method='POST',
        name='getConferenceSessionsBySpeakerRole')
    def getConferenceSessionsBySpeakerRole(self, request):
        """Return all sessions in a given conference, given a specific type."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.role == str(request.speakerRole)).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_LOCATION_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getConferenceSessionsByLocation',
        http_method='POST',
        name='getConferenceSessionsByLocation')
    def getConferenceSessionsByLocation(self, request):
        """getConferenceSessionsByLocation -- Returns all sessions in a given conference, given a location."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.location == request.sessionLocation).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_DATE_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getConferenceSessionsByDate',
        http_method='POST',
        name='getConferenceSessionsByDate')
    def getConferenceSessionsByDate(self, request):
        """getConferenceSessionsByDate -- Returns all sessions in a given conference, provided a date."""

        sessions = Session.query(ancestor=ndb.Key(urlsafe=request.websafeConferenceKey)).filter(
            Session.date == datetime.strptime(str(request.sessionDate)[:10], "%Y-%m-%d").date()).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_LOCATION_TYPE_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getLocationType',
        http_method='POST',
        name='getConferenceSessionsByLocationType')
    def getConferenceSessionsByLocationByType(self, request):
        """getConferenceSessionsByLocationByType -- Return all sessions in a given conference, given a combination of \
         session type and location."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.location == request.sessionLocation).filter(
            Session.typeOfSession == str(request.typeOfSession)).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(
        SESSION_LOCATION_TYPE_DATE_POST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getLocationTypeDate',
        http_method='POST',
        name='getConferenceSessionsByLocationTypeDate')
    def getConferenceSessionsByLocationByTypeByDate(self, request):
        """getConferenceSessionsByLocationByTypeByDate -- Return all sessions in a given conference, given \
          a combination of session type, location and date."""

        sessions = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey)).filter(
            Session.location == request.sessionLocation).filter(
            Session.typeOfSession == str(request.typeOfSession)).filter(
            Session.date == datetime.strptime(str(request.sessionDate)[:10], "%Y-%m-%d").date()).fetch()

        # return set of SessionForm objects
        return SessionForms(
            items=[self._copySessionToForm(session) for session in sessions]
        )

    @endpoints.method(SESSION_WISHLIST_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}/sessionWishlist',
                      http_method='PUT', name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Add Session to User wishlist."""
        return self._manageSessionsWishlist(request)

    @endpoints.method(
        SESSION_WISHLIST_REQUEST,
        BooleanMessage,
        path='conference/{websafeConferenceKey}/deleteSessionWishlist',
        http_method='PUT',
        name='deleteSessionFromWishlist')
    def deleteSessionFromWishlist(self, request):
        """Delete Session from User wishlist."""
        return self._manageSessionsWishlist(request, False)

    @endpoints.method(
        SESSION_CONFERENCE_GET_WISHLIST_REQUEST,
        SessionForms,
        path='conference/{websafeConferenceKey}/getSessionsInWishlist',
        http_method='POST',
        name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get sessions in User wishlist."""
        prof = self._getProfileFromUser()  # get user Profile

        keys = prof.sessionWishList

        return SessionForms(
            items=[
                self._copySessionToForm(
                    Session.query(
                        ancestor=ndb.Key(
                            urlsafe=request.websafeConferenceKey)) .filter(
                        Session.key == key).get()) for key in keys])

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='getAllSessionsInWishlist',
                      http_method='GET', name='getAllSessionsInWishlist')
    def getAllSessionsInWishlist(self, request=None):
        """Get sessions in User wishlist."""
        prof = self._getProfileFromUser()  # get user Profile

        keys = prof.sessionWishList

        return SessionForms(
            items=[
                self._copySessionToForm(
                    Session.query(
                        Session.key == key).get()) for key in keys])

    @endpoints.method(
        SPEAKER_GET_REQUEST, SpeakerForms,
        path='getAllSpeakers', http_method='GET',
        name='getAllSpeakers')
    def getAllSpeakers(self, request=None):
        """getAllSpeakers - returns all speakers across all conferences and sessions."""
        speakers = Speaker.query().fetch()

        return SpeakerForms(items=[SpeakerForm(
            speaker=speaker.name,
            sessionNames=[Session.query(Session.key == key).get().sessionName for key in speaker.session_keys]
        )for speaker in speakers])


api = endpoints.api_server([ConferenceApi])  # register API
