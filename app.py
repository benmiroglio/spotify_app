from flask import Flask, jsonify, render_template, request, send_file
import spotipy
from spotipy import oauth2
from collections import defaultdict
import pandas as pd
import os
import json
import re


app = Flask(__name__)

PORT_NUMBER = 8000
SPOTIPY_CLIENT_ID = '79c39d73e30e483faf9e49f36ee0d773'
SPOTIPY_CLIENT_SECRET = '8c9568ea87fe41cf9e1bfd8900092e42'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:{}'.format(PORT_NUMBER)
SCOPE = "playlist-read-collaborative user-library-read user-top-read"
CACHE = '.spotipyoauthcache'

sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET,SPOTIPY_REDIRECT_URI,scope=SCOPE,cache_path=CACHE )

username = None
TOKEN = None
_id = None


@app.route('/loading')
def loading():
    '''
    This path is called by jQuery and returns the results on the home page (/)
    Displays "Listing..." + a GIF while the user waits for a prediction to render
    '''
    return jsonify(result = '''
        <div id="spinner"
        <i class="fa fa-circle-o-notch fa-spin fa-5x fa-fw"></i>
        </div>
        ''')

@app.route('/templates/login.css')
def login_style():
    return open('templates/login.css').read()

@app.route('/username.txt')
def username():
    return open('username.txt').read()

@app.route('/user_hist.csv')
def user_hist():
    return open('user_hist.csv').read()

@app.route('/user_summary.csv')
def user_summary():
    return open('user_summary.csv').read()

@app.route('/top5_clean2.csv')
def top5_clean2():
    return open('top5_clean2.csv').read()

@app.route('/')
def index():
    global TOKEN, username, _id
    access_token = ""

    token_info = None
    print 'here'
    if token_info:
        print "Found cached token!"
        access_token = token_info['access_token']
    else:
        url = request.url
        code = sp_oauth.parse_response_code(url)
        print url
        print code
        if code:
            print "Found Spotify auth code in Request URL! Trying to get valid access token..."
            token_info = sp_oauth.get_access_token(code)
            access_token = token_info['access_token']

    if access_token:
        print "Access token available! Trying to get user information..."
        sp = spotipy.Spotify(access_token)
        results = sp.current_user()
        TOKEN = access_token
        username = results['id']
        _id = results['display_name']
        return render_template('untitled.html')

    else:
        return htmlForLoginButton()





def htmlForLoginButton():
    auth_url = getSPOauthURI()
    htmlLoginButton = '''
    <head>
    <script src="https://use.fontawesome.com/cc6ed501ab.js"></script>
    <link rel="stylesheet" type="text/css" href="templates/login.css">
    </head>
    <body>
    <h1>Login to Spotify</h1>
    <div class='button'>
    <a href={}>
    <i class="fa fa-key fa-5x" aria-hidden="true", id='DLbutton'></i>
    </a>
    </div>
    '''.format(auth_url)
    return htmlLoginButton

def getSPOauthURI():
    auth_url = sp_oauth.get_authorize_url()
    return auth_url


