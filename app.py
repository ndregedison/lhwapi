# -*- coding: utf8 -*-

import hashlib
import json
import os
import random
import re
import string
import sys
import time
import urllib
from datetime import datetime
from io import BytesIO
from Queue import Queue
from threading import Thread
from urlparse import urlparse

import backoff
import boto3
import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from lxml import html
from PIL import Image

from countrycodes import country_codes

###################################################################
###################################################################

reload(sys)
sys.setdefaultencoding("utf-8")


ACCESS_KEY = "AKIAIE32TAAENSQROZJQ"
SECURITY_KEY = "uJ8B2kp3Kk8D/qfYv5TMV0vsVWrfnwukUsOxcu+4"

resource = boto3.resource(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECURITY_KEY,
)

bucket_name = "sixtravel-dev"
###################################################################
###################################################################

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:root@localhost/lhwApi')
db = SQLAlchemy(app)

####################################################################
####################################################################

class Station(db.Model):
    """
        Station table
    """
    __tablename__ = "stations"

    id      = db.Column(db.String(120), primary_key=True)
    url     = db.Column(db.Text)
    domain   = db.Column(db.Text)    # project , domain
    status   = db.Column(db.Integer) # 1: Pending,  2: Running, 3: Finished,  0: Stopped, None: None
    result   = db.Column(db.Text)    # JSON STRING
    create_time  = db.Column(db.DateTime)    # job created time
    start_time   = db.Column(db.DateTime)    # job started time
    finish_time = db.Column(db.DateTime)     # job finished time

db.create_all()

#####################################################################
#####################################################################

class Job(object):
    """[Job Class]
    
    Arguments:
        object {[type]} -- [description]
    """
    
    def __init__(self, _id=None, url=None, status=None, create_time=None, start_time=None, finish_time=None, result=None):
        self.id = _id
        self.url = url
        self.status = status
        self.result = result
        self.create_time = create_time
        self.start_time = start_time
        self.finish_time = finish_time
        self.type = self.get_type(url)

        self.save_job()


    def save_job(self):
        station = Station(id=self.id, url=self.url, status=self.status, result=self.result,
                            create_time=self.create_time, start_time=self.start_time, finish_time=self.finish_time)  # pending
        db.session.add(station)
        db.session.commit()

    def update_job(self):
        station = db.session.query(Station).filter(Station.id == self.id).first()
        
        station.status = self.status
        station.create_time = self.create_time
        station.result = self.result
        station.start_time = self.start_time
        station.finish_time = self.finish_time
        
        db.session.commit()

    def get_domain(self, url):
        parse_uri = urlparse(url)
        domain = "{0.netloc}".format(parse_uri)
        return domain


    def get_type(self, url):
        if "lhw.com" in self.get_domain(url):
            return run_lhwapi
        else:
            return None

#####################################################################
#####################################################################

@app.route('/')
def index():
    return "Welcome API Home!"

#####################################################################
#####################################################################

@app.route('/create', methods=['POST'])
def create():
    url = None

    if request.method == 'POST':
        # request param : url
        url = request.form['url']
        
        if url is None:
            return jsonify({
                "status": None, # not started & failed
                "message": "failed",
                "id": None,
            })

        # if url is encoded
        url = urllib.unquote_plus(url)
        job_id = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        station = db.session.query(Station).filter(Station.url == url)

        if not station.count():
            new_job = Job(_id=job_id, url=url, status=1,
                          create_time=datetime.utcnow())  # create a job

            job_queue.put(new_job)

            return jsonify({"status": "1", "id": job_id, "message":"pending" })
        
        else:
            job_id = station.first().id
            status = station.first().status
            
            if status == 3:
                return jsonify({"status": "3", "id": job_id, "message": "finished"})
            elif status == 2:
                return jsonify({"status": "2", "id": job_id, "message": "running"})
            elif status == 1:
                return jsonify({"status": "1", "id": job_id, "message": "pending"})
            elif status == 0:
                return jsonify({"status": "0", "id": job_id, "message": "failed"})

#####################################################################
#####################################################################

