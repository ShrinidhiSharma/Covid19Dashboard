import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import os
import json
from datetime import datetime, timedelta
import requests        
from dash.dependencies import Output , Input      
from plotly.subplots import make_subplots 
from plotly.graph_objs import *
from datetime import datetime as dt
import plotly.express as px
from scipy.integrate import odeint
from scipy.optimize import minimize,curve_fit
from flask import send_from_directory
global glob_data, beta, gamma

ts_cases_path = "../../data/processed/time_series_covid19_confirmed_global.csv"
ts_deaths_path = "../../data/processed/time_series_covid19_deaths_global.csv"
ts_recovery_path = "../../data/processed/time_series_covid19_recovered_global.csv"




print(os.getcwd())
df_input_large=pd.read_csv('../../data/processed/processed/COVID_final_set.csv',sep=';')
fig = go.Figure()


beta=0.4   
gamma=0.1

def get_data():
    data_table = []
    url="https://corona.lmao.ninja/v2/countries?yesterday&sort"
    data= requests.get(url)
    data=json.loads(data.text)
    for item in data:
        data_table.append([item['countryInfo']['iso3'],item['country'],item['cases'],item['recovered'],item['active'],item['deaths'],item['critical'], item['population']])
    data = pd.DataFrame(data_table,columns = ['Code','Country', 'Confirmed', 'Recovered', 'Active', 'Deaths','Critical', 'Population'])
    data = data.sort_values(by = 'Confirmed', ascending=False)
    return data

def get_country_data(country):

    till_date_data=[]

    url=f"https://api.covid19api.com/total/country/{country}"
    requested_data= requests.get(url)
    requested_data=json.loads(requested_data.text)

    for each in requested_data:
        till_date_data.append([each['Date'][:10],each['Confirmed'],each['Recovered'],each['Active'],each['Deaths']])

    country_data = pd.DataFrame(till_date_data,columns = ['Date','Confirmed', 'Recovered', 'Active', 'Deaths',])

    data = country_data[['Confirmed','Recovered','Deaths']]
    unrepaired_data= data - data.shift(1)

    false_index_deaths = list(unrepaired_data.index[unrepaired_data['Deaths'] < 0])

    if false_index_deaths != None :
        for each in false_index_deaths:
            data.at[each,'Deaths'] = data.at[each-1,'Deaths']

    false_index_confirmed = list(unrepaired_data.index[unrepaired_data['Confirmed'] < 0])

    if false_index_confirmed != None :
        for each in false_index_confirmed:
            data.at[each,'Confirmed'] = data.at[each-1,'Confirmed']


    false_index_recovered = list(unrepaired_data.index[unrepaired_data['Recovered'] < 0])

    if false_index_recovered != None :
        for each in false_index_recovered:
            data.at[each,'Recovered'] = data.at[each-1,'Recovered']

    daily_data = data - data.shift(1)
    daily_data = daily_data.fillna(0)
    daily_data = daily_data.mask(daily_data < 0, 0)

    new_data = pd.concat([country_data[['Date']],data,daily_data], axis=1, sort=False)
    new_data.columns = ['Date', 'Total_confirmed', 'Total_recovered', 'Total_deaths', 'Daily_confirmed','Daily_recovered', 'Daily_deaths']

    return new_data


def collected_data(data, country_code = 'DEU'):
    
    if country_code == 'KOR':
        return 'KOR'
        
    if country_code != "USA":
        data = np.array(data[['Code','Country']])

        for records in data:
            if records[0] == country_code:
                break

        return records[1]

    if country_code == 'USA':
        return 'United States'
        
#to fetch the total world stats
def total_status():

    url = 'https://api.covid19api.com/world/total'
    data = requests.get(url)
    total_data = json.loads(data.text)

    total_confirmed = f'{total_data["TotalConfirmed"]:,}'
    total_deaths = f"{total_data['TotalDeaths']:,}"
    total_recovered = f"{total_data['TotalRecovered']:,}"
    total_active = total_data["TotalConfirmed"] -total_data['TotalDeaths'] - total_data['TotalRecovered']
    total_active = f"{total_active:,}"

    return total_confirmed,total_recovered,total_active,total_deaths

