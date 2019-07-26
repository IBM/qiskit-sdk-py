# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Timeslots for channels.
"""
import itertools
from collections import defaultdict
from typing import Tuple

from .channels import Channel
from .exceptions import PulseError


# pylint: disable=missing-return-doc


class Interval:
    """Time interval."""

    def __init__(self, begin: int, end: int):
        """Create an interval = (begin, end))

        Args:
            begin: begin time of this interval
            end: end time of this interval

        Raises:
            PulseError: when invalid time or duration is specified
        """
        if begin < 0:
            raise PulseError("Cannot create Interval with negative begin time")
        if end < 0:
            raise PulseError("Cannot create Interval with negative end time")
        if begin > end:
            raise PulseError("Cannot create Interval with time beginning after end")
        self._begin = begin
        self._end = end

    @property
    def begin(self):
        """Begin time of this interval."""
        return self._begin

    @property
    def end(self):
        """End time of this interval."""
        return self._end

    @property
    def duration(self):
        """Duration of this interval."""
        return self._end - self._begin

    def has_overlap(self, interval: 'Interval') -> bool:
        """Check if self has overlap with `interval`.

        Args:
            interval: interval to be examined

        Returns:
            bool: True if self has overlap with `interval` otherwise False
        """
        if self.begin < interval.end and interval.begin < self.end:
            return True
        return False

    def shift(self, time: int) -> 'Interval':
        """Return a new interval shifted by `time` from self

        Args:
            time: time to be shifted

        Returns:
            Interval: interval shifted by `time`
        """
        return Interval(self._begin + time, self._end + time)

    def __eq__(self, other):
        """Two intervals are the same if they have the same begin and end.

        Args:
            other (Interval): other Interval

        Returns:
            bool: are self and other equal.
        """
        if self._begin == other._begin and self._end == other._end:
            return True
        return False

    def __repr__(self):
        """Return a readable representation of Interval Object"""
        return "{}({}, {})".format(self.__class__.__name__, self.begin, self.end)


class Timeslot:
    """Named tuple of (Interval, Channel)."""

    def __init__(self, interval: Interval, channel: Channel):
        self._interval = interval
        self._channel = channel

    @property
    def interval(self):
        """Interval of this time slot."""
        return self._interval

    @property
    def channel(self):
        """Channel of this time slot."""
        return self._channel

    def shift(self, time: int) -> 'Timeslot':
        """Return a new Timeslot shifted by `time`.

        Args:
            time: time to be shifted
        """
        return Timeslot(self.interval.shift(time), self.channel)

    def __eq__(self, other) -> bool:
        """Two time-slots are the same if they have the same interval and channel.

        Args:
            other (Timeslot): other Timeslot
        """
        if self.interval == other.interval and self.channel == other.channel:
            return True
        return False

    def __repr__(self):
        """Return a readable representation of Timeslot Object"""
        return "{}({}, {})".format(self.__class__.__name__,
                                   self.channel,
                                   (self.interval.begin, self.interval.end))


class TimeslotCollection:
    """Collection of `Timeslot`s."""

    def __init__(self, *timeslots: Timeslot):
        """Create a new time-slot collection.

        Args:
            *timeslots: list of time slots
        Raises:
            PulseError: when overlapped time slots are specified
        """
        self._table = defaultdict(list)

        for slot in timeslots:
            for interval in self._table[slot.channel]:
                if slot.interval.has_overlap(interval):
                    raise PulseError("Cannot create TimeslotCollection from overlapped timeslots")
            self._table[slot.channel].append(slot.interval)

        self._timeslots = tuple(timeslots)

    @property
    def timeslots(self) -> Tuple[Timeslot, ...]:
        """`Timeslot`s in collection."""
        return self._timeslots

    @property
    def channels(self) -> Tuple[Channel, ...]:
        """Channels within the timeslot collection."""
        return tuple(self._table.keys())

    @property
    def start_time(self) -> int:
        """Return earliest start time in this collection."""
        return self.ch_start_time(*self.channels)

    @property
    def stop_time(self) -> int:
        """Return maximum time of timeslots over all channels."""
        return self.ch_stop_time(*self.channels)

    @property
    def duration(self) -> int:
        """Return maximum duration of timeslots over all channels."""
        return self.stop_time

    def ch_start_time(self, *channels: Channel) -> int:
        """Return earliest start time in this collection.

        Args:
            *channels: Channels over which to obtain start_time.
        """
        intervals = list(itertools.chain(*(self._table[chan] for chan in channels
                                           if chan in self._table)))
        if intervals:
            return min(interval.begin for interval in intervals)
        return 0

    def ch_stop_time(self, *channels: Channel) -> int:
        """Return maximum time of timeslots over all channels.

        Args:
            *channels: Channels over which to obtain stop time.
        """
        intervals = list(itertools.chain(*(self._table[chan] for chan in channels
                                           if chan in self._table)))
        if intervals:
            return max(interval.end for interval in intervals)
        return 0

    def ch_duration(self, *channels: Channel) -> int:
        """Return maximum duration of timeslots over all channels.

        Args:
            *channels: Channels over which to obtain the duration.
        """
        return self.ch_stop_time(*channels)

    def is_mergeable_with(self, other: 'TimeslotCollection') -> bool:
        """Return if self is mergeable with `other` collection.

        Args:
            other: TimeslotCollection to be checked
        """
        for slot in other.timeslots:
            if slot.channel in self.channels:
                for interval in self._table[slot.channel]:
                    if slot.interval.has_overlap(interval):
                        return False
        return True

    def merged(self, other: 'TimeslotCollection') -> 'TimeslotCollection':
        """Return a new TimeslotCollection merged with a specified `timeslots`

        Args:
            other: TimeslotCollection to be merged
        Raises:
            PulseError: when invalid time or duration is specified
        """
        if not self.is_mergeable_with(other):
            raise PulseError("Cannot merge with overlapped TimeslotCollection")
        res = TimeslotCollection()
        res.__merge(self)
        res.__merge(other)
        return res

    def __merge(self, other: 'TimeslotCollection') -> 'TimeslotCollection':
        """Merge self with a specified `other` collection.

        Args:
            other: TimeslotCollection to be merged
        """
        self._timeslots += other.timeslots
        for channel, slots in other._table.items():
            self._table[channel].extend(slots)

    def shift(self, time: int) -> 'TimeslotCollection':
        """Return a new TimeslotCollection shifted by `time`.

        Args:
            time: time to be shifted by
        """
        slots = [Timeslot(slot.interval.shift(time), slot.channel) for slot in self.timeslots]
        return TimeslotCollection(*slots)

    def __eq__(self, other) -> bool:
        """Two time-slot collections are the same if they have the same time-slots.

        Args:
            other (TimeslotCollection): other TimeslotCollection
        """
        if self.timeslots == other.timeslots:
            return True
        return False

    def __repr__(self):
        """Return a readable representation of TimeslotCollection Object"""
        rep = dict()
        for key, val in self._table.items():
            rep[key] = [(interval.begin, interval.end) for interval in val]
        return self.__class__.__name__ + str(rep)
