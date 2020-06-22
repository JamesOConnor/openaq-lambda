import requests

from src import generate_bokeh_plot, get_dataframes_for_parameters, unpack_city_response, unpack_query_params, \
    RequestValidator


def lambda_handler(event, context):

    if not event.get('queryStringParameters'):
        form = requests.get('http://joc-website.s3-website.eu-central-1.amazonaws.com/openaq_form.html')
        response = {
            "statusCode": 200,
            "body": form.text,
            "headers": {
                'Content-Type': 'text/html',
            }}
        return response

    city, location_limit, result_limit, var = unpack_query_params(event)
    errors = RequestValidator().validate(
        {'city': city, 'var': var, 'result_limit': result_limit, 'location_limit': location_limit})
    if errors:
        return errors

    city = city.split(',')[0]
    city_resp = requests.get(f'https://api.openaq.org/v1/locations?city={city}')
    if city_resp.status_code == 429:
        return {"statusCode": 429, "body": "Rate limit reached", "headers": {'Content-Type': 'text/html', }}

    city_resp_body = city_resp.json()
    if city_resp_body.get('meta').get('found') == 0:
        return {"statusCode": 200, "body": "No data for this city", "headers": {'Content-Type': 'text/html', }}

    location_coords, location_ids = unpack_city_response(city_resp_body)
    chosen_location_coords, chosen_location_dataframes, unit = get_dataframes_for_parameters(location_coords,
                                                                                             location_ids,
                                                                                             location_limit,
                                                                                             result_limit, var)
    if len(chosen_location_dataframes) == 0:
        return {"statusCode": 200, "body": "No data for this query", "headers": {'Content-Type': 'text/html', }}

    html = generate_bokeh_plot(chosen_location_coords, chosen_location_dataframes, city, result_limit, unit, var)
    response = {"statusCode": 200, "body": html, "headers": {'Content-Type': 'text/html', }}
    return response
