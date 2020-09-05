from flask import Flask, request
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask_mysqldb import MySQL

from data import *

app = Flask(__name__)

# Mysql connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'fisi_calidad'

# settings
app.secret_key = 'mysecretkey'

mysql = MySQL(app)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/')
def index():
    return 'API BACKEND - CALIDAD DE SERVICIO FISI'

# RESPUESTAS - ALUMNOS
@app.route('/traer_data')
def traer_data_bd():
    print("TRAER_DATA_BD")

    registros, diccionario_preguntas = traer_data()

    try:
        #verificar el número de alumnos en la BD, 
        cur = mysql.connection.cursor()
        script_select = "SELECT COUNT(*) FROM alumno"
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuesta  =  cur.fetchone()

        cantidad_alumnos_bd = respuesta[0]
        print("Cantidad de alumnos en la bd:",cantidad_alumnos_bd)

        print("Cantidad de registros: ",len(registros))

        # cantidad_alumnos_bd = 6 # prueba
        nuevo_inicio = cantidad_alumnos_bd
        print("nuevo_inicio: ",nuevo_inicio)
        if nuevo_inicio<0:
            nuevo_inicio=0

        registros_mod = registros[nuevo_inicio:]
        print("registros a ingresar: ",len(registros_mod))

        if len(registros_mod)==0:
            print("No se han ingresado nuevos registros, no hay nuevos registros a insertar")
            return {
                "mensaje":"No se han ingresado nuevos registros, no hay nuevos registros a insertar",
                "status":200
            }

        for registro in registros_mod:
            # print(registro)
            print("*****REGISTRO*****")
            print("***ALUMNO***")

            # PRIMERO insertamos un alumno
            id_registro=0
            if registro['Escuela']=='Escuela de Ingeniería de Sistemas':
                id_registro=1
            else:
                id_registro=2

            cur = mysql.connection.cursor()
            script_insert ='INSERT INTO alumno (sexo,anio_ingreso,id_escuela) VALUES ("{}","{}",{})'.format(
                registro['Género'][0],
                registro['Año de ingreso'],
                id_registro
            )
            print('script_insert: ',script_insert)
            cur.execute(script_insert)
            mysql.connection.commit()

            #SEGUNDO obtenemos el id del alumno que insertamos
            cur = mysql.connection.cursor()
            script_select = "SELECT MAX(id_alumno) from alumno"
            print("script_select: ",script_select)
            
            cur.execute(script_select)
            alumno  =  cur.fetchone()
            # id_alumno=0 #prueba
            id_alumno=alumno[0]
            print("id_alumno: ",id_alumno)

            print("***RESPUESTA***")

            for num_p in diccionario_preguntas.keys():
                # print(num_p,registro[num_p])
                cur = mysql.connection.cursor()
                script_insert_pregunta = "INSERT INTO respuesta (respuesta,id_pregunta,id_alumno) VALUES ('{}',{},{})".format(
                    registro[num_p],
                    num_p,
                    id_alumno
                )

                print("script_insert_pregunta: ",script_insert_pregunta)
                cur.execute(script_insert_pregunta)
                mysql.connection.commit()

        response = {
            "respuesta": "Se actualizó satisfactoriamente la base de datos con las respuestas",
            "status":200
        }
    except Exception as e:
        print(e)
        response={
            "respuesta":"Error",
            "status":500
        }
    return response

@app.route('/alumnos')
def encuestados():
    print("TRAER_RESPUESTA_POR_DIMENSION")

    try:

        # NUMERO DE ENCUESTADOS
        cur = mysql.connection.cursor()
        script_select = "SELECT COUNT(*) FROM alumno;"
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuesta =  cur.fetchone()
        print(respuesta)
        cantidad_encuestados = respuesta[0]
        
        # NUMERO DE ENCUESTADOS POR SEXO
        script_select = "SELECT sexo,COUNT(*) FROM alumno GROUP BY sexo;"
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuesta_2 =  cur.fetchall()

        lista_encuestados_sexo=[]
        for reg in respuesta_2:
            encuestados_sexo = {"sexo":reg[0],"encuestados":reg[1]}
            lista_encuestados_sexo.append(encuestados_sexo)
        print(respuesta_2)

        # NUMERO DE ENCUESTADOS POR AÑO DE INGRESO
        script_select = "SELECT anio_ingreso,COUNT(*) FROM alumno GROUP BY anio_ingreso;"
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuesta_3 =  cur.fetchall()

        lista_encuestados_anio=[]
        for reg in respuesta_3:
            encuestados_anio = {"año":reg[0],"encuestados":reg[1]}
            lista_encuestados_anio.append(encuestados_anio)
        print(respuesta_3)

        response = {
            "respuesta": {
                "cantidad encuestados":cantidad_encuestados,
                "encuestados por sexo":lista_encuestados_sexo,
                "encuestados por anio":lista_encuestados_anio,
            },
            "status":200
        }

    except Exception as e:
        print(e)
        response={
            "respuesta":"Error",
            "status":500
        }
    return response