glob_data = get_data()
glob_data = glob_data.dropna()
comparision_countries_list = glob_data.sort_values('Confirmed',ascending = False)
comparision_countries_list = comparision_countries_list[0:187]
sir_simulation_countries_list = comparision_countries_list[0:187]
confirmed, recovered, active, deaths = total_status()




def prepare_daily_report():
    

    current_date = (datetime.today() - timedelta(days=1)).strftime('%m-%d-%Y')
    if (os.path.isfile('coviddashboard/data/raw/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports/' + current_date + '.csv')):
        df = pd.read_csv('coviddashboard/data/raw/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports/' + current_date + '.csv')
    else:
        current_date = (datetime.today() - timedelta(days=2)).strftime('%m-%d-%Y')
        df = pd.read_csv('coviddashboard/data/raw/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports/' + current_date + '.csv')
    
    df_country = df.groupby(['Country_Region']).sum().reset_index()
    df_country.replace('US', 'United States', inplace=True)
    df_country.replace(0, 1, inplace=True)
    
    code_df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/2014_world_gdp_with_codes.csv')
    df_country_code = df_country.merge(code_df, left_on='Country_Region', right_on='COUNTRY', how='left')

    df_country_code.loc[df_country_code.Country_Region == 'Congo (Kinshasa)', 'CODE'] = 'COD'
    df_country_code.loc[df_country_code.Country_Region == 'Congo (Brazzaville)', 'CODE'] = 'COG'
    
    return(df_country_code)


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Covid19-Dash'


