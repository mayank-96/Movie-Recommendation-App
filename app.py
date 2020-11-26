import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')
from scipy import spatial
import operator
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
from flask import Flask, render_template, request
import random

# MODEL

# Import data
data1 = pd.read_pickle('data1.pkl')
data2 = pd.read_pickle('data2.pkl')
movies = data1.append(data2)
poster = pd.read_pickle('poster.pkl')

result = pd.merge(movies, poster, how='left', on=['id'])
result['poster'] = result['poster'].fillna('https://www.themoviedb.org/assets/2/v4/glyphicons/basic/glyphicons-basic-38-picture-grey-c2ebdbb057f2a7614185931650f8cee23fa137b93812ccb132b9df511df1cfac.svg')
movies = result

# Similarity function
def Similarity(movieId1, movieId2):
    A = movies.iloc[movieId1]
    B = movies.iloc[movieId2]
    
    genresA = A['genres_bin']
    genresB = B['genres_bin']
    
    genreDistance = spatial.distance.cosine(genresA, genresB)
    
    castA = A['cast_bin']
    castB = B['cast_bin']
    
    castDistance = spatial.distance.cosine(castA, castB)
    
    directorA = A['director_bin']
    directorB = B['director_bin']
    
    directorDistance = spatial.distance.cosine(directorA, directorB)
    
    wordsA = A['words_bin']
    wordsB = B['words_bin']
    
    wordsDistance = spatial.distance.cosine(wordsA, wordsB)
    return genreDistance + castDistance + directorDistance + wordsDistance

# Recommendation function
def recommendation(name):
    new_movie = movies[movies['original_title'].str.contains(name)].iloc[0].to_frame().T
    # print('Selected Movie : ',new_movie.original_title.values[0])
    
    def getNeighbours(baseMovie, k):
        distances = []
        for index,movie in movies.iterrows():
            if(movie['new_id'] != baseMovie['new_id'].values[0]):
                dist = Similarity(baseMovie['new_id'].values[0], movie['new_id'])
                distances.append((movie['new_id'],dist))
                
        distances.sort(key=operator.itemgetter(1))
        neighbour=[]
        for x in range(k):
            neighbour.append(distances[x])
        return neighbour
    K = 20    
    neighbours = getNeighbours(new_movie,K)
    
    movie_name = []
    movie_id = []
    link = []
    # print('\nRecommended Movies: \n')
    for i in neighbours:
        # print( movies.iloc[i[0]][2]+" | Rating: "+str(movies.iloc[i[0]][7]))
        movie_id.append(movies.iloc[i[0]][0])
        movie_name.append(movies.iloc[i[0]][1])
        link.append(movies.iloc[i[0]]['poster'])
    return movie_id,movie_name,link

def highest_voted():
    movies['std_vote'] = (movies['vote_count'] / movies['vote_count'].max()) * movies['vote_average']
    df_vote = movies.sort_values(by=['std_vote']).tail(100).reset_index()
    randomlist = []
    k=0
    while k!=20:
        n = random.randint(0,99)
        if n not in randomlist: 
            randomlist.append(n)
            k+=1
    randomlist.sort()
    randomlist.reverse()
    
    movie_name = []
    movie_id = []
    link = []
    # print('\nHighest Voted Movies: \n')
    for i in randomlist:
        # print( df_vote.iloc[i][2]+" | Rating: "+str(df_vote.iloc[i][5]))
        movie_id.append(df_vote.iloc[i][1])
        movie_name.append(df_vote.iloc[i][2])
        link.append(df_vote.iloc[i]['poster'])
    return movie_id,movie_name,link

def most_popular():
    df_vote = movies.sort_values(by=['popularity']).tail(100).reset_index()
    randomlist = []
    k=0
    while k!=20:
        n = random.randint(0,99)
        if n not in randomlist: 
            randomlist.append(n)
            k+=1
    randomlist.sort()
    randomlist.reverse()
    
    movie_name = []
    movie_id = []
    link = []
    # print('\nMost Popular Movies: \n')
    for i in randomlist:
        # print( df_vote.iloc[i][2]+" | Rating: "+str(df_vote.iloc[i][5]))
        movie_id.append(df_vote.iloc[i][1])
        movie_name.append(df_vote.iloc[i][2])
        link.append(df_vote.iloc[i]['poster'])
    return movie_id,movie_name,link


def get_values(inputmovie):
    df = movies[movies['original_title'] == inputmovie]
    values = {}
    values['id'] = df['id'].iloc[0]
    values['title'] = inputmovie
    values['tagline'] = df['tagline'].iloc[0]
    values['date'] = df['release_date'].iloc[0]
    values['runtime'] = df['runtime'].iloc[0]
    genre = df['genres'].iloc[0]
    values['genre'] = ", ".join(genre)
    values['rating'] = int(df['vote_average'].iloc[0]*10)
    values['degree'] = (values['rating']*180)/100
    values['overview'] = df['overview'].iloc[0]
    cast = df['cast_list'].iloc[0]
    res = cast.strip('][').split(', ') 
    cast=[]
    for i in range(5):
        cast.append(res[i][1:-1])
    values['cast'] = ", ".join(cast)
    values['link'] = df['poster'].iloc[0]
    return values

# FLASK APP

def get_suggestions():
    return list(movies['original_title'])

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip
@app.route("/")
@app.route("/home")
def home():
    suggestions = get_suggestions()
    return render_template('home.html',suggestions=suggestions)

@app.route("/rated")
def rated():
    recc_id , recc_name , link = highest_voted()
    return render_template("rated.html",movie=recc_name,link=link)

@app.route("/popular")
def popular():
    recc_id , recc_name , link = most_popular()
    return render_template("popular.html",movie=recc_name,link=link)

@app.route('/result/<mname>')
def convertersexample(mname):
        recc_id , recc_name , link = recommendation(mname)
        values2=get_values(mname)
        return render_template("result.html",movie=recc_name,link=link,values=values2)


@app.route('/result',methods = ['POST', 'GET'])
def result():
    if request.method == 'POST':

        # Input
        inputmovie = request.form['myMovie']
        movies_list=movies['original_title'].tolist()

        if inputmovie in movies_list:
            # Model
            values = get_values(inputmovie)
            recc_id , recc_name , link = recommendation(inputmovie)
            dis_name  = []
            for i in range(20):
                if len(recc_name[i])>25:
                    temp = recc_name[i][:22] + "..."
                    dis_name.append(temp)
                else:
                    dis_name.append(recc_name[i])
        
            return render_template("result.html",movie=recc_name,link=link,values=values)
        else:
            return render_template("sorry.html")

if __name__ == '__main__':
    app.run(debug=True)