@app.route('/get_user_data')
def get_user_data():
    # TOKEN='BQAwLsyJbYWa_sSlULAizCNK3bt7gM8BzQRHS72v0_QVUT4QA5bVk2CUKwmnXRIR7FmuLMsyeMkC-4-MnwSIOyLpkbA4EGEI4M6Bfv-L83r5RbWOEgAwTSr9QAP04e-ZxOX8enFz5XK_Y41UCEPjyjNPjDmIaXzJ5vAd72JrqtJ7ALi1EooCXEyxkwbu3N7c8x-JBQv47K0FoSkaHOxVJvM_0BiqjyrVTaM3pD4KCDxSkIUA3xxDiBF43eHX5y_S8YufpEpyXsQFSvAzagTeWE4UK0tpXQ0nVKsUFPXmdagQG_sDYRhsQqk'
    # stores user's top songs over past year 
    # using Spotify's "Affinity" dataset for a user
    global TOKEN, username, _id
    print TOKEN, username
    song_ids = defaultdict(dict)


    # route curl to file
    command = \
    '''
    curl -X GET "https://api.spotify.com/v1/me/top/tracks?time_range=long_term&limit=50" -H "Accept: application/json" \
    -H "Authorization: \
    Bearer {}" > top_songs.json
    '''.format(TOKEN)
    os.system(command)

    with open('top_songs.json') as f:
        j = json.loads(f.read())


    if len(j['items']) == 0:
        return jsonify(result = '''
            <h1> No tracks found :( </h1>
            ''')
    for track in j['items']:
        image = track['album']['images'][0]['url'], 
        songid = track['id']
        name = re.sub("\W", ' ', track['name'])
        artist = re.sub("\W", ' ', track['artists'][0]['name'])
        print name, artist
        popularity = track['popularity']
        preview = track['preview_url']
        song_ids[songid] = {'art':image[0], 'popularity':popularity, \
                            'desc': "{} by {}".format(name, artist),\
                            'prev':preview} 



    command = \
    '''
    curl -X GET "https://api.spotify.com/v1/audio-features?ids={}" -H \
    "Accept: application/json" -H "Authorization: Bearer \
    {}" > track_feats.json
    '''.format(','.join(song_ids.keys()), TOKEN)
    os.system(command)

    with open('track_feats.json') as f:
        j = json.loads(f.read())

    for track in j['audio_features']:
        trackid = track['id']
        for feature in ['energy', 'liveness', \
        'tempo', 'speechiness', 'acousticness', 'danceability', \
        'loudness', 'valence', 'mode', 'instrumentalness']:
            song_ids[trackid][feature] = track[feature]



    command = \
    '''
    curl -X GET "https://api.spotify.com/v1/users/{}/playlists?limit=50" -H \
    "Accept: application/json" -H "Authorization: Bearer \
    {}" > playlists.json
    '''.format(username, TOKEN)
    os.system(command)

    with open('playlists.json') as f:
        j = json.loads(f.read())


    playlist_ids = []
    for playlist in j['items']:
        playlist_ids.append(playlist['id'])

    print len(playlist_ids)
    if len(playlist_ids) == 0:
        print 'no Found'
        return jsonify(result = '''
            <h1> No Playlists Found :(. 
            You must have playlists for the process to work! </h1>
            ''')
    track_dict = defaultdict(dict)
    for playlist_id in playlist_ids:
        print playlist_id
        os.system( \
        '''
        curl -X GET "https://api.spotify.com/v1/users/{}/playlists/{}/tracks" -H \
        "Accept: application/json" -H "Authorization: Bearer {}" > ptracks.json
        '''.format(username,playlist_id, TOKEN))
        with open('ptracks.json') as f:
            data = json.loads(f.read())
            try:
                for track in data['items']:
                    date = '-'.join(track['added_at'].split('-')[:2])
                    track_dict[track['track']['id']] = {'date':date}
            except:
                    print 'woops'
                    continue


    tracks = track_dict.keys()
    while len(tracks) >= 100:       
            subset = [tracks.pop() for i in range(100)]
            subset = [i for i in subset if i is not None]
            os.system(\
            '''
            curl -X GET "https://api.spotify.com/v1/audio-features?ids={}" -H "Accept: application/json" -H "Authorization: Bearer {}" > tracks.json
            '''.format(','.join(subset), TOKEN))
            with open('tracks.json') as f:
                j = json.loads(f.read())

            for track in j['audio_features']:
                trackid = track['id']
                for feature in ['energy', 'liveness', \
                'tempo', 'speechiness', 'acousticness', 'danceability', \
                'loudness', 'valence', 'mode', 'instrumentalness']:
                    track_dict[trackid][feature] = track[feature]
    if len(tracks) > 0:
        print tracks, 'OK"'
        os.system(\
        '''
        curl -X GET "https://api.spotify.com/v1/audio-features?ids={}" -H "Accept: application/json" -H "Authorization: Bearer {}" > tracks.json
        '''.format(','.join([i for i in tracks if i is not None]), TOKEN))
        with open('tracks.json') as f:
            j = json.loads(f.read())
        for track in j['audio_features']:
            trackid = track['id']
            for feature in ['energy', 'liveness', \
            'tempo', 'speechiness', 'acousticness', 'danceability', \
            'loudness', 'valence', 'mode', 'instrumentalness']:
                track_dict[trackid][feature] = track[feature]


    with open('user_hist.csv', 'w') as out:
        headers = track_dict.values()[0].keys()
        out.write(','.join(['track'] + headers))
        out.write('\n')
        for track in track_dict:
            try:
                out.write(','.join([track] + [str(track_dict[track][i]) for i in headers]))
                out.write('\n')
            except:
                continue


    with open('user_summary.csv', 'w') as out:
        headers = song_ids[song_ids.keys()[0]].keys()
        out.write(','.join(headers))
        out.write('\n')
        for key in song_ids:
            data = song_ids[key]
            out.write(','.join([str(data[i]) for i in headers]))
            out.write('\n')


    with open('username.txt', 'w') as f:
        print 'Writing Username {}'.format(_id)
        if _id:
            f.write(_id)

    import matplotlib.pyplot as plt
    import pandas as pd

    d = pd.DataFrame.from_csv('user_hist.csv', sep=',', index_col=None)
    values = d.values
    new_vals = []
    for v in values:
        for i in v:
            try:
                new_vals.append(float(i))
            except:
                continue


    def tonum(col):
        try:
            return pd.to_numeric(col)
        except:
            return col
    d.apply(tonum)

    new_d = d[['energy', u'liveness', u'tempo', u'speechiness',
           u'acousticness', u'instrumentalness', u'danceability',
           u'loudness', u'valence', u'mode']]
    dnorm = (new_d - new_d.mean()) / (pd.to_numeric(new_d.max()) - pd.to_numeric(new_d.min()))
    dnorm['date'] = d['date']
    dnorm['date'] = dnorm['date'].apply(str)

    # get histogram of all music features, (not by group)
    # x = [] 
    # for i in dnorm.values:
    #     for j in i:
    #         if type(j) == float:
    #             x.append(j)        
    # plt.hist(x, 100)
    # plt.title('Histogram of Normalized Music Features in Total')
    # plt.show()

    # # plot multi-line chart by date
    # dnorm.groupby('date').mean().plot(title="Spotify's Featured Song Characteristics by Year")
    # plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    # plt.show()

    # # plot multi-bar chart by date
    # dnorm.groupby('date').mean().plot.bar(title="Spotify's Featured Song Characteristics by Year")
    # plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    # plt.show()


    dnorm.groupby('date').mean().to_csv('user_hist.csv', index_col=None)

    d = pd.read_csv('user_summary.csv')
    new_d = d[['energy', u'liveness', u'tempo', u'speechiness',
           u'acousticness', u'instrumentalness', u'danceability',
           u'loudness', u'valence', 'mode']]

    dnorm = (new_d - new_d.mean()) / (pd.to_numeric(new_d.max()) - pd.to_numeric(new_d.min()))
    summary = dnorm.mean()

    with open('user_summary.csv', 'w') as out:
        out.write('feature,value')
        out.write('\n')
        for i in summary.index:
            out.write(','.join([str(i), str(summary[i])]))
            out.write('\n')


    d = d.sort_values('popularity', ascending=False)

    l = []
    seen = []
    for row in d.iterrows():
        if len(l) == 5:
            break
        row = row[1]
        art = row.art
        if art in seen:
            continue
        seen.append(art)
        l.append(row)

    d = pd.DataFrame(l)

    new_d = d[['energy', u'liveness', u'tempo', u'speechiness',
           u'acousticness', u'instrumentalness', u'danceability',
           u'loudness', u'valence']]

    dnorm = abs((new_d - new_d.mean()) / (pd.to_numeric(new_d.max()) - pd.to_numeric(new_d.min())))
    d['max_feat'] = dnorm.idxmax(axis=1)

    d.to_csv('top5_clean2.csv', index=False)
    return jsonify(result = """
<!DOCTYPE html>
<meta charset="utf-8">
<script src="//d3js.org/d3.v3.min.js"></script>

<style>

body {
font: 10px Helvetica;
margin: auto;
}


#proftext {
font: 0px;
}


.axis path,
.axis line {
fill: none;
stroke: #000;
shape-rendering: crispEdges;
}
form {
position: absolute;
right: 10px;
top: 10px;
}

.x.axis path {
display: none;
font-weight: 100;
}

.line {
fill: none;
stroke-width: 3px;
stroke-opacity: .5;
}

.lineHover {
fill: none;
stroke: transparent;
stroke-width: 6px;
}


/*#energy {
stroke-width: 5px;
}*/

</style>
<body>
<h1></h1>
<p></p>
<script>

var margin = {top: 140, right: 80, bottom: 30, left: 80},
width = 1000- margin.left - margin.right,
height = 580 - margin.top - margin.bottom;

var parseDate = d3.time.format("%Y-%m").parse;

var x = d3.time.scale()
.range([20, width]);

var y = d3.scale.linear()
.range([height, 0]);

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
.scale(x)
.tickFormat(function(d, i){
return [d.getMonth(), d.getFullYear()].join('-')

});


var yAxis = d3.svg.axis()
.scale(y)
.orient("left");


var svg = d3.select("body").append("svg")
.attr("width", width + margin.left + margin.right + 600)
.attr("height", height + margin.top + margin.bottom + 320)
.append("g")
.attr("transform", "translate(" + margin.left + "," + margin.top + ")");


var score_descriptions = {
'danceability'    : "Danceability describes how suitable a track is "  + 
"for dancing based on a combination of musical "   + 
"elements",

'energy'          :  "Energy represents "+
"a perceptual measure of intensity and activity. "   + 
"Typically, energetic tracks feel fast, loud, and "  +
"noisy.",

'acousticness'    : "A confidence measure of whether the " + 
"track is acoustic.",

'instrumentalness': 'Predicts whether a track contains no vocals.' + 
'"Ooh" and "aah" sounds are treated as instrumental '+ 
'in this context.',

'liveness'        :  "Detects the presence of an audience in the recording. " +
"Higher liveness values represent an increased probability "+
"that the track was performed live.",

'loudness'        :  'The overall loudness of a track in decibels (dB) (normalized). '+
'Loudness values are averaged across the entire track',

'mode'            :  "Mode indicates the modality (major or minor) of a track",

'tempo'           :  "The overall estimated tempo of a track in beats per minute (BPM) (normalized)",

'speechiness'     :  "Speechiness detects the presence of spoken words in a track",

'valence'         :  "A measure describing the "+
"musical positiveness conveyed by a track. "+
"Tracks with high valence sound more positive"
}

user=''

d3.text('username.txt', function(error, data) {
if (error) throw error;
d3.select('h1').append('text').text('Spotify User: ' + data)
.style('font-size', 30).style('font-weight', 100)
user = data;
})

global_cols = []

d3.csv("user_hist.csv", function(error, data) {
if (error) throw error;

for (key in data[0]) {
if (key != 'date') {
global_cols.push(key)
}
}

color.domain(d3.keys(data[0]).filter(function(key) { return key !== "date"; }));

data.forEach(function(d) {
d.date = parseDate(d.date);
});

var interp = 'cardinal';

var line = d3.svg.line()
.interpolate(interp)
.x(function(d) { return x(d.date); })
.y(function(d) { return y(d.score); });

var lineHover = d3.svg.line()
.interpolate(interp)
.x(function(d) { return x(d.date); })
.y(function(d) { return y(d.score); });

var scores = color.domain().map(function(name) {
return {
name: name,
selected: true,
values: data.map(function(d) {
return {date: d.date, score: +d[name]};
})
};
});


x.domain(d3.extent(data, function(d) { return d.date; }));

y.domain([
d3.min(scores, function(c) { return d3.min(c.values, function(v) { return v.score; }); }) - .02,
d3.max(scores, function(c) { return d3.max(c.values, function(v) { return v.score; }); })
]);

svg.append("g")
.attr("class", "x axis")
.attr("transform", "translate(0," +height + ")")
.call(xAxis).style('font-weight', 100)
.style('font-size', '12px')

svg.append("g")
.attr("class", "y axis")
.call(yAxis)
.append("text")
.attr("transform", "rotate(-90, -70, 0) translate(-190)")
.attr("y", 6)
.attr("dy", ".71em")
.style("text-anchor", "end")
.text("Averge Normalized Score").style('font-weight', 100)
.style('font-size', '12px');

var score = svg.selectAll(".score")
.data(scores.filter(function(d){return d.selected=true}))
.enter().append("g")
.attr("class", "score");


// svg.append()
// add line with colors, smaller default stroke-width
score.append("path")
.attr("class", "line")
.attr("id", function(d) {return d.name})
.attr("d", function(d) { return line(d.values);})
.style("stroke", function(d) { return color(d.name);});


var highlight_line = function(d) {
if (d.selected == true) {
d3.selectAll('#' + d.name)
.style('stroke-width', '8px')
.style('stroke-opacity', '1');
d3.selectAll('#rect' + d.name)
.style('x', 1150)
.transition()
.style('fill-opacity', 1)
d3.selectAll('#' + 'side_text' + d.name).style('fill', color(d.name))
}
}

var unhighlight_line = function(d) {
if (d.selected == true) {
d3.selectAll('#' + d.name).style('stroke-width', '3px')
.style('stroke-opacity', '.5');
d3.selectAll('#rect' + d.name)
.style('x', 1100)
.transition().style('fill-opacity', .6)
d3.selectAll('#' + 'side_text' + d.name).style('fill', 'transparent')

}
}
// add transparent line, with thicker stoke width
// for easier highlighing
score.append("path")
.attr("class", "lineHover")
.attr("id", function(d) {return 'hover' +d.name})
.attr("d", function(d) { return line(d.values); })
.style("stroke-width", '20px')
.style('stroke', 'transparent')
.on("mouseover", highlight_line)
.on("mouseout", unhighlight_line)

score.append("text")
.datum(function(d) { return {name: d.name, value: d.values[d.values.length - 1]}; })
.attr("transform", function(d) { return "translate(" + x(d.value.date) + "," + y(d.value.score) + ")"; })
.attr("x", 20)
.attr('class', 'curtain')
.attr("dy", ".35em")
.attr('id', function(d) {return 'side_text' + d.name})
.text(function(d) { return d.name; })
.style('font-size', '30px')
.style('font-weight', 100)
.style('fill', 'transparent');


var legend = svg.append('g').attr('class', 'legend')
legend.selectAll('g').data(scores)
.enter()
.append('g')
.each(function(d, i) {
var score_id = d.name
g = d3.select(this)
g.append("circle")
.attr("class", "legend_circle")
.attr('id', 'LC' + d.name)
.attr("cx", 20 + i * 95)
.attr("cy", -80)
.attr("r", 16)
.style("fill", color(d.name))
.style("fill-opacity", ".6")
.on("mouseover", function(d) {
if (d.selected == true) {
d3.selectAll('#' + d.name).transition()
.style('stroke-width', '8px')
.style('stroke-opacity', '1')
}
d3.selectAll('#rect' + d.name)
.transition()
.style('x', 1150)
.style('fill-opacity', 1)
d3.select(this).transition(500).style('fill-opacity', '1');
d3.select('#desc' + d.name).transition().style('font-size', '13px');
d3.select('#legendtxt' + d.name).style('fill', color(d.name))
.style('font-size', '13px')
})
.on("mouseout", function(d) {
if (d.selected == false) {opac = '.2'}
else {
opac = '.6'
d3.selectAll('#' + d.name).transition().style('stroke-width', '3px')
.style('stroke-opacity', '.5');
}
d3.selectAll('#rect' + d.name)
.transition()
.style('x', 1100)
.transition().style('fill-opacity', .6)
d3.select(this).transition(200).style('fill-opacity', opac);
d3.selectAll('#desc' + d.name).transition().style('font-size', '0px');
d3.select('#legendtxt' + d.name).transition().style('fill', 'black')
.style('font-size', '11px')
})
// .on("click", function(d) {
//   if (d.selected == true) {
//     d3.selectAll('#desc' + d.name).style('font-size', '0px')
//     d3.selectAll('#' + d.name).transition().style("stroke-opacity", "0")
//     d3.select(this).style('fill-opacity', ".2").style("fill", 'grey')
//     d3.select('#' + 'legendtxt' + d.name).style('fill-opacity', ".2")
//     d3.select('#'+'hover'+d.name).style("stroke-width", "1px")
//     d.selected=false;
//   } else {
//     d3.selectAll('#desc' + d.name).transition().style('font-size', '12px')
//     d3.selectAll('#' + d.name)
//       .style('stroke-width', '0px')
//       .style('stroke-opacity', "1")
//       .transition().style("stroke-width", "16px")
//       .transition().style("stroke-width", "8px")

//       // .transition().style("stroke-width", "3px")
//       // .style('stroke-opacity', ".5")
//     d3.select(this).style('fill-opacity', ".6").style("fill", color(d.name))
//     d3.select('#' + 'legendtxt' + d.name).style('fill-opacity', '1')
//     d3.select('#'+'hover'+d.name).style("stroke-width", "20px")
//     d.selected=true
//   }
//   })
g.append("text")
.attr('x', 20 + i * 95)
.attr('y', -110)
.attr('id', 'legendtxt' + d.name)
.text(d.name).style('text-anchor', 'middle')
.style('font-size', '11')
.style('font-weight', '100')
g.append("text")
.attr('x', width/2).attr('y', -30)
.attr('id', function(d) {return 'desc' + d.name})
.text(score_descriptions[d.name])
.style("fill", color(d.name))
.style("font-size", 0)
.style("font-weight", '100')
.style("text-align", "center")
.style("text-anchor", "middle")
});

feature_values = []
d3.csv('user_summary.csv', function(error, data) {
if (error) throw error;
var profile = svg.append('g').attr('class', 'profile')
profile.selectAll('g').data(data)
.enter()
.append('g')
.each(function(d, i) {
var val = function() {
if (d.value < 0) {
return -(d.value * Math.abs(d.value * Math.pow(10, 31)))
} else {
return d.value * Math.abs(d.value * Math.pow(10, 31))
}
}
feature_values.push(val())
}).each(function(d, i) {
g = d3.select(this)
var start = -120  ;
g.append("rect")
.attr("id", 'rect' + d.feature)
.attr("width", 100)
.attr("height", 430*feature_values[i])
.attr('x', 1100)
.attr('y', function() {
if (i == 0) {return start}
else {return start+430*feature_values
.slice(0, i).reduce((a, b) => a + b, 0)}
})
.style("fill", color(d.feature))
.style("fill-opacity", .6)
.on("mouseover", function() {
d3.select('#LC' + d.feature).style('fill-opacity', '1');
d3.select('#desc' + d.feature).style('font-size', '13px');
d3.select('#legendtxt' + d.feature).style('fill', color(d.feature))
.style('font-size', '13px')
d3.select(this).style('fill-opacity', 1)
d3.selectAll('#' + d.feature)
.style('stroke-width', '8px')
.style('stroke-opacity', '1');
d3.selectAll('#rect' + d.feature)
.transition()
.style('fill-opacity', 1)
d3.selectAll('#' + 'side_text' + d.feature).style('fill', color(d.feature))

})
.on("mouseout", function(){
d3.select('#LC' + d.feature).style('fill-opacity', .6);
d3.selectAll('#desc' + d.feature).style('font-size', '0px');
d3.select('#legendtxt' + d.feature).style('fill', 'black')
.style('font-size', '11px')
d3.select(this).style('fill-opacity', .6)
d3.selectAll('#' + d.feature).style('stroke-width', '3px')
.style('stroke-opacity', '.5');
d3.selectAll('#rect' + d.feature)
.transition().style('fill-opacity', .6)
d3.selectAll('#' + 'side_text' + d.feature).style('fill', 'transparent')
})
});


});


g.append('text').attr('y', 500).attr('x', -30)
.style('font-size', 30).style('font-weight', 100)
.text('Of your most-listened tracks, here are the 5 most popular:')
// var color = d3.scale.category10();

// g.append('text').attr('y', -110).attr('x', 980)
//  .style('font-size', 30).style('font-weight', 100)
//  .text('Of your most-listened tracks,')

//  g.append('text').attr('y', -70).attr('x', 1110)
//  .style('font-size', 30).style('font-weight', 100)
//  .text('Here is your flavor')

//  g.append('text').attr('y', -30).attr('x', 1110)
//  .style('font-size', 30).style('font-weight', 100)
//  .text('profile')

g.append('text').attr('y', -80).attr('x', 1080)
.style('writing-mode', 'tb')
.style('font-size', 30).style('font-weight', 100)
.text(user + "'s Flavor Profile")




// var color = d3.scale.category10();
d3.csv('top5_clean2.csv', function(error, data) {
if (error) throw error;
console.log(data)
var color1 = d3.scale.category10();
color1.domain(global_cols)
var art = svg.append("g")
art.selectAll('image').data(data).enter().append('g')
.each(function(d, i) {
g.append('text')
.attr('id', 'text' + d.desc.split(' ').join(''))
.attr('x', -30).attr('y', 730)
.text(d.desc)
// .style('fill', color(d.max_feat))
.style('font-size', 0)
.style('font-weight', 100)
.style('font', "italic")
d3.selectAll('svg')
.append('image')
.attr('xlink:href', d.art)
.attr('class', 'pico')
.attr('height', 190)
.attr('width', 190)
.attr('y', 650)
.attr('x', 50 + i*200)
.attr('opacity', .2)
.on('mouseover', function() {
x = document.createElement("AUDIO");

if (x.canPlayType(d.prev)) {
x.setAttribute("src",d.prev);
} else {
x.setAttribute("src",d.prev);
}
x.play()
d3.select('#text' + d.desc.split(' ').join(''))
.transition().style('font-size', '30px')
d3.select(this).transition().style('opacity', 1)
d3.select('#' + d.max_feat)
.style('stroke-width', '8px')
.style('stroke-opacity', '1');
d3.select('#rect' + d.max_feat)
.style('x', 1150)
.transition()
.style('fill-opacity', 1)
d3.select('#' + 'side_text' + d.max_feat).style('fill', color1(d.max_feat))

})
.on('mouseout', function() {
x.pause()
d3.select('#text' + d.desc.split(' ').join(''))
.transition().style('font-size', 0)
d3.select(this).transition().style('opacity', .4)
d3.selectAll('#' + d.max_feat).style('stroke-width', '3px')
.style('stroke-opacity', '.5');
d3.selectAll('#rect' + d.max_feat)
.style('x', 1100)
.transition().style('fill-opacity', .6)
d3.selectAll('#' + 'side_text' + d.max_feat).style('fill', 'transparent')
});

var dataset = {
apples: [53245, 28479, 19697, 24037, 40245],
};

var width = 460,
height = 300,
radius = Math.min(width, height) / 2;

var color = d3.scale.category20();

var pie = d3.layout.pie()
.sort(null);

var arc = d3.svg.arc()
.innerRadius(radius - 100)
.outerRadius(radius - 50);

var svg = d3.select("body").append("svg")
.attr("width", width)
.attr("height", height)
.append("g")
.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

var path = svg.selectAll("path")
.data(pie(dataset.apples))
.enter().append("path")
.attr("fill", function(d, i) { return color(i); })
})
})


});
d3.select(self.frameElement).style("height", height + margin.top + margin.bottom + 100 + "px")
.style("width", width + margin.left + margin.right + 400+ "px");

d3.select("body").append('div')
d3.select("body").append('hi')

</script>
</body>
""")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port = PORT_NUMBER)