#app.layout = html.Div([html.Div([html.H1("COVID19 Global Cases")],
#                                style={'textAlign': "center", "padding-bottom": "30"}
#                               ),
#                       html.Div([html.Span("Choose the required Metric to be displayed : ", className="six columns",
#                                           style={"text-align": "right", "width": "40%", "padding-top": 10}),
#                                 dcc.Dropdown(id="value-selected", value='Confirmed',
#                                              options=[{'label': "Confirmed ", 'value': 'Confirmed'},
#                                                       {'label': "Recovered ", 'value': 'Recovered'},
#                                                       {'label': "Deaths ", 'value': 'Deaths'},
#                                                       {'label': "Active ", 'value': 'Active'}],
#                                              style={"display": "block", "margin-left": "auto", "margin-right": "auto",
#                                                     "width": "70%"},
#                                              className="six columns")], className="row"),
#                       dcc.Graph(id="my-graph")
#                       ],
#    
#    
#    className="container")
    
    
app.layout = html.Div([
        
        html.Div([html.Div([html.H1("COVID19 Global Cases Dashboard")],
                                style={'textAlign': "center", "padding-bottom": "5",'font-weight': '1000','color':'#05386b','text-decoration': 'underline'}
                               ),
                       html.Div([html.Span("Choose the required Metric to be displayed : ", className="six columns",
                                           style={"text-align": "right", "width": "40%", "padding-top": "10",'color':'#05386b'}),
                                 dcc.Dropdown(id="value-selected", value='Confirmed',
                                              options=[{'label': "Confirmed ", 'value': 'Confirmed'},
                                                       {'label': "Recovered ", 'value': 'Recovered'},
                                                       {'label': "Deaths ", 'value': 'Deaths'},
                                                       {'label': "Active ", 'value': 'Active'}],
                                              style={"display": "block", "margin-left": "auto", "margin-right": "auto",
                                                     "width": "70%"},
                                              className="six columns")], className="row"),
                       dcc.Graph(id="my-graph",style={"display": "block", "margin-left": "auto", "margin-right": "auto",
                                                     "width": "80%","padding-bottom":"10"}),
                       ], className = 'container'),
           
          
               html.Div([ html.Div([
                dcc.Graph(id = 'fig_2',style = {'height':'289px','backgroundColor' : "#7395AE", "width": "80%", "text-align": "center","padding-bottom": "300","margin": "auto"} ),
                dcc.Interval(id = 'fig_2_update', interval= 360*1000, n_intervals = 0)
            ], style = {'height':'300px','backgroundColor' : "#7395AE", "width": "100%", "text-align": "center","padding-bottom": "300","margin": "auto",'border': '5px solid #05386b'} ,
    className = 'five columns'),
    ], className = 'row'),
        
            
             html.Div([
            html.Div([
                dcc.Graph(id = 'fig_3'),
                dcc.Interval(id= 'fig_3_update' , interval = 360*1000 , n_intervals= 0)
            ],style = {'backgroundColor' : "#18191c", "width": "31%", "text-align": "center","display": "inline-block", 'border-style': 'groove', 'border': '5px solid #05386b'}, 
            className ='four columns'),
            html.Div([
                dcc.Graph(id = 'fig_4'),
                dcc.Interval(id = 'fig_4_update' , interval = 360*1000 , n_intervals=0)
            ], style = {'backgroundColor' : "#18191c", "width": "31%", "text-align": "center","display": "inline-block", 'border-style': 'groove', 'border': '5px solid #05386b'}, 
            className = 'four columns'),
            html.Div([
                dcc.Graph(id = 'fig_5' ),
                dcc.Interval(id = 'fig_5_update' , interval = 360*1000 , n_intervals= 0)
            ], style = {'backgroundColor' : "#18191c", "width": "30%", "text-align": "center","display": "inline-block",'border-style': 'groove', 'border': '5px solid #05386b'}, 
            className = 'four columns')
        ], style = {'margin-top':'50','width':'100%','backgroundColor':'#7395AE'}, 
           className = 'row'),
            
               html.Div([
            html.Div([
                dcc.Graph(id = 'fig_6'),
                dcc.Interval(id= 'fig_6_update' , interval = 360*1000 , n_intervals= 0)
            ],  style = {'backgroundColor' : "#18191c", "width": "31%", "text-align": "center","display": "inline-block",'border': '5px solid #05386b', 'margin-top':'50'}, 
            className ='four columns'),
            html.Div([
                dcc.Graph(id = 'fig_7'),
                dcc.Interval(id = 'fig_7_update' , interval = 360*1000 , n_intervals=0)
            ],  style = {'backgroundColor' : "#18191c", "width": "31%", "text-align": "center","display": "inline-block",'border': '5px solid #05386b','margin-top':'50'}, 
            className = 'four columns'),
            html.Div([
                dcc.Graph(id = 'fig_8' ),
                dcc.Interval(id = 'fig_8_update' , interval = 360*1000 , n_intervals= 0)
            ],  style = {'backgroundColor' : "#18191c", "width": "30%", "text-align": "center","display": "inline-block",'border': '5px solid #05386b','margin-top':'50'}, 
            className = 'four columns'),
            
              ],style = {'margin-top':'50','width':'100%','backgroundColor':'#7395AE'},  className = 'row'),
            
            html.Div([
            html.Div([

    dcc.Markdown('''
    COVID-19 Status by Country

    ''',style={'font-weight': 'bold','color':'#05386b' , 'backgroundColor':"#edf5e1",'width':'100%','text-align':'center','font-size':'150%'}),

    dcc.Markdown('''
    Select one or more countries for visualization
    ''',style={'color':'#05386b' , 'backgroundColor':"#edf5e1",'width':'100%','text-align':'left'}),


    dcc.Dropdown(
        id='country_drop_down',
        options=[ {'label': each,'value':each} for each in df_input_large['country'].unique()],
        value=['US', 'Germany','Italy'],
        multi=True,
        style={"display": "block", "align":"left",
                                                     "width": "50%"}
    ),

    dcc.Markdown('''
         Choose either COVID-19 case increase timeline or approx. doubling time
        ''',style={'color':'#05386b' , 'backgroundColor':"#edf5e1",'width':'100%','text-align':'left'}),


    dcc.Dropdown(
    id='doubling_time',
    options=[
        {'label': 'Timeline Confirmed ', 'value': 'confirmed'},
        {'label': 'Timeline Confirmed Filtered', 'value': 'confirmed_filtered'},
        {'label': 'Timeline Doubling Rate', 'value': 'confirmed_DR'},
        {'label': 'Timeline Doubling Rate Filtered', 'value': 'confirmed_filtered_DR'},
    ],
    value='confirmed',
    multi=False, style={"display": "block", "align":"left",
                                                     "width": "50%"},
    ),

    dcc.Graph(figure=fig, id='main_window_slope')
],style = {'backgroundColor' : "#edf5e1", "text-align": "center","display": "inline-block",'border': '5px solid #05386b','margin-top':'50', 'width':'810px'}
            ,className = 'four columns'),
            
            
            
            
            
            
            
            
      
       
        
        
        
        html.Div([
            html.Div([
                html.H3(children = '20 Worst Affected Countries' , style = {'font-weight': 'bold','color':'#05386b' , 'backgroundColor':"#edf5e1",'width':'100%','text-align':'center'}),
                html.Div(id = 'table_data'),
                dcc.Interval(id='update_table' , interval= 480*1000 , n_intervals=0)
            ], className = 'container'),
    
    
    
    
        ] ,style = {'float':'right','margin':'auto','width':'35%','backgroundColor':"#edf5e1",'border': '5px solid #05386b'},
            className = 'row'),
            ],style = {'backgroundColor':'#7395AE'},  className = 'row'),
    
    
    
            
    html.Div([   
    html.Div('SIR SIMULATIONS',style = {'textAlign':'center',
    'backgroundColor': '#edf5e1',
    'font-size': '23px',
    'textTransform': 'uppercase',
    'lineHeight': '40px',
    'display' : 'block',
    'font-weight': 'bold','color':'#05386b'}),

    html.Div([
            dcc.Dropdown(id = 'simulation_countries',
        options=[{'label': country_name, 'value': country_code} for country_name,country_code in zip(sir_simulation_countries_list["Country"],sir_simulation_countries_list["Code"]) ],
        value="DEU",
    )
        ]),

    html.Div([
        dcc.Graph(id = "SIR_simulations")
   ])],style={'backgroundColor' : "#edf5e1", "text-align": "center","display": "inline-block",'border': '5px solid #05386b','margin-top':'50', 'width':'100%'},
       
    ),    

   
    

   
],
    
    
  )


                