@app.route('/result/<job_id>', methods=['GET'])
def result(job_id):
    station = db.session.query(Station).filter(Station.id == job_id)

    if not station.count():
        return jsonify({"message": "no exist", "id": job_id, "status": None, "result": None, "create_time": None, "start_time":None, "finish_time": None})
    else:
        try:
            status = station.first().status
        except:
            status = None
        try:
            url = station.first().url
        except:
            url = None
        try:
            result = station.first().result
        except:
            result = None
        try:
            create_time = station.first().create_time
        except:
            create_time = None
        try:
            finish_time = station.first().finish_time
        except:
            finish_time = None
        try:
            status = station.first().status
        except:
            status = None

        if status == None:
            return jsonify({"message": "no exist", "id": job_id, "status": status, "result": None, "create_time": create_time, "finish_time": finish_time})
        elif status == 1:
            return jsonify({"message": "pending", "id": job_id, "status": status, "result": None, "create_time": create_time, "finish_time": finish_time})
        elif status == 2:
            return jsonify({"message": "running", "id": job_id, "status": status, "result": None, "create_time": create_time, "finish_time": finish_time})
        elif status == 3:
            return jsonify({"message": "finished", "id": job_id, "status": status, "result": json.loads(result), "create_time": create_time, "finish_time": finish_time})
        elif status == 0:
            return jsonify({"message": "stopped", "id": job_id, "status": status, "result": None, "create_time": create_time, "finish_time": finish_time})

#####################################################################
#####################################################################

