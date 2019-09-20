from inspector import __main__ as inspector


def test_get_required_parameters():
    test_string = 'GameID is required'
    res = inspector.get_required_parameters(test_string)
    assert len(res) == 1
    assert res == ['GameID']

    test_string = 'ClutchTime is required; '\
        'AheadBehind is required; ' \
        'PointDiff is required; ' \
        'The GameScope property is required.; ' \
        'The PlayerExperience property is required.; ' \
        'The PlayerPosition property is required.; ' \
        'The StarterBench property is required.; ' \
        'MeasureType is required; ' \
        'PerMode is required; ' \
        'PlusMinus is required; ' \
        'PaceAdjust is required; ' \
        'Rank is required; ' \
        'SeasonType is required; ' \
        'The Outcome property is required.; ' \
        'The Location property is required.; ' \
        'Month is required; ' \
        'The SeasonSegment property is required.; ' \
        'The DateFrom property is required.; ' \
        'The DateTo property is required.; ' \
        'OpponentTeamID is required; ' \
        'The VsConference property is required.; ' \
        'The VsDivision property is required.; ' \
        'The GameSegment property is required.; ' \
        'Period is required; ' \
        'LastNGames is required'
    res = inspector.get_required_parameters(test_string)
    assert len(res) == 25
    assert res == ['ClutchTime', 'AheadBehind',
                   'PointDiff', 'GameScope', 'PlayerExperience',
                   'PlayerPosition', 'StarterBench', 'MeasureType',
                   'PerMode', 'PlusMinus', 'PaceAdjust', 'Rank',
                   'SeasonType', 'Outcome', 'Location', 'Month',
                   'SeasonSegment', 'DateFrom', 'DateTo',
                   'OpponentTeamID', 'VsConference', 'VsDivision',
                   'GameSegment', 'Period', 'LastNGames']

    test_string = 'Game Scope is required; ' \
        'The Player Scope property is required.; ' \
        'Stat Category is required'
    res = inspector.get_required_parameters(test_string)
    assert len(res) == 3
    assert res == ['GameScope', 'PlayerScope', 'StatCategory']

    test_string = ''
    res = inspector.get_required_parameters(test_string)
    assert len(res) == 0
    assert res == []

    test_string = 'GameID is invalid'
    res = inspector.get_required_parameters(test_string)
    assert len(res) == 0
    assert res == []