@app.route('/dimension')
def resultados_dimensiones():
    print("TRAER_RESULTADOS_POR_DIMENSIONES")

    try:
        cur = mysql.connection.cursor()
        script_select = '''SELECT d.nombre, r.respuesta, COUNT(*)
FROM pregunta P
JOIN dimension d ON p.id_dimension = d.id_dimension
JOIN respuesta r ON r.id_pregunta = p.id_pregunta
GROUP BY d.nombre, r.respuesta;
        '''
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuestas  =  cur.fetchall()

        #parseamos las respuestas

        df_dimensiones = pd.DataFrame(respuestas, columns=['dimensión','opción','respuestas'])
        df_respuestas = df_dimensiones.groupby(['dimensión','opción'])['respuestas'].mean().unstack(1)
        resultado = df_respuestas.to_dict(orient='index')

        print(resultado)
        response = {
            "respuesta": resultado,
            "status":200
        }

    except Exception as e:
        print(e)
        response={
            "respuesta":"Error",
            "status":500
        }
    return response

@app.route('/respuesta')
def obtener_respuestas():
    print("TRAER_RESPUESTAS")

    try:
        cur = mysql.connection.cursor()
        script_select = '''
SELECT d.nombre, p.descripcion, r.respuesta, COUNT(*)
FROM dimension d
JOIN pregunta p ON d.id_dimension = p.id_dimension
JOIN respuesta r ON p.id_pregunta = r.id_pregunta
GROUP BY d.nombre, p.descripcion, r.respuesta;
        '''
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuestas  =  cur.fetchall()
        print(respuestas)

        #parseamos las respuestas

        df_res =  pd.DataFrame(respuestas,columns=['dimensión','pregunta','opción','respuestas'])
        dimensiones = list(df_res['dimensión'].unique())
        df_res_final = df_res.pivot_table(values='respuestas',index=['dimensión','pregunta'],columns=['opción']).fillna(0)


        diccionario = {}
        for dim in dimensiones:
            tmp = df_res_final.loc[dim].to_dict('index')
            # lista_preguntas=[]
            diccionario_preguntas={}
            for k,v in tmp.items():
                num = k[:2]
                if num.isnumeric():
                    num = int(num)
                else:
                    num = int(num[0])
                diccionario_preguntas[num] = {"pregunta":k,"resultados":v}
                # lista_preguntas.append({"pregunta":k,"resultados":v})
            diccionario[dim] = diccionario_preguntas

        print(diccionario)
        response = {
            "respuesta": diccionario,
            "status":200
        }

    except Exception as e:
        print(e)
        response={
            "respuesta":"Error",
            "status":500
        }
    return response

