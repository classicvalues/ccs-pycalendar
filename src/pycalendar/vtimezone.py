##
#    Copyright (c) 2007-2011 Cyrus Daboo. All rights reserved.
#    
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#    
#        http://www.apache.org/licenses/LICENSE-2.0
#    
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
##

from component import PyCalendarComponent
from datetime import PyCalendarDateTime
import definitions

class PyCalendarVTimezone(PyCalendarComponent):

    def __init__(self, parent=None):
        super(PyCalendarVTimezone, self).__init__(parent=parent)
        self.mID = ""
        self.mUTCOffsetSortKey = None

    def duplicate(self, parent=None):
        other = super(PyCalendarVTimezone, self).duplicate(parent=parent)
        other.mID = self.mID
        other.mUTCOffsetSortKey = self.mUTCOffsetSortKey
        return other

    def getType(self):
        return definitions.cICalComponent_VTIMEZONE

    def getMimeComponentName(self):
        # Cannot be sent as a separate MIME object
        return None

    def addComponent(self, comp):
        # We can embed the timezone components only
        if ((comp.getType() == definitions.cICalComponent_STANDARD)
                or (comp.getType() == definitions.cICalComponent_DAYLIGHT)):
            super(PyCalendarVTimezone, self).addComponent(comp)
        else:
            raise ValueError

    def getMapKey(self):
        return self.mID

    def finalise(self):
        # Get TZID
        temp = self.loadValueString(definitions.cICalProperty_TZID)
        if temp is not None:
            self.mID = temp

        # Sort sub-components by DTSTART
        self.mComponents.sort(key=lambda x:x.getStart())

        # Do inherited
        super(PyCalendarVTimezone, self).finalise()

    def getID(self):
        return self.mID

    def getUTCOffsetSortKey(self):
        if self.mUTCOffsetSortKey is None:
            # Take time from first element
            if len(self.mComponents) > 0:
                # Initial offset provides the primary key
                utc_offset1 = self.mComponents[0].getUTCOffset()

                # Presence of secondary is the next key
                utc_offset2 = utc_offset1
                if len(self.mComponents) > 1:
                    utc_offset2 = self.mComponents[1].getUTCOffset()

                # Create key
                self.mUTCOffsetSortKey = (utc_offset1 + utc_offset2) / 2
            else:
                self.mUTCOffsetSortKey = 0

        return self.mUTCOffsetSortKey

    def getTimezoneOffsetSeconds(self, dt):
        # Get the closet matching element to the time
        found = self.findTimezoneElement(dt)

        # Return it
        if found is None:
            return 0
        else:
            # Get its offset
            return found.getUTCOffset()

    def getTimezoneDescriptor(self, dt):
        result = ""

        # Get the closet matching element to the time
        found = self.findTimezoneElement(dt)

        # Get it
        if found is not None:
            if len(found.getTZName()) == 0:
                tzoffset = found.getUTCOffset()
                negative = False
                if tzoffset < 0:
                    tzoffset = -tzoffset
                    negative = True
                result = ("+", "-")[negative]
                hours_offset = tzoffset / (60 * 60)
                if hours_offset < 10:
                    result += "0"
                result += str(hours_offset)
                mins_offset = (tzoffset / 60) % 60
                if mins_offset < 10:
                    result += "0"
                result += str(mins_offset)
            else:
                result = "("
                result += found.getTZName()
                result += ")"

        return result

    def mergeTimezone(self, tz):
        pass

    def findTimezoneElement(self, dt):
        # Need to make the incoming date-time relative to the DTSTART in the
        # timezone component for proper comparison.
        # This means making the incoming date-time a floating (no timezone)
        # item
        temp = dt.duplicate()
        temp.setTimezoneID(None)

        # Had to rework this because some VTIMEZONEs have sub-components where the DST instances are interleaved. That
        # means we have to evaluate each and every sub-component to find the instance immediately less than the time we are checking.

        # Now do the expansion for each one found and pick the lowest
        found = None
        dt_found = PyCalendarDateTime()

        for item in self.mComponents:
            dt_item = item.expandBelow(temp)
            if temp >= dt_item:
                if found is not None:
                    # Compare with the one previously cached and switch to this
                    # one if newer
                    if dt_item > dt_found:
                        found = item
                        dt_found = dt_item
                else:
                    found = item
                    dt_found = dt_item

        return found

    def expandAll(self, start, end):
        results = []
        for item in self.mComponents:
            results.extend(item.expandAll(start, end))
        results = [x for x in set(results)]
        results.sort(key=lambda x:x[0].getPosixTime())
        return results

    def sortedPropertyKeyOrder(self):
        return (
            definitions.cICalProperty_TZID,
            definitions.cICalProperty_LAST_MODIFIED,
            definitions.cICalProperty_TZURL,
        )

    @staticmethod
    def sortByUTCOffsetComparator(tz1, tz2):
        sort1 = tz1.getUTCOffsetSortKey()
        sort2 = tz2.getUTCOffsetSortKey()
        if sort1 == sort2:
            return tz1.getID().compareToIgnoreCase(tz2.getID())
        else:
            return (1, -1)[sort1 < sort2]