def get_header():
    header = {
        'Pragma': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    return header

#####################################################################
#####################################################################

@backoff.on_exception(backoff.constant, requests.exceptions.RequestException, max_tries=5, interval=10)
def get_response(url, headers=None):
    if headers is not None:
        response = requests.get(url, headers=headers)
    else:
        response = requests.get(url)
    return response

#####################################################################
#####################################################################

def run_lhwapi(app, db, job):
    try:
        results = {}
        job.start_time = datetime.utcnow()
        job.status = 2
        job.update_job()
        headers = get_header()
        response = get_response(job.url, headers=headers) # send the requests to url
        tree = html.fromstring(response.content)
        # prop_id
        prop_id = ''.join(
            [random.choice(string.ascii_letters + string.digits) for n in range(10)])
        # address
        address = tree.xpath(
            "//div[@class='contactinfo']/p[1]/text()")[0]
        # name | city
        name = tree.xpath(
            "//div[@class='hotelheader']/h1/span/text()")[0].split(",")[-2].strip()
        # country
        country = get_country_code(address)
        # title
        title = tree.xpath(
            "//div[@class='hotelheader']/h1/text()")[0].strip()
        # geo location
        latitude = re.search("mapLat=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()      # Latitude
        longitude = re.search("mapLong=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()    # Longitude
        geo_point = {
            "latitude": float(latitude),
            "longitude": float(longitude)
        }
        # product detailImage:

        hotelGalleryJsonId = re.search("var hotelGalleryJson = galleryJson\[\"(.*?)\"\]\;", response.text, re.S|re.M|re.I).group(1).strip()
        hotelGalleryJson = json.loads(re.search("var galleryJson = (.*?)\;", response.text, re.S|re.M|re.I).group(1).strip())
        productDetailImage = "http:" + \
            hotelGalleryJson[hotelGalleryJsonId][0]["Url"].replace(
                ".jpg", "_720x450.jpg")
        
        overviewDeatailImage = "https:" + \
            hotelGalleryJson[hotelGalleryJsonId][0]["Url"].replace(
                ".jpg", "_720x450.jpg")
        services = []  # service:Array<Service> // List of related services
        iii = 0
        variants = []
        for variant in tree.xpath('//div[@class="roomitem"]'):
            iii += 1
            variant_title = variant.xpath('p/text()')[0].strip()
            try:
                variant_size = re.search("(\d+[\s]?|\d+[\s]?\-\d+[\s]?)sq[\s]?f", variant.xpath(
                    'img[contains(@class, "roompic")]/@alt')[0].lower(), re.S | re.M).group(1).strip()
            except:
                try:
                    variant_size = re.search(
                        "(\d+[\s]?|\d+[\s]?\-\d+[\s]?)sq[\s]?f", variant_title.lower(), re.S | re.M).group(1).strip()
                except:
                    variant_size = ""
            variant_desc = variant_title
            try:
                variant_img_id = re.search("(\w+\-\w+\-\w+\-\w+\-\w+)", variant.xpath(
                    './/a[@class="gallerylaunch"]/@onclick')[0], re.S | re.M).group(1)
            except:
                variant_img_id = ""
            variant_url = "https://www.lhw.com/hotel/" + \
                variant.xpath(
                    './/a[@class="btn btn-2"]/@href')[0].split(",")[0]
            resp = get_response(variant_url, headers=headers)
            tree_room = html.fromstring(resp.text)
            long_desc = tree_room.xpath(
                '//div[@id="selected-room"]//span[@class="feat"]/text()')[0].strip()
            images = []
            try:
                for img_name in hotelGalleryJson[variant_img_id]:
                    img_url = "https:" + img_name["Url"]
                    img_ext = img_url.split(".")[-1]
                    img_url = img_url.replace(".{}".format(
                        img_ext), "_790x490.{}".format(img_ext))
                    
                    images.append(get_image_property(
                        img_url, prop_id, "VariantHotel.images"))
            except:
                pass
            
            variant_entity = {
                "propId": prop_id,         # identifier of related product
                "title": variant_title,    # Room title
                # List of room amenities merged in one string with "\n" as delimiter, up to 25 items
                "desc": variant_desc,
                # Room description up to 1000 symbols breaked by paragraph, line or paragraph break should be replaced with "\n"
                "longDesc": long_desc,
                # Room size including measure or measures and coverage if this is possible
                "variantSize": variant_size + " Sqft",
                # List of room interior images up to 25 images (related image type should be "VariantHotel.images")
                "images": images,
            }
            variants.append(variant_entity)
        
        svc = {
            "propId": prop_id,          # identifier of related product
            "title": title,             # Hotel name
            "type": 1,                  # Raw value
            "variant": variants,        # List of related rooms
            "address": address,         # Hotel full address
            "loc": geo_point,           # Hotel location
            "city": name,               # City name of hotel location
            # Country of hotel location according to ISO 3166-1 (alpha-2 country code) in lower case
            "country": country
        }

        services.append(svc)
        cards = []     # card:Array<Card>       // List of related cards
        images = []
        
        gallary_count = len(hotelGalleryJson[hotelGalleryJsonId])
        iii = 0
        for img_name in hotelGalleryJson[hotelGalleryJsonId]:
            iii += 1
            img_url = "https:" + img_name["Url"]
            img_ext = img_url.split(".")[-1]
            img_url = img_url.replace(".{}".format(
                img_ext), "_720x450.{}".format(img_ext))

            images.append(get_image_property(img_url, prop_id, "Card.images"))
        map_card = {}  # Map card entity
        overview_card = {}  # Overview card entity
        room_selection_card = {}  # Room selection card entity
        slider_card = {
            "propId": prop_id,         # identifier of related product
            "subject": name,           # City name of hotel location
            "title": address,          # Hotel name
            "logicType": 4,            # Raw value
            # List of hotel images excluding room interior images up to 50 images (related image type should be "Card.images")
            "images": images,
            "type": 4                  # Raw value
        }
        img_url = "https://api.mapbox.com/styles/v1/sixtravel/cj46j8tu40c4m2rp9js45y80x/static/{},{},7/1250x1250?access_token=pk.eyJ1Ijoic2l4dHJhdmVsIiwiYSI6ImNqNDZqNXRhdzJiOG0ycm9iOGJmcHBmbWsifQ.ybkyZTQl4kInpOEabItxmA&attribution=false&logo=false".format(
            longitude, latitude)
        detailImage = get_image_property(img_url, prop_id, "Card.detailImage")
        map_card = {
            "propId": prop_id,         # identifier of related product
            "subject": title,          # Hotel name
            "title": address,          # Hotel full address
            "logicType": 2,            # Raw value
            # Map screenshot (please see how to make map screenshot below) (related image type should be "c")
            "detailImage": detailImage,
            "loc": geo_point,                          # Hotel location
            "type": 5                  # Raw value
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
            ul_tags.append(tree.xpath(
                '//li[contains(text(),"Total Rooms:")]/text()')[0])
        except Exception as e:
            pass
        try:
            ul_tags.append(tree.xpath(
                '//li[contains(text(),"Total Suites:")]/text()')[0])
        except:
            pass
        try:
            ul_tags.append(tree.xpath(
                '//li[contains(text(),"Total Villas:")]/text()')[0])
        except:
            pass
        try:
            ul_tags += tree.xpath('//p[@class="airport"]/text()')[
                0].strip().split(";")
        except:
            pass

        description_entity.append({
            "tag": "ul",
            "value": "\n".join(ul_tags)
        })
        print ("11")
        overview_card = {
            "propId": prop_id,         # identifier of related product
            "subject": "ABOUT HOTEL",  # Raw value
            "title": "Overview",       # Raw value
            "logicType": 1,            # Raw value
            # Hotel outer exterior image (related image type should be "Card.detailImage")
            "detailImage": get_image_property(overviewDeatailImage, prop_id, "Card.detailImage"),
            "attributedDescription": description_entity,
            "type": 1                  # Raw value
        }
        room_url = "{}/rooms".format(job.url)
        room_resp = get_response(room_url, headers=headers)
        room_content = html.fromstring(room_resp.text)
        img_url = "https:" + re.search("background-image\:url\((.*?)\)\;", room_content.xpath('//div[@class="bigimageheader"]/@style')[0], re.S | re.M).group(1)
        room_selection_card = {
            "propId": prop_id,         # identifier of related product
            "subject": "STAY",         # Raw value
            "title": "Rooms & Rates",  # Raw value
            "logicType": 3,            # Raw value
            "actionType": 1,           # Raw value
            # Hotel inner interior image or room interior image (related image type should be "Card.detailImage")
            "detailImage": get_image_property(img_url, prop_id, "Card.detailImage"),
            "type": 1                  # Raw value
        }
        card = [slider_card, map_card, overview_card, room_selection_card]

        product_entity = {
            # Random unique identifier matching the following regular expression /^[A-Za-z0-9]{10}$/, this is needed to locate all entities related to certain product
            "propId": prop_id,
            "name": name,         # City name of hotel location
            "title": title,        # Hotel name
            # Hotel outer exterior image (related image type should be "Product.detailImage")
            "detailImage": get_image_property(productDetailImage, prop_id, "Product.detailImage"),
            "service": services,      # List of related services
            "card": card      # List of related cards
        }
        job.status = 3
        job.result = json.dumps(product_entity)
        job.finish_time = datetime.utcnow()
        job.update_job()
    except Exception as e:
        print (e)
        job.finish_time = datetime.utcnow()
        job.status = 0
        job.result = None
        job.update_job()

#####################################################################
#####################################################################
def get_image_property(img_url, prop_id, tp):
    filename = img_url.split("/")[-1]
    img_resp = get_response(img_url)
    img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(
        img_resp)
    img_border_color = get_border_color_of_image(
        img_resp.content)
    img_average_color = get_average_color_of_image(
        img_resp.content)

    md5_string = hashlib.md5(
        ("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
    thumb_url = md5_string + "_" + filename.replace("_", "-")

    thumb_prop = convert_img_structure(
        filename, real_size_x, real_size_y, tp, img_mime_type, "thumb", img_size, img_border_color, img_average_color)

    md5_string = hashlib.md5(
        ("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
    px1_url = md5_string + "_" + filename.replace("_", "-")

    px1_prop = convert_img_structure(
        filename, real_size_x, real_size_y, tp, img_mime_type, "px1", img_size, img_border_color, img_average_color)

    md5_string = hashlib.md5(
        ("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
    px3_url = md5_string + "_" + filename.replace("_", "-")

    px3_prop = convert_img_structure(
        filename, real_size_x, real_size_y, tp, img_mime_type, "px3", img_size, img_border_color, img_average_color)

    md5_string = hashlib.md5(
        ("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
    dx1_2_url = md5_string + "_" + filename.replace("_", "-")

    dx1_2_prop = convert_img_structure(
        filename, real_size_x, real_size_y, tp, img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)

    md5_string = hashlib.md5(
        ("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
    original_url = md5_string + "_" + filename

    original_prop = convert_img_structure(
        filename, real_size_x, real_size_y, tp, img_mime_type, "original", img_size, img_border_color, img_average_color)

    return {
        "propId": prop_id,              # identifier of related product
        "thumbUrl": thumb_url,
        "thumbProp": thumb_prop,           # Image variant properties
        "px1Url": px1_url,
        "px1Prop": px1_prop,             # Image variant properties
        "px3Url": px3_url,
        "px3Prop": px3_prop,             # Image variant properties
        "dx1_2Url": dx1_2_url,
        "dx1_2Prop": dx1_2_prop,           # Image variant properties
        "originalUrl": original_url,
        "originalProp": original_prop,        # Image variant properties
        # Image type (please refer to which value should be specified to parent entity)
        "type": tp
    }
    
#####################################################################
#####################################################################

def run(app, db, queue):
    job = queue.get()
    job.type(app, db, job)
    queue.task_done()

###################################################################
###################################################################


job_queue = Queue()

with app.app_context():
    thr = Thread(target=run, args=(app, db, job_queue))
    thr.daemon = True
    thr.start()

#####################################################################
#####################################################################

# def scrape(app, db, job):
#     try:
#         # headers = get_header()
        
#         # sys.stdout.write("\rProcess: 5%")
#         # sys.stdout.flush()

#         # response = requests.get(url, headers=headers)
#         # tree = html.fromstring(response.text)

#         # prop_id = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(10)])
#         # address = tree.xpath("//div[@class='contactinfo']/p[1]/text()")[0]

#         # name = tree.xpath("//div[@class='hotelheader']/h1/span/text()")[0].split(",")[-2].strip()

#         # country = get_country_code(address) # country
#         # title = tree.xpath("//div[@class='hotelheader']/h1/text()")[0].strip() # title

        

#         # latitude = re.search("mapLat=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()      # Latitude
#         # longitude = re.search("mapLong=(.*?)\&", response.text, re.S|re.M|re.I).group(1).strip()    # Longitude
        
#         # geo_point = {
#         #     "latitude": float(latitude),
#         #     "longitude": float(longitude)
#         # }
#         # variants = []

#         # hotelGalleryJsonId = re.search("var hotelGalleryJson = galleryJson\[\"(.*?)\"\]\;", response.text, re.S|re.M|re.I).group(1).strip()
#         # hotelGalleryJson = json.loads(re.search("var galleryJson = (.*?)\;", response.text, re.S|re.M|re.I).group(1).strip())
        
#         # sys.stdout.write("\rProcess: 10%")
#         # sys.stdout.flush()

#         # variants_count  = len(tree.xpath('//div[@class="roomitem"]'))
#         # iii = 0
#         for variant in tree.xpath('//div[@class="roomitem"]'):
#             iii += 1
#             variant_title = variant.xpath('p/text()')[0].strip()
#             try:
#                 variant_size = re.search("(\d+[\s]?|\d+[\s]?\-\d+[\s]?)sq[\s]?f", variant.xpath('img[contains(@class, "roompic")]/@alt')[0].lower(), re.S | re.M).group(1).strip()
#             except:
#                 try:
#                     variant_size = re.search("(\d+[\s]?|\d+[\s]?\-\d+[\s]?)sq[\s]?f", variant_title.lower(), re.S | re.M).group(1).strip()
#                 except:
#                     variant_size = ""
#             variant_desc = variant_title
#             try:
#                 variant_img_id = re.search("(\w+\-\w+\-\w+\-\w+\-\w+)", variant.xpath('.//a[@class="gallerylaunch"]/@onclick')[0], re.S | re.M).group(1)
#             except:
#                 variant_img_id = ""
#             variant_url = "https://www.lhw.com/hotel/" + variant.xpath('.//a[@class="btn btn-2"]/@href')[0].split(",")[0]
#             resp = get_response(variant_url, headers=headers)
#             tree_room = html.fromstring(resp.text)
#             long_desc = tree_room.xpath('//div[@id="selected-room"]//span[@class="feat"]/text()')[0].strip()
#             images = []
#             try:
#                 for img_name in hotelGalleryJson[variant_img_id]:
#                     img_url = "https:" + img_name["Url"]
#                     img_ext = img_url.split(".")[-1]
#                     img_url = img_url.replace(".{}".format(img_ext), "_790x490.{}".format(img_ext))

#             except:
#                 pass
#             variant_entity = {
#                 "propId" : prop_id,         # identifier of related product
#                 "title" : variant_title,    # Room title
#                 "desc" : variant_desc,      # List of room amenities merged in one string with "\n" as delimiter, up to 25 items
#                 "longDesc" : long_desc,     # Room description up to 1000 symbols breaked by paragraph, line or paragraph break should be replaced with "\n"
#                 "variantSize" : variant_size + " Sqft", # Room size including measure or measures and coverage if this is possible
#                 "images" : images,              # List of room interior images up to 25 images (related image type should be "VariantHotel.images")
#             }
#             variants.append(variant_entity)

#             sys.stdout.write("\rProcess: {}%".format(int(10 + 40 / variants_count * iii)))
#             sys.stdout.flush()

#         svc = {
#             "propId": prop_id,          # identifier of related product
#             "title": title,             # Hotel name
#             "type": 1,                  # Raw value
#             "variant": variants,        # List of related rooms
#             "address": address,         # Hotel full address
#             "loc": geo_point,           # Hotel location
#             "city": name,               # City name of hotel location
#             "country": country          # Country of hotel location according to ISO 3166-1 (alpha-2 country code) in lower case
#         }

#         services.append(svc)

#         cards = []
#         images = []

#         sys.stdout.write("\rProcess: 50%")
#         sys.stdout.flush()

#         gallary_count = len(hotelGalleryJson[hotelGalleryJsonId])
#         iii = 0
#         for img_name in hotelGalleryJson[hotelGalleryJsonId]:
#             iii += 1
#             img_url = "https:" + img_name["Url"]
#             img_ext = img_url.split(".")[-1]
#             img_url = img_url.replace(".{}".format(img_ext), "_720x450.{}".format(img_ext))
#             filename = img_url.split("/")[-1]
#             img_resp = get_response(img_url)
#             img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(img_resp)
#             img_border_color = get_border_color_of_image(img_resp.content)
#             img_average_color = get_average_color_of_image(img_resp.content)
            
#             md5_string = hashlib.md5(("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
#             thumb_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#             thumb_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "thumb", img_size, img_border_color, img_average_color)
#             # save_image(thumb_prop["crop"]["x"], thumb_prop["crop"]["y"], thumb_prop["crop"]["width"],thumb_prop["crop"]["height"],thumb_prop["width"],thumb_prop["height"],70, thumb_url, img_resp.content)
#             # images.append(thumb_prop)

#             md5_string = hashlib.md5(("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
#             px1_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")
            
#             px1_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "px1", img_size, img_border_color, img_average_color)
#             # save_image(thumb_prop["crop"]["x"], px1_prop["crop"]["y"], px1_prop["crop"]["width"],px1_prop["crop"]["height"],px1_prop["width"],px1_prop["height"],70, px1_url, img_resp.content)
#             # images.append(px1_prop)
            
#             md5_string = hashlib.md5(("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
#             px3_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#             px3_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "px3", img_size, img_border_color, img_average_color)
#             # save_image(px3_prop["crop"]["x"], px3_prop["crop"]["y"], px3_prop["crop"]["width"],px3_prop["crop"]["height"],px3_prop["width"],px3_prop["height"],70, px3_url, img_resp.content)
#             # images.append(px3_prop)
            
#             md5_string = hashlib.md5(("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
#             dx1_2_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#             dx1_2_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)
#             # save_image(dx1_2_prop["crop"]["x"], dx1_2_prop["crop"]["y"], dx1_2_prop["crop"]["width"],dx1_2_prop["crop"]["height"],dx1_2_prop["width"],dx1_2_prop["height"],70, dx1_2_url, img_resp.content)
#             # images.append(dx1_2_prop)

#             md5_string = hashlib.md5(("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
#             original_url = md5_string + "_" + filename.replace("_", "-")

#             original_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.images", img_mime_type, "original", img_size, img_border_color, img_average_color)
#             # save_image(original_prop["crop"]["x"], original_prop["crop"]["y"], original_prop["crop"]["width"],original_prop["crop"]["height"],original_prop["width"],original_prop["height"],70, original_url, img_resp.content)
#             # images.append(orginal_prop)
            
#             images.append({
#                 "propId"        : prop_id,              # identifier of related product
#                 "thumbUrl": thumb_url.replace("_", "-"),
#                 "thumbProp"     : thumb_prop,           # Image variant properties
#                 "px1Url": px1_url.replace("_", "-"),
#                 "px1Prop"       : px1_prop,             # Image variant properties
#                 "px3Url": px3_url.replace("_", "-"),
#                 "px3Prop"       : px3_prop,             # Image variant properties
#                 "dx1_2Url": dx1_2_url.replace("_", "-"),
#                 "dx1_2Prop"     : dx1_2_prop,           # Image variant properties
#                 "originalUrl": original_url,
#                 "originalProp"  : original_prop,        # Image variant properties
#                 "type"          : "Card.images"         # Image type (please refer to which value should be specified to parent entity)
#             })

#             sys.stdout.write("\rProcess: {}%".format(int(50 + 40 * iii / gallary_count)))
#             sys.stdout.flush()

#         sys.stdout.write("\rProcess: 90%")
#         sys.stdout.flush()

#         slider_card = {
#             "propId" : prop_id,         # identifier of related product
#             "subject" : name,           # City name of hotel location
#             "title" : address,          # Hotel name
#             "logicType" : 4,            # Raw value
#             "images" : images,              # List of hotel images excluding room interior images up to 50 images (related image type should be "Card.images")
#             "type" : 4                  # Raw value
#         }

#         img_url = "https://api.mapbox.com/styles/v1/sixtravel/cj46j8tu40c4m2rp9js45y80x/static/{},{},7/1250x1250?access_token=pk.eyJ1Ijoic2l4dHJhdmVsIiwiYSI6ImNqNDZqNXRhdzJiOG0ycm9iOGJmcHBmbWsifQ.ybkyZTQl4kInpOEabItxmA&attribution=false&logo=false".format(longitude, latitude)
#         filename = title.lower().replace(" ", "-") + "-map.png"
#         img_resp = get_response(img_url)
#         img_size, img_mime_type, real_size_x, real_size_y = get_image_properties(img_resp)
#         img_border_color = get_border_color_of_image(img_resp.content)
#         img_average_color = get_average_color_of_image(img_resp.content)
        
#         md5_string = hashlib.md5(("{};{}".format("thumb", filename)).encode('utf-8')).hexdigest()
#         thumb_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#         thumb_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "thumb", img_size, img_border_color, img_average_color)
#         # save_image(thumb_prop["crop"]["x"], thumb_prop["crop"]["y"], thumb_prop["crop"]["width"],thumb_prop["crop"]["height"],thumb_prop["width"],thumb_prop["height"],70, thumb_url, img_resp.content)
#         # images.append(thumb_prop)

#         md5_string = hashlib.md5(("{};{}".format("px1", filename)).encode('utf-8')).hexdigest()
#         px1_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")
        
#         px1_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "px1", img_size, img_border_color, img_average_color)
#         # save_image(thumb_prop["crop"]["x"], px1_prop["crop"]["y"], px1_prop["crop"]["width"],px1_prop["crop"]["height"],px1_prop["width"],px1_prop["height"],70, px1_url, img_resp.content)
#         # images.append(px1_prop)
        
#         md5_string = hashlib.md5(("{};{}".format("px3", filename)).encode('utf-8')).hexdigest()
#         px3_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#         px3_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "px3", img_size, img_border_color, img_average_color)
#         # save_image(px3_prop["crop"]["x"], px3_prop["crop"]["y"], px3_prop["crop"]["width"],px3_prop["crop"]["height"],px3_prop["width"],px3_prop["height"],70, px3_url, img_resp.content)
#         # images.append(px3_prop)
        
#         md5_string = hashlib.md5(("{};{}".format("dx1_2", filename)).encode('utf-8')).hexdigest()
#         dx1_2_url = md5_string + "_" + filename.replace("_", "-").replace(".png",".jpg")

#         dx1_2_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "dx1_2", img_size, img_border_color, img_average_color)
#         # save_image(dx1_2_prop["crop"]["x"], dx1_2_prop["crop"]["y"], dx1_2_prop["crop"]["width"],dx1_2_prop["crop"]["height"],dx1_2_prop["width"],dx1_2_prop["height"],70, dx1_2_url, img_resp.content)
#         # images.append(dx1_2_prop)

#         md5_string = hashlib.md5(("{};{}".format("original", filename)).encode('utf-8')).hexdigest()
#         original_url = md5_string + "_" + filename

#         original_prop = convert_img_structure(filename, real_size_x, real_size_y, "Card.detailImage", img_mime_type, "original", img_size, img_border_color, img_average_color)
#         # save_image(original_prop["crop"]["x"], original_prop["crop"]["y"], original_prop["crop"]["width"],original_prop["crop"]["height"],original_prop["width"],original_prop["height"],70, original_url, img_resp.content)
#         # images.append(orginal_prop)

#         sys.stdout.write("\rProcess: 95%")
#         sys.stdout.flush()

#         detailImage = {
#             "propId"        : prop_id,              # identifier of related product
#             "thumbUrl": thumb_url.replace("_", "-"),
#             "thumbProp"     : thumb_prop,           # Image variant properties
#             "px1Url": px1_url.replace("_", "-"),
#             "px1Prop"       : px1_prop,             # Image variant properties
#             "px3Url": px3_url.replace("_", "-"),
#             "px3Prop"       : px3_prop,             # Image variant properties
#             "dx1_2Url": dx1_2_url.replace("_", "-"),
#             "dx1_2Prop"     : dx1_2_prop,           # Image variant properties
#             "originalUrl": original_url,
#             "originalProp"  : original_prop,        # Image variant properties
#             "type"          : "Card.detailImage"         # Image type (please refer to which value should be specified to parent entity)
#         }
#         map_card = {
#             "propId" : prop_id,         # identifier of related product
#             "subject" : title,          # Hotel name
#             "title" : address,          # Hotel full address
#             "logicType" : 2,            # Raw value
#             "detailImage" : detailImage,         # Map screenshot (please see how to make map screenshot below) (related image type should be "c")
#             "loc": {
#                 "latitude": latitude,   # Latitude
#                 "longitude": longitude  # Longitude
#             },                          # Hotel location
#             "type" : 5                  # Raw value
#         }

#         description_entity = [
#             {
#                 "tag": "blockquote",
#                 "value": tree.xpath('//p[@class="shortintro"]/text()')[0].strip()
#             },
#             {
#                 "tag": "p",
#                 "value": tree.xpath('//div[@class="mainintro"]/div/text()')[0].strip()
#             }
#         ]
#         ul_tags = []
#         try:
#             ul_tags.append(tree.xpath('//li[contains(text(),"Total Rooms:")]/text()')[0])
#             # description_entity.append({
#             #         "tag": "ul",
#             #         "value": tree.xpath('//li[contains(text(),"Total Rooms:")]/text()')[0]
#             #     })
#         except Exception as e:
#             print (e)
#             pass
#         try:
#             ul_tags.append(tree.xpath('//li[contains(text(),"Total Suites:")]/text()')[0])
            
#             # description_entity.append({
#             #         "tag": "ul",
#             #         "value": tree.xpath('//li[contains(text(),"Total Suites:")]/text()')[0]
#             #     })
#         except:
#             pass
#         try:
#             ul_tags.append(tree.xpath('//li[contains(text(),"Total Villas:")]/text()')[0])
#             # description_entity.append({
#             #         "tag": "ul",
#             #         "value": tree.xpath('//li[contains(text(),"Total Villas:")]/text()')[0]
#             #     })
#         except:
#             pass
#         try:
#             ul_tags += tree.xpath('//p[@class="airport"]/text()')[0].strip().split(";")
#         except:
#             pass
#         description_entity.append({
#                 "tag": "ul",
#                 "value": "\n".join(ul_tags)
#             })


#         sys.stdout.write("\rProcess: 98%")
#         sys.stdout.flush()

#         overview_card = {
#             "propId" : prop_id,         # identifier of related product
#             "subject" : "ABOUT HOTEL",  # Raw value
#             "title" : "Overview",       # Raw value
#             "logicType" : 1,            # Raw value
#             "detailImage" : {},         # Hotel outer exterior image (related image type should be "Card.detailImage")
#             "attributedDescription" : description_entity,
#             "type" : 1                  # Raw value
#         }

#         room_selection_card = {
#             "propId" : prop_id,         # identifier of related product
#             "subject" : "STAY",         # Raw value
#             "title" : "Rooms & Rates",  # Raw value
#             "logicType" : 3,            # Raw value
#             "actionType" : 1,           # Raw value
#             "detailImage" : {},         # Hotel inner interior image or room interior image (related image type should be "Card.detailImage")
#             "type" : 1                  # Raw value
#         }

#         card = [slider_card, map_card, overview_card, room_selection_card]
        
#         product_entity = {
#             "propId"		: prop_id,      # Random unique identifier matching the following regular expression /^[A-Za-z0-9]{10}$/, this is needed to locate all entities related to certain product
#             "name"			: name,         # City name of hotel location
#             "title"			: title,        # Hotel name
#             "detailImage"	: {},       # Hotel outer exterior image (related image type should be "Product.detailImage")
#             "service"       : services,      # List of related services
#             "card"		    : card      # List of related cards
#         }
        
#         job_id = hashlib.md5(url).hexdigest()
#         jobUrl = url

#         station = db.session.query(Station).filter(Station.jobUrl == url).first()
#         station.jobStatus = 1
#         station.jobResult = json.dumps(product_entity)
#         db.session.commit()
        
#         sys.stdout.write("\rProcess: 100%")
#         sys.stdout.write("Done!")
#         sys.stdout.flush()

#     except Exception as e:
#         station = db.session.query(Station).filter(Station.jobUrl == url).first()
#         station.jobStatus = -1
#         station.jobResult = ""
#         station.jobProcess = 0
#         db.session.commit()
        

#####################################################################
#####################################################################

def get_country_code(address):
    correct_address = address.replace(".", "").replace(",", " ").lower()
    for cc in country_codes:
        tt = re.findall("\s({}|{}|{})$".format(cc[0],cc[2],cc[3]), correct_address)
        if len(tt) > 0:
            return cc[1]

#####################################################################
#####################################################################

def get_average_color_of_image(content):
    im = Image.open(BytesIO(content)).convert('RGB')
    img2 = im.resize((1,1))
    try:
        (r,g,b) = img2.getpixel((0,0))
    except:
        (r,g,b,a) = img2.getpixel((0,0))
    return '{:02x}{:02x}{:02x}'.format(r, g, b)

#####################################################################
#####################################################################

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

#####################################################################
#####################################################################

def get_image_properties(response):
    im = Image.open(BytesIO(response.content))
    size = im.size
    return response.headers["Content-Length"], response.headers["Content-Type"], size[0], size[1]

#####################################################################
#####################################################################

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

#####################################################################
#####################################################################

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

#####################################################################
#####################################################################

def save_image(cx, cy, cw, ch, rw, rh, rq, fn, content):
    im = Image.open(BytesIO(content))
    im = im.crop((cx, cy, cw, ch))
    im = im.resize((rw, rh))
    im.save(fn)

#####################################################################
#####################################################################

if __name__ == '__main__':
    app.debug = False
    app.run()
