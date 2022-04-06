#!/bin/python

import pytest
import pandas as pd
import sqlite3


def test_PPMatchPointing():

    from surveySimPP.modules.PPMatchPointing import PPMatchPointing
    padapo = PPMatchPointing('./data/test/baseline_10yrs_10klines.db', ['u', 'g', 'r', 'i', 'z', 'y'], 'SELECT observationId, observationStartMJD, filter, seeingFwhmGeom, seeingFwhmEff, fiveSigmaDepth, fieldRA, fieldDec, rotSkyPos FROM SummaryAllProps order by observationId')

    nlines = 10007

    nlinesdb = len(padapo.index)

    assert nlines == nlinesdb
    return
