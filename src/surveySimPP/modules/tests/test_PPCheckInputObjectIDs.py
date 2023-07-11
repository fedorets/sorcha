from surveySimPP.tests.data import get_test_filepath


def test_PPCheckInputObjectIDs():
    from surveySimPP.modules.PPCheckInputObjectIDs import PPCheckInputObjectIDs
    from surveySimPP.modules.PPReadOif import PPReadOif
    from surveySimPP.readers.CSVReader import CSVDataReader
    from surveySimPP.readers.OrbitAuxReader import OrbitAuxReader

    compval = 1

    orbit_reader = OrbitAuxReader(get_test_filepath("testorb.des"), "whitespace")
    padaor = orbit_reader.read_rows(0, 10)

    param_reader = CSVDataReader(get_test_filepath("testcolour.txt"), "whitespace")
    padacl = param_reader.read_rows(0, 10)

    padapo = PPReadOif(get_test_filepath("oiftestoutput.txt"), "whitespace")

    print(padaor)
    print(padacl)
    print(padapo)

    try:
        PPCheckInputObjectIDs(padaor, padacl, padapo)
        ret = 1
    except Exception:
        ret = 0

    assert ret == compval

    return
