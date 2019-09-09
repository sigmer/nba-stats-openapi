import os
import argparse
import logging
import requests
import re
import yaml
import time

parser = argparse.ArgumentParser()
parser.add_argument(
    '--log', '-l', help="the logging level (default: WARN)", default='WARN')
args = parser.parse_args()
log_level = getattr(logging, args.log.upper(), logging.WARN)
logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)
logger = logging.getLogger(__name__)

base_url = 'http://stats.nba.com'
base_path = '/stats'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
    'Accept-Language': 'en-US,en',
    'Referer': 'https://stats.nba.com/leaders/'
    # 'User-Agent': 'nba-stats-inspector/0.1.0',
}
endpoints = ['allstarballotpredictor', 'boxscoreadvancedv2', 'boxscorefourfactorsv2',
             'boxscoremiscv2', 'boxscoreplayertrackv2', 'boxscorescoringv2', 'boxscoresummaryv2',
             'boxscoretraditionalv2', 'boxscoreusagev2', 'commonTeamYears', 'commonallplayers',
             'commonplayerinfo', 'commonplayoffseries', 'commonteamroster', 'draftcombinedrillresults',
             'draftcombinenonstationaryshooting', 'draftcombineplayeranthro', 'draftcombinespotshooting',
             'draftcombinestats', 'drafthistory', 'franchisehistory', 'homepageleaders', 'homepagev2',
             'leaderstiles', 'leaguedashlineups', 'leaguedashplayerbiostats', 'leaguedashplayerclutch',
             'leaguedashplayerptshot', 'leaguedashplayershotlocations', 'leaguedashplayerstats',
             'leaguedashptdefend', 'leaguedashptteamdefend', 'leaguedashteamclutch', 'leaguedashteamptshot',
             'leaguedashteamshotlocations', 'leaguedashteamstats', 'leagueleaders', 'playbyplay', 'playbyplayv2',
             'playercareerstats', 'playercompare', 'playerdashboardbyclutch', 'playerdashboardbygamesplits',
             'playerdashboardbygeneralsplits', 'playerdashboardbylastngames', 'playerdashboardbyopponent',
             'playerdashboardbyshootingsplits', 'playerdashboardbyteamperformance', 'playerdashboardbyyearoveryear',
             'playerdashptpass', 'playerdashptreb', 'playerdashptshotdefend', 'playerdashptshots',
             'playergamelog', 'playerprofile', 'playerprofilev2', 'playersvsplayers', 'playervsplayer',
             'playoffpicture', 'scoreboard', 'scoreboardV2', 'shotchartdetail', 'shotchartlineupdetail',
             'teamdashboardbyclutch', 'teamdashboardbygamesplits', 'teamdashboardbygeneralsplits',
             'teamdashboardbylastngames', 'teamdashboardbyopponent', 'teamdashboardbyshootingsplits',
             'teamdashboardbyteamperformance', 'teamdashboardbyyearoveryear', 'teamdashlineups',
             'teamdashptpass', 'teamdashptreb', 'teamdashptshots', 'teamgamelog', 'teaminfocommon',
             'teamplayerdashboard', 'teamplayeronoffdetails', 'teamplayeronoffsummary', 'teamvsplayer',
             'teamyearbyyearstats', 'videoStatus']
# endpoints = ['playerprofile', 'franchisehistory', 'teamvsplayer']


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = {}

    doc['servers'] = [{'url': base_url + base_path}]

    for endpoint in endpoints:
        handle_endpoint(doc, endpoint)

    dist_dir = '/'.join([root_dir, 'dist/'])
    os.makedirs(os.path.dirname(dist_dir), exist_ok=True)
    with open(dist_dir + 'swagger.yaml', 'w') as output:
        yaml.dump(doc, output)


def handle_endpoint(doc, endpoint):
    response = get_endpoint(endpoint)
    logger.info(
        f'{endpoint}: {response.status_code}, {response.headers["Content-Type"]}')
    if response.status_code == 200 and response.headers['Content-Type'].startswith('text/html'):
        logger.warn(f'{endpoint} is not a valid endpoint')
        return
    if response.status_code == 400:
        req_params = get_required_parameters(response.text)
        params = dict.fromkeys(req_params, 'x')
        response_with_required = get_endpoint(endpoint, params)
        patterns = get_parameter_patterns(response_with_required.text)
        for param in params:
            pattern = patterns.get(param, None)
            if pattern:
                is_enum = re.match(
                    r'^\^?\(?(\([A-Za-z0-9 _-]+\)\|?)+\)?\??\$$', pattern)
                if is_enum:
                    enums = re.findall(r'\(([A-Za-z0-9 _-]+)\)', pattern)
                    params[param] = {'type': 'string', 'enum': enums}
                else:
                    params[param] = {'type': 'string', 'pattern': pattern}
            else:
                params[param] = {'type': 'string'}
        add_path(doc, endpoint, params)


def get_endpoint(endpoint, params={}):
    endpoint_url = ''.join([base_url, base_path, '/', endpoint])
    response = requests.get(endpoint_url, params=params,
                            headers=headers, timeout=5)
    # pause after each request so we don't hit the rate limit
    time.sleep(1)
    return response


def get_required_parameters(text):
    required_params = []
    for error in text.split(';'):
        required = re.match(
            r'^\s*(The )?(?P<param>((\w*)(\s\w+)*?))( property)? is required.?', error)
        if required:
            param = required.group('param')
            required_params.append(param.replace(' ', ''))
    return required_params


def get_parameter_patterns(text):
    patterns = {}
    for error in text.split(';'):
        pattern = re.match(
            r"^\s*The field (?P<param>((\w*)(\s\w+)*?)) must match the regular expression '(?P<pattern>(.*))'.?", error)
        if pattern:
            param = pattern.group('param')
            regex = pattern.group('pattern')
            patterns[param] = regex
    return patterns


def add_path(doc, endpoint, params):
    path = f'/{endpoint}'
    paths = doc.get('paths', {})
    if path in paths:
        logger.warn(f'{path} path already exists')
    else:
        for name, schema in params.items():
            add_schema(doc, name, schema)
            add_parameter(doc, name)
        paramRefs = map(
            lambda p: {'$ref': f'#/components/parameters/{p}'}, params)
        paths.update({
            path: {
                'get': {
                    'description': 'Auto generated using nba-stats-inspector',
                    'parameters': list(paramRefs),
                    'responses': {
                        '200': {'description': 'Auto generated using nba-stats-inspector'}
                    }
                }
            }
        })
        doc.update({'paths': paths})


def add_parameter(doc, name):
    components = doc.get('components', {})
    parameters = components.get('parameters', {})
    if name in parameters:
        # TODO: check if it has the same schema
        logger.info(f'{name} parameter already exists')
    else:
        parameters.update({
            name: {
                'name': name,
                'in': 'query',
                'schema': {'$ref': f'#/components/schemas/{name}'},
                'required': True
            }
        })
        components.update({'parameters': parameters})
        doc.update({'components': components})


def add_schema(doc, name, schema):
    components = doc.get('components', {})
    schemas = components.get('schemas', {})
    if name in schemas:
        # TODO: check if it has the same schema
        logger.info(f'{name} schema already exists')
    else:
        schemas.update({
            name: schema
        })
        components.update({'schemas': schemas})
        doc.update({'components': components})


if __name__ == "__main__":
    main()
