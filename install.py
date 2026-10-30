# installer for the weewx-rtldavis driver
# Copyright 2019 Matthew Wall and Luc Heijst
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller

def loader():
    return RtldavisInstaller()

class RtldavisInstaller(ExtensionInstaller):
    def __init__(self):
        super(RtldavisInstaller, self).__init__(
            version="0.22.0",
            name='rtldavis',
            description='Receive Davis wireless weather data with RTL-SDR',
            author="Matthew Wall, Luc Heijst, weewx-packages",
            author_email="",
            files=[('bin/user', ['bin/user/rtldavis.py',
                                 'bin/user/rtldavis_receiver.py',
                                 'bin/user/rtldavis_dsp.py'])]
        )