@app.callback(
    [dash.dependencies.Output("my-graph", "figure"),
     dash.dependencies.Output('main_window_slope', 'figure'),

    dash.dependencies.Output('fig_2' , 'figure'),
     dash.dependencies.Output('fig_3', 'figure'),
     dash.dependencies.Output('fig_4' , 'figure'),
     dash.dependencies.Output('fig_5' , 'figure'),
     dash.dependencies.Output('fig_6' , 'figure'),
     dash.dependencies.Output('fig_7' , 'figure'),
     dash.dependencies.Output('fig_8' , 'figure'),
     dash.dependencies.Output('table_data' , 'children'),
     dash.dependencies.Output('SIR_simulations','figure')
     ],
    [dash.dependencies.Input("value-selected", "value"),
     dash.dependencies.Input('country_drop_down', 'value'),
    dash.dependencies.Input('doubling_time', 'value'),
    dash.dependencies.Input('fig_2_update' , 'n_intervals'),
    dash.dependencies.Input('simulation_countries', 'value')]
)
def update_figure(selected,country_list,show_doubling,n,value):
    #dff = prepare_confirmed_data()

    dff = prepare_daily_report()
    dff['hover_text'] = dff["Country_Region"] + ": " + dff[selected].apply(str)

    trace = go.Choropleth(locations=dff['CODE'],z=np.log(dff[selected]),
                          text=dff['hover_text'],
                          hoverinfo="text",
                          marker_line_color='white',
                          autocolorscale=False,
                          reversescale=True,
                          colorscale="RdBu",marker={'line': {'color': 'rgb(180,180,180)','width': 0.5}},
                          colorbar={"thickness": 10,"len": 0.3,"x": 0.9,"y": 0.7,
                                    'title': {"text": 'persons', "side": "bottom"},
                                    'tickvals': [ 2, 10],
                                    'ticktext': ['100', '100,000']})   
    
    
    
    if 'doubling_rate' in show_doubling:
        my_yaxis={'type':"log",
               'title':'Approximated doubling rate over 3 days (larger numbers are better #stayathome)'
              }
    else:
        my_yaxis={'type':"log",
                  'title':'Confirmed infected people (source johns hopkins csse, log-scale)'
              }


    traces = []
    for each in country_list:

        df_plot=df_input_large[df_input_large['country']==each]

        if show_doubling=='doubling_rate_filtered':
            df_plot=df_plot[['state','country','confirmed','confirmed_filtered','confirmed_DR','confirmed_filtered_DR','date']].groupby(['country','date']).agg(np.mean).reset_index()
        else:
            df_plot=df_plot[['state','country','confirmed','confirmed_filtered','confirmed_DR','confirmed_filtered_DR','date']].groupby(['country','date']).agg(np.sum).reset_index()
       #print(show_doubling)


        traces.append(dict(x=df_plot.date,
                                y=df_plot[show_doubling],
                                mode='markers+lines',
                                opacity=0.9,
                                name=each
                        )
                )
    
    
    
    
    
    data_raw = requests.get('https://services1.arcgis.com/0MSEUqKaxRlEPj5g/arcgis/rest/services/Coronavirus_2019_nCoV_Cases/FeatureServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=json')
    data_raw_json = data_raw.json()
    data = pd.DataFrame(data_raw_json['features'])
    data_list = data['attributes'].tolist()

    data_final = pd.DataFrame(data_list)
    data_final.set_index('OBJECTID')
    data_final = data_final[['Country_Region' ,'Province_State' , 'Lat' , 'Long_', 'Confirmed' , 'Recovered' , 'Deaths','Last_Update' ]]

    def convertTime(t):
        t = int(t)
        return datetime.fromtimestamp(t)

    data_final = data_final.dropna(subset=['Last_Update'])
    data_final['Province_State'].fillna(value="" , inplace=True)

    data_final['Last_Update'] = data_final['Last_Update']/1000

    # data final
    data_final['Last_Update'] = data_final['Last_Update'].apply(convertTime)

    data_total = data_final.groupby('Country_Region' , as_index=False).agg(
        {
            'Confirmed':'sum',
            'Recovered' : 'sum',
            'Deaths' : 'sum'
        }
    )
    ts_cases = pd.read_csv(ts_cases_path, parse_dates=['Date'])
    ts_cases = ts_cases[['Date' , 'Cases']]
    ts_deaths = pd.read_csv(ts_deaths_path , parse_dates = ['Date'])
    ts_deaths = ts_deaths[['Date' , 'Deaths']]
    ts_recovery = pd.read_csv(ts_recovery_path , parse_dates = ['Date'])
    ts_recovery = ts_recovery[['Date' , 'Recovery']]
    total_confirmed = data_total['Confirmed'].sum()
    total_recovered = data_total['Recovered'].sum()
    total_deaths = data_total['Deaths'].sum()
    # current numbers
    current_date = data_final['Last_Update'].dt.date.max()
    c_cases = total_confirmed
    c_deaths = total_deaths
    c_recovery = total_recovered

    # function to update the csv files with current number
    def update_time_series(file , label, current_value , csvfile , current_date):
        last_date = csvfile['Date'].dt.date.max()
        if ( last_date == current_date):
            if (int(csvfile[csvfile.Date.dt.date == last_date][label].values) != current_value):
                csvfile.loc[csvfile['Date'] == last_date , label] = current_value
        else:
            csvfile = csvfile.append({'Date':current_date , label:current_value},ignore_index=True )
        csvfile.to_csv(file)

    # updating the csv file
    update_time_series(ts_cases_path , label='Cases' , current_value=c_cases , csvfile=ts_cases , current_date=current_date)
    update_time_series(ts_deaths_path , label="Deaths" , current_value=c_deaths , csvfile=ts_deaths , current_date=current_date)
    update_time_series(ts_recovery_path , label='Recovery' , current_value=c_recovery , csvfile=ts_recovery , current_date=current_date)

    msg = data_final['Country_Region'] + " " + data_final['Province_State'] + "<br>"
    msg += "Confirmed : " + data_final['Confirmed'].astype(str)+ "<br>"
    msg += "Recovered : " + data_final['Recovered'].astype(str)+ "<br>"
    msg += "Deaths : " + data_final['Deaths'].astype(str)+ "<br>"
    msg += "Last_Updated : " + data_final['Last_Update'].astype(str) + "<br>"

    data_final['text'] = msg

    # top 10 
    df_top10_cases = data_total.nlargest(10 , 'Confirmed')
    df_top10_recovery = data_total.nlargest(10 , 'Recovered')
    df_top10_deaths = data_total.nlargest(10, 'Deaths')
    
    
    
    
    
    
                   
                        
                        
                        
    fig_2 = make_subplots(
        rows = 2, cols = 3,
        specs = [
            [{'type':'indicator'} , {'type':'indicator'} , {'type':'indicator'}],
            [{'colspan':0 , 'type':'scatter'},None , None]
          
        ],
       # horizontal_spacing = 0.2
    )
    # number indicators
    fig_2.add_trace(
        go.Indicator(
            mode = 'number',
            value = total_confirmed,
            title = "TOTAL CASES"
        ),
        row =1 , col= 1
    )

    fig_2.add_trace(
        go.Indicator(
            mode = 'number' ,
            value = total_recovered,
            title = "TOTAL RECOVERED"
        ),
        row = 1 , col = 2
    )

    fig_2.add_trace(
        go.Indicator(
            mode = 'number' ,
            value = total_deaths,
            title = "TOTAL DEATHS"
        ),
        row = 1 , col = 3
    )
    # daily cases
    #

