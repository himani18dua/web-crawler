from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import os
import subprocess


app=Flask(__name__)
CORS(app) 
@app.route('/img-members', methods=['GET'])
def img_members():
    file_path = os.path.join('output_directory', 'images_without_alt.json')
    with open(file_path, 'r') as f:
        images_without_alt = json.load(f)
    return jsonify(images_without_alt)

@app.route("/members", methods=['GET'])

def members():
    
    print('hello')
    file_path = os.path.join('output_directory', 'broken_links.json')
    print(file_path)

    with open(file_path, 'r') as f:
        broken_links = json.load(f)

    return broken_links
@app.route('/crawl',methods=['POST'])

def crawl():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL is required"}), 400

       

# output_dir = './flask-server/myproject/output_directory'
        script_directory = 'myproject/myproject/spiders'

        script_name = 'crawler.py'


        script_path = f'{script_directory}/{script_name}'
        command=['scrapy','runspider',script_path,'-a', f'url={url}']
        print("Command:", command)
        subprocess.run(command,text=True)
        return jsonify({"message": "Crawling started"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    output_file = 'myproject/output_directory/broken_links.json'

@app.route('/img-crawl',methods=['POST'])

def imgcrawl():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "URL is required"}), 400

       

# output_dir = './flask-server/myproject/output_directory'
        script_directory = 'myproject/myproject/spiders'

        script_name = 'img-crawler.py'


        script_path = f'{script_directory}/{script_name}'
        command=['scrapy','runspider',script_path,'-a', f'url={url}']
        print("Command:", command)
        subprocess.run(command,text=True)
        return jsonify({"message": "Crawling started"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    output_file = 'myproject/output_directory/broken_links.json'   

@app.route('/img-download')
def download():
    json_path = 'output_directory/images_without_alt.json'
    pdf_path = 'output_directory/images_without_alt.pdf'

    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Create a PDF
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    text = c.beginText(40, height - 40)
    text.setFont("Helvetica", 10)

    # Convert JSON data to text
    json_str = json.dumps(data, indent=4)
    lines = json_str.split('\n')

    # Add text to PDF
    for line in lines:
        text.textLine(line)

    c.drawText(text)
    c.save()

    # Send the PDF file as a response
    return send_file(pdf_path, as_attachment=True)   
    
   

@app.route('/download')
def download_file():
    # file_path = os.path.join('output_directory', 'broken_links.json')
    # if os.path.exists(file_path):
    #     return send_file(file_path, as_attachment=True)
    # else:
    #     return 'File not found', 404
    json_path = 'output_directory/broken_links.json'
    pdf_path = 'output_directory/broken_links.pdf'

    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Create a PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    text = c.beginText(40, height - 40)
    text.setFont("Helvetica", 10)

    # Convert JSON data to text
    json_str = json.dumps(data, indent=4)
    lines = json_str.split('\n')

    # Add text to PDF
    for line in lines:
        text.textLine(line)

    c.drawText(text)
    c.save()

    # Send the PDF file as a response
    return send_file(pdf_path, as_attachment=True)

if __name__=="__main__":
    app.run(host='0.0.0.0')