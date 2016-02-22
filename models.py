#!/usr/bin/env python

"""models.py

Udacity conference server-side Python App Engine data & ProtoRPC models

$Id: models.py,v 1.1 2014/05/24 22:01:10 wesc Exp $

created/forked from conferences.py by wesc on 2014 may 24

"""

__author__ = 'wesc+api@google.com (Stanley Calixte)'

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    sessionWishList = ndb.KeyProperty(repeated=True)


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(1)
    mainEmail = messages.StringField(2)
    teeShirtSize = messages.EnumField('TeeShirtSize', 3)
    c = messages.StringField(4, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)


class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)


class Conference(ndb.Model):
    """Conference -- Conference object"""
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics = ndb.StringProperty(repeated=True)
    city = ndb.StringProperty()
    startDate = ndb.DateProperty()
    month = ndb.IntegerProperty()  # TODO: do we need for indexing like Java?
    endDate = ndb.DateProperty()
    maxAttendees = ndb.IntegerProperty()
    seatsAvailable = ndb.IntegerProperty()


class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name = messages.StringField(1)
    description = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics = messages.StringField(4, repeated=True)
    city = messages.StringField(5)
    startDate = messages.StringField(6)  # DateTimeField()
    month = messages.IntegerField(7, variant=messages.Variant.INT32)
    maxAttendees = messages.IntegerField(8, variant=messages.Variant.INT32)
    seatsAvailable = messages.IntegerField(9, variant=messages.Variant.INT32)
    endDate = messages.StringField(10)  # DateTimeField()
    websafeConferenceKey = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)


class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15


class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)


class Speaker(ndb.Model):
    """Speaker -- Speaker Object"""
    name = ndb.StringProperty(required=True)
    session_keys = ndb.KeyProperty(repeated=True)


class AddSpeakerForm(messages.Message):
    """SpeakerForm -- Speaker outbound form message"""
    speaker = messages.StringField(1)
    sessionName = messages.StringField(2)


class SpeakerForm(messages.Message):
    """SpeakerForm -- Speaker outbound form message"""
    speaker = messages.StringField(1)
    sessionNames = messages.StringField(2, repeated=True)


class SpeakerForms(messages.Message):
    """SpeakerForms -- multiple Conference outbound form message"""
    items = messages.MessageField(SpeakerForm, 1, repeated=True)


class SpeakerQueryForm(messages.Message):
    """SpeakerQueryForm -- Speaker query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class SpeakerQueryForms(messages.Message):
    """SpeakerQueryForms -- multiple SpeakerQueryForm inbound form message"""
    filters = messages.MessageField(SpeakerQueryForm, 1, repeated=True)


class Session(ndb.Model):
    """Session --- Session object"""
    sessionName = ndb.StringProperty(required=True)
    highlights = ndb.StringProperty()
    webSafeKey = ndb.StringProperty(required=True)
    typeOfSession = ndb.StringProperty(default='TBD')
    speaker = ndb.StringProperty(required=True)
    role = ndb.StringProperty(default='Speaker')
    location = ndb.StringProperty()
    date = ndb.DateProperty(auto_now=False)
    startTime = ndb.TimeProperty()
    duration = ndb.IntegerProperty(default=50)


class SessionForm(messages.Message):
    sessionName = messages.StringField(1, required=True)
    highlights = messages.StringField(2)
    speaker = messages.StringField(3, required=True)
    typeOfSession = messages.EnumField('SessionType', 4)
    role = messages.EnumField('SessionRole', 5)
    location = messages.StringField(6)
    date = messages.StringField(7)  # Date: YYYY-MM-DD
    startTime = messages.StringField(8)  # Time: HH24:MI
    duration = messages.IntegerField(9)


class SessionForms(messages.Message):
    """SessionForms -- multiple Sessions outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)


class SessionType(messages.Enum):
    """SessionType -- session type selection for a specific session"""
    TBD = 1  # Session type to be determined
    UNKNOWN = 2  # Session type exists but is unknown - similar to TBD
    Workshop = 3
    Case_Study = 4
    Tutorial = 5
    Talk = 6
    Keynote = 7
    Demonstration = 8
    Panel = 9
    Special = 10
    Forum = 11


class SessionRole(messages.Enum):
    """SessionRole -- speaker role enumeration value"""
    NOT_SPECIFIED = 1
    Speaker = 2
    Host = 3
    Keynote = 4
    Presenter = 5


class SessionLocationTypeOfSessionDateQueryForm(messages.Message):
    """SessionLocationTypeOfSessionDateQueryForm -- Find sessions by location, type of session and date by query inbound form message"""
    sessionLocation = messages.StringField(1, required=True)
    typeOfSession = messages.EnumField('SessionType', 2, required=True)
    sessionDate = messages.StringField(3, required=True)  # Date: YYYY-MM-DD


class SessionLocationTypeOfSessionQueryForm(messages.Message):
    """SessionLocationTypeOfSessionQueryForm -- Find sessions by location, type of session and date by query inbound form message"""
    sessionLocationc = messages.StringField(1, required=True)
    typeOfSession = messages.EnumField('SessionType', 2, required=True)


class SessionBySpeakerQueryForm (messages.Message):
    """SessionBySpeakerQueryForm -- Session Speaker query inbound form message"""
    speakerName = messages.StringField(1, required=True)


class SessionBySessionTypeQueryForm(messages.Message):
    """SessionBySessionTypeQueryForm -- Session Speaker query inbound form message"""
    typeOfSession = messages.EnumField('SessionType', 1, required=True)


class SessionBySpeakerRoleForm(messages.Message):
    """SessionBySessionTypeQueryForm -- Session Speaker query inbound form message"""
    speakerRole = messages.EnumField('SessionRole', 1, required=True)


class SessionByLocationQueryForm (messages.Message):
    """SessionBySpeakerQueryForm -- Session Speaker query inbound form message"""
    sessionLocation = messages.StringField(1, required=True)


class SessionByDateQueryForm (messages.Message):
    """SessionByDateQueryForm -- Conference query inbound form message"""
    sessionDate = messages.StringField(1, required=True)


class QuerySessionsToWishlistForm(messages.Message):
    """SessionWishListQueryForm -- Session Speaker query inbound form message"""
    session = messages.StringField(1, required=True)
    speaker = messages.StringField(2)


class SessionWishListForm(messages.Message):
    """SessionWishListQueryForm -- Session Speaker query inbound form message"""
    session = messages.StringField(1, repeated=True)


class SessionQueryForm(messages.Message):
    """SessionQueryForm -- Speaker query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class SessionQueryForms(messages.Message):
    """SessionQueryForms -- multiple SpeakerQueryForm inbound form message"""
    filters = messages.MessageField(SessionQueryForm, 1, repeated=True)
