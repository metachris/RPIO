# This file is part of RPIO.
#
# Copyright
#
#     Copyright (C) 2013 Chris Hager <chris@linuxuser.at>
#
# License
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Lesser General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Lesser General Public License for more details at
#     <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>
#
# Documentation
#
#     http://pythonhosted.org/RPIO
#
"""
This module contains all the exceptions used by the C GPIO wrapper.
"""
import RPIO._GPIO as _GPIO

WrongDirectionException = _GPIO.WrongDirectionException
InvalidModeException = _GPIO.InvalidModeException
InvalidDirectionException = _GPIO.InvalidDirectionException
InvalidChannelException = _GPIO.InvalidChannelException
InvalidPullException = _GPIO.InvalidPullException
ModeNotSetException = _GPIO.ModeNotSetException
