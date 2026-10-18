# SPDX-License-Identifier: BSD-2-Clause
#
# This file is part of pyosmium. (https://osmcode.org/pyosmium/)
#
# Copyright (C) 2024 Sarah Hoffmann <lonvia@denofr.de> and others.
# For a full list of authors see the git log.


# start delvewheel patch
def _delvewheel_patch_1_12_0():
    import os
    if os.path.isdir(libs_dir := os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'osmium.libs'))):
        os.add_dll_directory(libs_dir)


_delvewheel_patch_1_12_0()
del _delvewheel_patch_1_12_0
# end delvewheel patch

from ._osmium import (InvalidLocationError as InvalidLocationError,
                      apply as apply,
                      BaseHandler as BaseHandler,
                      BaseFilter as BaseFilter,
                      BufferIterator as BufferIterator,
                      SimpleWriter as SimpleWriter,
                      NodeLocationsForWays as NodeLocationsForWays,
                      OsmFileIterator as OsmFileIterator,
                      IdTracker as IdTracker)
from .helper import (make_simple_handler as make_simple_handler,
                     WriteHandler as WriteHandler,
                     MergeInputReader as MergeInputReader)
from .simple_handler import (SimpleHandler as SimpleHandler)
from .file_processor import (FileProcessor as FileProcessor,
                             zip_processors as zip_processors)
from .back_reference_writer import BackReferenceWriter as BackReferenceWriter
from .forward_reference_writer import ForwardReferenceWriter as ForwardReferenceWriter
import osmium.io
import osmium.osm
import osmium.index
import osmium.geom
import osmium.area
import osmium.filter
