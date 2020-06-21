import requests

from src import generate_bokeh_plot, get_dataframes_for_parameters, unpack_city_response, unpack_query_params, \
    RequestValidator


def lambda_handler(event, context):
    if not event.get('queryStringParameters').get('city'):
        return 'No city'

    city, location_limit, result_limit, var = unpack_query_params(event)
    errors = RequestValidator().validate(
        {'city': city, 'var': var, 'result_limit': result_limit, 'location_limit': location_limit})
    if errors:
        return errors

    # Request city metadata
    city_resp = requests.get(f'https://api.openaq.org/v1/locations?city={city}').json()

    location_coords, location_ids = unpack_city_response(city_resp)

    chosen_location_coords, chosen_location_dataframes, unit = get_dataframes_for_parameters(location_coords,
                                                                                             location_ids,
                                                                                             location_limit,
                                                                                             result_limit, var)

    html = generate_bokeh_plot(chosen_location_coords, chosen_location_dataframes, city, result_limit, unit, var)

    response = {
        "statusCode": 200,
        "body": html,
        "headers": {
            'Content-Type': 'text/html',
        }}

    return response