#    # daily deaths
#    daily_deaths = ts_deaths['Deaths'].diff()
#    fig_2.add_trace(
#        go.Scatter(
#            x = ts_deaths.loc[1: , 'Date'],
#            y = daily_deaths[1:],
#            mode = 'lines',
#            name = 'Daily Fatalities',
#            marker = dict(
#                color = 'red'
#            )
#        ),
#        row = 3 , col=1
#    )
#    # daily recovery
#    daily_recoveries = ts_recovery['Recovery'].diff()
#    fig_2.add_trace(
#        go.Scatter(
#            x = ts_recovery.loc[1:, 'Date'],
#            y = daily_recoveries[1:],
#            mode = 'lines',
#            name ='Daily Recoveries',
#            marker = dict(
#                color = 'green'
#            )
#        ),
#        row = 4 , col = 1
#    )
    # tweaking the layout
    fig_2.update_layout(paper_bgcolor ="#edf5e1" , 
                        plot_bgcolor="#edf5e1" , 
                        font = dict(color = '#05386b'),
                                  
                        legend_orientation='h',
                        legend = dict(x = 0.05 , y = 0.8))
    fig_2.update_xaxes(showgrid = False , zeroline = False ,showline=False )
    fig_2.update_yaxes(showgrid = False , zeroline = False , showline = False)
    
    
    
    
    
    
    
    
    fig_3 = go.Figure(
        data=    go.Scatter(
            x = ts_cases['Date'],
            y = ts_cases['Cases'],
            mode = 'lines',
            name = 'Cases Cumulative'
        )
    )
    fig_3.update_layout(title = '<b>GLOBAL CASES COUNT</b>' , paper_bgcolor ="#edf5e1" , 
                        plot_bgcolor="#edf5e1" , 
                        font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = -0.05))
    fig_3.update_xaxes(showgrid = False , zeroline = False ,showline=False )
    fig_3.update_yaxes(showgrid = False , zeroline = False , showline = False )

    ################### creating fig 4 #####################################################

    fig_4 = go.Figure(
        data = go.Scatter(
            x = ts_recovery['Date'],
            y = ts_recovery['Recovery'],
            mode = 'lines',
            name = 'Recovery Cumulative',
            marker = dict(color='green')
        )
    )
    fig_4.update_layout(title="<b>GLOBAL RECOVERY COUNT</b>" ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1" , font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = -0.05))
    fig_4.update_xaxes(showgrid = False , zeroline = False ,showline=False )
    fig_4.update_yaxes(showgrid = False , zeroline = False , showline = False)

    ############################ creating fig 5 ####################################################
    fig_5 = go.Figure(
        data = go.Scatter(
            x = ts_deaths['Date'],
            y = ts_deaths['Deaths'],
            mode = 'lines',
            name = 'Deaths Cumulative',
            marker = dict(color = 'red')
        )
    )
    fig_5.update_layout(title="<b>GLOBAL DEATH COUNT</b>" ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1" , font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = -0.05))
    fig_5.update_xaxes(showgrid = False , zeroline = False ,showline=False )
    fig_5.update_yaxes(showgrid = False , zeroline = False , showline = False)

    ########################## creating fig 6 #################################################
    d_r_1 = df_top10_cases.sort_values('Confirmed' , ascending=True)
    fig_6 = go.Figure(
        data =  go.Bar(
            x = d_r_1['Confirmed'],
            y = d_r_1['Country_Region'],
            orientation ='h',
            name = 'TOP 10 COUNTRIES - CASES',
        )
    )
    fig_6.update_layout(title = '<b>CASE COUNT IN 10 WORST <br>AFFECTED COUNTRIES</b>' ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1" , font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = -0.05))
    fig_6.update_xaxes(showgrid = False , zeroline = False ,showline=False)
    fig_6.update_yaxes(showgrid = False , zeroline = False , showline = False)

    ################################## creating fig 7 ##########################################

    d_r_2 = df_top10_recovery.sort_values('Recovered' , ascending=True )
    fig_7 = go.Figure(
        data = go.Bar(
            x = d_r_2['Recovered'],
            y = d_r_2['Country_Region'],
            orientation = 'h',
            name = 'TOP 10 COUNTRIES - RECOVERY',
            marker = dict(color = 'LightGreen')
        )
    )
    fig_7.update_layout(title='<b>TOTAL RECOVERIES IN 10 WORST <br>AFFECTED COUNTRIES</b>' ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1" , font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = 0.05))
    fig_7.update_xaxes(showgrid = False , zeroline = False ,showline=False)
    fig_7.update_yaxes(showgrid = False , zeroline = False , showline = False)

    #################################### creating fig 8 ##########################################
    d_r_3 = df_top10_deaths.sort_values('Deaths' , ascending=True )
    fig_8 = go.Figure(
        data = go.Bar(
            x = d_r_3['Deaths'],
            y = d_r_3['Country_Region'],
            orientation = 'h',
            name = 'TOP 10 COUNTRIES - DEATHS',
            marker = dict(color = '#eb3131')
        )
    )
    fig_8.update_layout(title = '<b>TOTAL DEATHS IN 10 WORST <br>AFFECTED COUNTRIES</b>' ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1" , font = dict(color = '#05386b') ,legend_orientation='h', legend = dict(x = 0.1 , y = -0.05))
    fig_8.update_xaxes(showgrid = False , zeroline = False ,showline=False)
    fig_8.update_yaxes(showgrid = False , zeroline = False , showline = False)

    ###################### updating table data ################################################

    def generate_table(dataframe, max_rows=10):
        return html.Table([
            html.Thead(
                html.Tr([html.Th(col) for col in dataframe.columns] , style = {'color':'#05386b'})
            ),
            html.Tbody([
                html.Tr([
                    html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
                ] , style = {'color':'#05386b'}) for i in range(min(len(dataframe), max_rows))
            ])
        ], style = {
            'backgroundColor':"#edf5e1"
        })
    df_table = data_total.sort_values('Confirmed' ,ascending=False)
    table = generate_table(df_table , max_rows=20)
    
    
    
    
    
    #############################################3
    country = collected_data(glob_data,value)
    data = get_country_data(country)
    data_size = 8
    t = np.arange(data_size)
    N = glob_data[glob_data['Code'] == value]['Population'].values[0]

    def SIR(y, t, beta, gamma):
        S = y[0]
        I = y[1]
        R = y[2]
        return -beta*S*I/N, (beta*S*I)/N-(gamma*I), gamma*I
   # print(t,beta, gamma)

    def fit_odeint(t,beta, gamma):
        return odeint(SIR,(s_0,i_0,r_0), t, args = (beta,gamma))[:,1]

    def loss(point, data, s_0, i_0, r_0):
        predict = fit_odeint(t, *point)
        l1 = np.sqrt(np.mean((predict - data)**2))
        return l1

    predicted_simulations = []

    for i in range(len(data)-data_size):
        if i%data_size == 0:
            j = i
            train = list(data['Total_confirmed'][i:i+data_size])
            i_0 = train[0]
            r_0 = data ['Total_recovered'].values[i]
            s_0 = N - i_0 - r_0
            params, cerr = curve_fit(fit_odeint,t, train)
            optimal = minimize(loss, params, args=(train, s_0, i_0, r_0))
            beta,gamma = optimal.x
            predict = list(fit_odeint(t,beta,gamma))
            predicted_simulations.extend(predict)

    train = list(data['Total_confirmed'][-data_size:])
    i_0 = train[0]
    r_0 = data ['Total_recovered'].values[-data_size]
    s_0 = N - i_0 - r_0
    params, cerr = curve_fit(fit_odeint, t, train)
    optimal = minimize(loss, params, args=(train, s_0, i_0, r_0))
    beta,gamma = optimal.x
    predict = list(fit_odeint(np.arange(data_size + 7), beta, gamma))
    predicted_simulations.extend(predict[j-i-8:])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data['Total_confirmed'],
                        mode='lines+markers',
                        name='Actual'))
    
    ## insert extra dates here
    dates = data["Date"].values.tolist()
    last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    for _ in range (7):
        last_date += timedelta(days=1)
        dates.append(last_date.strftime("%Y-%m-%d"))
    
    fig.add_bar(x = dates[:len(predicted_simulations)], y=predicted_simulations, name = "Simulated")    
    fig.update_layout(height = 700,
                      paper_bgcolor ="#edf5e1" , 
                        plot_bgcolor="#edf5e1" , 
                        font = dict(color = '#05386b'))
    
    
    
    ################
    
    
    
    
    
    
    
    return [{"data": [trace],
            "layout": go.Layout(geo={'showframe': False,'showcoastlines': False,
                                                                      'projection': {'type': "miller"}},
        margin=dict(l=20, r=20, t=20, b=0))},
    {
            'data': traces,
            'layout': dict (
                width=800,
                height=500
                 ,paper_bgcolor ="#edf5e1" , plot_bgcolor="#edf5e1",

                xaxis={'title':'Timeline',
                        'tickangle':-45,
                        'nticks':20,
                        'tickfont':dict(size=14,color="#7f7f7f"),
                      },

                yaxis=my_yaxis
        )
    },
                fig_2,
                fig_3 ,
            fig_4 ,
            fig_5 ,
            fig_6 ,
            fig_7 ,
            fig_8 ,
            table,
            fig
          
    ]

if __name__ == '__main__':
    app.run_server(debug=True)
