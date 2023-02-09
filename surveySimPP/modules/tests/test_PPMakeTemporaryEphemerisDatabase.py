#!/bin/python

import sqlite3
import pandas as pd
import os

from surveySimPP.tests.data import get_test_filepath


def test_PPMakeTemporaryEphemerisDatabase(tmp_path):

    from surveySimPP.modules.PPMakeTemporaryEphemerisDatabase import PPMakeTemporaryEphemerisDatabase
    from surveySimPP.modules.PPReadOif import PPReadOif

    temp_path = os.path.dirname(get_test_filepath('oiftestoutput.txt'))
    stem_name = ('testdb_PPIntermDB.db')
    daba = PPMakeTemporaryEphemerisDatabase(get_test_filepath('oiftestoutput.txt'), os.path.join(temp_path, stem_name), 'whitespace')

    cnx = sqlite3.connect(daba)
    cur = cnx.cursor()

    cur.execute('select * from interm')
    col_names = list(map(lambda x: x[0], cur.description))

    oif_database = pd.DataFrame(cur.fetchall(), columns=col_names)

    oif_file = PPReadOif(get_test_filepath('oiftestoutput.txt'), 'whitespace')
    pd.testing.assert_frame_equal(oif_file, oif_database)

    return
