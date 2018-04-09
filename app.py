# coding: utf-8
import hashlib
import json
import os
import random
import re
import string
import sys
import time
from io import BytesIO
from threading import Thread

import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from lxml import html
from PIL import Image

from countrycodes import country_codes

# reload(sys)
# sys.setdefaultencoding("utf-8")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:root@localhost/lhwApi')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Create our database model
class Station(db.Model):
    """
        Station table
    """
    __tablename__ = "stations"
    id = db.Column(db.Integer, primary_key=True)
    jobId = db.Column(db.String(120), unique=True)
    jobUrl = db.Column(db.Text)
    jobStatus = db.Column(db.Integer) # 0: PENDING,  1: SUCCESSS, -1: FAILED
    jobResult = db.Column(db.Text)    # JSON STRING
    jobProcess = db.Column(db.Integer)    # JSON STRING


db.create_all()

# Set "homepage" to index.html
@app.route('/')
def index():
    return "API"

# Save e-mail to database and send to success page
@app.route('/create', methods=['POST'])
def create():
    # return "Create"
    url = None
    if request.method == 'POST':
        url = request.form['url']
        # Check that email does not already exist (not a great query, but works)
        station = db.session.query(Station).filter(Station.jobUrl == url)
        if not station.count():
            job_id = hashlib.md5(url).hexdigest()

            with app.app_context():
                thr = Thread(target=scrape, args=[app,db,url])
                thr.daemon = True
                thr.start()

            station = Station(jobId=job_id, jobUrl=url, jobStatus=0, jobResult="", jobProcess=0)
            db.session.add(station)
            db.session.commit()
            return jsonify({"status": "new", "id": job_id, "is_exist": 0, "job_status":0 })
        else:
            job_id = station.first().jobId
            status = station.first().jobStatus
            if status == 0:
                return jsonify({"status": "exist", "id": job_id, "is_exist": 1, "job_status": status})
            elif status == -1:
                job_id = station.first().jobId
                with app.app_context():
                    thr = Thread(target=scrape, args=[app, db, url])
                    thr.daemon = True
                    thr.start()
                station.first().jobStatus  = 0
                station.first().jobProcess = 0
                db.session.commit()

                return jsonify({"status": "restart", "id": job_id, "is_exist": 1, "job_status": status})

@app.route('/result/<job_id>', methods=['GET'])
def result(job_id):
    station = db.session.query(Station).filter(Station.jobId == job_id)
    if not station.count():
        return jsonify({"failed": "error", "id": job_id, "result": ""})
    else:
        status = station.first().jobStatus
        url = station.first().jobUrl
        result = station.first().jobResult
        pros = station.first().jobProcess
        if status == 0:
            return jsonify({"status":"pending", "id":job_id, "url":url, "result":"", "process": pros})
        elif status == 1:
            return jsonify({"status":"success", "id":job_id, "url":url, "result":json.loads(result),"process": 100})
        elif status == -1:
            return jsonify({"status": "failed", "id": job_id, "url": url, "result": "", "process": 0})

