import dateutil.parser
from marshmallow import Schema, fields
import pandas as pd
import requests
from bokeh.embed import file_html
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.palettes import Spectral
from bokeh.plotting import figure
from bokeh.resources import CDN
from marshmallow.validate import OneOf, Range


class RequestValidator(Schema):
    """
    Validate incoming requests
    """
    city = fields.Str(required=True)
    var = fields.Str(required=False, validate=OneOf(('bc', 'co', 'no2', 'o3', 'pm10', 'pm25', 'so2')))
    result_limit = fields.Int(required=False, validate=Range(min=1, max=10000))
    location_limit = fields.Int(required=False, validate=Range(min=1, max=10))

def generate_bokeh_plot(chosen_location_coords, chosen_location_dataframes, city, result_limit, unit, var):
    """
    Returns html for generating a bokeh plot
    :param chosen_location_coords: list of location coordinates associated with air quality measurements
    :param chosen_location_dataframes: list of dataframes associated with stations
    :param city: city for the query
    :param result_limit: the number of results per location
    :param unit: the unit of measurement for the figure
    :param var: the variable of interest (id from openaq docs)
    :return: the html for the bokeh figure
    """
    bokeh_figure = figure(plot_width=1500, plot_height=600, x_axis_type='datetime',
                          title=f"{var} concentration for last {result_limit} readings from stations in {city}")
    colors = get_unique_colors(len(chosen_location_dataframes))

    for color, df, ll in zip(colors, chosen_location_dataframes, chosen_location_coords):
        bokeh_figure.line('date', 'val', source=df, alpha=1, legend_label=df['location'].iloc[0] + ': ' + str(ll)[1:-1],
                          color=color, line_dash='solid')

    bokeh_figure.legend.location = "top_left"
    bokeh_figure.legend.click_policy = "hide"

    bokeh_figure.add_tools(HoverTool(show_arrow=False, line_policy='next', tooltips=[
        ('date', '@date{%F}'),
        (var, '$data_y')
    ], formatters={'@date': 'datetime'}))
    bokeh_figure.xaxis.formatter = DatetimeTickFormatter(
        days=["%Y-%m-%d"],
        months=["%Y-%m-%d"],
        years=["%Y-%m-%d"],
    )
    bokeh_figure.xaxis.axis_label = 'Date'
    bokeh_figure.yaxis.axis_label = f'{var} concentration ({unit})'
    html = file_html(bokeh_figure, CDN, f"{var} concentration for last {result_limit} readings from stations in {city}")
    return html


def get_unique_colors(number):
    """
    Returns color hexes for a number of time series we are plotting
    :param chosen_location_dataframes:
    :return:
    """
    colors = Spectral[number] if number > 2 else ['#FF0000', '#0000ff'][:number]
    return colors


def get_dataframes_for_parameters(location_coords, location_ids, location_limit, result_limit, var):
    """
    Given the response from the city, generate dataframes from stations within that city
    :param location_coords: the coordinates of the stations
    :param location_ids: the ids of the stations to proxy the requests to
    :param location_limit: the number of locations we provision for
    :param result_limit: the number of results for a given station we want to return
    :param var: the variable to query for
    :return: the filtered location coordinates, dataframes and unit to plot
    """
    chosen_location_dataframes = []
    chosen_location_coords = []
    for idx, loc in enumerate(location_ids):
        if len(chosen_location_dataframes) == int(location_limit):
            break
        r = requests.get(
            f'https://api.openaq.org/v1/measurements?location={loc}&parameter={var}&limit={result_limit}')

        df = get_dataframe_for_response(loc, r)
        if len(df) == 0:  # Skip no data
            continue
        unit = r.json()['results'][0]['unit']
        chosen_location_dataframes.append(df)
        chosen_location_coords.append(location_coords[idx])
    return chosen_location_coords, chosen_location_dataframes, unit


def get_dataframe_for_response(loc, r):
    """
    Generate a dataframe for a given response from a station
    :param loc: the location id
    :param r: the response for that location
    :return: pandas dataframe
    """
    df = pd.DataFrame(
        [[dateutil.parser.parse(i['date']['local']), i['value'], loc] for i in r.json()['results']],
        columns=['date', 'val', 'location'])
    return df


def unpack_city_response(city_resp):
    """
    Generates required lists for downstream use given a city's response
    :param city_resp: response from querying for a given city
    :return: list of station coordinates and list of station ids
    """
    location_ids = [i['location'] for i in city_resp['results']]
    location_coords = [(i['coordinates']['latitude'], i['coordinates']['longitude']) for i in city_resp['results']]
    return location_coords, location_ids


def unpack_query_params(event):
    """
    Unpack initial query parameters from the request
    :param event: aws lambda event
    :return: the city, location_limit, result_limit and var parameters
    """
    city = event.get('queryStringParameters').get('city')
    var = event.get('queryStringParameters').get('var') or 'pm10'
    result_limit = event.get('queryStringParameters').get('result_limit') or 1000
    location_limit = event.get('queryStringParameters').get('loc_limit') or 5
    return city, location_limit, result_limit, var