@app.route('/respuesta/<id>')
def obtener_respuestas_dimension(id):
    print("TRAER_RESPUESTAS_DIMENSION")

    try:
        cur = mysql.connection.cursor()
        script_select = '''
SELECT d.nombre, p.descripcion, r.respuesta, COUNT(*)
FROM dimension d
JOIN pregunta p ON d.id_dimension = p.id_dimension
JOIN respuesta r ON p.id_pregunta = r.id_pregunta
WHERE d.id_dimension = 1
GROUP BY d.nombre, p.descripcion, r.respuesta;
        '''
        print("script_select: ",script_select)
        cur.execute(script_select)
        respuestas  =  cur.fetchall()
        print(respuestas)

        #parseamos las respuestas

        df_res =  pd.DataFrame(respuestas,columns=['dimensión','pregunta','opción','respuestas'])
        dimensiones = list(df_res['dimensión'].unique())
        dimension = dimensiones[0]
        df_res_final = df_res.pivot_table(values='respuestas',index=['dimensión','pregunta'],columns=['opción']).fillna(0)


        diccionario = {}
        for dim in dimensiones:
            tmp = df_res_final.loc[dim].to_dict('index')
            # lista_preguntas=[]
            diccionario_preguntas={}
            for k,v in tmp.items():
                num = k[:2]
                if num.isnumeric():
                    num = int(num)
                else:
                    num = int(num[0])
                diccionario_preguntas[num] = {"pregunta":k,"resultados":v}
                # lista_preguntas.append({"pregunta":k,"resultados":v})
            diccionario[dim] = diccionario_preguntas

        print(diccionario)
        response = {
            "respuesta": diccionario,
            "status":200
        }

    except Exception as e:
        print(e)
        response={
            "respuesta":"Error",
            "status":500
        }
    return response
# FIN RESPUESTAS - ALUMNOS

# PREGUNTAS
@app.route('/pregunta',methods=['POST'])
def agregar_pregunta():
    if request.method == 'POST':
        print("AGREGAR_PREGUNTA")
        descripcion = request.form['descripcion']
        id_dimension = request.form['id_dimension']

        try:
            cur = mysql.connection.cursor()
            script_insert ='INSERT INTO pregunta (descripcion,id_dimension) VALUES ("{}",{})'.format(
                descripcion,
                id_dimension
            )
            print('script_insert: ',script_insert)

            cur.execute(script_insert)
            mysql.connection.commit()

            response = {
                "respuesta":"Se agregó satisfactoriamente la pregunta",
                "status":200,
                "pregunta":{
                    "descripcion":descripcion,
                    "id_dimension":id_dimension
                }
            }
        except Exception as e:
            print(e)
            response = {
                "respuesta":"Error",
                "status":500
            }
        return response

@app.route('/pregunta')
def obtener_preguntas():
    print("OBTENER_PREGUNTAS")
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM pregunta')
    preguntas_obt  =  cur.fetchall()
    preguntas_resp = []
    for pregunta in preguntas_obt:
        pregunta_dict = {"id_pregunta":pregunta[0], "descripcion":pregunta[1], "id_dimension":pregunta[2]}
        preguntas_resp.append(pregunta_dict)

    return jsonify({'preguntas':preguntas_resp})

@app.route('/pregunta/<id>')
def obtener_pregunta(id):
    print("OBTENER_PREGUNTA")
    cur = mysql.connection.cursor()
    script_select="SELECT * FROM pregunta WHERE id_pregunta={}".format(id)
    cur.execute(script_select)
    pregunta = cur.fetchone()
    print(pregunta)
    if pregunta:
        response = {
            "pregunta":{
                "id_pregunta":pregunta[0],
                "descripcion":pregunta[1],
                "id_dimension":pregunta[2]
                }
        }
    else:
        response = {
            "mensaje":"No se encontró la pregunta con el id_pregunta: {}".format(id)
        }
    return jsonify(response)

@app.route('/pregunta/<id>',methods=['POST'])
def editar_pregunta(id):
    if request.method == 'POST':
        print("EDITAR_PREGUNTA")
        descripcion = request.form['descripcion']
        id_dimension = request.form['id_dimension']

        cur = mysql.connection.cursor()
        script_select = 'SELECT * FROM pregunta WHERE id_pregunta = {}'.format(id)
        print("script_select: ",script_select)
        cur.execute(script_select)
        pregunta = cur.fetchone()
        if not pregunta :
            return jsonify({"mensaje":"Pregunta no encontrada"})
        else:
            try:
                cur = mysql.connection.cursor()
                script_update = "UPDATE pregunta SET descripcion= '{}', id_dimension={} WHERE id_pregunta = {}".format(
                    descripcion,
                    id_dimension,
                    id
                )
                print("script_update: ",script_update)
                cur.execute(script_update)
                mysql.connection.commit()
                return jsonify({"mensaje": "Pregunta actualizada satisfactoriamente"})
            except Exception as e:
                print(e)
                return jsonify({"mensaje": "Algo salió mal"})
# FIN PREGUNTAS

if __name__ == '__main__':
    app.run(debug=True,port=5000)