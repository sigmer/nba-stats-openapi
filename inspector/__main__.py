import os
import argparse
import logging
import requests
import re
import yaml
import time
from deepmerge import Merger
from inspector import __version__

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
    'User-Agent': 'nba-stats-inspector/0.1.0',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.7'
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


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = {}

    doc['openapi'] = '3.0.1'
    doc['info'] = {
        'title': 'NBA Stats API',
        'description': 'OpenAPI documentation for the NBA Stats API generated by sigmer/nba-stats-openapi',
        'version': __version__
    }
    doc['servers'] = [{'url': base_url + base_path}]

    for endpoint in endpoints:
        handle_endpoint(doc, endpoint)

    # Uncomment to include header parameters
    # for key, value in headers.items():
    #     components = doc['components']
    #     parameters = components['parameters']
    #     header = {
    #         'name': key,
    #         'in': 'header',
    #         'required': True,
    #         'schema': {'type': 'string'},
    #         'example': value
    #     }
    #     parameters[key] = header
    #     components['parameters'] = parameters
    #     doc['components'] = components

    default = {}
    with open('/'.join([root_dir, 'templates', 'default.yaml'])) as f:
        default = yaml.load(f, Loader=yaml.Loader)

    merger = Merger([(list, ['append']), (dict, ['merge'])], [
        'override'], ['override'])
    merger.merge(doc, default)

    dist_dir = '/'.join([root_dir, 'dist/'])
    os.makedirs(os.path.dirname(dist_dir), exist_ok=True)
    with open(dist_dir + 'swagger.yaml', 'w') as output:
        yaml.dump(doc, output, sort_keys=False)


def handle_endpoint(doc, endpoint):
    response = get_endpoint(endpoint)
    logger.info(
        f'{endpoint}: {response.status_code}, {response.headers["Content-Type"]}')
    if response.status_code == 200 and response.headers['Content-Type'].startswith('text/html'):
        logger.warning(f'{endpoint} is not a valid endpoint')
        return
    if response.status_code == 400:
        req_params = get_required_parameters(response.text)
        params = dict.fromkeys(req_params, 'x')
        schemas = {}
        response_with_required = get_endpoint(endpoint, params)
        patterns = get_parameter_patterns(response_with_required.text)
        invalids = get_invalid_params(response_with_required.text)
        for param in req_params:
            pattern = patterns.get(param, None)
            if pattern:
                is_enum = re.match(
                    r'^\^?\(?(\([A-Za-z0-9 _-]+\)\|?)+\)?\??\$$', pattern)
                if is_enum:
                    enums = re.findall(r'\(([A-Za-z0-9 _-]+)\)', pattern)
                    schemas[param] = {'type': 'string', 'enum': enums}
                else:
                    schemas[param] = {'type': 'string', 'pattern': pattern}
            elif param not in invalids:
                # a string is valid
                schema = {'type': 'string'}
                if 'Date' in param:
                    schema['format'] = 'date'
                schemas[param] = schema
        for param in invalids:
            params[param] = 1
        response_with_nums = get_endpoint(endpoint, params)
        invalids_with_nums = get_invalid_params(response_with_nums.text)
        for param in invalids:
            if param not in invalids_with_nums:
                # a number is valid
                schemas[param] = {'type': 'number'}
            else:
                logger.warning(
                    f'Unable to determine the type of parameter {param}')
                schema = {'type': 'string'}
                if param.startswith('Date'):
                    schema['format'] = 'date'
                schemas[param] = schema
        add_path(doc, endpoint, schemas)
    current = endpoints.index(endpoint) + 1
    total = len(endpoints)
    logger.info(f'{round((current/total)*100)}% complete')


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


def get_invalid_params(text):
    params = []
    for error in text.split(';'):
        invalid = re.match(r".+is not valid for (?P<param>(\w+))\.", error)
        if invalid:
            params.append(invalid.group('param').strip())
    return params


def add_path(doc, endpoint, params):
    path = f'/{endpoint}'
    paths = doc.get('paths', {})
    if path in paths:
        logger.warning(f'{path} path already exists')
    else:
        param_refs = list(map(
            lambda p: {'$ref': f'#/components/parameters/{p}'}, params))
        # header_params = list(map(
        #     lambda p: {'$ref': f'#/components/parameters/{p}'}, headers))
        # param_refs.extend(header_params)
        paths.update({
            path: {
                'get': {
                    'parameters': param_refs,
                    'responses': {
                        '200': {'description': 'Success'}
                    }
                }
            }
        })
        doc.update({'paths': paths})
        for name, schema in params.items():
            add_parameter(doc, name)
            add_schema(doc, name, schema)


def add_parameter(doc, name):
    components = doc.get('components', {})
    parameters = components.get('parameters', {})
    if name in parameters:
        # TODO: check if it has the same schema
        pass
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
        pass
    else:
        schemas.update({
            name: schema
        })
        components.update({'schemas': schemas})
        doc.update({'components': components})


if __name__ == "__main__":
    main()