def scrape(app, db, url):
    print ("Starting....")
    time.sleep(3)
    try:
        headers = {
            'Pragma': 'no-cache',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }

        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 5
        db.session.commit()
        sys.stdout.write("\rProcess: 5%")
        sys.stdout.flush()

        response = requests.get(url, headers=headers)

        tree = html.fromstring(response.text)
        prop_id = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(10)])
        address = tree.xpath("//div[@class='contactinfo']/p[1]/text()")[0]
        # correct_address = geocoder.google(address)
        # print (correct_address.address)

        name = tree.xpath("//div[@class='hotelheader']/h1/span/text()")[0].split(",")[-2].strip()
        # name = correct_address.city # city
        # print (name)

        country = get_country_code(address) # country
        title = tree.xpath("//div[@class='hotelheader']/h1/text()")[0].strip() # title

        # images = tree.xpath("//div[@class='hotelheader']/h1/text()")[0]
        # print (images)
        
        services = []

        latitude = re.search("mapLat=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()      # Latitude
        longitude = re.search("mapLong=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()    # Longitude
        
        geo_point = {
            "latitude": float(latitude),
            "longitude": float(longitude)
        }
        variants = []

        hotelGalleryJsonId = re.search("var hotelGalleryJson = galleryJson\[\"(.*?)\"\]\;", response.text, re.S|re.M|re.I).group(1).strip()
        hotelGalleryJson = json.loads(re.search("var galleryJson = (.*?)\;", response.text, re.S|re.M|re.I).group(1).strip())

        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 10
        db.session.commit()

        sys.stdout.write("\rProcess: 5%")
        sys.stdout.flush()

        variants_count  = len(tree.xpath('//div[@class="roomitem"]'))
        iii = 0
        for variant in tree.xpath('//div[@class="roomitem"]'):
            iii += 1
            variant_title = variant.xpath('p/text()')[0].strip()
            variant_size = re.search("(\d+[\s]?|\d+[\s]?\-\d+[\s]?)sq[\s]?f", variant.xpath('img[contains(@class, "roompic")]/@alt')[0].lower(), re.S | re.M).group(1).strip()
            variant_desc = variant_title
            variant_img_id = re.search("(\w+\-\w+\-\w+\-\w+\-\w+)", variant.xpath('.//a[@class="gallerylaunch"]/@onclick')[0], re.S | re.M).group(1)
            variant_url = "https://www.lhw.com/hotel/" + variant.xpath('.//a[@class="btn btn-2"]/@href')[0].split(",")[0]
            resp = requests.get(variant_url, headers=headers)
            tree_room = html.fromstring(resp.text)
            long_desc = tree_room.xpath('//div[@id="selected-room"]//span[@class="feat"]/text()')[0].strip()
            images = []
            
            for img_name in hotelGalleryJson[variant_img_id]:
                img_url = "https:" + img_name["Url"]
                img_ext = img_url.split(".")[-1]
                img_url = img_url.replace(".{}".format(img_ext), "_790x490.{}".format(img_ext))
                filename = img_url.split("/")[-1]
                img_resp = get_response(img_url)
                img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(img_resp)
                img_border_color = get_border_color_of_image(img_resp.content)
                img_average_color = get_average_color_of_image(img_resp.content)
                
                md5_string = hashlib.md5(("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
                thumb_url = md5_string + "_" + filename

                thumb_prop = convert_img_structure(filename, real_size_x, real_size_y, "VariantHotel.images", img_mime_type, "thumb", img_size, img_border_color, img_average_color)
                # save_image(thumb_prop["crop"]["x"], thumb_prop["crop"]["y"], thumb_prop["crop"]["width"],thumb_prop["crop"]["height"],thumb_prop["width"],thumb_prop["height"],70, thumb_url, img_resp.content)
                # images.append(thumb_prop)

                md5_string = hashlib.md5(("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
                px1_url = md5_string + "_" + filename
                
                px1_prop = convert_img_structure(filename, real_size_x, real_size_y, "VariantHotel.images", img_mime_type, "px1", img_size, img_border_color, img_average_color)
                # save_image(thumb_prop["crop"]["x"], px1_prop["crop"]["y"], px1_prop["crop"]["width"],px1_prop["crop"]["height"],px1_prop["width"],px1_prop["height"],70, px1_url, img_resp.content)
                # images.append(px1_prop)
                
                md5_string = hashlib.md5(("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
                px3_url = md5_string + "_" + filename

                px3_prop = convert_img_structure(filename, real_size_x, real_size_y, "VariantHotel.images", img_mime_type, "px3", img_size, img_border_color, img_average_color)
                # save_image(px3_prop["crop"]["x"], px3_prop["crop"]["y"], px3_prop["crop"]["width"],px3_prop["crop"]["height"],px3_prop["width"],px3_prop["height"],70, px3_url, img_resp.content)
                # images.append(px3_prop)
                
                md5_string = hashlib.md5(("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
                dx1_2_url = md5_string + "_" + filename

                dx1_2_prop = convert_img_structure(filename, real_size_x, real_size_y, "VariantHotel.images", img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)
                # save_image(dx1_2_prop["crop"]["x"], dx1_2_prop["crop"]["y"], dx1_2_prop["crop"]["width"],dx1_2_prop["crop"]["height"],dx1_2_prop["width"],dx1_2_prop["height"],70, dx1_2_url, img_resp.content)
                # images.append(dx1_2_prop)

                md5_string = hashlib.md5(("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
                original_url = md5_string + "_" + filename

                original_prop = convert_img_structure(filename, real_size_x, real_size_y, "VariantHotel.images", img_mime_type, "original", img_size, img_border_color, img_average_color)
                # save_image(original_prop["crop"]["x"], original_prop["crop"]["y"], original_prop["crop"]["width"],original_prop["crop"]["height"],original_prop["width"],original_prop["height"],70, original_url, img_resp.content)
                # images.append(orginal_prop)
                
                images.append({
                    "propId"        : prop_id,              # identifier of related product
                    "thumbUrl": thumb_url.replace("_", "-"),
                    "thumbProp"     : thumb_prop,           # Image variant properties
                    "px1Url": px1_url.replace("_", "-"),
                    "px1Prop"       : px1_prop,             # Image variant properties
                    "px3Url": px3_url.replace("_", "-"),
                    "px3Prop"       : px3_prop,             # Image variant properties
                    "dx1_2Url": dx1_2_url.replace("_", "-"),
                    "dx1_2Prop"     : dx1_2_prop,           # Image variant properties
                    "originalUrl": original_url,
                    "originalProp"  : original_prop,        # Image variant properties
                    "type"          : "VariantHotel.images" # Image type (please refer to which value should be specified to parent entity)
                })
            variant_entity = {
                "propId" : prop_id,         # identifier of related product
                "title" : variant_title,    # Room title
                "desc" : variant_desc,      # List of room amenities merged in one string with "\n" as delimiter, up to 25 items
                "longDesc" : long_desc,     # Room description up to 1000 symbols breaked by paragraph, line or paragraph break should be replaced with "\n"
                "variantSize" : variant_size + " Sqft", # Room size including measure or measures and coverage if this is possible
                "images" : images,              # List of room interior images up to 25 images (related image type should be "VariantHotel.images")
            }
            variants.append(variant_entity)
            
            station = db.session.query(Station).filter(Station.jobUrl == url).first()
            station.process = int(10 + 60 / variants_count * iii)
            db.session.commit()

            sys.stdout.write("\rProcess: {}%".format(int(10 + 60 / variants_count * iii)))
            sys.stdout.flush()

        svc = {
            "propId": prop_id,          # identifier of related product
            "title": title,             # Hotel name
            "type": 1,                  # Raw value
            "variant": variants,        # List of related rooms
            "address": address,         # Hotel full address
            "loc": geo_point,           # Hotel location
            "city": name,               # City name of hotel location
            "country": country          # Country of hotel location according to ISO 3166-1 (alpha-2 country code) in lower case
        }

        services.append(svc)

        cards = []
        images = []

        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 70
        db.session.commit()

        sys.stdout.write("\rProcess: 70%")
        sys.stdout.flush()

        gallary_count = len(hotelGalleryJson[hotelGalleryJsonId])
        iii = 0
        for img_name in hotelGalleryJson[hotelGalleryJsonId]:
            iii += 1
            img_url = "https:" + img_name["Url"]
            img_ext = img_url.split(".")[-1]
            img_url = img_url.replace(".{}".format(img_ext), "_720x450.{}".format(img_ext))
            filename = img_url.split("/")[-1]
            img_resp = get_response(img_url)
            img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(img_resp)
            img_border_color = get_border_color_of_image(img_resp.content)
            img_average_color = get_average_color_of_image(img_resp.content)
            
            md5_string = hashlib.md5(("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
            thumb_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

            thumb_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "thumb", img_size, img_border_color, img_average_color)
            # save_image(thumb_prop["crop"]["x"], thumb_prop["crop"]["y"], thumb_prop["crop"]["width"],thumb_prop["crop"]["height"],thumb_prop["width"],thumb_prop["height"],70, thumb_url, img_resp.content)
            # images.append(thumb_prop)

            md5_string = hashlib.md5(("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
            px1_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")
            
            px1_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "px1", img_size, img_border_color, img_average_color)
            # save_image(thumb_prop["crop"]["x"], px1_prop["crop"]["y"], px1_prop["crop"]["width"],px1_prop["crop"]["height"],px1_prop["width"],px1_prop["height"],70, px1_url, img_resp.content)
            # images.append(px1_prop)
            
            md5_string = hashlib.md5(("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
            px3_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

            px3_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "px3", img_size, img_border_color, img_average_color)
            # save_image(px3_prop["crop"]["x"], px3_prop["crop"]["y"], px3_prop["crop"]["width"],px3_prop["crop"]["height"],px3_prop["width"],px3_prop["height"],70, px3_url, img_resp.content)
            # images.append(px3_prop)
            
            md5_string = hashlib.md5(("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
            dx1_2_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

            dx1_2_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)
            # save_image(dx1_2_prop["crop"]["x"], dx1_2_prop["crop"]["y"], dx1_2_prop["crop"]["width"],dx1_2_prop["crop"]["height"],dx1_2_prop["width"],dx1_2_prop["height"],70, dx1_2_url, img_resp.content)
            # images.append(dx1_2_prop)

            md5_string = hashlib.md5(("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
            original_url = md5_string + "_" + filename.replace("_", "-")

            original_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "original", img_size, img_border_color, img_average_color)
            # save_image(original_prop["crop"]["x"], original_prop["crop"]["y"], original_prop["crop"]["width"],original_prop["crop"]["height"],original_prop["width"],original_prop["height"],70, original_url, img_resp.content)
            # images.append(orginal_prop)
            
            images.append({
                "propId"        : prop_id,              # identifier of related product
                "thumbUrl": thumb_url.replace("_", "-"),
                "thumbProp"     : thumb_prop,           # Image variant properties
                "px1Url": px1_url.replace("_", "-"),
                "px1Prop"       : px1_prop,             # Image variant properties
                "px3Url": px3_url.replace("_", "-"),
                "px3Prop"       : px3_prop,             # Image variant properties
                "dx1_2Url": dx1_2_url.replace("_", "-"),
                "dx1_2Prop"     : dx1_2_prop,           # Image variant properties
                "originalUrl": original_url,
                "originalProp"  : original_prop,        # Image variant properties
                "type"          : "Card.images"         # Image type (please refer to which value should be specified to parent entity)
            })

            station = db.session.query(Station).filter(Station.jobUrl == url).first()
            station.process = 70 + int(20.0/gallary_count) * iii
            db.session.commit()
            sys.stdout.write("\rProcess: {}%".format(int(70 + 20 * iii / variants_count)))
            sys.stdout.flush()

        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 90
        db.session.commit()

        sys.stdout.write("\rProcess: 90%")
        sys.stdout.flush()

        slider_card = {
            "propId" : prop_id,         # identifier of related product
            "subject" : name,           # City name of hotel location
            "title" : address,          # Hotel name
            "logicType" : 4,            # Raw value
            "images" : images,              # List of hotel images excluding room interior images up to 50 images (related image type should be "Card.images")
            "type" : 4                  # Raw value
        }

        img_url = "https://api.mapbox.com/styles/v1/sixtravel/cj46j8tu40c4m2rp9js45y80x/static/{},{},7/1250x1250?access_token=pk.eyJ1Ijoic2l4dHJhdmVsIiwiYSI6ImNqNDZqNXRhdzJiOG0ycm9iOGJmcHBmbWsifQ.ybkyZTQl4kInpOEabItxmA&attribution=false&logo=false".format(longitude, latitude)
        filename = title.lower().replace(" ", "-") + "-map.png"
        img_resp = get_response(img_url)
        img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(img_resp)
        img_border_color = get_border_color_of_image(img_resp.content)
        img_average_color = get_average_color_of_image(img_resp.content)
        
        md5_string = hashlib.md5(("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
        thumb_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

        thumb_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "thumb", img_size, img_border_color, img_average_color)
        # save_image(thumb_prop["crop"]["x"], thumb_prop["crop"]["y"], thumb_prop["crop"]["width"],thumb_prop["crop"]["height"],thumb_prop["width"],thumb_prop["height"],70, thumb_url, img_resp.content)
        # images.append(thumb_prop)

        md5_string = hashlib.md5(("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
        px1_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")
        
        px1_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "px1", img_size, img_border_color, img_average_color)
        # save_image(thumb_prop["crop"]["x"], px1_prop["crop"]["y"], px1_prop["crop"]["width"],px1_prop["crop"]["height"],px1_prop["width"],px1_prop["height"],70, px1_url, img_resp.content)
        # images.append(px1_prop)
        
        md5_string = hashlib.md5(("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
        px3_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

        px3_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "px3", img_size, img_border_color, img_average_color)
        # save_image(px3_prop["crop"]["x"], px3_prop["crop"]["y"], px3_prop["crop"]["width"],px3_prop["crop"]["height"],px3_prop["width"],px3_prop["height"],70, px3_url, img_resp.content)
        # images.append(px3_prop)
        
        md5_string = hashlib.md5(("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
        dx1_2_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

        dx1_2_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)
        # save_image(dx1_2_prop["crop"]["x"], dx1_2_prop["crop"]["y"], dx1_2_prop["crop"]["width"],dx1_2_prop["crop"]["height"],dx1_2_prop["width"],dx1_2_prop["height"],70, dx1_2_url, img_resp.content)
        # images.append(dx1_2_prop)

        md5_string = hashlib.md5(("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
        original_url = md5_string + "_" + filename

        original_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "original", img_size, img_border_color, img_average_color)
        # save_image(original_prop["crop"]["x"], original_prop["crop"]["y"], original_prop["crop"]["width"],original_prop["crop"]["height"],original_prop["width"],original_prop["height"],70, original_url, img_resp.content)
        # images.append(orginal_prop)
        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 95
        db.session.commit()
        sys.stdout.write("\rProcess: 95%")
        sys.stdout.flush()
        detailImage = {
            "propId"        : prop_id,              # identifier of related product
            "thumbUrl": thumb_url.replace("_", "-"),
            "thumbProp"     : thumb_prop,           # Image variant properties
            "px1Url": px1_url.replace("_", "-"),
            "px1Prop"       : px1_prop,             # Image variant properties
            "px3Url": px3_url.replace("_", "-"),
            "px3Prop"       : px3_prop,             # Image variant properties
            "dx1_2Url": dx1_2_url.replace("_", "-"),
            "dx1_2Prop"     : dx1_2_prop,           # Image variant properties
            "originalUrl": original_url,
            "originalProp"  : original_prop,        # Image variant properties
            "type"          : "Card.detailImage"         # Image type (please refer to which value should be specified to parent entity)
        }
        map_card = {
            "propId" : prop_id,         # identifier of related product
            "subject" : title,          # Hotel name
            "title" : address,          # Hotel full address
            "logicType" : 2,            # Raw value
            "detailImage" : detailImage,         # Map screenshot (please see how to make map screenshot below) (related image type should be "c")
            "loc": {
                "latitude": latitude,   # Latitude
                "longitude": longitude  # Longitude
            },                          # Hotel location
            "type" : 5                  # Raw value
        }

        description_entity = [
            {
                "tag": "blockquote",
                "value": tree.xpath('//p[@class="shortintro"]/text()')[0].strip()
            },
            {
                "tag": "p",
                "value": tree.xpath('//div[@class="mainintro"]/div/text()')[0].strip()
            }
        ]
        ul_tags = []
        try:
            ul_tags.append(tree.xpath('//li[contains(text(),"Total Rooms:")]/text()')[0])
            # description_entity.append({
            #         "tag": "ul",
            #         "value": tree.xpath('//li[contains(text(),"Total Rooms:")]/text()')[0]
            #     })
        except Exception as e:
            print (e)
            pass
        try:
            ul_tags.append(tree.xpath('//li[contains(text(),"Total Suites:")]/text()')[0])
            
            # description_entity.append({
            #         "tag": "ul",
            #         "value": tree.xpath('//li[contains(text(),"Total Suites:")]/text()')[0]
            #     })
        except:
            pass
        try:
            ul_tags.append(tree.xpath('//li[contains(text(),"Total Villas:")]/text()')[0])
            # description_entity.append({
            #         "tag": "ul",
            #         "value": tree.xpath('//li[contains(text(),"Total Villas:")]/text()')[0]
            #     })
        except:
            pass
        try:
            ul_tags += tree.xpath('//p[@class="airport"]/text()')[0].strip().split(";")
        except:
            pass
        description_entity.append({
                "tag": "ul",
                "value": "\n".join(ul_tags)
            })


        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.process = 98
        db.session.commit()

        sys.stdout.write("\rProcess: 98%")
        sys.stdout.flush()

        overview_card = {
            "propId" : prop_id,         # identifier of related product
            "subject" : "ABOUT HOTEL",  # Raw value
            "title" : "Overview",       # Raw value
            "logicType" : 1,            # Raw value
            "detailImage" : {},         # Hotel outer exterior image (related image type should be "Card.detailImage")
            "attributedDescription" : description_entity,
            "type" : 1                  # Raw value
        }

        room_selection_card = {
            "propId" : prop_id,         # identifier of related product
            "subject" : "STAY",         # Raw value
            "title" : "Rooms & Rates",  # Raw value
            "logicType" : 3,            # Raw value
            "actionType" : 1,           # Raw value
            "detailImage" : {},         # Hotel inner interior image or room interior image (related image type should be "Card.detailImage")
            "type" : 1                  # Raw value
        }

        card = [slider_card, map_card, overview_card, room_selection_card]
        
        product_entity = {
            "propId"		: prop_id,      # Random unique identifier matching the following regular expression /^[A-Za-z0-9]{10}$/, this is needed to locate all entities related to certain product
            "name"			: name,         # City name of hotel location
            "title"			: title,        # Hotel name
            "detailImage"	: {},       # Hotel outer exterior image (related image type should be "Product.detailImage")
            "service"       : services,      # List of related services
            "card"		    : card      # List of related cards
        }
        
        job_id = hashlib.md5(url).hexdigest()
        jobUrl = url
        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.jobStatus = 1
        station.jobResult = json.dumps(product_entity)
        station.process = 100
        db.session.commit()
        
        sys.stdout.write("\rProcess: 100%")
        sys.stdout.write("Done!")
        sys.stdout.flush()

    except:
        station = db.session.query(Station).filter(Station.jobUrl == url).first()
        station.jobStatus = -1
        station.jobResult = ""
        station.process = 0
        db.session.commit()
        
    # with open("product.json", "w") as f:
    #     json.dump(product_entity, f, indent=2)
        # break
def get_country_code(address):
    correct_address = address.replace(".", "").replace(",", " ").lower()
    for cc in country_codes:
        tt = re.findall("\s({}|{}|{})$".format(cc[0],cc[2],cc[3]), correct_address)
        if len(tt) > 0:
            return cc[1]
def get_average_color_of_image(content):
    im = Image.open(BytesIO(content)).convert('RGB')
    img2 = im.resize((1,1))
    try:
        (r,g,b) = img2.getpixel((0,0))
    except:
        (r,g,b,a) = img2.getpixel((0,0))
    return '{:02x}{:02x}{:02x}'.format(r, g, b)
    
def get_border_color_of_image(content):
    im = Image.open(BytesIO(content)).convert('RGB')
    size = im.size
    img2 = im.crop((0, 0, 1,size[1]))
    img3 = img2.resize((1,1))
    try:
        (r,g,b) = img2.getpixel((0,0))
    except:
        print (img2.getpixel((0,0)))
        (r,g,b,a) = img2.getpixel((0,0))
    return '{:02x}{:02x}{:02x}'.format(r, g, b)

def get_image_properties(response):
    im = Image.open(BytesIO(response.content))
    size = im.size
    return response.headers["Content-Length"], response.headers["Content-Type"], size[0], size[1]

def get_response(img_url):
    try:
        response = requests.get(img_url)
    except: 
        response = None
    return response

def get_image_rect(width, height, ratio_des):
    ratio_ori = width / height
    if ratio_des < 1.0:
        if ratio_ori >= ratio_des:
            x = int((width - height * ratio_des) / 2.0)
            y = 0
            w = int(height * ratio_des)
            h = height
        else:
            x = 0
            y = int((height - width / ratio_des) / 2.0)
            w = width
            h = int(width / ratio_des)
    else:
        if ratio_ori >= 1.0/ratio_des:
            x = int((width - height * ratio_des) / 2.0)
            y = 0
            w = int(height * ratio_des)
            h = height
        else:
            x = 0
            y = int((height - width / ratio_des) / 2.0)
            w = width
            h = int(width / ratio_des)
    return x, y, w, h

def convert_img_structure(filename, width, height, img_type, img_mime_type, variant_type, img_size, img_border_color, img_average_color):
    if variant_type == "thumb":
        imgw = 250
        imgh = 250
    elif variant_type == "px1":
        if img_type == "VariantHotel.images":
            imgw = 750
            imgh = 624
        else:
            imgw = 750
            imgh = 943
    elif variant_type == "px3":
        if img_type == "VariantHotel.images":
            imgw = 1125
            imgh = 1140
        else:
            imgw = 1125
            imgh = 1722
    elif variant_type == "dx1_2":
        if img_type == "VariantHotel.images":
            imgw = 960
            imgh = 1058
        else:
            imgw = 960
            imgh = 800
    elif variant_type == "original":
        imgw = width
        imgh = height
        
    ratio = float(float(imgw) / float(imgh))
   
    x, y, w, h = get_image_rect(width, height, ratio)
    if variant_type == "original":
        img_prop = {
            "fileName"  : filename.replace("_", "-"),         # Image filename
            "imageType" : img_mime_type,        # Image variant mime type
            "width"     : imgw,             # Image variant width in pixels
            "height"    : imgh,             # Image variant height in pixels
            "ratio"     : imgw/imgh,        # Image variant ratio as `width / height` 
            "crop"   : {             # Image variant cropping area (please see image cropping below) 
                "x"      : x,
                "y"      : y,
                "width"  : w,
                "height" : h
            },
            "size"      : int(img_size),            # Image variant size in bytes
            "bgColor"   : img_border_color, # Average color of image border (please see image border color below)
            "avgColor"  : img_average_color # Average color of entire image (please see image average color below)
        }
    else:
        img_prop = {
            "fileName"  : filename.replace("_", "-").replace(".png",".jpg"),         # Image filename
            "imageType" : img_mime_type,        # Image variant mime type
            "width"     : imgw,             # Image variant width in pixels
            "height"    : imgh,             # Image variant height in pixels
            "ratio"     : imgw/imgh,        # Image variant ratio as `width / height` 
            "crop"   : {             # Image variant cropping area (please see image cropping below) 
                "x"      : x,
                "y"      : y,
                "width"  : w,
                "height" : h
            },
            "size"      : int(img_size),            # Image variant size in bytes
            "bgColor"   : img_border_color, # Average color of image border (please see image border color below)
            "avgColor"  : img_average_color # Average color of entire image (please see image average color below)
        }
    return (img_prop)

def save_image(cx, cy, cw, ch, rw, rh, rq, fn, content):
    im = Image.open(BytesIO(content))
    im = im.crop((cx, cy, cw, ch))
    im = im.resize((rw, rh))
    im.save(fn)

if __name__ == '__main__':
    app.debug = True
    app.run()
