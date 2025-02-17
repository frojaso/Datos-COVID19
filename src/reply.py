# by MinCiencia, based in https://realpython.com/twitter-bot-python-tweepy/#the-reply-to-mentions-bot

import tweepy
import logging
from config_bot import create_api
import time
import pandas as pd
import os
import numpy as np
import requests
import io
import re
import utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def check_mentions(api, keywords, since_id):
    logger.info("Retrieving mentions")
    new_since_id = since_id
    my_files = {
        'activos':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto19/CasosActivosPorComuna.csv',
        'activos_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto19/CasosActivosPorComuna_T.csv',
        'vacunacion':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_1eraDosis.csv',
        'vacunacion1_comuna_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_1eraDosis_T.csv',
        'vacunacion2_comuna_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_2daDosis_T.csv',
        'poblacion_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/poblacion_comuna_edad_T.csv',
        'vacunacion1_dosis_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto80/vacunacion_comuna_1eraDosis_T.csv',
        'vacunacion2_dosis_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto80/vacunacion_comuna_2daDosis_T.csv',
    }
    for tweet in tweepy.Cursor(api.mentions_timeline,since_id=since_id).items():
        new_since_id = max(tweet.id, new_since_id)
        if tweet.in_reply_to_status_id is not None:
            continue
        texto = tweet.text.lower()
        texto = texto.replace('ñ', 'n')
        texto = texto.replace('á', 'a')
        texto = texto.replace('é', 'e')
        texto = texto.replace('í', 'i')
        texto = texto.replace('ó', 'o')
        texto = texto.replace('ú', 'u')
        texto = texto.replace('ü', 'u')
        texto = texto.replace('?', '')
        texto = texto.replace('¿', '')
        if any(keyword in texto for keyword in keywords):
            comuna = texto.replace('@min_ciencia_ia ', '')
            if comuna in keywords:
                logger.info(f"Answering to {tweet.user.name}")
                #casos activos
                content = requests.get(my_files['activos']).content
                df = pd.read_csv(io.StringIO(content.decode('utf-8')))

                content = requests.get(my_files['activos_t']).content
                dfT = pd.read_csv(io.StringIO(content.decode('utf-8')))

                df["Comuna"] = df["Comuna"].str.lower()
                n = df.index[df['Comuna'] == comuna]
                casos_ultimo_informe = int(pd.to_numeric(dfT.iloc[dfT.index.max()][n + 1]))
                casos_informe_anterior = int(pd.to_numeric(dfT.iloc[dfT.index.max() - 1][n + 1]))
                variacion = casos_ultimo_informe - casos_informe_anterior
                fecha = dfT.iloc[dfT.index.max()][0]

                #vacunación
                content = requests.get(my_files['vacunacion']).content
                dfve1 = pd.read_csv(io.StringIO(content.decode('utf-8')))

                content = requests.get(my_files['vacunacion1_comuna_t']).content
                dfve1_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                content = requests.get(my_files['vacunacion2_comuna_t']).content
                dfve2_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                content = requests.get(my_files['poblacion_t']).content
                dfvep_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                content = requests.get(my_files['vacunacion1_dosis_t']).content
                dfv1_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                content = requests.get(my_files['vacunacion2_dosis_t']).content
                dfv2_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                dfve1["Comuna"] = dfve1["Comuna"].str.lower()
                n = dfve1.index[dfve1['Comuna'] == comuna]

                #total poblacion objetivo de la comuna
                dfvep_T = dfvep_T[5:][n + 1]
                dfvep_T = dfvep_T.astype(float)
                tot = int(dfvep_T.sum())

                # Porcentaje 1era dosis
                dfve1_T = dfve1_T[5:][n + 1]
                dfve1_T = dfve1_T.astype(float)
                v1 = int(dfve1_T.sum())
                porcentaje1 = str(round(100*v1/tot))

                # Porcentaje 2da dosis
                dfve2_T = dfve2_T[5:][n + 1]
                dfve2_T = dfve2_T.astype(float)
                v2 = int(dfve2_T.sum())
                porcentaje2 = str(round(100 * v2 / tot))

                # Rolling mean last week
                dfv1_T = dfv1_T[5:][n + 1]
                dfv2_T = dfv2_T[5:][n + 1]
                dfv1_T = dfv1_T.astype(float)
                dfv2_T = dfv2_T.astype(float)
                dft = dfv1_T + dfv2_T
                dft.reset_index(drop=True, inplace=True)
                dft = dft.rolling(7).mean().round(4)
                promedio = str(int(dft.iloc[dft.index.max() - 1][n + 1]))


                if variacion > 0:
                    reply = "🤖Hola @" + tweet.user.screen_name + ". En " + comuna + " los casos activos de Covid19 son " + str(casos_ultimo_informe) + " según mis registros en base al último informe epidemiológico del @ministeriosalud (" + fecha + "), " + str(variacion) + " más que en el informe anterior."
                    reply2 = "🤖Además, acorde a la información de la campaña #YoMeVacuno ✌️, un " + porcentaje1 + "% de la población objetivo tiene su primera dosis, y un " + porcentaje2 + "% tiene ambas dosis. Un promedio diario de " + promedio + " personas han recibido su vacuna en " + comuna + " esta semana 🦾."
                    update = api.update_status(status=reply, in_reply_to_status_id=tweet.id)
                    api.update_status(status=reply2, in_reply_to_status_id=update.id)
                else:
                    reply = "🤖Hola @" + tweet.user.screen_name + ". En " + comuna + " los casos activos de Covid19 son " + str(casos_ultimo_informe) + " según mis registros en base al último informe epidemiológico del @ministeriosalud (" + fecha + "), " + str((-1) * variacion) + " menos que en el informe anterior."
                    reply2 = "🤖Además, acorde a la información de la campaña #YoMeVacuno ✌️, un " + porcentaje1 + "% de la población objetivo tiene su primera dosis, y un " + porcentaje2 + "% tiene ambas dosis. Un promedio diario de " + promedio + " personas han recibido su vacuna en " + comuna + " esta semana 🦾."
                    update = api.update_status(status=reply, in_reply_to_status_id=tweet.id)
                    api.update_status(status=reply2, in_reply_to_status_id=update.id)

            else:
                for word in texto.lower().split():
                    if word in keywords:
                        logger.info(f"Answering to {tweet.user.name}")
                        #vacunacion
                        content = requests.get(my_files['vacunacion']).content
                        dfve1 = pd.read_csv(io.StringIO(content.decode('utf-8')))

                        content = requests.get(my_files['vacunacion1_comuna_t']).content
                        dfve1_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                        content = requests.get(my_files['vacunacion2_comuna_t']).content
                        dfve2_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                        content = requests.get(my_files['poblacion_t']).content
                        dfvep_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                        content = requests.get(my_files['vacunacion1_dosis_t']).content
                        dfv1_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                        content = requests.get(my_files['vacunacion2_dosis_t']).content
                        dfv2_T = pd.read_csv(io.StringIO(content.decode('utf-8')), header=None)

                        dfve1["Comuna"] = dfve1["Comuna"].str.lower()
                        n = dfve1.index[dfve1['Comuna'] == word]

                        # total poblacion objetivo de la comuna
                        dfvep_T = dfvep_T[5:][n + 1]
                        dfvep_T = dfvep_T.astype(float)
                        tot = int(dfvep_T.sum())

                        # Porcentaje 1era dosis
                        dfve1_T = dfve1_T[5:][n + 1]
                        dfve1_T = dfve1_T.astype(float)
                        v1 = int(dfve1_T.sum())
                        porcentaje1 = str(round(100 * v1 / tot))

                        # Porcentaje 2da dosis
                        dfve2_T = dfve2_T[5:][n + 1]
                        dfve2_T = dfve2_T.astype(float)
                        v2 = int(dfve2_T.sum())
                        porcentaje2 = str(round(100 * v2 / tot))

                        # Rolling mean last week
                        dfv1_T = dfv1_T[5:][n + 1]
                        dfv2_T = dfv2_T[5:][n + 1]
                        dfv1_T = dfv1_T.astype(float)
                        dfv2_T = dfv2_T.astype(float)
                        dft = dfv1_T + dfv2_T
                        dft.reset_index(drop=True, inplace=True)
                        dft = dft.rolling(7).mean().round(4)
                        promedio = str(int(dft.iloc[dft.index.max() - 1][n + 1]))

                        #casos activos

                        content = requests.get(my_files['activos']).content
                        df = pd.read_csv(io.StringIO(content.decode('utf-8')))

                        content = requests.get(my_files['activos_t']).content
                        dfT = pd.read_csv(io.StringIO(content.decode('utf-8')))

                        df["Comuna"] = df["Comuna"].str.lower()
                        n = df.index[df['Comuna'] == word]
                        casos_ultimo_informe = int(pd.to_numeric(dfT.iloc[dfT.index.max()][n + 1]))
                        casos_informe_anterior = int(pd.to_numeric(dfT.iloc[dfT.index.max()-1][n + 1]))
                        variacion = casos_ultimo_informe - casos_informe_anterior
                        fecha = dfT.iloc[dfT.index.max()][0]
                        if variacion > 0:
                            reply = "🤖Hola @" + tweet.user.screen_name + ". En " + word + " los casos activos de Covid19 son " + str(casos_ultimo_informe) + " según mis registros en base al último informe epidemiológico del @ministeriosalud (" + fecha + "), " + str(variacion) + " más que en el informe anterior."
                            reply2 = "🤖Además, acorde a la información de la campaña #YoMeVacuno ✌️, un " + porcentaje1 + "% de la población objetivo tiene su primera dosis, y un " + porcentaje2 + "% tiene ambas dosis. Un promedio diario de " + promedio + " personas han recibido su vacuna en " + word + " esta semana 🦾."
                            update = api.update_status(status=reply, in_reply_to_status_id=tweet.id)
                            api.update_status(status=reply2, in_reply_to_status_id=update.id)

                        else:
                            reply = "🤖Hola @" + tweet.user.screen_name + ". En " + word + " los casos activos de Covid19 son " + str(casos_ultimo_informe) + " según mis registros en base al último informe epidemiológico del @ministeriosalud (" + fecha + "), " + str((-1) * variacion) + " menos que en el informe anterior."
                            reply2 = "🤖Además, acorde a la información de la campaña #YoMeVacuno ✌️, un " + porcentaje1 + "% de la población objetivo tiene su primera dosis, y un " + porcentaje2 + "% tiene ambas dosis. Un promedio diario de " + promedio + " personas han recibido su vacuna en " + word + " esta semana 🦾."
                            update = api.update_status(status=reply, in_reply_to_status_id=tweet.id)
                            api.update_status(status=reply2, in_reply_to_status_id=update.id)

    return new_since_id

def main(a,b,c,d):
    api = create_api(a,b,c,d)
    since_id = 1380576552883265537
    my_files = {
        'activos':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto19/CasosActivosPorComuna.csv',
        'activos_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto19/CasosActivosPorComuna_T.csv',
        'vacunacion':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_1eraDosis.csv',
        'vacunacion1_comuna_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_1eraDosis_T.csv',
        'vacunacion2_comuna_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/vacunacion_comuna_edad_2daDosis_T.csv',
        'poblacion_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto81/poblacion_comuna_edad_T.csv',
        'vacunacion1_dosis_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto80/vacunacion_comuna_1eraDosis_T.csv',
        'vacunacion2_dosis_t':
            'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/output/producto80/vacunacion_comuna_2daDosis_T.csv',
    }
    content = requests.get(my_files['activos']).content
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    df.dropna(subset=['Codigo comuna'], inplace=True)
    keywords = df.Comuna.unique()
    a = np.array([x.lower() if isinstance(x, str) else x for x in keywords])
    keywords = a.tolist()
    while True:
        since_id = check_mentions(api, keywords, since_id)
        logger.info("Waiting...")
        time.sleep(60)

if __name__ == "__main__":
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
    main(consumer_key,consumer_secret,access_token,access_token_secret)