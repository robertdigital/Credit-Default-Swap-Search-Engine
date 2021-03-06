from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, flash
from json2html import *
from werkzeug.utils import secure_filename
from flask_cors import CORS
from serve import model_api

import os
import pandas as pd
import glob
import subprocess
import csv
import json
import re

pd.set_option('display.max_colwidth', -1)
parent_dir = "../Data/"
filelist = []

UPLOAD_FOLDER = '../Uploads/files'
ALLOWED_EXTENSIONS = set(['txt', 'pdf'])


app = Flask(__name__,static_url_path='/static', static_folder='static', template_folder='templates')
app.secret_key = '1234'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def makefilelist(parent_dir):
    subject_dirs=[os.path.join(parent_dir, dir) for dir in os.listdir(
        parent_dir) if os.path.isdir(os.path.join(parent_dir, dir))]
    filelist=[]
    for dir in subject_dirs:
        csv_files=[os.path.join(dir, csv) for csv in os.listdir(
            dir) if os.path.isfile(os.path.join(dir, csv)) and csv.endswith('.csv')]
        for file in csv_files:
            filelist.append(file)
    return filelist


def createJsonOjectArray(filelist):
    makefilelist(parent_dir)
    json_array=[]
    for filename in filelist:
        json_data = []
        with open(filename, 'r+', encoding="utf-8") as csvfile:
            for row in csv.DictReader(csvfile):
                json_data=json.dumps(row)
                json_array.append(json_data)

    return json_array


def searchJsonArray(search_string):
    filelist=[]
    json_array=[]
    filelist=makefilelist(parent_dir)
    json_array=createJsonOjectArray(filelist)
    # search
    results=[elem for elem in json_array if search_string.lower()
               in elem.lower()]
    return results


def search_csv(search_string):
    csv_file = pd.read_csv('../UnifiedCSV/final_csv.csv',
                           dtype = str)
    list_columns = list(csv_file)
    num_columns = len(list(csv_file))
    results_rows = []
    csvreader_file = csv.reader(
        open('../UnifiedCSV/final_csv.csv', "r+", encoding="utf-8"), delimiter=",")
    for row in csvreader_file:
        for iterator in range(num_columns):
            if search_string in row[iterator]:
                results_rows.append(row)

    search_results = pd.DataFrame(
        results_rows, columns=list_columns, index=None)

    html_tags = search_results.to_html()
    return html_tags

def default_aggregate(search_string):
    csv_file = pd.read_csv('../UnifiedCSV/calculation.csv',
                           dtype = str)
    list_columns = list(csv_file)
    num_columns = len(list(csv_file))
    results_rows = []
    csvreader_file = csv.reader(
        open('../UnifiedCSV/calculation.csv', "r+", encoding="utf-8"), delimiter=",")
    for row in csvreader_file:
        for iterator in range(num_columns):
            if search_string in row[iterator]:
                results_rows.append(row)

    search_results = pd.DataFrame(
        results_rows, columns=list_columns, index=None)

    search_results['25% Recovery Rate'] = search_results['25% Recovery Rate'].replace(['#VALUE!'], '0')
    search_results['50% Recovery Rate'] = search_results['50% Recovery Rate'].replace(['#VALUE!'], '0')
    search_results['75% Recovery Rate'] = search_results['75% Recovery Rate'].replace(['#VALUE!'], '0')
    search_results['25% Recovery Rate'] = pd.to_numeric(search_results['25% Recovery Rate'])
    search_results['50% Recovery Rate'] = pd.to_numeric(search_results['50% Recovery Rate'])
    search_results['75% Recovery Rate'] = pd.to_numeric(search_results['75% Recovery Rate'])

    firstprobability = (sum(search_results['25% Recovery Rate'])/(search_results.shape[0] - search_results[search_results.Spread=='NaN'].shape[0])) + 30
    secondprobability = (sum(search_results['50% Recovery Rate'])/(search_results.shape[0] -  search_results[search_results.Spread=='NaN'].shape[0])) + 30
    thirdprobability = (sum(search_results['75% Recovery Rate'])/(search_results.shape[0] - search_results[search_results.Spread=='NaN'].shape[0])) + 30

    return firstprobability, secondprobability, thirdprobability


# Functions with URL routing
# Need to add consolidated view


@app.route("/")
def get_form():
    return render_template("index.html")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/raw_results", methods=['POST', 'GET'])
def printJsonResults():
    if 'button1' in request.form:
        tags = []
        if request.method == 'POST':
            search_string = request.form['input']
            results = searchJsonArray(search_string)
            for json_object in results:
                tags.append(json2html.convert(json=json_object,))
            return render_template('raw_result.html', results=tags)

    if 'button2' in request.form:
        if request.method == 'POST':
            search_string = request.form['input']
            result = search_csv(search_string)
            return render_template('unified_results.html', results=result)

    return '', 204


@app.route('/default', methods=['POST'])
def default():
    return render_template('default_view.html')

@app.route('/default_results', methods=['GET', 'POST'])
def default_processing():
    if request.method == 'POST':
        search_string = request.form['input']
        first, second, third = default_aggregate(search_string)

        return render_template('default_results.html', first=first, second=second, third=third, input=search_string)

@app.route('/ner', methods=['POST'])
def ner():
    return render_template('ner_front.html')


@app.route('/api', methods=['POST'])
def api():
    input_data = request.json
    output_data = model_api(input_data)
    response = jsonify(output_data)

    return response


@app.route('/redirect', methods=['POST'])
def upload():
    if request.method == 'POST':
        global filename
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return '', 204
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return '', 204

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            listOfFiles = []
            jsonObjects = [[]]
            finalResults = []
            filepath = "../Uploads/m_formatwithouttotal/"
            subprocess.call(['../Uploads/./duplicate.sh'])
            listOfFiles = makefilelist(filepath)
            jsonObjects = createJsonOjectArray(listOfFiles)
            for json_object in jsonObjects:
                finalResults.append(json2html.convert(json=json_object,))

            return render_template('upload_results.html', results=finalResults)

        return '', 204

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='80', debug=False)
